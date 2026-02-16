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
        
        # If no history, return as-is
        if not conversation_history or len(conversation_history) < 2:
            return current_question
        
        # Check if question seems to need context (has pronouns, incomplete, vague)
        needs_enhancement = self._needs_enhancement(current_question)
        
        if not needs_enhancement:
            return current_question
        
        # Build conversation context
        history_text = self._build_history_text(conversation_history)
        
        # Use LLM to expand the query
        system_prompt = """You are a query rewriter that makes vague follow-up questions standalone and clear.

RULES:
1. If the question mentions "it", "that", "their", "the company", "this", or is incomplete → rewrite to include the specific entity from history
2. If asking about metrics without naming the company (like "revenue?", "valuation?") → add the company name from context
3. Keep the same intent and meaning
4. Return ONLY the rewritten question, nothing else
5. If question is already clear and complete, return it unchanged

Examples:
History: User asked "What is SpaceX valuation?" | Bot answered about SpaceX
Current: "What about revenue?"
Output: What is the revenue of SpaceX?

History: User asked "Tell me about Anthropic" | Bot answered about Anthropic  
Current: "What's their valuation?"
Output: What is the valuation of Anthropic?

History: User asked "SpaceX revenue?" | Bot answered about 2023 revenue
Current: "What is total revenue over 2025?"
Output: What is the total revenue of SpaceX over 2025?

History: User asked "Compare deals" | Bot gave comparison
Current: "Tell me more about the first one"
Output: Tell me more about SpaceX

IMPORTANT: Extract the company/entity being discussed from the MOST RECENT assistant message."""

        user_prompt = f"""Conversation History:
{history_text}

Current Question: {current_question}

Rewritten Question:"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        enhanced = self.chat_service.generate_response(
            messages=messages,
            temperature=0.1,  # Very low for consistent rewrites
            max_tokens=100
        )
        
        enhanced_query = enhanced.strip().strip('"').strip("'")
        
        # Only use enhanced version if it's different and makes sense
        if len(enhanced_query) > 0 and enhanced_query != current_question:
            print(f"🔄 Enhanced: '{current_question}' → '{enhanced_query}'")
            return enhanced_query
        
        return current_question
    
    
    def _needs_enhancement(self, question: str) -> bool:
        """
        Check if question needs enhancement based on vagueness indicators
        
        Args:
            question: User's question
            
        Returns:
            True if needs enhancement
        """
        
        question_lower = question.lower()
        
        # Vagueness indicators
        vague_words = [
            'it', 'that', 'this', 'these', 'those',
            'they', 'their', 'them',
            'the company', 'the deal', 'the investment',
            'same', 'also', 'too'
        ]
        
        # Check for vague words
        for word in vague_words:
            if word in question_lower:
                return True
        
        # Check if question is very short (< 4 words) and doesn't mention a company
        words = question.split()
        if len(words) < 4:
            # Common company names to check
            company_names = ['spacex', 'anthropic', 'tesla', 'openai', 'google', 'amazon']
            has_company = any(company in question_lower for company in company_names)
            if not has_company:
                return True
        
        # Check if it's just a metric without context
        metric_only_patterns = [
            'revenue', 'valuation', 'profit', 'growth', 'ebitda',
            'customers', 'users', 'employees'
        ]
        
        # If question is ONLY a metric (like "revenue?" or "what's the valuation?")
        if len(words) <= 5:
            for metric in metric_only_patterns:
                if metric in question_lower:
                    # Check if company name is mentioned
                    company_names = ['spacex', 'anthropic', 'tesla', 'openai']
                    has_company = any(company in question_lower for company in company_names)
                    if not has_company:
                        return True
        
        return False
    
    
    def _build_history_text(self, history: List[Dict]) -> str:
        """
        Build formatted history text focusing on recent context
        
        Args:
            history: Conversation history
            
        Returns:
            Formatted history string
        """
        
        lines = []
        
        # Use last 6 messages (3 exchanges) for context
        recent_history = history[-6:] if len(history) > 6 else history
        
        for msg in recent_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"]
            
            # Truncate very long assistant responses
            if role == "Assistant" and len(content) > 200:
                content = content[:200] + "..."
            
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)