"""
Google Document AI Extraction Service

Handles:
    - OCR-based extraction
    - Imageless mode
    - Automatic chunking for large PDFs
    - Intelligent page limit handling
"""

# Python Packages
from io import BytesIO
from typing import List

# Google SDK
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions
from google.oauth2 import service_account

# PDF Utilities
from PyPDF2 import PdfReader, PdfWriter

# Constants
from ...base import constants

# Exceptions
from ...util.exceptions import ServiceException

# Messages
from ...util import messages





class GoogleDocumentAIExtractionService:

    # Google limits:
    # 15 pages normal mode
    # 30 pages imageless mode
    MAX_PAGES_PER_REQUEST = 15

    def __init__(self):
        try:
            credentials = service_account.Credentials.from_service_account_file(
                constants.GOOGLE_APPLICATION_CREDENTIALS
            )

            self.client = documentai.DocumentProcessorServiceClient(
                credentials = credentials,
                client_options = ClientOptions(
                    api_endpoint = f"{constants.GOOGLE_PROJECT_LOCATION}-documentai.googleapis.com"
                )
            )

            self.processor_name = self.client.processor_path(
                constants.GOOGLE_PROJECT_ID,
                constants.GOOGLE_PROJECT_LOCATION,
                constants.GOOGLE_PROJECT_PROCESSOR_ID
            )

        except Exception as error:
            raise ServiceException(
                error_code = "GOOGLE_INIT_FAILED",
                message = messages.ERROR["GOOGLE_INIT_FAILED"],
                details = str(error)
            )


    # ==========================================================
    # PUBLIC METHOD
    # ==========================================================

    def extract(self, file_bytes: bytes) -> str:
        """
        Extract text from PDF using Google Document AI.

        Automatically handles:
            - Imageless mode
            - Page limit splitting
        """

        try:
            total_pages = self._get_pdf_page_count(file_bytes)

            # If within limit → single call
            if total_pages <= self.MAX_PAGES_PER_REQUEST:
                return self._process_chunk(file_bytes)

            # If exceeds limit → split
            chunks = self._split_pdf_into_chunks(
                pdf_bytes = file_bytes,
                max_pages = self.MAX_PAGES_PER_REQUEST
            )

            full_text = ""

            for chunk in chunks:
                full_text += self._process_chunk(chunk) + "\n"

            if not full_text.strip():
                raise ServiceException(
                    error_code = "GOOGLE_EMPTY_RESPONSE",
                    message = messages.ERROR["GOOGLE_EMPTY_RESPONSE"]
                )

            return full_text

        except ServiceException:
            raise

        except Exception as error:
            raise ServiceException(
                error_code = "GOOGLE_DOC_AI_FAILED",
                message = messages.ERROR["GOOGLE_DOC_AI_FAILED"],
                details = str(error)
            )


    # ==========================================================
    # INTERNAL PROCESSING
    # ==========================================================

    def _process_chunk(self, chunk_bytes: bytes) -> str:
        """
        Process single PDF chunk via Google API
        """

        request = documentai.ProcessRequest(
            name = self.processor_name,
            raw_document = documentai.RawDocument(
                content = chunk_bytes,
                mime_type = "application/pdf"
            ),
            process_options = documentai.ProcessOptions(
                ocr_config = documentai.OcrConfig(
                    enable_native_pdf_parsing = True
                )
            )
        )

        result = self.client.process_document(request=request)

        return result.document.text or ""





    # ==========================================================
    # HELPER METHODS
    # ==========================================================

    def _get_pdf_page_count(self, pdf_bytes: bytes) -> int:
        """
        Return number of pages in PDF
        """

        reader = PdfReader(BytesIO(pdf_bytes))
        return len(reader.pages)



    def _split_pdf_into_chunks(self, pdf_bytes: bytes, max_pages: int) -> List[bytes]:
        """
        Split PDF bytes into smaller chunks of max_pages
        """

        reader = PdfReader(BytesIO(pdf_bytes))
        chunks = []

        for i in range(0, len(reader.pages), max_pages):
            writer = PdfWriter()

            for page in reader.pages[i:i + max_pages]:
                writer.add_page(page)

            output_stream = BytesIO()
            writer.write(output_stream)
            chunks.append(output_stream.getvalue())

        return chunks
