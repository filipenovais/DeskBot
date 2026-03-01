#!/bin/bash

# Start Ollama server in the background
ollama serve &

# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
while ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; do
    sleep 1
done
echo "Ollama is ready!"

# Pull a small model if not already present
# Using qwen2.5:0.5b - very small (~400MB) but capable model
MODEL="qwen2.5:0.5b"
echo "Checking for model: $MODEL"

if ! ollama list | grep -q "$MODEL"; then
    echo "Pulling model: $MODEL (this may take a few minutes on first run)..."
    ollama pull $MODEL
    echo "Model $MODEL pulled successfully!"
else
    echo "Model $MODEL already available."
fi

echo "Ollama service ready at http://localhost:11434/v1/"
echo "Available model: $MODEL"

# Keep the container running
wait
