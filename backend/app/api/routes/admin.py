"""Administrator screens: user management, audit trail, and internal diagnostics."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.errors import DuplicateKeyError

from app.api.deps import require_admin
from app.core.container import get_container
from app.core.security import hash_password
from app.schemas.auth import AdminCreateUser, AdminUpdateUser, UserOut
from app.services.access_service import Principal
from app.services.generation_service import ollama_status

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(p: Principal = Depends(require_admin)) -> list[dict]:
    return get_container().users.list_public()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(req: AdminCreateUser, p: Principal = Depends(require_admin)) -> dict:
    c = get_container()
    email = req.email.strip().lower()
    try:
        user = c.users.create(email, req.name.strip(), hash_password(req.password), req.role)
    except DuplicateKeyError as exc:
        raise HTTPException(409, "An account with this email already exists.") from exc
    c.audit.record("admin.user_created", p, "user", user["user_id"], {"role": req.role})
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: str, req: AdminUpdateUser, p: Principal = Depends(require_admin)) -> dict:
    c = get_container()
    target = c.users.get_public(user_id)
    if target is None:
        raise HTTPException(404, "User not found.")
    changes = req.model_dump(exclude_none=True)
    loses_admin = (changes.get("role") not in (None, "admin")) or changes.get("active") is False
    if loses_admin and target["role"] == "admin" and target["active"] and _admin_count(c) <= 1:
        raise HTTPException(422, "At least one active administrator must remain.")
    if loses_admin and user_id == p.user_id:
        raise HTTPException(422, "You cannot remove your own administrator access.")
    user = c.users.update(user_id, **changes) if changes else target
    c.audit.record("admin.user_updated", p, "user", user_id, changes)
    return user


def _admin_count(c) -> int:
    return sum(1 for u in c.users.list_public() if u["role"] == "admin" and u["active"])


@router.get("/audit")
def audit_log(
    action: str | None = Query(None, max_length=60),
    actor_id: str | None = Query(None, max_length=64),
    limit: int = Query(200, ge=1, le=1000),
    p: Principal = Depends(require_admin),
) -> list[dict]:
    return get_container().audit.list(action=action, actor_id=actor_id, limit=limit)


@router.get("/system")
def system(p: Principal = Depends(require_admin)) -> dict:
    c = get_container()
    docs = c.store.list_for(p)
    return {
        "documents": len(docs),
        "documents_processed": sum(1 for d in docs if d.status.value == "processed"),
        "documents_failed": sum(1 for d in docs if d.status.value == "failed"),
        "chunks_indexed": c.vectors.count(),
        "embedding_model": c.embedder.model_name,
        "embedding_model_loaded": c.embedder.is_loaded(),
        "llm": ollama_status(),
        "retrieval": c.retrieval.config(),
    }
