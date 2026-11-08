"""Evidence-grounded answer generation with a local Ollama model."""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.schemas.models import Chunk, RetrievedChunk
from app.services.adaptive_retrieval_service import STOPWORDS
from app.services.vector_service import VectorService

INSUFFICIENT = "Insufficient evidence was found in the uploaded documents to answer this question reliably."
MAX_SUMMARY_CHARS = 6000

ANSWER_RULES = (
    "1. Answer ONLY using the numbered context passages provided. Do not use outside knowledge.\n"
    "2. Do not invent facts, figures, names or identifiers.\n"
    "3. Cite the passages you used with their labels in square brackets, e.g. [S1] or [S2][S3].\n"
    "4. If the context does not contain enough information, reply exactly: "
    f'"{INSUFFICIENT}"\n'
    "5. Be concise."
)

ANSWER_PROMPT = "You are a document question-answering assistant for an enterprise.\nRules:\n" + ANSWER_RULES

COMPARE_PROMPT = (
    "You are a document analyst for an enterprise. The passages come from several documents, identified in "
    "their source line.\nRules:\n"
    "1. Answer ONLY using the numbered passages. Do not use outside knowledge.\n"
    "2. For each document that bears on the question, say what it states and cite it with its label, e.g. [S2].\n"
    "3. Point out agreements, differences and gaps between the documents.\n"
    "4. If a document does not address the question, say so instead of guessing.\n"
    "5. Do not invent facts, figures, names or identifiers. Be concise."
)

SUMMARY_PROMPT = (
    "You are a document analyst for an enterprise. Summarise the numbered passages of one document.\n"
    "Rules:\n"
    "1. Use ONLY the passages. Do not use outside knowledge.\n"
    "2. Write 5 to 8 short bullet points covering the purpose, key obligations or facts, dates, owners "
    "and identifiers that appear.\n"
    "3. Cite the passage labels you used in square brackets, e.g. [S1].\n"
    "4. Do not invent facts, figures, names or identifiers."
)


class LLMUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Generated:
    text: str
    sufficient: bool
    cited_labels: set[str]


def ollama_status() -> dict:
    s = get_settings()
    try:
        r = httpx.get(f"{s.ollama_url}/api/tags", timeout=3)
        r.raise_for_status()
        names = [m["name"] for m in r.json().get("models", [])]
        installed = any(n == s.ollama_model or n.startswith(s.ollama_model) for n in names)
        return {"reachable": True, "model": s.ollama_model, "model_installed": installed}
    except Exception as exc:  # noqa: BLE001
        return {"reachable": False, "model": s.ollama_model, "model_installed": False, "error": str(exc)}


def build_context(results: list[RetrievedChunk]) -> str:
    return "\n\n".join(
        f"[S{r.rank}] (source: {r.chunk.document_name}, page {r.chunk.page})\n{r.chunk.text}" for r in results
    )


def summary_passages(chunks: list[Chunk]) -> list[Chunk]:
    """Leading chunks of a document, up to the context budget, in reading order."""
    picked: list[Chunk] = []
    used = 0
    for chunk in chunks:
        if picked and used + len(chunk.text) > MAX_SUMMARY_CHARS:
            break
        picked.append(chunk)
        used += len(chunk.text)
    return picked


def lexical_coverage(query: str, text: str) -> float:
    """Share of the query's content words that appear in the chunk (cheap sufficiency signal)."""
    words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in STOPWORDS and len(w) > 2]
    if not words:
        return 0.0
    low = text.lower()
    return sum(1 for w in set(words) if w in low) / len(set(words))


def parse_citations(text: str, valid_labels: set[str]) -> set[str]:
    return {m for m in re.findall(r"\[(S\d+)\]", text) if m in valid_labels}


def _call_ollama(system: str, user: str) -> str:
    s = get_settings()
    payload = {
        "model": s.ollama_model,
        "stream": False,
        "options": {"temperature": 0.1},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    try:
        r = httpx.post(f"{s.ollama_url}/api/chat", json=payload, timeout=s.ollama_timeout_s)
    except httpx.HTTPError as exc:
        raise LLMUnavailable(
            f"The local language model is not reachable ({exc}). Start Ollama and run: ollama pull {s.ollama_model}"
        ) from exc
    if r.status_code == 404:
        raise LLMUnavailable(f"The language model '{s.ollama_model}' is not installed. Run: ollama pull {s.ollama_model}")
    if r.status_code != 200:
        raise LLMUnavailable(f"The local language model returned an error (HTTP {r.status_code}).")
    return r.json()["message"]["content"].strip()


class GenerationService:
    def __init__(self, vectors: VectorService) -> None:
        self.vectors = vectors

    def evidence_sufficient(self, query: str, results: list[RetrievedChunk]) -> bool:
        """Pre-LLM gate: require either real semantic similarity or strong lexical coverage.

        Uses the *raw* cosine similarity (not min-max normalised scores, which always put the best
        candidate at 1.0 and therefore carry no absolute-relevance information).
        """
        s = get_settings()
        if not results:
            return False
        cos = self.vectors.cosine_for(query, [r.chunk.chunk_id for r in results])
        best_cos = max(cos.values(), default=0.0)
        best_cov = max((lexical_coverage(query, r.chunk.text) for r in results), default=0.0)
        return best_cos >= s.min_evidence_score or best_cov >= 0.6

    def answer(self, query: str, results: list[RetrievedChunk], compare: bool = False) -> Generated:
        if not self.evidence_sufficient(query, results):
            return Generated(text=INSUFFICIENT, sufficient=False, cited_labels=set())
        system = COMPARE_PROMPT if compare else ANSWER_PROMPT
        text = _call_ollama(system, f"Context:\n{build_context(results)}\n\nQuestion: {query}\n\nAnswer:")
        if INSUFFICIENT.lower() in text.lower():
            return Generated(text=INSUFFICIENT, sufficient=False, cited_labels=set())
        valid = {f"S{r.rank}" for r in results}
        return Generated(text=text, sufficient=True, cited_labels=parse_citations(text, valid))

    def summarize(self, passages: list[Chunk]) -> Generated:
        context = "\n\n".join(
            f"[S{i}] (source: {c.document_name}, page {c.page})\n{c.text}" for i, c in enumerate(passages, start=1)
        )
        text = _call_ollama(SUMMARY_PROMPT, f"Passages:\n{context}\n\nSummary:")
        valid = {f"S{i}" for i in range(1, len(passages) + 1)}
        return Generated(text=text, sufficient=True, cited_labels=parse_citations(text, valid))
