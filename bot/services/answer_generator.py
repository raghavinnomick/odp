"""
Answer Generator Service
Generates answers using LLM with provided context
"""

# Python Packages
from typing import List, Dict

# Vendors
from ...vendors.openai import ChatService





class AnswerGenerator:
    """
    Service for generating answers using LLM
    """
    
    def __init__(self):
        self.chat_service = ChatService()
    
    
    def generate_answer(self, question: str, context: str, conversation_history: str = None) -> str:
        """
        Generate answer using OpenAI chat completion
        
        Args:
            question: User's question (may include conversation history)
            context: Context built from relevant chunks
            conversation_history: Optional conversation history string
        
        Returns:
            Generated answer from LLM
        """
        
        print(f"🤖 Generating answer using LLM...")
        
        system_prompt = self._get_system_prompt()
        user_prompt = self._format_user_prompt(question, context, conversation_history)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        answer = self.chat_service.generate_response(
            messages=messages,
            temperature=0.3,  # Lower temperature for factual answers
            max_tokens=500
        )
        
        return answer
    
    
    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for the LLM
        
        Returns:
            System prompt string
        """
        
        return """You are a helpful assistant that answers questions about investment deals based on provided documents.

IMPORTANT INSTRUCTIONS:
- Use information from the provided context AND conversation history
- If the current question refers to something mentioned earlier (like "it", "that company", "their revenue"), use the conversation history to understand what they're referring to
- Only use information from the provided context
- If the answer is not in the context, say "I don't have enough information in the documents to answer this question."
- Be concise and specific
- Cite sources when possible (e.g., "According to the investor deck...")
- If there are numbers, dates, or specific terms, quote them exactly from the context
- Do not make up information or use external knowledge
- Format your answer in clear paragraphs"""
    
    
    def _format_user_prompt(self, question: str, context: str, conversation_history: str = None) -> str:
        """
        Format the user prompt with question, context, and history
        
        Args:
            question: User's question
            context: Retrieved context
            conversation_history: Optional conversation history
        
        Returns:
            Formatted prompt string
        """
        
        prompt_parts = []
        
        # Add conversation history if available
        if conversation_history and conversation_history != question:
            prompt_parts.append("Conversation History:")
            prompt_parts.append(conversation_history)
            prompt_parts.append("")
        
        # Add document context
        prompt_parts.append("Context from documents:")
        prompt_parts.append(context)
        prompt_parts.append("")
        prompt_parts.append("---")
        prompt_parts.append("")
        
        # Add current question
        if conversation_history and conversation_history != question:
            # Extract just the current question from history
            current_q = question.split("Current question:")[-1].strip() if "Current question:" in question else question
            prompt_parts.append(f"Current Question: {current_q}")
        else:
            prompt_parts.append(f"Question: {question}")
        
        prompt_parts.append("")
        prompt_parts.append("Answer:")
        
        return "\n".join(prompt_parts)