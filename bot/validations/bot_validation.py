"""
Bot validation for all bot endpoints.
"""

# Exceptions
from ...util.exceptions import AppException

# Messages
from ...util import messages





class BotValidation:

    @staticmethod
    def validate_body(data):
        if not data:
            raise AppException(
                error_code = "INVALID_REQUEST",
                message = messages.ERROR["INVALID_REQUEST"]
            )


    @staticmethod
    def validate_question(question):
        if not question:
            raise AppException(
                error_code = "MISSING_QUESTION",
                message = messages.ERROR["MISSING_QUESTION"]
            )

        if not isinstance(question, str) or len(question.strip()) == 0:
            raise AppException(
                error_code = "INVALID_QUESTION",
                message = messages.ERROR["INVALID_QUESTION"]
            )


    @staticmethod
    def validate_top_k(top_k):
        if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
            raise AppException(
                error_code = "INVALID_TOP_K",
                message = messages.ERROR["INVALID_TOP_K"]
            )


    @staticmethod
    def validate_user_id(user_id):
        if not user_id:
            raise AppException(
                error_code = "MISSING_USER_ID",
                message = messages.ERROR["MISSING_USER_ID"]
            )

        if not isinstance(user_id, str) or len(user_id.strip()) == 0:
            raise AppException(
                error_code = "INVALID_USER_ID",
                message = messages.ERROR["INVALID_USER_ID"]
            )


    @staticmethod
    def validate_thread_text(thread_text):
        """
        Validate raw email thread text before storing.
        Length limits come from config/bot_config.py.
        """
        from ..config import bot_config

        if not thread_text:
            raise AppException(
                error_code  = "MISSING_THREAD_TEXT",
                message     = "thread_text is required.",
                status_code = 400
            )

        if not isinstance(thread_text, str):
            raise AppException(
                error_code  = "INVALID_THREAD_TEXT",
                message     = "thread_text must be a string.",
                status_code = 400
            )

        stripped = thread_text.strip()

        if len(stripped) < bot_config.BOT_THREAD_MIN_LENGTH:
            raise AppException(
                error_code  = "THREAD_TOO_SHORT",
                message     = f"thread_text must be at least {bot_config.BOT_THREAD_MIN_LENGTH} characters.",
                status_code = 400
            )

        if len(stripped) > bot_config.BOT_THREAD_MAX_LENGTH:
            raise AppException(
                error_code  = "THREAD_TOO_LONG",
                message     = f"thread_text must not exceed {bot_config.BOT_THREAD_MAX_LENGTH} characters.",
                status_code = 400
            )


    @staticmethod
    def validate_session_id(session_id):
        if not session_id or not isinstance(session_id, str) or not session_id.strip():
            raise AppException(
                error_code  = "MISSING_SESSION_ID",
                message     = messages.ERROR.get("MISSING_SESSION_ID", "session_id is required."),
                status_code = 400
            )
