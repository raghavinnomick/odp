"""
Document Extraction Orchestrator

Responsible for:
    - Selecting extraction engine
    - Handling fallback logic
    - Returning final extracted text
"""

# Extraction Engines
from .pdfplumber_extraction_service import PDFPlumberExtractionService
from .google_doc_ai_extraction_service import GoogleDocumentAIExtractionService

# Exceptions
from ...util.exceptions import ServiceException

# Messages
from ...util import messages





class DocumentExtractionOrchestrator:
    """
    Central decision engine for document extraction
    """

    def __init__(self):
        self.pdf_engine = PDFPlumberExtractionService()
        self.google_engine = GoogleDocumentAIExtractionService()



    def _is_text_valid(self, text: str) -> bool:
        """
        Intelligent extraction validation

        Returns False when:
            - Text is empty
            - Mostly whitespace
            - Too few alphabetic characters (likely scanned image)
        """

        if not text:
            return False

        stripped = text.strip()

        if len(stripped) == 0:
            return False

        # Count alphabetic characters
        alpha_chars = sum(c.isalpha() for c in stripped)
        total_chars = len(stripped)

        # Ratio of meaningful text
        ratio = alpha_chars / max(total_chars, 1)

        # If less than 10% alphabetic content → suspicious
        if ratio < 0.1:
            return False

        return True



    def extract(self, file_bytes: bytes, extension: str) -> dict:
        """
        Extract text using best available engine.

        Args:
            file_bytes (bytes)
            extension (str)

        Returns:
            dict:
                {
                    "text": str,
                    "engine_used": str
                }
        """

        try:
            extracted_text = ""

            # --------------------------------------------------
            # Primary Engine (PDF / DOCX)
            # --------------------------------------------------

            if extension in ["pdf", "docx"]:
                """
                extracted_text = self.pdf_engine.extract(
                    file_bytes = file_bytes,
                    extension = extension
                )

                # Validate quality
                if not self._is_text_valid(extracted_text):
                    # Fallback to Google OCR
                    extracted_text = self.google_engine.extract(
                        file_bytes = file_bytes
                    )

                    return {
                        "text": extracted_text,
                        "engine_used": "GOOGLE_DOCUMENT_AI"
                    }

                return {
                    "text": extracted_text,
                    "engine_used": "PDFPLUMBER"
                }
                """

                # Fallback to Google OCR
                extracted_text = self.google_engine.extract(
                    file_bytes = file_bytes
                )

                return {
                    "text": extracted_text,
                    "engine_used": "GOOGLE_DOCUMENT_AI"
                }

            raise ServiceException(
                error_code = "UNSUPPORTED_FILE_TYPE",
                message = messages.ERROR["UNSUPPORTED_FILE_FORMAT"].format(file_extension = file_extension)
            )

        except ServiceException:
            raise

        except Exception as error:
            raise ServiceException(
                error_code = "DOCUMENT_EXTRACTION_FAILED",
                message = messages.ERROR["DOCUMENT_EXTRACTION_FAILED"],
                details = str(error)
            )
