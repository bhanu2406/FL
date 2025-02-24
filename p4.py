import unittest
import boto3
from botocore.stub import Stubber
from unittest.mock import patch, MagicMock
from global_distributions.distributions_lite.alz_s3_file_service import ALZS3FileService


class ALZS3FileServiceTest(unittest.TestCase):


    s3_bucket_name = "testing_bucket"
    s3_region = "us-east-1"


    def setUp(self):
        self.mock_s3_client = boto3.client('s3', region_name=self.s3_region)
        self.s3_stub = Stubber(self.mock_s3_client)
        self.service = ALZS3FileService(self.mock_s3_client)


    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b'data')
    def test_upload_file_to_s3(self, mock_open):
        file_path = '/tmp/test_file'
        s3_key = 'test_key'


        self.s3_stub.add_response(
            'put_object',
            expected_params={
                'Bucket': self.s3_bucket_name,
                'Key': s3_key,
                'Body': b'data'
            },
            service_response={}
        )


        self.s3_stub.activate()
        self.service.upload_file_to_s3(file_path, self.s3_bucket_name, s3_key)
        self.s3_stub.deactivate()


        mock_open.assert_called_once_with(file_path, 'rb')