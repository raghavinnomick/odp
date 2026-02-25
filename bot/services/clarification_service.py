"""
Service: ClarificationService
==============================
Handles ambiguous or unclear questions.

Core rule:
    Deal-specific questions (structure, fees, minimum, payment, etc.) REQUIRE
    a known deal_id before answering. Without it, ask "which deal?" first.
    This prevents hallucination — the LLM must never invent deal-specific numbers.
"""

# Python Packages
from typing import List

# Vendors
from ...vendors import ChatService

# Config
from ..config import prompts, llm_config, keywords


class ClarificationService:
    """
    Detects when we must ask "which deal?" before answering.
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
            1. Deal context is known → never clarify (proceed to answer)
            2. No deal context + general/greeting question → answer (no deal needed)
            3. No deal context + deal-specific question → MUST clarify
            4. No deal context + truly vague → clarify
        """
        # Rule 1: Deal context established — proceed
        if has_deal_context:
            return False

        question_lower = question.lower().strip()

        # Rule 2: General questions don't need a deal
        for pattern in keywords.GENERAL_KEYWORDS:
            if pattern in question_lower:
                return False

        # Rule 3: Deal-specific question WITHOUT known deal → must clarify
        for kw in keywords.DEAL_SPECIFIC_KEYWORDS:
            if kw in question_lower:
                print("⚠️  Deal-specific question with no deal context — must clarify")
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
        """
        if available_deals:
            deals_text = " or ".join(available_deals)
            deal_prompt = f"Are you asking about {deals_text}?"
        else:
            deal_prompt = "Could you let me know which deal you're asking about?"

        # Fast path: deal-specific keyword → return directly without LLM call
        question_lower = question.lower()
        for kw in keywords.DEAL_SPECIFIC_KEYWORDS:
            if kw in question_lower:
                return f"Happy to help! {deal_prompt}"

        # Vague question → use LLM for a more natural response
        deals_text    = " and ".join(available_deals) if available_deals else "our current investment opportunities"
        system_prompt = prompts.CLARIFICATION_SYSTEM_PROMPT.format(deals_text=deals_text)
        user_prompt   = prompts.CLARIFICATION_USER_PROMPT.format(question=question)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ]

        return self.chat_service.generate_response(
            messages    = messages,
            temperature = llm_config.LLM_CLARIFICATION_TEMPERATURE,
            max_tokens  = llm_config.LLM_CLARIFICATION_MAX_TOKENS
        ).strip()
