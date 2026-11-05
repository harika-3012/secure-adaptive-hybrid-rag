import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank  # noqa: E402


def test_precision_recall():
    r = ["a", "b", "c", "d"]
    assert precision_at_k(r, {"b", "z"}, 4) == 0.25
    assert recall_at_k(r, {"b", "z"}, 4) == 0.5
    assert recall_at_k(r, set(), 4) == 0.0


def test_mrr():
    assert reciprocal_rank(["a", "b", "c"], {"c"}) == 1 / 3
    assert reciprocal_rank(["a"], {"z"}) == 0.0


def test_ndcg_perfect_and_partial():
    assert ndcg_at_k(["a", "b"], {"a"}, 5) == 1.0
    expected = (1 / math.log2(3)) / 1.0
    assert abs(ndcg_at_k(["x", "a"], {"a"}, 5) - expected) < 1e-9
