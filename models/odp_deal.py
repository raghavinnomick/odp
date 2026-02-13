""" Deal model"""

# Python Packages
from sqlalchemy import func

# Database
from ..config.database import db





class Deal(db.Model):
    # Table Name
    __tablename__ = "odp_deals"

    # Columns
    deal_id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    deal_name = db.Column(db.String(255), nullable = False)

    deal_code = db.Column(
        db.String(255),
        nullable = False,
        unique = True,
        index = True
    )

    status = db.Column(
        db.Boolean,
        nullable = False,
        default = True
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
