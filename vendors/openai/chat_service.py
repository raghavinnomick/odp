"""OpenAI Chat/Completion Service"""
from typing import List, Dict, Optional
from .openai_client import OpenAIClient

class ChatService:
    """Service for chat completions using OpenAI"""
    
    def __init__(self, api_key: str = None):
        """Initialize chat service"""
        self.client = OpenAIClient(api_key).get_client()
        self.default_model = "gpt-4o-mini"  # or "gpt-4o" for better quality
    
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Generate a chat completion response
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: OpenAI model to use
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated response text
        """
        try:
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ Error generating response: {e}")
            raise
    
    def generate_answer_from_context(
        self,
        question: str,
        context: str,
        model: str = None
    ) -> str:
        """
        Generate answer based on provided context
        
        Args:
            question: User's question
            context: Relevant context from documents
            model: OpenAI model to use
            
        Returns:
            Generated answer
        """
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that answers questions based on provided documents. Only use information from the context provided. If the answer is not in the context, say so."
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
            }
        ]
        
        return self.generate_response(messages, model=model)