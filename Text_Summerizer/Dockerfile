# Use a Python base image
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Ollama CLI and dependencies
RUN curl -fsSL https://ollama-download-url | bash

# Preload the model
RUN ollama pull llama3.2:3b

# Copy shared module first
COPY shared/ /app/shared/

# Copy only requirements first for better caching
COPY Text_Summerizer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --compile

COPY Text_Summerizer/ .
ENV PYTHONUNBUFFERED=1

# Run both services
CMD ollama serve & python app.py
