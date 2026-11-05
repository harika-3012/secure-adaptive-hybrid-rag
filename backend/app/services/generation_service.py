"""Evidence-grounded answer generation with a local Ollama model."""
from __future__ import annotations

import re
import time

import httpx

from app.core.config import get_settings
from app.schemas.models import ChatResponse, Citation, SearchResponse
from app.services.adaptive_retrieval_service import STOPWORDS
from app.services.vector_service import VectorService

INSUFFICIENT = "Insufficient evidence was found in the uploaded documents to answer this question reliably."

SYSTEM_PROMPT = (
    "You are a document question-answering assistant for an enterprise.\n"
    "Rules:\n"
    "1. Answer ONLY using the numbered context passages provided. Do not use outside knowledge.\n"
    "2. Do not invent facts, figures, names or identifiers.\n"
    "3. Cite the passages you used with their labels in square brackets, e.g. [S1] or [S2][S3].\n"
    "4. If the context does not contain enough information, reply exactly: "
    f'"{INSUFFICIENT}"\n'
    "5. Be concise."
)


class LLMUnavailable(RuntimeError):
    pass


def ollama_status() -> dict:
    s = get_settings()
    try:
        r = httpx.get(f"{s.ollama_url}/api/tags", timeout=3)
        r.raise_for_status()
        names = [m["name"] for m in r.json().get("models", [])]
        installed = any(n == s.ollama_model or n.startswith(s.ollama_model) for n in names)
        return {"reachable": True, "model": s.ollama_model, "model_installed": installed, "installed_models": names}
    except Exception as exc:  # noqa: BLE001
        return {"reachable": False, "model": s.ollama_model, "model_installed": False, "error": str(exc)}


def build_context(search: SearchResponse) -> str:
    return "\n\n".join(
        f"[S{r.rank}] (source: {r.chunk.document_name}, page {r.chunk.page})\n{r.chunk.text}" for r in search.results
    )


def lexical_coverage(query: str, text: str) -> float:
    """Share of the query's content words that appear in the chunk (cheap sufficiency signal)."""
    words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in STOPWORDS and len(w) > 2]
    if not words:
        return 0.0
    low = text.lower()
    return sum(1 for w in set(words) if w in low) / len(set(words))


class GenerationService:
    def __init__(self, vectors: VectorService) -> None:
        self.vectors = vectors

    def evidence_sufficient(self, query: str, search: SearchResponse) -> bool:
        """Pre-LLM gate: require either real semantic similarity or strong lexical coverage.

        Uses the *raw* cosine similarity (not min-max normalised scores, which always put the best
        candidate at 1.0 and therefore carry no absolute-relevance information).
        """
        s = get_settings()
        if not search.results:
            return False
        cos = self.vectors.cosine_for(query, [r.chunk.chunk_id for r in search.results])
        best_cos = max(cos.values(), default=0.0)
        best_cov = max((lexical_coverage(query, r.chunk.text) for r in search.results), default=0.0)
        return best_cos >= s.min_evidence_score or best_cov >= 0.6

    def _call_ollama(self, question: str, context: str) -> str:
        s = get_settings()
        payload = {
            "model": s.ollama_model,
            "stream": False,
            "options": {"temperature": 0.1},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"},
            ],
        }
        try:
            r = httpx.post(f"{s.ollama_url}/api/chat", json=payload, timeout=s.ollama_timeout_s)
        except httpx.HTTPError as exc:
            raise LLMUnavailable(
                f"Cannot reach Ollama at {s.ollama_url} ({exc}). Install/start Ollama and run: ollama pull {s.ollama_model}"
            ) from exc
        if r.status_code == 404:
            raise LLMUnavailable(f"Model '{s.ollama_model}' is not installed. Run: ollama pull {s.ollama_model}")
        if r.status_code != 200:
            raise LLMUnavailable(f"Ollama returned HTTP {r.status_code}: {r.text[:200]}")
        return r.json()["message"]["content"].strip()

    def answer(self, query: str, search: SearchResponse) -> ChatResponse:
        s = get_settings()
        t0 = time.perf_counter()
        sufficient = self.evidence_sufficient(query, search)
        if not sufficient:
            answer, cited = INSUFFICIENT, set()
        else:
            answer = self._call_ollama(query, build_context(search))
            valid = {f"S{r.rank}" for r in search.results}
            cited = {m for m in re.findall(r"\[(S\d+)\]", answer) if m in valid}  # drop invented labels
            if INSUFFICIENT.lower() in answer.lower():
                sufficient = False
        gen_ms = (time.perf_counter() - t0) * 1000

        citations = [
            Citation(
                label=f"S{r.rank}",
                chunk_id=r.chunk.chunk_id,
                document_id=r.chunk.document_id,
                document_name=r.chunk.document_name,
                page=r.chunk.page,
                excerpt=r.chunk.text,
                cited_by_model=f"S{r.rank}" in cited,
            )
            for r in search.results
        ]
        return ChatResponse(
            answer=answer,
            sufficient_evidence=sufficient,
            method=search.method,
            retrieved=search.results,
            citations=citations,
            adaptive=search.adaptive,
            model=s.ollama_model,
            retrieval_latency_ms=search.latency_ms,
            generation_latency_ms=round(gen_ms, 2),
            total_latency_ms=round(search.latency_ms + gen_ms, 2),
        )
