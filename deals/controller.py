"""
Deal Controller

Handles:
    - Orchestration between handler and service layer
"""

# Services
from .services.add_deal_service import AddDealService
from .services.extraction_service import DealDocumentExtractionService





class DealController:

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

        # You can format response here if needed
        return result



    def process_deal_document(self, doc_id: int) -> dict:
        """
        Process uploaded deal document

        Step-2 Part-1:
            - Fetch document by doc_id
            - Extract text from S3
            - Return preview + metadata

        Args:
            doc_id (int): Deal Document ID

        Returns:
            dict: Extraction result
        """

        # Call Service Layer
        result = DealDocumentExtractionService().extract_text_by_doc_id(doc_id)

        return result
