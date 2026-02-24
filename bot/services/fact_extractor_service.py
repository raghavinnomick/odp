"""
Service: FactExtractorService
==============================
Detects when an ODP team member's chat message contains a factual deal value
(e.g. "Share Price is ~$378", "Minimum ticket is $50k", "Lockup is 12 months")
and stores it in odp_deal_dynamic_facts as an approved fact.

Effect:
  - The NEXT user who asks the same question gets the answer from the KB.
  - The bot never asks the same question twice.

Design:
  - The extraction prompt lives in config/prompts.py (FACT_EXTRACTOR_SYSTEM_PROMPT).
  - LLM settings live in config/llm_config.py.
  - Uses the LLM to extract structured JSON from the user's message.
  - Stores with approval_status='approved' immediately (team = trusted source).
  - If fact_key already exists for the deal → updates value (upsert).
  - Skips greetings, questions, and messages with no clear factual value.
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
from ...vendors import ChatService

# Config
from ..config import prompts, llm_config


class FactExtractorService:
    """
    Extracts deal facts from team member messages and persists them to
    odp_deal_dynamic_facts so they immediately enrich the Dynamic KB.
    """

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

        Returns:
            {"action": "created"|"updated", "fact_key": ..., "fact_value": ...,
             "deal_id": ...}  if a fact was stored, else None.
        """
        if not deal_id:
            return None

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
        Fast pre-screen — returns True for clear non-facts to skip the LLM call.

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

    def _extract_via_llm(self, message: str, conversation_context: str = "") -> Optional[Dict]:
        """
        Call the LLM to extract a structured fact from *message*.
        The system prompt is defined in config/prompts.py.
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
                    {"role": "system", "content": prompts.FACT_EXTRACTOR_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_content}
                ],
                temperature = llm_config.LLM_FACT_EXTRACTOR_TEMPERATURE,
                max_tokens  = llm_config.LLM_FACT_EXTRACTOR_MAX_TOKENS
            )

            clean = response.strip().strip("```json").strip("```").strip()
            return json.loads(clean)

        except Exception as exc:
            print(f"⚠️  FactExtractor LLM call failed: {exc}")
            return None

    def _upsert_fact(
        self,
        deal_id:     int,
        fact_key:    str,
        fact_value:  str,
        user_id:     str,
        raw_message: str
    ) -> Optional[Dict]:
        """
        Insert or update a fact in odp_deal_dynamic_facts.
        Always sets approval_status='approved' (team member is trusted).
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
                old_value                = existing.fact_value
                existing.fact_value      = fact_value
                existing.source_note     = source_note
                existing.approval_status = "approved"
                existing.approved_by     = user_id
                existing.approved_at     = now
                existing.as_of_date      = date.today()
                db.session.commit()

                print(f"✅ Fact UPDATED — deal_id={deal_id} | {fact_key}: \"{old_value}\" → \"{fact_value}\"")
                return {"action": "updated", "fact_key": fact_key, "fact_value": fact_value, "deal_id": deal_id}

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
                return {"action": "created", "fact_key": fact_key, "fact_value": fact_value, "deal_id": deal_id}

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  _upsert_fact failed: {exc}")
            return None
