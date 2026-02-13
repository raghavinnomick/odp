"""
PDFPlumber Extraction Service

Responsible for:
    - Extracting text from PDF and DOCX files
    - No fallback logic
    - No S3 logic
"""

# Python Packages
from io import BytesIO
import pdfplumber
from docx import Document

# Exceptions
from ...util.exceptions import ServiceException

# Messages
from ...util import messages





class PDFPlumberExtractionService:
    """
    Handles extraction using:
        - pdfplumber (PDF)
        - python-docx (DOCX)
    """

    def extract(self, file_bytes: bytes, extension: str) -> str:
        """
        Extract text from file bytes.

        Args:
            file_bytes (bytes)
            extension (str)

        Returns:
            str
        """

        try:
            extension = extension.lower()

            # --------------------------------------------------
            # PDF Extraction
            # --------------------------------------------------
            if extension == "pdf":
                return self._extract_pdf(file_bytes)

            # --------------------------------------------------
            # DOCX Extraction
            # --------------------------------------------------
            elif extension == "docx":
                return self._extract_docx(file_bytes)

            else:
                raise ServiceException(
                    error_code = "UNSUPPORTED_FILE_TYPE",
                    message = messages.ERROR["UNSUPPORTED_FILE_FORMAT"].format(file_extension = extension)
                )

        except ServiceException:
            raise

        except Exception as error:
            raise ServiceException(
                error_code = "PDFPLUMBER_EXTRACTION_FAILED",
                message = messages.ERROR["UNSUPPORTED_FILE_FORMAT"],
                details = str(error)
            )



    def _extract_pdf(self, file_bytes: bytes) -> str:
        """
        Extract text from PDF using pdfplumber
        """

        text = ""

        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        return text



    def _extract_docx(self, file_bytes: bytes) -> str:
        """
        Extract text from DOCX using python-docx
        """

        document = Document(BytesIO(file_bytes))
        return "\n".join(
            paragraph.text for paragraph in document.paragraphs
        )
