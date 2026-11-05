"""Score normalization and fusion helpers (pure Python/NumPy)."""
from __future__ import annotations

import numpy as np


def min_max(scores: dict[str, float]) -> dict[str, float]:
    """Min-max normalize to [0, 1] over the candidate set.

    If all scores are equal: 1.0 for all when positive, otherwise 0.0 (no signal).
    """
    if not scores:
        return {}
    vals = np.array(list(scores.values()), dtype=float)
    lo, hi = float(vals.min()), float(vals.max())
    if hi - lo < 1e-12:
        return {k: (1.0 if hi > 0 else 0.0) for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def fuse(bm25: dict[str, float], dense: dict[str, float], alpha: float) -> dict[str, float]:
    """alpha*BM25_norm + (1-alpha)*Dense_norm over the union of candidates.

    A chunk missing from one retriever's candidate list gets 0 from that retriever.
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0, 1]")
    nb, nd = min_max(bm25), min_max(dense)
    ids = set(nb) | set(nd)
    return {i: alpha * nb.get(i, 0.0) + (1 - alpha) * nd.get(i, 0.0) for i in ids}
