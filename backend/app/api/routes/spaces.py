"""Knowledge Spaces: curated groups of documents with their own members."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_principal, require_editor
from app.core.container import get_container
from app.schemas.models import DocumentOut
from app.schemas.workspace import SpaceCreate, SpaceDocumentAdd, SpaceMembersSet, SpaceUpdate
from app.services.access_service import Principal, can_manage_space, can_read_document, can_read_space

router = APIRouter(prefix="/api/spaces", tags=["spaces"])


def _load_space(space_id: str, p: Principal) -> dict:
    space = get_container().spaces.get(space_id)
    if space is None or not can_read_space(p, space):
        raise HTTPException(404, "Space not found.")
    return space


def _load_managed_space(space_id: str, p: Principal) -> dict:
    space = _load_space(space_id, p)
    if not can_manage_space(p, space):
        raise HTTPException(403, "Only the space owner or an administrator can change this space.")
    return space


def _summary(space: dict, p: Principal) -> dict:
    return {**space, "can_manage": can_manage_space(p, space), "document_count": len(space["document_ids"])}


@router.get("")
def list_spaces(p: Principal = Depends(get_principal)) -> list[dict]:
    c = get_container()
    query = {} if p.is_admin else {"$or": [{"owner_id": p.user_id}, {"member_ids": p.user_id}]}
    return [_summary(s, p) for s in c.spaces.list_for_filter(query)]


@router.post("", status_code=201)
def create_space(req: SpaceCreate, p: Principal = Depends(require_editor)) -> dict:
    space = get_container().spaces.create(p.user_id, req.name.strip(), req.description.strip())
    get_container().audit.record("space.create", p, "space", space["space_id"], {"name": space["name"]})
    return _summary(space, p)


@router.get("/{space_id}")
def get_space(space_id: str, p: Principal = Depends(get_principal)) -> dict:
    c = get_container()
    space = _load_space(space_id, p)
    readable = {d.document_id: d for d in c.store.list_for(p)}
    documents = [
        DocumentOut(**readable[d].model_dump(), can_manage=False).model_dump()
        for d in space["document_ids"]
        if d in readable
    ]
    return {**_summary(space, p), "documents": documents}


@router.patch("/{space_id}")
def update_space(space_id: str, req: SpaceUpdate, p: Principal = Depends(get_principal)) -> dict:
    c = get_container()
    _load_managed_space(space_id, p)
    fields = {k: (v.strip() if isinstance(v, str) else v) for k, v in req.model_dump(exclude_none=True).items()}
    space = c.spaces.update(space_id, **fields)
    return _summary(space, p)


@router.delete("/{space_id}", status_code=204)
def delete_space(space_id: str, p: Principal = Depends(get_principal)) -> None:
    c = get_container()
    _load_managed_space(space_id, p)
    c.spaces.delete(space_id)
    c.audit.record("space.delete", p, "space", space_id)


@router.post("/{space_id}/documents", status_code=201)
def add_document(space_id: str, req: SpaceDocumentAdd, p: Principal = Depends(get_principal)) -> dict:
    c = get_container()
    _load_managed_space(space_id, p)
    info = c.store.get(req.document_id)
    if info is None or not can_read_document(p, info.model_dump()):
        raise HTTPException(404, "Document not found.")
    c.spaces.add_document(space_id, req.document_id)
    c.audit.record("space.document_added", p, "space", space_id, {"document_id": req.document_id})
    return get_space(space_id, p)


@router.delete("/{space_id}/documents/{document_id}")
def remove_document(space_id: str, document_id: str, p: Principal = Depends(get_principal)) -> dict:
    c = get_container()
    _load_managed_space(space_id, p)
    c.spaces.remove_document(space_id, document_id)
    c.audit.record("space.document_removed", p, "space", space_id, {"document_id": document_id})
    return get_space(space_id, p)


@router.put("/{space_id}/members")
def set_members(space_id: str, req: SpaceMembersSet, p: Principal = Depends(get_principal)) -> dict:
    c = get_container()
    _load_managed_space(space_id, p)
    members = sorted({m for m in req.member_ids if m})
    if c.users.active_ids(members) != set(members):
        raise HTTPException(422, "One or more selected people are not active accounts.")
    c.spaces.set_members(space_id, members)
    c.audit.record("space.members_changed", p, "space", space_id, {"members": len(members)})
    return _summary(c.spaces.get(space_id), p)
