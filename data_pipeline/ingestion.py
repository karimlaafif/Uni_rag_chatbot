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

class DataIngestionPipeline:
    def __init__(self, qdrant_manager=None):
        self.qdrant_manager = qdrant_manager
        
        # Semantic Chunker approximation since `SemanticChunker` is experimental and might differ
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=64,
            length_function=len,
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
            
            if self.qdrant_manager and self.qdrant_manager.hash_exists(content_hash):
                return []
                
            metadata['content_hash'] = content_hash
            metadata['timestamp'] = datetime.utcnow().isoformat()
            
            docs = self.text_splitter.create_documents([content])
            filtered_docs = []
            for i, d in enumerate(docs):
                # Approximation of 80 tokens (around 60-80 words max, >300 chars usually)
                if len(d.page_content) >= 300: 
                    d.metadata.update(metadata)
                    d.metadata['chunk_index'] = i
                    filtered_docs.append(d)
                
            return filtered_docs
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
