""" Deal Documents Model: Stores source files for each deal... """

# Python Packages
from sqlalchemy import func

# Database
from ..config.database import db





class DealDocument(db.Model):
    # Table Name
    __tablename__ = "odp_deal_documents"

    # Columns
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
        nullable = False
    )  # deck / faq / email / term_sheet

    storage_path = db.Column(
        db.String(500),
        nullable = False
    )  # S3 path / Drive path

    version = db.Column(
        db.String(50),
        nullable = True
    )

    uploaded_at = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        server_default = func.now()
    )



    def __repr__(self):
        return f"<DealDocument {self.doc_name}>"
