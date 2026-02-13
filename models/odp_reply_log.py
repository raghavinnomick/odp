""" Reply Logs Model: Stores AI draft + final response audit trail... """

# Python Packages
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB

# Database
from ..config.database import db





class ReplyLog(db.Model):
    # Table Name 
    __tablename__ = "odp_reply_logs"

    # Columns
    log_id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    deal_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_deals.deal_id", ondelete = "CASCADE"),
        nullable = False,
        index = True
    )

    question_text = db.Column(
        db.Text,
        nullable = False
    )

    kb_sources_used = db.Column(
        JSONB,
        nullable = True
    )  # store term fields + faq_ids + dynamic_fact_ids

    draft_reply = db.Column(
        db.Text,
        nullable = True
    )

    confidence = db.Column(
        db.Float,
        nullable = True
    )

    session_id = db.Column(
        db.String(100),
        nullable = True,
        index = True
    )

    user_channel = db.Column(
        db.String(50),
        nullable = True
    )  # web / postman / slack / gmail_addon

    error_flag = db.Column(
        db.Boolean,
        nullable = False,
        default = False
    )

    error_message = db.Column(
        db.Text,
        nullable = True
    )

    created_at = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        server_default = func.now()
    )



    def __repr__(self):
        return f"<ReplyLog {self.log_id}>"
