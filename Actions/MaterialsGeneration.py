from Models.AmazonModel import AmazonModel
from Models.GeminModel import GeminiModel
from Prompt.Prompt import Prompt
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

class MaterialsGeneration:

    def __init__(self, db, channel, method, client: Client, model_type: str):
        self.db = db
        self.model_type = model_type
        self.channel = channel
        self.method = method
        self.client = client
        
    def query_database_for_requirements(self) -> tuple:
        assessment = self.db.get_assessment(self.client.get_assessment_id())
        questions = self.db.get_assessment_questions(self.client.get_assessment_id())
        if not assessment:
            self.db.update_materials_task((DONE,0,0, self.client.get_s3_output_key(), self.client.get_organization_id()))
            return None
        if not questions or len(questions) <= 0:
            self.db.update_materials_task((DONE,0,0, self.client.get_s3_output_key(), self.client.get_organization_id()))
            return None
        return (questions, assessment)

    def run_model(self, questions, assessment):
        questions_stringify = json.dumps(questions)
        prompts = Prompt(questions_stringify, assessment['title'], assessment['description'], assessment['max_score'], assessment['subject'], self.client.get_bias_type())
        model = None
        if self.model_type == "AMZN":
            model = AmazonModel(prompts.get_prompt(),temp=0.7, top_p=0.9, max_gen_len=3000)
            logger.info(f"Model generated: {model.total_token()}")
        if self.model_type == "GOOGLE":
            model = GeminiModel(prompts.get_prompt())
            logger.info(f"Model generated: {model.total_token()}")
        return model
    
    def error_model_result(self):
        self.db.update_materials_task((ERROR, ZERO, ZERO, self.client.get_s3_output_key(), self.client.get_organization_id()))

    def save_model_results(self, model):
        if model.valid_response():
            s3.put_object(f"materials/{self.client.get_s3_output_key()}", model.get_generation())
            self.db.update_materials_task((DONE,ZERO,ZERO, self.client.get_s3_output_key(), self.client.get_organization_id()))
        else:
            self.db.update_materials_task((ERROR, model.total_token(), ZERO, self.client.get_s3_output_key(), self.client.get_organization_id()))
    

