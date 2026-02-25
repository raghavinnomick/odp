"""
vendors/factory.py — AI Provider Factory
==========================================
Single place that decides which AI provider to use for chat/LLM calls.

How to switch providers
------------------------
In your .env file, set:

    AI_PROVIDER=anthropic    ← use Claude (current default)
    AI_PROVIDER=openai       ← use GPT models

That's the ONLY change needed to switch providers across the entire codebase.
No service files, no prompt files, no bot logic needs to change.

Why embeddings are always OpenAI
----------------------------------
Anthropic does not offer an embedding API. Embeddings are used to store and
search document chunks in PostgreSQL (pgvector). Switching embedding models
would invalidate all existing stored embeddings and require re-processing
every uploaded document. Therefore EmbeddingService always uses OpenAI
regardless of the AI_PROVIDER setting.

If you want to switch embeddings in future (e.g. to Cohere or a local model),
create a new embedding service in vendors/ and update get_embedding_service()
below — that's the only place to change.
"""

# Constants
from ..base import constants





def get_chat_service():
    """
    Return the correct ChatService instance based on AI_PROVIDER env variable.

    Returns:
        ChatService with a generate_response(messages, temperature, max_tokens) method.

    Raises:
        ValueError: If AI_PROVIDER is set to an unsupported value.
    """

    provider = constants.AI_PROVIDER.lower().strip()

    if provider == "anthropic":
        from .anthropic.chat_service import ChatService
        print(f"🤖 LLM Provider: Anthropic ({constants.ANTHROPIC_DEFAULT_MODEL})")
        return ChatService()

    elif provider == "openai":
        from .openai.chat_service import ChatService
        print(f"🤖 LLM Provider: OpenAI ({constants.OPENAI_DEFAULT_MODEL})")
        return ChatService()

    else:
        raise ValueError(
            f"Unsupported AI_PROVIDER='{provider}'. "
            f"Allowed values: 'anthropic', 'openai'. "
            f"Check your .env file."
        )


def get_embedding_service():
    """
    Always returns the OpenAI EmbeddingService.

    Anthropic has no embedding API. OpenAI embeddings are used for pgvector
    similarity search across all document chunks.
    """

    from .openai.embedding_service import EmbeddingService
    return EmbeddingService()
