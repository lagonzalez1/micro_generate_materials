from Models.AmazonModel import AmazonModel
from Actions.GraderGenerator import GraderGenerator
from Models.GeminModel import GeminiModel
from Prompt.Prompt import Prompt
from S3.main import S3Instance
from Config.Client import Client
from typing import Optional
from Prompt.Identity import get_context, get_identity_prompt, get_rules, get_instructions_prompt, get_examples_prompt
import json
import logging
import os
# --- Python logger ---
logging.basicConfig(
    level=logging.INFO, # Adjust to logging.DEBUG for more verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
## Sessions -> assessment_ids (list of assessments to get questions and answers) ->   -> loop and check while feeding model
logger = logging.getLogger(__name__)
MODEL_ID  = os.getenv("MODEL_ID")
DONE = 'DONE'
ZERO = 0
ERROR = 'ERROR'
MODEL_TYPE = 'GOOGLE'
SUCCESS = 'SUCCESS'
FAIL = 'FAIL'


# Each class will load assessments and choices per session payload.
class Grader:
    def __init__(self, db, client: Client):
        self.db = db
        self.client = client

    def parse_assessments(self, sessions: Optional[list]) -> list:
        """
            List of unique ids.
            Returns a list of ids
        """
        if sessions is None:
            return []
        res = {}
        for i in range(0, len(sessions)):
            id = sessions[i]['assessment_id']
            if id not in res:
                res[sessions[i]['assessment_id']] = 1
        return [value for value in res.keys()]

    def build_assessment_(self, assessments: Optional[list], assessment_questions: Optional[list])->dict:
        """
            Build assessment by placing question in assessment dict
            Params: assessments (list), assessment_questions (list)
            
            Returns Object
            dict{id, questions, ...}
        """
        try:    
            if not assessments and not assessment_questions:
                return None
            bmap = {}
            for i in range(0, len(assessments)):
                aid = assessments[i]['id'] 
                if aid not in bmap:
                    bmap[aid] = assessments[i]
                    bmap[aid]['questions'] = {}

            for i in range(0, len(assessment_questions)):
                aid = assessment_questions[i]['assessment_id']
                if aid in bmap:
                    question = assessment_questions[i]
                    bmap[aid]['questions'][question['question_id']] = question
            return bmap
        except RuntimeError as e:
            logger.info("unable to build assessment_builder {e}")
            return None
        
    def grade_non_agent(self, assessment: Optional[dict], session: Optional[list]) ->list:
        try:
            return None
        except RuntimeError as e:
            logger.info("grade_non_agent", e)
            return None
    
    def grade_(self, assessment: Optional[dict], session: Optional[list] ) -> tuple:
        """
            Grade session list given assessments.
            Call Bedrock API for inteligent, feedback driven responses.

            Returns Tuple
            (list(dict), 
            list(tuples))
            dict {assessment_student_id, student_id, question_id, choice_id, answer_text, is_correct, feedback, points},
            tuples(organization_id, input_tokens, output_tokens, MODEL_TYPE, MODEL_ID, FAIL/SUCCESS) 
        """
        try:
            if self.client is None or assessment is None or session is None:
                return None
            updates = []
            model_usage = []
            for item in session:
                kl = assessment[item['assessment_id']]
                question = kl['questions'][item['question_id']]
                if question['question_type'] == "short_answer":
                    prompt = Prompt(kl, question, item['answer_text'])
                    grader_context = GraderGenerator(model_type=MODEL_TYPE, prompt=prompt)
                    input_tokens = prompt.get_input_length()
                    model = grader_context.run_grade_model()
                    output_tokens = model['output_tokens']
                    if model is None:
                        model_usage.append((self.client.get_orgainzation_id(), input_tokens, 0, MODEL_TYPE, MODEL_ID, FAIL ))
                        return None
                    else:
                        model_usage.append((self.client.get_orgainzation_id(),input_tokens, output_tokens, MODEL_TYPE, MODEL_ID, SUCCESS))
                        is_correct_ = float(question['points'] / 2)
                        model_response_points = float(model["response"]["score"])
                        upsert = {'assessment_student_id': item['id'], 'student_id': item['student_id'],
                                  'question_id': question['question_id'], 
                                  'choice_id': None, 'answer_text': item['answer_text'], 
                                  'is_correct': True if float(model_response_points) > float(is_correct_) else False , 
                                  'points' : model_response_points,
                                  "feedback": model["response"]["feedback"]}
                        updates.append(upsert)
                else:
                    if item['choice_id'] is None:
                        upsert = { 'assessment_student_id': item['id'], 'student_id': item['student_id'],
                                  'question_id': question['question_id'], 
                                  'choice_id': None, 'answer_text': None, 'is_correct': False, 'points' : 0}
                        updates.append(upsert)
                        continue
                        # Incorrect
                    if question['choice_id'] == item['choice_id']:
                        logger.info(f"simple grader called")
                        upsert = { 'assessment_student_id': item['id'], 'student_id': item['student_id'],
                                  'question_id': question['question_id'], 
                                  'choice_id': None, 'answer_text': None, 'is_correct': True, 'points' : question['points'] }
                        updates.append(upsert)
                        continue
                    else:
                        upsert = { 'assessment_student_id': item['id'], 'student_id': item['student_id'],
                                  'question_id': question['question_id'], 
                                  'choice_id': None, 'answer_text': None, 'is_correct': False,'points' : 0}
                        updates.append(upsert)
                        continue
                        # incorrect
            return (updates, model_usage)
        except RuntimeError as e:
            logger.error(f"unable to grade assessment with error: {e}")
            return False
         
    
    def graded_details(self, graded_list: Optional[list]) -> Optional[dict]:
        """
            Create a map of graded students responses by mapping { student: {Object} }
            Allows for fast student lookup and indexing
            Params: graded_list (list(dict))
            
            Returns Object
            dict {student_id: {....} }
        """
        details = { i['student_id']: {"score": 0} for i in graded_list}
        for i in graded_list:
            if details[i['student_id']]:
                details[i['student_id']]['score'] += i['points']
        return details