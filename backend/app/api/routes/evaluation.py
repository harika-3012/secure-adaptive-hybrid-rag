from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import require_admin
from app.core.config import get_settings
from app.core.container import get_container
from app.schemas.models import EvaluationRequest
from app.services.access_service import Principal
from app.services.embedding_service import EmbeddingUnavailable
from app.services.evaluation_service import EvaluationError, EvaluationService

router = APIRouter(prefix="/api/admin/evaluation", tags=["admin"])


@router.post("/run")
def run(req: EvaluationRequest | None = None, p: Principal = Depends(require_admin)) -> dict:
    """Run the four-method comparison on the bundled synthetic corpus (isolated from uploaded documents)."""
    req = req or EvaluationRequest()
    try:
        return EvaluationService(get_container().embedder).run(req.k, req.fixed_alpha)
    except EmbeddingUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except EvaluationError as exc:
        raise HTTPException(500, str(exc)) from exc


@router.get("/results")
def results(p: Principal = Depends(require_admin)) -> dict:
    data = EvaluationService.latest()
    if data is None:
        raise HTTPException(404, "No evaluation results yet. Run POST /api/evaluation/run first.")
    return data


@router.get("/charts/{name}")
def chart(name: str, p: Principal = Depends(require_admin)) -> FileResponse:
    path = (get_settings().results_dir / name).resolve()
    if path.parent != get_settings().results_dir.resolve() or path.suffix != ".png" or not path.exists():
        raise HTTPException(404, "Chart not found.")
    return FileResponse(path, media_type="image/png")
