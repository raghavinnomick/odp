"""
Service: DealContextService

Loads deal metadata, tone rules, and Dynamic KB entries from the database.
Injected into every LLM prompt so the bot always works from live DB data.

Data sources
============
odp_deals               → deal names and codes (detection + context line)
odp_tone_rules          → global + deal-specific tone/compliance rules
odp_deal_dynamic_facts  → team-supplied Q&A and individual atomic facts (Tier-2 KB)

Why atomic fact decomposition matters
======================================
When a user answers a multi-part question:
  "Payment Dates would be Next Tuesday and Minimum Ticket would be $25K"

If we store this as ONE record under the full multi-part investor question
("Do you have further information on the structure, payment dates, minimum ticket?"),
then a future single-fact query like "What is the minimum check size?" has
low embedding similarity to that long question and MISSES the stored fact.

Solution: store_dynamic_kb_with_decomposition() stores:
  1. The full Q&A as one record (for multi-part queries)
  2. Each detected individual fact as a SEPARATE record with a focused question
     e.g. question="What is the minimum ticket for SpaceX?" answer="$25K"
         question="What are the payment dates for SpaceX?"  answer="Next Tuesday"

This ensures any future phrasing of a single-fact query finds the right answer.

Design decisions
================
- All DB reads wrap exceptions with rollback() to prevent InFailedSqlTransaction.
- search_dynamic_kb() returns results formatted to be placed FIRST in LLM context
  (before static KB chunks) so team corrections override document content.
- approval_status is set to 'approved' immediately for team-member answers.
"""

# Python Packages
from typing import List, Dict, Optional

# Database
from sqlalchemy import text as sql_text
from ...config.database import db

# Models
from ...models.odp_deal import Deal
from ...models.odp_tone_rule import ToneRule
from ...models.odp_deal_dynamic_fact import DealDynamicFact

# Vendors
from ...vendors.openai import EmbeddingService

# Config
from ..config import bot_config
from ..config import prompts





