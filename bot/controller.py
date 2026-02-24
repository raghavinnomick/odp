"""
Bot Controller
Orchestrates between handler and service layer.
"""

# Python Packages
from typing import Optional

# Services
from .services.query_service import QueryService
from .services.conversation_service import ConversationService

# Config
from .config import bot_config





class BotController:

    def __init__(self):
        """ Initialize services... """

        self.query_service        = QueryService()
        self.conversation_service = ConversationService()



    def ask_question(
        self,
        question: str,
        user_id: str,
        deal_id: Optional[int] = None,
        session_id: Optional[str] = None,
        top_k: int = bot_config.BOT_DEFAULT_TOP_K
    ) -> dict:
        """
        Ask a question to the bot and get an answer.

        Args:
            question: The user's question as a string.
            user_id: The identifier of the user asking the question.
            deal_id: Optional deal ID to scope the question to a specific deal.
            session_id: Optional session ID to maintain conversation context.
            top_k: Number of top results to retrieve (default from constants).

        Returns:
            Dict containing the bot's response with answer and metadata.
        """

        return self.query_service.answer_question(
            question   = question,
            user_id    = user_id,
            deal_id    = deal_id,
            session_id = session_id,
            top_k      = top_k
        )



    def generate_draft(self, session_id: str, user_id: str) -> dict:
        """
        Generate a draft email reply from the conversation history.

        Args:
            session_id: The unique session identifier for the conversation.
            user_id: The identifier of the user owning the session.

        Returns:
            Dict containing the generated draft email and related metadata.
        """

        return self.query_service.generate_draft_from_session(
            session_id = session_id,
            user_id    = user_id
        )



    def get_conversation_history(self, session_id: str, limit: int = 10) -> dict:
        """
        Retrieve the conversation history for a specific session.

        Args:
            session_id: The unique session identifier.
            limit: Maximum number of messages to retrieve (default: 10).

        Returns:
            Dict containing session_id, messages list, and total message count.
        """

        history = self.conversation_service.get_conversation_history(
            session_id = session_id, limit = limit
        )
        return {"session_id": session_id, "messages": history, "total": len(history)}



    def clear_conversation(self, session_id: str) -> bool:
        """
        Delete a conversation session and all its associated messages.

        Args:
            session_id: The unique session identifier to clear.

        Returns:
            Boolean indicating success (True) or failure (False).
        """

        return self.conversation_service.clear_conversation(session_id)



    def get_user_sessions(self, user_id: str) -> dict:
        """
        Retrieve all conversations for a given user_id.

        Args:
            user_id: The user identifier.

        Returns:
            Dict with user_id, sessions list, and total count.
        """

        sessions = self.conversation_service.get_sessions_by_user_id(user_id)

        return {
            "user_id": user_id,
            "sessions": sessions,
            "total": len(sessions)
        }
