"""Runs the four-method retrieval comparison on the bundled synthetic corpus.

The corpus is ingested into an isolated temporary store + ChromaDB collection, so a user's uploaded
documents are never touched and the evaluation is reproducible.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.core.config import PROJECT_ROOT, Settings, get_settings
from app.core.database import create_scratch_database, drop_database, ensure_indexes
from app.schemas.models import DocStatus, DocumentInfo, RetrievalMethod
from app.services.bm25_service import BM25Service
from app.services.document_service import DocumentStore
from app.services.embedding_service import EmbeddingService
from app.services.generation_service import GenerationService
from app.services.hybrid_retrieval_service import RetrievalService
from app.services.ingestion_service import IngestionService
from app.services.vector_service import VectorService
from app.utils.clock import now_iso

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from experiments.charts import make_charts  # noqa: E402
from experiments.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank  # noqa: E402
from experiments.summarize import METHOD_ORDER, summarize  # noqa: E402


class EvaluationError(RuntimeError):
    pass


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


class EvaluationService:
    def __init__(self, embedder: EmbeddingService) -> None:
        self.embedder = embedder

    # ---- helpers -------------------------------------------------------
    @staticmethod
    def _ingest_corpus(corpus_dir: Path, store: DocumentStore, ingestion: IngestionService, es: Settings) -> None:
        files = sorted(corpus_dir.glob("*.txt"))
        if not files:
            raise EvaluationError(f"No corpus files found in {corpus_dir}.")
        for f in files:
            doc_id = f.stem
            shutil.copy(f, es.documents_dir / f"{doc_id}__{f.name}")
            store.add(
                DocumentInfo(
                    document_id=doc_id,
                    filename=f.name,
                    size_bytes=f.stat().st_size,
                    status=DocStatus.queued,
                    uploaded_at=now_iso(),
                    synthetic=True,
                )
            )
            ingestion.process(doc_id)
            info = store.get(doc_id)
            if info is None or info.status != DocStatus.processed:
                raise EvaluationError(f"Corpus document {f.name} failed to process: {info.error if info else 'unknown'}")

    @staticmethod
    def _resolve(questions: list[dict], store: DocumentStore) -> None:
        chunks = store.all_chunks()
        for q in questions:
            if q["query_type"] == "insufficient":
                q["relevant_chunk_ids"] = []
                continue
            phrase = _norm(q["evidence_phrase"])
            q["relevant_chunk_ids"] = [
                c.chunk_id for c in chunks if c.document_id == q["relevant_document_id"] and phrase in _norm(c.text)
            ]
            if not q["relevant_chunk_ids"]:
                raise EvaluationError(f"{q['id']}: evidence phrase not found in any chunk of {q['relevant_document_id']}.")

    # ---- main ----------------------------------------------------------
    def run(self, k: int = 5, fixed_alpha: float | None = None) -> dict:
        s = get_settings()
        if not s.eval_dataset_path.exists():
            raise EvaluationError(f"Evaluation dataset not found: {s.eval_dataset_path}")
        dataset = json.loads(s.eval_dataset_path.read_text(encoding="utf-8"))
        questions: list[dict] = dataset["questions"]

        work = Path(tempfile.mkdtemp(prefix="eval_", dir=s.evaluation_dir))
        db = create_scratch_database()
        ensure_indexes(db)
        try:
            es = Settings(data_dir=work, chroma_dir=work / "chroma")
            es.ensure_dirs()
            store = DocumentStore(db, es)
            vectors = VectorService(self.embedder, es)
            bm25 = BM25Service()
            ingestion = IngestionService(store, vectors, bm25)
            retrieval = RetrievalService(store, bm25, vectors)
            generation = GenerationService(vectors)

            self._ingest_corpus(s.corpus_dir, store, ingestion, es)
            self._resolve(questions, store)
            n_chunks = len(store.all_chunks())

            methods = [RetrievalMethod(m) for m in METHOD_ORDER]
            for q in questions[:3]:  # warm-up so model load / index build is not counted as latency
                for m in methods:
                    retrieval.search(q["question"], m, k, fixed_alpha)

            rows: list[dict] = []
            for q in questions:
                relevant = set(q["relevant_chunk_ids"])
                for m in methods:
                    res = retrieval.search(q["question"], m, k, fixed_alpha)
                    ranked = [r.chunk.chunk_id for r in res.results]
                    answerable = bool(relevant)
                    rows.append(
                        {
                            "question_id": q["id"],
                            "question": q["question"],
                            "query_type": q["query_type"],
                            "method": m.value,
                            "retrieved_chunk_ids": ranked,
                            "relevant_chunk_ids": sorted(relevant),
                            "precision": precision_at_k(ranked, relevant, k) if answerable else None,
                            "recall": recall_at_k(ranked, relevant, k) if answerable else None,
                            "mrr": reciprocal_rank(ranked, relevant) if answerable else None,
                            "ndcg": ndcg_at_k(ranked, relevant, k) if answerable else None,
                            "latency_ms": res.latency_ms,
                            "sufficient": generation.evidence_sufficient(q["question"], res.results),
                            "adaptive_class": res.adaptive.query_class if res.adaptive else None,
                            "alpha_bm25": res.adaptive.bm25_weight if res.adaptive else None,
                        }
                    )

            df = pd.DataFrame(rows)
            summary = summarize(df)
            n_answerable = sum(1 for q in questions if q["query_type"] != "insufficient")

            out = s.results_dir
            out.mkdir(parents=True, exist_ok=True)
            per_query = df.copy()
            per_query["retrieved_chunk_ids"] = per_query["retrieved_chunk_ids"].map(json.dumps)
            per_query["relevant_chunk_ids"] = per_query["relevant_chunk_ids"].map(json.dumps)
            per_query.to_csv(out / "per_query.csv", index=False)
            summary["overall"].round(4).to_csv(out / "summary_overall.csv")
            summary["by_type"].round(4).to_csv(out / "summary_by_query_type.csv")
            summary["evidence_gate"].round(4).to_csv(out / "summary_evidence_gate.csv")
            charts = make_charts(summary, out, k, n_answerable)

            def frame_json(d: pd.DataFrame) -> list[dict]:
                return json.loads(d.round(4).reset_index().to_json(orient="records"))

            result = {
                "status": "PRELIMINARY",
                "caveat": (
                    f"{n_answerable} answerable questions over a small synthetic corpus ({n_chunks} chunks). "
                    "Differences between methods are indicative only and are not statistically established."
                ),
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "k": k,
                "fixed_alpha": s.fixed_alpha if fixed_alpha is None else fixed_alpha,
                "embedding_model": self.embedder.model_name,
                "chunk_size": s.chunk_size,
                "chunk_overlap": s.chunk_overlap,
                "n_questions": len(questions),
                "n_answerable": n_answerable,
                "n_chunks": n_chunks,
                "overall": frame_json(summary["overall"]),
                "by_query_type": frame_json(summary["by_type"]),
                "evidence_gate": frame_json(summary["evidence_gate"]),
                "adaptive_class_vs_labelled_type": json.loads(summary["adaptive_classes"].to_json())
                if not summary["adaptive_classes"].empty
                else {},
                "charts": [p.name for p in charts],
                "per_query": json.loads(df.to_json(orient="records")),
            }
            (out / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            return result
        finally:
            drop_database(db)
            shutil.rmtree(work, ignore_errors=True)

    @staticmethod
    def latest() -> dict | None:
        p = get_settings().results_dir / "results.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
