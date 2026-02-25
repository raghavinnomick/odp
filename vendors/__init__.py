"""
vendors/__init__.py
====================
Public surface of the vendors package.

All service files import like this (unchanged from before):

    from ...vendors.openai import ChatService       ← still works (OpenAI direct)
    from ...vendors.openai import EmbeddingService  ← still works

OR use the factory (recommended — provider-agnostic):

    from ...vendors import ChatService       ← switches via AI_PROVIDER in .env
    from ...vendors import EmbeddingService  ← always OpenAI

The factory import is what bot services use going forward.
"""

from .factory import get_chat_service, get_embedding_service

# Expose as class-like names so existing import style still works:
#   from ...vendors import ChatService
#   service = ChatService()
# These are factory functions, not classes — calling them returns the right instance.
ChatService      = get_chat_service
EmbeddingService = get_embedding_service
