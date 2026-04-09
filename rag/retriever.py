"""
rag/retriever.py — MultiQuery + Hybrid + Cross-Encoder Retriever
=================================================================
Implements a two-stage retrieval pipeline:

  Stage 1 — MultiQuery expansion
    The user's question is rewritten into N variants (default 3) so that
    different phrasings hit different embedding clusters in Qdrant.

  Stage 2 — Hybrid search + RRF + Cross-Encoder reranking
    Each variant runs hybrid search (dense + BM25 sparse, fused with RRF).
    All candidate chunks are deduplicated then re-ranked by a Cross-Encoder
    for maximum precision.

Usage:
    from rag.retriever import build_retriever

    retriever = build_retriever(qdrant_manager, llm)
    docs = retriever.retrieve("Quels documents pour s'inscrire ?", user_role="student")
"""

import logging
from typing import List, Optional

from langchain_core.documents import Document

from data_pipeline.vectorstore import QdrantManager
from rag.prompt import build_query_rewrite_prompt

logger = logging.getLogger(__name__)

# ── Default tuning parameters ────────────────────────────────────────────────

DEFAULT_TOP_K     = 20   # candidates per variant before reranking
DEFAULT_RERANK_N  = 5    # final chunks returned to the LLM
DEFAULT_NQ        = 3    # number of query variants generated


class HybridMultiQueryRetriever:
    """
    Two-stage retriever:
      1. Generate N query variants with an LLM
      2. Run hybrid search for each variant → deduplicate → rerank
    """

    def __init__(
        self,
        qdrant_manager: QdrantManager,
        llm,
        top_k: int = DEFAULT_TOP_K,
        rerank_n: int = DEFAULT_RERANK_N,
        n_queries: int = DEFAULT_NQ,
    ):
        self.qdrant  = qdrant_manager
        self.llm     = llm
        self.top_k   = top_k
        self.rerank_n = rerank_n
        self.n_queries = n_queries
        self._rewrite_prompt = build_query_rewrite_prompt()

    # ── Query expansion ──────────────────────────────────────────────────────

    def _expand_query(self, question: str) -> List[str]:
        """
        Generate `n_queries` alternative phrasings using the LLM.
        Falls back to the original question on any error.
        """
        try:
            chain  = self._rewrite_prompt | self.llm
            result = chain.invoke({"question": question})
            raw    = result.content if hasattr(result, "content") else str(result)

            variants = [
                line.strip()
                for line in raw.strip().splitlines()
                if line.strip() and len(line.strip()) > 10
            ]

            # Prepend original so it is always included
            all_queries = [question] + variants[: self.n_queries]
            logger.debug(f"Query expansion: {len(all_queries)} variants for '{question[:60]}'")
            return all_queries

        except Exception as e:
            logger.warning(f"Query expansion failed ({e}). Using original question only.")
            return [question]

    # ── Deduplication ────────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(docs: List[Document]) -> List[Document]:
        """Remove duplicate chunks by page_content fingerprint."""
        seen = set()
        unique = []
        for doc in docs:
            key = doc.page_content[:200]  # first 200 chars as fingerprint
            if key not in seen:
                seen.add(key)
                unique.append(doc)
        return unique

    # ── Public API ───────────────────────────────────────────────────────────

    def retrieve(
        self,
        question: str,
        user_role: str = "public",
        image_base64: Optional[str] = None,
    ) -> List[Document]:
        """
        Full retrieval pipeline for a given question.

        Parameters
        ----------
        question     : User's natural-language question
        user_role    : RBAC role — controls which documents are visible
        image_base64 : Optional base64-encoded image for multimodal retrieval

        Returns
        -------
        List of top-N reranked Document objects
        """
        # 1. Multi-query expansion
        queries = self._expand_query(question)

        # 2. Hybrid search for each variant (without per-variant reranking)
        all_candidates: List[Document] = []
        for q in queries:
            try:
                # We pass a large top_k here; the final reranking step reduces it
                candidates = self.qdrant.hybrid_search(
                    query=q,
                    top_k=self.top_k,
                    user_role=user_role,
                )
                all_candidates.extend(candidates)
            except Exception as e:
                logger.warning(f"Hybrid search failed for variant '{q[:50]}': {e}")

        if not all_candidates:
            logger.warning("No candidates retrieved. Returning empty list.")
            return []

        # 3. Deduplicate across all variants
        unique_candidates = self._deduplicate(all_candidates)
        logger.debug(
            f"Retrieved {len(all_candidates)} total chunks, "
            f"{len(unique_candidates)} unique after dedup."
        )

        # 4. Global rerank over all unique candidates → top rerank_n
        reranked = self.qdrant.rerank(question, unique_candidates, self.rerank_n)

        logger.info(
            f"Retrieval complete: {len(reranked)} chunks returned "
            f"(role={user_role}, variants={len(queries)})"
        )
        return reranked


def build_retriever(
    qdrant_manager: QdrantManager,
    llm,
    top_k: int = DEFAULT_TOP_K,
    rerank_n: int = DEFAULT_RERANK_N,
    n_queries: int = DEFAULT_NQ,
) -> HybridMultiQueryRetriever:
    """
    Factory function — builds and returns a configured retriever.

    Parameters
    ----------
    qdrant_manager : Shared QdrantManager instance
    llm            : LangChain-compatible LLM for query expansion
    top_k          : Candidate pool size per query variant
    rerank_n       : Final number of chunks after cross-encoder reranking
    n_queries      : Number of query variants to generate

    Returns
    -------
    HybridMultiQueryRetriever instance
    """
    return HybridMultiQueryRetriever(
        qdrant_manager=qdrant_manager,
        llm=llm,
        top_k=top_k,
        rerank_n=rerank_n,
        n_queries=n_queries,
    )
