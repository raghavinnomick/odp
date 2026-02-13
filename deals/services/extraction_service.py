"""
Deal Document Extraction Service

Flow:
    - Fetch document by doc_id
    - Get file from S3
    - Pass to DocumentExtractionOrchestrator
    - Return preview + metadata
"""

# Database
from odp.config.database import db

# Models
from ...models.odp_deal_document import DealDocument

# Vendors
from ...vendors.aws.s3_direct_reader import S3DirectReader

# Document Processing
from ...document_processing.services.document_extraction_orchestrator import (
    DocumentExtractionOrchestrator
)

# Exceptions
from ...util.exceptions import ServiceException

# Messages
from ...util import messages





class DealDocumentExtractionService:

    PREVIEW_LENGTH = 1000

    def extract_text_by_doc_id(self, doc_id: int) -> dict:

        try:
            # 1️⃣ Fetch document
            document = db.session.query(DealDocument)\
                .filter(DealDocument.doc_id == doc_id)\
                .first()

            if not document:
                raise ServiceException(
                    error_code = "DOCUMENT_NOT_FOUND",
                    message = messages.ERROR["DOCUMENT_NOT_FOUND"]
                )

            if not document.storage_path:
                raise ServiceException(
                    error_code = "INVALID_STORAGE_PATH",
                    message = messages.ERROR["DOCUMENT_STORAGE_MISSING"]
                )

            # 2️⃣ Fetch file from S3
            file_bytes, extension = S3DirectReader().get_file_from_s3(
                document.storage_path
            )

            # 3️⃣ Orchestrate extraction
            extraction_result = DocumentExtractionOrchestrator().extract(
                file_bytes = file_bytes,
                extension = extension
            )

            extracted_text = extraction_result["text"]
            engine_used = extraction_result["engine_used"]

            # 4️⃣ Return metadata + preview
            return {
                "doc_id": doc_id,
                "deal_id": document.deal_id,
                "document_name": document.doc_name,
                "engine_used": engine_used,
                "text_length": len(extracted_text),
                "text_preview": extracted_text[:self.PREVIEW_LENGTH]
            }

        except ServiceException:
            raise

        except Exception as errors:
            raise ServiceException(
                error_code = "DOCUMENT_EXTRACTION_FAILED",
                message = messages.ERROR["DOCUMENT_EXTRACTION_FAILED"],
                details = str(errors)
            )