class DealContextService:
    """
    Provides deal metadata, tone rules, and Tier-2 Dynamic KB access.
    All methods return safe fallback values on DB error.
    """

    def __init__(self):
        """ Initialize the DealContextService with an EmbeddingService instance. """

        self.embedding_service = EmbeddingService()



    # ── Deal Discovery ─────────────────────────────────────────────────────────
    def get_all_active_deals(self) -> List[Dict]:
        """Return all active deals as [{deal_id, deal_name, deal_code}, ...]."""

        try:
            deals = Deal.query.filter_by(status = True).all()
            return [
                {"deal_id": d.deal_id, "deal_name": d.deal_name, "deal_code": d.deal_code}
                for d in deals
            ]

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  get_all_active_deals failed: {exc}")
            return []


    def detect_deal_in_text(self, text: str, all_deals: List[Dict]) -> Optional[int]:
        """Return deal_id if any deal name/code appears in text (case-insensitive)."""

        text_lower = text.lower()
        for deal in all_deals:
            if (deal["deal_name"].lower() in text_lower or
                    deal["deal_code"].lower() in text_lower):
                print(f"🔍 Deal detected: '{deal['deal_name']}' → deal_id = {deal['deal_id']}")
                return deal["deal_id"]
        return None


    def get_deal_name(self, deal_id: int) -> Optional[str]:
        """Return the deal_name for deal_id, or None."""
        try:
            deal = Deal.query.get(deal_id)
            return deal.deal_name if deal else None
        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  get_deal_name failed (deal_id={deal_id}): {exc}")
            return None


    def get_all_deal_names(self) -> List[str]:
        """Return names of all active deals."""
        return [d["deal_name"] for d in self.get_all_active_deals()]


    def build_deal_context(self, deal_id: int) -> str:
        """
        Build a one-line deal identifier for the LLM prompt.
        Returns "ACTIVE DEAL: <name> (code: <code>)" or "" on error.
        """
        try:
            deal = Deal.query.get(deal_id)
            if not deal:
                return ""
            return f"ACTIVE DEAL: {deal.deal_name} (code: {deal.deal_code})"
        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  build_deal_context failed (deal_id={deal_id}): {exc}")
            return ""



    # ── Tone Rules ─────────────────────────────────────────────────────────────
    def get_tone_rules(self, deal_id: Optional[int] = None) -> str:
        """
        Load tone and compliance rules from odp_tone_rules.
        Global rules always loaded; deal-specific rules added when deal_id given.
        Falls back to minimal hardcoded default if table is empty.
        """
        try:
            global_rules = (
                ToneRule.query
                .filter_by(is_active = True, scope = "global")
                .order_by(ToneRule.priority.desc())
                .all()
            )
            deal_rules = []
            if deal_id:
                deal_rules = (
                    ToneRule.query
                    .filter_by(is_active = True, scope = "deal", deal_id = deal_id)
                    .order_by(ToneRule.priority.desc())
                    .all()
                )

            all_rules = global_rules + deal_rules
            if not all_rules:
                print("⚠️  No tone rules in DB — using minimal fallback.")
                return prompts.DEFAULT_TONE_RULES

            return "\n".join(f"- [{r.rule_type.upper()}] {r.rule_text}" for r in all_rules)

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  get_tone_rules failed: {exc}")
            return "- Be direct, warm, and helpful."



    # ── Dynamic KB — Tier-2 Search ─────────────────────────────────────────────
    def search_dynamic_kb(
        self,
        question: str,
        deal_id: Optional[int] = None,
        top_k: int = 5,
        similarity_threshold: float = bot_config.BOT_SIMILARITY_THRESHOLD
    ) -> str:
        """
        Search odp_deal_dynamic_facts for entries that match *question*.

        Two passes:
          1. Vector similarity on embedding (Q&A records with embeddings)
          2. All structured fact_key/fact_value records for the deal

        Results are formatted and returned to be placed FIRST in the LLM context
        block (before static KB chunks), so team corrections override documents.

        Returns "" if nothing found or on error.
        """
        parts = []

        # ── Pass 1: Vector similarity over Q&A records ─────────────────────────
        try:
            embedding = self.embedding_service.generate_embedding(question)
            emb_str   = "[" + ",".join(map(str, embedding)) + "]"

            if deal_id:
                sql = sql_text("""
                    SELECT question, answer,
                           1 - (embedding <=> CAST(:emb AS vector)) AS similarity
                    FROM odp_deal_dynamic_facts
                    WHERE deal_id = :deal_id
                      AND approval_status = 'approved'
                      AND embedding IS NOT NULL
                      AND question IS NOT NULL
                      AND (1 - (embedding <=> CAST(:emb AS vector))) >= :threshold
                    ORDER BY embedding <=> CAST(:emb AS vector)
                    LIMIT :top_k
                """)
                qa_rows = db.session.execute(sql, {
                    "emb": emb_str, "deal_id": deal_id,
                    "threshold": similarity_threshold, "top_k": top_k
                }).fetchall()
            else:
                sql = sql_text("""
                    SELECT question, answer,
                           1 - (embedding <=> CAST(:emb AS vector)) AS similarity
                    FROM odp_deal_dynamic_facts
                    WHERE approval_status = 'approved'
                      AND embedding IS NOT NULL
                      AND question IS NOT NULL
                      AND (1 - (embedding <=> CAST(:emb AS vector))) >= :threshold
                    ORDER BY embedding <=> CAST(:emb AS vector)
                    LIMIT :top_k
                """)
                qa_rows = db.session.execute(sql, {
                    "emb": emb_str,
                    "threshold": similarity_threshold,
                    "top_k": top_k
                }).fetchall()

            if qa_rows:
                print(f"📚 Dynamic KB Q&A: {len(qa_rows)} entries matched")
                parts.append("── TEAM-SUPPLIED FACTS (override document values below) ──")
                for row in qa_rows:
                    parts.append(f"Q: {row[0]}")
                    parts.append(f"A: {row[1]}")
                    parts.append("")

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  Dynamic KB vector search failed: {exc}")

        # ── Pass 2: Structured fact_key/fact_value records ─────────────────────
        try:
            query = (
                DealDynamicFact.query
                .filter_by(approval_status="approved")
                .filter(DealDynamicFact.fact_key.isnot(None))
                .filter(DealDynamicFact.fact_value.isnot(None))
            )
            if deal_id:
                query = query.filter_by(deal_id=deal_id)
            fact_rows = query.all()

            if fact_rows:
                print(f"📚 Dynamic KB facts: {len(fact_rows)} structured facts")
                if not parts:
                    parts.append("── TEAM-SUPPLIED FACTS (override document values below) ──")
                for f in fact_rows:
                    label = f.fact_key.replace("_", " ").title()
                    parts.append(f"{label}: {f.fact_value}")
                parts.append("")

        except Exception as exc:
            db.session.rollback()
            print(f"⚠️  Dynamic KB fact lookup failed: {exc}")

        return "\n".join(parts) if parts else ""

    # ── Dynamic KB — Store (Full Q&A only) ────────────────────────────────────

    def store_dynamic_kb(
        self,
        deal_id: int,
        question: str,
        answer: str,
        created_by: str
    ) -> Optional[DealDynamicFact]:
        """
        Persist a single Q&A pair with its embedding.
        Use store_dynamic_kb_with_decomposition() for user-supplied answers
        so individual facts are stored for precise future retrieval.
        """
        try:
            print(f"💾 Storing to Dynamic KB | deal_id={deal_id}")
            print(f"   Q: {question[:80]}")
            print(f"   A: {answer[:80]}")

            combined  = f"{question} {answer}"
            embedding = self.embedding_service.generate_embedding(combined)

            entry = DealDynamicFact(
                deal_id         = deal_id,
                question        = question,
                answer          = answer,
                embedding       = embedding,
                approval_status = "approved"
            )
            db.session.add(entry)
            db.session.commit()
            db.session.refresh(entry)

            print(f"✅ Saved to odp_deal_dynamic_facts | id={entry.id} | deal_id={deal_id}")
            return entry

        except Exception as exc:
            db.session.rollback()
            print(f"❌ store_dynamic_kb FAILED (deal_id={deal_id}): {exc}")
            import traceback
            traceback.print_exc()
            return None

    # ── Dynamic KB — Store with Decomposition ─────────────────────────────────

    def store_dynamic_kb_with_decomposition(
        self,
        deal_id: int,
        investor_question: str,
        user_answer: str,
        created_by: str
    ) -> None:
        """
        Store a user-supplied answer in three ways for maximum future retrieval:

        1. Full Q&A record — original investor question + full user answer.
        2. Atomic fact records — one record per detected sub-fact, each with a
           short focused question so single-fact queries find them precisely.
        3. Fallback fact_key record — when no atomic pattern matches, stores a
           fact_key/fact_value record with a derived snake_case key so the fact
           is always searchable even for brand-new topics.

        Example:
          investor_question = "Whats the price per share now?"
          user_answer = "Share Price is ~$378."
          → Full Q&A stored
          → Atomic: Q="What is the current share price for SpaceX?" A="~$378."
            (because "price per share" matches the share_price pattern)

        Args:
            deal_id:           The active deal.
            investor_question: The original investor question.
            user_answer:       The team member's reply.
            created_by:        user_id of the team member.
        """
        import re as _re
        print(f"\n📦 Storing to Dynamic KB | deal_id={deal_id}")
        print(f"   Q: {investor_question[:100]}")
        print(f"   A: {user_answer[:100]}")

        # 1. Full Q&A record
        self.store_dynamic_kb(
            deal_id    = deal_id,
            question   = investor_question,
            answer     = user_answer,
            created_by = created_by
        )

        # 2. Atomic facts
        atomic_facts = self._extract_atomic_facts(
            investor_question = investor_question,
            user_answer       = user_answer,
            deal_id           = deal_id
        )

        if atomic_facts:
            for fact_question, fact_answer in atomic_facts:
                self.store_dynamic_kb(
                    deal_id    = deal_id,
                    question   = fact_question,
                    answer     = fact_answer,
                    created_by = created_by
                )
                print(f"⚛️  Atomic stored: Q=\"{fact_question}\" A=\"{fact_answer}\"")
        else:
            # 3. Fallback: fact_key / fact_value record
            fact_key = self._derive_fact_key(investor_question)
            if fact_key:
                try:
                    print(f"🔑 No pattern — storing fact_key='{fact_key}' value='{user_answer[:60]}'")
                    combined  = f"{investor_question} {user_answer}"
                    embedding = self.embedding_service.generate_embedding(combined)
                    entry = DealDynamicFact(
                        deal_id         = deal_id,
                        question        = investor_question,
                        answer          = user_answer,
                        fact_key        = fact_key,
                        fact_value      = user_answer.strip(),
                        embedding       = embedding,
                        approval_status = "approved"
                    )
                    db.session.add(entry)
                    db.session.commit()
                    db.session.refresh(entry)
                    print(f"✅ Fallback fact saved | id={entry.id} | fact_key={fact_key}")
                except Exception as exc:
                    db.session.rollback()
                    print(f"❌ Fallback fact storage failed: {exc}")

    def _derive_fact_key(self, question: str) -> Optional[str]:
        """
        Derive a snake_case fact_key from a question string.
        Used as fallback when no FACT_PATTERN matches.

        Examples:
          "Whats the price per share now?"  → "share_price"
          "What is the IRR?"                → "irr"
          "How long is the lock-up?"        → "lockup_period"
        """
        import re as _re
        q = question.lower().strip()

        KEY_MAPPINGS = [
            (["price per share", "share price", "stock price", "per share",
              "price of share", "current price", "cost per share"], "share_price"),
            (["minimum ticket", "min ticket", "check size", "minimum check",
              "minimum investment", "min check"], "minimum_ticket"),
            (["payment date", "wire date", "payment deadline",
              "payment schedule"], "payment_dates"),
            (["management fee", "carry", "carried interest"], "fees_and_carry"),
            (["lock-up", "lockup", "lock up", "holding period"], "lockup_period"),
            (["closing date", "close date", "final close"], "closing_date"),
            (["valuation", "company value", "pre-money", "post-money"], "valuation"),
            (["irr", "internal rate of return"], "irr"),
            (["allocation", "available allocation"], "allocation"),
            (["distribution", "distribution schedule"], "distributions"),
            (["return", "expected return", "target return"], "expected_return"),
            (["fee", "fees"], "fees"),
            (["structure", "investment structure"], "deal_structure"),
        ]

        for keywords, key in KEY_MAPPINGS:
            if any(kw in q for kw in keywords):
                return key

        # Generic fallback: extract meaningful words
        stopwords = {
            "what", "whats", "is", "the", "are", "how", "much", "many",
            "long", "do", "you", "have", "can", "tell", "me", "about",
            "for", "of", "a", "an", "now", "current", "currently", "any"
        }
        words = _re.sub(r"[^\w\s]", " ", q).split()
        meaningful = [w for w in words if w not in stopwords and len(w) > 2]
        if meaningful:
            return "_".join(meaningful[:3])

        return None

    # ── Private: Atomic Fact Extractor ────────────────────────────────────────

    def _extract_atomic_facts(
        self,
        investor_question: str,
        user_answer: str,
        deal_id: int
    ) -> List[tuple]:
        """
        Parse user_answer into (focused_question, value) pairs.

        Strategy:
          - Define a set of fact topics with their question template and
            keywords that indicate the value follows in the answer text.
          - Scan user_answer for each keyword and extract the following value.
          - Only emit a fact if the investor_question also mentions that topic,
            confirming the user was answering that specific sub-question.

        Returns:
            List of (question_str, value_str) tuples.
            Empty list if no atomic facts could be extracted.
        """
        deal_name = self.get_deal_name(deal_id) or "the deal"
        q_lower   = investor_question.lower()
        a_lower   = user_answer.lower()
        facts     = []

        # Each entry: (topic_keywords_in_question, answer_signal_keywords, question_template)
        # topic_keywords:  must appear in investor_question for this topic to be relevant
        # answer_signals:  phrases in user_answer that precede the actual value
        # question_tmpl:   the focused standalone question to store
        FACT_PATTERNS = [
            (
                ["minimum", "ticket", "check size", "min ticket", "minimum ticket",
                 "minimum check", "min check", "minimum investment"],
                ["minimum ticket", "min ticket", "minimum check", "min check",
                 "minimum is", "minimum would be", "minimum:", "ticket is",
                 "ticket would be", "ticket:", "check size is", "check size would be",
                 "check size:", "minimum investment"],
                f"What is the minimum ticket size for {deal_name}?"
            ),
            (
                ["payment date", "payment dates", "wire date", "wire dates",
                 "payment deadline", "when to pay", "payment schedule"],
                ["payment date", "payment dates", "wire date", "wire by",
                 "payment is", "payment would be", "payment:", "dates would be",
                 "date would be", "dates are", "date is"],
                f"What are the payment dates for {deal_name}?"
            ),
            (
                ["structure", "investment structure", "deal structure",
                 "how is it structured", "investing structure"],
                ["structure is", "structure would be", "structured as",
                 "structured through", "investment structure"],
                f"What is the investment structure for {deal_name}?"
            ),
            (
                ["fee", "fees", "management fee", "carry", "carried interest"],
                ["fee is", "fees are", "management fee", "carry is",
                 "carry would be", "carried interest"],
                f"What are the fees and carry for {deal_name}?"
            ),
            (
                ["lockup", "lock-up", "lock up", "lock period", "holding period"],
                ["lockup is", "lock-up is", "lock up is", "lockup period",
                 "holding period", "locked for", "locked up for"],
                f"What is the lock-up period for {deal_name}?"
            ),
            (
                ["closing date", "close date", "deadline", "final close",
                 "closing deadline"],
                ["closing date", "close date", "deadline is", "closes on",
                 "closing on", "final close"],
                f"What is the closing date for {deal_name}?"
            ),
            (
                ["valuation", "pre-money", "post-money", "company valuation"],
                ["valuation is", "valued at", "valuation:", "pre-money",
                 "post-money"],
                f"What is the valuation of {deal_name}?"
            ),
            # ── Share / stock price ──────────────────────────────────────────
            (
                ["price per share", "share price", "stock price", "per share",
                 "price of share", "share cost", "price now", "current price",
                 "cost per share"],
                ["share price is", "share price:", "price per share is",
                 "price per share:", "price is", "price would be", "priced at",
                 "currently priced", "trading at", "cost is", "price now"],
                f"What is the current share price for {deal_name}?"
            ),
            # ── Allocation / availability ────────────────────────────────────
            (
                ["allocation", "how much is available", "available allocation",
                 "total allocation", "remaining allocation"],
                ["allocation is", "allocation:", "available allocation",
                 "total allocation", "we have", "remaining is"],
                f"What is the available allocation for {deal_name}?"
            ),
            # ── Return / IRR / multiple ──────────────────────────────────────
            (
                ["return", "irr", "multiple", "expected return", "target return",
                 "projected return"],
                ["return is", "irr is", "expected return", "target return",
                 "projected return", "multiple is", "multiple would be"],
                f"What is the expected return or IRR for {deal_name}?"
            ),
            # ── Distribution schedule ────────────────────────────────────────
            (
                ["distribution", "distributions", "distribution schedule",
                 "when are distributions", "distribution frequency"],
                ["distribution is", "distributions are", "distributed",
                 "distribution schedule", "distributions would be"],
                f"What is the distribution schedule for {deal_name}?"
            ),
        ]

        for topic_keywords, answer_signals, question_template in FACT_PATTERNS:
            # Check that this topic was part of the original investor question
            topic_relevant = any(kw in q_lower for kw in topic_keywords)
            if not topic_relevant:
                continue

            # Find the value in the user's answer
            value = self._extract_value_after_signal(a_lower, user_answer, answer_signals)
            if value:
                facts.append((question_template, value))

        return facts

    def _extract_value_after_signal(
        self,
        answer_lower: str,
        answer_original: str,
        signals: List[str]
    ) -> Optional[str]:
        """
        Find the first signal phrase in answer_lower, then return the following
        text (up to the next clause boundary) from answer_original.

        Returns None if no signal found.

        Example:
          answer = "Payment Dates would be Next Tuesday and Minimum Ticket $25K"
          signals = ["payment dates", "payment date"]
          → finds "payment dates would be" at position 0
          → extracts "Next Tuesday" (stops at " and ")
        """
        for signal in signals:
            idx = answer_lower.find(signal)
            if idx == -1:
                continue

            # Move past the signal phrase
            start = idx + len(signal)
            remaining_lower  = answer_lower[start:]
            remaining_original = answer_original[start:]

            # Skip connector words ("is", "are", "would be", ":", " -")
            connectors = [" would be ", " is ", " are ", ": ", " - ", " = "]
            for conn in connectors:
                if remaining_lower.startswith(conn):
                    remaining_lower    = remaining_lower[len(conn):]
                    remaining_original = remaining_original[len(conn):]
                    break
            else:
                # Skip any leading whitespace/punctuation
                stripped = remaining_original.lstrip(" :=-")
                remaining_original = stripped
                remaining_lower    = remaining_lower.lstrip(" :=-")

            if not remaining_original.strip():
                continue

            # Stop at clause boundaries: comma, " and ", " or ", newline, period
            terminators = [" and ", ", ", "\n", ". ", " or ", "; "]
            end = len(remaining_original)
            for term in terminators:
                pos = remaining_lower.find(term)
                if 0 < pos < end:
                    end = pos

            value = remaining_original[:end].strip()
            if value and len(value) >= 2:
                return value

        return None
