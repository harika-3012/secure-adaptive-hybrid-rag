"""Aggregation logic checked on a tiny hand-computable frame (these numbers are a unit-test fixture, not results)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.summarize import summarize  # noqa: E402


def frame():
    rows = []
    for method, mrrs in {"bm25": (1.0, 0.5), "dense": (0.5, 0.5)}.items():
        for qid, (qt, m) in enumerate(zip(("identifier", "conceptual"), mrrs)):
            rows.append(dict(query_type=qt, method=method, precision=m, recall=m, mrr=m, ndcg=m,
                             latency_ms=10.0 + qid, sufficient=True, adaptive_class=None))
        rows.append(dict(query_type="insufficient", method=method, precision=None, recall=None, mrr=None,
                         ndcg=None, latency_ms=12.0, sufficient=(method == "dense"), adaptive_class=None))
    return pd.DataFrame(rows)


def test_overall_excludes_insufficient_and_means_are_correct():
    s = summarize(frame())
    assert s["overall"].loc["bm25", "mrr"] == 0.75
    assert s["overall"].loc["dense", "mrr"] == 0.5
    assert s["overall"].loc["bm25", "latency_mean_ms"] == (10 + 11 + 12) / 3


def test_gate_rates():
    g = summarize(frame())["evidence_gate"]
    assert g.loc["bm25", "correct_abstention_rate"] == 1.0
    assert g.loc["dense", "correct_abstention_rate"] == 0.0
    assert g.loc["bm25", "answerable_pass_rate"] == 1.0
