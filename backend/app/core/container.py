"""Lazy singletons wiring services together. Permission checks live in the routes and access_service."""
from __future__ import annotations

import threading

from pymongo.database import Database

from app.core.config import get_settings
from app.core.database import ensure_indexes, get_database
from app.services.assistant_service import AssistantService
from app.services.audit_service import AuditLog
from app.services.bm25_service import BM25Service
from app.services.conversation_service import ConversationRepository
from app.services.document_service import DocumentStore
from app.services.embedding_service import EmbeddingService
from app.services.generation_service import GenerationService
from app.services.hybrid_retrieval_service import RetrievalService
from app.services.ingestion_service import IngestionService
from app.services.session_service import SessionRevocations
from app.services.space_service import SpaceRepository
from app.services.user_service import UserRepository
from app.services.vector_service import VectorService


class Container:
    def __init__(self, db: Database | None = None) -> None:
        self.db = db if db is not None else get_database()
        ensure_indexes(self.db)
        self.store = DocumentStore(self.db, get_settings())
        self.store.recover_interrupted()
        self.users = UserRepository(self.db)
        self.sessions = SessionRevocations(self.db)
        self.audit = AuditLog(self.db)
        self.spaces = SpaceRepository(self.db)
        self.conversations = ConversationRepository(self.db)
        self.embedder = EmbeddingService()
        self.vectors = VectorService(self.embedder)
        self.bm25 = BM25Service()
        self.retrieval = RetrievalService(self.store, self.bm25, self.vectors)
        self.ingestion = IngestionService(self.store, self.vectors, self.bm25)
        self.generation = GenerationService(self.vectors)
        self.assistant = AssistantService(
            self.store, self.spaces, self.conversations, self.retrieval, self.generation, self.audit
        )


_container: Container | None = None
_lock = threading.Lock()


def get_container() -> Container:
    global _container
    with _lock:
        if _container is None:
            _container = Container()
        return _container
