import json
import logging
import datetime
from typing import Optional


# --- Python logger ---
logging.basicConfig(
    level=logging.INFO, # Adjust to logging.DEBUG for more verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
AI_QUESTION = "generate_questions"
AI_MATERIALS = "generate_materials"


class Client:
    def __init__(self, body):
        try:
            self.body = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.info("Unable to parse file")
            self.body = {}
        
        logging.info("Body", self.body)
        self.generation_type = self.body.get("generation_type")
        self.organization_id: Optional[int] = self.body.get("organization_id")

        if self.generation_type == AI_MATERIALS:
            self.ai_materials = self.body.get(AI_MATERIALS)
            if not self.ai_materials:
                return None
            self._bias_type: Optional[str] = self.ai_materials.get("bias_type")
            self._assessment_id: Optional[int] = self.ai_materials.get("assessment_id")
            self.s3_output_key: Optional[int] = self.ai_materials.get("s3_output_key")
            self.organization_id: Optional[int] = self.body.get("organization_id")

        if self.generation_type == AI_QUESTION:
            self.ai_questions = self.body.get(AI_QUESTION)
            if not self.ai_questions:
                return None
            self.process_type: Optional[int] = self.ai_questions.get("process_type")
            self.s3_output_key: Optional[int] = self.ai_questions.get("s3_output_key")
            self.district_id: Optional[int] = self.ai_questions.get("district_id")
            self.subject_id: Optional[int] = self.ai_questions.get("subject_id")
            self.description: Optional[int] = self.ai_questions.get("description")
            self.max_points: Optional[int] = self.ai_questions.get("max_points")
            self.questions_count: Optional[int] = self.ai_questions.get("questions_count")
            self.grade_level: Optional[int] = self.ai_questions.get("grade_level")
            self.difficulty: Optional[str] = self.ai_questions.get("difficulty")

        if not self.generation_type:
            return None
            

    def get_generation_type(self)->str:
        return self.generation_type
    
    def get_body(self) ->Optional[dict]:
        return self.body

    def get_bias_type(self) -> Optional[int]:
        return self._bias_type

    def get_assessment_id(self) -> Optional[str]:
        return self._assessment_id

    def get_s3_output_key(self) -> Optional[str]:
        return self.s3_output_key

    def get_process_type(self)-> str:
        return self.process_type

    def get_output_key(self) -> str:
        return self.s3_output_key
    
    def get_organization_id(self) -> int:
        return self.organization_id
    
    def get_district_id(self) -> int:
        return int(self.district_id)

    def get_subject_id(self) -> int:
        return int(self.subject_id)

    def get_description(self)->str:
        return self.description

    def get_max_points(self)->int:
        return int(self.max_points)

    def get_question_count(self) ->int:
        return int(self.questions_count)
    
    def get_grade_level(self) ->int:
        return int(self.grade_level)

    def get_difficulty(self) -> str:
        return self.difficulty
