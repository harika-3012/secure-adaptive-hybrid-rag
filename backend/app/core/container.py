"""Lazy singletons wiring services together (single place to add auth/RBAC/audit later)."""
from __future__ import annotations

import threading

from app.services.bm25_service import BM25Service
from app.services.document_service import DocumentStore
from app.services.embedding_service import EmbeddingService
from app.services.generation_service import GenerationService
from app.services.hybrid_retrieval_service import RetrievalService
from app.services.ingestion_service import IngestionService
from app.services.vector_service import VectorService


class Container:
    def __init__(self) -> None:
        self.store = DocumentStore()
        self.embedder = EmbeddingService()
        self.vectors = VectorService(self.embedder)
        self.bm25 = BM25Service()
        self.retrieval = RetrievalService(self.store, self.bm25, self.vectors)
        self.ingestion = IngestionService(self.store, self.vectors, self.bm25)
        self.generation = GenerationService(self.vectors)


_container: Container | None = None
_lock = threading.Lock()


def get_container() -> Container:
    global _container
    with _lock:
        if _container is None:
            _container = Container()
        return _container


def reset_container() -> None:
    """Used by tests to rebuild services against a fresh data directory."""
    global _container
    with _lock:
        _container = None
