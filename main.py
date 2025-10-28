import os
from Config.RabbitMQ import RabbitMQ
from Config.PostgresClient import PostgresClient
from Config.Client import Client
from dotenv import load_dotenv
from Actions.MaterialsGeneration import MaterialsGeneration
from Actions.QuestionGeneration import QuestionGeneration
import json
import logging

load_dotenv()
# --- Python logger ---
logging.basicConfig(
    level=logging.INFO, # Adjust to logging.DEBUG for more verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

AI_QUESTION = "generate_questions"
AI_MATERIALS = "generate_materials"

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

def create_callback(db):
    def on_message(channel, method, properties, body):
        try:
            client = Client(body)  # make sure Client never throws; it should default to {} on parse error
            gen_type = client.get_generation_type()
            logger.info("Received message: delivery_tag=%s, routing_key=%s, gen_type=%s",
                        method.delivery_tag, getattr(method, "routing_key", None), gen_type)
            logger.debug("Properties: %r", properties)

            if gen_type == AI_MATERIALS:
                ai = MaterialsGeneration(db, channel, method, client, MODEL)
            elif gen_type == AI_QUESTION:
                ai = QuestionGeneration(db, channel, method, client, MODEL)
            else:
                logger.warning("Unknown generation_type: %r. NACK (dead-letter).", gen_type)
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Step 1: data requirements
            try:
                res = ai.query_database_for_requirements()
                logger.info("%s.query_database_for_requirements -> %s", ai.__class__.__name__, bool(res))
            except Exception as e:
                logger.exception("Requirement query failed: %s", e)
                # Persist error state if your class supports it:
                try:
                    ai.error_model_result()
                except Exception:
                    logger.exception("Failed to write error state")
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Validate result shape
            if not res or not isinstance(res, (list, tuple)) or len(res) < 2:
                logger.error("Requirements result invalid: %r", res)
                try:
                    ai.error_model_result()
                except Exception:
                    logger.exception("Failed to write error state")
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Step 2: run model
            try:
                model = ai.run_model(res[0], res[1])
                logger.info("%s.run_model -> %s", ai.__class__.__name__, "OK" if model else "None")
            except Exception as e:
                logger.exception("Model execution failed: %s", e)
                try:
                    ai.error_model_result()
                except Exception:
                    logger.exception("Failed to write error state")
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            if not model:
                try:
                    ai.error_model_result()
                except Exception:
                    logger.exception("Failed to write error state")
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Step 3: save results
            try:
                ai.save_model_results(model)
                logger.info("Results saved successfully. ACK.")
                channel.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.exception("Saving results failed: %s", e)
                # Decide policy: requeue or dead-letter. Often dead-letter to avoid hot-loop.
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception:
            # absolutely last-resort catch: never leave a message un-acked
            logger.exception("Unexpected error in on_message; NACK (dead-letter).")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    return on_message


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