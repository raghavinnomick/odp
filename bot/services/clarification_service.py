"""
Clarification Service
Handles ambiguous or unclear questions.

Core rule:
    Deal-specific questions (structure, fees, minimum, payment, etc.) REQUIRE
    a known deal context before answering. Without it, ask which deal first.
    This prevents hallucination — the LLM must never invent deal-specific numbers.
"""

# Python Packages
from typing import Optional, Dict, List

# Vendors
from ...vendors.openai import ChatService

# Config
from ..config import prompts, service_constants





class ClarificationService:
    """
    Service for detecting when we must ask "which deal?" before answering.
    All deal names come from the database — nothing is hardcoded.
    """

    def __init__(self):
        self.chat_service = ChatService()


    def needs_clarification(
        self,
        question: str,
        chunks_found: int,
        confidence: str,
        has_deal_context: bool = False
    ) -> bool:
        """
        Determine if we need to ask "which deal?" before answering.

        Decision logic:
            1. Deal context is known → never clarify (we know which deal, proceed)
            2. No deal context + general/greeting question → answer (no deal needed)
            3. No deal context + deal-specific question → MUST clarify (ask which deal)
            4. No deal context + truly vague → clarify

        The key insight: deal-specific questions (fees, structure, minimum ticket,
        payment dates, etc.) CANNOT be answered correctly without knowing which deal.
        Attempting to answer them without deal context causes hallucination.

        Args:
            question: User's question
            chunks_found: Number of relevant RAG chunks found
            confidence: Confidence string from context builder
            has_deal_context: True if an active deal_id is known

        Returns:
            True if we should ask for clarification before answering
        """

        # Rule 1: Deal context is established — proceed to answer
        # (chunks or DB facts will have the right deal-specific info)
        if has_deal_context:
            return False

        question_lower = question.lower().strip()

        # Rule 2: General / greeting questions don't need a deal — answer them
        for pattern in service_constants.GENERAL_KEYWORDS:
            if pattern in question_lower:
                return False

        # Rule 3: Deal-specific question WITHOUT a known deal → MUST clarify
        # This is the key fix: we cannot answer "what is the minimum ticket?"
        # or "tell me about the structure" without knowing which deal.
        # Attempting to do so causes the LLM to hallucinate specific numbers.
        for keyword in service_constants.DEAL_SPECIFIC_KEYWORDS:
            if keyword in question_lower:
                print(f"⚠️  Deal-specific question with no deal context — must clarify")
                return True

        # Rule 4: Vague question with no deal context → clarify
        return True



    def generate_clarifying_question(
        self,
        question: str,
        available_documents: List[str],
        available_deals: List[str] = None
    ) -> str:
        """
        Generate a short, warm clarifying question.
        Deal names are passed in from the DB — nothing is hardcoded.

        Args:
            question: Original question from the user
            available_documents: Document names in the system
            available_deals: Deal names loaded from odp_deals table

        Returns:
            Clarifying question string
        """

        if available_deals and len(available_deals) > 0:
            deals_text = " or ".join(available_deals)
            deal_prompt = f"Are you asking about {deals_text}?"
        else:
            deal_prompt = "Could you let me know which deal you're asking about?"

        # Fast path: if it's clearly a "which deal" situation, return directly
        # without an LLM call (cheaper and more consistent)
        question_lower = question.lower()
        for keyword in service_constants.DEAL_SPECIFIC_KEYWORDS:
            if keyword in question_lower:
                return f"Happy to help! {deal_prompt}"

        # For genuinely vague questions, use LLM to generate a better response
        if available_deals:
            deals_text = " and ".join(available_deals)
        else:
            deals_text = "our current investment opportunities"

        system_prompt = prompts.CLARIFICATION_SYSTEM_TEMPLATE.format(deals_text=deals_text)
        user_prompt = prompts.CLARIFICATION_USER_PROMPT.format(question=question)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        clarification = self.chat_service.generate_response(
            messages=messages,
            temperature=service_constants.LLM_CLARIFICATION_TEMPERATURE,
            max_tokens=service_constants.LLM_CLARIFICATION_MAX_TOKENS
        )

        return clarification.strip()
