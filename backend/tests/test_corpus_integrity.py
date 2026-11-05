"""Checks that every evidence phrase in the evaluation set really occurs in its corpus document."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "data" / "evaluation"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def load():
    return json.loads((EVAL / "eval_dataset.json").read_text(encoding="utf-8"))["questions"]


def test_every_phrase_is_in_its_document():
    for q in load():
        if q["query_type"] == "insufficient":
            assert q["relevant_document_id"] is None
            continue
        text = norm((EVAL / "corpus" / f"{q['relevant_document_id']}.txt").read_text(encoding="utf-8"))
        assert norm(q["evidence_phrase"]) in text, q["id"]


def test_all_query_types_present_and_ids_unique():
    qs = load()
    assert {q["query_type"] for q in qs} == {
        "exact_keyword", "identifier", "conceptual", "paraphrased", "mixed", "insufficient",
    }
    assert len({q["id"] for q in qs}) == len(qs)


def test_corpus_files_are_labelled_synthetic():
    for p in (EVAL / "corpus").glob("*.txt"):
        assert p.read_text(encoding="utf-8").startswith("SYNTHETIC DOCUMENT"), p.name
