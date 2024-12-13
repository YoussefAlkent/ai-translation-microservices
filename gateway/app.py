from fastapi import FastAPI, HTTPException, Request, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from pydantic import BaseModel
import httpx
import os
import time
from prometheus_client import make_asgi_app, Counter, Histogram

# Initialize tracing
resource = Resource.create({
    "service.name": "gateway",
    "deployment.environment": os.getenv("DEPLOYMENT_ENV", "production")
})
trace.set_tracer_provider(TracerProvider(resource=resource))

# Configure OTLP exporter
otlp_exporter = OTLPSpanExporter(
    endpoint=f"http://{os.getenv('JAEGER_HOST', 'jaeger')}:4318/v1/traces"
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)
tracer = trace.get_tracer(__name__)

# Initialize metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="API Gateway")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add security middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]
)

# Initialize metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

SERVICES = {
    "summarizer": os.getenv("SUMMARIZER_URL", "http://summarizer:8000"),
    "e2a_translator": os.getenv("E2A_TRANSLATOR_URL", "http://e2a-translator:8000"),
    "a2e_translator": os.getenv("A2E_TRANSLATOR_URL", "http://a2e-translator:8000")
}

# Add SERVICE_PATHS back
API_VERSION_PREFIX = "/api/v1"
SERVICE_PATHS = {
    f"{API_VERSION_PREFIX}/translate/english-to-arabic": ("e2a_translator", "api/v1/translate/en2ar"),
    f"{API_VERSION_PREFIX}/translate/arabic-to-english": ("a2e_translator", "api/v1/translate/ar2en")
}

# Add request/response models
class SummarizeRequest(BaseModel):
    text: str
    style: str = "formal"
    max_length: int = 500
    bullet_points: bool = False

class SummarizeResponse(BaseModel):
    summary: str

# Remove the SERVICE_PATHS mapping and add specific route handlers
@app.post("/api/v1/summarize")
@limiter.limit("100/minute")
async def summarize(request: Request, text_request: SummarizeRequest):
    client = httpx.AsyncClient(timeout=60.0)  # Increase timeout
    with tracer.start_as_current_span(
        "summarize_request",
        attributes={"service": "summarizer"}
    ) as span:
        try:
            # Add debug logging
            print(f"Sending request to summarizer: {SERVICES['summarizer']}/api/v1/summarize")
            print(f"Request payload: {text_request.dict()}")
            
            response = await client.post(
                f"{SERVICES['summarizer']}/api/v1/summarize",
                json={
                    "text": text_request.text,
                    "style": text_request.style,
                    "max_length": text_request.max_length,
                    "bullet_points": text_request.bullet_points
                },
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
            
            # Add response logging
            print(f"Summarizer response status: {response.status_code}")
            print(f"Summarizer response: {response.text}")
            
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Summarizer service error: {response.text}"
                )
                
            return response.json()
            
        except httpx.HTTPError as e:
            print(f"HTTP error occurred: {str(e)}")  # Add error logging
            raise HTTPException(
                status_code=500,
                detail=f"Error communicating with summarizer service: {str(e)}"
            )
        except Exception as e:
            print(f"Unexpected error: {str(e)}")  # Add error logging
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}"
            )
        finally:
            await client.aclose()

@app.get("/api/v1/summarize/status/{request_id}")
@limiter.limit("100/minute")
async def get_summary_status(request: Request, request_id: str):  # Added Request parameter
    client = httpx.AsyncClient(timeout=30.0)
    try:
        response = await client.get(
            f"{SERVICES['summarizer']}/api/v1/summarize/status/{request_id}",
            headers={"Accept": "application/json"}
        )
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Summary request not found")
        elif response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Summarizer service error: {response.text}"
            )
            
        return response.json()
        
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error communicating with summarizer service: {str(e)}"
        )
    finally:
        await client.aclose()

# Add specific translation handler
@app.post("/api/v1/translate/english-to-arabic")
@limiter.limit("100/minute")
async def translate_english_to_arabic(request: Request, body: dict):
    client = httpx.AsyncClient(timeout=60.0)
    with tracer.start_as_current_span(
        "translate_request",
        attributes={"service": "e2a_translator"}
    ) as span:
        try:
            response = await client.post(
                f"{SERVICES['e2a_translator']}/api/v1/translate/en2ar",
                json=body,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Translation service error: {response.text}"
                )
                
            return response.json()
            
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error communicating with translation service: {str(e)}"
            )
        finally:
            await client.aclose()

# Add auth endpoints
@app.post("/auth/{action}")
@limiter.limit("20/minute")
async def handle_auth(action: str, request: Request):
    if action not in ["signup", "signin"]:
        raise HTTPException(status_code=404, detail="Invalid auth endpoint")
    
    client = httpx.AsyncClient(timeout=30.0)
    try:
        response = await client.post(
            f"http://user-service:3001/auth/{action}",
            json=await request.json(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error communicating with auth service: {str(e)}"
        )
    finally:
        await client.aclose()

# Keep the generic gateway route for other endpoints
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
@limiter.limit("100/minute")
async def gateway(path: str, request: Request):
    # Exclude paths that have specific handlers
    if path == "api/v1/summarize":
        raise HTTPException(status_code=404, detail="Use the specific endpoint")
    
    full_path = f"/{path}"
    
    # Match service path
    service_info = None
    for pattern, info in SERVICE_PATHS.items():
        if full_path.startswith(pattern):
            service_info = info
            break
    
    if not service_info:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service_name, service_path = service_info
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")
    
    client = httpx.AsyncClient(timeout=30.0)  # Increase timeout to 30 seconds
    with tracer.start_as_current_span(
        "gateway_request",
        attributes={
            "service": service_name,
            "path": path,
            "method": request.method,
        }
    ) as span:
        try:
            url = f"{SERVICES[service_name]}/{service_path}"
            response = await client.request(
                method=request.method,
                url=url,
                headers=request.headers,
                content=await request.body()
            )
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except httpx.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail="Request timed out while processing"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
        finally:
            await client.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
