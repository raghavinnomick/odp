"""
Service: FactExtractorService

Detects when an ODP team member's chat message contains a factual deal value
(e.g. "Share Price is ~$378", "Minimum ticket is $50k", "Lockup is 12 months")
and stores it in odp_deal_dynamic_facts as an approved fact.

Effect:
  - The NEXT user who asks the same question gets the answer from the KB.
  - The bot never asks the same question twice.

Design:
  - Uses the LLM to extract structured JSON from the user's message.
  - Stores with approval_status='approved' immediately (team = trusted source).
  - If fact_key already exists for the deal → updates value (upsert behaviour).
  - Skips greetings, questions, and messages with no clear factual value
    (pre-screen avoids unnecessary LLM calls).
"""

# Python Packages
import json
from datetime import date, datetime
from typing import Optional, Dict

# Database
from ...config.database import db

# Models
from ...models.odp_deal_dynamic_fact import DealDynamicFact

# Vendors
from ...vendors.openai import ChatService


class FactExtractorService:
    """
    Extracts deal facts from team member messages and persists them to
    odp_deal_dynamic_facts so they immediately enrich the Dynamic KB.
    """

    # Prompt that instructs the LLM to return a JSON extraction result.
    # Kept here so it can be updated without changing service logic.
    _EXTRACTION_SYSTEM_PROMPT = """You are a fact extractor for a private investment firm.

Your job: decide if a message from an internal team member contains a factual deal value,
and if so, extract it as structured JSON.

FACT types to extract:
- share_price           (e.g. "$378", "~$378 per share")
- minimum_ticket        (e.g. "$50,000", "$50k minimum")
- lockup_period         (e.g. "12 months", "1 year lockup")
- management_fee        (e.g. "2% per year", "2/20 structure")
- carry                 (e.g. "20% carry", "5% performance fee")
- valuation             (e.g. "valued at $350B")
- payment_date          (e.g. "payment on March 15")
- closing_date          (e.g. "closing April 2025")
- total_allocation      (e.g. "total raise of $5M")
- distribution_schedule (e.g. "quarterly distributions")
- other                 (any other specific deal fact with a clear value)

RULES:
- Only extract if there is a CLEAR factual value (number, date, duration, percentage).
- Do NOT extract questions, opinions, greetings, or vague statements.
- fact_key must be snake_case, lowercase, descriptive.
- fact_value must be the raw value exactly as stated by the user.

Respond ONLY with valid JSON, no markdown, no explanation:

If a fact is present:
{"is_fact": true, "fact_key": "share_price", "fact_value": "~$378"}

If no fact:
{"is_fact": false}"""

    def __init__(self):
        self.chat_service = ChatService()

    # ── Public ─────────────────────────────────────────────────────────────────

    def extract_and_store(
        self,
        message: str,
        deal_id: int,
        user_id: str,
        conversation_context: str = ""
    ) -> Optional[Dict]:
        """
        Check if *message* contains a deal fact. If yes, upsert it into
        odp_deal_dynamic_facts.

        Args:
            message:              The team member's chat message.
            deal_id:              The active deal ID (required).
            user_id:              Who provided the fact (stored in audit fields).
            conversation_context: Optional last bot message for better extraction.

        Returns:
            {"action": "created"|"updated", "fact_key": ..., "fact_value": ...,
             "deal_id": ...}  if a fact was stored, else None.
        """
        if not deal_id:
            return None

        # Fast pre-screen to avoid unnecessary LLM calls
        if self._is_obviously_not_a_fact(message):
            return None

        extracted = self._extract_via_llm(message, conversation_context)

        if not extracted or not extracted.get("is_fact"):
            return None

        fact_key   = extracted.get("fact_key", "").strip().lower().replace(" ", "_")
        fact_value = extracted.get("fact_value", "").strip()

        if not fact_key or not fact_value:
            return None

        return self._upsert_fact(deal_id, fact_key, fact_value, user_id, message)

    # ── Private ────────────────────────────────────────────────────────────────

    def _is_obviously_not_a_fact(self, message: str) -> bool:
        """
        Fast pre-screen — returns True for clear non-facts so we skip
        the LLM call entirely.

        Skips:
          - Messages shorter than 5 characters
          - Messages ending with "?" (questions)
          - Short greeting phrases
        """
        text = message.strip().lower()

        if len(text) < 5:
            return True

        if text.rstrip().endswith("?"):
            return True

        greeting_starts = (
            "hello", "hi ", "hey", "thanks", "thank you",
            "ok", "okay", "great", "sounds good", "noted"
        )
        if any(text.startswith(g) for g in greeting_starts) and len(text) < 30:
            return True

        return False

    def _extract_via_llm(
        self,
        message: str,
        conversation_context: str = ""
    ) -> Optional[Dict]:
        """
        Call the LLM to extract a structured fact from *message*.

        Args:
            message:              Raw team member message.
            conversation_context: Optional preceding bot message for context.

        Returns:
            Parsed JSON dict from LLM, or None on failure.
        """
        try:
            user_content = message
            if conversation_context:
                user_content = (
                    f"Previous bot message (context):\n{conversation_context}\n\n"
                    f"Team member replied:\n{message}"
                )

            response = self.chat_service.generate_response(
                messages=[
                    {"role": "system", "content": self._EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_content}
                ],
                temperature=0,
                max_tokens=100
            )

            # Strip accidental markdown fences before parsing
            clean = response.strip().strip("```json").strip("```").strip()
            return json.loads(clean)

        except Exception as exc:
            print(f"⚠️  FactExtractor LLM call failed: {exc}")
            return None

    def _upsert_fact(
        self,
        deal_id:    int,
        fact_key:   str,
        fact_value: str,
        user_id:    str,
        raw_message: str
    ) -> Optional[Dict]:
        """
        Insert or update a fact in odp_deal_dynamic_facts.

        If the same fact_key already exists for the deal, update its value.
        Always sets approval_status='approved' (team member is trusted).

        Args:
            deal_id:     Target deal.
            fact_key:    Snake_case key, e.g. "share_price".
            fact_value:  Raw value string, e.g. "~$378".
            user_id:     Team member's user_id.
            raw_message: Original message (stored as source_note).

        Returns:
            Dict with action / fact_key / fact_value / deal_id, or None on error.
        """
        source_note = (
            f"Provided by team member via chat. "
            f"Original message: \"{raw_message[:200]}\""
        )

        try:
            existing = DealDynamicFact.query.filter_by(
                deal_id  = deal_id,
                fact_key = fact_key
            ).first()

            now = datetime.utcnow()

            if existing:
                old_value               = existing.fact_value
                existing.fact_value     = fact_value
                existing.source_note    = source_note
                existing.approval_status = "approved"
                existing.approved_by    = user_id
                existing.approved_at    = now
                existing.as_of_date     = date.today()
                db.session.commit()

                print(f"✅ Fact UPDATED — deal_id={deal_id} | "
                      f"{fact_key}: \"{old_value}\" → \"{fact_value}\"")

                return {
                    "action": "updated", "fact_key": fact_key,
                    "fact_value": fact_value, "deal_id": deal_id
                }

            else:
                new_fact = DealDynamicFact(
                    deal_id         = deal_id,
                    fact_key        = fact_key,
                    fact_value      = fact_value,
                    as_of_date      = date.today(),
                    source_note     = source_note,
                    approval_status = "approved",
                    approved_by     = user_id,
                    approved_at     = now,
                    created_by      = user_id
                )
                db.session.add(new_fact)
                db.session.commit()

                print(f"✅ Fact STORED — deal_id={deal_id} | {fact_key}: \"{fact_value}\"")

                return {
                    "action": "created", "fact_key": fact_key,
                    "fact_value": fact_value, "deal_id": deal_id
                }

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  _upsert_fact failed: {exc}")
            return None
