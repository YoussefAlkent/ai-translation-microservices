from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from contextlib import asynccontextmanager

@asynccontextmanager
async def base_lifespan(app: FastAPI):
    yield

class BaseService:
    def __init__(self, service_name: str):
        # Create a custom registry for this service instance
        self.registry = CollectorRegistry()
        
        # Format service name for Prometheus (replace hyphens with underscores)
        metric_name = service_name.replace('-', '_')
        
        # Add Prometheus metrics with custom registry
        self.request_count = Counter(
            f'{metric_name}_requests_total',
            f'Total {service_name} requests',
            registry=self.registry
        )
        self.request_latency = Histogram(
            f'{metric_name}_request_latency_seconds',
            f'{service_name} request latency in seconds',
            registry=self.registry
        )

        # Initialize FastAPI with lifespan
        self.app = FastAPI(lifespan=base_lifespan)

        # Create metrics endpoint
        @self.app.get("/metrics")
        async def metrics():
            return Response(
                generate_latest(self.registry),
                media_type=CONTENT_TYPE_LATEST
            )

        # Add health check endpoint
        @self.app.get("/health")
        async def health():
            return {"status": "healthy"}

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
