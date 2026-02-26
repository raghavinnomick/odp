"""
Model: Deal
Table: odp_deals

Represents an investment deal managed by ODP.
Active deals (status=True) are searchable by the bot.
"""

# Python Packages
from sqlalchemy import func

# Database
from ..config.database import db





class Deal(db.Model):
    """ An ODP investment deal... """

    # Table Name
    __tablename__ = "odp_deals"

    deal_id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    deal_name = db.Column(
        db.String(255),
        nullable = False,
        doc = "Human-readable name, e.g. 'SpaceX Series C'."
    )

    deal_code = db.Column(
        db.String(255),
        nullable = False,
        unique = True,
        index = True,
        doc = "Short slug used in text detection, e.g. 'spacex-c'."
    )

    status = db.Column(
        db.Boolean,
        nullable = False,
        default = True,
        doc = "True = active (visible to bot). False = archived."
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
        return f"<Deal {self.deal_code}>"
