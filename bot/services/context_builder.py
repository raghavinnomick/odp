"""
Service: ContextBuilder
========================
Transforms raw RAG chunk tuples into formatted strings and metadata
structures ready to inject into LLM prompts.

Chunk tuple layout (7 values — matches SearchService output):
    [0] chunk_text    str
    [1] doc_name      str
    [2] similarity    float   (cosine similarity 0–1)
    [3] chunk_id      int
    [4] chunk_index   int
    [5] page_number   int | None
    [6] deal_id       int
"""

# Python Packages
from typing import List, Tuple, Dict

# Config
from ..config import thresholds


class ContextBuilder:
    """
    Formats chunk tuples for LLM consumption and confidence scoring.
    Stateless — safe to reuse across requests.
    """

    def build_context(self, chunks: List[Tuple]) -> str:
        """
        Build a formatted context string from retrieved chunks.
        Returns "" if chunks is empty.
        """
        if not chunks:
            return ""

        parts = []
        for i, chunk in enumerate(chunks, 1):
            chunk_text  = chunk[0]
            doc_name    = chunk[1]
            similarity  = chunk[2]
            page_number = chunk[5] if len(chunk) > 5 else None

            source_info = f"[Source: {doc_name}"
            if page_number:
                source_info += f", Page {page_number}"
            source_info += f", Relevance: {similarity:.2%}]"

            parts.append(f"Document {i}:\n{source_info}\n{chunk_text}\n")

        return "\n---\n".join(parts)


    def extract_sources(self, chunks: List[Tuple]) -> List[Dict]:
        """
        Build a de-duplicated list of source references for the API response.

        Returns:
            List of {"document_name", "relevance", "preview", "page_number"?}
        """
        sources   = []
        seen_docs = set()

        for chunk in chunks:
            doc_name    = chunk[1]
            similarity  = chunk[2]
            chunk_text  = chunk[0]
            page_number = chunk[5] if len(chunk) > 5 else None

            if doc_name in seen_docs:
                continue

            preview_len = thresholds.SOURCE_PREVIEW_MAX_LENGTH
            source = {
                "document_name": doc_name,
                "relevance":     f"{similarity:.2%}",
                "preview":       chunk_text[:preview_len] + "..." if len(chunk_text) > preview_len else chunk_text
            }
            if page_number:
                source["page_number"] = page_number

            sources.append(source)
            seen_docs.add(doc_name)

        return sources


    def calculate_confidence(self, chunks: List[Tuple]) -> str:
        """
        Derive a confidence tier from the average similarity of returned chunks.

        Thresholds (from thresholds.py):
          >= CONFIDENCE_HIGH_THRESHOLD   → "high"
          >= CONFIDENCE_MEDIUM_THRESHOLD → "medium"
          <  CONFIDENCE_MEDIUM_THRESHOLD → "low"
        """
        if not chunks:
            return "low"

        avg_similarity = sum(c[2] for c in chunks) / len(chunks)

        if avg_similarity >= thresholds.CONFIDENCE_HIGH_THRESHOLD:
            return "high"
        if avg_similarity >= thresholds.CONFIDENCE_MEDIUM_THRESHOLD:
            return "medium"
        return "low"
