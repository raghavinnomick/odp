"""
Query Service
Orchestrates the RAG pipeline: history → deal detection → search → context → answer

Key fixes vs previous version:
    1. Deal detection checks CURRENT QUESTION first (catches deal switches)
       then falls back to conversation history.
       Previously it only scanned history, so switching deals in the same
       thread kept returning the old deal_id.

    2. All deal facts loaded dynamically from DB via DealContextService.
       No hardcoded deal names, numbers, or facts anywhere.

    3. Tone rules loaded from odp_tone_rules table and passed to AnswerGenerator.

    4. Conversation history passed as real LLM message objects (not flat string).
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

# Database
from odp.config.database import db
from ...models.odp_deal_document import DealDocument

# Exceptions
from ...util.exceptions import ServiceException
from ...util import messages


class QueryService:
    """
    Main orchestrator for the RAG pipeline.
    All deal-specific context is loaded from DB — no hardcoded facts.
    """

    def __init__(self):
        self.search_service = SearchService()
        self.context_builder = ContextBuilder()
        self.answer_generator = AnswerGenerator()
        self.clarification_service = ClarificationService()
        self.conversation_service = ConversationService()
        self.query_enhancement_service = QueryEnhancementService()
        self.deal_context_service = DealContextService()


    def answer_question(
        self,
        question: str,
        deal_id: Optional[int] = None,
        session_id: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.5
    ) -> Dict:
        """
        Answer a question using the full RAG pipeline.

        Args:
            question: User's question
            deal_id: Explicit deal ID from the API caller (optional).
                     If None, we detect from the question or conversation history.
            session_id: Session ID for conversation history
            top_k: Number of document chunks to retrieve
            similarity_threshold: Minimum cosine similarity (0-1)

        Returns:
            dict: answer, sources, confidence, session_id, active_deal_id
        """

        try:
            print(f"\n{'='*60}")
            print(f"❓ Question: {question}")
            if session_id:
                print(f"📝 Session: {session_id}")
            print(f"{'='*60}")

            # ── Step 0: Conversation session ───────────────────────────────
            conversation = self.conversation_service.get_or_create_conversation(
                session_id=session_id
            )

            # ── Step 1: Load conversation history (before saving new msg) ──
            conversation_history = self.conversation_service.get_conversation_history(
                session_id=conversation.session_id,
                limit=10
            )

            # ── Step 2: Load all active deals for detection ────────────────
            all_deals = self.deal_context_service.get_all_active_deals()

            # ── Step 3: Detect the active deal ─────────────────────────────
            # Priority order:
            #   a) Explicit deal_id from API caller (highest)
            #   b) Deal name mentioned in the CURRENT question (catches switches)
            #   c) Most recent deal_id stored in conversation history (continuity)
            active_deal_id = deal_id

            if active_deal_id is None:
                # Check current question first — this catches deal switches
                active_deal_id = self.deal_context_service.detect_deal_in_text(
                    text=question,
                    all_deals=all_deals
                )

            if active_deal_id is None and conversation_history:
                # Fall back to most recent deal in history
                active_deal_id = self._get_deal_from_history(conversation_history)
                if active_deal_id:
                    print(f"🎯 Deal context from history: deal_id={active_deal_id}")

            # ── Step 4: Enhance the query using history ────────────────────
            enhanced_question = self.query_enhancement_service.enhance_query(
                current_question=question,
                conversation_history=conversation_history
            )

            # ── Step 5: Save the user's ORIGINAL question ──────────────────
            self.conversation_service.add_message(
                conversation_id=conversation.conversation_id,
                role="user",
                content=question,
                deal_id=active_deal_id
            )

            # ── Step 6: Vector search ──────────────────────────────────────
            # If active_deal_id is known, scope the search to that deal.
            # Otherwise search across all deals (first question, no context yet).
            relevant_chunks = self.search_service.search_similar_chunks(
                question=enhanced_question,
                deal_id=active_deal_id,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )

            # If search returned chunks from a specific deal, update active_deal_id
            # This handles the first question case where user mentions a deal name
            # but active_deal_id was None (detected AFTER search)
            if relevant_chunks and active_deal_id is None:
                deals_in_chunks = list(set([
                    chunk[6] for chunk in relevant_chunks
                    if len(chunk) > 6 and chunk[6] is not None
                ]))
                if deals_in_chunks:
                    active_deal_id = deals_in_chunks[0]
                    print(f"🎯 Deal detected from search results: deal_id={active_deal_id}")

            confidence = self.context_builder.calculate_confidence(relevant_chunks)

            # ── Step 7: Clarification check ────────────────────────────────
            if self.clarification_service.needs_clarification(
                question=question,
                chunks_found=len(relevant_chunks),
                confidence=confidence,
                has_deal_context=active_deal_id is not None
            ):
                if active_deal_id:
                    documents = db.session.query(DealDocument.doc_name).filter(
                        DealDocument.deal_id == active_deal_id
                    ).all()
                else:
                    documents = db.session.query(DealDocument.doc_name).all()

                doc_names = [doc[0] for doc in documents]
                deal_names = self.deal_context_service.get_all_deal_names()

                clarifying_q = self.clarification_service.generate_clarifying_question(
                    question=question,
                    available_documents=doc_names,
                    available_deals=deal_names
                )

                self.conversation_service.add_message(
                    conversation_id=conversation.conversation_id,
                    role="assistant",
                    content=clarifying_q,
                    metadata={"type": "clarification"}
                )

                return {
                    "needs_clarification": True,
                    "clarifying_question": clarifying_q,
                    "available_documents": doc_names,
                    "original_question": question,
                    "session_id": conversation.session_id
                }

            # ── Step 8: Build RAG document context ────────────────────────
            doc_context = self.context_builder.build_context(relevant_chunks)

            # ── Step 9: Load deal context from DB ─────────────────────────
            # This replaces ALL hardcoded deal facts.
            # Works for SpaceX, Anthropic, or any future deal.
            deal_context = ""
            if active_deal_id:
                deal_context = self.deal_context_service.build_deal_context(active_deal_id)

            # ── Step 10: Load tone rules from DB ──────────────────────────
            tone_rules = self.deal_context_service.get_tone_rules(
                deal_id=active_deal_id
            )

            # ── Step 11: Build real history messages for LLM ──────────────
            history_messages = self._build_history_messages(
                conversation_history=conversation_history,
                max_messages=6
            )

            # ── Step 12: Generate answer ───────────────────────────────────
            answer = self.answer_generator.generate_answer(
                question=question,
                context=doc_context,
                tone_rules=tone_rules,
                deal_context=deal_context,
                history_messages=history_messages
            )

            # ── Step 13: Save assistant message & return ───────────────────
            sources = self.context_builder.extract_sources(relevant_chunks)
            deals_used = list(set([
                chunk[6] for chunk in relevant_chunks
                if len(chunk) > 6 and chunk[6] is not None
            ]))

            self.conversation_service.add_message(
                conversation_id=conversation.conversation_id,
                role="assistant",
                content=answer,
                deal_id=active_deal_id,
                metadata={
                    "sources": sources,
                    "confidence": confidence,
                    "chunks_found": len(relevant_chunks)
                }
            )

            print(f"\n{'='*60}")
            print(f"✅ Answer generated | confidence={confidence} | deal_id={active_deal_id}")
            print(f"   Session: {conversation.session_id}")
            print(f"{'='*60}\n")

            return {
                "needs_clarification": False,
                "answer": answer,
                "sources": sources,
                "chunks_found": len(relevant_chunks),
                "confidence": confidence,
                "session_id": conversation.session_id,
                "deals_referenced": deals_used,
                "active_deal_id": active_deal_id
            }

        except Exception as error:
            print(f"❌ Error answering question: {str(error)}")
            raise ServiceException(
                error_code="QUERY_FAILED",
                message=messages.ERROR.get("QUERY_FAILED", "Failed to process question"),
                details=str(error)
            )


    # ── Private Helpers ────────────────────────────────────────────────────────

    def _get_deal_from_history(self, conversation_history: List[Dict]) -> Optional[int]:
        """
        Scan conversation history from newest to oldest for a stored deal_id.
        This provides continuity when the user asks follow-up questions
        without mentioning the deal name again.

        Note: This is only called AFTER checking the current question for deal
        mentions. So if the user switches deals ("what about Anthropic?"),
        the question check catches it first — this fallback never overrides it.

        Args:
            conversation_history: Chronological list of message dicts

        Returns:
            Most recently discussed deal_id, or None
        """
        for msg in reversed(conversation_history):
            msg_deal_id = msg.get("deal_id")
            if msg_deal_id is not None:
                return msg_deal_id
        return None


    def _build_history_messages(
        self,
        conversation_history: List[Dict],
        max_messages: int = 6
    ) -> List[Dict]:
        """
        Convert conversation history into real LLM message objects.
        These are injected directly into the messages array — not as text in the prompt.
        This gives the LLM proper multi-turn context for resolving follow-up questions.

        Args:
            conversation_history: Full chronological history
            max_messages: Cap to keep token budget manageable

        Returns:
            List of {role, content} dicts
        """
        if not conversation_history:
            return []

        recent = (
            conversation_history[-max_messages:]
            if len(conversation_history) > max_messages
            else conversation_history
        )

        result = []
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "").strip()
            if role in ("user", "assistant") and content:
                # Trim long assistant responses to keep token budget manageable
                if role == "assistant" and len(content) > 600:
                    content = content[:600] + "..."
                result.append({"role": role, "content": content})

        return result
