""" Deal FAQs Model: Stores approved Q/A pairs per deal... """

# Python Packages
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import TEXT

# Database
from ..config.database import db





class DealFAQ(db.Model):
    # Table Name    
    __tablename__ = "odp_faqs"

    # Columns
    faq_id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    deal_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_deals.deal_id", ondelete = "CASCADE"),
        nullable = False,
        index = True
    )

    question = db.Column(
        TEXT,
        nullable = False
    )

    answer = db.Column(
        TEXT,
        nullable = False
    )

    tags = db.Column(
        db.String(255),
        nullable = True
    )  # e.g. "fees, valuation, timeline"

    source_doc_id = db.Column(
        db.Integer,
        nullable = True
    )

    source_page = db.Column(
        db.String(50),
        nullable = True
    )

    status = db.Column(
        db.String(20),
        nullable = False,
        default = "draft"
    )  # draft / approved / retired

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable = False,
        server_default = func.now()
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable = False,
        server_default = func.now(),
        onupdate = func.now()
    )



    def __repr__(self):
        return f"<DealFAQ {self.faq_id}>"
