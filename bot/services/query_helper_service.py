"""
Service: QueryHelper

Utility functions for query processing, context management, and data extraction.
Provides helper methods used by QueryService and DraftService.
"""

# Python Packages
from typing import Dict, List, Optional

# Database
from ...config.database import db
from ...models.odp_deal_document import DealDocument

# Config
from ..config import service_constants





class QueryHelper:
    """
    Collection of utility and helper methods for query service operations.
    """

    # ── Context Management ─────────────────────────────────────────────────────
    def merge_context(self, dynamic_context: str, doc_context: str) -> str:
        """
        Merge Dynamic KB and Static KB context strings.
        Dynamic KB is always placed first so the LLM gives it higher priority.

        Args:
            dynamic_context: Context from Dynamic KB (team-supplied facts).
            doc_context: Context from Static KB (document passages).

        Returns:
            Merged context string with Dynamic KB first.
        """
        if dynamic_context and doc_context:
            return dynamic_context + "\n\n" + doc_context
        return dynamic_context or doc_context



    # ── Pending Question Detection ─────────────────────────────────────────────
    def get_pending_question(self, history: List[Dict]) -> Optional[Dict]:
        """
        Return pending investor question if last assistant message was needs_info.
        Returns None otherwise.

        Args:
            history: Conversation history list.

        Returns:
            Dict with 'investor_question' key, or None if no pending question.
        """

        if not history:
            return None

        for msg in reversed(history):
            if msg.get("role") == "assistant":
                meta = msg.get("metadata") or {}
                if meta.get("type") == "needs_info":
                    investor_q = meta.get("investor_question", "")
                    if investor_q:
                        return {"investor_question": investor_q}
                return None
    
        return None



    # ── Question Resolution ────────────────────────────────────────────────────
    def resolve_investor_question(
        self,
        history: List[Dict],
        current_question: str = ""
    ) -> str:
        """
        Find the ORIGINAL investor question, resolving through clarification.

        Priority order:
          1. current_question — if substantive (> 20 chars), it IS the investor
             question that triggered this needs_info response. Use it directly.
          2. clarification metadata — when flow is: question → "which deal?" → deal name,
             the real question is stored in clarification metadata["original_question"].
          3. Last resort — first substantive user message in history.

        Args:
            history: Conversation history list.
            current_question: The current question being processed.

        Returns:
            The resolved investor question string.
        """
        # Priority 1: current_question is substantive — it IS the investor question
        if current_question and len(current_question.strip()) > 20:
            print(f"🔍 Investor Q from current question: \"{current_question[:60]}\"")
            return current_question.strip()

        # Priority 2: clarification flow — find original_question from metadata
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                meta = msg.get("metadata") or {}
                if meta.get("type") == "clarification":
                    original = meta.get("original_question", "")
                    if original:
                        print(f"🔍 Investor Q from clarification: \"{original[:60]}\"")
                        return original
                break

        # Priority 3: first substantive user message
        for msg in history:
            if msg.get("role") == "user":
                content = msg.get("content", "").strip()
                if len(content) > 20:
                    print(f"🔍 Investor Q from first substantive msg: \"{content[:60]}\"")
                    return content

        return current_question



    # ── Deal Detection ────────────────────────────────────────────────────────
    def get_deal_from_history(self, history: List[Dict]) -> Optional[int]:
        """
        Scan history newest→oldest; return first non-None deal_id.

        Args:
            history: Conversation history list.

        Returns:
            Deal ID if found, None otherwise.
        """

        for msg in reversed(history):
            if msg.get("deal_id") is not None:
                return msg["deal_id"]

        return None



    # ── Document Management ────────────────────────────────────────────────────

    def get_doc_names(self, active_deal_id: Optional[int]) -> List[str]:
        """
        Return document names for the deal. Transaction-safe.

        Args:
            active_deal_id: The deal ID to get documents for (optional).

        Returns:
            List of document names.
        """
        try:
            query = db.session.query(DealDocument.doc_name)
            if active_deal_id:
                query = query.filter(DealDocument.deal_id == active_deal_id)
            return [row[0] for row in query.all()]
        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  get_doc_names failed: {exc}")
            return []

    # ── History Processing ────────────────────────────────────────────────────

    def build_history_messages(
        self,
        history: List[Dict],
        max_messages: int = 6
    ) -> List[Dict]:
        """
        Convert DB history to LLM turn dicts. Truncates long assistant messages.

        Args:
            history: Full conversation history from database.
            max_messages: Maximum number of recent messages to include.

        Returns:
            List of message dicts with 'role' and 'content' keys.
        """
        if not history:
            return []
        recent = history[-max_messages:] if len(history) > max_messages else history
        result = []
        for msg in recent:
            role    = msg.get("role", "user")
            content = msg.get("content", "").strip()
            if role in ("user", "assistant") and content:
                if role == "assistant" and len(content) > service_constants.ASSISTANT_MESSAGE_TRUNCATE_LENGTH:
                    content = content[:service_constants.ASSISTANT_MESSAGE_TRUNCATE_LENGTH] + "..."
                result.append({"role": role, "content": content})
        return result

    def build_conversation_summary(
        self,
        history: List[Dict],
        latest_user_answer: str = ""
    ) -> str:
        """
        Flatten conversation into plain-text for email draft generation.

        Args:
            history: Conversation history list.
            latest_user_answer: Most recent answer from the user (optional).

        Returns:
            Plain-text summary of the conversation.
        """
        if not history:
            return latest_user_answer
        lines = ["Conversation context:"]
        for msg in history:
            role    = "Investor" if msg["role"] == "user" else "ODP Team"
            content = msg.get("content", "").strip()
            if content:
                if msg["role"] == "assistant" and len(content) > service_constants.ASSISTANT_MESSAGE_DRAFT_LENGTH:
                    content = content[:service_constants.ASSISTANT_MESSAGE_DRAFT_LENGTH] + "..."
                lines.append(f"\n[{role}]: {content}")
        if latest_user_answer:
            lines.append(f"\n[ODP Team — answer provided]: {latest_user_answer}")
        return "\n".join(lines)
