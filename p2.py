import boto3
import logging


class ALZS3FileService:
    def __init__(self, s3_client):
        """
        Initialize the ALZS3FileService with an S3 client.


        :param s3_client: Boto3 S3 client.
        """
        self.s3_client = s3_client


    def upload_file_to_s3(self, file_path, s3_bucket_name, s3_key):
        """
        Upload a file to an S3 bucket.


        :param file_path: Path to the file to upload.
        :param s3_bucket_name: Name of the S3 bucket.
        :param s3_key: S3 key for the file.
        """
        with open(file_path, 'rb') as f:
            self.s3_client.put_object(
                Bucket=s3_bucket_name,
                Key=s3_key,
                Body=f
            )
        logging.info(f"File uploaded to s3://{s3_bucket_name}/{s3_key}")