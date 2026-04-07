import os
import hashlib
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
import aiohttp
import docx
from PIL import Image
import torch
import open_clip
from datetime import datetime
from langchain_core.documents import Document
from sqlalchemy import create_engine, text

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from data_pipeline.semantic_chunker import SemanticChunker

class DataIngestionPipeline:
    def __init__(self, qdrant_manager=None):
        self.qdrant_manager = qdrant_manager

        self.text_splitter = SemanticChunker(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            breakpoint_percentile=70.0,   # cut at the 30% lowest-similarity transitions
            max_chunk_chars=1500,          # hard ceiling per chunk
            min_chunk_chars=200,           # discard/merge chunks smaller than this
            fallback_chunk_size=512,       # fallback splitter params (unchanged)
            fallback_overlap=64,
        )
        
        # Load CLIP for images
        self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')
        self.tokenizer = open_clip.get_tokenizer('ViT-B-32')
        
    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def extract_webpage(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                return soup.get_text(separator="\n", strip=True)

    def extract_pdf(self, file_path: str) -> str:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    def extract_docx(self, file_path: str) -> str:
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])

    def extract_image(self, file_path: str) -> Dict[str, Any]:
        image = self.clip_preprocess(Image.open(file_path)).unsqueeze(0)
        with torch.no_grad():
            image_features = self.clip_model.encode_image(image)
        return {"image_vector": image_features.tolist()[0]}

    def clean_text(self, text: str) -> str:
        return "\n".join([line.strip() for line in text.split("\n") if line.strip()])

    def log_error(self, doc_id: str, step: str, message: str):
        import json
        error_log = {
            "doc_id": doc_id,
            "etape": step,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        with open("ingestion_errors.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(error_log) + "\n")

    def process_document(self, content: str, metadata: Dict[str, Any]) -> List[Document]:
        try:
            content = self.clean_text(content)
            content_hash = self._hash_content(content)

            # Skip documents already in the vector store (delta-sync)
            if self.qdrant_manager and self.qdrant_manager.hash_exists(content_hash):
                return []

            metadata['content_hash'] = content_hash
            metadata['timestamp'] = datetime.utcnow().isoformat()

            # SemanticChunker.create_documents already:
            #   - splits on meaning boundaries
            #   - adds chunk_index, chunk_total, chunk_preview to metadata
            #   - filters chunks smaller than min_chunk_chars internally
            docs = self.text_splitter.create_documents(content, metadata=metadata)

            return docs
        except Exception as e:
            self.log_error(metadata.get('source', 'unknown_source'), "process_document", str(e))
            return []
        
    def ingest_file(self, file_path: str, metadata: Dict[str, Any]) -> List[Document]:
        try:
            ext = file_path.split('.')[-1].lower()
            if ext == 'pdf':
                content = self.extract_pdf(file_path)
                return self.process_document(content, metadata)
            elif ext == 'docx':
                content = self.extract_docx(file_path)
                return self.process_document(content, metadata)
            elif ext in ['jpg', 'jpeg', 'png', 'webp']:
                image_info = self.extract_image(file_path)
                doc = Document(page_content=f"[IMAGE:{file_path}]", metadata={**metadata, **image_info})
                return [doc]
            return []
        except Exception as e:
            self.log_error(file_path, "ingest_file", str(e))
            return []

    async def ingest_url(self, url: str, metadata: Dict[str, Any]) -> List[Document]:
        content = await self.extract_webpage(url)
        return self.process_document(content, metadata)
        
    def ingest_db(self, db_uri: str, query: str, metadata: Dict[str, Any]) -> List[Document]:
        engine = create_engine(db_uri)
        with engine.connect() as conn:
            result = conn.execute(text(query)).fetchall()
            content = "\n".join([str(row) for row in result])
        return self.process_document(content, metadata)
