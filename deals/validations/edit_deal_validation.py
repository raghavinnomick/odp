"""
Edit Deal Validation

Checks:
    - deal_id is provided
    - deal exists
    - deal_name is provided
    - deal_name is not already used by another deal
"""

# Models
from ...models.odp_deal import Deal

# App Messages
from ...util import messages

# Exceptions
from ...util.exceptions import ValidationException





class EditDealValidation:

    def validate(self, args: dict):

        deal_id = args.get("deal_id")
        deal_name = args.get("deal_name")

        # 🔹 Check deal_id
        if not deal_id:
            raise ValidationException(
                message = messages.ERROR['INVALID_DEAL_ID']
            )

        # 🔹 Check deal_name
        if not deal_name or not deal_name.strip():
            raise ValidationException(
                message = messages.ERROR['INVALID_DEAL_NAME']
            )

        # 🔹 Check if Deal exists
        deal = Deal.query.filter_by(deal_id = deal_id).first()

        if not deal:
            raise ValidationException(
                message = messages.ERROR['DEAL_NOT_FOUND']
            )

        # 🔹 Check duplicate name (excluding current deal)
        existing = Deal.query.filter(
            Deal.deal_name.ilike(deal_name),
            Deal.deal_id != deal_id
        ).first()

        if existing:
            raise ValidationException(
                message = messages.ERROR['DEAL_NAME_ALREADY_EXISTS']
            )
