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


class AnswerGenerator:
    """
    LLM wrapper for all bot response types.
    Stateless — all context passed in per call. Nothing hardcoded.
    """

    def __init__(self):
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

        system_prompt = f"""You are a helpful assistant for Open Doors Partners (ODP), a private investment firm.
You assist the ODP team in answering investor questions.

TONE RULES (from database):
{tone_section}

TASK: The user sent a greeting or social message.
Reply in a warm, brief, natural way — 1 to 2 sentences maximum.
Do NOT mention deals or investments unless the user brings it up.
Just greet them and let them know you are ready to help."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": question}
        ]

        return self.chat_service.generate_response(
            messages=messages,
            temperature=0.5,
            max_tokens=80
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

        system_prompt = self._build_system_prompt(tone_rules=tone_rules, mode="answer")
        messages = [{"role": "system", "content": system_prompt}]

        if history_messages:
            for msg in history_messages:
                role    = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
            print(f"   📜 Injected {len(history_messages)} history turns")

        user_prompt = self._format_answer_prompt(
            question=question,
            doc_context=context,
            deal_context=deal_context
        )
        messages.append({"role": "user", "content": user_prompt})

        return self.chat_service.generate_response(
            messages=messages,
            temperature=0.2,
            max_tokens=900
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
            temperature=0.2,
            max_tokens=400
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
            temperature=0.3,
            max_tokens=1200
        )

    # ── Private: System Prompts ────────────────────────────────────────────────

    def _resolve_tone(self, tone_rules: str = None) -> str:
        """Return tone section — from DB if available, minimal fallback otherwise."""
        if tone_rules and tone_rules.strip():
            return tone_rules.strip()
        print("⚠️  No tone rules in DB — using minimal fallback.")
        return (
            "- Speak as 'we' (the firm). Be direct, warm, and confident.\n"
            "- Answer concisely. No corporate fluff.\n"
            "- Use exact numbers from context only. Never invent figures."
        )

    def _build_system_prompt(self, tone_rules: str = None, mode: str = "answer") -> str:
        """Assemble system prompt for the given mode. Tone always from DB."""
        tone_section = self._resolve_tone(tone_rules)

        if mode == "ask":
            mode_instructions = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK: REQUEST MISSING INFO (GAPS ONLY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You already gave a partial answer. Now ask ONLY for what you could NOT confirm.
- Read the partial answer carefully first.
- Ask ONLY about items where the answer said "we don't have",
  "not in knowledge base", "could you provide", or similar.
- Do NOT re-ask about anything that was already answered.
- Number each missing item.
- Be specific: "What are the payment dates?" not "Do you have more details?"
- Keep it short: one intro sentence + numbered list.
- End with: "Once you share these, I will draft the reply right away."
"""
        elif mode == "draft":
            mode_instructions = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK: DRAFT EMAIL REPLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Draft a professional email reply to the investor question provided.
Use team-supplied information, deal context, and document passages.

FORMAT:
- Start directly with the reply body (no subject line)
- Use tone rules faithfully
- Answer each part of the investor's question in order
- If numbered sub-questions, answer each one numbered
- End with "Best,"
- Do NOT add a name — the user will add that

ACCURACY:
- Only use facts from: team-supplied info, deal context, document passages
- If any part still cannot be confirmed, insert:
  "[Note: please confirm — {what is missing}]"
- NEVER invent any number, date, or term not present in the sources
"""
        else:  # answer mode
            mode_instructions = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT PRIORITY — READ CAREFULLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The context below is ordered from HIGHEST to LOWEST priority:

  1. TEAM-SUPPLIED FACTS  — at the top, labelled "TEAM-SUPPLIED FACTS"
     These are corrections and answers provided by the ODP team.
     They are ALWAYS correct and OVERRIDE any conflicting document values.
     Example: if team says minimum ticket is $25k, use $25k even if a
     document says $50k.

  2. DOCUMENT PASSAGES  — below, labelled "Document N:"
     These are from deal PDFs. Use them for any fact not covered above.
     If a fact appears in BOTH team facts AND documents, the team fact wins.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT NO-HALLUCINATION RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEVER invent:
- Dollar amounts (minimums, valuations, fees)
- Dates or timelines (payment dates, closing dates)
- Terms (lock-up periods, distribution schedules)

WHEN INFORMATION IS MISSING from ALL context above:
1. Answer only what you CAN confirm.
2. For missing items say: "We don't have [specific detail] in our knowledge base."
3. NEVER guess or use typical industry figures.

ESCALATION — say "Let me flag this for our team to follow up":
- Fee negotiation, commitments over $2M, KYC/subscription document requests
"""

        return f"""You are an AI assistant for Open Doors Partners (ODP), a private investment firm.
You help the ODP team respond accurately and professionally to investor questions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TONE & COMPLIANCE RULES (from database)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{tone_section}
{mode_instructions}"""

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
            parts.append("── DEAL INFORMATION ──")
            parts.append(deal_context.strip())
            parts.append("")

        if doc_context and doc_context.strip():
            parts.append("── KNOWLEDGE BASE (team facts first, then documents) ──")
            parts.append(doc_context.strip())
            parts.append("")
        else:
            parts.append("── NO KNOWLEDGE BASE CONTEXT FOUND ──")
            parts.append("Our knowledge base returned NO information for this question.")
            parts.append("Do NOT answer from training knowledge.")
            parts.append("Say: \"We don't have [specific detail] in our knowledge base.\"")
            parts.append("Ask the user to provide the specific information.")
            parts.append("")

        parts.append("──────────────────────────────────────")
        parts.append(f"Investor Question: {question}")
        parts.append("")
        parts.append("Answer:")

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

        parts.append("── INVESTOR'S QUESTION (we are replying to this) ──")
        parts.append(investor_question.strip())
        parts.append("")

        parts.append("── INFORMATION PROVIDED BY OUR TEAM ──")
        parts.append(user_info.strip() if user_info else "(none provided)")
        parts.append("")

        if deal_context and deal_context.strip():
            parts.append("── DEAL INFORMATION ──")
            parts.append(deal_context.strip())
            parts.append("")

        if doc_context and doc_context.strip():
            parts.append("── KNOWLEDGE BASE (team facts first, then documents) ──")
            parts.append(doc_context.strip())
            parts.append("")

        parts.append("──────────────────────────────────────")
        parts.append("Draft the email reply using all information above.")
        parts.append("Follow tone rules exactly. End with 'Best,'")
        parts.append("")
        parts.append("Draft Email:")

        return "\n".join(parts)
