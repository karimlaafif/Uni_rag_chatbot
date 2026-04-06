from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    query: str = Field(..., description="User's query text")
    image_base64: Optional[str] = Field(None, description="Base64 encoded image if present")
    session_id: str = Field(..., description="Unique session ID for memory")
    user_role: str = Field(..., description="User role: student, staff, or admin")

class SourceItem(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    score: Optional[float] = None

class ChatResponse(BaseModel):
    answer: str = Field(..., description="The assistant's response")
    sources: list[SourceItem] = Field(default_factory=list, description="List of document sources cited")
    session_id: str = Field(..., description="Unique session ID for memory")
    model: str = Field(..., description="Model name used")
    latency_ms: int = Field(..., description="Latency in ms")
    tokens_used: int = Field(..., description="Tokens used in response")

class KnowledgeStatusResponse(BaseModel):
    status: str = Field(..., description="Current status of the ingestion queue")
    last_update: str = Field(..., description="Timestamp of last successful update")

class BenchmarkResponse(BaseModel):
    job_id: str = Field(..., description="Unique ID for the benchmark run")
    status: str = Field(..., description="Status of the benchmark job")
    
class ErrorResponse(BaseModel):
    detail: str
