import os
from Config.RabbitMQ import RabbitMQ
from Config.PostgresClient import PostgresClient
from Config.Client import Client
from S3.main import S3Instance
from dotenv import load_dotenv
from Models.GeminModel import GeminiModel
from Models.AmazonModel import AmazonModel
from Prompt.Prompt import Prompt
import json
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

def create_callback(db):
    def on_message_test(channel, method, properties, body):
        client = Client(body)        
        s3 = S3Instance("tracker-client-storage")
        assessment = db.get_assessment(client.get_assessment_id())
        questions = db.get_assessment_questions(client.get_assessment_id())
        if not assessment:
            db.update_materials_task((DONE,0,0, client.get_s3_output_key(), client.get_organization_id()))
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        if not questions or len(questions) <= 0:
            db.update_materials_task((DONE,0,0, client.get_s3_output_key(), client.get_organization_id()))
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        questions_stringify = json.dumps(questions)
        prompts = Prompt(questions_stringify, assessment['title'], assessment['description'], assessment['max_score'], assessment['subject'], client.get_bias_type())
        ## model = AmazonModel(prompts.get_prompt(),temp=0.7, top_p=0.9, max_gen_len=3000)
        model = GeminiModel(prompts.get_prompt())
        
        logger.info(f"Model generated: {model.total_token()}")
        
        if not model.valid_response():
            db.update_materials_task((DONE,ZERO,ZERO, client.get_s3_output_key(), client.get_organization_id()))
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        else:
            s3.put_object(client.get_s3_output_key(), model.get_generation())
            db.update_materials_task((ERROR,prompts.get_token_length(), 0, client.get_s3_output_key(), client.get_organization_id()))
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        
    return on_message_test


def main():
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