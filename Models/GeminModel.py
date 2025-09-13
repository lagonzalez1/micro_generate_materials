import os
import json
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from google import genai

load_dotenv()

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

"""
    This will be used for testing since Amazon On-demand will charge!!!
    This is Free for development pusposes
"""
class GeminiModel:
    def __init__(self, prompt: str):
        self.prompt = prompt 
        self.response = self.generate_gemini()
        self.parsed_response = None


    def generate_gemini(self) -> dict:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=self.prompt
            )
            return response
        except (ClientError, Exception) as e:
            print(f"Error: Can't invoke. Reason: '{e}''")
    
    def valid_response(self)->bool:
        if self.response:
            return True
        return False

    def get_generation(self)->str:
        return self.response.text
    
    def get_text_length(self)->int:
        return len(self.response.text)
    
    def total_token(self) ->int:
        compressed = "".join(self.response.text.split())
        return (len(compressed) + 2) // 4



