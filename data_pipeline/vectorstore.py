import os
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, ScoredPoint
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
from config import settings
from langchain_community.embeddings import HuggingFaceEmbeddings

class QdrantManager:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        
        # Ensure collection exists
        self._ensure_collection()
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        self.embeddings = HuggingFaceEmbeddings(model_name="nomic-ai/nomic-embed-text-v1.5", model_kwargs={"trust_remote_code": True})

    def _ensure_collection(self):
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "text": VectorParams(size=768, distance=Distance.COSINE),
                    "image": VectorParams(size=512, distance=Distance.COSINE)
                }
            )

    def hash_exists(self, content_hash: str) -> bool:
        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter={
                "must": [
                    {
                        "key": "content_hash",
                        "match": {"value": content_hash}
                    }
                ]
            },
            limit=1
        )
        return len(records) > 0

    def upsert_docs(self, docs: List[Document]):
        points = []
        for doc in docs:
            doc_id = str(uuid.uuid4())
            text_vec = self.embeddings.embed_query(doc.page_content)
            
            vectors = {"text": text_vec}
            if "image_vector" in doc.metadata:
                vectors["image"] = doc.metadata["image_vector"]
                
            points.append(
                PointStruct(
                    id=doc_id,
                    vector=vectors,
                    payload={"page_content": doc.page_content, **doc.metadata}
                )
            )
        
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

    def hybrid_search(self, query: str, top_k: int = 10) -> List[Document]:
        query_vector = self.embeddings.embed_query(query)
        # Using dense vectors for simplicity, BM25 requires specialized setup
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=("text", query_vector),
            limit=top_k * 2
        )
        docs = [Document(page_content=r.payload.get("page_content", ""), metadata=r.payload) for r in results]
        return self.rerank(query, docs, top_k)

    def rerank(self, query: str, docs: List[Document], top_k: int) -> List[Document]:
        if not docs:
            return []
        pairs = [[query, doc.page_content] for doc in docs]
        scores = self.cross_encoder.predict(pairs)
        
        doc_score_pairs = list(zip(docs, scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        return [doc for doc, score in doc_score_pairs[:top_k]]
        
    def knowledge_update(self, file_path: str, metadata: Dict[str, Any]):
        from data_pipeline.ingestion import DataIngestionPipeline
        pipeline = DataIngestionPipeline(self)
        docs = pipeline.ingest_file(file_path, metadata)
        if docs:
            self.upsert_docs(docs)
