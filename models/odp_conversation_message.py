"""
Conversation Message Model
Stores individual messages in a conversation
"""

# Python Packages
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import TEXT, JSON

# Database
from ..config.database import db





class ConversationMessage(db.Model):
    """ Individual messages in a conversation... """

    # Table Name
    __tablename__ = "odp_conversation_messages"

    # Columns
    message_id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("odp_conversations.conversation_id", ondelete = "CASCADE"),
        nullable = False,
        index = True
    )

    role = db.Column(
        db.String(50),
        nullable = False
    )  # 'user' or 'assistant'

    content = db.Column(TEXT, nullable = False)

    deal_id = db.Column(db.Integer, nullable = True)  # Which deal was discussed

    message_metadata = db.Column(JSON, nullable = True)  # CHANGED: metadata -> message_metadata

    created_at = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        server_default=func.now()
    )

    # Relationships
    conversation = db.relationship("Conversation", backref = "messages")

    def __repr__(self):
        return f"<ConversationMessage {self.message_id} - {self.role}>"
