"""Local sentence-transformer embeddings (lazy loaded; no external API)."""
from __future__ import annotations

import threading

import numpy as np

from app.core.config import get_settings


class EmbeddingUnavailable(RuntimeError):
    pass


class EmbeddingService:
    def __init__(self) -> None:
        self._model = None
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        s = get_settings()
        return s.embedding_model_path or s.embedding_model

    def _load(self):
        with self._lock:
            if self._model is None:
                try:
                    from sentence_transformers import SentenceTransformer

                    self._model = SentenceTransformer(self.model_name)
                except Exception as exc:  # noqa: BLE001
                    raise EmbeddingUnavailable(
                        f"Could not load embedding model '{self.model_name}': {exc}. "
                        "Download it once while online, or set EMBEDDING_MODEL_PATH to a local folder "
                        "(see README: air-gapped model setup)."
                    ) from exc
        return self._model

    def is_loaded(self) -> bool:
        return self._model is not None

    def embed(self, texts: list[str]) -> np.ndarray:
        """L2-normalised embeddings, so dot product == cosine similarity."""
        model = self._load()
        return np.asarray(model.encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32))
