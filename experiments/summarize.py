"""Aggregate per-query evaluation rows into comparison tables (pure pandas, no backend imports)."""
from __future__ import annotations

import numpy as np
import pandas as pd

METHOD_ORDER = ["bm25", "dense", "fixed_hybrid", "adaptive_hybrid"]
METHOD_LABELS = {
    "bm25": "BM25",
    "dense": "Dense",
    "fixed_hybrid": "Fixed hybrid",
    "adaptive_hybrid": "Adaptive hybrid",
}
METRICS = ["precision", "recall", "mrr", "ndcg"]


def _p95(x: pd.Series) -> float:
    return float(np.percentile(x, 95))


def summarize(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Expected columns: query_type, method, precision, recall, mrr, ndcg, latency_ms, sufficient,
    adaptive_class. Retrieval metrics are averaged over answerable questions only; 'insufficient'
    questions have no relevant chunk and are scored by the evidence gate instead."""
    methods = [m for m in METHOD_ORDER if m in set(df["method"])]
    answerable = df[df["query_type"] != "insufficient"]
    insufficient = df[df["query_type"] == "insufficient"]

    overall = answerable.groupby("method")[METRICS].mean().reindex(methods)
    latency = (
        df.groupby("method")["latency_ms"]
        .agg(latency_mean_ms="mean", latency_median_ms="median", latency_p95_ms=_p95)
        .reindex(methods)
    )
    overall = overall.join(latency)

    by_type = answerable.groupby(["query_type", "method"])[METRICS].mean()
    by_type = by_type.reindex(
        pd.MultiIndex.from_product([sorted(answerable["query_type"].unique()), methods], names=["query_type", "method"])
    )

    gate = pd.DataFrame(index=methods)
    gate["answerable_pass_rate"] = answerable.groupby("method")["sufficient"].mean().reindex(methods)
    if len(insufficient):
        gate["correct_abstention_rate"] = 1.0 - insufficient.groupby("method")["sufficient"].mean().reindex(methods)

    adaptive_rows = df[(df["method"] == "adaptive_hybrid") & df["adaptive_class"].notna()]
    classes = (
        pd.crosstab(adaptive_rows["query_type"], adaptive_rows["adaptive_class"])
        if len(adaptive_rows)
        else pd.DataFrame()
    )
    return {"overall": overall, "by_type": by_type, "evidence_gate": gate, "adaptive_classes": classes}
