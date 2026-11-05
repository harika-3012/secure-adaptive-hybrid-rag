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

    def search(self, query: str, n: int) -> dict[str, float]:
        """Return {chunk_id: raw BM25 score} for the top-n chunks with a positive score."""
        if not self._bm25:
            return {}
        scores = self._bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]
        return {self._chunks[i].chunk_id: float(scores[i]) for i in order if scores[i] > 0}
