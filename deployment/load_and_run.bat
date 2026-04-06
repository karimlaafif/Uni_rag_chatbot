@echo off
echo Loading images on supervisor machine...
docker load -i images/fastapi_app.tar
docker load -i images/qdrant.tar
docker load -i images/ollama.tar
docker load -i images/redis.tar

echo Starting services...
docker-compose up -d

echo Reminder: Run this command to pull the mistral model:
echo docker exec -it uni_rag_chatbot-ollama-1 ollama run mistral
