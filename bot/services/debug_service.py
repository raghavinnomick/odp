"""
Service: DebugService

Development / diagnostics helper.
Exposes deal stats, sample chunks, and raw vector search results
for inspection via the GET /bot/debug/<deal_id> endpoint.

NOT intended for production use.
"""

# Python Packages
from typing import List, Dict

# Database
from sqlalchemy import text, func
from ...config.database import db

# Models
from ...models.odp_deal_document_chunks import DealDocumentChunk
from ...models.odp_deal_document import DealDocument


class DebugService:
    """
    Diagnostic utilities for inspecting vector search and document data.
    All methods are read-only and transaction-safe.
    """

    def get_deal_stats(self, deal_id: int) -> Dict:
        """
        Return document and chunk counts for a deal.

        Args:
            deal_id: The deal to inspect.

        Returns:
            Dict with total_documents, total_chunks, chunks_with_embeddings,
            and a per-document breakdown.
        """
        try:
            doc_count = (
                db.session.query(DealDocument)
                .filter(DealDocument.deal_id == deal_id)
                .count()
            )

            chunk_count = (
                db.session.query(DealDocumentChunk)
                .filter(DealDocumentChunk.deal_id == deal_id)
                .count()
            )

            embedded_count = db.session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM odp_deal_document_chunks
                    WHERE deal_id = :deal_id
                      AND embedding IS NOT NULL
                """),
                {"deal_id": deal_id}
            ).scalar()

            documents = (
                db.session.query(
                    DealDocument.doc_id,
                    DealDocument.doc_name,
                    func.count(DealDocumentChunk.chunk_id).label("chunk_count")
                )
                .outerjoin(DealDocumentChunk, DealDocument.doc_id == DealDocumentChunk.doc_id)
                .filter(DealDocument.deal_id == deal_id)
                .group_by(DealDocument.doc_id, DealDocument.doc_name)
                .all()
            )

            return {
                "deal_id":               deal_id,
                "total_documents":       doc_count,
                "total_chunks":          chunk_count,
                "chunks_with_embeddings": embedded_count,
                "documents": [
                    {"doc_id": d.doc_id, "doc_name": d.doc_name, "chunk_count": d.chunk_count}
                    for d in documents
                ]
            }

        except Exception as exc:
            db.session.rollback()
            return {"error": str(exc), "deal_id": deal_id}

    def get_sample_chunks(self, deal_id: int, limit: int = 3) -> List[Dict]:
        """
        Return a small sample of chunks for quick content inspection.

        Args:
            deal_id: The deal to inspect.
            limit:   Number of chunks to return (default 3).

        Returns:
            List of chunk summary dicts.
        """
        try:
            chunks = (
                db.session.query(DealDocumentChunk)
                .filter(DealDocumentChunk.deal_id == deal_id)
                .limit(limit)
                .all()
            )

            return [
                {
                    "chunk_id":         c.chunk_id,
                    "doc_id":           c.doc_id,
                    "text_preview":     c.chunk_text[:200] + "...",
                    "has_embedding":    c.embedding is not None,
                    "embedding_dims":   len(c.embedding) if c.embedding is not None else 0
                }
                for c in chunks
            ]

        except Exception as exc:
            db.session.rollback()
            return [{"error": str(exc)}]

    def test_search(self, deal_id: int, question: str) -> Dict:
        """
        Run a raw vector search WITHOUT a similarity threshold so you can
        see the top similarity scores for any question, even weak matches.

        Args:
            deal_id:  The deal to search in.
            question: The test question.

        Returns:
            Dict with question, total_results, and top_results list.
        """
        try:
            from .search_service import SearchService

            search = SearchService()
            embedding = search.embedding_service.generate_embedding(question)
            emb_str = "[" + ",".join(map(str, embedding)) + "]"

            rows = db.session.execute(
                text("""
                    SELECT
                        dc.chunk_id,
                        dc.chunk_text,
                        dd.doc_name,
                        1 - (dc.embedding <=> CAST(:emb AS vector)) AS similarity
                    FROM odp_deal_document_chunks dc
                    JOIN odp_deal_documents dd ON dc.doc_id = dd.doc_id
                    WHERE dc.deal_id = :deal_id
                      AND dc.embedding IS NOT NULL
                    ORDER BY dc.embedding <=> CAST(:emb AS vector)
                    LIMIT 10
                """),
                {"emb": emb_str, "deal_id": deal_id}
            ).fetchall()

            return {
                "question":      question,
                "total_results": len(rows),
                "top_results": [
                    {
                        "chunk_id":        r[0],
                        "text_preview":    r[1][:150] + "...",
                        "doc_name":        r[2],
                        "similarity_score": f"{r[3]:.4f}"
                    }
                    for r in rows[:5]
                ]
            }

        except Exception as exc:
            db.session.rollback()
            return {"error": str(exc), "question": question}
