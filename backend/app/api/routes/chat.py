from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.container import get_container
from app.schemas.models import ChatRequest, ChatResponse
from app.services.embedding_service import EmbeddingUnavailable
from app.services.generation_service import LLMUnavailable, ollama_status

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/query", response_model=ChatResponse)
def query(req: ChatRequest) -> ChatResponse:
    c = get_container()
    if not c.store.all_chunks():
        raise HTTPException(409, "No processed documents yet. Upload a document and wait for it to finish processing.")
    try:
        search = c.retrieval.search(req.query, req.method, req.top_k, req.fixed_alpha, req.adaptive_config)
        return c.generation.answer(req.query, search)
    except EmbeddingUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/status")
def status() -> dict:
    """Dashboard data: document counts and local model status."""
    c = get_container()
    docs = c.store.list()
    return {
        "project": "Secure Adaptive Hybrid RAG",
        "documents_uploaded": len(docs),
        "documents_processed": sum(1 for d in docs if d.status.value == "processed"),
        "documents_failed": sum(1 for d in docs if d.status.value == "failed"),
        "chunks_indexed": c.vectors.count(),
        "embedding_model": c.embedder.model_name,
        "embedding_model_loaded": c.embedder.is_loaded(),
        "llm": ollama_status(),
    }
