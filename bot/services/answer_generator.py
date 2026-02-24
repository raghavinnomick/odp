"""
Service: AnswerGenerator

Generates all LLM responses in the bot pipeline.

Modes
=====
greeting  Warm, brief social reply — no RAG.
answer    RAG Q&A. Dynamic KB (team facts) OVERRIDES document passages.
ask       Ask team ONLY for the specific values the bot could NOT confirm.
          Receives partial_answer so it never re-asks confirmed items.
draft     Draft a reply email using team-supplied info + KB context + tone.

Critical priority rule
======================
The LLM is explicitly told:
  "TEAM-SUPPLIED FACTS come first and OVERRIDE document passages.
   If a team fact says $25k but a document says $50k — use $25k."

This is enforced in two ways:
  1. Dynamic KB context is placed BEFORE static KB context in the prompt.
  2. The system prompt contains explicit override instructions.

All tone comes from odp_tone_rules via the tone_rules parameter.
Zero hardcoded tone or figures in this file.
"""

# Python Packages
from typing import List, Dict, Optional

# Vendors
from ...vendors.openai import ChatService

# Config
from ..config import prompts, service_constants





class AnswerGenerator:
    """
    LLM wrapper for all bot response types.
    Stateless — all context passed in per call. Nothing hardcoded.
    """

    def __init__(self):
        """ Initialize ChatService client. No state or config here."""
        self.chat_service = ChatService()



    # ── Greeting Reply ─────────────────────────────────────────────────────────
    def generate_greeting_reply(
        self,
        question: str,
        tone_rules: str = None
    ) -> str:
        """
        Generate a natural, warm greeting (1–2 sentences).
        No RAG context needed. Tone from DB via tone_rules.
        """
        print("👋 Generating greeting reply...")

        tone_section = self._resolve_tone(tone_rules)

        system_prompt = prompts.GREETING_SYSTEM_TEMPLATE.format(tone_section = tone_section)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": question}
        ]

        return self.chat_service.generate_response(
            messages = messages,
            temperature = service_constants.LLM_GREETING_TEMPERATURE,
            max_tokens = service_constants.LLM_GREETING_MAX_TOKENS
        ).strip()



    # ── Standard Answer ────────────────────────────────────────────────────────
    def generate_answer(
        self,
        question: str,
        context: str,
        tone_rules: str = None,
        deal_context: str = None,
        history_messages: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate a RAG answer from the provided context.

        Context is pre-merged with Dynamic KB FIRST, Static KB second.
        System prompt reinforces that team-supplied facts override documents.

        NEVER invents figures not present in context.

        Args:
            question:         The investor's question.
            context:          Pre-merged context (dynamic first, static second).
            tone_rules:       Rules from odp_tone_rules.
            deal_context:     One-line deal identifier.
            history_messages: Prior turns as [{role, content}].

        Returns:
            Answer string.
        """

        print("🤖 Generating answer...")

        system_prompt = self._build_system_prompt(tone_rules = tone_rules, mode = "answer")
        messages = [{"role": "system", "content": system_prompt}]

        if history_messages:
            for msg in history_messages:
                role    = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
            print(f"   📜 Injected {len(history_messages)} history turns")

        user_prompt = self._format_answer_prompt(
            question = question,
            doc_context = context,
            deal_context = deal_context
        )
        messages.append({"role": "user", "content": user_prompt})

        return self.chat_service.generate_response(
            messages = messages,
            temperature = service_constants.LLM_ANSWER_TEMPERATURE,
            max_tokens = service_constants.LLM_ANSWER_MAX_TOKENS
        )



    # ── Info Request (ask for gaps only) ──────────────────────────────────────
    def generate_info_request(
        self,
        original_question: str,
        partial_answer: str,
        tone_rules: str = None,
        history_messages: Optional[List[Dict]] = None
    ) -> str:
        """
        Ask the team ONLY for facts that could NOT be confirmed.

        Receives partial_answer so the LLM sees what was already confirmed
        and does NOT re-ask for those. This prevents both:
          - Re-asking about confirmed items (e.g. deal structure)
          - Hallucinating values for unknown items (e.g. "$50k")

        Args:
            original_question: The investor's full question.
            partial_answer:    The answer the bot already generated (has gaps).
            tone_rules:        Rules from odp_tone_rules.
            history_messages:  Conversation history.

        Returns:
            Short numbered message asking ONLY for confirmed-missing values.
        """
        print("📋 Generating info request (gaps only)...")

        system_prompt = self._build_system_prompt(tone_rules=tone_rules, mode="ask")
        messages = [{"role": "system", "content": system_prompt}]

        if history_messages:
            for msg in history_messages:
                role    = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        user_prompt = f"""The investor asked:
"{original_question}"

Here is what I was ALREADY ABLE TO CONFIRM from our knowledge base:
---
{partial_answer}
---

Look at the answer above carefully.
Find ONLY the items where I said something like "we don't have", "not in our knowledge base",
"could you provide", "please provide", or similar.

Write a short message asking our team member ONLY for those specific missing items.
Do NOT ask again about anything already confirmed above.
Number each missing item. Be precise ("What are the payment dates?" not "Tell me more").
End with: "Once you share these, I will draft the reply right away." """

        messages.append({"role": "user", "content": user_prompt})

        return self.chat_service.generate_response(
            messages=messages,
            temperature=service_constants.LLM_INFO_REQUEST_TEMPERATURE,
            max_tokens=service_constants.LLM_INFO_REQUEST_MAX_TOKENS
        )

    # ── Draft Email ────────────────────────────────────────────────────────────

    def generate_draft_email(
        self,
        original_investor_question: str,
        user_supplied_info: str,
        tone_rules: str = None,
        deal_context: str = None,
        doc_context: str = None,
        history_messages: Optional[List[Dict]] = None
    ) -> str:
        """
        Draft a reply email to an investor.

        Uses team-supplied info, dynamic KB (team corrections), and static KB.
        Tone from DB. No hardcoded figures.

        Returns:
            Draft email body (no subject, no signature).
        """
        print("✉️  Generating draft email...")

        system_prompt = self._build_system_prompt(tone_rules=tone_rules, mode="draft")
        messages = [{"role": "system", "content": system_prompt}]

        if history_messages:
            for msg in history_messages:
                role    = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        user_prompt = self._format_draft_prompt(
            investor_question=original_investor_question,
            user_info=user_supplied_info,
            deal_context=deal_context,
            doc_context=doc_context
        )
        messages.append({"role": "user", "content": user_prompt})

        return self.chat_service.generate_response(
            messages=messages,
            temperature=service_constants.LLM_DRAFT_TEMPERATURE,
            max_tokens=service_constants.LLM_DRAFT_MAX_TOKENS
        )

    # ── Private: System Prompts ────────────────────────────────────────────────
    def _resolve_tone(self, tone_rules: str = None) -> str:
        """ Return tone section — from DB if available, minimal fallback otherwise... """

        if tone_rules and tone_rules.strip():
            return tone_rules.strip()

        print("⚠️  No tone rules in DB — using minimal fallback.")
        return service_constants.FALLBACK_TONE_RULES



    def _build_system_prompt(self, tone_rules: str = None, mode: str = "answer") -> str:
        """Assemble system prompt for the given mode. Tone always from DB."""
        tone_section = self._resolve_tone(tone_rules)

        if mode == "ask":
            mode_instructions = prompts.ASK_MODE_INSTRUCTIONS
        elif mode == "draft":
            mode_instructions = prompts.DRAFT_MODE_INSTRUCTIONS
        else:  # answer mode
            mode_instructions = prompts.ANSWER_MODE_INSTRUCTIONS

        return prompts.SYSTEM_PROMPT_TEMPLATE.format(
            tone_section=tone_section,
            mode_instructions=mode_instructions
        )

    # ── Private: Prompt Formatters ─────────────────────────────────────────────

    def _format_answer_prompt(
        self,
        question: str,
        doc_context: str,
        deal_context: str = None
    ) -> str:
        """
        Build user-turn prompt for answer mode.

        Context order matters:
          - deal_context     (one-line identifier)
          - doc_context      (pre-merged: dynamic KB first, static second)

        The dynamic KB section is already labelled "TEAM-SUPPLIED FACTS"
        by DealContextService.search_dynamic_kb() — the LLM system prompt
        instructs it to give that section highest priority.
        """
        parts = []

        if deal_context and deal_context.strip():
            parts.append(prompts.ANSWER_PROMPT_DEAL_SECTION)
            parts.append(deal_context.strip())
            parts.append("")

        if doc_context and doc_context.strip():
            parts.append(prompts.ANSWER_PROMPT_KB_SECTION)
            parts.append(doc_context.strip())
            parts.append("")
        else:
            parts.append(prompts.ANSWER_PROMPT_NO_KB_SECTION)
            parts.append(prompts.ANSWER_PROMPT_NO_KB_MESSAGE)
            parts.append("")

        parts.append(prompts.ANSWER_PROMPT_FOOTER.format(question=question))

        return "\n".join(parts)

    def _format_draft_prompt(
        self,
        investor_question: str,
        user_info: str,
        deal_context: str = None,
        doc_context: str = None
    ) -> str:
        """Build user-turn prompt for draft mode."""
        parts = []

        parts.append(prompts.DRAFT_PROMPT_QUESTION_SECTION)
        parts.append(investor_question.strip())
        parts.append("")

        parts.append(prompts.DRAFT_PROMPT_INFO_SECTION)
        parts.append(user_info.strip() if user_info else "(none provided)")
        parts.append("")

        if deal_context and deal_context.strip():
            parts.append("── DEAL INFORMATION ──")
            parts.append(deal_context.strip())
            parts.append("")

        if doc_context and doc_context.strip():
            parts.append(prompts.DRAFT_PROMPT_KB_SECTION)
            parts.append(doc_context.strip())
            parts.append("")

        parts.append(prompts.DRAFT_PROMPT_FOOTER)

        return "\n".join(parts)
