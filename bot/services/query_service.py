"""
Service: QueryService  —  RAG Pipeline Orchestrator

3-Tier Answer Flow
==================
TIER 2  Dynamic KB   ALWAYS searched FIRST — odp_deal_dynamic_facts
                     Team-corrected facts OVERRIDE static document content.
TIER 1  Static KB    Searched second — odp_deal_document_chunks (documents)
TIER 3  Ask user     When both KBs have no answer → ask team for missing values
                     → User replies → decomposed + stored → Draft Email generated

Why Dynamic KB comes first
===========================
If a team member corrected the minimum ticket from $50k (in the PDF) to $25k,
that correction is in odp_deal_dynamic_facts. The static KB still has the old
$50k. By searching Dynamic KB first and placing its results at the TOP of the
LLM context, the LLM will always prefer the team-corrected value.

The system prompt also explicitly tells the LLM:
  "Team-supplied facts (Dynamic KB) override document passages."

Response types
==============
greeting      Friendly reply, no RAG
answer        Answer found in Dynamic KB or Static KB
needs_info    Partial/no answer — asks team for specific missing values only
draft_email   Team replied → KB updated → draft ready to send
"""

# Python Packages
from typing import Dict, List, Optional

# Services
from .query_enhancement_service import QueryEnhancementService
from .search_service import SearchService
from .context_builder import ContextBuilder
from .answer_generator import AnswerGenerator
from .clarification_service import ClarificationService
from .conversation_service import ConversationService
from .deal_context_service import DealContextService
from .draft_service import DraftService
from .question_analyzer_service import QuestionAnalyzerService
from .query_helper_service import QueryHelper

# Database
from ...config.database import db

# Exceptions & messages
from ...util.exceptions import ServiceException
from ...util import messages

# Config
from ..config import bot_config





