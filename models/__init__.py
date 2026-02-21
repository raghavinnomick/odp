"""
Models Package
Registers all SQLAlchemy ORM models so they are discoverable by Flask-SQLAlchemy.

Import order matters: models with foreign keys must be imported after
the models they reference.
"""

from .odp_deal import Deal
from .odp_deal_document import DealDocument
from .odp_deal_document_chunks import DealDocumentChunk
from .odp_deal_dynamic_fact import DealDynamicFact

from .odp_conversation import Conversation
from .odp_conversation_message import ConversationMessage

from .odp_tone_rule import ToneRule

__all__ = [
    "Deal",
    "DealDocument",
    "DealDocumentChunk",
    "DealDynamicFact",
    "Conversation",
    "ConversationMessage",
    "ToneRule",
]
