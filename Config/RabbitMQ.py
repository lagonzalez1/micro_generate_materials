
import os
import logging
import pika
from dotenv import load_dotenv
import boto3
import ssl

load_dotenv()  # loads variables from .env

# --- 1. Set up basic logging to stdout ---
# This ensures that all log messages from your script and libraries
# like pika will be captured by the ECS awslogs driver.
logging.basicConfig(
    level=logging.INFO, # You can set this to logging.DEBUG for more detail
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configure Pika's logging to be verbose ---
# This is a key step. Pika has its own logger. You want to make sure it's
# also configured to send logs at the INFO or DEBUG level.
pika_logger = logging.getLogger('pika')
pika_logger.setLevel(logging.INFO)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS")
RABBIT_LOCAL  = os.getenv("RABBIT_LOCAL")
s3 = boto3.client('s3')

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
class RabbitMQ:
    def __init__(self, prefetch_count, exchange, queue, routing_key, exchange_type):
        try:
            logger.info(f"Attempting to connect to RabbitMQ at host: {RABBITMQ_HOST}:{RABBITMQ_PORT}")
            params = None
            self.queue = queue
            if RABBIT_LOCAL == str(1) or RABBIT_LOCAL == 1:
                params = pika.ConnectionParameters(
                    host=RABBITMQ_HOST, 
                    port=RABBITMQ_PORT, 
                    credentials=credentials, 
                    heartbeat=60, 
                    blocked_connection_timeout=30
                )
            else:
                ssl_context = ssl.create_default_context()
                params = pika.ConnectionParameters(
                    host=RABBITMQ_HOST, 
                    port=RABBITMQ_PORT,
                    virtual_host="/",
                    credentials=credentials, 
                    heartbeat=60, 
                    blocked_connection_timeout=30,
                    ssl_options=pika.SSLOptions(context=ssl_context)
                )
            self.connection = pika.BlockingConnection(params)
            logger.info("Successfully established connection to RabbitMQ.")
            self.channel = self.connection.channel()
            self.channel.exchange_declare(exchange=exchange, exchange_type=exchange_type, durable=True)
            self.channel.queue_declare(queue=queue, durable=True)
            self.channel.queue_bind(exchange=exchange, queue=queue, routing_key=routing_key)
            self.channel.basic_qos(prefetch_count=prefetch_count)
            logger.info(f"RabbitMQ channel and queue '{self.queue}' configured successfully.")
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise # Re-raise the exception to terminate the task if connection fails
        except Exception as e:
            logger.exception("An unexpected error occurred during RabbitMQ setup.")
            raise


    def set_callback(self, callback_):
        self.channel.basic_consume(queue=self.queue, on_message_callback=callback_)

    def get_connection(self)->pika.BlockingConnection:
        return self.connection
        
    def get_channel(self):
        return self.channel