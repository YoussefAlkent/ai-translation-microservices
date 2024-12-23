from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException, Request
from shared.base_service import BaseService
from fastapi.middleware.gzip import GZipMiddleware
from cachetools import TTLCache
from confluent_kafka import Producer  # Changed import to confluent_kafka
from confluent_kafka import KafkaError  # Changed import to confluent_kafka
from pydantic import BaseModel
from dotenv import load_dotenv
import hashlib
import logging
import asyncio
import json
import time
import os
from contextlib import asynccontextmanager
from circuitbreaker import circuit
import uuid
from transformers import MarianMTModel, MarianTokenizer

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Script
    app.state.kafka_producer = await init_kafka()
    logger.info("[SUCCESS:E2A] Kafka producer initialized")
    yield

    # Shutdown Script
    if hasattr(app.state, 'kafka_producer'):
        app.state.kafka_producer.close()
        logger.info("[SUCCESS:E2A] Kafka producer closed")

api_router = APIRouter(prefix="/api/v1")
service = BaseService("e2a_translator")
app = service.app
app.lifespan = lifespan
app.add_middleware(GZipMiddleware, minimum_size=1000)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

translation_cache = TTLCache(maxsize=100, ttl=3600)

model = MarianMTModel.from_pretrained(os.getenv('MODEL_DIRECTORY', './model'))
tokenizer = MarianTokenizer.from_pretrained(os.getenv('MODEL_DIRECTORY', './model'))
class TranslationRequest(BaseModel):
    text: str

class TranslationStatus(BaseModel):
    id: str
    status: str
    result: dict = None
    error: str = None

#TODO: Replace with Redis
translation_status = {}

@circuit(failure_threshold=5, recovery_timeout=60)
def generate_translation(prompt:str) -> str:
    with service.request_latency.time():
        try:
            inputs = tokenizer([prompt], return_tensors="pt", padding=True)
            outputs = model.generate(**inputs)
            translation = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return translation
        except Exception as e:
            logger.error(f"Translation generation error: {str(e)}")
            raise

async def init_kafka():
    try:
        # Initialize KafkaProducer from confluent_kafka
        conf = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
            'acks': 'all',
            'retries': 3
        }
        producer = Producer(conf)
        return producer
    except KafkaError as e:
        logger.error(f"Kafka initialization error: {e}")
        return None

async def send_to_kafka(producer, message):
    if not producer:
        return
    try:
        # Use producer.produce instead of producer.send
        producer.produce('translator_requests', value=json.dumps(message), callback=delivery_report)
        producer.flush()
    except Exception as e:
        logger.error(f"Kafka send error: {e}")

def delivery_report(err, msg):
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}]")

@api_router.post("/translate/ar2en")
async def translate_text(request: TranslationRequest, background_tasks: BackgroundTasks):
    request_id = str(uuid.uuid4())
    try:
        service.request_count.inc()
        cache_key = hashlib.md5(f"{request.text}".encode()).hexdigest()

        if cache_key in translation_cache:
            result = translation_cache[cache_key]
            translation_status[request_id] = {"status": "completed", "result": result}
            return {
                'id': request_id,
                'status': 'completed',
                'result': result,
                'cache_hit': True
            }
        try:
            #TODO: change to en
            prompt = f"{request.text}"
            translation = generate_translation(prompt)

            result = {"translation": translation}
            translation_cache[cache_key] = result
            translation_status[request_id] = {"status": "completed", "result": result}

            background_tasks.add_task(process_translation, request, request_id, cache_key)

            return {
                "id": request_id,
                "status": "completed",
                "result": result,
                "cache_hit": False
            }
        except Exception as e:
            # Fall back to background processing if immediate translation fails
            translation_status[request_id] = {"status": "processing"}
            background_tasks.add_task(process_translation, request, request_id, cache_key)
            return {"id": request_id, "status": "processing"}

    except Exception as e:
        translation_status[request_id] = {"status": "error", "error": str(e)}
        raise HTTPException(status_code=500, detail=str(e))
    
async def process_translation(request: TranslationRequest, request_id: str, cache_key: str):
    try:
        prompt = f">>ara<< {request.text}"
        translation = generate_translation(prompt)
        result = {"translation": translation}
        translation_cache[cache_key] = result

        if hasattr(app.state, 'kafka_producer'):
            await send_to_kafka(
                app.state.kafka_producer,
                {
                    'text': request.text,
                    'timestamp': time.time(),
                    'cache_key': cache_key
                }
            )
        translation_status[request_id] = {"status": "completed", "result": result}
    except Exception as e:
        translation_status[request_id] = {"status": "error", "error": str(e)}

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    import multiprocessing

    uvicorn.run(
        "app:app",  # Use module:app format
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload in production
        workers=multiprocessing.cpu_count(),
        log_level="info"
    )
