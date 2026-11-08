"""BM25 lexical retrieval over chunks (rank-bm25), rebuilt when the chunk store changes."""
from __future__ import annotations

import re

from app.schemas.models import Chunk

_WORD = re.compile(r"[a-z0-9]+")
_COMPOUND = re.compile(r"[a-z0-9]+(?:[-/.][a-z0-9]+)+")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens plus whole compound identifiers.

    "POL-SEC-007" -> ["pol", "sec", "007", "pol-sec-007"], so identifier queries match exactly
    while partial matches still contribute.
    """
    t = text.lower()
    return _WORD.findall(t) + _COMPOUND.findall(t)


class BM25Service:
    def __init__(self) -> None:
        self._bm25 = None
        self._chunks: list[Chunk] = []

    def build(self, chunks: list[Chunk]) -> None:
        from rank_bm25 import BM25Okapi

        self._chunks = chunks
        self._bm25 = BM25Okapi([tokenize(c.text) for c in chunks]) if chunks else None

    def search(self, query: str, n: int, document_ids: set[str] | None = None) -> dict[str, float]:
        """Return {chunk_id: raw BM25 score} for the top-n chunks with a positive score.

        When document_ids is given, only chunks from those documents are considered.
        """
        if not self._bm25:
            return {}
        scores = self._bm25.get_scores(tokenize(query))
        out: dict[str, float] = {}
        for i in sorted(range(len(scores)), key=lambda i: scores[i], reverse=True):
            if scores[i] <= 0 or len(out) >= n:
                break
            chunk = self._chunks[i]
            if document_ids is not None and chunk.document_id not in document_ids:
                continue
            out[chunk.chunk_id] = float(scores[i])
        return out
