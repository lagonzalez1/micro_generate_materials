import boto3
from botocore.exceptions import BotoCoreError, ClientError
from io import StringIO
from typing import Optional
import json

## Asuuming the base role for CLI
s3 = boto3.client('s3')


"""
    Instance writes to path : materials/ 
    Writes the standalone json 

"""

class S3Instance:
    def __init__(self, bucket):
        self.bucket = bucket    

    def put_object(self, key, body: str)-> bool:
        try:
            print(f"Uploading to s3 with key {key}")
            s3.put_object(
                Bucket=self.bucket,
                Key=str(key),
                Body=body,
                ContentType='application/json'
            )
            return True
        except (BotoCoreError, ClientError) as e:
            return False
    


    