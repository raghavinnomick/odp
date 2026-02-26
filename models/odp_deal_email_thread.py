"""
Model: DealEmailThread
======================
ORM representation of the odp_deal_email_threads table.

PLACEMENT: Drop this file into your models/ directory at the same level
as odp_conversation.py, odp_deal.py, etc.

Purpose:
  Stores email threads pasted by team members (or injected by the Gmail
  Extension in future) before starting a bot conversation. Gives the bot
  investor context — tone, style, open questions, what is already answered.

Thread is OPTIONAL per session. Bot works with zero rows in this table.

source values:
  'manual_paste'    — team member pasted thread text manually (v1)
  'gmail_extension' — Gmail Extension auto-injected thread (future)

parse_status values:
  'pending'    — thread stored, parsing not yet started
  'completed'  — LLM parsed successfully, parsed_context populated
  'failed'     — LLM parsing failed, parse_error populated
"""

# Python Packages
from datetime import datetime

# Database
from ..config.database import db





class DealEmailThread(db.Model):
    """
    Represents one email thread attached to a bot session.
    At most one active thread per session at a time (enforced by DB unique index).
    """

    # Table Name
    __tablename__ = "odp_deal_email_threads"

    # ── Primary key
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    # ── Session link
    session_id = db.Column(db.String(255), nullable = False, index = True)

    # ── Deal scope (nullable — detected from thread, may not be known yet)
    deal_id = db.Column(db.Integer, nullable = True)

    # ── Raw thread text (exactly what was pasted / injected)
    raw_thread_text = db.Column(db.Text, nullable = False)

    # ── LLM-parsed fields (populated after successful parse)
    parsed_investor_name  = db.Column(db.String(255), nullable = True)
    parsed_investor_email = db.Column(db.String(255), nullable = True)
    parsed_latest_question = db.Column(db.Text,       nullable = True)
    parsed_summary         = db.Column(db.Text,       nullable = True)

    # Full structured extract:
    # {
    #   "investor_name", "investor_email", "investor_tone",
    #   "deal_signals", "latest_question", "already_discussed",
    #   "open_items", "thread_summary", "email_count", "participants"
    # }
    parsed_context = db.Column(db.JSON, nullable = True)

    # ── Source
    source = db.Column(db.String(50), nullable = False, default = "manual_paste")

    # ── State
    is_active    = db.Column(db.Boolean, nullable = False, default = True)
    parse_status = db.Column(db.String(50), nullable = False, default = "pending")
    parse_error  = db.Column(db.Text, nullable = True)

    # ── Audit
    created_by = db.Column(db.String(255), nullable = False)
    created_at = db.Column(db.DateTime, nullable = False, default = datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable = False,
                           default = datetime.utcnow, onupdate = datetime.utcnow)

    def __repr__(self):
        return (
            f"<DealEmailThread id={self.id} session={self.session_id} "
            f"deal={self.deal_id} status={self.parse_status} source={self.source}>"
        )


    def to_dict(self) -> dict:
        """Serialise to dict for API responses."""
        return {
            "id":                    self.id,
            "session_id":            self.session_id,
            "deal_id":               self.deal_id,
            "source":                self.source,
            "is_active":             self.is_active,
            "parse_status":          self.parse_status,
            "parsed_investor_name":  self.parsed_investor_name,
            "parsed_investor_email": self.parsed_investor_email,
            "parsed_latest_question":self.parsed_latest_question,
            "parsed_summary":        self.parsed_summary,
            "parsed_context":        self.parsed_context,
            "created_by":            self.created_by,
            "created_at":            self.created_at.isoformat() if self.created_at else None,
            "updated_at":            self.updated_at.isoformat() if self.updated_at else None,
        }
