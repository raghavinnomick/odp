"""
Add Deal Validation
"""

# Models
from ...models.odp_deal import Deal

# App Messages
from ...util import messages

# Exceptions
from ...util.exceptions import ValidationException





class AddDealValidation:

    def validate(self, args):
        """
        Validate full arguments
        """

        deal_name = args.get('deal_name')
        file = args.get('file')

        # -----------------------------------------
        # 🔹 Deal Name Validation
        # -----------------------------------------

        if not deal_name:
            raise ValidationException(
                message = messages.ERROR['ADD_DEAL_NAME_REQUIRED']
            )

        deal_name = deal_name.strip()

        if len(deal_name) < 5:
            raise ValidationException(
                message = messages.ERROR.get("ADD_DEAL_NAME_MIN").format(5)
            )

        # 🔥 NEW: Unique Deal Name Validation
        existing = Deal.query.filter(
            Deal.deal_name.ilike(deal_name)
        ).first()

        if existing:
            raise ValidationException(
                message = messages.ERROR['DEAL_NAME_ALREADY_EXISTS']
            )

        # -----------------------------------------
        # 🔹 File Validation
        # -----------------------------------------

        if not file:
            raise ValidationException(
                message = messages.ERROR['ADD_DEAL_FILE_REQUIRED']
            )

        filename = file.filename

        if not filename:
            raise ValidationException(
                message = messages.ERROR['ADD_DEAL_INVALID_FILE']
            )

        ext = filename.rsplit('.', 1)[-1].lower()

        if ext not in {'pdf'}:
            raise ValidationException(
                message = messages.ERROR["UNSUPPORTED_FILE_FORMAT"].format(
                    file_extension = ext.upper()
                )
            )

        return True
