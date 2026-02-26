"""
Service: DraftService

Handles draft email generation from conversation history and user-supplied answers.
Manages both manual draft generation and automatic draft creation after needs_info.
"""

# Python Packages
from typing import Dict, List, Optional

# Services
from .search_service import SearchService
from .context_builder import ContextBuilder
from .answer_generator import AnswerGenerator
from .conversation_service import ConversationService
from .deal_context_service import DealContextService
from .query_helper_service import QueryHelper
from .thread_parser_service import ThreadParserService

# Database
from ...config.database import db

# Exceptions & messages
from ...util.exceptions import ServiceException
from ...util import messages

# Config
from ..config import bot_config


class DraftService:
    """
    Manages draft email generation and user-supplied answer handling.
    Orchestrates between KB search, context building, and answer generation.
    """

    def __init__(self):
        self.search_service       = SearchService()
        self.context_builder      = ContextBuilder()
        self.answer_generator     = AnswerGenerator()
        self.conversation_service = ConversationService()
        self.deal_context_service = DealContextService()
        self.helper               = QueryHelper()
        self.thread_parser_service = ThreadParserService()

    # ── Manual Draft Generation ────────────────────────────────────────────────

    def generate_draft_from_session(
        self,
        session_id: str,
        user_id: str,
        top_k: int = bot_config.BOT_DEFAULT_TOP_K,
        similarity_threshold: float = bot_config.BOT_SIMILARITY_THRESHOLD
    ) -> Dict:
        """
        Generate a draft reply email from the full conversation (button-triggered).

        Args:
            session_id: The conversation session identifier.
            user_id: The user identifier.
            top_k: Number of top chunks to retrieve.
            similarity_threshold: Minimum similarity for chunk inclusion.

        Returns:
            Dict with draft_email, investor_question, and session metadata.

        Raises:
            ServiceException on error.
        """
        try:
            print(f"\n{'='*60}")
            print(f"✉️  Generating draft: session={session_id}")
            print(f"{'='*60}")

            conversation = self.conversation_service.get_or_create_conversation(
                session_id=session_id, user_id=user_id
            )
            history = self.conversation_service.get_conversation_history(
                session_id=conversation.session_id, limit=20
            )

            if not history:
                raise ServiceException(
                    error_code="NO_CONVERSATION",
                    message="No conversation history found.",
                    details=f"session_id={session_id}"
                )

            investor_question = self.helper.resolve_investor_question(history=history)
            if not investor_question:
                raise ServiceException(
                    error_code="NO_QUESTION",
                    message="No investor question found in conversation history."
                )

            active_deal_id = self.helper.get_deal_from_history(history)

            # Dynamic KB first, then static — same priority order as main flow
            dynamic_context = self.deal_context_service.search_dynamic_kb(
                question=investor_question,
                deal_id=active_deal_id,
                top_k=5,
                similarity_threshold=similarity_threshold
            )
            chunks      = self.search_service.search_similar_chunks(
                question=investor_question,
                deal_id=active_deal_id,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            doc_context  = self.context_builder.build_context(chunks)
            full_context = self.helper.merge_context(dynamic_context, doc_context)

            deal_context     = self.deal_context_service.build_deal_context(active_deal_id) if active_deal_id else ""
            tone_rules       = self.deal_context_service.get_tone_rules(deal_id=active_deal_id)
            history_messages = self.helper.build_history_messages(history, max_messages=10)
            summary          = self.helper.build_conversation_summary(history)

            # Thread context — enriches draft with investor's style when available
            thread_context = self.thread_parser_service.get_thread_context(
                session_id=conversation.session_id
            )
            if thread_context:
                print("📧 Thread context injected into draft prompt")

            draft = self.answer_generator.generate_draft_email(
                original_investor_question = investor_question,
                user_supplied_info         = summary,
                tone_rules                 = tone_rules,
                deal_context               = deal_context,
                doc_context                = full_context,
                thread_context             = thread_context,
                history_messages           = history_messages
            )

            self.conversation_service.add_message(
                conversation_id=conversation.conversation_id,
                role="assistant", content=draft,
                deal_id=active_deal_id,
                metadata={"type": "draft_email", "trigger": "generate_draft_button"}
            )

            print(f"✅ Draft generated | deal_id={active_deal_id}")
            return {
                "response_type":     "draft_email",
                "draft_email":       draft,
                "investor_question": investor_question,
                "session_id":        conversation.session_id,
                "active_deal_id":    active_deal_id,
                "show_draft_button": False
            }

        except ServiceException:
            raise
        except Exception as error:
            db.session.rollback()
            print(f"❌ Draft generation failed: {error}")
            raise ServiceException(
                error_code="DRAFT_FAILED",
                message="Failed to generate draft email.",
                details=str(error)
            )

    # ── User-Supplied Answer Handler ───────────────────────────────────────────

    def handle_user_supplied_answer(
        self,
        conversation,
        user_answer: str,
        pending_question: str,
        active_deal_id: int,
        user_id: str,
        history: List[Dict],
        top_k: int,
        similarity_threshold: float
    ) -> Dict:
        """
        Called when the user replies to a needs_info message.

        Key behaviour:
          - Calls store_dynamic_kb_with_decomposition() which stores the full
            Q&A AND individually decomposes multi-part answers into separate
            atomic fact records (e.g. "minimum ticket" → "$25k" stored with
            just that question, so future single-fact queries match it precisely).
          - Re-runs both KB tiers (Dynamic first) for the draft context.

        Args:
            conversation: The Conversation ORM object.
            user_answer: The answer supplied by the user.
            pending_question: The original investor question.
            active_deal_id: The deal context.
            user_id: The user identifier.
            history: Conversation history.
            top_k: Number of top chunks to retrieve.
            similarity_threshold: Minimum similarity for chunk inclusion.

        Returns:
            Draft email response dict.
        """
        print(f"💾 User supplied answer | pending Q: \"{pending_question[:60]}...\"")

        # Store the answer — decomposed into individual facts for precise retrieval
        self.deal_context_service.store_dynamic_kb_with_decomposition(
            deal_id           = active_deal_id,
            investor_question = pending_question,
            user_answer       = user_answer,
            created_by        = user_id
        )

        # Re-run both tiers for draft context (Dynamic first)
        dynamic_context = self.deal_context_service.search_dynamic_kb(
            question=pending_question,
            deal_id=active_deal_id,
            top_k=5,
            similarity_threshold=similarity_threshold
        )
        chunks      = self.search_service.search_similar_chunks(
            question=pending_question,
            deal_id=active_deal_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )
        doc_context  = self.context_builder.build_context(chunks)
        full_context = self.helper.merge_context(dynamic_context, doc_context)

        deal_context     = self.deal_context_service.build_deal_context(active_deal_id)
        tone_rules       = self.deal_context_service.get_tone_rules(deal_id=active_deal_id)
        history_messages = self.helper.build_history_messages(history, max_messages=10)
        summary          = self.helper.build_conversation_summary(history, user_answer)

        # Thread context — enriches draft with investor's style when available
        thread_context = self.thread_parser_service.get_thread_context(
            session_id=conversation.session_id
        )

        draft = self.answer_generator.generate_draft_email(
            original_investor_question = pending_question,
            user_supplied_info         = summary,
            tone_rules                 = tone_rules,
            deal_context               = deal_context,
            doc_context                = full_context,
            thread_context             = thread_context,
            history_messages           = history_messages
        )

        self.conversation_service.add_message(
            conversation_id = conversation.conversation_id,
            role            = "assistant",
            content         = draft,
            deal_id         = active_deal_id,
            metadata        = {"type": "draft_email", "trigger": "user_supplied_answer"}
        )

        print("✉️  Draft generated after user supplied answer")
        return {
            "response_type":     "draft_email",
            "draft_email":       draft,
            "investor_question": pending_question,
            "session_id":        conversation.session_id,
            "active_deal_id":    active_deal_id,
            "show_draft_button": False
        }
