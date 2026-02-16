"""
Conversation Service
Manages conversation history and context
"""

# Python Packages
from typing import List, Dict, Optional
import uuid

# Database
from odp.config.database import db

# Models
from ...models.odp_conversation import Conversation
from ...models.odp_conversation_message import ConversationMessage





class ConversationService:
    """
    Service for managing conversation sessions and history
    """

    def get_or_create_conversation(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Conversation:
        """
        Get existing conversation or create new one
        
        Args:
            session_id: Optional session ID (will generate if not provided)
            user_id: Optional user ID
        
        Returns:
            Conversation object
        """

        if session_id:
            # Try to find existing conversation
            conversation = Conversation.query.filter_by(
                session_id = session_id
            ).first()

            if conversation:
                return conversation
        
        # Create new conversation
        if not session_id:
            session_id = str(uuid.uuid4())

        conversation = Conversation(
            session_id = session_id,
            user_id = user_id
        )

        db.session.add(conversation)
        db.session.commit()

        print(f"✅ Created new conversation: {session_id}")
        return conversation

    

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        deal_id: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> ConversationMessage:
        """
        Add a message to the conversation
        
        Args:
            conversation_id: Conversation ID
            role: 'user' or 'assistant'
            content: Message content
            deal_id: Optional deal ID
            metadata: Optional metadata (sources, confidence, etc.)
        
        Returns:
            ConversationMessage object
        """
        
        message = ConversationMessage(
            conversation_id = conversation_id,
            role = role,
            content = content,
            deal_id = deal_id,
            message_metadata = metadata
        )

        db.session.add(message)
        db.session.commit()
        
        return message



    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get recent conversation history
        
        Args:
            session_id: Session ID
            limit: Number of recent messages to retrieve
        
        Returns:
            List of message dictionaries
        """
        
        conversation = Conversation.query.filter_by(
            session_id = session_id
        ).first()
        
        if not conversation:
            return []
        
        messages = ConversationMessage.query.filter_by(
            conversation_id = conversation.conversation_id
        ).order_by(
            ConversationMessage.created_at.desc()
        ).limit(limit).all()
        
        # Reverse to get chronological order
        messages = list(reversed(messages))
        
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "deal_id": msg.deal_id,
                "metadata": msg.message_metadata,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    


    def build_context_from_history(
        self,
        session_id: str,
        current_question: str,
        max_messages: int = 5
    ) -> str:
        """
        Build context string from conversation history
        
        Args:
            session_id: Session ID
            current_question: Current question being asked
            max_messages: Maximum number of previous messages to include
        
        Returns:
            Context string for LLM
        """
        
        history = self.get_conversation_history(
            session_id = session_id,
            limit = max_messages
        )
        
        if not history:
            return current_question
        
        # Build context
        context_parts = ["Previous conversation:"]
        
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role_label}: {msg['content']}")
        
        context_parts.append(f"\nCurrent question: {current_question}")
        
        return "\n".join(context_parts)
    


    def clear_conversation(self, session_id: str) -> bool:
        """
        Clear/delete a conversation
        
        Args:
            session_id: Session ID
        
        Returns:
            True if deleted, False if not found
        """
        
        conversation = Conversation.query.filter_by(
            session_id=session_id
        ).first()
        
        if not conversation:
            return False
        
        # First delete all messages (due to foreign key constraint)
        ConversationMessage.query.filter_by(
            conversation_id=conversation.conversation_id
        ).delete()
        
        # Then delete the conversation
        db.session.delete(conversation)
        db.session.commit()
        
        print(f"✅ Cleared conversation: {session_id}")
        return True
