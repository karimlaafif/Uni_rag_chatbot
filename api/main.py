import os
import uuid
import aiofiles
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from langsmith import traceable

from config import settings
from api.schemas import ChatRequest, ChatResponse, KnowledgeStatusResponse, BenchmarkResponse
from rag.chain import RAGChatbot
from data_pipeline.vectorstore import QdrantManager
from benchmarks.ragas_eval import run_benchmark_task

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title=settings.PROJECT_NAME)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chatbot = RAGChatbot()
qdrant_manager = QdrantManager()

BENCHMARK_RESULTS = {}

@app.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
@traceable(name="chat_endpoint")
async def chat(request: Request, body: ChatRequest):
    try:
        res = await chatbot.achat(
            query=body.query, 
            session_id=body.session_id, 
            user_role=body.user_role, 
            image_base64=body.image_base64
        )
        return ChatResponse(
            answer=res["answer"], 
            sources=res.get("sources", []),
            session_id=body.session_id,
            model=settings.LLM_PROVIDER,
            latency_ms=res.get("latency_ms", 0),
            tokens_used=res.get("tokens_used", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/update")
@limiter.limit("5/minute")
async def update_knowledge(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    department: str = Form(...),
    access_level: str = Form(...)
):
    os.makedirs("/tmp/uploads", exist_ok=True)
    temp_path = f"/tmp/uploads/{file.filename}"
    async with aiofiles.open(temp_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
        
    metadata = {
        "department": department,
        "access_level": access_level,
        "doc_version": "1.0",
        "source": file.filename
    }
    
    def process():
        qdrant_manager.knowledge_update(temp_path, metadata)
        
    background_tasks.add_task(process)
    return {"message": "Update queued successfully"}

@app.get("/knowledge/status", response_model=KnowledgeStatusResponse)
async def knowledge_status():
    return KnowledgeStatusResponse(status="idle", last_update="2023-10-01T12:00:00Z")

@app.post("/benchmark/run", response_model=BenchmarkResponse)
async def run_benchmark(background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    BENCHMARK_RESULTS[job_id] = "running"
    
    background_tasks.add_task(run_benchmark_task, job_id, BENCHMARK_RESULTS)
    return BenchmarkResponse(job_id=job_id, status="running")

@app.get("/benchmark/results/{job_id}")
async def get_benchmark_results(job_id: str):
    if job_id not in BENCHMARK_RESULTS:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "result": BENCHMARK_RESULTS[job_id]}
