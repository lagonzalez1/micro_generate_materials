from Models.AmazonModel import AmazonModel
from Models.GeminModel import GeminiModel
from Prompt.Prompt import Prompt
from typing import Optional
import json
import re
from json import JSONDecodeError
import logging
# --- Python logger ---
logging.basicConfig(
    level=logging.INFO, # Adjust to logging.DEBUG for more verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
MAX_RETRY = 2

logger = logging.getLogger(__name__)

## This is my actions Generator to call bedrock model
class GraderGenerator:
    def __init__(self, model_type:Optional[str], prompt: Optional[Prompt] ):
        self.model_type = model_type
        self.prompt = prompt

    def gemini_parser(self, response: Optional[str]) -> str:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json_str
        return None

    def amazon_parser(self, response: Optional[str]) -> str:
        clean = re.sub(r"^```JSON\s*|\s*```$", "", response)
        return clean

    def parse_response(self, str_response: Optional[str])->bool:
        try:
            _ = json.loads(str_response)
            return True
        except JSONDecodeError as e:
            logger.error("unable to parse response: %s", e)
            return False

    def run_grade_model(self) -> Optional[dict]:
        model, retry_count = None, 0
        while retry_count <= MAX_RETRY:
            logger.info("run_grade_model retry_count: %s", retry_count)
            if self.model_type == "AMZN":
                retry_count += 1
                model = AmazonModel(self.prompt.get_prompt(), temp=0.7, top_p=0.9, max_gen_len=3000)
                if model.valid_response():
                    logger.info(f"Model AMZN generated:  {model.total_token()}")
                    res = model.get_generation()
                    if not self.parse_response(res):
                        continue
                    return dict({"response": res, "output_tokens": model.output_token()})
                continue
            if self.model_type == "GOOGLE":
                retry_count += 1
                model = GeminiModel(self.prompt.get_prompt())
                if model.valid_response():
                    logger.info(f"Model GOOGLE generated:  {model.total_token()}")
                    res = model.get_generation()
                    p = self.gemini_parser(res)
                    logger.info("gemini_parser %s", p)
                    if not self.parse_response(p):
                        continue
                    return dict({"response": json.loads(p), "output_tokens": model.total_token()})
                continue

        return None
    

