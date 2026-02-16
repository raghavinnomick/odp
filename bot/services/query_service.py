"""
Query Service
Orchestrates the RAG pipeline: search → context → answer
Now with conversation history support
"""

# Python Packages
from typing import Dict, List, Optional

# Services
from .query_enhancement_service import QueryEnhancementService
from .search_service import SearchService
from .context_builder import ContextBuilder
from .answer_generator import AnswerGenerator
from .clarification_service import ClarificationService
from .conversation_service import ConversationService

# Database
from odp.config.database import db
from ...models.odp_deal_document import DealDocument

# Exceptions
from ...util.exceptions import ServiceException
from ...util import messages


class QueryService:
    """
    Main service for answering questions using RAG
    Orchestrates: SearchService → ContextBuilder → AnswerGenerator
    Now supports conversation history
    """
    
    def __init__(self):
        self.search_service = SearchService()
        self.context_builder = ContextBuilder()
        self.answer_generator = AnswerGenerator()
        self.clarification_service = ClarificationService()
        self.conversation_service = ConversationService()
        self.query_enhancement_service = QueryEnhancementService()
    
    
    def answer_question(
        self,
        question: str,
        deal_id: Optional[int] = None,
        session_id: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.5
    ) -> Dict:
        """
        Answer a question using RAG pipeline with conversation history
        
        Args:
            question: User's question
            deal_id: Optional deal ID (if None, searches all deals)
            session_id: Optional session ID for conversation history
            top_k: Number of relevant chunks to retrieve
            similarity_threshold: Minimum similarity score (0-1)
        
        Returns:
            dict: Answer with sources, metadata, and session_id
        """
        
        try:
            print(f"\n{'='*60}")
            print(f"❓ Question: {question}")
            if session_id:
                print(f"📝 Session: {session_id}")
            print(f"{'='*60}")
            
            # Get or create conversation
            conversation = self.conversation_service.get_or_create_conversation(
                session_id=session_id
            )

            # Get conversation history BEFORE saving current message
            conversation_history = self.conversation_service.get_conversation_history(
                session_id = conversation.session_id,
                limit = 6
            )

            # Enhance query using conversation history
            enhanced_question = self.query_enhancement_service.enhance_query(
                current_question=question,
                conversation_history=conversation_history
            )

            # Save user's ORIGINAL question
            self.conversation_service.add_message(
                conversation_id=conversation.conversation_id,
                role="user",
                content=question
            )

            # Step 1: Search using ENHANCED question
            relevant_chunks = self.search_service.search_similar_chunks(
                question=enhanced_question,  # Use enhanced question for search
                deal_id=deal_id,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            # Calculate confidence
            confidence = self.context_builder.calculate_confidence(relevant_chunks)
            
            # Step 2: Check if we need clarification
            if self.clarification_service.needs_clarification(
                question=question,
                chunks_found=len(relevant_chunks),
                confidence=confidence
            ):
                # Get available documents
                if deal_id:
                    documents = db.session.query(DealDocument.doc_name).filter(
                        DealDocument.deal_id == deal_id
                    ).all()
                else:
                    documents = db.session.query(DealDocument.doc_name).all()
                
                doc_names = [doc[0] for doc in documents]
                
                clarifying_q = self.clarification_service.generate_clarifying_question(
                    question=question,
                    available_documents=doc_names
                )
                
                # Save assistant's clarification
                self.conversation_service.add_message(
                    conversation_id=conversation.conversation_id,
                    role="assistant",
                    content=clarifying_q,
                    metadata={"type": "clarification"}
                )
                
                return {
                    "needs_clarification": True,
                    "clarifying_question": clarifying_q,
                    "available_documents": doc_names,
                    "original_question": question,
                    "session_id": conversation.session_id
                }
            
            # Step 3: Build context with conversation history
            context = self.context_builder.build_context(relevant_chunks)
            
            # Add conversation history to context if available
            history_context = self.conversation_service.build_context_from_history(
                session_id=conversation.session_id,
                current_question=question,
                max_messages=4  # Include last 2 exchanges (4 messages)
            )
            
            # Step 4: Generate answer using LLM
            answer = self.answer_generator.generate_answer(
                question = question,  # Original question
                context = context,
                conversation_history = history_context  # Pass history separately
            )
            
            # Step 5: Extract sources and determine which deal(s) were used
            sources = self.context_builder.extract_sources(relevant_chunks)
            deals_used = list(set([chunk[6] for chunk in relevant_chunks if len(chunk) > 6 and chunk[6] is not None]))

            # Save assistant's answer
            self.conversation_service.add_message(
                conversation_id=conversation.conversation_id,
                role="assistant",
                content=answer,
                deal_id=deals_used[0] if deals_used else None,
                metadata={
                    "sources": sources,
                    "confidence": confidence,
                    "chunks_found": len(relevant_chunks)
                }
            )
            
            print(f"\n{'='*60}")
            print(f"✅ Answer generated successfully")
            print(f"   Confidence: {confidence}")
            print(f"   Session: {conversation.session_id}")
            print(f"{'='*60}\n")
            
            return {
                "needs_clarification": False,
                "answer": answer,
                "sources": sources,
                "chunks_found": len(relevant_chunks),
                "confidence": confidence,
                "session_id": conversation.session_id,
                "deals_referenced": deals_used
            }
            
        except Exception as error:
            print(f"❌ Error answering question: {str(error)}")
            raise ServiceException(
                error_code="QUERY_FAILED",
                message=messages.ERROR.get(
                    "QUERY_FAILED",
                    "Failed to process question"
                ),
                details=str(error)
            )