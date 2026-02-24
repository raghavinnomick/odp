"""
thresholds.py — Confidence Thresholds & Text Length Limits
===========================================================
Numerical limits that control confidence scoring, context truncation,
and history windowing. Kept separate from prompts and keyword lists
so a developer can tune these values in isolation.

Confidence scoring (from average cosine similarity of retrieved chunks):
  similarity >= HIGH_THRESHOLD    → "high"
  similarity >= MEDIUM_THRESHOLD  → "medium"
  similarity <  MEDIUM_THRESHOLD  → "low"

Text length values control how much history/context is passed to the LLM.
Larger values = richer context but higher token cost.
"""

# ── Confidence Thresholds ──────────────────────────────────────────────────────
CONFIDENCE_HIGH_THRESHOLD   = 0.85   # avg cosine similarity ≥ 0.85 → "high"
CONFIDENCE_MEDIUM_THRESHOLD = 0.70   # avg cosine similarity ≥ 0.70 → "medium"
                                      # below 0.70               → "low"

# ── History Windowing ──────────────────────────────────────────────────────────
# How many recent conversation turns are injected into LLM context.
# More turns = better continuity, higher token cost.
HISTORY_MESSAGES_FOR_ANSWER = 6    # Used during standard Q&A (Steps 14–15)
HISTORY_MESSAGES_FOR_DRAFT  = 10   # Used during draft generation (more context needed)

# ── Source Preview ─────────────────────────────────────────────────────────────
# Characters shown in the API "sources" array before truncation with "…"
SOURCE_PREVIEW_MAX_LENGTH = 200

# ── Assistant Message Truncation ───────────────────────────────────────────────
# Long assistant messages are trimmed before being added back to LLM history.
# This keeps prompt sizes manageable without losing important context.
ASSISTANT_MESSAGE_TRUNCATE_LENGTH = 600   # In history messages for Q&A
ASSISTANT_MESSAGE_DRAFT_LENGTH    = 800   # In history messages for draft generation
