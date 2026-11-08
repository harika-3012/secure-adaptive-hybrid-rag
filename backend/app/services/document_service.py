"""Document registry and chunk store (MongoDB metadata + chunks; original files on the local disk)."""
from __future__ import annotations

import threading
from pathlib import Path

from pymongo import ReturnDocument
from pymongo.database import Database

from app.core.config import Settings, get_settings
from app.schemas.models import Chunk, DocStatus, DocumentInfo
from app.services.access_service import Principal, readable_document_filter


def _info(doc: dict) -> DocumentInfo:
    return DocumentInfo(**{k: v for k, v in doc.items() if k != "_id"})


class DocumentStore:
    def __init__(self, db: Database, settings: Settings | None = None) -> None:
        self.s = settings or get_settings()
        self._docs = db.documents
        self._chunks = db.chunks
        self._lock = threading.RLock()
        self._version = 0  # bumped on every change; retrievers use it to rebuild BM25

    # ---- registry ----------------------------------------------------
    def add(self, info: DocumentInfo) -> None:
        with self._lock:
            self._docs.insert_one(info.model_dump(mode="json"))
            self._version += 1

    def update(self, document_id: str, **fields) -> DocumentInfo:
        with self._lock:
            doc = self._docs.find_one_and_update(
                {"document_id": document_id}, {"$set": fields}, return_document=ReturnDocument.AFTER
            )
            self._version += 1
            return _info(doc)

    def get(self, document_id: str) -> DocumentInfo | None:
        doc = self._docs.find_one({"document_id": document_id})
        return _info(doc) if doc else None

    def list_for(self, principal: Principal) -> list[DocumentInfo]:
        docs = self._docs.find(readable_document_filter(principal)).sort("uploaded_at", -1)
        return [_info(d) for d in docs]

    def readable_ids(self, principal: Principal) -> set[str]:
        docs = self._docs.find(readable_document_filter(principal), {"document_id": 1, "_id": 0})
        return {d["document_id"] for d in docs}

    def remove(self, document_id: str) -> None:
        with self._lock:
            self._docs.delete_one({"document_id": document_id})
            self._chunks.delete_many({"document_id": document_id})
            self._version += 1

    def recover_interrupted(self) -> None:
        """Documents still queued or processing after a restart are surfaced as failed, not left hanging."""
        with self._lock:
            self._docs.update_many(
                {"status": {"$in": [DocStatus.queued.value, DocStatus.processing.value]}},
                {
                    "$set": {
                        "status": DocStatus.failed.value,
                        "error": "Processing interrupted by application restart; delete and re-upload.",
                    }
                },
            )
            self._version += 1

    # ---- chunks ------------------------------------------------------
    def set_chunks(self, document_id: str, chunks: list[Chunk]) -> None:
        with self._lock:
            self._chunks.delete_many({"document_id": document_id})
            if chunks:
                self._chunks.insert_many([c.model_dump(mode="json") for c in chunks])
            self._version += 1

    def chunks_for_document(self, document_id: str) -> list[Chunk]:
        rows = self._chunks.find({"document_id": document_id}, {"_id": 0}).sort("chunk_id", 1)
        return [Chunk(**r) for r in rows]

    def all_chunks(self) -> list[Chunk]:
        """Chunks of processed documents only, in stable order."""
        processed = [
            d["document_id"]
            for d in self._docs.find({"status": DocStatus.processed.value}, {"document_id": 1, "_id": 0})
        ]
        if not processed:
            return []
        rows = self._chunks.find({"document_id": {"$in": processed}}, {"_id": 0}).sort("chunk_id", 1)
        return [Chunk(**r) for r in rows]

    @property
    def version(self) -> int:
        return self._version

    def stored_file(self, document_id: str) -> Path | None:
        for p in self.s.documents_dir.glob(f"{document_id}__*"):
            return p
        return None
