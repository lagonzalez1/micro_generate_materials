from Models.AmazonModel import AmazonModel
from Models.GeminModel import GeminiModel
from Config.Client import Client
from typing import Optional
import datetime
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

# Observe and manage retries for failed attempts
class State:
    def __init__(self, db, client: Optional[Client]):
        self.db = db
        self.client: Optional[Client] = client

    def get_assessments(self, assessment_ids: list[int])->list:
        """
            Idempotent insert/return for DB table stu_tracker.Assessments.
            Params: assessment_ids (list(int))

            Returns list(dict)
            dict{ast.id, ast.title, ast.max_score, ast.easy_score, ast.description, sj.title AS subject_title}
        """
        try:    
            if self.client is None:
                return False
            return self.db.get_assessments(assessment_ids)
        except RuntimeError as e:
            logger.error(f"Unable to upsert assessment task")
            return None
        
    
    def get_assessment_questions(self, assessments_ids: list[int])->dict:
        """
            Get get_assessment_questions from db
            Params: assessment_ids list(int)

            Returns dict
            dict{q.assessment_id AS assessment_id, q.id AS question_id,q.question_text,c.id AS choice_id,c.question_id,c.is_correct,q.points,q.question_type}
        """
        try:
            assessment_map = self.db.get_assessment_questions(assessments_ids)
            return assessment_map
        except RuntimeError as e:
            logger.error(f"unable to get assessment questions: {e}")
    
    def upsert_assessment_task(self)->Optional[dict]:
        """
            Idempotent insert/return for DB table stu_tracker.Assessment_grader_task.
            Params: client.session_token, model_id.

            Returns Object
            {id, status, attempts}
        """
        try:    
            if self.client is None:
                return None
            task = self.db.create_grader_task((self.client.get_session_token(), MODEL_ID))
            return task
        except RuntimeError as e:
            logger.error(f"Unable to upsert assessment task")
            return False
        
    def upsert_assessment_students(self, sessions: Optional[list], session_id: Optional[int])->Optional[bool]:
        """ 
            Idempotent insert to table stu_tracker.Assessments_students to prepare score uploads.
            Required: session_id from Go API pre-insert.
            Params: sessions (list), session_id (int)

            Returns Boolean
             
        """
        try:    
            if self.client is None:
                return None
            student_map = { i['student_id']: i for i in sessions}
            d = [ (session_id, value['student_id'], ZERO, value['assessment_id'], None) for key, value in student_map.items() ]
            res = self.db.upsert_assessment_students(d)
            return res
        except RuntimeError as e:
            logger.error(f"Unable to upsert assessment task")
            return None
    
    def upsert_assessment_items(self, session_answers: Optional[list], task_id: Optional[int])->bool:
        """ 
            Idempotent insert to table stu_tracker.Grader_task_item. 
            Items need to be proccessed and marked as completed to finish this process.
            Required session_answers reference by id and task_id
            Params: session_answers (list), task_id(int)

            Returns Boolean
             
        """
        try:    
            if self.client is None:
                return False
            self.db.create_grader_task_item(session_answers, MODEL_ID, task_id)
            return True
        except RuntimeError as e:
            logger.error(f"Unable to upsert assessment task")
            return False
     
    def delete_session_grader_task(self, session_token: Optional[str])->bool:
        """ 
            Remove session grader task.
            Params: Session_task (str)
            
            Returns boolean
        """
        try:    
            self.db.delete_grader_task(session_token)
            return True
        except RuntimeError as e:
            logger.info("unable to remove session task")
            return None
    
    def delete_assessment_sessions(self, session_token: Optional[str])->bool:
        """ 
            Delete assessment sessions.
            Params: Session_task str
            
            Returns boolean
        """
        try:    
            self.db.delete_assessment_session(session_token)
            return True
        except RuntimeError as e:
            logger.info("unable to remove session task")
            return None
        
    def get_assessment_students(self, session_id: Optional[int]):
        """
            Get session answers from stu_tracker.Assessments_students.
            Params: session_id (int)

            Returns list[dict]
            dict {id, student_id, assessment_id}
        """
        try:
            data = self.db.get_assessment_students(session_id)
            if data is None:
                return None
            smap = {f'{item['student_id']}': item for item in data }
            return smap
        except RuntimeError as e:
            logger.info("unable to get get_assessment_students:", e)
            return None

    def upsert_grader_results(self, sessions: Optional[list[dict]], task_id: Optional[int], 
                              task_map: Optional[dict], assessments_students: Optional[dict], session_items_graded_details: Optional[dict]) -> list:
        """
            Idempodent bulk update for the following table in order.
            1. stu_tracker.Assessment_answers update -> points, choice_id, is_correct, feedback
            2. stu_tracker.Grader_task_item udpate -> attempts, updated_at, status
            3. stu_tracker.Assessment_grader_task udpate -> attempts, updated_at, status
            4. stu_tracker.Assessments_students udpate -> student_id, assessment_id, session_id, score

            Failure will result in a retry.

            Params: sessions (graded_items, list), task_id (int), task_map (dict), assessment_students (dict), session_items_graded_details (dict)

            Returns list(dict)
            Graded items
            dict{ "answers_upserted","grader_items_updated", "assessment_task_updated", "update_assessment_session_score" }
        """
        try:
            if len(sessions) == 0 or assessments_students is None:
                return None
            current_date = datetime.datetime.now()         
            an_rows = [
                (assessments_students[str(s['student_id'])]['id'], s['question_id'], s['choice_id'], s.get("answer_text"), s.get("is_correct"), s.get("feedback"), s.get("points"))
                for s in sessions
            ]
            logger.info("an_rows", an_rows)
            gr_rows = [
                ('COMPLETED', current_date , task_map[s['assessment_student_id']]['item_key'])
                for s in sessions
            ]

            tr_rows = [
                (key, assessments_students[str(key)]['assessment_id'], self.client.get_session_id(), value['score']) for key, value in session_items_graded_details.items()
            ]
            res = self.db.bulk_update(an_rows, gr_rows, tr_rows, task_id)
            return res
        except RuntimeError as e:
            logger.error("unable to upsert grader_results", e)
            return None


    def update_llm_usage(self, usage: Optional[list[tuple]])->int:
        try:
            return self.db.update_llm_usage(usage)
        except RuntimeError as e:
            logger.error(f"Error found grade_assessment: {e}")
            return -1

    def get_session_answers_by_item_key(self, grader_task_item: list)->list:
        """
            Get session answers from stu_tracker.Session_answers.
            Params: session_token (str)

            Returns list[dict]
            dict{id, assessment_id, student_id, question_id, choice_id, answer_text}
        """
        try:
            if not self.client:
                return None
            sessions = self.db.get_session_answers_by_item_key(grader_task_item)
            return sessions
        except RuntimeError as e:
            logger.error(f"Error found grade_assessment: {e}")
            return None

    def get_sessions_answers(self) ->list:
        """
            Get session answers from stu_tracker.Session_answers.
            Params: session_token (str)

            Returns list[dict]
            dict{id, assessment_id, student_id, question_id, choice_id, answer_text}
        """
        try:    
            if self.client is None:
                return []
            data = self.db.get_session_answers(self.client.get_session_token())
            return data
        except RuntimeError as e:
            logger.error(f"Unable to get item tasks: {e}")
            return []

    def get_item_tasks(self, task_id: Optional[int]) -> list:
        """
            Get item task by task_id.
            Params: task_id (int)

            Returns Object 
            { id, item_key, task_id, status, attempts }
            
        """
        try:    
            if self.client is None:
                return []
            data = self.db.get_grader_task_items(task_id)
            return data
        except RuntimeError as e:
            logger.error(f"Unable to get item tasks: {e}")
            return []

