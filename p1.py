import json
import boto3
from boto3.dynamodb.conditions import Attr
import logging



class ALZFundInfoService:
    def __init__(self, dynamo_table_obj):
        """
        Initialize the ALZFundInfoService with a DynamoDB table object.


        :param dynamo_table_obj: DynamoDB table object.
        """
        self.dynamo_table_obj = dynamo_table_obj
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)


    def export_fund_info(self):
        """
        Export fund info records to a JSON file.


        :return: Path to the JSON file.
        """
        scan_kwargs = {
            'FilterExpression': Attr('PK').begins_with('DOMICILE#US#TYPE#')
        }
        done = False
        start_key = None
        fund_info_list = []
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = self.dynamo_table_obj.scan(**scan_kwargs)
            items = response.get('Items', [])
            fund_info_list.extend(items)
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        json_data = json.dumps(fund_info_list, indent=4)
        file_path = '/tmp/fund_info.json'
        with open(file_path, 'w') as f:
            f.write(json_data)
        self.logger.info(f"Fund info exported to {file_path}")
        return file_path




