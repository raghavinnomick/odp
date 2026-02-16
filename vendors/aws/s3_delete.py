"""
S3 Delete Service

Handles:
    - Delete single object
    - Delete entire folder (prefix)
    - Safe pagination (more than 1000 objects)
"""

# Python Packages
import boto3

# Constants
from ...base import constants





class S3DeleteService:
    """
    AWS S3 Delete Operations
    """

    def __init__(self):
        """
        Initialize S3 client using environment constants
        """

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id = constants.AWS_ACCESS_KEY_ID,
            aws_secret_access_key = constants.AWS_SECRET_ACCESS_KEY,
            region_name = constants.AWS_REGION
        )

        self.bucket_name = constants.AWS_S3_BUCKET_NAME


    # ---------------------------------------------------------
    # 🔹 Delete Single File
    # ---------------------------------------------------------
    def delete_file(self, s3_key: str):
        """
        Delete a single file from S3

        Args:
            s3_key (str): Full S3 object key
        """

        try:
            self.s3_client.delete_object(
                Bucket = self.bucket_name,
                Key = s3_key
            )

        except Exception as e:
            raise Exception(f"S3 file delete failed: {str(e)}")


    # ---------------------------------------------------------
    # 🔹 Delete Folder (Prefix)
    # ---------------------------------------------------------
    def delete_folder(self, prefix: str):
        """
        Delete all objects under a given prefix (folder)

        Args:
            prefix (str): e.g. odp/deals/10/
        """

        try:
            continuation_token = None

            while True:
                # List objects
                if continuation_token:
                    response = self.s3_client.list_objects_v2(
                        Bucket = self.bucket_name,
                        Prefix = prefix,
                        ContinuationToken = continuation_token
                    )
                else:
                    response = self.s3_client.list_objects_v2(
                        Bucket = self.bucket_name,
                        Prefix = prefix
                    )

                # If no objects found
                if "Contents" not in response:
                    break

                # Prepare delete list
                objects_to_delete = [
                    {"Key": obj["Key"]}
                    for obj in response["Contents"]
                ]

                # Delete batch
                self.s3_client.delete_objects(
                    Bucket = self.bucket_name,
                    Delete = {"Objects": objects_to_delete}
                )

                # Check if more objects exist
                if response.get("IsTruncated"):
                    continuation_token = response.get("NextContinuationToken")

                else:
                    break

        except Exception as e:
            raise Exception(f"S3 folder delete failed: {str(e)}")
