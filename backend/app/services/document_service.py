"""Persistent document registry and chunk store (JSON / JSONL on local disk)."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import Settings, get_settings
from app.schemas.models import Chunk, DocStatus, DocumentInfo


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DocumentStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.s = settings or get_settings()
        self._lock = threading.RLock()
        self._docs: dict[str, DocumentInfo] = {}
        self._chunks: dict[str, list[Chunk]] = {}  # document_id -> chunks
        self._version = 0  # bumped on every change; retrievers use it to rebuild BM25
        self._load()

    # ---- persistence -------------------------------------------------
    def _load(self) -> None:
        if self.s.registry_path.exists():
            for d in json.loads(self.s.registry_path.read_text(encoding="utf-8")):
                info = DocumentInfo(**d)
                if info.status in (DocStatus.queued, DocStatus.processing):
                    # Interrupted by a restart: surface honestly instead of hanging forever.
                    info.status = DocStatus.failed
                    info.error = "Processing interrupted by application restart; delete and re-upload."
                self._docs[info.document_id] = info
        if self.s.chunks_path.exists():
            for line in self.s.chunks_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    c = Chunk(**json.loads(line))
                    self._chunks.setdefault(c.document_id, []).append(c)

    def _save(self) -> None:
        with self._lock:
            tmp = self.s.registry_path.with_suffix(".tmp")
            tmp.write_text(json.dumps([d.model_dump(mode="json") for d in self._docs.values()], indent=2), encoding="utf-8")
            tmp.replace(self.s.registry_path)
            tmpc = self.s.chunks_path.with_suffix(".tmp")
            with tmpc.open("w", encoding="utf-8") as fh:
                for chunks in self._chunks.values():
                    for c in chunks:
                        fh.write(json.dumps(c.model_dump(mode="json")) + "\n")
            tmpc.replace(self.s.chunks_path)
            self._version += 1

    # ---- registry ----------------------------------------------------
    def add(self, info: DocumentInfo) -> None:
        with self._lock:
            self._docs[info.document_id] = info
            self._save()

    def update(self, document_id: str, **fields) -> DocumentInfo:
        with self._lock:
            info = self._docs[document_id].model_copy(update=fields)
            self._docs[document_id] = info
            self._save()
            return info

    def get(self, document_id: str) -> DocumentInfo | None:
        return self._docs.get(document_id)

    def list(self) -> list[DocumentInfo]:
        return sorted(self._docs.values(), key=lambda d: d.uploaded_at, reverse=True)

    def remove(self, document_id: str) -> None:
        with self._lock:
            self._docs.pop(document_id, None)
            self._chunks.pop(document_id, None)
            self._save()

    # ---- chunks ------------------------------------------------------
    def set_chunks(self, document_id: str, chunks: list[Chunk]) -> None:
        with self._lock:
            self._chunks[document_id] = chunks
            self._save()

    def all_chunks(self) -> list[Chunk]:
        """Chunks of processed documents only, in stable order."""
        with self._lock:
            out: list[Chunk] = []
            for did, chunks in self._chunks.items():
                d = self._docs.get(did)
                if d and d.status == DocStatus.processed:
                    out.extend(chunks)
            return out

    def chunk_by_id(self, chunk_id: str) -> Chunk | None:
        for chunks in self._chunks.values():
            for c in chunks:
                if c.chunk_id == chunk_id:
                    return c
        return None

    @property
    def version(self) -> int:
        return self._version

    def stored_file(self, document_id: str) -> Path | None:
        for p in self.s.documents_dir.glob(f"{document_id}__*"):
            return p
        return None
