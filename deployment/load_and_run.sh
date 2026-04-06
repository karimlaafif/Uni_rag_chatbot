#!/bin/bash
echo "Loading images on supervisor machine..."
docker load < images/fastapi_app.tar.gz
docker load < images/qdrant.tar.gz
docker load < images/ollama.tar.gz
docker load < images/redis.tar.gz

echo "Starting services..."
docker-compose up -d

echo "Pulling mistral model inside Ollama container..."
docker exec -it $(docker-compose ps -q ollama) ollama run mistral
