#!/bin/bash
echo "Building the API image..."
docker-compose build

echo "Saving images to tarballs for offline supervisor nodes..."
mkdir -p images
docker save uni_rag_chatbot_fastapi_app:latest | gzip > images/fastapi_app.tar.gz
docker save qdrant/qdrant:v1.9.0 | gzip > images/qdrant.tar.gz
docker save ollama/ollama:latest | gzip > images/ollama.tar.gz
docker save redis:7-alpine | gzip > images/redis.tar.gz

echo "Done! Transfer the 'images' folder and 'docker-compose.yml' to your supervisor machines."
