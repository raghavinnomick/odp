"""
keywords.py — All Keyword Lists, Patterns & Detection Signals
=============================================================
Every word list, phrase set, and signal pattern used across the bot
services lives here. Services import from this file — no inline lists.

How to extend:
  - Add deal-specific terms to DEAL_SPECIFIC_KEYWORDS
  - Add new greeting phrases to GREETING_PATTERNS / GREETING_STARTERS
  - Add new missing-info signals to MISSING_INFO_SIGNALS
  - Add company names for query enhancement to COMPANY_NAMES
"""

# ── Deal-Specific Keywords ─────────────────────────────────────────────────────
# Questions containing these words REQUIRE a known deal_id before answering.
# Without a deal context, we must ask "which deal?" first — otherwise the LLM
# may hallucinate specific numbers for the wrong deal.
DEAL_SPECIFIC_KEYWORDS = [
    "structure", "minimum", "ticket", "fee", "fees", "carry",
    "management fee", "payment", "close", "closing", "timeline",
    "valuation", "revenue", "ipo", "lock", "lock-up", "lock up",
    "return", "returns", "share", "equity", "spv", "allocation",
    "upfront", "profit", "capital", "preferred", "common", "secondary",
    "distribution", "price", "cost", "how much", "how long",
    "invest", "investing", "investment", "deal", "terms",
    "when", "deadline", "date", "dates", "schedule",
    "documents", "sign", "dropbox", "wiring", "wire",
    "ebitda", "arr", "growth", "customers",
]

# ── General / ODP-Level Keywords ──────────────────────────────────────────────
# Questions about ODP in general — no deal context required to answer these.
GENERAL_KEYWORDS = [
    "hello", "hi", "hey", "how are you",
    "what can you", "what do you", "who are you",
    "what is odp", "open doors", "what deals", "which deals",
    "what opportunities", "what investment", "what do you offer",
    "tell me about", "available deals", "current deals",
]

# ── Missing Info Signals ───────────────────────────────────────────────────────
# Phrases that indicate the LLM could NOT confirm a fact from the KB.
# If the LLM answer contains any of these → trigger Tier 3 (ask the team).
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

# ── Question Starters ──────────────────────────────────────────────────────────
# If a user message starts with any of these, treat it as a NEW question —
# NOT as a supplied answer to a pending needs_info request.
# This guards Step 7 from swallowing real questions as answers.
QUESTION_STARTERS = [
    "what", "when", "where", "which", "who", "why", "how",
    "can you", "could you", "do you", "is there", "are there",
    "tell me", "please tell", "please provide", "please share",
    "can we", "would you",
]

# ── Greeting Detection ─────────────────────────────────────────────────────────
# Exact-match phrases that are unambiguously greetings/social messages.
GREETING_PATTERNS = {
    "hello", "hi", "hey", "hiya", "howdy",
    "good morning", "good afternoon", "good evening", "good day",
    "how are you", "how r u", "what's up", "whats up", "sup",
    "thanks", "thank you", "thank you!", "thanks!", "cheers",
    "bye", "goodbye", "see you", "talk later",
    "ok", "okay", "alright", "got it", "noted",
    "yes", "no", "sure", "great", "perfect", "sounds good",
}

# First words of a message that suggest it might be a greeting.
# If a message starts with one of these, we inspect further before deciding.
GREETING_STARTERS = {
    "hello", "hi", "hey", "hiya", "howdy", "good",
    "thanks", "thank", "bye", "goodbye", "ok", "okay", "alright",
}

# Words that carry NO business intent — pure social filler.
# After stripping these from a greeting-starter message, if nothing
# meaningful remains → treat as greeting.
SOCIAL_FILLER_WORDS = {
    "hello", "hi", "hey", "hiya", "howdy", "good", "morning",
    "afternoon", "evening", "day", "how", "are", "you", "doing",
    "i", "am", "we", "bot", "there", "mate", "sir", "team",
    "thanks", "thank", "cheers", "bye", "goodbye", "ok", "okay",
    "alright", "sure", "great", "perfect", "noted", "got", "it",
    "very", "well", "fine", "nice", "sup", "whats", "up",
}

# Words that confirm BUSINESS intent — if any remain after filtering filler,
# the message is NOT a greeting (e.g. "Hi, what is the fee?" → "fee" is here).
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

# Maximum word count for a greeting-starter message before we stop treating
# it as a greeting (e.g. a 10-word message starting with "Hi" is probably real).
GREETING_MAX_WORD_COUNT = 8

# ── Fact Extractor — Pre-screen Greetings ─────────────────────────────────────
# Messages that START with any of these AND are shorter than 30 characters
# are skipped by FactExtractorService without calling the LLM.
# Keeps the pre-screen fast and free of LLM cost for obvious non-facts.
FACT_EXTRACTOR_SKIP_STARTERS = (
    "hello", "hi ", "hey", "thanks", "thank you",
    "ok", "okay", "great", "sounds good", "noted",
)

# ── Query Enhancement — Vague Words ───────────────────────────────────────────
# If a question contains any of these, it likely needs context to be understood.
# Triggers the query rewriter to resolve pronouns / vague references.
VAGUE_WORDS = [
    "it", "that", "this", "these", "those",
    "they", "their", "them",
    "the company", "the deal", "the investment",
    "same", "also", "too",
]

# Short questions mentioning only a metric (with no company name) also need
# rewriting — e.g. "revenue?" → "What is the revenue of SpaceX?"
METRIC_ONLY_PATTERNS = [
    "revenue", "valuation", "profit", "growth",
    "ebitda", "customers", "users", "employees",
]

# ── Company Names (for Query Enhancement) ─────────────────────────────────────
# Used to detect whether a short question already names a company.
# If a short question has NO company name → likely needs rewriting.
# Expand this list as new deals are added (or replace with a DB lookup).
COMPANY_NAMES = [
    "spacex", "anthropic", "tesla", "openai", "google", "amazon",
]
