#!/bin/bash

# Start Ollama server in the background
ollama serve &

# Wait for the server to start
sleep 5

# Pull the llama3.2 model
ollama pull llama3.2:3b

# Start the Python app in the foreground
exec python app.py
