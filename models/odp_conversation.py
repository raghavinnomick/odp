"""
Conversation Model
Stores chat history for context-aware conversations
"""

# Python Packages
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import TEXT, JSON

# Database
from ..config.database import db





class Conversation(db.Model):
    """ Conversation session model... """

    # Table Name
    __tablename__ = "odp_conversations"

    # Columns
    conversation_id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    session_id = db.Column(
        db.String(255),
        nullable = False,
        index = True,
        unique = True
    )

    user_id = db.Column(db.String(255), nullable = True)  # Optional: track user

    context_data = db.Column(JSON, nullable = True)  # Store any context
    
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
        return f"<Conversation {self.session_id}>"
