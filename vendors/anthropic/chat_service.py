"""
vendors/anthropic/chat_service.py
===================================
ChatService implementation using Anthropic Claude models.

Implements the same interface as vendors/openai/chat_service.py so the
factory can swap providers transparently — no service files need to change.

Key difference from OpenAI:
  Anthropic separates the system prompt from the messages array.
  OpenAI sends system as {"role": "system", "content": "..."} inside messages.
  Anthropic takes system as a top-level parameter and messages must only
  contain "user" and "assistant" roles.

This class handles that conversion internally — callers always pass messages
in the standard OpenAI format (system role inside messages array) and this
service splits it out automatically before calling the Anthropic API.
"""

# Python Packages
from typing import List, Dict, Optional

# Client
from .anthropic_client import AnthropicClient

# Constants
from ...base import constants





class ChatService:
    """
    Anthropic Claude implementation of ChatService.
    Drop-in replacement for vendors/openai/chat_service.py.
    """

    def __init__(self):
        self.client        = AnthropicClient().get_client()
        self.default_model = constants.ANTHROPIC_DEFAULT_MODEL


    def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> str:
        """
        Generate a response using the Anthropic Claude API.

        Accepts messages in the standard format used across the codebase:
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]

        Internally converts to Anthropic's format:
            system   → top-level string parameter
            messages → only user/assistant turns

        Args:
            messages:    List of message dicts with 'role' and 'content'.
            model:       Claude model string. Defaults to ANTHROPIC_DEFAULT_MODEL.
            temperature: Sampling temperature (0.0 – 1.0).
            max_tokens:  Maximum tokens in response.

        Returns:
            Generated response text as a string.
        """

        try:
            system_prompt, conversation = self._split_messages(messages)

            kwargs = dict(
                model       = model or self.default_model,
                max_tokens  = max_tokens,
                temperature = temperature,
                messages    = conversation,
            )

            # Anthropic ignores empty system strings — only pass if present
            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.client.messages.create(**kwargs)
            return response.content[0].text

        except Exception as e:
            print(f"❌ Anthropic error generating response: {e}")
            raise



    def generate_answer_from_context(self, question: str, context: str, model: str = None) -> str:
        """
        Generate answer based on provided context.
        Matches the OpenAI ChatService interface for compatibility.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that answers questions based on provided documents. "
                    "Only use information from the context provided. "
                    "If the answer is not in the context, say so."
                )
            },
            {
                "role":    "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
            }
        ]
        return self.generate_response(messages, model=model)



    # ── Private ────────────────────────────────────────────────────────────────
    def _split_messages(self, messages: List[Dict[str, str]]):
        """
        Split OpenAI-style messages into Anthropic format.

        Returns:
            (system_prompt: str, conversation: List[Dict])

        Rules:
          - The FIRST "system" role message becomes the top-level system prompt.
          - All "user" and "assistant" messages form the conversation array.
          - Additional system messages (rare) are prepended to the next user message.
        """
        system_parts   = []
        conversation   = []
        pending_system = []

        for msg in messages:
            role    = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                if not conversation:
                    # Before any user/assistant turns → goes to top-level system
                    system_parts.append(content)
                else:
                    # Mid-conversation system message → buffer and prepend to next user turn
                    pending_system.append(content)

            elif role in ("user", "assistant"):
                if pending_system and role == "user":
                    content = "\n\n".join(pending_system) + "\n\n" + content
                    pending_system = []
                conversation.append({"role": role, "content": content})

        system_prompt = "\n\n".join(system_parts)
        return system_prompt, conversation
