"""
Deal Controller

Handles:
    - Orchestration between handler and service layer
"""

# Services
from .services.add_deal_service import AddDealService





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
