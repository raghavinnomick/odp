"""
Bot Handler
API endpoints for chatbot functionality.
"""

# Python Packages
from flask import request
from flask_restx import Namespace, Resource

# Validations
from .validations import BotValidation

# Controller
from .controller import BotController

# Exceptions
from ..util.exceptions import AppException, InternalServerException

# Constants
from ..base import constants

bot_namespace = Namespace("bot", description="Chatbot and Q&A operations")


# ── POST /bot/ask ─────────────────────────────────────────────────────────────

@bot_namespace.route("/ask")
class AskQuestion(Resource):
    """Ask a question — searches across ALL deals."""

    def post(self):
        """
        Ask a question about any deal.

        Request:
        {
            "question":   "What is the minimum ticket?",
            "user_id":    "user-123",
            "session_id": "abc-xyz"   // optional — omit to start a new session
        }

        Response types:
          "answer"               — found in Static or Dynamic KB
          "needs_info"           — not found, bot asks team for the value
          "needs_clarification"  — bot needs to know which deal
          "draft_email"          — user answered pending question, draft ready
        """

        try:
            data = request.get_json()
            BotValidation.validate_body(data)

            question   = data.get("question")
            user_id    = data.get("user_id")
            session_id = data.get("session_id")
            top_k      = constants.BOT_DEFAULT_TOP_K

            BotValidation.validate_question(question)
            BotValidation.validate_user_id(user_id)
            BotValidation.validate_top_k(top_k)

            result = BotController().ask_question(
                question=question.strip(),
                user_id=user_id,
                deal_id=None,
                session_id=session_id,
                top_k=top_k
            )

            return {"status": "success", "data": result}, 200

        except AppException as error:
            return error.to_dict(), error.status_code
        except Exception as error:
            error = InternalServerException(details=str(error))
            return error.to_dict(), error.status_code


# ── POST /bot/ask/<deal_id> ───────────────────────────────────────────────────

@bot_namespace.route("/ask/<int:deal_id>")
class AskQuestionDeal(Resource):
    """Ask a question scoped to a specific deal."""

    def post(self, deal_id):
        """
        Ask a question about a specific deal.

        Request:
        {
            "question":   "What is the valuation?",
            "user_id":    "user-123",
            "session_id": "abc-xyz"
        }
        """

        try:
            data = request.get_json()
            BotValidation.validate_body(data)

            question   = data.get("question")
            user_id    = data.get("user_id")
            session_id = data.get("session_id")
            top_k      = constants.BOT_DEFAULT_TOP_K

            BotValidation.validate_question(question)
            BotValidation.validate_user_id(user_id)
            BotValidation.validate_top_k(top_k)

            result = BotController().ask_question(
                question=question.strip(),
                user_id=user_id,
                deal_id=deal_id,
                session_id=session_id,
                top_k=top_k
            )

            return {"status": "success", "data": result}, 200

        except AppException as error:
            return error.to_dict(), error.status_code
        except Exception as error:
            error = InternalServerException(details=str(error))
            return error.to_dict(), error.status_code


# ── POST /bot/generate-draft ──────────────────────────────────────────────────

@bot_namespace.route("/generate-draft")
class GenerateDraft(Resource):
    """
    Manually trigger a draft email from the conversation history.
    Useful when the user wants a draft even after a complete answer.
    The draft is generated automatically after the user supplies a missing answer,
    but this endpoint allows triggering it at any time.
    """

    def post(self):
        """
        Generate a draft reply email from the full conversation.

        Request:
        {
            "session_id": "abc-xyz",
            "user_id":    "user-123"
        }

        Response:
        {
            "status": "success",
            "data": {
                "response_type":     "draft_email",
                "draft_email":       "...",
                "investor_question": "...",
                "session_id":        "abc-xyz",
                "active_deal_id":    1,
                "show_draft_button": false
            }
        }
        """

        try:
            data = request.get_json()
            BotValidation.validate_body(data)

            session_id = data.get("session_id", "").strip()
            user_id    = data.get("user_id", "").strip()

            BotValidation.validate_user_id(user_id)

            if not session_id:
                raise AppException(
                    error_code="MISSING_SESSION_ID",
                    message="session_id is required to generate a draft.",
                    status_code=400
                )

            result = BotController().generate_draft(
                session_id=session_id,
                user_id=user_id
            )

            return {"status": "success", "data": result}, 200

        except AppException as error:
            return error.to_dict(), error.status_code
        except Exception as error:
            error = InternalServerException(details=str(error))
            return error.to_dict(), error.status_code


# ── GET /bot/conversation/<session_id> ────────────────────────────────────────

@bot_namespace.route("/conversation/<session_id>")
class ConversationHistory(Resource):
    """Get or delete a conversation."""

    def get(self, session_id):
        """Get conversation history for a session."""
        try:
            limit  = request.args.get("limit", 10, type=int)
            result = BotController().get_conversation_history(
                session_id=session_id, limit=limit
            )
            return {"status": "success", "data": result}, 200
        except Exception as error:
            return {"status": "error", "message": str(error)}, 500

    def delete(self, session_id):
        """Clear a conversation."""
        try:
            result = BotController().clear_conversation(session_id)
            return {"status": "success", "data": {"session_id": session_id, "cleared": result}}, 200
        except Exception as error:
            return {"status": "error", "message": str(error)}, 500


# ── GET /bot/debug/<deal_id> ──────────────────────────────────────────────────

@bot_namespace.route("/debug/<int:deal_id>")
class DebugDeal(Resource):
    """Debug endpoint — inspect deal data. Not for production."""

    def get(self, deal_id):
        try:
            from .services.debug_service import DebugService
            debug   = DebugService()
            stats   = debug.get_deal_stats(deal_id)
            samples = debug.get_sample_chunks(deal_id, limit=3)

            question    = request.args.get("question")
            search_test = debug.test_search(deal_id, question) if question else None

            return {
                "status": "success",
                "data": {"stats": stats, "sample_chunks": samples, "search_test": search_test}
            }, 200
        except Exception as error:
            return {"status": "error", "message": str(error)}, 500
