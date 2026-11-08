"""ChromaDB persistent dense index."""
from __future__ import annotations

import numpy as np

from app.core.config import Settings, get_settings
from app.schemas.models import Chunk
from app.services.embedding_service import EmbeddingService

COLLECTION = "chunks"


class VectorService:
    def __init__(self, embedder: EmbeddingService, settings: Settings | None = None) -> None:
        import chromadb

        self.embedder = embedder
        s = settings or get_settings()
        self.client = chromadb.PersistentClient(path=str(s.chroma_path))
        self.col = self.client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        embs = self.embedder.embed([c.text for c in chunks])
        self.col.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=embs.tolist(),
            documents=[c.text for c in chunks],
            metadatas=[{"document_id": c.document_id, "page": c.page} for c in chunks],
        )

    def delete_document(self, document_id: str) -> None:
        self.col.delete(where={"document_id": document_id})

    def count(self) -> int:
        return self.col.count()

    def search(self, query: str, n: int, document_ids: set[str] | None = None) -> dict[str, float]:
        """Return {chunk_id: cosine similarity} for the n nearest chunks.

        When document_ids is given, only chunks from those documents are considered.
        """
        total = self.col.count()
        if total == 0:
            return {}
        where = None
        if document_ids is not None:
            if not document_ids:
                return {}
            where = {"document_id": {"$in": sorted(document_ids)}}
        q = self.embedder.embed([query])
        res = self.col.query(query_embeddings=q.tolist(), n_results=min(n, total), where=where)
        return {cid: 1.0 - float(dist) for cid, dist in zip(res["ids"][0], res["distances"][0])}

    def cosine_for(self, query: str, chunk_ids: list[str]) -> dict[str, float]:
        """Raw cosine similarity between the query and specific stored chunks."""
        if not chunk_ids:
            return {}
        got = self.col.get(ids=chunk_ids, include=["embeddings"])
        q = self.embedder.embed([query])[0]
        return {cid: float(np.dot(q, np.asarray(e))) for cid, e in zip(got["ids"], got["embeddings"])}
