"""
Service: QueryHelper
=====================
Utility functions for query processing, context management, and data extraction.
Provides helper methods used by QueryService and DraftService.
"""

# Python Packages
from typing import Dict, List, Optional

# Database
from ...config.database import db
from ...models.odp_deal_document import DealDocument

# Config
from ..config import thresholds


class QueryHelper:
    """
    Collection of utility and helper methods for query service operations.
    """

    # ── Context Merging ────────────────────────────────────────────────────────
    def merge_context(self, dynamic_context: str, doc_context: str) -> str:
        """
        Merge Dynamic KB and Static KB context strings.
        Dynamic KB is always placed first so the LLM gives it higher priority.
        """
        if dynamic_context and doc_context:
            return dynamic_context + "\n\n" + doc_context
        return dynamic_context or doc_context


    # ── Pending Question Detection ─────────────────────────────────────────────
    def get_pending_question(self, history: List[Dict]) -> Optional[Dict]:
        """
        Return pending investor question if last assistant message was needs_info.
        Returns None otherwise.

        Scans history newest → oldest and returns as soon as it finds any
        assistant message. If that message is needs_info → return its data.
        If it's anything else → no pending question.
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
                return None  # last assistant message was not needs_info

        return None


    # ── Investor Question Resolution ───────────────────────────────────────────
    def resolve_investor_question(self, history: List[Dict], current_question: str = "") -> str:
        """
        Find the ORIGINAL investor question, resolving through clarification.

        Priority order:
          1. current_question > 20 chars → it IS the investor question.
          2. clarification metadata      → original_question stored by Step 11.
          3. First substantive user message in history.
        """
        # Priority 1: current_question is substantive
        if current_question and len(current_question.strip()) > 20:
            print(f"🔍 Investor Q from current question: \"{current_question[:60]}\"")
            return current_question.strip()

        # Priority 2: clarification flow
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


    # ── Deal Detection from History ────────────────────────────────────────────
    def get_deal_from_history(self, history: List[Dict]) -> Optional[int]:
        """
        Scan history newest → oldest; return first non-None deal_id found.
        """
        for msg in reversed(history):
            if msg.get("deal_id") is not None:
                return msg["deal_id"]
        return None


    # ── Document Names ─────────────────────────────────────────────────────────
    def get_doc_names(self, active_deal_id: Optional[int]) -> List[str]:
        """
        Return document names for the deal. Transaction-safe.
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


    # ── History Processing ─────────────────────────────────────────────────────
    def build_history_messages(self, history: List[Dict], max_messages: int = 6) -> List[Dict]:
        """
        Convert DB history to LLM turn dicts.
        Truncates long assistant messages to keep prompts manageable.
        """
        if not history:
            return []

        recent = history[-max_messages:] if len(history) > max_messages else history
        result = []

        for msg in recent:
            role    = msg.get("role", "user")
            content = msg.get("content", "").strip()
            if role in ("user", "assistant") and content:
                if role == "assistant" and len(content) > thresholds.ASSISTANT_MESSAGE_TRUNCATE_LENGTH:
                    content = content[:thresholds.ASSISTANT_MESSAGE_TRUNCATE_LENGTH] + "..."
                result.append({"role": role, "content": content})

        return result


    def build_conversation_summary(self, history: List[Dict], latest_user_answer: str = "") -> str:
        """
        Flatten conversation into plain-text for email draft generation.
        """
        if not history:
            return latest_user_answer

        lines = ["Conversation context:"]
        for msg in history:
            role    = "Investor" if msg["role"] == "user" else "ODP Team"
            content = msg.get("content", "").strip()
            if content:
                if msg["role"] == "assistant" and len(content) > thresholds.ASSISTANT_MESSAGE_DRAFT_LENGTH:
                    content = content[:thresholds.ASSISTANT_MESSAGE_DRAFT_LENGTH] + "..."
                lines.append(f"\n[{role}]: {content}")

        if latest_user_answer:
            lines.append(f"\n[ODP Team — answer provided]: {latest_user_answer}")

        return "\n".join(lines)
