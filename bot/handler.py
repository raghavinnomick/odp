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

# Exceptions & messages
from ..util.exceptions import AppException, InternalServerException
from ..util import messages

# Config
from .config import bot_config

# Namespace
bot_namespace = Namespace("bot", description="Chatbot and Q&A operations")





# ── POST /bot/ask ─────────────────────────────────────────────────────────────
@bot_namespace.route("/ask")
class AskQuestion(Resource):
    """ Ask a question — searches across ALL deals... """

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

            # Request Data
            print(f"Request Data: {data}")

            BotValidation.validate_body(data)

            question   = data.get("question")
            user_id    = data.get("user_id")
            session_id = data.get("session_id")
            top_k      = bot_config.BOT_DEFAULT_TOP_K

            BotValidation.validate_question(question)
            BotValidation.validate_user_id(user_id)
            BotValidation.validate_top_k(top_k)

            result = BotController().ask_question(
                question = question.strip(),
                user_id = user_id,
                deal_id = None,
                session_id = session_id,
                top_k = top_k
            )

            return {"status": "success", "data": result}, 200

        except AppException as error:
            return error.to_dict(), error.status_code

        except Exception as error:
            error = InternalServerException(details = str(error))
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
            top_k      = bot_config.BOT_DEFAULT_TOP_K

            BotValidation.validate_question(question)
            BotValidation.validate_user_id(user_id)
            BotValidation.validate_top_k(top_k)

            result = BotController().ask_question(
                question = question.strip(),
                user_id = user_id,
                deal_id = deal_id,
                session_id = session_id,
                top_k = top_k
            )

            return {"status": "success", "data": result}, 200

        except AppException as error:
            return error.to_dict(), error.status_code

        except Exception as error:
            error = InternalServerException(details = str(error))
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
                    error_code = "MISSING_SESSION_ID",
                    message = messages.ERROR["MISSING_SESSION_ID"],
                    status_code = 400
                )

            result = BotController().generate_draft(
                session_id = session_id,
                user_id = user_id
            )

            return {"status": "success", "data": result}, 200

        except AppException as error:
            return error.to_dict(), error.status_code

        except Exception as error:
            error = InternalServerException(details = str(error))
            return error.to_dict(), error.status_code



# ── GET /bot/conversation/<session_id> ────────────────────────────────────────
@bot_namespace.route("/conversation/<session_id>")
class ConversationHistory(Resource):
    """Get or delete a conversation."""

    def get(self, session_id):
        """ Get conversation history for a session... """
 
        try:
            limit  = request.args.get("limit", bot_config.BOT_LAST_CONVERSATION_MESSAGES_LIMIT, type = int)
            result = BotController().get_conversation_history(
                session_id = session_id, limit = limit
            )
            return {"status": "success", "data": result}, 200

        except Exception as error:
            return {"status": "error", "message": str(error)}, 500


    def delete(self, session_id):
        """ Clear a conversation... """

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
            samples = debug.get_sample_chunks(deal_id, limit = 3)

            question    = request.args.get("question")
            search_test = debug.test_search(deal_id, question) if question else None

            return {
                "status": "success",
                "data": {"stats": stats, "sample_chunks": samples, "search_test": search_test}
            }, 200
        except Exception as error:
            return {"status": "error", "message": str(error)}, 500



# ── GET /bot/sessions/<user_id> ───────────────────────────────────────────────
@bot_namespace.route("/sessions/<user_id>")
class GetUserSessions(Resource):
    """Get all sessions for a specific user."""

    def get(self, user_id):
        """
        Retrieve all conversations (sessions) for a given user_id.
        Returns session_id and other session details from odp_conversations table.

        Request:
        GET /bot/sessions/<user_id>

        Response:
        {
            "status": "success",
            "data": {
                "user_id": "user-123",
                "total": 2,
                "sessions": [
                    {
                        "conversation_id": 1,
                        "session_id": "abc-xyz-123",
                        "user_id": "user-123",
                        "created_at": "2024-01-15T10:30:00",
                        "updated_at": "2024-01-15T11:45:00",
                        "context_data": null
                    },
                    {
                        "conversation_id": 2,
                        "session_id": "def-uvw-456",
                        "user_id": "user-123",
                        "created_at": "2024-01-14T09:20:00",
                        "updated_at": "2024-01-14T10:15:00",
                        "context_data": null
                    }
                ]
            }
        }
        """

        try:
            BotValidation.validate_user_id(user_id)

            result = BotController().get_user_sessions(user_id)

            return {"status": "success", "data": result}, 200

        except AppException as error:
            return error.to_dict(), error.status_code

        except Exception as error:
            error = InternalServerException(details = str(error))
            return error.to_dict(), error.status_code



