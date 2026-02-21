"""
Model: Conversation
Table: odp_conversations

Represents a chat session. Each session is identified by a UUID session_id
and belongs to a user. Messages are stored in odp_conversation_messages.
"""

# Python Packages
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSON

# Database
from ..config.database import db


class Conversation(db.Model):
    """A chat session between a user and the ODP bot."""

    __tablename__ = "odp_conversations"

    conversation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    session_id = db.Column(
        db.String(255),
        nullable=False,
        index=True,
        unique=True,
        doc="UUID-based identifier passed by the client."
    )

    user_id = db.Column(
        db.String(255),
        nullable=True,
        doc="Identifier of the team member who owns this session."
    )

    context_data = db.Column(
        JSON,
        nullable=True,
        doc="Arbitrary JSON for storing session-level context (reserved for future use)."
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
        return f"<Conversation {self.session_id}>"
