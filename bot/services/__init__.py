"""
Bot Services Package

Exports all service classes used by BotController.

Service responsibilities:
  QueryService            — RAG pipeline orchestrator (main entry point)
  SearchService           — Tier-1 vector search over odp_deal_document_chunks
  DealContextService      — Deal metadata, tone rules, Tier-2 Dynamic KB
  ConversationService     — Session and message persistence
  AnswerGenerator         — LLM prompting (answer / ask / draft modes)
  ClarificationService    — Detects "which deal?" ambiguity
  QueryEnhancementService — Dereferences pronouns using conversation history
  ContextBuilder          — Formats RAG chunks into LLM-ready context strings
  FactExtractorService    — Extracts deal facts from team member messages
  DebugService            — Development diagnostics (not for production)
"""

from .search_service import SearchService
from .context_builder import ContextBuilder
from .answer_generator import AnswerGenerator
from .query_service import QueryService
from .clarification_service import ClarificationService
from .debug_service import DebugService
from .conversation_service import ConversationService
from .query_enhancement_service import QueryEnhancementService
from .deal_context_service import DealContextService
from .fact_extractor_service import FactExtractorService

__all__ = [
    "SearchService",
    "ContextBuilder",
    "AnswerGenerator",
    "QueryService",
    "ClarificationService",
    "DebugService",
    "ConversationService",
    "QueryEnhancementService",
    "DealContextService",
    "FactExtractorService",
]
