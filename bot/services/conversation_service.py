"""
Service: ConversationService

Creates, reads, and manages conversation sessions and their messages.

Data tables:
  odp_conversations         → one row per session_id
  odp_conversation_messages → one row per message turn

Design:
  - get_or_create_conversation() is idempotent: safe to call on every request.
  - All DB writes include rollback on failure so a failed write never
    poisons the SQLAlchemy session for the caller's subsequent queries.
  - History is returned in chronological order (oldest first) so the LLM
    receives context in the correct reading order.
"""

# Python Packages
from typing import List, Dict, Optional
import uuid

# Database
from ...config.database import db

# Models
from ...models.odp_conversation import Conversation
from ...models.odp_conversation_message import ConversationMessage

# Constants
from ...base import constants


class ConversationService:
    """
    Manages conversation sessions and message persistence.
    All methods are transaction-safe (rollback on failure).
    """

    # ── Session Management ─────────────────────────────────────────────────────

    def get_or_create_conversation(
        self,
        session_id: Optional[str] = None,
        user_id: str = None
    ) -> Conversation:
        """
        Return an existing conversation or create a new one.

        If *session_id* is provided and a matching conversation exists,
        return it. Otherwise create a new session.

        Args:
            session_id: Client-supplied UUID, or None to generate a new one.
            user_id:    Team member identifier.

        Returns:
            Conversation ORM object.

        Raises:
            Exception: Propagated if the DB commit fails (caller handles).
        """
        if session_id:
            conversation = Conversation.query.filter_by(session_id=session_id).first()
            if conversation:
                return conversation

        if not session_id:
            session_id = str(uuid.uuid4())

        conversation = Conversation(session_id=session_id, user_id=user_id)
        db.session.add(conversation)
        db.session.commit()

        print(f"✅ New conversation created: {session_id}")
        return conversation

    # ── Message Persistence ────────────────────────────────────────────────────

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        deal_id: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[ConversationMessage]:
        """
        Append a message to a conversation.

        Args:
            conversation_id: PK of the parent Conversation.
            role:            "user" or "assistant".
            content:         Message text.
            deal_id:         Active deal at message time (optional).
            metadata:        Response-type flags, sources, confidence, etc.

        Returns:
            Saved ConversationMessage, or None on DB error.
        """
        try:
            message = ConversationMessage(
                conversation_id  = conversation_id,
                role             = role,
                content          = content,
                deal_id          = deal_id,
                message_metadata = metadata
            )
            db.session.add(message)
            db.session.commit()
            return message

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  add_message failed (conversation_id={conversation_id}): {exc}")
            return None

    # ── History Retrieval ──────────────────────────────────────────────────────

    def get_conversation_history(
        self,
        session_id: str,
        limit: int = constants.BOT_LAST_CONVERSATION_MESSAGES_LIMIT
    ) -> List[Dict]:
        """
        Return the *limit* most recent messages in chronological order.

        Args:
            session_id: The session UUID.
            limit:      Max messages to return (default from constants).

        Returns:
            List of message dicts, oldest first:
            [{"role", "content", "deal_id", "metadata", "created_at"}, ...]
            Empty list if the session does not exist or on DB error.
        """
        try:
            conversation = Conversation.query.filter_by(session_id=session_id).first()
            if not conversation:
                return []

            messages = (
                ConversationMessage.query
                .filter_by(conversation_id=conversation.conversation_id)
                .order_by(ConversationMessage.created_at.desc())
                .limit(limit)
                .all()
            )

            # Reverse so the LLM receives oldest → newest
            return [
                {
                    "role":       msg.role,
                    "content":    msg.content,
                    "deal_id":    msg.deal_id,
                    "metadata":   msg.message_metadata,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in reversed(messages)
            ]

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  get_conversation_history failed (session={session_id}): {exc}")
            return []

    def get_last_assistant_message(self, session_id: str) -> Optional[Dict]:
        """
        Return the most recent assistant message for a session.

        Returns:
            Message dict or None if no assistant messages exist.
        """
        try:
            conversation = Conversation.query.filter_by(session_id=session_id).first()
            if not conversation:
                return None

            msg = (
                ConversationMessage.query
                .filter_by(
                    conversation_id=conversation.conversation_id,
                    role="assistant"
                )
                .order_by(ConversationMessage.created_at.desc())
                .first()
            )

            if not msg:
                return None

            return {
                "role":     msg.role,
                "content":  msg.content,
                "deal_id":  msg.deal_id,
                "metadata": msg.message_metadata
            }

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  get_last_assistant_message failed (session={session_id}): {exc}")
            return None

    # ── Conversation Lifecycle ─────────────────────────────────────────────────

    def clear_conversation(self, session_id: str) -> bool:
        """
        Delete a conversation and all its messages.

        Args:
            session_id: The session UUID to clear.

        Returns:
            True if deleted, False if not found or on error.
        """
        try:
            conversation = Conversation.query.filter_by(session_id=session_id).first()
            if not conversation:
                return False

            ConversationMessage.query.filter_by(
                conversation_id=conversation.conversation_id
            ).delete()
            db.session.delete(conversation)
            db.session.commit()

            print(f"✅ Cleared conversation: {session_id}")
            return True

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  clear_conversation failed (session={session_id}): {exc}")
            return False
