"""
Service: QueryEnhancementService
==================================
Rewrites vague follow-up questions into self-contained, specific questions
by leveraging conversation history.

Examples:
  History:  "What is the SpaceX valuation?"
  Current:  "What about revenue?"
  Enhanced: "What is the revenue of SpaceX?"

The LLM is only called when the question contains vague indicators (pronouns,
short metric-only queries). Clear questions pass through unchanged.
"""

# Python Packages
from typing import List, Dict

# Vendors
from ...vendors import ChatService

# Config
from ..config import prompts, llm_config, keywords


class QueryEnhancementService:
    """
    Resolves anaphora and vague references in user questions using
    recent conversation history.
    """

    def __init__(self):
        self.chat_service = ChatService()


    def enhance_query(self, current_question: str, conversation_history: List[Dict]) -> str:
        """
        Rewrite *current_question* to be self-contained using history context.

        Returns the original question unchanged if:
          - history is too short to help
          - no vague indicators detected
          - the LLM call fails
        """
        if not conversation_history or len(conversation_history) < 2:
            return current_question

        if not self._needs_enhancement(current_question):
            return current_question

        history_text = self._build_history_text(conversation_history)

        user_prompt = prompts.QUERY_REWRITER_USER_TEMPLATE.format(
            history_text     = history_text,
            current_question = current_question
        )

        messages = [
            {"role": "system", "content": prompts.QUERY_REWRITER_SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt}
        ]

        try:
            enhanced = self.chat_service.generate_response(
                messages    = messages,
                temperature = llm_config.LLM_QUERY_REWRITER_TEMPERATURE,
                max_tokens  = llm_config.LLM_QUERY_REWRITER_MAX_TOKENS
            ).strip().strip('"').strip("'")
        except Exception as exc:
            print(f"⚠️  QueryEnhancement LLM call failed: {exc}")
            return current_question

        if enhanced and enhanced != current_question:
            print(f"🔄 Enhanced: '{current_question}' → '{enhanced}'")
            return enhanced

        return current_question


    # ── Private ────────────────────────────────────────────────────────────────
    def _needs_enhancement(self, question: str) -> bool:
        """
        Return True if the question likely needs context to be understood.

        Indicators:
          - Contains vague pronouns / references (it, that, same, etc.)
          - Very short (< 4 words) without a company name
          - Metric-only phrasing without a company name
        """
        question_lower = question.lower()

        for word in keywords.VAGUE_WORDS:
            if word in question_lower:
                return True

        words = question.split()

        if len(words) < 4:
            if not any(c in question_lower for c in keywords.COMPANY_NAMES):
                return True

        if len(words) <= 5:
            for metric in keywords.METRIC_ONLY_PATTERNS:
                if metric in question_lower:
                    if not any(c in question_lower for c in keywords.COMPANY_NAMES):
                        return True

        return False

    def _build_history_text(self, history: List[Dict]) -> str:
        """
        Format the last 6 messages as a readable history string.
        Long assistant responses are truncated to 200 chars.
        """
        recent = history[-6:] if len(history) > 6 else history
        lines  = []

        for msg in recent:
            role    = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"]
            if role == "Assistant" and len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"{role}: {content}")

        return "\n".join(lines)
