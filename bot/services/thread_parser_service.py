"""
Service: ThreadParserService
==============================
Parses a raw email thread pasted by a team member into structured JSON,
stores it in odp_deal_email_threads, and returns the parsed context so
QueryService and DraftService can inject it into every LLM prompt.

Flow
----
1. Team member pastes thread via POST /bot/thread (or Gmail Extension sends it).
2. ThreadParserService.submit_thread() is called.
   a. Validates and stores raw thread → parse_status = 'pending'.
   b. Calls _parse_via_llm() → LLM returns structured JSON.
   c. Updates row with parsed fields → parse_status = 'completed'.
   d. Returns the full DealEmailThread record.
3. On every subsequent /bot/ask call, QueryService calls get_thread_context()
   which returns the formatted context string (or "" if no thread).

Null thread handling
--------------------
A session with NO thread in this table works exactly as before — get_thread_context()
returns "" and QueryService/DraftService skip the thread block entirely.
No errors, no broken flows. The thread is purely additive context.

Deal detection
--------------
deal_signals extracted by the LLM are cross-referenced against active deals
in odp_deals. If a match is found, deal_id is set on the thread record.
If not (e.g. brand-new deal), deal_id stays null and the bot's existing
deal-detection logic handles it during chat.
"""

# Python Packages
import json
from typing import Optional, Dict

# Database
from ...config.database import db

# Models
from ...models.odp_deal_email_thread import DealEmailThread
from ...models.odp_deal import Deal

# Vendors
from ...vendors import ChatService

# Config
from ..config import prompts, llm_config, bot_config





