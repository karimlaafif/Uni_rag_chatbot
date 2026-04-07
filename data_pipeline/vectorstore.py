import uuid
import logging
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    SparseVectorParams, SparseIndexParams, SparseVector,
    Prefetch, FusionQuery, Fusion,
    Filter, FieldCondition, MatchValue,
)
from fastembed import SparseTextEmbedding
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
from config import settings
from langchain_community.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

# Noms des espaces vectoriels dans Qdrant — centralisés ici pour éviter les
# fautes de frappe dispersées dans le code.
DENSE_VECTOR  = "text"        # 768 dims, nomic-embed-text
SPARSE_VECTOR = "text_sparse" # BM25 via fastembed, dimensions creuses
IMAGE_VECTOR  = "image"       # 512 dims, CLIP ViT-B-32


class QdrantManager:
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        self.collection_name = settings.QDRANT_COLLECTION_NAME

        # ── Modèles d'embedding ──────────────────────────────────────────────
        # Dense : nomic-embed-text, 768 dimensions, très bon en multilingue
        self.embeddings = HuggingFaceEmbeddings(
            model_name="nomic-ai/nomic-embed-text-v1.5",
            model_kwargs={"trust_remote_code": True}
        )

        # Sparse : BM25 via fastembed — léger, pas besoin de GPU.

        logger.info("Chargement du modèle BM25 (fastembed)...")
        self.bm25_model = SparseTextEmbedding(model_name="Qdrant/bm25")

        # Cross-encoder pour le reranking final (inchangé)
        self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        # Vérification / création de la collection avec le bon schéma
        self._ensure_collection()

    # ── Helpers internes ─────────────────────────────────────────────────────

    def _sparse_embed(self, texts: List[str]) -> List[SparseVector]:
        """
        Calcule les sparse vectors BM25 pour une liste de textes en un seul
        batch (fastembed est optimisé pour le traitement par lot).
        Retourne des objets SparseVector prêts à être stockés dans Qdrant.
        """
        raw = list(self.bm25_model.embed(texts))
        return [
            SparseVector(
                indices=r.indices.tolist(),
                values=r.values.tolist(),
            )
            for r in raw
        ]

    # ── Gestion de la collection ─────────────────────────────────────────────

    def _ensure_collection(self):
        """
        Crée la collection si elle n'existe pas.
        Si elle existe mais sans sparse vectors (ancienne version), la recrée
        avec le nouveau schéma hybride — les données devront être ré-ingérées.
        """
        collections = self.client.get_collections().collections
        existing = next(
            (c for c in collections if c.name == self.collection_name), None
        )

        if existing is not None:
            info = self.client.get_collection(self.collection_name)
            sparse_cfg = info.config.params.sparse_vectors or {}
            has_sparse = SPARSE_VECTOR in sparse_cfg

            if not has_sparse:
                logger.warning(
                    f"Collection '{self.collection_name}' trouvée sans sparse vectors. "
                    "Recréation avec le schéma hybrid search. "
                    "Re-lancer l'ingestion pour repeupler la base."
                )
                self.client.delete_collection(self.collection_name)
                existing = None  # on laisse tomber dans le bloc de création

        if existing is None:
            logger.info(
                f"Création de la collection '{self.collection_name}' "
                "(dense text + sparse BM25 + image)."
            )
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    DENSE_VECTOR: VectorParams(size=768, distance=Distance.COSINE),
                    IMAGE_VECTOR: VectorParams(size=512, distance=Distance.COSINE),
                },
                sparse_vectors_config={
                    SPARSE_VECTOR: SparseVectorParams(
                        index=SparseIndexParams(on_disk=False)
                        # on_disk=False : index en RAM → recherche plus rapide.
                        # Passer à True si la machine GPU manque de RAM.
                    )
                },
            )

    # ── Vérification de doublon ──────────────────────────────────────────────

    def hash_exists(self, content_hash: str) -> bool:
        """Retourne True si un document avec ce hash SHA-256 est déjà indexé."""
        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="content_hash", match=MatchValue(value=content_hash))]
            ),
            limit=1,
        )
        return len(records) > 0

    # ── Ingestion ────────────────────────────────────────────────────────────

    def upsert_docs(self, docs: List[Document]):
        """
        Indexe une liste de documents dans Qdrant.
        Pour chaque chunk on stocke :
          - Le vecteur dense (nomic-embed-text, 768 dims)
          - Le vecteur sparse BM25 (fastembed, dimensions creuses)
          - Le vecteur image CLIP si le doc est une image (512 dims)
        Les sparse vectors sont calculés en batch pour l'efficacité.
        """
        if not docs:
            return

        texts = [doc.page_content for doc in docs]

        # Batch embedding : un seul appel modèle pour tous les chunks
        dense_vecs  = self.embeddings.embed_documents(texts)
        sparse_vecs = self._sparse_embed(texts)

        points = []
        for doc, dense_vec, sparse_vec in zip(docs, dense_vecs, sparse_vecs):
            vectors: Dict = {
                DENSE_VECTOR:  dense_vec,
                SPARSE_VECTOR: sparse_vec,
            }

            # Si c'est une image, on ajoute aussi son vecteur CLIP
            if "image_vector" in doc.metadata:
                vectors[IMAGE_VECTOR] = doc.metadata["image_vector"]

            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vectors,
                    payload={"page_content": doc.page_content, **doc.metadata},
                )
            )

        # Upsert par batches de 256 points pour éviter les timeouts
        BATCH_SIZE = 256
        for i in range(0, len(points), BATCH_SIZE):
            self.client.upsert(
                collection_name=self.collection_name,
                points=points[i : i + BATCH_SIZE],
            )

        has_images = any("image_vector" in d.metadata for d in docs)
        logger.info(
            f"{len(points)} chunks indexés (dense + sparse BM25"
            + (" + image" if has_images else "")
            + ")."
        )

    # ── Recherche hybride ────────────────────────────────────────────────────

    def hybrid_search(self, query: str, top_k: int = 10) -> List[Document]:
        """
        Recherche hybride en deux temps :

        1. Qdrant exécute en parallèle :
           - Dense search  : similarité sémantique (nomic-embed-text)
           - Sparse search : correspondance de mots-clés (BM25)
           puis fusionne les deux listes avec RRF (Reciprocal Rank Fusion).

        2. Le Cross-Encoder reranke les résultats fusionnés pour affiner
           la pertinence au niveau de la paire (question, chunk).

        """
        # Encodage de la requête sous les deux formes
        dense_vec  = self.embeddings.embed_query(query)
        sparse_vec = self._sparse_embed([query])[0]

        # Requête hybride native Qdrant avec fusion RRF
        response = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                Prefetch(
                    query=dense_vec,
                    using=DENSE_VECTOR,
                    limit=top_k * 2,
                ),
                Prefetch(
                    query=sparse_vec,
                    using=SPARSE_VECTOR,
                    limit=top_k * 2,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=top_k * 2,  # le reranker va réduire à top_k
        )

        docs = [
            Document(
                page_content=r.payload.get("page_content", ""),
                metadata=r.payload,
            )
            for r in response.points
        ]

        logger.debug(
            f"Hybrid search pour '{query[:60]}...' : "
            f"{len(docs)} candidats avant reranking."
        )

        return self.rerank(query, docs, top_k)

    # ── Reranking ────────────────────────────────────────────────────────────

    def rerank(self, query: str, docs: List[Document], top_k: int) -> List[Document]:
        """
        Cross-Encoder reranking : analyse chaque paire (query, chunk) ensemble
        pour un score de pertinence bien plus précis que la similarité vectorielle.
        """
        if not docs:
            return []

        pairs = [[query, doc.page_content] for doc in docs]
        scores = self.cross_encoder.predict(pairs)

        ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
        for doc, score in ranked[:top_k]:
            doc.metadata["rerank_score"] = round(float(score), 4)
        return [doc for doc, _ in ranked[:top_k]]

    # ── Mise à jour incrémentale ─────────────────────────────────────────────

    def knowledge_update(self, file_path: str, metadata: Dict[str, Any]):
        """Ingère un fichier et l'ajoute à la base sans reconstruire."""
        from data_pipeline.ingestion import DataIngestionPipeline
        pipeline = DataIngestionPipeline(self)
        docs = pipeline.ingest_file(file_path, metadata)
        if docs:
            self.upsert_docs(docs)
