""" AWS - S3 Bucket related Operations will be here... """

# Python Packages
import boto3
import os
from io import BytesIO
import pdfplumber
from docx import Document

# Constants
from base import constants

# Messages
from util.messages import ERROR



class S3DirectReader:
    """
    A class for directly retrieving and extracting text content from files in S3 bucket
    without downloading them to local storage. Supports PDF and DOCX formats.
    """

    def __init__(self):
        """
        Initialize the S3 client with AWS credentials from environment variables.
        """

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id = constants.AWS_ACCESS_KEY_ID,
            aws_secret_access_key = constants.AWS_SECRET_ACCESS_KEY,
            region_name = constants.AWS_REGION
        )
        self.bucket_name = constants.AWS_S3_BUCKET_NAME


    def get_text_from_s3(self, s3_path):
        """
        Retrieve and extract text content from a file in S3 bucket directly without downloading.

        Args:
            s3_path (str): The S3 key/path of the file

        Returns:
            str: Extracted text content

        Raises:
            ValueError: If file format is unsupported
            Exception: For S3 or processing errors
        """

        # Get object from S3
        response = self.s3_client.get_object(Bucket = self.bucket_name, Key = s3_path)
        body = response['Body'].read()

        # Determine file format and extract text
        file_extension = s3_path.lower().split('.')[-1]

        if file_extension == 'pdf':
            # Extract text from PDF
            text = ""
            with pdfplumber.open(BytesIO(body)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text

        elif file_extension == 'docx':
            # Extract text from DOCX
            doc = Document(BytesIO(body))
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)


        elif file_extension == 'doc':
            # DOC format not supported yet - would need additional library
            raise ValueError(ERROR["DOC_FORMAT_NOT_SUPPORTED"])


        else:
            raise ValueError(ERROR["UNSUPPORTED_FILE_FORMAT"].format(file_extension=file_extension))



    def get_file_bytes_from_s3(self, s3_path):
        """
        Retrieve raw file bytes from S3.
        """

        response = self.s3_client.get_object(
            Bucket = self.bucket_name,
            Key = s3_path
        )

        return response['Body'].read()
