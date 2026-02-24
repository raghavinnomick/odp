"""
llm_config.py — LLM Temperature & Token Settings
=================================================
Every LLM call in the bot pipeline is controlled from here.
No temperatures or max_tokens should be hardcoded inside service files.

Temperature guide (0.0 – 1.0):
  0.0 – 0.2  →  Deterministic, fact-focused (answers, info requests)
  0.3 – 0.5  →  Slightly creative, natural flow (drafts, greetings)
  0.6 – 1.0  →  High creativity (not used here — we need accuracy)

To improve output quality:
  - Lower temperature  → more predictable, less variation
  - Raise max_tokens   → longer responses allowed
  - Lower max_tokens   → forces concise output
"""

# ── Greeting Reply ─────────────────────────────────────────────────────────────
# Warm, 1–2 sentence social reply. Slightly creative but still consistent.
LLM_GREETING_TEMPERATURE = 0.5
LLM_GREETING_MAX_TOKENS  = 80

# ── Standard RAG Answer ────────────────────────────────────────────────────────
# Fact-focused Q&A. Low temperature = accurate, no hallucination.
LLM_ANSWER_TEMPERATURE = 0.2
LLM_ANSWER_MAX_TOKENS  = 900

# ── Info Request (ask team for gaps) ──────────────────────────────────────────
# Precise numbered list of ONLY missing items. Very deterministic.
LLM_INFO_REQUEST_TEMPERATURE = 0.2
LLM_INFO_REQUEST_MAX_TOKENS  = 400

# ── Draft Email ────────────────────────────────────────────────────────────────
# Full email body. Slightly creative for natural writing flow.
LLM_DRAFT_TEMPERATURE = 0.3
LLM_DRAFT_MAX_TOKENS  = 1200

# ── Clarifying Question ────────────────────────────────────────────────────────
# Single warm question. Conversational tone, short.
LLM_CLARIFICATION_TEMPERATURE = 0.5
LLM_CLARIFICATION_MAX_TOKENS  = 80

# ── Query Rewriter ─────────────────────────────────────────────────────────────
# Resolves pronouns & vague follow-ups. Near-zero creativity — just clarity.
# Max tokens is generous because user questions can be up to 1000 words.
LLM_QUERY_REWRITER_TEMPERATURE = 0.1
LLM_QUERY_REWRITER_MAX_TOKENS  = 1500

# ── Fact Extractor ─────────────────────────────────────────────────────────────
# Extracts structured JSON facts from team messages. Must be deterministic.
LLM_FACT_EXTRACTOR_TEMPERATURE = 0.0
LLM_FACT_EXTRACTOR_MAX_TOKENS  = 100
