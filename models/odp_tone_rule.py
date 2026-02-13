""" Tone Rules Model: Stores founder tone + compliance rules... """

# Python Packages
from sqlalchemy import func

# Database
from ..config.database import db





class ToneRule(db.Model):
    # Table Name    
    __tablename__ = "odp_tone_rules"

    # Columns
    rule_id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    scope = db.Column(
        db.String(20),
        nullable = False
    )  # global / deal

    deal_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_deals.deal_id", ondelete = "CASCADE"),
        nullable = True,
        index = True
    )

    rule_type = db.Column(
        db.String(50),
        nullable = False
    )  # tone / compliance / do-not-say / disclaimer

    rule_text = db.Column(
        db.Text,
        nullable = False
    )

    priority = db.Column(
        db.Integer,
        nullable = False,
        default = 1
    )

    is_active = db.Column(
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
        return f"<ToneRule {self.rule_type} ({self.scope})>"
