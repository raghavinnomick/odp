"""
Service: AnswerGenerator
========================
Generates all LLM responses in the bot pipeline.

Modes
-----
greeting  Warm, brief social reply — no RAG.
answer    RAG Q&A. Dynamic KB (team facts) OVERRIDES document passages.
ask       Ask team ONLY for the specific values the bot could NOT confirm.
          Receives partial_answer so it never re-asks confirmed items.
draft     Draft a reply email using team-supplied info + KB context + tone.

Critical priority rule
----------------------
The LLM is explicitly told:
  "TEAM-SUPPLIED FACTS come first and OVERRIDE document passages.
   If a team fact says $25k but a document says $50k — use $25k."

This is enforced in two ways:
  1. Dynamic KB context is placed BEFORE static KB context in the prompt.
  2. The system prompt contains explicit override instructions (ANSWER_MODE_INSTRUCTIONS).

Tone enforcement
----------------
TONE_CONSISTENCY_BLOCK is injected into EVERY system prompt (all modes).
It enforces three rules:
  (a) Consistent tone across all sentences in a response.
  (b) No random tone variation between paragraphs.
  (c) Progressive adaptation to match historical email/conversation style.

The tone block is placed AFTER the tone rules and BEFORE task instructions
so the LLM treats tone as a hard constraint that task logic works within.

All tone comes from odp_tone_rules via the tone_rules parameter.
Zero hardcoded tone or figures in this file — everything is in config/.
"""

# Python Packages
from typing import List, Dict, Optional

# Vendors
from ...vendors import ChatService

# Config
from ..config import prompts, llm_config, thresholds


