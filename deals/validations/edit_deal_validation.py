"""
Edit Deal Validation

Checks:
    - deal_id is provided
    - deal_id is integer
    - deal exists
    - deal_name is provided
    - deal_name minimum length
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

        # -----------------------------------------
        # 🔹 Deal ID Validation
        # -----------------------------------------

        if not deal_id:
            raise ValidationException(
                message = messages.ERROR['INVALID_DEAL_ID']
            )

        if not isinstance(deal_id, int):
            raise ValidationException(
                message = messages.ERROR['INVALID_DEAL_ID']
            )

        # -----------------------------------------
        # 🔹 Deal Name Validation
        # -----------------------------------------

        if not deal_name:
            raise ValidationException(
                message = messages.ERROR['INVALID_DEAL_NAME']
            )

        deal_name = deal_name.strip()

        if len(deal_name) < 5:
            raise ValidationException(
                message = messages.ERROR.get("ADD_DEAL_NAME_MIN").format(5)
            )

        # Optional: prevent only spaces
        if not deal_name:
            raise ValidationException(
                message = messages.ERROR['INVALID_DEAL_NAME']
            )

        # -----------------------------------------
        # 🔹 Check if Deal Exists
        # -----------------------------------------

        deal = Deal.query.filter_by(deal_id=deal_id).first()

        if not deal:
            raise ValidationException(
                message = messages.ERROR['DEAL_NOT_FOUND']
            )

        # -----------------------------------------
        # 🔹 Duplicate Name Check (Case-Insensitive)
        # -----------------------------------------

        existing = Deal.query.filter(
            Deal.deal_name.ilike(deal_name),
            Deal.deal_id != deal_id
        ).first()

        if existing:
            raise ValidationException(
                message = messages.ERROR['DEAL_NAME_ALREADY_EXISTS']
            )

        return True
