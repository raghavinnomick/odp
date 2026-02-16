""" Document Chunks Model: Stores text chunks with embeddings for RAG... """
# Python Packages
from sqlalchemy import func, Index
from sqlalchemy.dialects.postgresql import TEXT
from pgvector.sqlalchemy import Vector

# Database
from ..config.database import db





class DealDocumentChunk(db.Model):
    # Table Name
    __tablename__ = "odp_deal_document_chunks"
    
    # Columns
    chunk_id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    
    doc_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_deal_documents.doc_id", ondelete = "CASCADE"),
        nullable = False,
        index = True
    )
    
    deal_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_deals.deal_id", ondelete = "CASCADE"),
        nullable = False,
        index = True
    )
    
    chunk_text = db.Column(TEXT, nullable = False)
    
    chunk_index = db.Column(db.Integer, nullable = False)  # Order within document

    page_number = db.Column(db.Integer, nullable = True)  # Optional: source page

    # Vector embedding - 1536 dimensions for OpenAI text-embedding-3-small/ada-002
    embedding = db.Column(Vector(1536), nullable = True)

    # Metadata (can store additional info like section, headings, etc.)
    chunk_metadata = db.Column(db.JSON, nullable = True)

    created_at = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        server_default = func.now()
    )
    
    # Relationships
    document = db.relationship("DealDocument", backref = "chunks")
    deal = db.relationship("Deal", backref = "document_chunks")

    def __repr__(self):
        return f"<DealDocumentChunk doc_id={self.doc_id} chunk={self.chunk_index}>"



# Create index for vector similarity search
Index(
    'idx_deal_document_chunks_embedding',
    DealDocumentChunk.embedding,
    postgresql_using = 'ivfflat',
    postgresql_ops = {'embedding': 'vector_cosine_ops'}
)