import os
from Config.RabbitMQ import RabbitMQ
from Config.PostgresClient import PostgresClient
from Config.Client import Client
from dotenv import load_dotenv
from Actions.Grader import Grader
from Actions.State import State
import logging

load_dotenv()
# --- Python logger ---
logging.basicConfig(
    level=logging.INFO, # Adjust to logging.DEBUG for more verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
EXCHANGE     = os.getenv("EXCHANGE")
QUEUE        = os.getenv("QUEUE")
ROUTING_KEY  = os.getenv("ROUTING_KEY")
RABBIT_LOCAL  = os.getenv("RABBIT_LOCAL")
PREFETCH_COUNT = 1
EXCHANGE_TYPE = "direct"
DONE = 'DONE'
ZERO = 0
ERROR = 'ERROR'
MODEL = "GOOGLE"
MAX_ATTEMPTS = 6

def create_callback(db):
    def on_message(channel, method, properties, body):
        try:
            logger.info("Received message: delivery_tag=%s, routing_key=%s, gen_type=%s", method.delivery_tag, getattr(method, "routing_key", None), body) 
            try: 
                client = Client(body)
                grade_paper, state_manager = Grader(db, client), State(db, client)
                ## idempotent insert, increments if found.
                insert_assessment_task_res = state_manager.upsert_assessment_task()
                if insert_assessment_task_res is None:
                    delete_assessment_task, delete_assessment_sessions = state_manager.delete_session_grader_task(), state_manager.delete_assessment_sessions()
                    logger.info("Remove: delete_assessment_task: %s, delete_assessment_sessions %s", delete_assessment_task, delete_assessment_sessions)
                    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)    
                    return 
                if insert_assessment_task_res['attempts'] >= MAX_ATTEMPTS:
                    delete_assessment_task, delete_assessment_sessions = state_manager.delete_session_grader_task(), state_manager.delete_assessment_sessions()
                    logger.info("Remove: delete_assessment_task: %s, delete_assessment_sessions %s", delete_assessment_task, delete_assessment_sessions)
                    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    return

                item_tasks = state_manager.get_item_tasks(insert_assessment_task_res['id'])
                ## If no session items, try to set the values
                if len(item_tasks) == ZERO:
                    session_answers = state_manager.get_sessions_answers()
                    assessment_students, state_items = state_manager.upsert_assessment_students(session_answers, client.get_session_id()), state_manager.upsert_assessment_items(session_answers, insert_assessment_task_res['id'])
                    logger.info("Idempotent insert on get_session_answers %s, upsert_assessment_students: %s, upsert_assessment_items", session_answers, assessment_students, state_items)

                # This can be dangerous ? to insert then call suddently (early)
                item_tasks = state_manager.get_item_tasks(insert_assessment_task_res['id'])
                if item_tasks is None or len(item_tasks) == 0:
                    delete_assessment_sessions = state_manager.delete_assessment_sessions(client.get_session_token())
                    logger.info("Remove: delete_assessment_sssions: %s", delete_assessment_sessions)
                    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    return
                
                task_ids, task_map = [i['item_key'] for i in item_tasks], {i['item_key']: i for i in item_tasks}
                student_session_answers, assessment_students = state_manager.get_session_answers_by_item_key(task_ids), state_manager.get_assessment_students(client.get_session_id())
                assessment_ids = [ int(value['assessment_id']) for _, value in assessment_students.items()]

                assessments, assessment_questions = state_manager.get_assessments(assessment_ids), state_manager.get_assessment_questions(assessment_ids)
                assessment_build = grade_paper.build_assessment_(assessments, assessment_questions)
                if assessment_build is None:
                    logger.info("Retry: assessment build, graded, will try again.")
                    channel.basic_ack(delivery_tag=method.delivery_tag, requeue=True)
                    return
                session_items_graded, model_insert = grade_paper.grade_(assessment_build, student_session_answers)
                if len(model_insert) >= 1:
                    logger.info("LLM usage: %s", model_insert)
                    update_llm_usage = state_manager.update_llm_usage(model_insert)
                    logger.info("Update: update_llm_usage: %s", update_llm_usage)

                if session_items_graded is None:
                    logger.info("Retry: no items, graded, will try again.")
                    channel.basic_ack(delivery_tag=method.delivery_tag, requeue=True)
                    return
                session_items_graded_details, commit_changes = grade_paper.graded_details(session_items_graded), None
                commit_changes = state_manager.upsert_grader_results(session_items_graded, int(insert_assessment_task_res['id']), task_map, assessment_students, session_items_graded_details)
                if commit_changes is None:
                    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    return
                logger.info("removing from queue %s", client.get_session_token())
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return
            except RuntimeError as e:
                # Requeue
                logger.error("unable to grade assessment with session_token %s", client.get_session_token())
                return 
        except KeyboardInterrupt as e:
            logger.error("Error found", e)
            return
    return on_message


def main():##
    mq = RabbitMQ(PREFETCH_COUNT, EXCHANGE, QUEUE, ROUTING_KEY, EXCHANGE_TYPE)
    db = PostgresClient()
    callback = create_callback(db)
    mq.set_callback(callback)
    channel = mq.get_channel()
    connection = mq.get_connection()
    try:
        print(f"RabbitMQ consuming on {QUEUE} with routing key {ROUTING_KEY}")
        channel.start_consuming()
    except KeyboardInterrupt as e:
        print(e)
    finally:
        channel.close()
        connection.close()
        db.close()

if __name__ == "__main__":
    main()