class QueryService:
    """
    Orchestrates the full RAG pipeline for a single user message.

    LLM context order (highest priority → lowest):
      1. Dynamic KB  — team-supplied / corrected facts (odp_deal_dynamic_facts)
      2. Static KB   — document passages (odp_deal_document_chunks)
      3. Deal info   — one-line deal identifier

    This order guarantees that when a team member corrects a figure
    (e.g. minimum ticket $25k, not $50k as written in the PDF),
    the correction always wins over the document.
    """

    def __init__(self):
        """ Initialize all services used by the query pipeline. """

        self.search_service            = SearchService()
        self.context_builder           = ContextBuilder()
        self.answer_generator          = AnswerGenerator()
        self.clarification_service     = ClarificationService()
        self.conversation_service      = ConversationService()
        self.query_enhancement_service = QueryEnhancementService()
        self.deal_context_service      = DealContextService()
        self.draft_service             = DraftService()
        self.question_analyzer         = QuestionAnalyzerService()
        self.helper                    = QueryHelper()



    # ── Main Entry Point ───────────────────────────────────────────────────────
    def answer_question(
        self,
        question: str,
        user_id: str,
        deal_id: Optional[int] = None,
        session_id: Optional[str] = None,
        top_k: int = bot_config.BOT_DEFAULT_TOP_K,
        similarity_threshold: float = bot_config.BOT_SIMILARITY_THRESHOLD
    ) -> Dict:
        """
        Process one user message through the full RAG pipeline.

        Args:
            question:             Raw message from the team member.
            user_id:              Team member identifier.
            deal_id:              Explicit deal scope from URL param (optional).
            session_id:           Existing session UUID, or None for new session.
            top_k:                Max chunks per search tier.
            similarity_threshold: Min cosine similarity for chunk inclusion.

        Returns:
            Response dict with "response_type" and "session_id".

        Raises:
            ServiceException on unrecoverable error.
        """

        try:
            print(f"\n{'='*60}")
            print(f"❓ Question: {question}")
            print(f"{'='*60}")

            # ── Step 1: Session ────────────────────────────────────────────────
            conversation = self.conversation_service.get_or_create_conversation(
                session_id = session_id, user_id = user_id
            )

            # ── Step 2: History ────────────────────────────────────────────────
            history = self.conversation_service.get_conversation_history(
                session_id = conversation.session_id,
                limit = bot_config.BOT_LAST_CONVERSATION_MESSAGES_LIMIT
            )

            # ── Step 3: Active deals ───────────────────────────────────────────
            all_deals = self.deal_context_service.get_all_active_deals()

            # ── Step 4: Deal detection (URL → question text → history) ─────────
            active_deal_id = deal_id
            if active_deal_id is None:
                active_deal_id = self.deal_context_service.detect_deal_in_text(
                    text = question, all_deals = all_deals
                )
 
            if active_deal_id is None:
                active_deal_id = self.helper.get_deal_from_history(history)
                if active_deal_id:
                    print(f"🎯 Deal from history: deal_id={active_deal_id}")

            # ── Step 5: Persist user message ───────────────────────────────────
            self.conversation_service.add_message(
                conversation_id = conversation.conversation_id,
                role = "user",
                content = question,
                deal_id = active_deal_id
            )

            # ── Step 6: Greeting short-circuit ────────────────────────────────
            # MUST run before the pending needs_info check.
            # If the user says "Hello" after a needs_info message, we should greet
            # them back — NOT treat "Hello" as the missing answer.
            # MAY BE THIS LOGIC, WE CAN REMOVE IT IN FUTURE [RAGHAV GARG] 2026-02-23
            if self.question_analyzer.is_greeting(question):
                # Get Tone Rules
                tone_rules = self.deal_context_service.get_tone_rules(deal_id = active_deal_id)

                # Get Reply and persist
                reply = self.answer_generator.generate_greeting_reply(
                    question = question,
                    tone_rules = tone_rules
                )
                self.conversation_service.add_message(
                    conversation_id = conversation.conversation_id,
                    role = "assistant", 
                    content = reply,
                    deal_id = active_deal_id,
                    metadata = {"type": "greeting"}
                )
                print("👋 Greeting handled — skipping RAG and pending check")
                return {
                    "response_type":     "answer",
                    "answer":            reply,
                    "sources":           [],
                    "chunks_found":      0,
                    "confidence":        "high",
                    "session_id":        conversation.session_id,
                    "active_deal_id":    active_deal_id,
                    "show_draft_button": False
                }

            # ── Step 7: Pending needs_info check ───────────────────────────────
            # Only reaches here when the message is NOT a greeting.
            # If the last bot message was type = needs_info AND we have a deal,
            # treat this message as the team member's supplied answer —
            # BUT only if the message does NOT look like a new question.
            # Without this guard, questions like "Whats the price per share?"
            # get swallowed as answers to the previous needs_info message.

            pending = self.helper.get_pending_question(history)

            if pending and active_deal_id and not self.question_analyzer.is_new_question(question):
                return self.draft_service.handle_user_supplied_answer(
                    conversation         = conversation,
                    user_answer          = question,
                    pending_question     = pending["investor_question"],
                    active_deal_id       = active_deal_id,
                    user_id              = user_id,
                    history              = history,
                    top_k                = top_k,
                    similarity_threshold = similarity_threshold
                )

            # ── Step 8: Query enhancement (resolve pronouns) ───────────────────
            enhanced_question = self.query_enhancement_service.enhance_query(
                current_question=question,
                conversation_history=history
            )

            # ── Step 9: TIER 2 — Dynamic KB (ALWAYS first) ────────────────────
            # Team corrections must always override document content.
            # Searched unconditionally, before static KB.
            print("📚 Searching Dynamic KB (Tier 2 — always first)...")
            dynamic_context = self.deal_context_service.search_dynamic_kb(
                question = enhanced_question,
                deal_id = active_deal_id,
                top_k = 5,
                similarity_threshold = similarity_threshold
            )
            if dynamic_context:
                print("✅ Dynamic KB returned results — will override static KB for same facts")

            # ── Step 10: TIER 1 — Static KB vector search ─────────────────────
            chunks = self.search_service.search_similar_chunks(
                question = enhanced_question,
                deal_id = active_deal_id,
                top_k = top_k,
                similarity_threshold = similarity_threshold
            )

            # Infer deal from search results if still unknown
            if chunks and active_deal_id is None:
                deal_ids = [c[6] for c in chunks if len(c) > 6 and c[6]]
                if deal_ids:
                    active_deal_id = deal_ids[0]
                    print(f"🎯 Deal inferred from search: deal_id={active_deal_id}")

            confidence = self.context_builder.calculate_confidence(chunks)

            # ── Step 11: Clarification ("which deal?") ─────────────────────────
            if self.clarification_service.needs_clarification(
                question = question,
                chunks_found = len(chunks),
                confidence = confidence,
                has_deal_context = active_deal_id is not None
            ):
                doc_names  = self.helper.get_doc_names(active_deal_id)
                deal_names = self.deal_context_service.get_all_deal_names()
                clarifying_q = self.clarification_service.generate_clarifying_question(
                    question = question,
                    available_documents = doc_names,
                    available_deals = deal_names
                )
                self.conversation_service.add_message(
                    conversation_id = conversation.conversation_id,
                    role = "assistant", content = clarifying_q,
                    metadata={
                        "type":              "clarification",
                        "original_question": question  # preserved for needs_info
                    }
                )
                return {
                    "response_type":       "needs_clarification",
                    "needs_clarification": True,
                    "clarifying_question": clarifying_q,
                    "session_id":          conversation.session_id,
                    "show_draft_button":   False
                }

            # ── Step 12: Merge context — Dynamic KB FIRST ─────────────────────
            # By placing dynamic_context at the top, the LLM sees team corrections
            # before document passages. Combined with system prompt instructions,
            # this ensures team-supplied values override document values.
            doc_context  = self.context_builder.build_context(chunks)
            full_context = self._merge_context(dynamic_context, doc_context)

            # ── Step 13: Deal context + tone rules ─────────────────────────────
            deal_context = (
                self.deal_context_service.build_deal_context(active_deal_id)
                if active_deal_id else ""
            )
            tone_rules = self.deal_context_service.get_tone_rules(deal_id = active_deal_id)

            # ── Step 14: LLM history messages ─────────────────────────────────
            history_messages = self.helper.build_history_messages(history, max_messages = 6)

            # ── Step 15: Generate answer ───────────────────────────────────────
            answer = self.answer_generator.generate_answer(
                question = question,
                context = full_context,
                tone_rules = tone_rules,
                deal_context = deal_context,
                history_messages=history_messages
            )

            sources = self.context_builder.extract_sources(chunks)

            # ── Step 16: TIER 3 — Missing info detected ────────────────────────
            if self.question_analyzer.has_missing_info_signal(answer):
                original_investor_question = self.helper.resolve_investor_question(
                    history=history, current_question=question
                )
                info_request = self.answer_generator.generate_info_request(
                    original_question=original_investor_question,
                    partial_answer=answer,
                    tone_rules=tone_rules,
                    history_messages=history_messages
                )
                full_response = f"{answer}\n\n---\n{info_request}"
                self.conversation_service.add_message(
                    conversation_id=conversation.conversation_id,
                    role="assistant", content=full_response,
                    deal_id=active_deal_id,
                    metadata={
                        "type":              "needs_info",
                        "investor_question": original_investor_question,
                        "sources":           sources,
                        "confidence":        confidence
                    }
                )
                print("📋 Tier 3 — asking user for missing info")
                return {
                    "response_type":     "needs_info",
                    "needs_info":        True,
                    "partial_answer":    answer,
                    "info_request":      info_request,
                    "session_id":        conversation.session_id,
                    "active_deal_id":    active_deal_id,
                    "show_draft_button": False
                }

            # ── Step 17: Full answer ───────────────────────────────────────────
            self.conversation_service.add_message(
                conversation_id=conversation.conversation_id,
                role="assistant", content=answer,
                deal_id=active_deal_id,
                metadata={"type": "answer", "sources": sources, "confidence": confidence}
            )
            print(f"✅ Answer | confidence={confidence} | deal_id={active_deal_id}")
            return {
                "response_type":     "answer",
                "answer":            answer,
                "sources":           sources,
                "chunks_found":      len(chunks),
                "confidence":        confidence,
                "session_id":        conversation.session_id,
                "active_deal_id":    active_deal_id,
                "show_draft_button": True
            }

        except Exception as error:
            db.session.rollback()
            print(f"❌ Query pipeline failed: {error}")
            raise ServiceException(
                error_code="QUERY_FAILED",
                message=messages.ERROR.get("QUERY_FAILED", "Failed to process question"),
                details=str(error)
            )


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

        Delegates to DraftService which handles all draft generation logic.

        Args:
            session_id: The conversation session identifier.
            user_id: The user identifier.
            top_k: Number of top chunks to retrieve.
            similarity_threshold: Minimum similarity for chunk inclusion.

        Returns:
            Draft email response dict.
        """
        return self.draft_service.generate_draft_from_session(
            session_id=session_id,
            user_id=user_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )
