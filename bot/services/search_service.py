"""
Service: SearchService

Tier-1 RAG vector search over odp_deal_document_chunks.

Converts a user question to an OpenAI embedding, then runs a
cosine-similarity search against the chunks table.

Key design decisions:
  - Each query runs inside a try/except with db.session.rollback() on failure.
    This prevents the "InFailedSqlTransaction" error from poisoning the
    session for subsequent queries in the same request.
  - Returns a consistent 7-tuple so callers never need to guard tuple length.
  - deal_id=None → searches all deals (used by /bot/ask endpoint).
"""

# Python Packages
from typing import List, Tuple, Optional

# Database
from sqlalchemy import text
from ...config.database import db

# Vendors
from ...vendors.openai import EmbeddingService

# Constants
from ...base import constants


class SearchService:
    """
    Vector similarity search over odp_deal_document_chunks.

    Each public method is transaction-safe: exceptions are caught, the
    session is rolled back, and an empty list is returned so the caller
    can continue gracefully.
    """

    # Chunk tuple field positions (for documentation clarity)
    IDX_TEXT       = 0
    IDX_DOC_NAME   = 1
    IDX_SIMILARITY = 2
    IDX_CHUNK_ID   = 3
    IDX_CHUNK_IDX  = 4
    IDX_PAGE       = 5
    IDX_DEAL_ID    = 6

    def __init__(self):
        self.embedding_service = EmbeddingService()

    # ── Public ─────────────────────────────────────────────────────────────────

    def search_similar_chunks(
        self,
        question: str,
        deal_id: Optional[int] = None,
        top_k: int = constants.BOT_DEFAULT_TOP_K,
        similarity_threshold: float = constants.BOT_SIMILARITY_THRESHOLD
    ) -> List[Tuple]:
        """
        Find document chunks semantically similar to *question*.

        Args:
            question:            The (possibly enhanced) user question.
            deal_id:             Scope search to one deal. None = all deals.
            top_k:               Max chunks to return.
            similarity_threshold: Min cosine similarity (0–1).

        Returns:
            List of 7-tuples:
            (chunk_text, doc_name, similarity, chunk_id, chunk_index,
             page_number, deal_id)
            Empty list on any error.
        """
        try:
            print(f"🧮 Generating question embedding...")
            embedding = self.embedding_service.generate_embedding(question)
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"

            if deal_id:
                print(f"🔍 Searching deal_id={deal_id}...")
                return self._search_single_deal(
                    embedding_str, deal_id, top_k, similarity_threshold
                )
            else:
                print("🔍 Searching across all deals...")
                return self._search_all_deals(
                    embedding_str, top_k, similarity_threshold
                )

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  SearchService.search_similar_chunks failed: {exc}")
            return []

    # ── Private ────────────────────────────────────────────────────────────────

    def _search_single_deal(
        self,
        embedding_str: str,
        deal_id: int,
        top_k: int,
        threshold: float
    ) -> List[Tuple]:
        """Vector search scoped to one deal. Rolls back session on failure."""
        try:
            sql = text("""
                SELECT
                    dc.chunk_text,
                    dd.doc_name,
                    1 - (dc.embedding <=> CAST(:emb AS vector)) AS similarity,
                    dc.chunk_id,
                    dc.chunk_index,
                    dc.page_number,
                    dc.deal_id
                FROM odp_deal_document_chunks dc
                JOIN odp_deal_documents dd ON dc.doc_id = dd.doc_id
                WHERE dc.deal_id = :deal_id
                  AND dc.embedding IS NOT NULL
                  AND (1 - (dc.embedding <=> CAST(:emb AS vector))) >= :threshold
                ORDER BY dc.embedding <=> CAST(:emb AS vector)
                LIMIT :top_k
            """)

            rows = db.session.execute(sql, {
                "emb": embedding_str,
                "deal_id": deal_id,
                "threshold": threshold,
                "top_k": top_k
            }).fetchall()

            print(f"✅ Found {len(rows)} chunks in deal_id={deal_id}")
            return rows

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  _search_single_deal failed (deal_id={deal_id}): {exc}")
            return []

    def _search_all_deals(
        self,
        embedding_str: str,
        top_k: int,
        threshold: float
    ) -> List[Tuple]:
        """Vector search across all deals. Rolls back session on failure."""
        try:
            sql = text("""
                SELECT
                    dc.chunk_text,
                    dd.doc_name,
                    1 - (dc.embedding <=> CAST(:emb AS vector)) AS similarity,
                    dc.chunk_id,
                    dc.chunk_index,
                    dc.page_number,
                    dc.deal_id
                FROM odp_deal_document_chunks dc
                JOIN odp_deal_documents dd ON dc.doc_id = dd.doc_id
                WHERE dc.embedding IS NOT NULL
                  AND (1 - (dc.embedding <=> CAST(:emb AS vector))) >= :threshold
                ORDER BY dc.embedding <=> CAST(:emb AS vector)
                LIMIT :top_k
            """)

            rows = db.session.execute(sql, {
                "emb": embedding_str,
                "threshold": threshold,
                "top_k": top_k
            }).fetchall()

            print(f"✅ Found {len(rows)} chunks across all deals")
            return rows

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  _search_all_deals failed: {exc}")
            return []
