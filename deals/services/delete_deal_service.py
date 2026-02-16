"""
Delete Deal Service

Handles:
    - Delete Deal
    - Delete related Deal Documents
    - Delete S3 Folder
"""

# Database
from odp.config.database import db

# Models
from ...models.odp_deal import Deal

# Services
from ...vendors.aws.s3_delete import S3DeleteService

# Exceptions
from ...util.exceptions import ServiceException

# App Messages
from ...util import messages





class DeleteDealService:

    def delete_deal(self, deal_id: int) -> dict:
        """
        Delete deal and related documents + S3 folder

        Args:
            deal_id (int)

        Returns:
            dict
        """

        try:
            # 🔹 Fetch Deal
            deal = Deal.query.filter_by(deal_id = deal_id).first()

            if not deal:
                raise ServiceException(
                    error_code = "DEAL_NOT_FOUND",
                    message = messages.ERROR['DEAL_NOT_FOUND']
                )

            # 🔹 Delete S3 Folder FIRST
            prefix = f"odp/deals/{deal_id}/"
            S3DeleteService().delete_folder(prefix)

            # 🔹 Delete Deal (DB)
            db.session.delete(deal)

            db.session.commit()

            return {
                "deal_id": deal_id,
                "message": messages.SUCCESS['DEAL_DELETE_SUCCESS']
            }

        except ServiceException:
            raise

        except Exception as errors:
            db.session.rollback()

            raise ServiceException(
                error_code="DEAL_DELETE_FAILED",
                message=messages.ERROR['DEAL_DELETE_FAILED'],
                details=str(errors)
            )
