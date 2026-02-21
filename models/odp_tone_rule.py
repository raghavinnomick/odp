"""
Model: ToneRule
Table: odp_tone_rules

Stores tone, compliance, and do-not-say rules that are injected into
every LLM system prompt. Rules are loaded dynamically from the DB so
the team can update them without touching code.

Scope:
  global — applies to all deals
  deal   — applies only to a specific deal_id

Rule types: tone | compliance | do-not-say | disclaimer
"""

# Python Packages
from sqlalchemy import func

# Database
from ..config.database import db


class ToneRule(db.Model):
    """A tone or compliance rule injected into the LLM system prompt."""

    __tablename__ = "odp_tone_rules"

    rule_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    scope = db.Column(
        db.String(20),
        nullable=False,
        doc="'global' or 'deal'."
    )

    deal_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_deals.deal_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Set when scope='deal'. Null for global rules."
    )

    rule_type = db.Column(
        db.String(50),
        nullable=False,
        doc="One of: tone | compliance | do-not-say | disclaimer"
    )

    rule_text = db.Column(db.Text, nullable=False)

    priority = db.Column(
        db.Integer,
        nullable=False,
        default=1,
        doc="Higher value = injected first into the prompt."
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self):
        return f"<ToneRule {self.rule_type} scope={self.scope}>"
