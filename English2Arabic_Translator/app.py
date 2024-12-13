from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException, Request
from shared.base_service import BaseService
from fastapi.middleware.gzip import GZipMiddleware
from cachetools import TTLCache
from kafka import KafkaProducer
from kafka.errors import KafkaError
from pydantic import BaseModel
from dotenv import load_dotenv
import hashlib
import ollama
import logging
import asyncio
import json
import time
import os
from contextlib import asynccontextmanager
from circuitbreaker import circuit
import uuid

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.kafka_producer = await init_kafka()
    logger.info("Kafka producer initialized")
    yield
    # Shutdown
    if hasattr(app.state, 'kafka_producer'):
        app.state.kafka_producer.close()
        logger.info("Kafka producer closed")

api_router = APIRouter(prefix="/api/v1")
service = BaseService("e2a_translator")  # Changed from "english_arabic_translator"
app = service.app
app.lifespan = lifespan  # to Set lifespan for the service app

app.add_middleware(GZipMiddleware, minimum_size=1000)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache configuration
translation_cache = TTLCache(maxsize=100, ttl=3600)

class TranslationRequest(BaseModel):
    text: str
    formality: str = "neutral"  # formal, neutral, informal

class TranslationStatus(BaseModel):
    id: str
    status: str
    result: dict = None
    error: str = None

# In-memory status storage (replace with Redis in production)
translation_status = {}

FORMALITY_PROMPTS = {
    "formal": "Translate to formal Arabic (provide ONLY the Arabic translation):",
    "neutral": "Translate to Arabic (provide ONLY the Arabic translation):",
    "informal": "Translate to informal Arabic (provide ONLY the Arabic translation):"
}

@circuit(failure_threshold=5, recovery_timeout=60)
def generate_translation(prompt: str) -> str:
    with service.request_latency.time():
        try:
            client = ollama.Client(host=os.getenv('OLLAMA_API_URL', 'http://ollama:11434'))
            response = client.generate(
                model=os.getenv('MODEL_NAME', 'llama3.1:3b'),
                prompt=prompt,
                options={
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'num_ctx': 2048,
                    'num_predict': 1024,
                }
            )
            return response['response']
        except Exception as e:
            logger.error(f"Circuit breaker: {str(e)}")
            raise

async def init_kafka():
    try:
        return KafkaProducer(
            bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3
        )
    except KafkaError as e:
        logger.error(f"Kafka initialization error: {e}")
        return None

async def send_to_kafka(producer, message):
    if not producer:
        return
    try:
        future = producer.send('translator_requests', message)  # Changed topic name
        await asyncio.get_event_loop().run_in_executor(None, future.get, 60)
    except Exception as e:
        logger.error(f"Kafka send error: {e}")

@api_router.post("/translate/en2ar")
async def translate_text(request: TranslationRequest, background_tasks: BackgroundTasks):
    request_id = str(uuid.uuid4())
    try:
        service.request_count.inc()
        cache_key = hashlib.md5(f"{request.text}{request.formality}".encode()).hexdigest()
        
        if cache_key in translation_cache:
            result = translation_cache[cache_key]
            translation_status[request_id] = {"status": "completed", "result": result}
            return {
                "id": request_id,
                "status": "completed",
                "result": result,
                "cache_hit": True
            }
        
        # Try immediate translation first
        try:
            prompt = f"""{FORMALITY_PROMPTS.get(request.formality, FORMALITY_PROMPTS["neutral"])}

{request.text}

Reply with ONLY the Arabic translation, no explanations or transliterations."""
        
            translation = generate_translation(prompt)
            arabic_only = ''.join(char for char in translation if '\u0600' <= char <= '\u06FF' or char in ['؟', '،', ' '])
            arabic_only = ' '.join(arabic_only.split())
            
            result = {"translation": arabic_only, "formality": request.formality}
            translation_cache[cache_key] = result
            translation_status[request_id] = {"status": "completed", "result": result}
            
            # Process Kafka and other async operations in background
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

@api_router.get("/translate/en2ar/status/{request_id}")
async def get_translation_status(request: Request, request_id: str):  # Added Request parameter
    if request_id not in translation_status:
        raise HTTPException(status_code=404, detail="Translation request not found")
    
    return translation_status[request_id]

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

async def process_translation(request: TranslationRequest, request_id: str, cache_key: str):
    try:
        prompt = f"""{FORMALITY_PROMPTS.get(request.formality, FORMALITY_PROMPTS["neutral"])}

{request.text}

Reply with ONLY the Arabic translation, no explanations or transliterations."""
    
        translation = generate_translation(prompt)

        arabic_only = ''.join(char for char in translation if '\u0600' <= char <= '\u06FF' or char in ['؟', '،', ' '])
        arabic_only = ' '.join(arabic_only.split())
    
        result = {"translation": arabic_only, "formality": request.formality}
        translation_cache[cache_key] = result
    
        if hasattr(app.state, 'kafka_producer'):
            await send_to_kafka(
                app.state.kafka_producer,
                {
                    'text': request.text,
                    'formality': request.formality,
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
