""" Deal Dynamic Facts Model: Stores continuously updated deal facts... """

# Python Packages
from sqlalchemy import func

# Database
from ..config.database import db





class DealDynamicFact(db.Model):
    # Table Name 
    __tablename__ = "odp_deal_dynamic_facts"

    # Columns
    fact_id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    deal_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_deals.deal_id", ondelete = "CASCADE"),
        nullable = False,
        index = True
    )

    fact_key = db.Column(
        db.String(100),
        nullable = False,
        index = True
    )  # e.g., current_share_price

    fact_value = db.Column(
        db.Text,
        nullable = False
    )

    as_of_date = db.Column(
        db.Date,
        nullable = True
    )

    source_note = db.Column(
        db.Text,
        nullable = True
    )

    approval_status = db.Column(
        db.String(20),
        nullable = False,
        default = "pending"
    )  # pending / approved

    approved_by = db.Column(
        db.String(100),
        nullable = True
    )

    approved_at = db.Column(
        db.DateTime(timezone = True),
        nullable = True
    )

    created_at = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        server_default = func.now()
    )

    updated_at = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        server_default = func.now(),
        onupdate = func.now()
    )



    def __repr__(self):
        return f"<DealDynamicFact {self.fact_key}>"
