"""
Edit Deal Service

Handles:
    - Update Deal Name only
"""

# Database
from odp.config.database import db

# Models
from ...models.odp_deal import Deal

# Exceptions
from ...util.exceptions import ServiceException

# App Messages
from ...util import messages





class EditDealService:

    def edit_deal(self, args: dict) -> dict:
        """
        Update deal name only

        Args:
            deal_id (int)
            args (dict)

        Returns:
            dict
        """

        deal_id = args.get("deal_id")
        new_deal_name = args.get("deal_name")

        try:
            deal = Deal.query.filter_by(deal_id = deal_id).first()

            deal.deal_name = new_deal_name

            db.session.commit()

            return {
                "deal_id": deal.deal_id,
                "deal_name": deal.deal_name,
                "message": messages.SUCCESS['DEAL_UPDATE_SUCCESS'],
            }

        except Exception as errors:
            db.session.rollback()

            raise ServiceException(
                error_code="DEAL_UPDATE_FAILED",
                message = messages.ERROR['DEAL_UPDATE_FAILED'],
                details = str(errors)
            )
