"""Central, environment-driven configuration (no hardcoded paths or secrets)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    data_dir: Path = PROJECT_ROOT / "data"
    chroma_dir: Path | None = None

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_model_path: str = ""  # local folder, preferred when set (air-gapped)

    chunk_size: int = Field(800, ge=100, le=4000)
    chunk_overlap: int = Field(120, ge=0, le=1000)
    max_upload_mb: int = Field(25, ge=1, le=500)
    allowed_extensions: tuple[str, ...] = (".pdf", ".docx", ".txt")

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_s: int = 180

    fixed_alpha: float = Field(0.5, ge=0.0, le=1.0)
    min_evidence_score: float = Field(0.25, ge=0.0, le=1.0)
    candidate_pool: int = Field(30, ge=5, le=200)

    # Adaptive retrieval: base alpha per query class (weight given to BM25).
    adaptive_alpha_identifier: float = 0.85
    adaptive_alpha_exact: float = 0.75
    adaptive_alpha_mixed: float = 0.50
    adaptive_alpha_semantic: float = 0.30
    adaptive_alpha_conceptual: float = 0.20

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def evaluation_dir(self) -> Path:
        return self.data_dir / "evaluation"

    @property
    def corpus_dir(self) -> Path:
        return self.evaluation_dir / "corpus"

    @property
    def eval_dataset_path(self) -> Path:
        return self.evaluation_dir / "eval_dataset.json"

    @property
    def results_dir(self) -> Path:
        return PROJECT_ROOT / "experiments" / "results"

    @property
    def chroma_path(self) -> Path:
        return self.chroma_dir or (self.processed_dir / "chroma")

    @property
    def registry_path(self) -> Path:
        return self.processed_dir / "documents.json"

    @property
    def chunks_path(self) -> Path:
        return self.processed_dir / "chunks.jsonl"

    def ensure_dirs(self) -> None:
        for p in (self.documents_dir, self.processed_dir, self.evaluation_dir, self.chroma_path):
            p.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
