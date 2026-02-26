"""
Model: DealDynamicFact
Table: odp_deal_dynamic_facts

Stores team-supplied facts and Q&A pairs during chat sessions.
Serves as the Tier-2 fallback in the 3-tier RAG pipeline.

Two usage modes:
  1. Q&A mode   — (question + answer + embedding) for vector similarity search
  2. Fact mode  — (fact_key + fact_value) for structured key-value lookups
     e.g. fact_key="share_price", fact_value="~$378"

Both modes are stored in the same table so they can be searched together.
"""

# Python Packages
from datetime import datetime
from sqlalchemy import func, Index

# Vendor
from pgvector.sqlalchemy import Vector

# Database
from ..config.database import db





class DealDynamicFact(db.Model):
    """
    Dynamic facts and Q&A pairs supplied by ODP team members during chat.

    Records are written when:
      - A team member answers a "needs_info" bot message  → Q&A mode
      - The FactExtractorService detects a factual value  → Fact mode

    All approved records are immediately searchable by the bot.
    """

    # Table Name
    __tablename__ = "odp_deal_dynamic_facts"

    # ── Primary Key
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    # ── Foreign Key
    deal_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_deals.deal_id", ondelete = "CASCADE"),
        nullable = False,
        index = True,
        doc = "The deal this fact belongs to."
    )

    # ── Q&A Fields (used by vector similarity search)
    question = db.Column(
        db.Text,
        nullable = True,
        doc = "The investor question that triggered this entry."
    )

    answer = db.Column(
        db.Text,
        nullable = True,
        doc = "The answer provided by the ODP team member."
    )

    # ── Fact Fields (used by FactExtractorService key-value lookups)
    fact_key = db.Column(
        db.String(255),
        nullable = True,
        index = True,
        doc = "Snake_case key, e.g. 'share_price', 'minimum_ticket'."
    )

    fact_value = db.Column(
        db.Text,
        nullable = True,
        doc = "Raw value as stated by the team member, e.g. '~$378'."
    )

    # ── Vector Embedding
    embedding = db.Column(
        Vector(1536),
        nullable = True,
        doc = "OpenAI ada-002 / text-embedding-3-small embedding (1536 dims). "
            "Embedding is generated over 'question + answer' for richer matching."
    )

    # ── Approval & Source
    approval_status = db.Column(
        db.String(50),
        nullable = False,
        default = "approved",
        doc = "'approved' | 'pending'. Team-member facts are auto-approved."
    )

    created_at = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        server_default = func.now()
    )


    def __repr__(self):
        identifier = self.fact_key or (self.question[:40] if self.question else "?")
        return f"<DealDynamicFact deal_id={self.deal_id} '{identifier}'>"


# ── Vector Index for fast cosine-similarity search
Index(
    "idx_deal_dynamic_facts_embedding",
    DealDynamicFact.embedding,
    postgresql_using = "ivfflat",
    postgresql_ops = {"embedding": "vector_cosine_ops"}
)
