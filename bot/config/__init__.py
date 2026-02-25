"""
bot/config/__init__.py
======================
Public surface of the bot configuration package.

Config files:
  bot_config   — API-level settings (top_k, similarity threshold, message limits)
  llm_config   — LLM temperatures & max_tokens for every call type
  prompts      — ALL system prompts, user prompt templates, and section strings
  keywords     — ALL keyword lists, detection patterns, and phrase sets
  thresholds   — Confidence scoring thresholds & text truncation limits
"""

from . import bot_config
from . import llm_config
from . import prompts
from . import keywords
from . import thresholds
