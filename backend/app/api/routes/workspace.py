"""Semantic search across the signed-in user's documents, the sharing directory, and dashboard status."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_principal
from app.core.container import get_container
from app.services.access_service import Principal
from app.services.generation_service import ollama_status

router = APIRouter(tags=["workspace"])


@router.get("/api/search")
def semantic_search(
    q: str = Query(..., min_length=2, max_length=500),
    limit: int = Query(8, ge=1, le=20),
    p: Principal = Depends(get_principal),
) -> dict:
    groups = get_container().assistant.search(p, q.strip(), limit)
    return {"query": q.strip(), "results": groups}


@router.get("/api/users/directory")
def directory(p: Principal = Depends(get_principal)) -> list[dict]:
    return get_container().users.list_active_directory()


@router.get("/api/status")
def status(p: Principal = Depends(get_principal)) -> dict:
    c = get_container()
    visible = c.store.list_for(p)
    return {
        "documents_visible": len(visible),
        "documents_processed": sum(1 for d in visible if d.status.value == "processed"),
        "conversations": len(c.conversations.list_for_owner(p.user_id)),
        "assistant_ready": ollama_status()["reachable"],
    }
