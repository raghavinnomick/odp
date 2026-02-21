"""
Service: QueryEnhancementService

Rewrites vague follow-up questions into self-contained, specific questions
by leveraging conversation history.

Examples:
  History:  "What is the SpaceX valuation?"
  Current:  "What about revenue?"
  Enhanced: "What is the revenue of SpaceX?"

  History:  "Tell me about Anthropic"
  Current:  "What's their valuation?"
  Enhanced: "What is the valuation of Anthropic?"

The LLM is only called when the question contains vague indicators (pronouns,
short metric-only queries). Clear questions pass through unchanged.
"""

# Python Packages
from typing import Optional, List, Dict

# Vendors
from ...vendors.openai import ChatService

# Configuration
from ..config import query_config
from ..config import deal_config
from ..config import prompts


class QueryEnhancementService:
    """
    Resolves anaphora and vague references in user questions using
    recent conversation history.
    """

    def __init__(self):
        self.chat_service = ChatService()

    def enhance_query(
        self,
        current_question: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        Rewrite *current_question* to be self-contained using history context.

        Args:
            current_question:    The raw question from the user.
            conversation_history: Recent messages [{role, content}, ...].

        Returns:
            Rewritten question string, or *current_question* unchanged if
            no enhancement is needed or the LLM call fails.
        """
        # Skip enhancement when there is no useful history
        if not conversation_history or len(conversation_history) < 2:
            return current_question

        if not self._needs_enhancement(current_question):
            return current_question

        history_text = self._build_history_text(conversation_history)

        user_prompt = (
            f"Conversation History:\n{history_text}\n\n"
            f"Current Question: {current_question}\n\n"
            f"Rewritten Question:"
        )

        messages = [
            {"role": "system", "content": prompts.QUERY_REWRITER_PROMPT},
            {"role": "user",   "content": user_prompt}
        ]

        try:
            enhanced = self.chat_service.generate_response(
                messages    = messages,
                temperature = query_config.QUERY_REWRITER_TEMPERATURE,
                max_tokens  = query_config.QUERY_REWRITER_MAX_TOKENS
            )
        except Exception as exc:
            print(f"⚠️  QueryEnhancement LLM call failed: {exc}")
            return current_question

        enhanced_query = enhanced.strip().strip('"').strip("'")

        if enhanced_query and enhanced_query != current_question:
            print(f"🔄 Enhanced: '{current_question}' → '{enhanced_query}'")
            return enhanced_query

        return current_question

    # ── Private ────────────────────────────────────────────────────────────────

    def _needs_enhancement(self, question: str) -> bool:
        """
        Return True if the question likely requires context to be understood.

        Indicators:
          - Contains vague pronouns / references (it, that, same, etc.)
          - Very short (< 4 words) without a company name
          - Metric-only phrasing (e.g. "revenue?") without a company name
        """
        question_lower = question.lower()

        # Vague pronoun / reference words
        for word in query_config.VAGUE_WORDS:
            if word in question_lower:
                return True

        words = question.split()

        # Short question with no company name mentioned
        if len(words) < 4:
            if not any(c in question_lower for c in deal_config.COMPANY_NAMES):
                return True

        # Metric-only question without a company name
        if len(words) <= 5:
            for metric in query_config.METRIC_ONLY_PATTERNS:
                if metric in question_lower:
                    if not any(c in question_lower for c in deal_config.COMPANY_NAMES):
                        return True

        return False

    def _build_history_text(self, history: List[Dict]) -> str:
        """
        Format the last 6 messages as a readable history string.

        Long assistant responses are truncated to 200 chars to keep the
        rewriter prompt small and focused.

        Args:
            history: Conversation history, oldest first.

        Returns:
            Multi-line string "User: ...\nAssistant: ...\n..."
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
