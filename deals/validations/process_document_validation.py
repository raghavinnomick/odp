"""
Process Deal Document Validation
"""

# Exceptions
from ...util.exceptions import ValidationException

# Messages
from ...util import messages





class ProcessDocumentValidation:

    def validate(self, doc_id: int):
        """
        Validate doc_id for document processing
        """

        if not doc_id:
            raise ValidationException(
                message = messages.ERROR['DOCUMENT_ID_REQUIRED']
            )

        if not isinstance(doc_id, int):
            raise ValidationException(
                message = messages.ERROR['INVALID_DOCUMENT_ID']
            )

        if doc_id <= 0:
            raise ValidationException(
                message = messages.ERROR['INVALID_DOCUMENT_ID']
            )

        return True
