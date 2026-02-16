"""
Deal Service

Handles:
    - Create Deal
    - Upload Document to S3
    - Store Deal + Document metadata
    - Trigger document processing
"""

# Python Packages
import re
from datetime import datetime

# Database
from odp.config.database import db

# Models
from ...models.odp_deal import Deal
from ...models.odp_deal_document import DealDocument

# Vendors
from ...vendors.aws.s3_uploader import S3Uploader

# Exceptions
from ...util.exceptions import ServiceException

# Tasks (optional - only if Celery is configured)
try:
    from ..tasks.document_tasks import process_deal_document_task
    CELERY_AVAILABLE = True

except Exception:
    CELERY_AVAILABLE = False

# Services for sync processing
from .extraction_service import DealDocumentExtractionService
from .document_process_service import DocumentProcessService





class AddDealService:

    def create_deal(self, args: dict) -> dict:
        """
        Create deal and upload document

        Args:
            args (dict):
                {
                    "deal_name": str,
                    "file": FileStorage,
                    "process_async": bool (optional, default False)
                }

        Returns:
            dict
        """

        deal_name = args.get("deal_name")
        deal_code = self._generate_deal_code(deal_name)
        file = args.get("file")
        process_async = args.get("process_async", False)  # Default to sync

        # Start DB transaction
        try:
            # 1️⃣ Create Deal
            deal = Deal(
                deal_name = deal_name,
                deal_code = deal_code,
                status = True 
            )
            db.session.add(deal)
            db.session.flush()  # Get deal_id before commit


            # 2️⃣ Upload File to S3
            s3_key = f"odp/deals/{deal.deal_id}/{file.filename}"

            s3_path = S3Uploader().upload_file(
                file_obj = file,
                s3_key = s3_key
            )


            # 3️⃣ Store Document Metadata
            document = DealDocument(
                deal_id = deal.deal_id,
                doc_name = file.filename,
                doc_type = "investment_memo", # Change it later
                storage_path = s3_path,
                version = "v1"
            )
            db.session.add(document)

            # 4️⃣ Commit Transaction
            db.session.commit()

            # 5️⃣ Process Document
            processing_result = None
            
            if process_async and CELERY_AVAILABLE:
                # Async processing with Celery
                print(f"📋 Queuing async processing for doc_id: {document.doc_id}")
                task = process_deal_document_task.delay(document.doc_id)
                processing_result = {
                    "processing_mode": "async",
                    "task_id": task.id,
                    "message": "Document processing queued in background"
                }
            else:
                # Synchronous processing (default)
                print(f"⚡ Processing document synchronously: {document.doc_id}")
                processing_result = self._process_document_sync(
                    doc_id = document.doc_id,
                    deal_id = deal.deal_id
                )

            return {
                "deal_id": deal.deal_id,
                "deal_name": deal.deal_name,
                "deal_code": deal.deal_code,
                "doc_id": document.doc_id,
                "document_name": file.filename,
                "processing": processing_result
            }

        except Exception as errors:
            # Rollback DB changes
            db.session.rollback()

            raise ServiceException(
                error_code = "DEAL_CREATE_FAILED",
                message = "Unable to create deal. Please try again.",
                details = str(errors)
            )


    def _process_document_sync(self, doc_id: int, deal_id: int) -> dict:
        """
        Process document synchronously (immediately)
        
        Args:
            doc_id: Document ID
            deal_id: Deal ID
        
        Returns:
            dict: Processing result
        """
        
        try:
            # Step 1: Extract text
            extraction_service = DealDocumentExtractionService()
            extraction_result = extraction_service.extract_text_by_doc_id(doc_id)

            # Step 2: Chunk + Embed
            process_service = DocumentProcessService()
            process_result = process_service.process_and_store(
                deal_id = extraction_result["deal_id"],
                doc_id = extraction_result["doc_id"],
                extracted_text = extraction_result["extracted_text"],
                doc_name = extraction_result["document_name"]
            )

            return {
                "processing_mode": "sync",
                "status": "completed",
                "chunks_created": process_result["chunks_created"],
                "embeddings_generated": process_result["embeddings_generated"],
                "text_length": extraction_result["text_length"]
            }

        except Exception as e:
            print(f"❌ Sync processing failed: {str(e)}")
            return {
                "processing_mode": "sync",
                "status": "failed",
                "error": str(e)
            }


    def _generate_deal_code(self, deal_name: str) -> str:
        """
        Generate unique deal code based on name
        """

        # Remove special characters
        cleaned = re.sub(r'[^A-Za-z0-9 ]+', '', deal_name)

        # Replace spaces with hyphen
        slug = cleaned.strip().replace(" ", "-").upper()

        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        return f"{slug}-{timestamp}"