class ThreadParserService:
    """
    Manages the full lifecycle of an email thread:
      submit → parse → store → serve context to pipeline.

    All DB writes are transaction-safe with rollback on failure.
    """

    def __init__(self):
        """ Initialize the service with any necessary clients or config."""

        self.chat_service = ChatService()



    # ── Public: Submit & Parse ─────────────────────────────────────────────────
    def submit_thread(
        self,
        session_id: str,
        raw_thread_text: str,
        user_id: str,
        source: str = "manual_paste"
    ) -> DealEmailThread:
        """
        Validate, store, parse, and return a thread record.

        Steps:
          1. Deactivate any existing active thread for this session.
          2. Store new thread row with parse_status='pending'.
          3. Parse via LLM.
          4. Update row with parsed fields.
          5. Attempt deal_id detection from deal_signals.

        Args:
            session_id:      The bot conversation session this thread belongs to.
            raw_thread_text: The full pasted email thread text.
            user_id:         The team member submitting the thread.
            source:          'manual_paste' (v1) or 'gmail_extension' (future).

        Returns:
            Updated DealEmailThread record (parse_status='completed' or 'failed').

        Raises:
            ValueError: If thread text fails validation.
            Exception:  Propagated on unrecoverable DB error.
        """
        raw_thread_text = raw_thread_text.strip()

        # ── Validate ───────────────────────────────────────────────────────────
        self._validate_thread_text(raw_thread_text)

        # ── Deactivate any existing active thread for this session ─────────────
        self._deactivate_existing_threads(session_id)

        # ── Store raw thread ───────────────────────────────────────────────────
        thread = DealEmailThread(
            session_id      = session_id,
            raw_thread_text = raw_thread_text,
            source          = source,
            parse_status    = "pending",
            is_active       = True,
            created_by      = user_id
        )
        db.session.add(thread)
        db.session.commit()
        db.session.refresh(thread)
        print(f"📧 Thread stored | id={thread.id} | session={session_id}")

        # ── Parse via LLM ──────────────────────────────────────────────────────
        parsed = self._parse_via_llm(raw_thread_text)

        if parsed:
            # ── Detect deal_id from deal_signals ───────────────────────────────
            deal_id = self._detect_deal_from_signals(
                parsed.get("deal_signals", [])
            )

            # ── Update record with parsed data ─────────────────────────────────
            thread.parsed_investor_name   = parsed.get("investor_name")
            thread.parsed_investor_email  = parsed.get("investor_email")
            thread.parsed_latest_question = parsed.get("latest_question")
            thread.parsed_summary         = parsed.get("thread_summary")
            thread.parsed_context         = parsed
            thread.deal_id                = deal_id
            thread.parse_status           = "completed"

            print(f"✅ Thread parsed | investor={thread.parsed_investor_name} "
                  f"| deal_id={deal_id} | signals={parsed.get('deal_signals', [])}")
        else:
            thread.parse_status = "failed"
            thread.parse_error  = "LLM returned no valid JSON."
            print(f"⚠️  Thread parse failed | id={thread.id}")

        db.session.commit()
        db.session.refresh(thread)
        return thread



    # ── Public: Load Thread Context ────────────────────────────────────────────
    def get_thread_context(self, session_id: str) -> str:
        """
        Return a formatted context string for injection into LLM prompts.

        Returns "" if:
          - No thread exists for this session.
          - Thread parse_status is not 'completed'.
          - parsed_context is missing.

        The caller (QueryService / DraftService) injects this string into
        the user-turn prompt BEFORE the KB context blocks.
        """
        thread = self._get_active_thread(session_id)

        if not thread or thread.parse_status != "completed" or not thread.parsed_context:
            return ""

        ctx = thread.parsed_context
        unk = prompts.THREAD_CONTEXT_UNKNOWN
        non = prompts.THREAD_CONTEXT_NONE

        already_discussed = ctx.get("already_discussed") or []
        open_items        = ctx.get("open_items")        or []

        return prompts.THREAD_CONTEXT_BLOCK_TEMPLATE.format(
            investor_name     = ctx.get("investor_name")   or unk,
            investor_email    = ctx.get("investor_email")  or unk,
            investor_tone     = ctx.get("investor_tone")   or unk,
            already_discussed = ", ".join(already_discussed) if already_discussed else non,
            open_items        = ", ".join(open_items)        if open_items        else non,
            latest_question   = ctx.get("latest_question")  or unk,
            thread_summary    = ctx.get("thread_summary")   or unk,
        )


    def get_thread_deal_id(self, session_id: str) -> Optional[int]:
        """
        Return the deal_id detected from the thread, or None.
        Used by QueryService to pre-populate active_deal_id from the thread.
        """
        thread = self._get_active_thread(session_id)
        if thread and thread.deal_id:
            print(f"🎯 Deal from thread: deal_id={thread.deal_id}")
            return thread.deal_id
        return None


    def get_thread_for_session(self, session_id: str) -> Optional[Dict]:
        """
        Return the active thread record as a dict for the API response.
        Returns None if no active thread exists.
        """
        thread = self._get_active_thread(session_id)
        return thread.to_dict() if thread else None


    def deactivate_thread(self, session_id: str) -> bool:
        """
        Deactivate the active thread for a session (used by DELETE endpoint).
        Returns True if a thread was found and deactivated, False otherwise.
        """
        return self._deactivate_existing_threads(session_id)


    # ── Private: LLM Parse ────────────────────────────────────────────────────
    def _parse_via_llm(self, raw_thread: str) -> Optional[Dict]:
        """
        Call LLM to extract structured context from the raw thread text.

        Returns parsed dict on success, None on failure.
        The LLM is instructed to return ONLY valid JSON (see THREAD_PARSER_SYSTEM_PROMPT).
        """

        try:
            user_prompt = prompts.THREAD_PARSER_USER_TEMPLATE.format(
                raw_thread=raw_thread
            )

            response = self.chat_service.generate_response(
                messages=[
                    {"role": "system", "content": prompts.THREAD_PARSER_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt}
                ],
                temperature = llm_config.LLM_THREAD_PARSER_TEMPERATURE,
                max_tokens  = llm_config.LLM_THREAD_PARSER_MAX_TOKENS
            )

            # Strip any accidental markdown fences
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()

            parsed = json.loads(clean)

            # Ensure required fields exist (set defaults for missing ones)
            parsed.setdefault("deal_signals",      [])
            parsed.setdefault("already_discussed", [])
            parsed.setdefault("open_items",        [])
            parsed.setdefault("participants",      [])
            parsed.setdefault("email_count",       0)
            parsed.setdefault("thread_summary",    "")

            return parsed

        except json.JSONDecodeError as exc:
            print(f"⚠️  ThreadParser: JSON decode failed: {exc}")
            return None
        except Exception as exc:
            print(f"⚠️  ThreadParser: LLM call failed: {exc}")
            return None



    # ── Private: Deal Detection ───────────────────────────────────────────────
    def _detect_deal_from_signals(self, deal_signals: list) -> Optional[int]:
        """
        Cross-reference LLM-extracted deal_signals against active deals in DB.

        Returns deal_id of the first match, or None.
        Case-insensitive substring match on deal_name and deal_code.
        """
        if not deal_signals:
            return None

        try:
            active_deals = Deal.query.filter_by(status=True).all()
            signals_lower = [s.lower() for s in deal_signals]

            for deal in active_deals:
                name_lower = deal.deal_name.lower()
                code_lower = deal.deal_code.lower()

                for signal in signals_lower:
                    if signal in name_lower or name_lower in signal:
                        print(f"🎯 Deal matched from thread signal: '{signal}' → {deal.deal_name} (id={deal.deal_id})")
                        return deal.deal_id
                    if signal in code_lower or code_lower in signal:
                        print(f"🎯 Deal matched from thread signal: '{signal}' → {deal.deal_name} (id={deal.deal_id})")
                        return deal.deal_id

            print(f"⚠️  No deal matched from signals: {deal_signals}")
            return None

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  _detect_deal_from_signals failed: {exc}")
            return None



    # ── Private: DB Helpers ───────────────────────────────────────────────────
    def _get_active_thread(self, session_id: str) -> Optional[DealEmailThread]:
        """Return the active thread for a session, or None."""
        try:
            return DealEmailThread.query.filter_by(
                session_id = session_id,
                is_active  = True
            ).first()
        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  _get_active_thread failed (session={session_id}): {exc}")
            return None


    def _deactivate_existing_threads(self, session_id: str) -> bool:
        """
        Deactivate all active threads for a session.
        Called before storing a new thread so only one is ever active.
        Returns True if at least one thread was deactivated.
        """
        try:
            updated = (
                DealEmailThread.query
                .filter_by(session_id=session_id, is_active=True)
                .all()
            )
            if not updated:
                return False

            for t in updated:
                t.is_active = False

            db.session.commit()
            print(f"🔄 Deactivated {len(updated)} existing thread(s) for session={session_id}")
            return True

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  _deactivate_existing_threads failed (session={session_id}): {exc}")
            return False

    def _validate_thread_text(self, text: str) -> None:
        """
        Raise ValueError if thread text fails basic sanity checks.
        Limits live in config/bot_config.py.
        """
        if len(text) < bot_config.BOT_THREAD_MIN_LENGTH:
            raise ValueError(
                f"Thread text too short. Minimum {bot_config.BOT_THREAD_MIN_LENGTH} characters."
            )
        if len(text) > bot_config.BOT_THREAD_MAX_LENGTH:
            raise ValueError(
                f"Thread text too long. Maximum {bot_config.BOT_THREAD_MAX_LENGTH} characters."
            )
