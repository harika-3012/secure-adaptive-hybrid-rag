from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.container import get_container
from app.schemas.models import SearchRequest, SearchResponse
from app.services.embedding_service import EmbeddingUnavailable

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    c = get_container()
    if not c.store.all_chunks():
        raise HTTPException(409, "No processed documents yet. Upload a document and wait for it to finish processing.")
    try:
        return c.retrieval.search(req.query, req.method, req.top_k, req.fixed_alpha, req.adaptive_config)
    except EmbeddingUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/config")
def config() -> dict:
    return get_container().retrieval.config()
