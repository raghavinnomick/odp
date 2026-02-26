"""
fact_patterns.py — Deal Fact Extraction Patterns
==================================================
All structured fact-extraction logic used by DealContextService lives here.

Two groups:
  KEY_MAPPINGS   — maps question phrases → snake_case fact_key strings
                   used by _derive_fact_key() as a last-resort fallback.
  FACT_PATTERNS  — used by _extract_atomic_facts() to decompose multi-part
                   user answers into separate atomic fact records.

How to extend:
  - Add a new KEY_MAPPINGS entry: (list_of_phrases, "fact_key_string")
  - Add a new FACT_PATTERNS entry:
      (topic_keywords_in_question, answer_signal_keywords, "{deal_name}" template)
  - Keep question templates natural and specific — they become the stored
    question used for future vector similarity searches.
"""

# ── Fact Key Mappings ──────────────────────────────────────────────────────────
# Maps question phrase substrings → canonical snake_case fact_key.
# First match wins. Used by _derive_fact_key() when no FACT_PATTERN fires.
#
# Format: (list_of_trigger_phrases, "fact_key_string")
KEY_MAPPINGS = [
    (
        ["price per share", "share price", "stock price", "per share",
         "price of share", "current price", "cost per share"],
        "share_price"
    ),
    (
        ["minimum ticket", "min ticket", "check size", "minimum check",
         "minimum investment", "min check"],
        "minimum_ticket"
    ),
    (
        ["payment date", "wire date", "payment deadline", "payment schedule"],
        "payment_dates"
    ),
    (
        ["management fee", "carry", "carried interest"],
        "fees_and_carry"
    ),
    (
        ["lock-up", "lockup", "lock up", "holding period"],
        "lockup_period"
    ),
    (
        ["closing date", "close date", "final close"],
        "closing_date"
    ),
    (
        ["valuation", "company value", "pre-money", "post-money"],
        "valuation"
    ),
    (
        ["irr", "internal rate of return"],
        "irr"
    ),
    (
        ["allocation", "available allocation"],
        "allocation"
    ),
    (
        ["distribution", "distribution schedule"],
        "distributions"
    ),
    (
        ["return", "expected return", "target return"],
        "expected_return"
    ),
    (
        ["fee", "fees"],
        "fees"
    ),
    (
        ["structure", "investment structure"],
        "deal_structure"
    ),
]

# ── Atomic Fact Patterns ───────────────────────────────────────────────────────
# Each entry is a 3-tuple:
#   (topic_keywords, answer_signals, question_template)
#
# topic_keywords   : if ANY appear in the investor's question → this topic is relevant
# answer_signals   : phrases in the user's answer that precede the actual value
# question_template: focused question stored in Dynamic KB; use {deal_name} placeholder
#
# IMPORTANT: question_template must contain {deal_name} so the service can fill it.
FACT_PATTERNS = [
    (
        ["minimum", "ticket", "check size", "min ticket", "minimum ticket",
         "minimum check", "min check", "minimum investment"],
        ["minimum ticket", "min ticket", "minimum check", "min check",
         "minimum is", "minimum would be", "minimum:", "ticket is",
         "ticket would be", "ticket:", "check size is", "check size would be",
         "check size:", "minimum investment"],
        "What is the minimum ticket size for {deal_name}?"
    ),
    (
        ["payment date", "payment dates", "wire date", "wire dates",
         "payment deadline", "when to pay", "payment schedule"],
        ["payment date", "payment dates", "wire date", "wire by",
         "payment is", "payment would be", "payment:", "dates would be",
         "date would be", "dates are", "date is"],
        "What are the payment dates for {deal_name}?"
    ),
    (
        ["structure", "investment structure", "deal structure",
         "how is it structured", "investing structure"],
        ["structure is", "structure would be", "structured as",
         "structured through", "investment structure"],
        "What is the investment structure for {deal_name}?"
    ),
    (
        ["fee", "fees", "management fee", "carry", "carried interest"],
        ["fee is", "fees are", "management fee", "carry is",
         "carry would be", "carried interest"],
        "What are the fees and carry for {deal_name}?"
    ),
    (
        ["lockup", "lock-up", "lock up", "lock period", "holding period"],
        ["lockup is", "lock-up is", "lock up is", "lockup period",
         "holding period", "locked for", "locked up for"],
        "What is the lock-up period for {deal_name}?"
    ),
    (
        ["closing date", "close date", "deadline", "final close",
         "closing deadline"],
        ["closing date", "close date", "deadline is", "closes on",
         "closing on", "final close"],
        "What is the closing date for {deal_name}?"
    ),
    (
        ["valuation", "pre-money", "post-money", "company valuation"],
        ["valuation is", "valued at", "valuation:", "pre-money", "post-money"],
        "What is the valuation of {deal_name}?"
    ),
    (
        ["price per share", "share price", "stock price", "per share",
         "price of share", "share cost", "price now", "current price",
         "cost per share"],
        ["share price is", "share price:", "price per share is",
         "price per share:", "price is", "price would be", "priced at",
         "currently priced", "trading at", "cost is", "price now"],
        "What is the current share price for {deal_name}?"
    ),
    (
        ["allocation", "how much is available", "available allocation",
         "total allocation", "remaining allocation"],
        ["allocation is", "allocation:", "available allocation",
         "total allocation", "we have", "remaining is"],
        "What is the available allocation for {deal_name}?"
    ),
    (
        ["return", "irr", "multiple", "expected return", "target return",
         "projected return"],
        ["return is", "irr is", "expected return", "target return",
         "projected return", "multiple is", "multiple would be"],
        "What is the expected return or IRR for {deal_name}?"
    ),
    (
        ["distribution", "distributions", "distribution schedule",
         "when are distributions", "distribution frequency"],
        ["distribution is", "distributions are", "distributed",
         "distribution schedule", "distributions would be"],
        "What is the distribution schedule for {deal_name}?"
    ),
]
