"""
Bot Controller
Handles orchestration between handler and service layer for bot functionality
"""

# Python Packages
from typing import Optional

# Services
from .services.query_service import QueryService
from .services.conversation_service import ConversationService


class BotController:
    """
    Controller for bot operations
    """
    
    def __init__(self):
        self.query_service = QueryService()
        self.conversation_service = ConversationService()
    
    
    def ask_question(
        self,
        question: str,
        deal_id: Optional[int] = None,
        session_id: Optional[str] = None,
        top_k: int = 5
    ) -> dict:
        """
        Ask a question (with optional deal_id and session_id)
        
        Args:
            question: User's question
            deal_id: Optional deal ID (None = search all deals)
            session_id: Optional session ID for conversation history
            top_k: Number of relevant chunks to retrieve
        
        Returns:
            dict: Answer with sources, session_id, and metadata
        """
        
        result = self.query_service.answer_question(
            question=question,
            deal_id=deal_id,
            session_id=session_id,
            top_k=top_k
        )
        
        return result
    
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> dict:
        """
        Get conversation history
        
        Args:
            session_id: Session ID
            limit: Number of messages
        
        Returns:
            dict: Conversation history
        """
        
        history = self.conversation_service.get_conversation_history(
            session_id=session_id,
            limit=limit
        )
        
        return {
            "session_id": session_id,
            "messages": history,
            "total": len(history)
        }
    
    
    def clear_conversation(self, session_id: str) -> bool:
        """
        Clear a conversation
        
        Args:
            session_id: Session ID
        
        Returns:
            bool: True if cleared
        """
        
        return self.conversation_service.clear_conversation(session_id)