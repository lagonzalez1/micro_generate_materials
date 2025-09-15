import os
import json
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
import logging
load_dotenv()

# --- 1. Set up basic logging to stdout ---
logging.basicConfig(
    level=logging.INFO, # Adjust to logging.DEBUG for more verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MODEL_ID = os.getenv("MODEL_ID")
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

class AmazonModel:
    def __init__(self, prompt: str, temp: float, top_p: float, max_gen_len: int):
        self.prompt = prompt 
        self.temp = temp
        self.top_p = top_p
        self.max_gen_len = max_gen_len
        # Build the response
        self.response = self._invoke_model()
        self.parsed_response = None
        # Verify the response and append
        if self.response:
            self.parsed_response = self._parse_response()


    def _invoke_model(self) -> dict:
        try:
            response = bedrock.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps({
                    "inputText": self.prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": self.max_gen_len,
                        "temperature": self.temp
                    }
                })
            )
            logger.info(f"Successfully invoked model '{MODEL_ID}'.")
            logger.info(f"Successfully response '{response}'.")
            return response
        except ClientError as e:
            logger.error(f"Bedrock ClientError invoking model '{MODEL_ID}': {e.response['Error']['Message']}")
            return None
        except ValueError as e:
            logger.error(f"ValueError while invoking model: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while invoking model '{MODEL_ID}': {e}")
            return None

    def input_token(self):
        try:
            response_body = json.loads(self.response.get("body").read())
            usage = response_body.get("usage")
            return usage.get("inputTokens")
        except (AttributeError, json.JSONDecodeError) as e:
            logger.error(f"output token error {e}")
            return None

    def output_token(self):
        try:
            response_body = json.loads(self.response.get("body").read())
            usage = response_body.get("usage")
            return usage.get("outputTokens")
        except (AttributeError, json.JSONDecodeError) as e:
            logger.error(f"output token error {e}")
            return None

    def total_token(self):
        try:
            response_body = json.loads(self.response.get("body").read())
            usage = response_body.get("usage")
            return usage.get("totalTokens")
        except (AttributeError, json.JSONDecodeError) as e:
            logger.error(f"output token error {e}")
            return None

    def _parse_response(self):
        if not self.response:
            logger.warning("No response to parse. The model invocation may have failed.")
            return None
        try:
            parsed_body = json.loads(self.response.get("body").read())
            logger.debug("Successfully parsed model response body.")
            return parsed_body
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from model response: {e}")
            return None
        except (AttributeError, KeyError) as e:
            logger.error(f"Error accessing response body or key: {e}")
            return None


    def valid_response(self)->bool:
        if self.parsed_response:
            return True
        return False
    
    def get_generation(self)->str:
        if self.parsed_response is None:
            return None
        try:
            response = self.parsed_response["results"][0]["outputText"]
            return response
        except AttributeError as e:
            return None 



