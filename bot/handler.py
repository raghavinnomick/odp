"""
Bot Handler
API endpoints for chatbot functionality
Now supports conversation history and cross-deal search
"""

# Python Packages
from flask import request
from flask_restx import Namespace, Resource

# Controller
from .controller import BotController

# Exceptions
from ..util.exceptions import AppException, InternalServerException





# Create namespace
bot_namespace = Namespace(
    'bot',
    description='Chatbot and Q&A operations'
)





@bot_namespace.route('/ask')
class AskQuestion(Resource):
    """
    Ask a question (searches across ALL deals)
    """
    
    def post(self):
        """
        Answer a question about any deal
        
        Request body:
        {
            "question": "What is the valuation of SpaceX?",
            "session_id": "optional-session-id",  // for conversation history
            "top_k": 5  // optional, default 5
        }
        
        Response:
        {
            "status": "success",
            "data": {
                "answer": "The valuation of SpaceX is...",
                "sources": [...],
                "session_id": "abc-123",  // use this for follow-up questions
                "deals_referenced": [10, 11],
                "confidence": "high"
            }
        }
        """
        
        try:
            # Parse request
            data = request.get_json()
            
            if not data:
                raise AppException(
                    error_code="INVALID_REQUEST",
                    message="Request body is required"
                )
            
            question = data.get('question')
            session_id = data.get('session_id')  # Optional
            top_k = data.get('top_k', 5)
            
            # Validate question
            if not question:
                raise AppException(
                    error_code="MISSING_QUESTION",
                    message="Question is required"
                )
            
            if not isinstance(question, str) or len(question.strip()) == 0:
                raise AppException(
                    error_code="INVALID_QUESTION",
                    message="Question must be a non-empty string"
                )
            
            # Validate top_k
            if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
                raise AppException(
                    error_code="INVALID_TOP_K",
                    message="top_k must be an integer between 1 and 20"
                )
            
            # Call controller (no deal_id = search all deals)
            result = BotController().ask_question(
                question=question.strip(),
                deal_id=None,  # Search all deals
                session_id=session_id,
                top_k=top_k
            )
            
            return {
                "status": "success",
                "data": result
            }, 200
            
        except AppException as error:
            return error.to_dict(), error.status_code
            
        except Exception as error:
            error = InternalServerException(details=str(error))
            return error.to_dict(), error.status_code


@bot_namespace.route('/ask/<int:deal_id>')
class AskQuestionDeal(Resource):
    """
    Ask a question about a specific deal
    """
    
    def post(self, deal_id):
        """
        Answer a question about a specific deal
        
        Request body:
        {
            "question": "What is the valuation?",
            "session_id": "optional-session-id",
            "top_k": 5
        }
        """
        
        try:
            # Parse request
            data = request.get_json()
            
            if not data:
                raise AppException(
                    error_code="INVALID_REQUEST",
                    message="Request body is required"
                )
            
            question = data.get('question')
            session_id = data.get('session_id')
            top_k = data.get('top_k', 5)
            
            # Validate
            if not question:
                raise AppException(
                    error_code="MISSING_QUESTION",
                    message="Question is required"
                )
            
            if not isinstance(question, str) or len(question.strip()) == 0:
                raise AppException(
                    error_code="INVALID_QUESTION",
                    message="Question must be a non-empty string"
                )
            
            if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
                raise AppException(
                    error_code="INVALID_TOP_K",
                    message="top_k must be an integer between 1 and 20"
                )
            
            # Call controller (with specific deal_id)
            result = BotController().ask_question(
                question=question.strip(),
                deal_id=deal_id,
                session_id=session_id,
                top_k=top_k
            )
            
            return {
                "status": "success",
                "data": result
            }, 200
            
        except AppException as error:
            return error.to_dict(), error.status_code
            
        except Exception as error:
            error = InternalServerException(details=str(error))
            return error.to_dict(), error.status_code


@bot_namespace.route('/conversation/<session_id>')
class ConversationHistory(Resource):
    """
    Get conversation history
    """
    
    def get(self, session_id):
        """
        Get conversation history for a session
        
        Query params:
        - limit: Number of messages (default 10)
        """
        
        try:
            limit = request.args.get('limit', 10, type=int)
            
            result = BotController().get_conversation_history(
                session_id=session_id,
                limit=limit
            )
            
            return {
                "status": "success",
                "data": result
            }, 200
            
        except Exception as error:
            return {
                "status": "error",
                "message": str(error)
            }, 500
    
    def delete(self, session_id):
        """
        Clear/delete a conversation
        """
        
        try:
            result = BotController().clear_conversation(session_id)
            
            return {
                "status": "success",
                "data": {
                    "session_id": session_id,
                    "cleared": result
                }
            }, 200
            
        except Exception as error:
            return {
                "status": "error",
                "message": str(error)
            }, 500


@bot_namespace.route('/debug/<int:deal_id>')
class DebugDeal(Resource):
    """Debug endpoint to inspect deal data"""
    
    def get(self, deal_id):
        """Get debug information about a deal"""
        try:
            from .services.debug_service import DebugService
            
            debug_service = DebugService()
            stats = debug_service.get_deal_stats(deal_id)
            samples = debug_service.get_sample_chunks(deal_id, limit=3)
            
            question = request.args.get('question')
            search_test = None
            if question:
                search_test = debug_service.test_search(deal_id, question)
            
            return {
                "status": "success",
                "data": {
                    "stats": stats,
                    "sample_chunks": samples,
                    "search_test": search_test
                }
            }, 200
            
        except Exception as error:
            return {
                "status": "error",
                "message": str(error)
            }, 500