"""
Document Background Tasks
"""

# Python Packages
from celery import shared_task

# Services only (NO controller import)
from ..services.extraction_service import DealDocumentExtractionService
from ..services.document_process_service import DocumentProcessService





@shared_task(bind=True, max_retries=3)
def process_deal_document_task(self, doc_id: int):
    """
    Background task to process deal document
    """

    try:
        # Step 1: Extract
        extraction_service = DealDocumentExtractionService()
        extraction_result = extraction_service.extract_text_by_doc_id(doc_id)

        # Step 2: Chunk + Embed
        process_service = DocumentProcessService()
        process_service.process_and_store(
            deal_id = extraction_result["deal_id"],
            doc_id = extraction_result["doc_id"],
            extracted_text = extraction_result["extracted_text"],
            doc_name = extraction_result["document_name"]
        )

    except Exception as e:
        raise self.retry(exc = e, countdown = 10)
