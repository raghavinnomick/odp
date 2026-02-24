"""
Application Custom Exceptions

Purpose:
    - Standardize error handling across ODP
    - Prevent leaking internal errors
    - Maintain consistent API error format
"""





class AppException(Exception):
    """
    Base application exception.
    """

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 400,
        details: str = None
    ):
        """
        Args:
            error_code (str): Unique business error identifier
            message (str): User-friendly error message
            status_code (int): HTTP status code (default: 400)
            details (str): Optional internal/debug details
        """

        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details

        super().__init__(message)



    def to_dict(self) -> dict:
        """
        Convert exception to standardized API response format.
        """

        response = {
            "status": "error",
            "error_code": self.error_code,
            "message": self.message
        }

        if self.details:
            response["details"] = self.details

        return response





# --------------------------------------------
# Specific Exception Types
# --------------------------------------------

class ValidationException(AppException):
    """
    Raised when validation fails.
    """

    def __init__(self, message: str, details: str = None):
        super().__init__(
            error_code = "VALIDATION_ERROR",
            message = message,
            status_code = 400,
            details = details
        )





class ServiceException(AppException):
    """
    Raised when business logic fails.
    """

    def __init__(self, error_code: str, message: str, details: str = None):
        super().__init__(
            error_code = error_code,
            message = message,
            status_code = 400,
            details = details
        )





class NotFoundException(AppException):
    """
    Raised when resource is not found.
    """

    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            error_code = "NOT_FOUND",
            message = message,
            status_code = 404
        )





class UnauthorizedException(AppException):
    """
    Raised when authentication fails.
    """

    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(
            error_code = "UNAUTHORIZED",
            message = message,
            status_code = 401
        )





class InternalServerException(AppException):
    """
    Raised for unexpected system errors.
    """

    def __init__(self, details: str = None):
        super().__init__(
            error_code = "INTERNAL_SERVER_ERROR",
            message = "Something went wrong. Please try again later.",
            status_code = 500,
            details  = details
        )
