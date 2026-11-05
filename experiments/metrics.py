"""Retrieval metrics with binary relevance. `retrieved` is a ranked list of chunk IDs."""
from __future__ import annotations

import math
from typing import Sequence


def precision_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    top = list(retrieved)[:k]
    if k <= 0:
        return 0.0
    return sum(1 for c in top if c in relevant) / k


def recall_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return sum(1 for c in list(retrieved)[:k] if c in relevant) / len(relevant)


def reciprocal_rank(retrieved: Sequence[str], relevant: set[str]) -> float:
    for i, c in enumerate(retrieved, start=1):
        if c in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    dcg = sum(1.0 / math.log2(i + 1) for i, c in enumerate(list(retrieved)[:k], start=1) if c in relevant)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0
