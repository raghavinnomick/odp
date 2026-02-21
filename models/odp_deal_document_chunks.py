"""
Model: DealDocumentChunk
Table: odp_deal_document_chunks

Text chunks extracted from deal documents, each stored with a vector
embedding for Tier-1 RAG similarity search.

Chunk tuple returned by search queries:
    (chunk_text, doc_name, similarity, chunk_id, chunk_index, page_number, deal_id)
"""

# Python Packages
from sqlalchemy import func, Index
from sqlalchemy.dialects.postgresql import TEXT
from pgvector.sqlalchemy import Vector

# Database
from ..config.database import db


class DealDocumentChunk(db.Model):
    """A text chunk from a deal document, with an OpenAI vector embedding."""

    __tablename__ = "odp_deal_document_chunks"

    chunk_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    doc_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_deal_documents.doc_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    deal_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_deals.deal_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    chunk_text = db.Column(TEXT, nullable=False)

    chunk_index = db.Column(
        db.Integer,
        nullable=False,
        doc="Sequential position of this chunk within its document."
    )

    page_number = db.Column(
        db.Integer,
        nullable=True,
        doc="Source PDF page number, if available."
    )

    # 1536 dimensions — OpenAI text-embedding-3-small / ada-002
    embedding = db.Column(Vector(1536), nullable=True)

    chunk_metadata = db.Column(
        db.JSON,
        nullable=True,
        doc="Optional extra info: section heading, table flag, etc."
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Relationships
    document = db.relationship("DealDocument", backref="chunks")
    deal = db.relationship("Deal", backref="document_chunks")

    def __repr__(self):
        return f"<DealDocumentChunk doc_id={self.doc_id} chunk={self.chunk_index}>"


# IVFFlat index for fast approximate cosine-similarity search
Index(
    "idx_deal_document_chunks_embedding",
    DealDocumentChunk.embedding,
    postgresql_using="ivfflat",
    postgresql_ops={"embedding": "vector_cosine_ops"}
)
