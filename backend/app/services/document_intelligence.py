"""Document intelligence computed at ingestion: type, title, identifiers, dates, keywords, key points.

Pure functions only, so the rules can be unit tested without a database or model.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from app.services.adaptive_retrieval_service import STOPWORDS

DOC_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "policy": ("policy", "policies", "procedure", "shall", "must comply", "employees", "controls"),
    "regulatory circular": ("circular", "regulator", "regulated entities", "directive", "notification", "compliance"),
    "contract": ("agreement", "party", "parties", "hereinafter", "termination", "governing law", "liability"),
    "report": ("findings", "executive summary", "methodology", "results", "analysis", "recommendations"),
    "guide": ("step", "steps", "install", "configure", "instructions", "how to", "guide"),
    "faq": ("faq", "frequently asked", "question", "answer"),
}
MIN_TYPE_HITS = 2

IDENTIFIER_RE = re.compile(r"\b[A-Z]{2,}(?:[-/][A-Z0-9]+)+\b")
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
MONTH_DATE_RE = re.compile(
    r"\b\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}\b"
)
WORD_RE = re.compile(r"[a-z][a-z0-9]{3,}")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
MAX_IDENTIFIERS = 12
MAX_DATES = 8
MAX_KEYWORDS = 8
MAX_KEY_POINTS = 3
MAX_POINT_CHARS = 300
MAX_TITLE_CHARS = 120


@dataclass
class DocumentIntelligence:
    doc_type: str = "other"
    title: str = ""
    identifiers: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)


def _unique(items: list[str], limit: int) -> list[str]:
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return list(seen)[:limit]


def classify_type(text: str) -> str:
    low = text.lower()
    best_type, best_hits = "other", 0
    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        hits = sum(low.count(k) for k in keywords)
        if hits > best_hits:
            best_type, best_hits = doc_type, hits
    return best_type if best_hits >= MIN_TYPE_HITS else "other"


def extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        candidate = line.strip()
        if sum(ch.isalpha() for ch in candidate) >= 5:
            return candidate[:MAX_TITLE_CHARS]
    return fallback


def extract_identifiers(text: str) -> list[str]:
    return _unique(IDENTIFIER_RE.findall(text), MAX_IDENTIFIERS)


def extract_dates(text: str) -> list[str]:
    return _unique(ISO_DATE_RE.findall(text) + MONTH_DATE_RE.findall(text), MAX_DATES)


def extract_keywords(text: str) -> list[str]:
    counts = Counter(w for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS)
    return [w for w, _ in counts.most_common(MAX_KEYWORDS)]


def extract_key_points(text: str) -> list[str]:
    """Extractive key points: the sentences whose words recur most often, kept in document order."""
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(" ".join(text.split())) if len(s.strip()) >= 40]
    if not sentences:
        return []
    freq = Counter(w for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS)
    scored: list[tuple[float, int]] = []
    for idx, sentence in enumerate(sentences):
        words = [w for w in WORD_RE.findall(sentence.lower()) if w not in STOPWORDS]
        if not words:
            continue
        score = sum(freq[w] for w in set(words)) / math.sqrt(len(words))
        scored.append((score, idx))
    top = sorted(scored, reverse=True)[:MAX_KEY_POINTS]
    return [sentences[idx][:MAX_POINT_CHARS] for _, idx in sorted(top, key=lambda t: t[1])]


def analyse_document(page_texts: list[str], filename: str) -> DocumentIntelligence:
    text = "\n".join(page_texts)
    return DocumentIntelligence(
        doc_type=classify_type(text),
        title=extract_title(text, fallback=filename),
        identifiers=extract_identifiers(text),
        dates=extract_dates(text),
        keywords=extract_keywords(text),
        key_points=extract_key_points(text),
    )
