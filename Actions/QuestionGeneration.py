from Models.AmazonModel import AmazonModel
from Models.GeminModel import GeminiModel
from Prompt.PromptQ import PromptQ
from S3.main import S3Instance
from Config.Client import Client
import json
import logging
# --- Python logger ---
logging.basicConfig(
    level=logging.INFO, # Adjust to logging.DEBUG for more verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

DONE = 'DONE'
ZERO = 0
ERROR = 'ERROR'
s3 = S3Instance("tracker-client-storage")

class QuestionGeneration:
    def __init__(self, db, channel, method, client: Client, model_type: str):
        self.db = db
        self.channel = channel
        self.model_type = model_type
        self.method = method
        self.client = client
        
    def query_database_for_requirements(self) -> tuple:
        district_data = self.db.get_district_data((self.client.get_organization_id(), self.client.get_district_id()))
        if not district_data:
            return None

        subject_data = self.db.get_subject_data((self.client.get_organization_id(), self.client.get_subject_id()))
        if not subject_data:
            return None
        return (district_data, subject_data)

    def run_model(self, district_data, subject_data):
        prompt = PromptQ(district_data, subject_data, self.client.get_description(), 
                                self.client.get_max_points(), self.client.get_question_count(), self.client.get_grade_level(),
                                self.client.get_difficulty())
        model = None
        if self.model_type == "AMZN":
            model = AmazonModel(prompt=prompt.get_prompt(), temp=0.5, top_p=0.9, max_gen_len=3072)
        if self.model_type == "GOOGLE":
            model = GeminiModel(prompt.get_prompt())
            logger.info(f"Model generated: {model.total_token()}")
            
        return model

    def error_model_result(self):
        self.db.update_question_task((ERROR, 0, ZERO, self.client.get_output_key(), self.client.get_organization_id()))


    def save_model_results(self, model):
        if model.valid_response():
            s3.put_object(f"assessments/{self.client.get_s3_output_key()}", model.get_generation())
            self.db.update_question_task(("COMPLETE", model.total_token(), model.total_token(), self.client.get_output_key()))
        else:
            self.db.update_question_task((ERROR, model.total_token(), ZERO, self.client.get_output_key(), self.client.get_organization_id()))
    

