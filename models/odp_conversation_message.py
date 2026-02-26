"""
Model: ConversationMessage
Table: odp_conversation_messages

An individual message in a conversation session.
Role is either 'user' (team member) or 'assistant' (bot).

The message_metadata JSON column stores response-type flags:
  {"type": "answer" | "needs_info" | "needs_clarification" | "draft_email" | "greeting",
   "investor_question": "...",   # present when type=needs_info
   "sources": [...],
   "confidence": "high" | "medium" | "low"}
"""

# Python Packages
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import TEXT, JSON

# Database
from ..config.database import db





class ConversationMessage(db.Model):
    """ One message (user or assistant turn) in a conversation... """

    # Table Name
    __tablename__ = "odp_conversation_messages"

    message_id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_conversations.conversation_id", ondelete = "CASCADE"),
        nullable = False,
        index = True
    )

    role = db.Column(
        db.String(50),
        nullable = False,
        doc = "'user' or 'assistant'."
    )

    content = db.Column(TEXT, nullable = False)

    deal_id = db.Column(
        db.Integer,
        nullable = True,
        doc = "Deal being discussed at the time of this message."
    )

    message_metadata = db.Column(
        JSON,
        nullable = True,
        doc = "Response type flags and source references. See module docstring."
    )

    created_at = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        server_default = func.now()
    )

    # Relationship
    conversation = db.relationship("Conversation", backref = "messages")

    def __repr__(self):
        return f"<ConversationMessage {self.message_id} role={self.role}>"
