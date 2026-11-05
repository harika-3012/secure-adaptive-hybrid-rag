"""Query analysis and adaptive weighting (the core research module).

Algorithm
---------
1. Extract surface features from the query (identifiers, quotes, length, question type, ...).
2. Classify the query into one of five classes using explicit rules (see `classify`).
3. Start from a configurable base alpha for the class (alpha = weight of BM25).
4. Apply small, bounded feature adjustments (e.g. long natural-language queries push toward dense).
5. Clamp alpha to [0.05, 0.95] so neither retriever is ever fully switched off.
Every decision is recorded in `reasons`, so the choice is explainable.

This is a rule-based heuristic, not a learned model; learning alpha from data is future work.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Identifiers such as "RBI/2023-24/12", "ISO 27001", "Section 4.2.1", "POL-SEC-007", "CP-9".
ID_PATTERNS = [
    re.compile(r"\b[A-Z]{2,}[-/][A-Z0-9]{1,}(?:[-/][A-Z0-9.]+)*\b"),  # POL-SEC-007, RBI/2023-24/12
    re.compile(r"\b(?:section|clause|article|annex(?:ure)?|para(?:graph)?|policy|circular|regulation|rule)\s*(?:no\.?\s*)?[\dA-Z][\w.\-/]*", re.I),
    re.compile(r"\b[A-Z]{2,}\s?\d{3,}\b"),  # ISO 27001
    re.compile(r"\b\d+(?:\.\d+){1,}\b"),  # 4.2.1
]
QUOTE_RE = re.compile(r"[\"“”'‘’]([^\"“”'‘’]{3,})[\"“”'‘’]")
ACRONYM_RE = re.compile(r"\b[A-Z]{2,6}\b")
CONCEPT_WORDS = {
    "why", "how", "explain", "describe", "purpose", "reason", "impact", "importance",
    "overview", "difference", "compare", "benefit", "risk", "approach", "principle",
    "responsibilities", "ensure", "protect", "prevent", "manage", "handle", "should",
}
PARAPHRASE_HINTS = {"something", "kind of", "sort of", "basically", "in general", "ways to", "rules about", "what happens"}
QUESTION_WORDS = ("what", "which", "who", "when", "where", "how", "why", "is", "are", "does", "do", "can", "should")
STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are", "what", "which", "how", "why",
    "does", "do", "can", "should", "be", "by", "with", "at", "as", "that", "this", "it", "from", "about",
}

EXACT = "exact_keyword"
IDENTIFIER = "identifier"
SEMANTIC = "semantic"
CONCEPTUAL = "conceptual"
MIXED = "mixed"


@dataclass
class QueryFeatures:
    n_tokens: int
    identifiers: list[str]
    quoted_phrases: list[str]
    acronyms: list[str]
    concept_hits: int
    paraphrase_hits: int
    question_type: str  # "wh", "yes_no", "imperative", "keywords"
    content_ratio: float  # share of non-stopword tokens


@dataclass
class AdaptiveDecision:
    query_class: str
    alpha_bm25: float
    alpha_dense: float
    features: QueryFeatures
    reasons: list[str] = field(default_factory=list)


def extract_features(query: str) -> QueryFeatures:
    q = query.strip()
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-/.]*", q)
    ids: list[str] = []
    for pat in ID_PATTERNS:
        ids.extend(m.group(0).strip() for m in pat.finditer(q))
    ids = list(dict.fromkeys(ids))
    quotes = [m.group(1).strip() for m in QUOTE_RE.finditer(q)]
    acr = [a for a in ACRONYM_RE.findall(q) if a not in {"A", "I"} and a.lower() not in STOPWORDS]
    lower = q.lower()
    words = re.findall(r"[a-z]+", lower)
    concept_hits = sum(1 for w in words if w in CONCEPT_WORDS)
    para_hits = sum(1 for p in PARAPHRASE_HINTS if p in lower)
    first = words[0] if words else ""
    if first in {"is", "are", "does", "do", "can", "should"}:
        qtype = "yes_no"
    elif first in QUESTION_WORDS or q.endswith("?"):
        qtype = "wh"
    elif len(words) <= 4:
        qtype = "keywords"
    else:
        qtype = "imperative"
    content = [w for w in words if w not in STOPWORDS]
    ratio = len(content) / max(len(words), 1)
    return QueryFeatures(len(tokens), ids, quotes, acr, concept_hits, para_hits, qtype, ratio)


def classify(f: QueryFeatures) -> tuple[str, list[str]]:
    """Rule cascade; the first matching rule wins. Returns (class, reasons)."""
    reasons: list[str] = []
    has_id = bool(f.identifiers)
    has_quote = bool(f.quoted_phrases)
    conceptual = f.concept_hits >= 1 or f.paraphrase_hits >= 1

    if has_id and (conceptual and f.n_tokens > 6):
        reasons.append(f"identifier(s) {f.identifiers} present but question is also conceptual/long -> mixed")
        return MIXED, reasons
    if has_id:
        reasons.append(f"exact identifier(s) detected: {f.identifiers}")
        return IDENTIFIER, reasons
    if has_quote:
        reasons.append(f"quoted phrase(s) detected: {f.quoted_phrases}")
        return EXACT, reasons
    if f.question_type == "keywords" and f.content_ratio >= 0.8 and not conceptual:
        reasons.append("short keyword-style query without question intent")
        return EXACT, reasons
    if f.acronyms and not conceptual and f.n_tokens <= 6:
        reasons.append(f"short query centred on technical term(s): {f.acronyms}")
        return EXACT, reasons
    if f.acronyms and conceptual:
        reasons.append(f"technical term(s) {f.acronyms} combined with conceptual wording -> mixed")
        return MIXED, reasons
    if f.concept_hits >= 2 or (f.concept_hits >= 1 and f.n_tokens >= 8):
        reasons.append(f"explanatory intent ({f.concept_hits} concept cue words, {f.n_tokens} tokens)")
        return CONCEPTUAL, reasons
    if f.paraphrase_hits >= 1 or f.n_tokens >= 9:
        reasons.append("long or loosely-worded natural-language query")
        return SEMANTIC, reasons
    reasons.append("no strong lexical or semantic signal -> balanced")
    return MIXED, reasons


def decide(query: str, base_alphas: dict[str, float] | None = None) -> AdaptiveDecision:
    """Compute alpha(q), the BM25 weight; dense weight is 1 - alpha(q)."""
    base = {
        IDENTIFIER: 0.85,
        EXACT: 0.75,
        MIXED: 0.50,
        SEMANTIC: 0.30,
        CONCEPTUAL: 0.20,
    }
    if base_alphas:
        base.update(base_alphas)

    f = extract_features(query)
    cls, reasons = classify(f)
    alpha = base[cls]
    reasons.append(f"base alpha for '{cls}' = {alpha:.2f}")

    # Bounded feature adjustments (each <= 0.1 in magnitude).
    if f.n_tokens >= 14:
        alpha -= 0.05
        reasons.append("long query (>=14 tokens): -0.05 toward dense")
    if f.n_tokens <= 3 and cls != CONCEPTUAL:
        alpha += 0.05
        reasons.append("very short query (<=3 tokens): +0.05 toward BM25")
    if f.question_type == "wh" and cls in (MIXED, SEMANTIC, CONCEPTUAL):
        alpha -= 0.05
        reasons.append("wh-question: -0.05 toward dense")
    if len(f.identifiers) >= 2:
        alpha += 0.05
        reasons.append("multiple identifiers: +0.05 toward BM25")
    if f.quoted_phrases and cls != EXACT:
        alpha += 0.05
        reasons.append("quoted phrase present: +0.05 toward BM25")

    alpha = min(0.95, max(0.05, alpha))
    return AdaptiveDecision(cls, round(alpha, 4), round(1 - alpha, 4), f, reasons)
