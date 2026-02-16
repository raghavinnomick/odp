"""
Clarification Service
Handles ambiguous or unclear questions
"""

# Python Packages
from typing import Optional, Dict, List

# Vendors
from ...vendors.openai import ChatService


class ClarificationService:
    """
    Service for detecting unclear queries and asking clarifying questions
    """
    
    def __init__(self):
        self.chat_service = ChatService()
    
    def needs_clarification(
        self,
        question: str,
        chunks_found: int,
        confidence: str
    ) -> bool:
        """
        Determine if we need to ask for clarification
        
        Args:
            question: User's question
            chunks_found: Number of relevant chunks found
            confidence: Confidence level from search
        
        Returns:
            True if clarification needed
        """
        
        # ONLY need clarification if:
        # 1. NO chunks found at all
        # 2. Very low confidence AND very short question
        
        # If we found chunks, we should try to answer
        if chunks_found > 0:
            # Even with medium/low confidence, if we have chunks, try to answer
            return False
        
        # No chunks found - need clarification
        return True
    
    def generate_clarifying_question(
        self,
        question: str,
        available_documents: List[str]
    ) -> str:
        """
        Generate a clarifying question for the user
        
        Args:
            question: Original unclear question
            available_documents: List of document names in the deal
        
        Returns:
            Clarifying question to ask the user
        """
        
        system_prompt = """You are a helpful assistant that asks clarifying questions when user queries are ambiguous.

Your job is to:
1. Identify what information is missing or unclear
2. Ask a specific, helpful clarifying question
3. Mention available documents if relevant
4. Be concise and friendly

DO NOT:
- Try to answer the question
- Make assumptions
- Be overly verbose"""

        user_prompt = f"""The user asked: "{question}"

Available documents:
{', '.join(available_documents)}

I couldn't find relevant information in the documents.

Generate ONE specific clarifying question to help the user get better results."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        clarification = self.chat_service.generate_response(
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        
        return clarification.strip()