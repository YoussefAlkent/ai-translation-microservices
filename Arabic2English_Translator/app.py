import json
import logging
import time
import uuid
from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from confluent_kafka import Consumer, Producer, KafkaError
from pydantic import BaseModel
from transformers import MarianMTModel, MarianTokenizer
from dotenv import load_dotenv
import hashlib
from contextlib import asynccontextmanager
from circuitbreaker import circuit

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app and router
api_router = APIRouter(prefix="/api/v1")
app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Initialize Kafka consumer and producer
consumer = None
producer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Kafka consumer and producer
    app.state.kafka_consumer = await init_kafka_consumer()
    app.state.kafka_producer = await init_kafka_producer()
    logger.info("[SUCCESS] Kafka consumer and producer initialized")
    yield
    # Cleanup Kafka consumer and producer
    if hasattr(app.state, 'kafka_consumer'):
        app.state.kafka_consumer.close()
        logger.info("[SUCCESS] Kafka consumer closed")
    if hasattr(app.state, 'kafka_producer'):
        app.state.kafka_producer.close()
        logger.info("[SUCCESS] Kafka producer closed")

app.lifespan = lifespan

# Translation model setup
model = MarianMTModel.from_pretrained(os.getenv('MODEL_DIRECTORY', './model'))
tokenizer = MarianTokenizer.from_pretrained(os.getenv('MODEL_DIRECTORY', './model'))

class TranslationRequest(BaseModel):
    correlation_id: str
    user_id: str
    chat_id: str
    text: str

class TranslationStatus(BaseModel):
    id: str
    status: str
    result: dict = None
    error: str = None

# Kafka initialization functions
async def init_kafka_consumer():
    try:
        # Initialize Kafka Consumer
        conf = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
            'group.id': 'translator-group',
            'auto.offset.reset': 'earliest'
        }
        consumer = Consumer(conf)
        consumer.subscribe(['a2e-translation'])
        return consumer
    except KafkaError as e:
        logger.error(f"Kafka consumer initialization error: {e}")
        return None

async def init_kafka_producer():
    try:
        # Initialize Kafka Producer
        conf = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
            'acks': 'all',
            'retries': 3
        }
        producer = Producer(conf)
        return producer
    except KafkaError as e:
        logger.error(f"Kafka producer initialization error: {e}")
        return None

async def send_to_kafka(producer, message):
    if not producer:
        return
    try:
        # Send message to Kafka topic
        producer.produce('a2e-translation-response', value=json.dumps(message), callback=delivery_report)
        producer.flush()
    except Exception as e:
        logger.error(f"Kafka send error: {e}")

def delivery_report(err, msg):
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}]")

@circuit(failure_threshold=5, recovery_timeout=60)
def generate_translation(prompt: str) -> str:
    try:
        inputs = tokenizer([prompt], return_tensors="pt", padding=True)
        outputs = model.generate(**inputs)
        translation = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return translation
    except Exception as e:
        logger.error(f"Translation generation error: {str(e)}")
        raise

# Kafka consumer function
async def consume_kafka_messages(consumer):
    try:
        while True:
            msg = consumer.poll(1.0)  # Wait for message for up to 1 second
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.info(f"End of partition reached: {msg.partition}")
                else:
                    logger.error(f"Error while consuming: {msg.error()}")
            else:
                # Deserialize the message
                message = json.loads(msg.value().decode('utf-8'))

                # Extract the necessary fields from the consumed message
                request_data = message.value
                request = TranslationRequest(**request_data)

                if not request.user_id or not request.chat_id or not request.text:
                    logger.error("Missing required fields in the message.")
                    continue

                # Generate the output text (translation in this case)
                output_text = generate_translation(request.text)

                # Prepare the response message with user-id, chat-id, input text, and output text
                response_message = {
                    'correlation-id': request.correlation_id,
                    'user-id': request.user_id,
                    'chat-id': request.chat_id,
                    'input-text': request.text,
                    'output-text': output_text
                }

                # Send the response message to the a2e-translation-response topic
                if hasattr(app.state, 'kafka_producer'):
                    await send_to_kafka(app.state.kafka_producer, response_message)

                logger.info(f"Processed message and sent to response topic: {response_message}")

    except Exception as e:
        logger.error(f"Consumer error: {e}")

# FastAPI translation route
@api_router.post("/translate/ar2en")
async def translate_text(request: TranslationRequest, background_tasks: BackgroundTasks):
    request_id = str(uuid.uuid4())
    try:
        cache_key = hashlib.md5(f"{request.text}".encode()).hexdigest()

        # Simulate translation generation
        output_text = generate_translation(request.text)

        result = {"translation": output_text}

        background_tasks.add_task(process_translation, request, request_id, cache_key)

        return {
            "id": request_id,
            "status": "completed",
            "result": result,
            "cache_hit": False
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Translation background processing task
async def process_translation(request: TranslationRequest, request_id: str, cache_key: str):
    try:
        output_text = generate_translation(request.text)
        result = {"translation": output_text}

        # Send the processed translation result to Kafka
        if hasattr(app.state, 'kafka_producer'):
            await send_to_kafka(
                app.state.kafka_producer,
                {
                    'text': request.text,
                    'user-id': "example_user_id",  # Assume user ID is available
                    'chat-id': "example_chat_id",  # Assume chat ID is available
                    'output-text': output_text,
                    'cache_key': cache_key
                }
            )
    except Exception as e:
        logger.error(f"Error processing translation: {e}")

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    import multiprocessing

    # Start FastAPI server
    uvicorn.run(
        "app:app",  # Use module:app format
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload in production
        workers=multiprocessing.cpu_count(),
        log_level="info"
    )
