"""Retrieval orchestrator: BM25, dense, fixed hybrid and adaptive hybrid. Internal only; not exposed to end users."""
from __future__ import annotations

import time

from app.core.config import get_settings
from app.schemas.models import (
    AdaptiveConfig,
    AdaptiveInfo,
    RetrievalMethod,
    RetrievedChunk,
    SearchResponse,
)
from app.services import adaptive_retrieval_service as adaptive
from app.services.bm25_service import BM25Service
from app.services.document_service import DocumentStore
from app.services.vector_service import VectorService
from app.utils.scoring import fuse, min_max


class RetrievalService:
    def __init__(self, store: DocumentStore, bm25: BM25Service, vectors: VectorService) -> None:
        self.store, self.bm25, self.vectors = store, bm25, vectors
        self._built_version = -1
        self._by_id: dict = {}

    def _ensure_index(self) -> None:
        if self._built_version != self.store.version:
            chunks = self.store.all_chunks()
            self.bm25.build(chunks)
            self._by_id = {c.chunk_id: c for c in chunks}
            self._built_version = self.store.version

    def config(self) -> dict:
        s = get_settings()
        return {
            "chunk_size": s.chunk_size,
            "chunk_overlap": s.chunk_overlap,
            "embedding_model": s.embedding_model_path or s.embedding_model,
            "fixed_alpha": s.fixed_alpha,
            "candidate_pool": s.candidate_pool,
            "adaptive_base_alpha_bm25": self._base_alphas(None),
            "min_evidence_score": s.min_evidence_score,
            "methods": [m.value for m in RetrievalMethod],
        }

    @staticmethod
    def _base_alphas(cfg: AdaptiveConfig | None) -> dict[str, float]:
        s = get_settings()
        base = {
            adaptive.IDENTIFIER: s.adaptive_alpha_identifier,
            adaptive.EXACT: s.adaptive_alpha_exact,
            adaptive.MIXED: s.adaptive_alpha_mixed,
            adaptive.SEMANTIC: s.adaptive_alpha_semantic,
            adaptive.CONCEPTUAL: s.adaptive_alpha_conceptual,
        }
        if cfg:
            for key, val in cfg.model_dump().items():
                if val is not None:
                    base[key] = val
        return base

    def search(
        self,
        query: str,
        method: RetrievalMethod,
        top_k: int = 5,
        fixed_alpha: float | None = None,
        adaptive_config: AdaptiveConfig | None = None,
        document_ids: set[str] | None = None,
    ) -> SearchResponse:
        """Rank chunks. document_ids limits candidates to those documents (None = no restriction)."""
        s = get_settings()
        self._ensure_index()
        t0 = time.perf_counter()
        pool = max(s.candidate_pool, top_k)
        info: AdaptiveInfo | None = None
        alpha_used: float | None = None

        bm_raw: dict[str, float] = {}
        de_raw: dict[str, float] = {}
        if method in (RetrievalMethod.bm25, RetrievalMethod.fixed_hybrid, RetrievalMethod.adaptive_hybrid):
            bm_raw = self.bm25.search(query, pool, document_ids)
        if method in (RetrievalMethod.dense, RetrievalMethod.fixed_hybrid, RetrievalMethod.adaptive_hybrid):
            de_raw = self.vectors.search(query, pool, document_ids)

        nb, nd = min_max(bm_raw), min_max(de_raw)
        if method == RetrievalMethod.bm25:
            final = nb
        elif method == RetrievalMethod.dense:
            final = nd
        elif method == RetrievalMethod.fixed_hybrid:
            alpha_used = s.fixed_alpha if fixed_alpha is None else fixed_alpha
            final = fuse(bm_raw, de_raw, alpha_used)
        else:
            d = adaptive.decide(query, self._base_alphas(adaptive_config))
            final = fuse(bm_raw, de_raw, d.alpha_bm25)
            info = AdaptiveInfo(
                query_class=d.query_class,
                bm25_weight=d.alpha_bm25,
                dense_weight=d.alpha_dense,
                reasons=d.reasons,
                features=vars(d.features),
            )

        ranked = sorted(final.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        results: list[RetrievedChunk] = []
        for cid, score in ranked:
            chunk = self._by_id.get(cid)
            if chunk is None:
                continue
            results.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=round(score, 6),
                    bm25_score=round(nb.get(cid, 0.0), 6) if bm_raw or method == RetrievalMethod.bm25 else None,
                    dense_score=round(nd.get(cid, 0.0), 6) if de_raw or method == RetrievalMethod.dense else None,
                    rank=len(results) + 1,
                )
            )
        latency = (time.perf_counter() - t0) * 1000
        return SearchResponse(
            method=method,
            query=query,
            results=results,
            adaptive=info,
            fixed_alpha=alpha_used,
            latency_ms=round(latency, 2),
        )
