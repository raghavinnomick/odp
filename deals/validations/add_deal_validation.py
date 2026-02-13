""" Add Deal Validation... """

# App Constants
from ...base import constants

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

        # Deal Name Validation
        if not deal_name:
            raise ValidationException(
                message = messages.ERROR['ADD_DEAL_NAME_REQUIRED']
            )

        if len(deal_name.strip()) < 5:
            raise ValidationException(
                message = messages.ERROR.get("ADD_DEAL_NAME_MIN").format(5)
            )


        # File Validation
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
