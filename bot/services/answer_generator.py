"""
Answer Generator Service
Generates answers using LLM with context built dynamically from the database.

Design principles:
    - ZERO hardcoded deal names, facts, or numbers
    - System prompt = ODP identity + tone rules from DB
    - Deal facts = passed in from DB at query time (odp_deal_terms, dynamic_facts, faqs)
    - Document context = RAG chunks from vector search
    - Conversation history = real LLM message objects
    - Hard no-hallucination rule: never invent numbers, dates, or terms
"""

# Python Packages
from typing import List, Dict, Optional

# Vendors
from ...vendors.openai import ChatService


class AnswerGenerator:
    """
    Service for generating answers using LLM.
    Receives all context dynamically — nothing is hardcoded.
    """

    def __init__(self):
        self.chat_service = ChatService()


    def generate_answer(
        self,
        question: str,
        context: str,
        tone_rules: str = None,
        deal_context: str = None,
        history_messages: Optional[List[Dict]] = None,
        conversation_history: str = None  # legacy param, not used
    ) -> str:
        """
        Generate answer using OpenAI chat completion.

        Args:
            question: User's current question
            context: RAG document chunks from vector search
            tone_rules: Tone/compliance rules from odp_tone_rules table
            deal_context: Structured deal facts from DB
            history_messages: Prior conversation as real LLM turns [{role, content}, ...]
            conversation_history: Legacy — ignored

        Returns:
            Generated answer string
        """

        print(f"🤖 Generating answer using LLM...")

        system_prompt = self._get_system_prompt(tone_rules=tone_rules)
        messages = [{"role": "system", "content": system_prompt}]

        # Inject real conversation history as proper LLM turns
        if history_messages:
            for msg in history_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
            print(f"   📜 Injected {len(history_messages)} history turns")

        user_prompt = self._format_user_prompt(
            question=question,
            doc_context=context,
            deal_context=deal_context
        )
        messages.append({"role": "user", "content": user_prompt})

        answer = self.chat_service.generate_response(
            messages=messages,
            temperature=0.2,   # Lower = less creative = less hallucination
            max_tokens=900
        )

        return answer


    def _get_system_prompt(self, tone_rules: str = None) -> str:
        """
        Build the system prompt.
        ODP identity + tone rules from DB.
        No deal names, facts, or numbers — all deal data arrives via the user message.
        """

        if tone_rules and tone_rules.strip():
            tone_section = tone_rules.strip()
        else:
            tone_section = (
                "- Be direct, warm, and confident. Always say 'we' (the firm).\n"
                "- Answer concisely. No corporate fluff or excessive disclaimers.\n"
                "- For multi-part questions, answer each part clearly.\n"
                "- When the user says 'it', 'them', 'that deal' — use conversation history to resolve."
            )

        return f"""You are an AI assistant for Open Doors Partners (ODP), a private investment firm.
You answer investor questions about the firm's active investment deals.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TONE & COMPLIANCE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{tone_section}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT NO-HALLUCINATION RULE — CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You will receive deal-specific context below (deal facts from DB and document passages).
ONLY use the exact information in that context. Do NOT fill in gaps with general knowledge.

NEVER invent:
- Specific dollar amounts (minimums, valuations, fees, carry percentages)
- Dates or timelines (payment dates, closing dates, IPO dates)
- Terms or conditions (lock-up periods, distribution schedules, return projections)
- Process steps (signing platforms, onboarding steps, document names)

If specific information is NOT present in the context provided:
→ Say: "I don't have that specific detail in our documents — let me flag it for our team."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO USE THE CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each message contains up to two context sections:

1. DEAL INFORMATION (from database): Structured facts — use exact figures as stated.
2. DOCUMENT PASSAGES (from deal documents): Retrieved text — use for detailed answers.

PRIORITY: Document passages > Deal information > Say "I don't have that detail."

CONVERSATION HISTORY is injected as prior messages in this thread.
Use it to understand what deal the user is referring to when they say "it",
"that", "the structure", "the minimum" — without re-asking about context
already established.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESCALATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Say "Let me flag this for our team to follow up":
- Fee negotiation
- Commitments over $2M
- Subscription or KYC document requests
- Track record or legal verification"""


    def _format_user_prompt(
        self,
        question: str,
        doc_context: str,
        deal_context: str = None
    ) -> str:
        """
        Build the user-turn prompt.
        History is injected as prior LLM turns — not here.

        Args:
            question: User's current question
            doc_context: RAG context from vector search
            deal_context: Structured deal facts from DB

        Returns:
            Formatted prompt string
        """

        parts = []

        if deal_context and deal_context.strip():
            parts.append("── DEAL INFORMATION (from database) ──")
            parts.append(deal_context.strip())
            parts.append("")

        if doc_context and doc_context.strip():
            parts.append("── DOCUMENT PASSAGES (from deal documents) ──")
            parts.append(doc_context.strip())
            parts.append("")

        if not (deal_context and deal_context.strip()) and not (doc_context and doc_context.strip()):
            parts.append("── NOTE ──")
            parts.append("No specific document context was retrieved for this question.")
            parts.append("Only answer what you can confirm from the deal information above.")
            parts.append("If you cannot confirm a specific fact, say so — do not guess.")
            parts.append("")

        parts.append("──────────────────────────────────────")
        parts.append(f"Question: {question}")
        parts.append("")
        parts.append("Answer:")

        return "\n".join(parts)
