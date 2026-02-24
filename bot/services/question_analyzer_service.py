"""
Service: QuestionAnalyzerService
==================================
Classifies user messages for routing and intent detection.
Handles greeting detection, question type classification, and missing-info signals.
All keyword lists live in config/keywords.py — nothing is hardcoded here.
"""

# Python Packages
import re
from typing import List

# Config
from ..config import keywords


class QuestionAnalyzerService:
    """
    Analyzes user messages to classify them and detect special cases.
    Stateless — all configuration comes from config/keywords.py.
    """

    # ── Missing Info Detection ─────────────────────────────────────────────────
    def has_missing_info_signal(self, answer: str) -> bool:
        """
        Return True if the LLM answer signals it could not confirm some facts.
        Triggers Tier 3 (Step 16) — ask the team for missing values.
        """
        answer_lower = answer.lower()
        return any(signal in answer_lower for signal in keywords.MISSING_INFO_SIGNALS)


    # ── New Question Detection ─────────────────────────────────────────────────
    def is_new_question(self, question: str) -> bool:
        """
        Return True if the message looks like a new question rather than a
        supplied answer to a pending needs_info request.

        Used to guard Step 7: prevents new questions being swallowed as answers.

        Returns True (new question):
          "What is the minimum ticket?"   ← starts with "what"
          "Can you tell me the structure?" ← starts with "can you"
          "Please share the payment dates" ← starts with "please"

        Returns False (supplied answer):
          "Share price is ~$378"           ← statement, not a question
          "$25k minimum"                   ← value only
        """
        q = question.lower().strip()
        return any(q.startswith(starter) for starter in keywords.QUESTION_STARTERS)


    # ── Greeting Detection ─────────────────────────────────────────────────────
    def is_greeting(self, question: str) -> bool:
        """
        Return True if the message is pure social/small-talk with no business intent.

        Logic (in order):
          1. Exact match against known greeting phrases (e.g. "how are you").
          2. If the message starts with a greeting word, strip all social filler
             words and check whether any REAL business keywords remain.
             If none remain → greeting.
          3. Otherwise → not a greeting.

        Returns True  (greeting):    "Hello", "Hi there", "Hello Bot, How are you?"
        Returns False (not greeting): "How much is the minimum?", "Hi, what is the fee?"
        """
        # Normalise: lowercase, strip punctuation
        text = re.sub(r"[^\w\s]", " ", question.strip().lower()).strip()
        text = re.sub(r"\s+", " ", text)

        # 1. Exact match
        if text in keywords.GREETING_PATTERNS:
            return True

        words = text.split()
        if not words:
            return False

        # 2. Starts with a greeting word?
        if words[0] in keywords.GREETING_STARTERS:
            remaining = [w for w in words if w not in keywords.SOCIAL_FILLER_WORDS]

            if not remaining:
                return True   # only social filler remains → pure greeting

            if any(w in keywords.BUSINESS_KEYWORDS for w in remaining):
                return False  # business intent detected

            # Short message with no business words → treat as greeting
            if len(words) <= keywords.GREETING_MAX_WORD_COUNT:
                return True

        return False
