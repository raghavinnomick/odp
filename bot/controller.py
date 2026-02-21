"""
Bot Controller
Orchestrates between handler and service layer.
"""

# Python Packages
from typing import Optional

# Services
from .services.query_service import QueryService
from .services.conversation_service import ConversationService

# Constants
from ..base import constants





class BotController:

    def __init__(self):
        """Initialize services."""

        self.query_service        = QueryService()
        self.conversation_service = ConversationService()



    def ask_question(
        self,
        question: str,
        user_id: str,
        deal_id: Optional[int] = None,
        session_id: Optional[str] = None,
        top_k: int = constants.BOT_DEFAULT_TOP_K
    ) -> dict:

        return self.query_service.answer_question(
            question   = question,
            user_id    = user_id,
            deal_id    = deal_id,
            session_id = session_id,
            top_k      = top_k
        )



    def generate_draft(self, session_id: str, user_id: str) -> dict:

        return self.query_service.generate_draft_from_session(
            session_id = session_id,
            user_id    = user_id
        )



    def get_conversation_history(self, session_id: str, limit: int = 10) -> dict:

        history = self.conversation_service.get_conversation_history(
            session_id=session_id, limit=limit
        )
        return {"session_id": session_id, "messages": history, "total": len(history)}



    def clear_conversation(self, session_id: str) -> bool:

        return self.conversation_service.clear_conversation(session_id)
