"""
bot_config.py — API-Level Bot Settings
=======================================
Top-level configuration for the bot API layer.
Controls how many chunks to retrieve, similarity cutoff,
and how many history messages to expose via the API.

To tune RAG quality:
  - Raise BOT_DEFAULT_TOP_K        → more chunks, richer context, slower
  - Lower BOT_SIMILARITY_THRESHOLD → more results, possibly noisier
"""

# Number of document chunks returned per KB search tier
BOT_DEFAULT_TOP_K = 5

# Minimum cosine similarity for a chunk to be included (0.0 – 1.0)
BOT_SIMILARITY_THRESHOLD = 0.5

# Max messages returned by GET /bot/conversation/<session_id>
BOT_LAST_CONVERSATION_MESSAGES_LIMIT = 10

# ── Email Thread Settings ───────────────────────────────────────────────────────
# Maximum raw thread text length accepted (characters).
# Prevents extremely large pastes that would blow the LLM context window.
BOT_THREAD_MAX_LENGTH = 50_000

# Minimum raw thread text length (characters).
# Rejects obviously empty or trivial submissions.
BOT_THREAD_MIN_LENGTH = 20
