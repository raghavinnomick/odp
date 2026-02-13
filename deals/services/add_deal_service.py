"""
Deal Service

Handles:
    - Create Deal
    - Upload Document to S3
    - Store Deal + Document metadata
"""

# Python Packages
import re
from datetime import datetime

# Database
from odp.config.database import db

# Models
from ...models.odp_deal import Deal
from ...models.odp_deal_document import DealDocument

# Vendors
from ...vendors.aws.s3_uploader import S3Uploader

# Expections
from ...util.exceptions import ServiceException





class AddDealService:

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
            dict
        """

        deal_name = args.get("deal_name")
        deal_code = self._generate_deal_code(deal_name)
        file = args.get("file")

        # Start DB transaction
        try:
            # 1️⃣ Create Deal
            deal = Deal(
                deal_name = deal_name,
                deal_code = deal_code,
                status = False # Draft 
            )
            db.session.add(deal)
            db.session.flush()  # Get deal_id before commit


            # 2️⃣ Upload File to S3
            s3_key = f"odp/deals/{deal.deal_id}/{file.filename}"

            s3_path = S3Uploader().upload_file(
                file_obj = file,
                s3_key = s3_key
            )


            # 3️⃣ Store Document Metadata
            document = DealDocument(
                deal_id = deal.deal_id,
                doc_name = file.filename,
                doc_type = "investment_memo", # Change it later
                storage_path = s3_path,
                version = "v1"
            )
            db.session.add(document)


            # 4️⃣ Commit Transaction
            db.session.commit()
            
            return {
                "deal_id": deal.deal_id,
                "deal_name": deal.deal_name,
                "document_name": file.filename
            }

        except Exception as errors:
            # Rollback DB changes
            db.session.rollback()

            raise ServiceException(
                error_code = "DEAL_CREATE_FAILED",
                message = "Unable to create deal. Please try again.",
                details = str(e)  # optional (remove in production)
            )



    def _generate_deal_code(self, deal_name: str) -> str:
        """
        Generate unique deal code based on name
        """

        # Remove special characters
        cleaned = re.sub(r'[^A-Za-z0-9 ]+', '', deal_name)

        # Replace spaces with hyphen
        slug = cleaned.strip().replace(" ", "-").upper()

        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        return f"{slug}-{timestamp}"
