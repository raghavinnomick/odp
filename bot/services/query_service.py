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
import re
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
from ...config.database import db
from ...models.odp_deal_document import DealDocument

# Exceptions & messages
from ...util.exceptions import ServiceException
from ...util import messages

# Constants
from ...base import constants


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

    GREETING_PATTERNS = {
        "hello", "hi", "hey", "hiya", "howdy",
        "good morning", "good afternoon", "good evening", "good day",
        "how are you", "how r u", "what's up", "whats up", "sup",
        "thanks", "thank you", "thank you!", "thanks!", "cheers",
        "bye", "goodbye", "see you", "talk later",
        "ok", "okay", "alright", "got it", "noted",
        "yes", "no", "sure", "great", "perfect", "sounds good",
    }

    MISSING_INFO_SIGNALS = [
        "we don't have",
        "we do not have",
        "not in our knowledge base",
        "not found in our",
        "could you provide",
        "could you share",
        "please provide",
        "please share",
        "i need the following",
        "missing from our knowledge base",
        "not present in our documents",
        "i don't have",
        "i do not have",
    ]

    def __init__(self):
        self.search_service            = SearchService()
        self.context_builder           = ContextBuilder()
        self.answer_generator          = AnswerGenerator()
        self.clarification_service     = ClarificationService()
        self.conversation_service      = ConversationService()
        self.query_enhancement_service = QueryEnhancementService()
        self.deal_context_service      = DealContextService()

    # ── Main Entry Point ───────────────────────────────────────────────────────

    def answer_question(
        self,
        question: str,
        user_id: str,
        deal_id: Optional[int] = None,
        session_id: Optional[str] = None,
        top_k: int = constants.BOT_DEFAULT_TOP_K,
        similarity_threshold: float = constants.BOT_SIMILARITY_THRESHOLD
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
                session_id=session_id, user_id=user_id
            )

            # ── Step 2: History ────────────────────────────────────────────────
            history = self.conversation_service.get_conversation_history(
                session_id=conversation.session_id,
                limit=constants.BOT_LAST_CONVERSATION_MESSAGES_LIMIT
            )

            # ── Step 3: Active deals ───────────────────────────────────────────
            all_deals = self.deal_context_service.get_all_active_deals()

            # ── Step 4: Deal detection (URL → question text → history) ─────────
            active_deal_id = deal_id
            if active_deal_id is None:
                active_deal_id = self.deal_context_service.detect_deal_in_text(
                    text=question, all_deals=all_deals
                )
            if active_deal_id is None:
                active_deal_id = self._get_deal_from_history(history)
                if active_deal_id:
                    print(f"🎯 Deal from history: deal_id={active_deal_id}")

            # ── Step 5: Persist user message ───────────────────────────────────
            self.conversation_service.add_message(
                conversation_id=conversation.conversation_id,
                role="user",
                content=question,
                deal_id=active_deal_id
            )

            # ── Step 6: Greeting short-circuit ────────────────────────────────
            # MUST run before the pending needs_info check.
            # If the user says "Hello" after a needs_info message, we should greet
            # them back — NOT treat "Hello" as the missing answer.
            if self._is_greeting(question):
                tone_rules = self.deal_context_service.get_tone_rules(deal_id=active_deal_id)
                reply = self.answer_generator.generate_greeting_reply(
                    question=question,
                    tone_rules=tone_rules
                )
                self.conversation_service.add_message(
                    conversation_id=conversation.conversation_id,
                    role="assistant", content=reply,
                    deal_id=active_deal_id,
                    metadata={"type": "greeting"}
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
            # If the last bot message was type=needs_info AND we have a deal,
            # treat this message as the team member's supplied answer —
            # BUT only if the message does NOT look like a new question.
            # Without this guard, questions like "Whats the price per share?"
            # get swallowed as answers to the previous needs_info message.
            pending = self._get_pending_question(history)
            if pending and active_deal_id and not self._is_new_question(question):
                return self._handle_user_supplied_answer(
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
                question=enhanced_question,
                deal_id=active_deal_id,
                top_k=5,
                similarity_threshold=similarity_threshold
            )
            if dynamic_context:
                print("✅ Dynamic KB returned results — will override static KB for same facts")

            # ── Step 10: TIER 1 — Static KB vector search ─────────────────────
            chunks = self.search_service.search_similar_chunks(
                question=enhanced_question,
                deal_id=active_deal_id,
                top_k=top_k,
                similarity_threshold=similarity_threshold
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
                question=question,
                chunks_found=len(chunks),
                confidence=confidence,
                has_deal_context=active_deal_id is not None
            ):
                doc_names  = self._get_doc_names(active_deal_id)
                deal_names = self.deal_context_service.get_all_deal_names()
                clarifying_q = self.clarification_service.generate_clarifying_question(
                    question=question,
                    available_documents=doc_names,
                    available_deals=deal_names
                )
                self.conversation_service.add_message(
                    conversation_id=conversation.conversation_id,
                    role="assistant", content=clarifying_q,
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
            tone_rules = self.deal_context_service.get_tone_rules(deal_id=active_deal_id)

            # ── Step 14: LLM history messages ─────────────────────────────────
            history_messages = self._build_history_messages(history, max_messages=6)

            # ── Step 15: Generate answer ───────────────────────────────────────
            answer = self.answer_generator.generate_answer(
                question=question,
                context=full_context,
                tone_rules=tone_rules,
                deal_context=deal_context,
                history_messages=history_messages
            )

            sources = self.context_builder.extract_sources(chunks)

            # ── Step 16: TIER 3 — Missing info detected ────────────────────────
            if self._has_missing_info_signal(answer):
                original_investor_question = self._resolve_investor_question(
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
        top_k: int = constants.BOT_DEFAULT_TOP_K,
        similarity_threshold: float = constants.BOT_SIMILARITY_THRESHOLD
    ) -> Dict:
        """Generate a draft reply email from the full conversation (button-triggered)."""
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

            investor_question = self._resolve_investor_question(history=history)
            if not investor_question:
                raise ServiceException(
                    error_code="NO_QUESTION",
                    message="No investor question found in conversation history."
                )

            active_deal_id = self._get_deal_from_history(history)

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
            full_context = self._merge_context(dynamic_context, doc_context)

            deal_context     = self.deal_context_service.build_deal_context(active_deal_id) if active_deal_id else ""
            tone_rules       = self.deal_context_service.get_tone_rules(deal_id=active_deal_id)
            history_messages = self._build_history_messages(history, max_messages=10)
            summary          = self._build_conversation_summary(history)

            draft = self.answer_generator.generate_draft_email(
                original_investor_question=investor_question,
                user_supplied_info=summary,
                tone_rules=tone_rules,
                deal_context=deal_context,
                doc_context=full_context,
                history_messages=history_messages
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

    def _handle_user_supplied_answer(
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
        full_context = self._merge_context(dynamic_context, doc_context)

        deal_context     = self.deal_context_service.build_deal_context(active_deal_id)
        tone_rules       = self.deal_context_service.get_tone_rules(deal_id=active_deal_id)
        history_messages = self._build_history_messages(history, max_messages=10)
        summary          = self._build_conversation_summary(history, user_answer)

        draft = self.answer_generator.generate_draft_email(
            original_investor_question = pending_question,
            user_supplied_info         = summary,
            tone_rules                 = tone_rules,
            deal_context               = deal_context,
            doc_context                = full_context,
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

    # ── Private Helpers ────────────────────────────────────────────────────────

    def _merge_context(self, dynamic_context: str, doc_context: str) -> str:
        """
        Merge Dynamic KB and Static KB context strings.
        Dynamic KB is always placed first so the LLM gives it higher priority.
        """
        if dynamic_context and doc_context:
            return dynamic_context + "\n\n" + doc_context
        return dynamic_context or doc_context

    def _get_pending_question(self, history: List[Dict]) -> Optional[Dict]:
        """
        Return pending investor question if last assistant message was needs_info.
        Returns None otherwise.
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

    def _resolve_investor_question(
        self,
        history: List[Dict],
        current_question: str = ""
    ) -> str:
        """
        Find the ORIGINAL investor question, resolving through clarification.

        Priority order:
          1. current_question — if substantive (> 20 chars), it IS the investor
             question that triggered this needs_info response. Use it directly.
             This prevents stale first-session questions from propagating forever.
          2. clarification metadata — when flow is: question → "which deal?" → deal name,
             the real question is stored in clarification metadata["original_question"].
          3. Last resort — first substantive user message in history.
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

    def _has_missing_info_signal(self, answer: str) -> bool:
        """Return True if the LLM answer signals it could not confirm some facts."""
        answer_lower = answer.lower()
        return any(sig in answer_lower for sig in self.MISSING_INFO_SIGNALS)

    def _get_doc_names(self, active_deal_id: Optional[int]) -> List[str]:
        """Return document names for the deal. Transaction-safe."""
        try:
            query = db.session.query(DealDocument.doc_name)
            if active_deal_id:
                query = query.filter(DealDocument.deal_id == active_deal_id)
            return [row[0] for row in query.all()]
        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  _get_doc_names failed: {exc}")
            return []

    def _get_deal_from_history(self, history: List[Dict]) -> Optional[int]:
        """Scan history newest→oldest; return first non-None deal_id."""
        for msg in reversed(history):
            if msg.get("deal_id") is not None:
                return msg["deal_id"]
        return None

    def _build_history_messages(
        self,
        history: List[Dict],
        max_messages: int = 6
    ) -> List[Dict]:
        """Convert DB history to LLM turn dicts. Truncates long assistant messages."""
        if not history:
            return []
        recent = history[-max_messages:] if len(history) > max_messages else history
        result = []
        for msg in recent:
            role    = msg.get("role", "user")
            content = msg.get("content", "").strip()
            if role in ("user", "assistant") and content:
                if role == "assistant" and len(content) > 600:
                    content = content[:600] + "..."
                result.append({"role": role, "content": content})
        return result

    def _build_conversation_summary(
        self,
        history: List[Dict],
        latest_user_answer: str = ""
    ) -> str:
        """Flatten conversation into plain-text for email draft generation."""
        if not history:
            return latest_user_answer
        lines = ["Conversation context:"]
        for msg in history:
            role    = "Investor" if msg["role"] == "user" else "ODP Team"
            content = msg.get("content", "").strip()
            if content:
                if msg["role"] == "assistant" and len(content) > 800:
                    content = content[:800] + "..."
                lines.append(f"\n[{role}]: {content}")
        if latest_user_answer:
            lines.append(f"\n[ODP Team — answer provided]: {latest_user_answer}")
        return "\n".join(lines)

    def _is_new_question(self, question: str) -> bool:
        """
        Return True if the message looks like a new question rather than a
        supplied answer to a pending needs_info request.

        Used in Step 7 to prevent new questions being swallowed as answers.

        Examples that return True (new questions):
          "Whats the price per share now?"       ✓ starts with "whats"
          "What is the minimum ticket?"          ✓ starts with "what"
          "Can you tell me the structure?"       ✓ starts with "can you"
          "Do you have further info on fees?"    ✓ starts with "do you"
          "Please tell me the closing date"      ✓ starts with "please"

        Examples that return False (supplied answers):
          "Share price is ~$378"                 ✗ answer statement
          "Payment dates would be next Tuesday"  ✗ answer statement
          "$25k minimum"                         ✗ value only
        """
        q = question.lower().strip()

        QUESTION_STARTERS = [
            "what", "when", "where", "which", "who", "why", "how",
            "can you", "could you", "do you", "is there", "are there",
            "tell me", "please tell", "please provide", "please share",
            "can we", "would you",
        ]
        return any(q.startswith(starter) for starter in QUESTION_STARTERS)

    def _is_greeting(self, question: str) -> bool:
        """
        Return True if the message is pure social/small-talk with no business intent.

        Logic (in order):
          1. Exact match against known greeting phrases (e.g. "how are you").
          2. If the message starts with a greeting word, strip all social filler
             words (bot, you, are, doing, i, am, we, etc.) and check whether
             any REAL business keywords remain. If none remain → greeting.
          3. Otherwise → not a greeting.

        Examples that must return True:
          "Hello"                   ✓ exact
          "Hi there"                ✓ greeting starter, no business words
          "Hello Bot, How are you?" ✓ greeting starter, only social filler remains
          "Hey! Thanks a lot"       ✓ greeting starter, only social filler

        Examples that must return False:
          "How much is the minimum?" ✗ business keyword "minimum"
          "What is the share price?" ✗ business keyword "share", "price"
          "Hi, what is the fee?"     ✗ business keyword "fee"
        """
        # Normalise: lowercase, strip punctuation
        text = re.sub(r"[^\w\s]", " ", question.strip().lower()).strip()
        text = re.sub(r"\s+", " ", text)

        # 1. Exact match against known greeting/social phrases
        if text in self.GREETING_PATTERNS:
            return True

        # Words that indicate real business intent — if any appear after
        # stripping social filler, this is NOT a greeting
        BUSINESS_KEYWORDS = {
            "minimum", "ticket", "investment", "deal", "structure",
            "payment", "date", "fee", "fees", "carry", "valuation",
            "return", "returns", "fund", "close", "closing", "allocation",
            "share", "shares", "price", "wire", "document", "documents",
            "sign", "subscription", "information", "details", "lockup",
            "lock", "period", "spv", "equity", "preferred", "common",
            "distribution", "ebitda", "arr", "revenue", "growth",
            # Question starters that indicate an information request
            "what", "when", "where", "which", "who", "why",
            "can you", "could you", "please", "tell me", "explain",
            "do you have", "is there", "are there", "how much", "how many",
            "how long", "how do",
        }

        # Social filler words — these do NOT indicate business intent
        SOCIAL_FILLER = {
            "hello", "hi", "hey", "hiya", "howdy", "good", "morning",
            "afternoon", "evening", "day", "how", "are", "you", "doing",
            "i", "am", "we", "bot", "there", "mate", "sir", "team",
            "thanks", "thank", "cheers", "bye", "goodbye", "ok", "okay",
            "alright", "sure", "great", "perfect", "noted", "got", "it",
            "very", "well", "fine", "nice", "sup", "whats", "up",
        }

        GREETING_STARTERS = {
            "hello", "hi", "hey", "hiya", "howdy", "good",
            "thanks", "thank", "bye", "goodbye", "ok", "okay", "alright",
        }

        words = text.split()
        if not words:
            return False

        # 2. Starts with a greeting word?
        if words[0] in GREETING_STARTERS:
            # Remove all social filler — what's left must be empty for a greeting
            remaining = [w for w in words if w not in SOCIAL_FILLER]
            if not remaining:
                return True  # only social words remain → pure greeting
            # Check if any remaining words are business keywords
            if any(w in BUSINESS_KEYWORDS for w in remaining):
                return False  # business intent detected
            # Short message with no business words → treat as greeting
            if len(words) <= 8:
                return True

        return False
