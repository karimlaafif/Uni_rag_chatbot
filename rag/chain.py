import os
import torch
import base64
from PIL import Image
import io
from typing import List, Dict, Any, Tuple
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.documents import Document

from config import settings
from data_pipeline.vectorstore import QdrantManager
# Singleton CLIP partagé avec ingestion.py — un seul chargement par processus
from shared_models import get_clip_model

def get_llm():
    if settings.LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(temperature=0, model="gpt-4o-mini")
    elif settings.LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(temperature=0, model="claude-3-haiku-20240307")
    else:
        # Default to Ollama
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.1)

class RAGChatbot:
    def __init__(self):
        self.qdrant_manager = QdrantManager()
        self.llm = get_llm()
        
        system_template = """Assistant académique de Ibn Zohr Université. Je réponds uniquement aux questions liées aux études, services universitaires et informations académiques.
Réponds toujours dans la langue de l'utilisateur. Langues supportées : Français, Arabe, Anglais.
Pour chaque affirmation factuelle, cite la source entre crochets [source_n]. Inclus le titre et l'URL si disponibles.
Si la question est hors périmètre, réponds : 'Je suis désolé, cette question dépasse le périmètre de mes connaissances universitaires. Contactez [service compétent].'
Ne divulgue jamais de données personnelles d'autres utilisateurs. Filtre les réponses selon le niveau d'accès de l'utilisateur courant.

Niveau d'accès : {user_role}

Context documents:
{context}

Historical Conversation:
{chat_history}"""
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("human", "{question}")
        ])
        
        # Charge CLIP ou récupère l'instance déjà en mémoire (singleton partagé)
        self.clip_model, self.clip_preprocess, self.tokenizer = get_clip_model()

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        return RedisChatMessageHistory(session_id, url=settings.REDIS_URL)

    def retrieve(self, input_dict: Dict[str, Any]) -> str:
        query       = input_dict["question"]
        image_base64 = input_dict.get("image_base64")
        user_role   = input_dict.get("user_role", "public")

        # Filtre d'accès partagé entre recherche texte et image
        access_filter = self.qdrant_manager._build_access_filter(user_role)

        docs = []
        if image_base64:
            # Multi-modal retrieval using CLIP
            try:
                image_data = base64.b64decode(image_base64)
                image = Image.open(io.BytesIO(image_data))
                img_tensor = self.clip_preprocess(image).unsqueeze(0)
                with torch.no_grad():
                    img_features = self.clip_model.encode_image(img_tensor).tolist()[0]

                results = self.qdrant_manager.client.search(
                    collection_name=self.qdrant_manager.collection_name,
                    query_vector=("image", img_features),
                    query_filter=access_filter,   # filtre d'accès sur les images aussi
                    limit=5,
                )
                docs = [Document(page_content=r.payload.get("page_content", ""), metadata=r.payload) for r in results]
            except Exception as e:
                print(f"Error processing image retrieval: {e}")
                docs = self.qdrant_manager.hybrid_search(query, user_role=user_role)
        else:
            docs = self.qdrant_manager.hybrid_search(query, user_role=user_role)
            
            
        context_str = ""
        for i, doc in enumerate(docs):
            context_str += f"[source_{i+1}] {doc.page_content}\n"
            
        input_dict["raw_docs"] = docs
        return context_str

    async def achat(self, query: str, session_id: str, user_role: str, image_base64: str = None) -> Dict[str, Any]:
        history = self.get_session_history(session_id)
        chat_history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in history.messages[-10:]])
        
        input_dict = {
            "question": query,
            "image_base64": image_base64,
            "chat_history": chat_history_str,
            "user_role": user_role
        }
        
        context_str = self.retrieve(input_dict)
        input_dict["context"] = context_str
        
        chain = self.prompt | self.llm | StrOutputParser()
        
        import time
        start_time = time.time()
        response = await chain.ainvoke(input_dict)
        latency = int((time.time() - start_time) * 1000)
        
        history.add_user_message(query)
        history.add_ai_message(response)
        
        formatted_sources = []
        for idx, doc in enumerate(input_dict.get("raw_docs", [])):
            formatted_sources.append({
                "title":        doc.metadata.get("source", f"Source {idx+1}"),
                "url":          doc.metadata.get("url", ""),
                "rerank_score": doc.metadata.get("rerank_score", 0.0),
                "access_level": doc.metadata.get("access_level", "public"),
                # Texte brut du chunk — utilisé par RAGAS pour calculer les métriques
                # (Faithfulness, Context Precision/Recall) qui ont besoin du contenu réel.
                "page_content": doc.page_content,
            })
        
        return {
            "answer": response, 
            "sources": formatted_sources,
            "latency_ms": latency,
            "tokens_used": len(response.split()) # roughly estimating response tokens
        }
