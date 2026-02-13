""" Deal Terms Model: Stores structured deck facts (one row per deal)... """

# Python Packages
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import TEXT

# Database
from ..config.database import db





class DealTerm(db.Model):
    # Table Name
    __tablename__ = "odp_deal_terms"

    # Columns
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    deal_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_deals.deal_id", ondelete = "CASCADE"),
        nullable = False,
        index = True
    )

    security_type = db.Column(db.String(100), nullable = True)

    valuation = db.Column(db.String(100), nullable = True)

    round_type = db.Column(db.String(100), nullable = True)

    structure_summary = db.Column(TEXT, nullable = True)

    fee_summary = db.Column(TEXT, nullable = True)

    source_doc_id = db.Column(db.Integer, nullable = True)

    source_page = db.Column(db.String(50), nullable = True)

    created_at = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        server_default = func.now()
    )

    updated_at = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        server_default =func.now(),
        onupdate = func.now()
    )



    def __repr__(self):
        return f"<DealTerms deal_id={self.deal_id}>"
