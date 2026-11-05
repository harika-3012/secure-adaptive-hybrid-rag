"""Check that the local embedding model and the Ollama LLM are reachable.

Run from the backend venv:  python scripts/verify_models.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx  # noqa: E402

from app.core.config import get_settings  # noqa: E402


def main() -> int:
    s = get_settings()
    ok = True

    print(f"[1/2] Embedding model: {s.embedding_model_path or s.embedding_model}")
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(s.embedding_model_path or s.embedding_model)
        dim = model.get_sentence_embedding_dimension()
        print(f"      OK (dimension={dim})")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"      FAILED: {exc}")
        print("      Fix: connect once to download the model, or set EMBEDDING_MODEL_PATH to a local copy.")

    print(f"[2/2] Ollama at {s.ollama_url}, model {s.ollama_model}")
    try:
        r = httpx.get(f"{s.ollama_url}/api/tags", timeout=5)
        r.raise_for_status()
        names = [m["name"] for m in r.json().get("models", [])]
        if any(n == s.ollama_model or n.startswith(s.ollama_model) for n in names):
            print(f"      OK (installed: {', '.join(names)})")
        else:
            ok = False
            print(f"      Ollama is running but '{s.ollama_model}' is not installed. Run: ollama pull {s.ollama_model}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"      FAILED: {exc}")
        print("      Fix: install Ollama from https://ollama.com and start it.")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
