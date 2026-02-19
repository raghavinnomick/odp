"""
Deal Context Service
Dynamically loads deal-specific context from the database.

This service is the replacement for ALL hardcoded deal facts in the system prompt.
It works for any deal — current or future — without any code changes.

Data sources:
    odp_deals            → deal name, code (for detection)
    odp_deal_terms       → structured terms (valuation, fees, structure, security type)
    odp_deal_dynamic_facts → live facts (approved only): share price, min ticket, carry, etc.
    odp_faqs             → approved Q&A pairs for this deal
    odp_tone_rules       → global + deal-specific tone/compliance rules
"""

# Python Packages
from typing import List, Dict, Optional, Tuple

# Database
from odp.config.database import db

# Models
from ...models.odp_deal import Deal
from ...models.odp_deal_term import DealTerm
from ...models.odp_deal_dynamic_fact import DealDynamicFact
from ...models.odp_faq import DealFAQ
from ...models.odp_tone_rule import ToneRule


class DealContextService:
    """
    Service for dynamically loading deal context from the database.
    No deal names, facts, or numbers are hardcoded anywhere in this file.
    """

    # ── Deal Discovery ─────────────────────────────────────────────────────────

    def get_all_active_deals(self) -> List[Dict]:
        """
        Get all active deals from the database.
        Used for dynamic deal name detection in user messages.

        Returns:
            List of dicts: [{deal_id, deal_name, deal_code}, ...]
        """
        try:
            deals = Deal.query.filter_by(status=True).all()
            return [
                {
                    "deal_id": d.deal_id,
                    "deal_name": d.deal_name,
                    "deal_code": d.deal_code
                }
                for d in deals
            ]
        except Exception as e:
            print(f"⚠️  Error loading active deals: {e}")
            return []


    def detect_deal_in_text(self, text: str, all_deals: List[Dict]) -> Optional[int]:
        """
        Check if any deal name or code appears in the given text.
        Used to detect deal switches when user mentions a new deal in their question.

        Checks deal_name and deal_code (both case-insensitive).
        Returns the FIRST match found (most deals have unique names).

        Args:
            text: Text to search (typically the user's current question)
            all_deals: List returned by get_all_active_deals()

        Returns:
            deal_id if a deal name/code is found in text, else None
        """
        text_lower = text.lower()

        for deal in all_deals:
            deal_name_lower = deal["deal_name"].lower()
            deal_code_lower = deal["deal_code"].lower()

            if deal_name_lower in text_lower or deal_code_lower in text_lower:
                print(f"🔍 Deal detected in question: '{deal['deal_name']}' → deal_id={deal['deal_id']}")
                return deal["deal_id"]

        return None


    # ── Deal Context Builder ───────────────────────────────────────────────────

    def build_deal_context(self, deal_id: int) -> str:
        """
        Build a structured context string for a specific deal, loaded entirely from DB.
        This is injected into the LLM prompt alongside the RAG document chunks.

        Includes:
            - Deal name and code
            - Deal terms (valuation, security type, fees, structure, round type)
            - Approved dynamic facts (live, up-to-date facts like share price, minimum)
            - Approved FAQs (curated Q&A pairs)

        Args:
            deal_id: The deal to load context for

        Returns:
            Formatted string ready to include in the LLM prompt.
            Returns empty string if deal not found.
        """
        try:
            parts = []

            # ── Deal name ─────────────────────────────────────────────────────
            deal = Deal.query.get(deal_id)
            if not deal:
                print(f"⚠️  No deal found for deal_id={deal_id}")
                return ""

            parts.append(f"ACTIVE DEAL: {deal.deal_name} (code: {deal.deal_code})")
            parts.append("")

            # ── Deal Terms ────────────────────────────────────────────────────
            terms = DealTerm.query.filter_by(deal_id=deal_id).first()
            if terms:
                parts.append("── DEAL TERMS ──")
                if terms.security_type:
                    parts.append(f"Security Type: {terms.security_type}")
                if terms.valuation:
                    parts.append(f"Valuation: {terms.valuation}")
                if terms.round_type:
                    parts.append(f"Round Type: {terms.round_type}")
                if terms.structure_summary:
                    parts.append(f"Structure: {terms.structure_summary}")
                if terms.fee_summary:
                    parts.append(f"Fees: {terms.fee_summary}")
                parts.append("")

            # ── Approved Dynamic Facts ────────────────────────────────────────
            dynamic_facts = DealDynamicFact.query.filter_by(
                deal_id=deal_id,
                approval_status="approved"
            ).order_by(DealDynamicFact.fact_key).all()

            if dynamic_facts:
                parts.append("── CURRENT DEAL FACTS ──")
                for fact in dynamic_facts:
                    label = fact.fact_key.replace("_", " ").title()
                    value = fact.fact_value
                    if fact.as_of_date:
                        value += f" (as of {fact.as_of_date})"
                    parts.append(f"{label}: {value}")
                parts.append("")

            # ── Approved FAQs ─────────────────────────────────────────────────
            faqs = DealFAQ.query.filter_by(
                deal_id=deal_id,
                status="approved"
            ).all()

            if faqs:
                parts.append("── APPROVED Q&A FOR THIS DEAL ──")
                for faq in faqs:
                    parts.append(f"Q: {faq.question}")
                    parts.append(f"A: {faq.answer}")
                    parts.append("")

            context = "\n".join(parts)
            print(f"✅ Deal context built for '{deal.deal_name}': "
                  f"{len(dynamic_facts)} facts, {len(faqs)} FAQs")
            return context

        except Exception as e:
            print(f"⚠️  Error building deal context for deal_id={deal_id}: {e}")
            return ""


    # ── Tone Rules ────────────────────────────────────────────────────────────

    def get_tone_rules(self, deal_id: Optional[int] = None) -> str:
        """
        Load tone and compliance rules from odp_tone_rules.
        Always loads global rules; also loads deal-specific rules if deal_id is given.

        Args:
            deal_id: Optional deal ID for deal-specific rules

        Returns:
            Formatted string of tone/compliance rules for injection into system prompt.
        """
        try:
            # Load global rules first (highest priority always)
            query = ToneRule.query.filter_by(
                is_active=True,
                scope="global"
            ).order_by(ToneRule.priority.desc())

            global_rules = query.all()

            deal_rules = []
            if deal_id:
                deal_rules = ToneRule.query.filter_by(
                    is_active=True,
                    scope="deal",
                    deal_id=deal_id
                ).order_by(ToneRule.priority.desc()).all()

            all_rules = global_rules + deal_rules

            if not all_rules:
                # Fallback minimal tone if no rules in DB yet
                return (
                    "- Be direct, warm, and confident. Speak as 'we' (the firm).\n"
                    "- Answer concisely. No corporate fluff.\n"
                    "- Always use exact numbers and terms from the documents."
                )

            parts = []
            for rule in all_rules:
                parts.append(f"- [{rule.rule_type.upper()}] {rule.rule_text}")

            return "\n".join(parts)

        except Exception as e:
            print(f"⚠️  Error loading tone rules: {e}")
            return "- Be direct, warm, and helpful."


    # ── Deal Name Lookup ───────────────────────────────────────────────────────

    def get_deal_name(self, deal_id: int) -> Optional[str]:
        """
        Get the deal name for a given deal_id.

        Args:
            deal_id: Deal ID

        Returns:
            Deal name string, or None if not found
        """
        try:
            deal = Deal.query.get(deal_id)
            return deal.deal_name if deal else None
        except Exception as e:
            print(f"⚠️  Error getting deal name: {e}")
            return None

    def get_all_deal_names(self) -> List[str]:
        """
        Get names of all active deals.
        Used for generating dynamic clarification questions.
        """
        deals = self.get_all_active_deals()
        return [d["deal_name"] for d in deals]
