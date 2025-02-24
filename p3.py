import json
import unittest
import boto3
from botocore.stub import Stubber
from unittest.mock import patch, MagicMock
from ..global_distributions.distributions_lite.alz_fund_info_service import ALZFundInfoService


class ALZFundInfoServiceTest(unittest.TestCase):


    dynamo_table = "DMGOversight"
    dynamo_region = "us-east-1"


    def setUp(self):
        self.mock_dynamo_table = boto3.resource('dynamodb', region_name=self.dynamo_region).Table(self.dynamo_table)
        self.dynamo_stub = Stubber(self.mock_dynamo_table.meta.client)
        self.service = ALZFundInfoService(self.mock_dynamo_table)


    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('json.dumps')
    def test_export_fund_info(self, mock_json_dumps, mock_open):
        mock_items = [{'PK': 'DOMICILE#US#TYPE#1'}, {'PK': 'DOMICILE#US#TYPE#2'}]
        self.dynamo_stub.add_response(
            'scan',
            {'Items': mock_items, 'LastEvaluatedKey': 'key1'}
        )
        self.dynamo_stub.add_response(
            'scan',
            {'Items': [], 'LastEvaluatedKey': None}
        )
        mock_json_dumps.return_value = 'json_data'


        with self.dynamo_stub:
            file_path = self.service.export_fund_info()


            self.assertEqual(file_path, '/tmp/fund_info.json')
            self.mock_dynamo_table.scan.assert_called()
            mock_open.assert_called_with('/tmp/fund_info.json', 'w')
            mock_open().write.assert_called_with('json_data')