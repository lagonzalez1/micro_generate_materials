import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2 import OperationalError, ProgrammingError, Error
from dotenv import load_dotenv
import datetime
import logging

# --- 1. Set up basic logging to stdout ---
logging.basicConfig(
    level=logging.INFO, # Adjust to logging.DEBUG for more verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
load_dotenv()

class PostgresClient:
    def __init__(self):
        self.conn = None
        self._connect()
    
    def _connect(self):
        """Internal method to handle the database connection and logging."""
        try:
            logger.info("Attempting to connect to PostgreSQL database.")
            self.conn = psycopg2.connect(
                host=os.getenv("POSTGRES_URL"),
                port=os.getenv("POSTGRES_PORT"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                dbname=os.getenv("POSTGRES_DB_NAME")
            )
            self.conn.autocommit = True
            logger.info("Successfully connected to PostgreSQL database.")
        except OperationalError as e:
            # This handles connection-related errors
            logger.error("Failed to connect to PostgreSQL database.")
            logger.exception(e)
            raise RuntimeError("Database connection failed") from e
        except Exception as e:
            logger.exception("An unexpected error occurred during database connection.")
            raise RuntimeError("Database connection failed") from e
        
    @contextmanager
    def _get_cursor_transaction(self, cursor_factory=None):
        if not self.conn or self.conn.closed:
            logger.warning("Datebase connection is closed.")
            self._connect()
        self.conn.autocommit = False
        curr = self.conn.cursor(cursor_factory=cursor_factory)
        try:
            yield curr
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            logger.exception("Transaction rolled back due to errors")
            raise
        finally:
            curr.close()
    
    def _get_cursor(self, cursor_factory=None):
        """Internal helper to get a cursor and handle potential connection issues."""
        if not self.conn or self.conn.closed:
            logger.warning("Database connection is closed. Attempting to reconnect...")
            self._connect()
        return self.conn.cursor(cursor_factory=cursor_factory)

    def fetch_one(self, query, params=None):
        try:
            with self._get_cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                logger.debug(f"Executed query: {query} with params: {params}")
                return cursor.fetchone()
        except (OperationalError, ProgrammingError) as e:
            logger.error(f"Failed to execute query: {query}")
            logger.exception(e)
            raise RuntimeError("Database query failed") from e

    def fetch_all(self, query, params=None):
        try:
            with self._get_cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                logger.debug(f"Executed query: {query} with params: {params}")
                return cursor.fetchall()
        except (OperationalError, ProgrammingError) as e:
            logger.error(f"Failed to execute query: {query}")
            logger.exception(e)
            raise RuntimeError("Database query failed") from e

    def execute(self, query, params=None):
        try:
            with self._get_cursor() as cursor:
                cursor.execute(query, params)
                logger.info(f"Executed command: {query} with params: {params}")
        except (OperationalError, ProgrammingError) as e:
            logger.error(f"Failed to execute command: {query}")
            logger.exception(e)
            raise RuntimeError("Database command failed") from e
    
    def execute_res(self, query, params=None):
        try:
            with self._get_cursor() as cursor:
                cursor.execute(query, params)
                logger.info(f"Executed command: {query} with params: {params}")
                affected = cursor.rowcount
                return affected
        except (OperationalError, ProgrammingError) as e:
            logger.error(f"Failed to execute command: {query}")
            logger.exception(e)
            raise RuntimeError("Database command failed") from e
    
    def get_assessment_responses(self, session_token: int, student_id: int, assessment_id: int):
        query = """
        SELECT question_id, choice_id, answer_text, assessment_id 
        FROM stu_tracker.Session_answers WHERE session_token = $1 AND student_id = $2 AND assessment_id = $3;
        """
        data = self.fetch_all(query, session_token, student_id, assessment_id)
        if data is None:
            return None
        return dict(data)
    

    def get_student_responses(self, session_token: str):
        query = """
            SELECT s.id, s.student_id, s.question_id, s.choice_id, s.answer_text 
            FROM stu_tracker.Session_answers s 
        """
        q = " ".join(query)
        data = self.fetch_all(q, (session_token,))
        if data is None:
            return None
        return dict(data)

    def get_assessments(self, ids: list[int]):
        params = ", ".join([f'{id}' for id in ids])
        query = f"""
        SELECT ast.id, ast.title, ast.max_score, ast.easy_score, ast.description, sj.title AS subject_title
        FROM stu_tracker.Assessments ast
        LEFT JOIN stu_tracker.Subjects 
        sj ON sj.id = ast.subject_id 
        WHERE ast.id IN ({params})
        """
        data = self.fetch_all(query)
        if data is None:
            return None
        return [dict(row) for row in data]
    

    def get_session_answers(self, session_token: str):
        query = """
            SELECT id, assessment_id, student_id, question_id, choice_id, answer_text
            FROM stu_tracker.Session_answers WHERE session_token = %s;
        """
        data = self.fetch_all(query, (session_token,))
        if data is None:
            return None
        return [dict(row) for row in data]


    def get_session_answers_by_item_key(self, item_keys: list[int]):
        params = ", ".join([f'{id}' for id in item_keys])
        query = f"""
            SELECT id, assessment_id, student_id, question_id, choice_id, answer_text
            FROM stu_tracker.Session_answers WHERE id IN ({params});
        """
        data = self.fetch_all(query)
        if data is None:
            return None
        return [dict(row) for row in data]

    def update_llm_usage(self, params):
        try:
            with self._get_cursor() as curr:
                query = """
                    INSERT INTO stu_tracker.LLM_usage (organization_id, input_tokens, output_tokens, model, provider, status)
                    VALUES (%s);
                """
                execute_values(curr, query, params)
                return curr.rowcount
        except (OperationalError, ProgrammingError) as e:
            logger.error("unable to update llm usage for {e}", e)
            return None

    def get_assessment_questions(self, ids: int):
        params = ", ".join([f'{id}' for id in ids])
        query = f"""
        SELECT 
        q.assessment_id AS assessment_id,
        q.id AS question_id,
        q.question_text,
        c.id AS choice_id,
        c.question_id,
        c.is_correct,
        q.points,
		q.question_type
        FROM stu_tracker.Choices c
        INNER JOIN stu_tracker.Questions q ON c.question_id = q.id
        WHERE q.assessment_id IN ({params}) AND c.is_correct = TRUE
        ORDER BY c.question_id, c.order_number;
        """
        data = self.fetch_all(query)
        if data is None:
            return None
        return [dict(row) for row in data]

    def get_grader_task_items(self, task_id: int):
        query = """
            SELECT id, item_key, task_id, status, attempts FROM stu_tracker.Grader_task_item
            WHERE task_id = %s AND status IN ('PENDING', 'FAILED_RETRYABLE')
        """
        data = self.fetch_all(query, (task_id,))
        if data is None:
            return None
        return [dict(row) for row in data]

    def get_grader_task_id(self, params):
        query = """ SELECT id, status, attempts FROM stu_tracker.Assessment_grader_task WHERE session_token = %s;"""
        data = self.fetch_one(query, (params,))
        if data is None:
            return None
        return dict(data)

    def create_grader_task(self, params):
        query = """
            INSERT INTO stu_tracker.Assessment_grader_task (session_token, model_id)
            VALUES (%s, %s) ON CONFLICT(session_token, model_id) DO UPDATE SET attempts = Assessment_grader_task.attempts + 1 RETURNING attempts, status, id;
        """
        res = self.fetch_one(query, params)
        return dict(res)

    def delete_grader_task(self, params):
        query = """
            DELETE FROM stu_tracker.Assessment_grader_task WHERE session_token = %s;
        """ 
        self.execute(query, (params,))
    
    def delete_assessment_session(self, params):
        query = """
            DELETE FROM stu_tracker.Assessment_sessions WHERE session_token = %s;
        """ 
        self.execute(query, (params,))

    
    def create_grader_task_item(self, sessions: list, model: str, task_id: str):
        rows = []
        for s in sessions:
            item_id = s['id']
            key = f"{model}:{item_id}"
            rows.append((item_id, task_id, key))
        placeholder = ", ".join(["(%s, %s, %s)"] * len(rows))
        query = f"""
            INSERT INTO stu_tracker.Grader_task_item(item_key, task_id, idempotency_key)
            VALUES {placeholder} ON CONFLICT (task_id, item_key) DO UPDATE SET idempotency_key = EXCLUDED.idempotency_key;
        """
        params = [v for row in rows for v in row]
        self.execute(query, params)


    def bulk_update(self, an_rows, gr_rows, tr_rows, task_id):
        current_time = datetime.datetime.now()
        with self._get_cursor_transaction(cursor_factory=RealDictCursor) as curr:
            ## id, assessment_student_id, points, is_correct;
            answers_inserted = self.upsert_assessment_answers(an_rows, curr)
            logger.info("answers_inserted", answers_inserted)
            if len(answers_inserted) != len(an_rows):
                #Fail and try again
                raise RuntimeError("Unable to upsert_assessment_answers")
            grader_update_items_count = self.update_grader_task_item(gr_rows, curr)
            logger.info("grader_update_items_count", grader_update_items_count)
            if grader_update_items_count != len(an_rows):
                # Fail try again
                raise RuntimeError("Unable to commit grader_update_items")
            parent_id = self.update_grader_assessment('COMPLETED', current_time, task_id, curr)
            logger.info("parent_id", parent_id)
            if parent_id is None:
                raise RuntimeError("Unable to commit update_grader_assessment")
            
            update_assessment_session_score = self.update_assessment_student_score(tr_rows, curr)
            logger.info("update_assessment_session_score", update_assessment_session_score)
            if update_assessment_session_score is None:
                raise RuntimeError("Unable to update_assessment_student_score") 
            return {
                "answers_upserted": len(answers_inserted),
                "grader_items_updated": grader_update_items_count,
                "assessment_task_updated": parent_id,
                "update_assessment_session_score": update_assessment_session_score
            }
    
    def update_assessment_student_score(self, params, curr):
        query = """ 
            INSERT INTO stu_tracker.Assessments_students (
                student_id, assessment_id, session_id, score
            )
            VALUES %s
            ON CONFLICT (student_id, assessment_id, session_id) DO UPDATE SET
                score      = EXCLUDED.score
            RETURNING id, score, student_id, session_id;
        """
        execute_values(curr, query, params)
        cols = [d.name for d in curr.description]    
        return [dict(zip(cols, r)) for r in curr.fetchall()]

    def get_assessment_students(self, session_id):
        query = """ SELECT id, student_id, assessment_id FROM stu_tracker.Assessments_students WHERE session_id = %s;"""
        data = self.fetch_all(query, (session_id,))
        return data

    def upsert_assessment_answers(self, params, curr):
        query = """ 
            INSERT INTO stu_tracker.Assessment_answers (
                assessment_student_id, question_id, choice_id, answer_text, is_correct, feedback, points
            )
            VALUES %s
            ON CONFLICT (assessment_student_id, question_id, choice_id) DO UPDATE SET
                choice_id   = EXCLUDED.choice_id,
                answer_text = EXCLUDED.answer_text,
                is_correct  = EXCLUDED.is_correct,
                feedback    = EXCLUDED.feedback,
                points      = EXCLUDED.points
            RETURNING id, assessment_student_id, points, is_correct;
        """
        execute_values(curr, query, params)
        cols = [d.name for d in curr.description]    
        return [dict(zip(cols, r)) for r in curr.fetchall()]
    

    def update_assessment_students (self, params):
        query = """
            INSERT INTO stu_tracker.Assessments_students (
                session_id, student_id, score, assessment_id, subject_id
            )
            VALUES %s
            ON CONFLICT (student_id, assessment_id, session_id, score) DO UPDATE SET
                score = EXCLUDED.score
            RETURNING id;
        """
        try:
            with self._get_cursor() as curr:
                execute_values(curr, query, params)
                return curr.rowcount
        except (OperationalError, ProgrammingError) as e:
            logger.error(f"Failed to execute query: {query}")
            logger.exception(e)
            raise RuntimeError("Database query failed") from e

    def upsert_assessment_students (self, params):
        query = """
            INSERT INTO stu_tracker.Assessments_students (
                session_id, student_id, score, assessment_id, subject_id
            )
            VALUES %s
            ON CONFLICT (student_id, assessment_id, session_id) DO UPDATE SET
                score = EXCLUDED.score
            RETURNING session_id, student_id, id;
        """
        try:
            with self._get_cursor() as curr:
                execute_values(curr, query, params)
                cols = [d.name for d in curr.description]
                return [dict(zip(cols, r)) for r in curr.fetchall()]
        except (OperationalError, ProgrammingError) as e:
            logger.error(f"Failed to execute query: {query}")
            logger.exception(e)
            raise RuntimeError("Database query failed") from e

    def update_grader_task_item(self, params, curr):
        query = """
            UPDATE stu_tracker.Grader_task_item AS g
            SET 
                status = v.status,
                attempts = g.attempts + 1,
                updated_at = v.updated_at
            FROM (VALUES %s) AS v(status, updated_at, item_key)
            WHERE g.item_key = v.item_key;
        """
        execute_values(curr, query, params)
        return curr.rowcount
        
    def update_grader_assessment(self, STATUS, current_time, task_id, curr):
        query = """
            UPDATE stu_tracker.Assessment_grader_task
            SET status = %s, attempts = attempts + 1, updated_at = %s WHERE id = %s;
        """
        curr.execute(query, (STATUS, current_time, task_id))
        return curr.rowcount
    
    def query_assessment_grader_task(self, params):
        query = """
            SELECT id, status FROM stu_tracker.Assessment_grader_task WHERE session_token = %s;
        """ 
        self.execute(query, params)
        
    def query_assessment_grader_task_item(self, params):
        query = """
            SELECT item_key, status, attempts FROM stu_tracker.Grader_task_item WHERE idempotency_key = %s;
        """ 
        self.execute(query, params)

    def create_assessment_answers(self, params):
        query =   """
            INSERT INTO stu_tracker.Assessment_answers(assessment_student_id, question_id, choice_id, answer_text, is_correct, feedback) 
            VALUES(%s, %s, %s, %s, %s, %s);
        """
        self.execute(query, params)
                
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("PostgreSQL connection closed.")