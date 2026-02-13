""" File: S3 Uploader Service """

# Python Packages
import boto3

# Constants
from ...base import constants





class S3Uploader:

    def __init__(self):
        self.bucket_name = constants.AWS_S3_BUCKET_NAME
        self.client = boto3.client(
            's3',
            aws_access_key_id = constants.AWS_ACCESS_KEY_ID,
            aws_secret_access_key = constants.AWS_SECRET_ACCESS_KEY,
            region_name = constants.AWS_REGION
        )

    def upload_file(self, file_obj, s3_key):
        """
        Upload file object to S3
        """

        self.client.upload_fileobj(
            Fileobj = file_obj,
            Bucket = self.bucket_name,
            Key = s3_key
        )

        return f"s3://{self.bucket_name}/{s3_key}"
