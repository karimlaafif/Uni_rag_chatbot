"""
Semantic Chunker for the University RAG pipeline.

Instead of splitting text by a fixed character count (which cuts ideas mid-sentence),
this chunker:
  1. Splits text into sentences (handles French, Arabic, English punctuation)
  2. Embeds each sentence with a lightweight model
  3. Measures the cosine similarity between consecutive sentences
  4. Finds "breakpoints" where the similarity drops — meaning the topic has shifted
  5. Groups sentences into semantically coherent chunks

Fallback: if the text is too short or embedding fails, it falls back to the
RecursiveCharacterTextSplitter used previously.
"""

import re
import logging
import numpy as np
from typing import List, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Multilingual sentence splitter
# ---------------------------------------------------------------------------

# Handles end-of-sentence punctuation for French, English and Arabic.
# Arabic sentence-final marks: ؟ (question) and ۔ or . and !
_SENTENCE_SPLIT_PATTERN = re.compile(
    r'(?<=[.!?؟।\n])\s+'          # split after common punctuation + whitespace
    r'|(?<=[\.\!\?؟])\s*\n'       # or after punctuation at end of line
    r'|\n{2,}'                     # or on double newline (paragraph break)
)


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences in a language-agnostic way.
    Returns only non-empty sentences with meaningful content (>= 15 chars).
    """
    raw = _SENTENCE_SPLIT_PATTERN.split(text)
    sentences = []
    for s in raw:
        s = s.strip()
        # Skip very short fragments (headers fragments, page numbers, etc.)
        if len(s) >= 15:
            sentences.append(s)
    return sentences


# ---------------------------------------------------------------------------
# Core SemanticChunker class
# ---------------------------------------------------------------------------

class SemanticChunker:
    """
    Splits text into semantically coherent chunks by detecting topic shifts
    in the embedding space.

    Parameters
    ----------
    model_name : str
        A SentenceTransformer-compatible model. We use a multilingual model
        by default so that French / Arabic / English documents are all handled.
    breakpoint_percentile : float (0–100)
        We compute the distribution of cosine-similarity drops between
        consecutive sentences and cut wherever the drop is in the bottom
        `breakpoint_percentile` percent. Higher value → more, smaller chunks.
        Lower value → fewer, larger chunks.  Default 70 works well in practice.
    max_chunk_chars : int
        Hard ceiling: even within a semantic block, split if the chunk would
        exceed this many characters.  Prevents runaway chunks.
    min_chunk_chars : int
        Chunks smaller than this are either merged with the next one or
        discarded (too short to be useful for retrieval).
    fallback_chunk_size : int
        Chunk size used by the RecursiveCharacterTextSplitter fallback.
    fallback_overlap : int
        Overlap used by the fallback splitter.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        breakpoint_percentile: float = 70.0,
        max_chunk_chars: int = 1500,
        min_chunk_chars: int = 200,
        fallback_chunk_size: int = 512,
        fallback_overlap: int = 64,
    ):
        logger.info(f"Loading semantic chunker embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.breakpoint_percentile = breakpoint_percentile
        self.max_chunk_chars = max_chunk_chars
        self.min_chunk_chars = min_chunk_chars

        # Fallback splitter (same as the previous implementation)
        self._fallback = RecursiveCharacterTextSplitter(
            chunk_size=fallback_chunk_size,
            chunk_overlap=fallback_overlap,
            length_function=len,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def split_text(self, text: str) -> List[str]:
        """
        Main entry point. Returns a list of chunk strings.
        Falls back to RecursiveCharacterTextSplitter when the text is too
        short to warrant semantic analysis.
        """
        sentences = split_into_sentences(text)

        # Not enough sentences → fall back
        if len(sentences) < 4:
            logger.debug("Too few sentences for semantic splitting, using fallback.")
            return self._fallback.split_text(text)

        try:
            return self._semantic_split(sentences)
        except Exception as exc:
            logger.warning(f"Semantic split failed ({exc}), using fallback.")
            return self._fallback.split_text(text)

    def create_documents(
        self, text: str, metadata: Optional[dict] = None
    ) -> List[Document]:
        """
        Convenience wrapper: split text and wrap each chunk in a LangChain Document.
        Adds 'chunk_index' and a brief 'chunk_preview' to the metadata.
        """
        chunks = self.split_text(text)
        base_meta = metadata or {}
        docs = []
        for i, chunk in enumerate(chunks):
            meta = {
                **base_meta,
                "chunk_index": i,
                "chunk_total": len(chunks),
                # First 80 chars as a quick preview (useful for debugging)
                "chunk_preview": chunk[:80].replace("\n", " "),
            }
            docs.append(Document(page_content=chunk, metadata=meta))
        return docs

    # ------------------------------------------------------------------
    # Internal logic
    # ------------------------------------------------------------------

    def _embed_sentences(self, sentences: List[str]) -> np.ndarray:
        """Embed all sentences in one batch for efficiency."""
        return self.model.encode(sentences, batch_size=32, show_progress_bar=False)

    def _compute_similarity_drops(self, embeddings: np.ndarray) -> np.ndarray:
        """
        For each pair of consecutive sentences compute how much the cosine
        similarity DROPS compared to its neighbours.  A large drop indicates
        a topic shift.

        We use the *gradient* of similarities rather than raw similarity so
        that the threshold adapts to each document's own distribution.
        """
        n = len(embeddings)
        # Pairwise cosine similarities between consecutive sentences
        sims = np.array([
            cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
            for i in range(n - 1)
        ])
        return sims

    def _find_breakpoints(self, sims: np.ndarray) -> List[int]:
        """
        A breakpoint is placed *after* sentence i when the similarity
        sim[i] is below the `breakpoint_percentile`-th percentile of all
        similarities in this document.

        Using a document-level percentile (not a fixed threshold) means the
        chunker adapts to each document's density of topic changes.
        """
        threshold = np.percentile(sims, 100 - self.breakpoint_percentile)
        # Index i means "break after sentence i"
        return [i for i, s in enumerate(sims) if s < threshold]

    def _sentences_to_chunks(
        self, sentences: List[str], breakpoints: List[int]
    ) -> List[str]:
        """
        Group sentences into chunks using the detected breakpoints.
        Also enforces max_chunk_chars and merges orphan mini-chunks.
        """
        breakpoint_set = set(breakpoints)
        chunks: List[str] = []
        current: List[str] = []
        current_len: int = 0

        for i, sentence in enumerate(sentences):
            current.append(sentence)
            current_len += len(sentence) + 1  # +1 for the space

            is_last = (i == len(sentences) - 1)
            hit_breakpoint = i in breakpoint_set
            hit_max = current_len >= self.max_chunk_chars

            if (hit_breakpoint or hit_max) and not is_last:
                chunk_text = " ".join(current).strip()
                if len(chunk_text) >= self.min_chunk_chars:
                    chunks.append(chunk_text)
                    current = []
                    current_len = 0
                # If the chunk is too small, keep accumulating (merge forward)

        # Last group
        if current:
            tail = " ".join(current).strip()
            if tail:
                if chunks and len(tail) < self.min_chunk_chars:
                    # Merge orphan tail into the previous chunk
                    chunks[-1] = chunks[-1] + " " + tail
                else:
                    chunks.append(tail)

        return chunks

    def _semantic_split(self, sentences: List[str]) -> List[str]:
        """Full semantic splitting pipeline."""
        embeddings = self._embed_sentences(sentences)
        sims = self._compute_similarity_drops(embeddings)
        breakpoints = self._find_breakpoints(sims)
        chunks = self._sentences_to_chunks(sentences, breakpoints)
        logger.debug(
            f"Semantic split: {len(sentences)} sentences → "
            f"{len(breakpoints)} breakpoints → {len(chunks)} chunks"
        )
        return chunks
