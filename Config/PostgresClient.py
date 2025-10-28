import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import OperationalError, ProgrammingError, Error
from dotenv import load_dotenv
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
        

    
    def get_assessment(self, id: int):
        query = [
            "SELECT",
            "a.title,",
            "a.description,",
            "a.max_score,",
            "CASE ",
            "       WHEN a.subject_id IS NULL THEN 'NA'",
            "       ELSE sj.title",
            "END AS subject",
            "FROM stu_tracker.Assessments a",
            "LEFT JOIN stu_tracker.Subjects sj",
            "ON sj.id = a.subject_id",
            "WHERE a.id = %s"
        ]
        q = " ".join(query)
        data = self.fetch_one(q, (id,))
        print("Print data", data)
        if data is None:
            return None
        return dict(data)

    def get_assessment_questions(self, id: int):
        query = [
            "SELECT",
            "q.question_text,",
            "q.question_type,",
            "q.points",
            "FROM stu_tracker.Questions q",
            "WHERE assessment_id = %s"
        ]
        q = " ".join(query)
        data = self.fetch_all(q, (id,))
        if data is None:
            return None
        return [dict(row) for row in data]


    ## import from ai_questions
    def update_materials_task(self, params):
        query = "UPDATE stu_tracker.Generate_materials_task SET status = %s, input_tokens = %s, output_tokens = %s WHERE s3_output_key = %s AND organization_id = %s"
        self.execute(query, params)
    
    def update_materials_task_retry(self, params):
        retry_query = "UPDATE stu_tracker.Generate_materials_task SET status = %s, retry_count = retry_count + 1 WHERE s3_output_key = %s;"
        self.execute(retry_query, params)

    def update_status(self, task_id, status):
        query = """
            UPDATE stu_tracker.Generate_question_task
            SET status = %s WHERE id = %s;
        """
        self.execute(query, (status, task_id))

    def get_district_data(self, params):
        district_query = "SELECT name, city, state, region FROM stu_tracker.District WHERE organization_id = %s AND id = %s"
        return self.fetch_one(district_query, params)
    
    def get_subject_data(self, params):
        subject_query = "SELECT title, description FROM stu_tracker.Subjects WHERE organization_id = %s AND id = %s"
        return self.fetch_one(subject_query, params)
    
    def update_question_task(self, params):
        success_query = "UPDATE stu_tracker.Generate_questions_task SET status = %s, input_tokens = %s, output_tokens = %s WHERE s3_output_key = %s;"
        self.execute(success_query, params)
        
    def update_question_task_retry(self, params):
        retry_query = "UPDATE stu_tracker.Generate_questions_task SET status = %s, retry_count = retry_count + 1 WHERE s3_output_key = %s;"
        self.execute(retry_query, params)
                
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("PostgreSQL connection closed.")