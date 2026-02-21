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
