from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import get_principal, require_editor
from app.core.config import get_settings
from app.core.container import get_container
from app.schemas.models import DocStatus, DocumentInfo, DocumentOut
from app.schemas.workspace import DocumentAccessUpdate
from app.services.access_service import (
    VISIBILITIES,
    VISIBILITY_PRIVATE,
    VISIBILITY_SHARED,
    Principal,
    can_manage_document,
    can_read_document,
)
from app.services.assistant_service import ScopeError
from app.utils.clock import now_iso

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _safe_name(name: str) -> str:
    base = Path(name).name
    return re.sub(r"[^A-Za-z0-9._\- ]", "_", base)[:150] or "document"


def _view(info: DocumentInfo, p: Principal) -> DocumentOut:
    return DocumentOut(**info.model_dump(), can_manage=can_manage_document(p, info.model_dump()))


def _load_readable(document_id: str, p: Principal) -> DocumentInfo:
    c = get_container()
    info = c.store.get(document_id)
    if info is None or not can_read_document(p, info.model_dump()):
        raise HTTPException(404, "Document not found.")
    return info


def _load_manageable(document_id: str, p: Principal) -> DocumentInfo:
    info = _load_readable(document_id, p)
    if not can_manage_document(p, info.model_dump()):
        raise HTTPException(403, "Only the owner or an administrator can change this document.")
    return info


def _validated_sharing(visibility: str, shared_with: list[str], p: Principal) -> list[str]:
    if visibility not in VISIBILITIES:
        raise HTTPException(422, "Unknown visibility setting.")
    if visibility != VISIBILITY_SHARED:
        return []
    ids = sorted({uid for uid in shared_with if uid and uid != p.user_id})
    if not ids:
        raise HTTPException(422, "Choose at least one person to share this document with.")
    if get_container().users.active_ids(ids) != set(ids):
        raise HTTPException(422, "One or more selected people are not active accounts.")
    return ids


@router.post("/upload", response_model=DocumentOut, status_code=202)
async def upload(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    visibility: str = Form(VISIBILITY_PRIVATE),
    shared_with: str = Form(""),
    p: Principal = Depends(require_editor),
) -> DocumentOut:
    s = get_settings()
    c = get_container()
    filename = _safe_name(file.filename or "document")
    ext = Path(filename).suffix.lower()
    if ext not in s.allowed_extensions:
        raise HTTPException(415, f"Unsupported file type '{ext}'. Allowed: {', '.join(s.allowed_extensions)}")
    recipients = _validated_sharing(visibility, [x.strip() for x in shared_with.split(",")], p)

    doc_id = uuid.uuid4().hex[:12]
    dest = s.documents_dir / f"{doc_id}__{filename}"
    limit = s.max_upload_mb * 1024 * 1024
    size = 0
    try:
        with dest.open("wb") as fh:
            while block := await file.read(1024 * 1024):
                size += len(block)
                if size > limit:
                    raise HTTPException(413, f"File exceeds the {s.max_upload_mb} MB limit.")
                fh.write(block)
        if size == 0:
            raise HTTPException(400, "Uploaded file is empty.")
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise

    info = DocumentInfo(
        document_id=doc_id,
        filename=filename,
        size_bytes=size,
        status=DocStatus.queued,
        uploaded_at=now_iso(),
        owner_id=p.user_id,
        owner_name=p.name,
        visibility=visibility,
        shared_with=recipients,
    )
    c.store.add(info)
    c.audit.record("document.upload", p, "document", doc_id, {"filename": filename, "visibility": visibility})
    background.add_task(c.ingestion.process, doc_id)
    return _view(info, p)


@router.get("", response_model=list[DocumentOut])
def list_documents(p: Principal = Depends(get_principal)) -> list[DocumentOut]:
    return [_view(d, p) for d in get_container().store.list_for(p)]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, p: Principal = Depends(get_principal)) -> DocumentOut:
    return _view(_load_readable(document_id, p), p)


@router.get("/{document_id}/status")
def get_status(document_id: str, p: Principal = Depends(get_principal)) -> dict:
    info = _load_readable(document_id, p)
    return {"document_id": document_id, "status": info.status, "chunks": info.chunks, "error": info.error}


@router.put("/{document_id}/access", response_model=DocumentOut)
def update_access(document_id: str, req: DocumentAccessUpdate, p: Principal = Depends(get_principal)) -> DocumentOut:
    c = get_container()
    _load_manageable(document_id, p)
    recipients = _validated_sharing(req.visibility, req.shared_with, p)
    info = c.store.update(document_id, visibility=req.visibility, shared_with=recipients)
    c.audit.record("document.access_changed", p, "document", document_id, {"visibility": req.visibility, "recipients": len(recipients)})
    return _view(info, p)


@router.post("/{document_id}/summary")
def summarize(document_id: str, refresh: bool = False, p: Principal = Depends(get_principal)) -> dict:
    try:
        return get_container().assistant.summarize(p, document_id, refresh)
    except ScopeError as exc:
        raise HTTPException(409 if "processing" in str(exc) else 404, str(exc)) from exc


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, p: Principal = Depends(get_principal)) -> None:
    c = get_container()
    _load_manageable(document_id, p)
    path = c.store.stored_file(document_id)
    c.vectors.delete_document(document_id)
    c.spaces.remove_document_everywhere(document_id)
    c.store.remove(document_id)
    if path:
        path.unlink(missing_ok=True)
    c.audit.record("document.delete", p, "document", document_id)
