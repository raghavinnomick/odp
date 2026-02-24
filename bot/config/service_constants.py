"""
Service Constants and Magic Numbers

All hardcoded configuration values, thresholds, and constants used across bot services.
Update values here instead of in service files.
"""

# ── LLM Temperature & Token Settings ───────────────────────────────────────────
# Temperature: controls creativity/randomness (0–1, lower = more deterministic)
# Max tokens: controls response length

LLM_GREETING_TEMPERATURE = 0.5  # Slightly creative but consistent
LLM_GREETING_MAX_TOKENS = 80    # Brief 1-2 sentence greeting

LLM_ANSWER_TEMPERATURE = 0.2    # Deterministic, fact-focused
LLM_ANSWER_MAX_TOKENS = 900     # Full answer with context

LLM_INFO_REQUEST_TEMPERATURE = 0.2    # Deterministic, precise
LLM_INFO_REQUEST_MAX_TOKENS = 400     # Concise list of missing items

LLM_DRAFT_TEMPERATURE = 0.3     # Slightly creative for flow
LLM_DRAFT_MAX_TOKENS = 1200     # Full email body

LLM_CLARIFICATION_TEMPERATURE = 0.5      # Warm/natural
LLM_CLARIFICATION_MAX_TOKENS = 80        # Single clarifying question

# ── Confidence Thresholds (for ContextBuilder) ─────────────────────────────────
# Derived from average cosine similarity of retrieved chunks

CONFIDENCE_HIGH_THRESHOLD = 0.85      # ≥ 0.85  → "high"
CONFIDENCE_MEDIUM_THRESHOLD = 0.70    # ≥ 0.70  → "medium"
                                        # < 0.70  → "low"

# ── Clarification Service Keywords ────────────────────────────────────────────

# Questions that REQUIRE a specific deal to answer correctly.
# If no deal_id is known, we MUST ask "which deal?" first before answering.
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
    "ebitda", "arr", "growth", "customers"
]

# Questions that are about ODP in general — no deal context needed
GENERAL_KEYWORDS = [
    "hello", "hi", "hey", "how are you",
    "what can you", "what do you", "who are you",
    "what is odp", "open doors", "what deals", "which deals",
    "what opportunities", "what investment", "what do you offer",
    "tell me about", "available deals", "current deals"
]

# ── Conversation History Settings ──────────────────────────────────────────────
# Maximum number of recent messages to include in LLM context

HISTORY_MESSAGES_FOR_ANSWER = 6      # General answer generation
HISTORY_MESSAGES_FOR_DRAFT = 10      # Draft email generation

# ── Context Formatting ────────────────────────────────────────────────────────

# Source preview length before truncation with "..."
SOURCE_PREVIEW_MAX_LENGTH = 200

# Assistant message length before truncation in history (with "...")
ASSISTANT_MESSAGE_TRUNCATE_LENGTH = 600  # For general history
ASSISTANT_MESSAGE_DRAFT_LENGTH = 800     # For draft generation context

# ── Missing Info Detection (Fallback Tone Rules) ─────────────────────────────

# Default tone if none provided from database
FALLBACK_TONE_RULES = """- Speak as 'we' (the firm). Be direct, warm, and confident.
- Answer concisely. No corporate fluff.
- Use exact numbers from context only. Never invent figures."""

# ── Question Analyzer Settings ─────────────────────────────────────────────────

# Question starter patterns for detecting new questions vs supplied answers
QUESTION_STARTERS = [
    "what", "when", "where", "which", "who", "why", "how",
    "can you", "could you", "do you", "is there", "are there",
    "tell me", "please tell", "please provide", "please share",
    "can we", "would you",
]

# Greeting starter words
GREETING_STARTERS = {
    "hello", "hi", "hey", "hiya", "howdy", "good",
    "thanks", "thank", "bye", "goodbye", "ok", "okay", "alright",
}

# Social filler words that don't indicate business intent
SOCIAL_FILLER_WORDS = {
    "hello", "hi", "hey", "hiya", "howdy", "good", "morning",
    "afternoon", "evening", "day", "how", "are", "you", "doing",
    "i", "am", "we", "bot", "there", "mate", "sir", "team",
    "thanks", "thank", "cheers", "bye", "goodbye", "ok", "okay",
    "alright", "sure", "great", "perfect", "noted", "got", "it",
    "very", "well", "fine", "nice", "sup", "whats", "up",
}

# Business keywords that indicate real intent (not just greeting)
BUSINESS_KEYWORDS = {
    "minimum", "ticket", "investment", "deal", "structure",
    "payment", "date", "fee", "fees", "carry", "valuation",
    "return", "returns", "fund", "close", "closing", "allocation",
    "share", "shares", "price", "wire", "document", "documents",
    "sign", "subscription", "information", "details", "lockup",
    "lock", "period", "spv", "equity", "preferred", "common",
    "distribution", "ebitda", "arr", "revenue", "growth",
    # Question starters that indicate information request
    "what", "when", "where", "which", "who", "why",
    "can you", "could you", "please", "tell me", "explain",
    "do you have", "is there", "are there", "how much", "how many",
    "how long", "how do",
}

# Maximum message length before requiring truncation in greeting check
GREETING_MAX_MESSAGE_LENGTH = 8  # words

# ── Missing Info Detection ─────────────────────────────────────────────────────

# Signals that indicate the LLM could not confirm some facts
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

# Greeting patterns — exact matches and keywords indicating greeting/small-talk
GREETING_PATTERNS = {
    "hello", "hi", "hey", "hiya", "howdy", "good morning", "good afternoon", "good evening", "good day", 
    "how are you", "how r u", "what's up", "whats up", "sup", "thanks", "thank you", "thank you!", 
    "thanks!", "cheers", "bye", "goodbye", "see you", "talk later", "ok", "okay", "alright", 
    "got it", "noted", "yes", "no", "sure", "great", "perfect", "sounds good",
}
