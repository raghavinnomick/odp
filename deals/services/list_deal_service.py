"""
List Deal Service

Handles:
    - Fetch all deals
    - Search by deal name
"""

# Database
from odp.config.database import db

# Models
from ...models.odp_deal import Deal

# SQLAlchemy
from sqlalchemy import or_





class ListDealService:

    def list_deals(self, search: str = None) -> dict:
        """
        Fetch deal list with optional search

        Args:
            search (str): Deal name search keyword

        Returns:
            dict
        """

        query = Deal.query

        # 🔎 Apply Search Filter
        if search:
            query = query.filter(
                Deal.deal_name.ilike(f"%{search}%")
            )

        # Order latest first
        deals = query.order_by(Deal.deal_id.desc()).all()

        return {
            "total": len(deals),
            "deals": [
                {
                    "deal_id": deal.deal_id,
                    "deal_name": deal.deal_name,
                    "deal_code": deal.deal_code,
                    "status": deal.status
                }
                for deal in deals
            ]
        }
