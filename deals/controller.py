"""
Deal Controller

Handles:
    - Orchestration between handler and service layer
"""

# Services
from .services.add_deal_service import AddDealService
from .services.list_deal_service import ListDealService
from .services.edit_deal_service import EditDealService
from .services.delete_deal_service import DeleteDealService
from .services.extraction_service import DealDocumentExtractionService
from .services.document_process_service import DocumentProcessService





class DealController:

    def __init__(self):
        """ Initialize controller with service instances... """

        self.extraction_service = DealDocumentExtractionService()
        self.process_service = DocumentProcessService()


    def create_deal(self, args: dict) -> dict:
        """
        Create deal and upload document

        Args:
            args (dict):
                {
                    "deal_name": str,
                    "file": FileStorage
                }

        Returns:
            dict: API response
        """
        # Call Service Layer
        result = AddDealService().create_deal(args)
        return result



    def list_deals(self, search: str = None) -> dict:
        """
        List deals with optional search

        Args:
            search (str): Deal name search text

        Returns:
            dict
        """

        return ListDealService().list_deals(search)



    def edit_deal(self, args: dict) -> dict:
        """
        Edit deal name only

        Args:
            deal_id (int)
            args (dict): {"deal_name": str}

        Returns:
            dict
        """

        return EditDealService().edit_deal(args)



    def delete_deal(self, deal_id: int) -> dict:
        """
        Delete deal and related records

        Args:
            deal_id (int)

        Returns:
            dict
        """

        return DeleteDealService().delete_deal(deal_id)



    def process_deal_document(self, doc_id: int) -> dict:
        """
        Process uploaded deal document
        Flow:
            1. Extract text from document
            2. Chunk text and generate embeddings
            3. Store in database
        
        Args:
            doc_id (int): Deal Document ID
        
        Returns:
            dict: Complete processing result
        """

        # Step 1: Extract text
        extraction_result = self.extraction_service.extract_text_by_doc_id(doc_id)

        # Step 2: Process chunks and embeddings
        process_result = self.process_service.process_and_store(
            deal_id = extraction_result["deal_id"],
            doc_id = extraction_result["doc_id"],
            extracted_text = extraction_result["extracted_text"],
            doc_name = extraction_result["document_name"]
        )

        # Step 3: Combine results (remove full text from response)
        return {
            "doc_id": extraction_result["doc_id"],
            "deal_id": extraction_result["deal_id"],
            "document_name": extraction_result["document_name"],
            "engine_used": extraction_result["engine_used"],
            "text_length": extraction_result["text_length"],
            "text_preview": extraction_result["text_preview"],

            # Processing results
            "chunks_created": process_result["chunks_created"],
            "embeddings_generated": process_result["embeddings_generated"],
            "processing_status": process_result["status"]
        }
