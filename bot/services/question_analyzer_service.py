"""
Service: QuestionAnalyzerService

Analyzes and classifies user questions for routing and intent detection.
Handles greeting detection, question type classification, and signal detection.
"""

# Python Packages
import re
from typing import List

# Config
from ..config import service_constants





class QuestionAnalyzerService:
    """
    Analyzes user questions to classify them and detect special cases.
    Provides methods for greeting detection, question type identification,
    and signal detection for missing information.
    """

    # ── Missing Info Detection ─────────────────────────────────────────────────
    def has_missing_info_signal(self, answer: str) -> bool:
        """
        Return True if the LLM answer signals it could not confirm some facts.

        Args:
            answer: The LLM-generated answer text.

        Returns:
            Boolean indicating if missing information signals are detected.
        """
        answer_lower = answer.lower()
        return any(sig in answer_lower for sig in service_constants.MISSING_INFO_SIGNALS)



    # ── Question Type Detection ────────────────────────────────────────────────
    def is_new_question(self, question: str) -> bool:
        """
        Return True if the message looks like a new question rather than a
        supplied answer to a pending needs_info request.

        Used to prevent new questions being swallowed as answers.

        Examples that return True (new questions):
          "Whats the price per share now?"       ✓ starts with "whats"
          "What is the minimum ticket?"          ✓ starts with "what"
          "Can you tell me the structure?"       ✓ starts with "can you"
          "Do you have further info on fees?"    ✓ starts with "do you"
          "Please tell me the closing date"      ✓ starts with "please"

        Examples that return False (supplied answers):
          "Share price is ~$378"                 ✗ answer statement
          "Payment dates would be next Tuesday"  ✗ answer statement
          "$25k minimum"                         ✗ value only

        Args:
            question: The message to analyze.

        Returns:
            Boolean indicating if the message is a new question.
        """
        q = question.lower().strip()

        return any(q.startswith(starter) for starter in service_constants.QUESTION_STARTERS)



    def is_greeting(self, question: str) -> bool:
        """
        Return True if the message is pure social/small-talk with no business intent.

        Logic (in order):
          1. Exact match against known greeting phrases (e.g. "how are you").
          2. If the message starts with a greeting word, strip all social filler
             words (bot, you, are, doing, i, am, we, etc.) and check whether
             any REAL business keywords remain. If none remain → greeting.
          3. Otherwise → not a greeting.

        Examples that must return True:
          "Hello"                   ✓ exact
          "Hi there"                ✓ greeting starter, no business words
          "Hello Bot, How are you?" ✓ greeting starter, only social filler remains
          "Hey! Thanks a lot"       ✓ greeting starter, only social filler

        Examples that must return False:
          "How much is the minimum?" ✗ business keyword "minimum"
          "What is the share price?" ✗ business keyword "share", "price"
          "Hi, what is the fee?"     ✗ business keyword "fee"

        Args:
            question: The message to analyze.

        Returns:
            Boolean indicating if the message is a greeting.
        """

        # Normalise: lowercase, strip punctuation
        text = re.sub(r"[^\w\s]", " ", question.strip().lower()).strip()
        text = re.sub(r"\s+", " ", text)

        # 1. Exact match against known greeting/social phrases
        if text in service_constants.GREETING_PATTERNS:
            return True

        words = text.split()
        if not words:
            return False

        # 2. Starts with a greeting word?
        if words[0] in service_constants.GREETING_STARTERS:
            # Remove all social filler — what's left must be empty for a greeting
            remaining = [w for w in words if w not in service_constants.SOCIAL_FILLER_WORDS]
            if not remaining:
                return True  # only social words remain → pure greeting

            # Check if any remaining words are business keywords
            if any(w in service_constants.BUSINESS_KEYWORDS for w in remaining):
                return False  # business intent detected

            # Short message with no business words → treat as greeting
            if len(words) <= service_constants.GREETING_MAX_MESSAGE_LENGTH:
                return True

        return False
