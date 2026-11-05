from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.core.config import get_settings
from app.core.container import get_container
from app.schemas.models import DocStatus, DocumentInfo, DocumentStatus
from app.services.document_service import now_iso

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _safe_name(name: str) -> str:
    base = Path(name).name
    return re.sub(r"[^A-Za-z0-9._\- ]", "_", base)[:150] or "document"


@router.post("/upload", response_model=DocumentInfo, status_code=202)
async def upload(background: BackgroundTasks, file: UploadFile = File(...)) -> DocumentInfo:
    s = get_settings()
    c = get_container()
    filename = _safe_name(file.filename or "document")
    ext = Path(filename).suffix.lower()
    if ext not in s.allowed_extensions:
        raise HTTPException(415, f"Unsupported file type '{ext}'. Allowed: {', '.join(s.allowed_extensions)}")

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
        document_id=doc_id, filename=filename, size_bytes=size, status=DocStatus.queued, uploaded_at=now_iso()
    )
    c.store.add(info)
    background.add_task(c.ingestion.process, doc_id)
    return info


@router.get("", response_model=list[DocumentInfo])
def list_documents() -> list[DocumentInfo]:
    return get_container().store.list()


@router.get("/{document_id}", response_model=DocumentInfo)
def get_document(document_id: str) -> DocumentInfo:
    info = get_container().store.get(document_id)
    if info is None:
        raise HTTPException(404, "Document not found.")
    return info


@router.get("/{document_id}/status", response_model=DocumentStatus)
def get_status(document_id: str) -> DocumentStatus:
    info = get_container().store.get(document_id)
    if info is None:
        raise HTTPException(404, "Document not found.")
    return DocumentStatus(document_id=document_id, status=info.status, chunks=info.chunks, error=info.error)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str) -> None:
    c = get_container()
    if c.store.get(document_id) is None:
        raise HTTPException(404, "Document not found.")
    path = c.store.stored_file(document_id)
    c.vectors.delete_document(document_id)
    c.store.remove(document_id)
    if path:
        path.unlink(missing_ok=True)
