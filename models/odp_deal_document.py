"""
Model: DealDocument
Table: odp_deal_documents

Source files uploaded for each deal (pitch decks, FAQs, term sheets, etc.).
Each document is split into chunks stored in odp_deal_document_chunks.
"""

# Python Packages
from sqlalchemy import func

# Database
from ..config.database import db





class DealDocument(db.Model):
    """ A source document belonging to a deal... """

    # Table Name
    __tablename__ = "odp_deal_documents"

    doc_id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    deal_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_deals.deal_id", ondelete = "CASCADE"),
        nullable = False,
        index = True
    )

    doc_name = db.Column(db.String(255), nullable = False)

    doc_type = db.Column(
        db.String(50),
        nullable = False,
        doc = "One of: deck / faq / email / term_sheet"
    )

    storage_path = db.Column(
        db.String(500),
        nullable = False,
        doc = "S3 key or Drive path where the raw file is stored."
    )

    version = db.Column(db.String(50), nullable = True)

    uploaded_at = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        server_default = func.now()
    )

    def __repr__(self):
        return f"<DealDocument {self.doc_name}>"
