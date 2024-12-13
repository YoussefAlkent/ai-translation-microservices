# AI-Powered Text Processing Microservices

A robust microservices architecture providing advanced text summarization and bidirectional English-Arabic translation using state-of-the-art AI models.

## Table of Contents
- [AI-Powered Text Processing Microservices](#ai-powered-text-processing-microservices)
  - [Table of Contents](#table-of-contents)
  - [Services Overview](#services-overview)
  - [Architecture](#architecture)
  - [Prerequisites](#prerequisites)
  - [Deployment](#deployment)
  - [API Reference](#api-reference)
    - [Summarization](#summarization)
    - [Translation](#translation)
  - [Monitoring](#monitoring)
  - [Development](#development)
  - [Troubleshooting](#troubleshooting)
  - [License](#license)

## Services Overview

Detailed breakdown of each service:

- **Gateway Service** (Port 8080)
  - Route management and load balancing
  - Request validation and rate limiting
  - API documentation (Swagger UI)
  - Authentication and authorization

- **Summarizer Service** (Internal Port 8000)
  - AI-powered text summarization
  - Multiple summarization styles
  - Caching layer for improved performance
  - Bulk processing capabilities

- **Translator Service** (Internal Port 8000)
  - Bidirectional English-Arabic translation
  - Context-aware translations
  - Terminology consistency
  - Custom dictionary support

- **Supporting Infrastructure**
  - Kafka (Port 9094): Async message processing
  - Redis (Port 6379): Caching and rate limiting
  - Prometheus (Port 9090): Metrics collection
  - Grafana (Port 3000): Visualization and alerting

## Architecture

```
┌─────────┐     ┌───────────┐     ┌──────────────┐
│ Client  │────▶│  Gateway  │────▶│ Summarizer   │
└─────────┘     │  (nginx)  │     └──────────────┘
                │           │     ┌──────────────┐
                │           │────▶│ Translator   │
                └───────────┘     └──────────────┘
                     │           ┌──────────────┐
                     └──────────▶│    Redis     │
                     │           └──────────────┘
                     │           ┌──────────────┐
                     └──────────▶│    Kafka     │
                                └──────────────┘
                     │           ┌──────────────┐
                     └──────────▶│ Prometheus   │
                                └──────────────┘
```

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- 20GB disk space

## Deployment

1. **Clone and Deploy**
```bash
git clone <repository-url>
cd Cloud\ Project
docker-compose up -d
```

2. **Verify Services**
```bash
docker-compose ps
curl http://localhost:8080/health
```

3. **Scale Services (Optional)**
```bash
docker-compose up -d --scale summarizer=3 --scale translator=2
```

## API Reference

### Summarization
```bash
curl -X POST http://localhost:8080/api/v1/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your long text here...",
    "style": "formal",
    "max_length": 500
  }'
```

### Translation
```bash
curl -X POST http://localhost:8080/api/v1/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, how are you?",
    "formality": "formal"
  }'
```

## Monitoring

Access monitoring tools:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Troubleshooting

```bash
# View logs
docker-compose logs -f <service-name>

# Restart services
docker-compose restart <service-name>

# Reset everything
docker-compose down && docker-compose up -d
```

## License

MIT License
