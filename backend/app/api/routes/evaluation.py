from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.container import get_container
from app.schemas.models import EvaluationRequest
from app.services.embedding_service import EmbeddingUnavailable
from app.services.evaluation_service import EvaluationError, EvaluationService

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.post("/run")
def run(req: EvaluationRequest | None = None) -> dict:
    """Run the four-method comparison on the bundled synthetic corpus (isolated from uploaded documents)."""
    req = req or EvaluationRequest()
    try:
        return EvaluationService(get_container().embedder).run(req.k, req.fixed_alpha)
    except EmbeddingUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except EvaluationError as exc:
        raise HTTPException(500, str(exc)) from exc


@router.get("/results")
def results() -> dict:
    data = EvaluationService.latest()
    if data is None:
        raise HTTPException(404, "No evaluation results yet. Run POST /api/evaluation/run first.")
    return data


@router.get("/charts/{name}")
def chart(name: str) -> FileResponse:
    path = (get_settings().results_dir / name).resolve()
    if path.parent != get_settings().results_dir.resolve() or path.suffix != ".png" or not path.exists():
        raise HTTPException(404, "Chart not found.")
    return FileResponse(path, media_type="image/png")
