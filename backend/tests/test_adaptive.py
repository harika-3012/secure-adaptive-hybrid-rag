import pytest

from app.services import adaptive_retrieval_service as ar
from app.utils.scoring import fuse, min_max


@pytest.mark.parametrize(
    "query,expected",
    [
        ("What does POL-SEC-007 say about password rotation?", ar.IDENTIFIER),
        ("Section 4.2.1", ar.IDENTIFIER),
        ('Find the phrase "data retention schedule"', ar.EXACT),
        ("multi-factor authentication", ar.EXACT),
        ("Why should organizations protect customer data and how do they ensure it is handled responsibly?", ar.CONCEPTUAL),
    ],
)
def test_classification(query, expected):
    assert ar.decide(query).query_class == expected


def test_weights_sum_to_one_and_vary_by_query():
    a = ar.decide("POL-SEC-007")
    b = ar.decide("Why should organizations protect customer data and how do they ensure it?")
    assert abs(a.alpha_bm25 + a.alpha_dense - 1.0) < 1e-9
    assert a.alpha_bm25 > b.alpha_bm25  # identifiers lean lexical, concepts lean dense
    assert a.reasons and b.reasons


def test_alpha_is_clamped_and_configurable():
    d = ar.decide("POL-SEC-007 and ISO 27001", {ar.IDENTIFIER: 1.0})
    assert 0.05 <= d.alpha_bm25 <= 0.95


def test_min_max_edge_cases():
    assert min_max({}) == {}
    assert min_max({"a": 2.0, "b": 2.0}) == {"a": 1.0, "b": 1.0}
    assert min_max({"a": 0.0, "b": 0.0}) == {"a": 0.0, "b": 0.0}
    n = min_max({"a": 1.0, "b": 3.0})
    assert n == {"a": 0.0, "b": 1.0}


def test_fuse_union_and_alpha_extremes():
    bm, de = {"x": 5.0, "y": 1.0}, {"y": 0.9, "z": 0.2}
    only_bm = fuse(bm, de, 1.0)
    only_dense = fuse(bm, de, 0.0)
    assert max(only_bm, key=only_bm.get) == "x"
    assert max(only_dense, key=only_dense.get) == "y"
    assert set(fuse(bm, de, 0.5)) == {"x", "y", "z"}
    with pytest.raises(ValueError):
        fuse(bm, de, 1.5)