class AnswerGenerator:
    """
    LLM wrapper for all bot response types.
    Stateless — all context is passed in per call. Nothing hardcoded here.
    """

    def __init__(self):
        self.chat_service = ChatService()


    # ── Greeting Reply ─────────────────────────────────────────────────────────
    def generate_greeting_reply(self, question: str, tone_rules: str = None) -> str:
        """
        Generate a natural, warm greeting (1–2 sentences).
        No RAG context needed. Tone from DB via tone_rules.
        """
        print("👋 Generating greeting reply...")

        system_prompt = prompts.GREETING_SYSTEM_PROMPT.format(
            tone_section           = self._resolve_tone(tone_rules),
            tone_consistency_block = prompts.TONE_CONSISTENCY_BLOCK
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": question}
        ]

        return self.chat_service.generate_response(
            messages    = messages,
            temperature = llm_config.LLM_GREETING_TEMPERATURE,
            max_tokens  = llm_config.LLM_GREETING_MAX_TOKENS
        ).strip()


    # ── Standard RAG Answer ────────────────────────────────────────────────────
    def generate_answer(
        self,
        question: str,
        context: str,
        tone_rules: str = None,
        deal_context: str = None,
        thread_context: str = None,
        history_messages: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate a RAG answer from the provided context.

        Context is pre-merged with Dynamic KB FIRST, Static KB second.
        System prompt reinforces that team-supplied facts override documents.
        Thread context (if provided) is injected before KB so the LLM knows
        the investor's situation before reading documents.
        NEVER invents figures not present in context.
        """
        print("🤖 Generating answer...")

        system_prompt = self._build_system_prompt(tone_rules=tone_rules, mode="answer")
        messages      = [{"role": "system", "content": system_prompt}]

        if history_messages:
            for msg in history_messages:
                role, content = msg.get("role", "user"), msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
            print(f"   📜 Injected {len(history_messages)} history turns")

        messages.append({
            "role":    "user",
            "content": self._format_answer_prompt(question, context, deal_context, thread_context)
        })

        return self.chat_service.generate_response(
            messages    = messages,
            temperature = llm_config.LLM_ANSWER_TEMPERATURE,
            max_tokens  = llm_config.LLM_ANSWER_MAX_TOKENS
        )


    # ── Info Request (ask for gaps only) ──────────────────────────────────────
    def generate_info_request(
        self,
        original_question: str,
        partial_answer: str,
        tone_rules: str = None,
        thread_context: str = None,
        history_messages: Optional[List[Dict]] = None
    ) -> str:
        """
        Ask the team ONLY for facts that could NOT be confirmed.

        Receives partial_answer so the LLM sees what was already confirmed
        and does NOT re-ask for those items.
        Thread context is included so the LLM can reference the investor by name.
        """
        print("📋 Generating info request (gaps only)...")

        system_prompt = self._build_system_prompt(tone_rules=tone_rules, mode="ask")
        messages      = [{"role": "system", "content": system_prompt}]

        if history_messages:
            for msg in history_messages:
                role, content = msg.get("role", "user"), msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        # Build user prompt — prepend thread context if available
        user_prompt = ""
        if thread_context and thread_context.strip():
            user_prompt += thread_context.strip() + "\n\n"

        user_prompt += prompts.INFO_REQUEST_USER_PROMPT.format(
            original_question = original_question,
            partial_answer    = partial_answer
        )
        messages.append({"role": "user", "content": user_prompt})

        return self.chat_service.generate_response(
            messages    = messages,
            temperature = llm_config.LLM_INFO_REQUEST_TEMPERATURE,
            max_tokens  = llm_config.LLM_INFO_REQUEST_MAX_TOKENS
        )


    # ── Draft Email ────────────────────────────────────────────────────────────
    def generate_draft_email(
        self,
        original_investor_question: str,
        user_supplied_info: str,
        tone_rules: str = None,
        deal_context: str = None,
        doc_context: str = None,
        thread_context: str = None,
        history_messages: Optional[List[Dict]] = None
    ) -> str:
        """
        Draft a reply email to an investor.
        Uses team-supplied info, dynamic KB (team corrections), and static KB.
        Thread context (when available) lets the LLM match the investor's style.
        Tone from DB. No hardcoded figures.
        """
        print("✉️  Generating draft email...")

        system_prompt = self._build_system_prompt(tone_rules=tone_rules, mode="draft")
        messages      = [{"role": "system", "content": system_prompt}]

        if history_messages:
            for msg in history_messages:
                role, content = msg.get("role", "user"), msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        messages.append({
            "role":    "user",
            "content": self._format_draft_prompt(
                original_investor_question, user_supplied_info,
                deal_context, doc_context, thread_context
            )
        })

        return self.chat_service.generate_response(
            messages    = messages,
            temperature = llm_config.LLM_DRAFT_TEMPERATURE,
            max_tokens  = llm_config.LLM_DRAFT_MAX_TOKENS
        )


    # ── Private: System Prompt Builder ────────────────────────────────────────
    def _resolve_tone(self, tone_rules: str = None) -> str:
        """Return tone section from DB if available, fallback otherwise."""
        if tone_rules and tone_rules.strip():
            return tone_rules.strip()
        print("⚠️  No tone rules in DB — using fallback.")
        return prompts.DEFAULT_TONE_RULES

    def _build_system_prompt(self, tone_rules: str = None, mode: str = "answer") -> str:
        """
        Assemble system prompt for the given mode.

        Order: role → tone rules → tone consistency block → task instructions.
        Tone is always declared before task so it acts as a hard constraint.
        """
        mode_map = {
            "ask":   prompts.ASK_MODE_INSTRUCTIONS,
            "draft": prompts.DRAFT_MODE_INSTRUCTIONS,
        }
        mode_instructions = mode_map.get(mode, prompts.ANSWER_MODE_INSTRUCTIONS)

        return prompts.SYSTEM_PROMPT_TEMPLATE.format(
            tone_section           = self._resolve_tone(tone_rules),
            tone_consistency_block = prompts.TONE_CONSISTENCY_BLOCK,
            mode_instructions      = mode_instructions
        )


    # ── Private: Prompt Formatters ─────────────────────────────────────────────
    def _format_answer_prompt(
        self,
        question: str,
        doc_context: str,
        deal_context: str = None,
        thread_context: str = None
    ) -> str:
        """
        Build user-turn prompt for answer mode.

        Order:
          1. Thread context (investor background — highest priority for personalisation)
          2. Deal context (active deal identifier)
          3. KB context (dynamic facts first, static KB second)
          4. Question footer
        """
        parts = []

        # Thread context FIRST — investor context before any KB content
        if thread_context and thread_context.strip():
            parts += [thread_context.strip(), ""]

        if deal_context and deal_context.strip():
            parts += [prompts.ANSWER_SECTION_DEAL, deal_context.strip(), ""]

        if doc_context and doc_context.strip():
            parts += [prompts.ANSWER_SECTION_KB, doc_context.strip(), ""]
        else:
            parts += [prompts.ANSWER_SECTION_NO_KB, prompts.ANSWER_NO_KB_MESSAGE, ""]

        parts.append(prompts.ANSWER_FOOTER_TEMPLATE.format(question=question))
        return "\n".join(parts)

    def _format_draft_prompt(
        self,
        investor_question: str,
        user_info: str,
        deal_context: str = None,
        doc_context: str = None,
        thread_context: str = None
    ) -> str:
        """
        Build user-turn prompt for draft mode.

        Order:
          1. Thread context (investor style — so the draft mirrors their tone)
          2. Investor's question
          3. Team-supplied info
          4. Deal context
          5. KB context
          6. Draft instruction footer
        """
        parts = []

        # Thread context FIRST — style reference before any content
        if thread_context and thread_context.strip():
            parts += [thread_context.strip(), ""]

        parts += [
            prompts.DRAFT_SECTION_QUESTION,
            investor_question.strip(),
            "",
            prompts.DRAFT_SECTION_TEAM_INFO,
            user_info.strip() if user_info else "(none provided)",
            "",
        ]

        if deal_context and deal_context.strip():
            parts += [prompts.DRAFT_SECTION_DEAL, deal_context.strip(), ""]

        if doc_context and doc_context.strip():
            parts += [prompts.DRAFT_SECTION_KB, doc_context.strip(), ""]

        parts.append(prompts.DRAFT_FOOTER)
        return "\n".join(parts)
