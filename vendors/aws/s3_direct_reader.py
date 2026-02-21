"""
S3 Direct Reader

Handles:
    - Fetching file from S3
"""

# Python Packages
import boto3
from typing import Tuple

# Constants
from ...base import constants





class S3DirectReader:
    """
    Directly retrieves file bytes from S3 bucket.
    """

    def __init__(self):
        """ Initialize S3 client with credentials and bucket name from constants."""

        self.bucket_name = constants.AWS_S3_BUCKET_NAME

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id = constants.AWS_ACCESS_KEY_ID,
            aws_secret_access_key = constants.AWS_SECRET_ACCESS_KEY,
            region_name = constants.AWS_REGION
        )



    def _normalize_s3_key(self, s3_path: str) -> str:
        """
        Convert stored S3 path into valid S3 Key
        """

        key = s3_path

        if s3_path.startswith("s3://"):
            key = s3_path.replace(f"s3://{self.bucket_name}/", "")

        if "amazonaws.com/" in key:
            key = key.split("amazonaws.com/")[-1]

        return key



    def get_file_from_s3(self, s3_path: str) -> Tuple[bytes, str]:
        """
        Fetch file bytes and extension from S3

        Returns:
            Tuple[bytes, str] → (file_bytes, extension)
        """

        try:
            key = self._normalize_s3_key(s3_path)

            response = self.s3_client.get_object(
                Bucket = self.bucket_name,
                Key = key
            )

            file_bytes = response["Body"].read()
            file_extension = key.lower().split('.')[-1]

            return file_bytes, file_extension

        except Exception as error:
            raise Exception(
                f"S3 File Fetch Failed: {str(error)}"
            )
