<div align="center">

```
██████╗  █████╗  ██████╗      ██╗   ██╗███╗   ██╗██╗██╗   ██╗
██╔══██╗██╔══██╗██╔════╝      ██║   ██║████╗  ██║██║██║   ██║
██████╔╝███████║██║  ███╗     ██║   ██║██╔██╗ ██║██║██║   ██║
██╔══██╗██╔══██║██║   ██║     ██║   ██║██║╚██╗██║██║╚██╗ ██╔╝
██║  ██║██║  ██║╚██████╔╝     ╚██████╔╝██║ ╚████║██║ ╚████╔╝
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝       ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝
```

**University Multimodal RAG — Intelligent Knowledge Chatbot**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-0.2+-1C3C3C?style=flat-square&logo=chainlink&logoColor=white)](https://langchain.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-DC244C?style=flat-square)](https://qdrant.tech)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-Apache_2.0-green?style=flat-square)](LICENSE)
[![RAGAS](https://img.shields.io/badge/Benchmarks-RAGAS-FF6B35?style=flat-square)](https://docs.ragas.io)

<br/>

> *Ask anything. Get answers grounded in your university's real documents.*
> *No hallucinations. No retraining. No limits.*

<br/>

[**Quick Start**](#-quick-start-5-minutes) · [**Architecture**](#-architecture) · [**Benchmarks**](#-benchmarks) · [**API**](#-api-reference) · [**Add Knowledge**](#-adding-new-knowledge)

</div>

---

## 🧠 What is this?

**RAG-UNIV** is a production-grade, multimodal Retrieval-Augmented Generation chatbot built for universities. It ingests your institution's entire knowledge base — PDFs, course catalogs, regulations, websites, databases, images — and makes it instantly queryable in natural language.

```
Student:  "What are the prerequisites for the Machine Learning course?"
          "متى ينتهي تسجيل الامتحانات؟"
          "Comment faire appel d'une note ?"

Chatbot:  Accurate answer. Cited sources. Right language. Every time.
```

### Why RAG instead of fine-tuning?

| | Fine-tuning | **RAG (this project)** |
|---|---|---|
| Add new knowledge | Retrain for days 💸 | Upload a file ⚡ |
| Source citations | ❌ | ✅ Always |
| Hallucination risk | High | Near-zero |
| Update cost | GPU cluster | Zero |
| Data stays on-campus | Depends | ✅ Always |

---

## ✨ Features

- **🗂️ Universal Ingestion** — PDF, DOCX, HTML, images, SQL databases, REST APIs, LMS portals
- **🔍 Hybrid Search** — Dense vectors (semantic) + BM25 (lexical) fused with Reciprocal Rank Fusion
- **🎯 Cross-Encoder Re-ranking** — Top-20 → Top-5 precision boost on every query
- **🖼️ Multimodal** — Ask with text *and* images; CLIP handles visual retrieval
- **🔄 Zero-Retraining Updates** — New knowledge = upload file → done in minutes
- **🌍 Trilingual** — French, Arabic (RTL), English with auto-detection
- **📊 Mandatory Benchmarks** — RAGAS suite across 3+ models with quality scoring
- **🔒 Role-Based Access** — Students see student content, staff see staff content
- **⚡ LLM Agnostic** — Swap Mistral ↔ GPT-4o ↔ Llama with one env variable
- **📡 Observable** — Full LangSmith tracing on every chain call

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
│   📄 PDFs   🌐 Web Pages   🖼️ Images   🗄️ Databases   📚 LMS    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DATA ENGINEERING PIPELINE                       │
│                                                                  │
│  Fetch → Clean → Dedupe → Chunk → Tag Metadata → Delta Index    │
│                                                                  │
│  • SHA-256 hashing for delta ingestion (only new docs)          │
│  • SemanticChunker: 512 tokens, 64 overlap                      │
│  • Metadata: source, dept, access_level, language, version      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│               EMBEDDING + VECTOR STORE (Qdrant)                  │
│                                                                  │
│  nomic-embed-text (768d)  +  CLIP (512d)  +  BM25 sparse        │
│                                                                  │
│  Hybrid Search ──► RRF Fusion ──► Cross-Encoder Rerank          │
│      (top-20)                         (→ top-5)                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              LLM LAYER  (lightweight + updatable)                │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐    │
│  │ Mistral 7B  │  │  Phi-3 Mini │  │  GPT-4o-mini (ref)   │    │
│  │  [DEFAULT]  │  │  [FAST]     │  │  [BENCHMARK]         │    │
│  └─────────────┘  └─────────────┘  └──────────────────────┘    │
│                                                                  │
│           LLMFactory — swap via LLM_PROVIDER env var            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│               LANGCHAIN RAG CHAIN (LCEL)                         │
│                                                                  │
│  Query Router → MultiQueryRetriever → Hybrid Fetch → Rerank     │
│       → Redis Memory (k=10) → Prompt → LLM → Answer + Sources   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────┐  ┌──────────────────────────────────────┐
│   FASTAPI + JWT RBAC  │  │  BENCHMARKS (RAGAS)                  │
│                       │  │                                       │
│  POST /chat           │  │  Faithfulness · Relevancy            │
│  POST /knowledge/     │  │  Precision · Recall                  │
│       update          │  │  Latency p50/p95/p99                 │
│  GET  /benchmark/     │  │  3-model comparison table            │
│       results         │  │                                       │
└───────────────────────┘  └──────────────────────────────────────┘
```

---

## ⚡ Quick Start (5 minutes)

### Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Git
- 8 GB RAM minimum (16 GB recommended for local LLM)

### Step 1 — Clone and configure

```bash
git clone https://github.com/your-org/rag-univ.git
cd rag-univ
cp .env.example .env
```

Edit `.env` with your settings:

```env
LLM_PROVIDER=ollama          # ollama | openai | anthropic
OLLAMA_MODEL=mistral          # mistral | phi3 | gemma2
OPENAI_API_KEY=sk-...         # only if LLM_PROVIDER=openai
JWT_SECRET_KEY=your-secret    # generate with: openssl rand -hex 32
LANGCHAIN_API_KEY=ls__...     # from smith.langchain.com (free)
```

### Step 2 — Launch all services

```bash
docker compose up -d
```

This starts: **Qdrant** (vector DB) · **Ollama** (local LLM) · **Redis** (session memory) · **FastAPI** (your API)

### Step 3 — Pull the LLM

```bash
docker exec -it ollama ollama pull mistral
```

> ☕ First pull is ~4 GB. Grab a coffee.

### Step 4 — Ingest your first documents

```bash
# Drop your university PDFs into /data/documents/
cp /path/to/your/docs/*.pdf data/documents/

# Run the pipeline
python -m data_pipeline.ingestion --source data/documents/ --department academic
```

Watch the terminal — you'll see each document processed, chunked, and indexed in real time.

### Step 5 — Ask your first question

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the exam registration deadlines?",
    "session_id": "demo-session-001",
    "user_role": "student"
  }'
```

```json
{
  "answer": "Exam registration closes on January 15th for the winter session...",
  "sources": [
    { "title": "Academic Calendar 2024-25", "url": "...", "score": 0.94 }
  ],
  "model": "mistral:7b",
  "latency_ms": 1842,
  "tokens_used": 387
}
```

---

## 📁 Project Structure

```
rag-univ/
│
├── 📂 data_pipeline/
│   ├── ingestion.py          # Universal document loader + async crawler
│   ├── cleaning.py           # Dedup, normalize, language detection
│   ├── chunking.py           # SemanticChunker + RecursiveCharacter fallback
│   ├── metadata.py           # Tagging, ACL rules, versioning
│   └── vectorstore.py        # Qdrant manager: upsert, hybrid search, rerank
│
├── 📂 rag/
│   ├── chain.py              # Full LCEL RAG chain
│   ├── retriever.py          # MultiQuery + Hybrid + Reranker
│   ├── memory.py             # Redis-backed ConversationWindowMemory
│   ├── prompt.py             # System prompts (fr/ar/en)
│   └── llm_factory.py        # Ollama / OpenAI / Anthropic abstraction
│
├── 📂 api/
│   ├── main.py               # FastAPI app + all endpoints
│   ├── schemas.py            # Pydantic v2 request/response models
│   ├── auth.py               # JWT + RBAC middleware
│   └── rate_limit.py         # SlowAPI rate limiting
│
├── 📂 benchmarks/
│   ├── ragas_eval.py         # Full RAGAS suite across 3 models
│   ├── latency_bench.py      # Concurrent load test (p50/p95/p99)
│   └── results/              # benchmark_results.csv + .html report
│
├── 📂 data/
│   ├── documents/            # Drop your source files here
│   └── test_dataset/         # Generated Q&A pairs for RAGAS
│
├── docker-compose.yml
├── config.py                 # Pydantic BaseSettings from .env
├── requirements.txt
└── .env.example
```

---

## 🔄 Adding New Knowledge

> **This is the superpower of RAG. No retraining. No downtime. Ever.**

### Via API (production)

```bash
# Upload a new document
curl -X POST http://localhost:8000/knowledge/update \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -F "files=@new_regulation.pdf" \
  -F "department=academic" \
  -F "access_level=student"

# Or submit a URL to crawl
curl -X POST http://localhost:8000/knowledge/update \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{"urls": ["https://university.edu/new-policy"], "department": "admin"}'
```

### Via CLI (development)

```bash
python -m data_pipeline.ingestion \
  --source path/to/new/docs/ \
  --department registrar \
  --access-level student \
  --mode delta    # only processes changed files
```

### What happens under the hood

```
New file uploaded
      │
      ▼
SHA-256 hash check ──► Already indexed? → Skip ✓
      │ New/changed
      ▼
Parse → Clean → Chunk → Embed → Upsert into Qdrant
      │
      ▼
Knowledge available in < 3 minutes ⚡
LLM is NEVER touched.
```

---

## 📊 Benchmarks

Run the full evaluation suite:

```bash
python -m benchmarks.ragas_eval --models mistral phi3 gpt-4o-mini --questions 50
```

### Sample results

| Model | Faithfulness | Answer Relevancy | Context Precision | Context Recall | **Quality Score** | p95 Latency |
|---|---|---|---|---|---|---|
| Mistral 7B | 0.81 | 0.76 | 0.72 | 0.69 | **0.76** ✅ | 4.2s |
| Phi-3 Mini 3.8B | 0.74 | 0.71 | 0.67 | 0.64 | **0.71** ✅ | 1.8s |
| Llama 3.1 8B | 0.79 | 0.75 | 0.70 | 0.68 | **0.74** ✅ | 3.9s |
| GPT-4o-mini | 0.89 | 0.84 | 0.81 | 0.77 | **0.84** ✅ | 1.1s |

> **Quality Score** = `0.3×Faithfulness + 0.3×Relevancy + 0.2×Precision + 0.2×Recall`
> Minimum threshold for MVP validation: **≥ 0.70**

View the full interactive HTML report:

```bash
open benchmarks/results/benchmark_results.html
```

Run only the latency test:

```bash
python -m benchmarks.latency_bench --concurrent-users 10 --duration 60
```

---

## 🔌 API Reference

Full OpenAPI docs available at `http://localhost:8000/docs`

### `POST /chat`

```json
// Request
{
  "query": "string",
  "image_base64": "string (optional)",
  "session_id": "string",
  "user_role": "student | staff | admin"
}

// Response
{
  "answer": "string",
  "sources": [{ "title": "string", "url": "string", "score": 0.94 }],
  "session_id": "string",
  "model": "string",
  "latency_ms": 1842,
  "tokens_used": 387
}
```

### `POST /knowledge/update` *(admin only)*

Accepts multipart file uploads or JSON with `urls` array. Triggers delta ingestion pipeline.

### `GET /knowledge/status` *(admin only)*

Returns ingestion queue depth, last update timestamp, total indexed chunks.

### `POST /benchmark/run` *(admin only)*

Triggers async benchmark suite. Returns `{ "job_id": "uuid" }`.

### `GET /benchmark/results/{job_id}` *(admin only)*

Returns benchmark results as JSON or CSV.

### Authentication

```bash
# Get a token
curl -X POST http://localhost:8000/auth/token \
  -d '{"username": "user@university.edu", "password": "...", "role": "student"}'

# Use it
curl -H "Authorization: Bearer eyJ..." http://localhost:8000/chat
```

**Rate limits:** 20 req/min (student/staff) · 5 req/min for `/knowledge/update` (admin)

---

## 🤖 Switching Models

Change the LLM with zero code changes:

```env
# .env

# Local (default) — runs on your hardware, free, private
LLM_PROVIDER=ollama
OLLAMA_MODEL=mistral        # or: phi3, gemma2, llama3.1

# OpenAI — best quality, costs money
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Restart the API container — that's it.

```bash
docker compose restart api
```

---

## 🌍 Multilingual Support

The system auto-detects the user's language and responds accordingly.

```python
# French
"Quelles sont les conditions d'admission en master ?"
→ Réponse en français avec sources citées.

# Arabic (RTL)
"ما هي مواعيد التسجيل في الفصل الدراسي القادم؟"
→ الرد باللغة العربية مع الاستشهاد بالمصادر.

# English
"How do I appeal a failed grade?"
→ Answer in English with cited sources.
```

Supported embedding: `nomic-embed-text v1.5` (multilingual, 768 dimensions)

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | LLM backend: `ollama`, `openai`, `anthropic` |
| `OLLAMA_MODEL` | `mistral` | Model name for Ollama |
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant server port |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `JWT_SECRET_KEY` | — | **Required.** JWT signing secret |
| `JWT_EXPIRE_HOURS` | `24` | Token expiration in hours |
| `LANGCHAIN_API_KEY` | — | LangSmith tracing (optional but recommended) |
| `LANGCHAIN_PROJECT` | `rag-univ` | LangSmith project name |
| `CHUNK_SIZE` | `512` | Max tokens per chunk |
| `CHUNK_OVERLAP` | `64` | Token overlap between chunks |
| `RETRIEVAL_TOP_K` | `20` | Candidates before reranking |
| `RERANK_TOP_N` | `5` | Final chunks after reranking |
| `MEMORY_WINDOW_K` | `10` | Conversation turns to remember |
| `RATE_LIMIT_PER_MIN` | `20` | API rate limit per user |
| `ALLOWED_ORIGINS` | `*` | CORS origins (comma-separated) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## 🛠️ Development

### Run tests

```bash
pytest tests/ -v --cov=. --cov-report=html
```

### Lint and format

```bash
ruff check . --fix
black .
mypy . --strict
```

### Rebuild a single service

```bash
docker compose up --build api
```

### Access Qdrant dashboard

```
http://localhost:6333/dashboard
```

### View LangSmith traces

```
https://smith.langchain.com → your project → rag-univ
```

---

## 🗺️ Roadmap

- [x] MVP — Core RAG pipeline + API + RAGAS benchmarks
- [ ] **v1.1** — Streamlit / Gradio chat UI
- [ ] **v1.2** — SSO integration (SAML 2.0 / OAuth2) with university LDAP
- [ ] **v1.3** — LoRA fine-tuning adapter for domain-specific tone
- [ ] **v1.4** — Whisper ASR for video/audio lecture transcription
- [ ] **v2.0** — Multi-node Qdrant cluster + Kubernetes Helm chart
- [ ] **v2.1** — Grafana observability dashboard
- [ ] **v2.2** — Student feedback loop → automatic quality improvement

---

## 🤝 Contributing

```bash
# 1. Fork the repo
# 2. Create your branch
git checkout -b feature/your-feature-name

# 3. Commit with conventional commits
git commit -m "feat: add whisper transcription support"

# 4. Push and open a PR
git push origin feature/your-feature-name
```

Please read [CONTRIBUTING.md](CONTRIBUTING.md) and ensure all benchmarks pass before submitting.

---

## 📄 License

Apache 2.0 — free for academic and commercial use.
See [LICENSE](LICENSE) for full terms.

---

## 🙏 Acknowledgments

Built with:
[LangChain](https://langchain.com) ·
[Qdrant](https://qdrant.tech) ·
[Mistral AI](https://mistral.ai) ·
[RAGAS](https://ragas.io) ·
[FastAPI](https://fastapi.tiangolo.com) ·
[Ollama](https://ollama.ai) ·
[nomic-ai](https://nomic.ai)

---

<div align="center">

**Built for universities. Owned by universities.**

*Questions? Open an issue. Ideas? Open a PR.*

⭐ **Star this repo if it helped you** ⭐

</div>
