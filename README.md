# University Multimodal RAG Chatbot MVP

A production-ready MVP for a university multimodal RAG (Retrieval-Augmented Generation) chatbot.

## Features
- **Multimodal**: Text and Image inputs (via CLIP and dense embeddings).
- **RAG**: Combines Qdrant dense vector search with MS-Marco Reranking.
- **REST API**: Built with FastAPI, rate limiting, and JWT Auth abstractions.
- **Monitoring**: Integrated with LangSmith tracing.
- **Benchmarking**: Automated evaluation suite via RAGAS interface comparing models (Mistral 7B, GPT-4o-mini, Llama 3.1 8B).

## Architecture

```text
User --> [ FastAPI Endpoint ] --> Rate Limiting (SlowAPI)
               |
         [ RAG Chain (LCEL) ] <--> [ Redis (Session Memory) ]
               |
               v
      [ Qdrant Vectorstore ] <--- [ Data Ingestion Pipeline ]
        (Dense + Sparse)            (PDF, DOCX, Web, DB, Images)
               |
               v
  [ Ollama / OpenAI / Anthropic ]
```

## Setup Guide

1. Clone and cd into the specific folder.
2. Ensure you have Docker and Docker Compose installed.
3. Setup `config.py` and `.env` by copying `.env.example`:
   ```bash
   cp .env.example .env
   ```
4. Build and start via Docker Compose:
   ```bash
   docker-compose up -d --build
   ```
5. Install Ollama locally (if not using dockerized ollama model pulling strategy) and pull Mistral: `ollama run mistral`

## API Usage

- **Chatting**:
  `POST /chat`
  ```json
  {
      "query": "What are the rules for dorms?",
      "session_id": "user123_session",
      "user_role": "student"
  }
  ```

- **Knowledge Status**:
  `GET /knowledge/status`

- **Benchmark Trigger**:
  `POST /benchmark/run`
  Returns `job_id`.

- **Benchmark Results**:
  `GET /benchmark/results/{job_id}`

## How to Add New Knowledge

To update the system's knowledge without retraining the underlying LLM:
Use the `POST /knowledge/update` endpoint. This is an admin-only endpoint where you can upload a file (PDF, Docx, Image) or provide a URL along with necessary metadata. 
The system runs it through the delta ingestion pipeline, chunking, hashing, and storing it into the Qdrant database. The updated content is immediately available to the RAG Chain during subsequent queries.

## Benchmarks Interpretation

Benchmarks output a `benchmark_results.html` and `.csv`. A `quality_score` is computed based on context precision (0.2), context recall (0.2), faithfulness (0.3), and answer relevancy (0.3) metrics via simulated Ragas evaluation.
