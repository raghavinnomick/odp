"""
Query Enhancement Service
Enhances user queries using conversation history
"""

# Python Packages
from typing import Optional, List, Dict

# Vendors
from ...vendors.openai import ChatService


class QueryEnhancementService:
    """
    Service for enhancing queries with conversation context
    """
    
    def __init__(self):
        self.chat_service = ChatService()
    
    
    def enhance_query(
        self,
        current_question: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        Enhance query using conversation history
        
        Args:
            current_question: Current user question
            conversation_history: List of previous messages
        
        Returns:
            Enhanced query string
        """
        
        # If no history or question is already detailed, return as-is
        if not conversation_history or len(current_question.split()) > 5:
            return current_question
        
        # Build conversation context
        history_text = self._build_history_text(conversation_history)
        
        # Use LLM to expand the query
        system_prompt = """You are a helpful assistant that reformulates vague follow-up questions into clear, standalone questions using conversation history.

IMPORTANT:
- If the current question references previous context (like "it", "that", "the revenue", "what about"), rewrite it to be standalone
- Include the specific entity/company being discussed
- Keep it concise (one sentence)
- If the question is already clear and specific, return it unchanged

Examples:
History: "What is the valuation of SpaceX?" / "SpaceX is valued at $720B"
Current: "What about the revenue?"
Enhanced: "What is the revenue of SpaceX?"

History: "Tell me about Anthropic" / "Anthropic is an AI company..."
Current: "What's their valuation?"
Enhanced: "What is the valuation of Anthropic?"
"""

        user_prompt = f"""Conversation History:
{history_text}

Current Question: {current_question}

Enhanced Question (standalone and clear):"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        enhanced = self.chat_service.generate_response(
            messages=messages,
            temperature=0.3,
            max_tokens=100
        )
        
        enhanced_query = enhanced.strip().strip('"').strip("'")
        
        print(f"🔄 Enhanced query: '{current_question}' → '{enhanced_query}'")
        
        return enhanced_query
    
    
    def _build_history_text(self, history: List[Dict]) -> str:
        """Build formatted history text"""
        
        lines = []
        for msg in history[-4:]:  # Last 2 exchanges
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        
        return "\n".join(lines)