# ── POST /bot/thread ──────────────────────────────────────────────────────────
@bot_namespace.route("/thread")
class SubmitThread(Resource):
    """
    Submit a previous email thread before starting a bot conversation.

    Thread is OPTIONAL. The bot works perfectly without it.
    When provided, it gives the bot:
      - The investor's name, email, tone, and communication style
      - Which deal is being discussed (auto-detected from thread content)
      - What has already been discussed (so the bot does not repeat it)
      - What the investor's current open question is

    Submitting a new thread for a session that already has one replaces the old one.
    """

    def post(self):
        """
        Parse and store an email thread for a session.

        Request:
        {
            "session_id":      "abc-xyz",          // required — must already exist
            "user_id":         "user-123",          // required
            "raw_thread_text": "From: investor@...", // required — full thread text
            "source":          "manual_paste"       // optional — default: 'manual_paste'
        }

        Response:
        {
            "status": "success",
            "data": {
                "id":                     1,
                "session_id":             "abc-xyz",
                "deal_id":                3,           // null if deal not detected
                "source":                 "manual_paste",
                "parse_status":           "completed", // or "failed"
                "parsed_investor_name":   "John Smith",
                "parsed_investor_email":  "john@example.com",
                "parsed_latest_question": "What is the minimum ticket?",
                "parsed_summary":         "The investor asked about...",
                "parsed_context": {
                    "investor_tone":      "formal",
                    "deal_signals":       ["SpaceX"],
                    "already_discussed":  ["valuation"],
                    "open_items":         ["minimum ticket", "payment dates"],
                    ...
                },
                "created_at": "2024-01-15T10:30:00"
            }
        }

        Notes:
          - If parse_status is "failed", the thread is still stored but the bot
            will not have structured context — it falls back to no-thread mode.
          - deal_id in the response tells you which deal was auto-detected.
            If null, the bot will detect the deal from the conversation as normal.
        """

        try:
            data = request.get_json()
            BotValidation.validate_body(data)

            session_id      = data.get("session_id", "").strip()
            user_id         = data.get("user_id", "").strip()
            raw_thread_text = data.get("raw_thread_text", "")
            source          = data.get("source", "manual_paste").strip()

            BotValidation.validate_session_id(session_id)
            BotValidation.validate_user_id(user_id)
            BotValidation.validate_thread_text(raw_thread_text)

            result = BotController().submit_thread(
                session_id      = session_id,
                raw_thread_text = raw_thread_text,
                user_id         = user_id,
                source          = source
            )

            return {"status": "success", "data": result}, 200

        except AppException as error:
            return error.to_dict(), error.status_code

        except ValueError as error:
            # Raised by ThreadParserService._validate_thread_text()
            return {
                "status":     "error",
                "error_code": "INVALID_THREAD",
                "message":    str(error)
            }, 400

        except Exception as error:
            error = InternalServerException(details=str(error))
            return error.to_dict(), error.status_code



# ── GET / DELETE /bot/thread/<session_id> ─────────────────────────────────────
@bot_namespace.route("/thread/<session_id>")
class ThreadBySession(Resource):
    """Get or remove the active email thread for a session."""

    def get(self, session_id):
        """
        Get the active email thread for a session.

        Response when thread exists:
        {
            "status": "success",
            "data": { ...thread dict... }
        }

        Response when no thread:
        {
            "status": "success",
            "data": null
        }
        """

        try:
            result = BotController().get_thread(session_id = session_id)
            return {"status": "success", "data": result}, 200

        except Exception as error:
            return {"status": "error", "message": str(error)}, 500


    def delete(self, session_id):
        """
        Deactivate (soft-delete) the active thread for a session.

        The thread row is kept in the DB (is_active = false) for audit purposes.
        After deletion, the bot reverts to no-thread mode for this session.

        Response:
        {
            "status": "success",
            "data": {
                "session_id": "abc-xyz",
                "deactivated": true
            }
        }
        """

        try:
            deactivated = BotController().delete_thread(session_id = session_id)
            return {
                "status": "success",
                "data":   {"session_id": session_id, "deactivated": deactivated}
            }, 200

        except Exception as error:
            return {"status": "error", "message": str(error)}, 500
