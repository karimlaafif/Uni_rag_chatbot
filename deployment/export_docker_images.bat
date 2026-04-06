@echo off
echo Building the API image...
docker-compose build

echo Saving images to tarballs for offline supervisor nodes...
if not exist images mkdir images
docker save uni_rag_chatbot-fastapi_app:latest -o images/fastapi_app.tar
docker save qdrant/qdrant:v1.9.0 -o images/qdrant.tar
docker save ollama/ollama:latest -o images/ollama.tar
docker save redis:7-alpine -o images/redis.tar

echo Done! Transfer the 'images' folder and 'docker-compose.yml' to your supervisor machines.
