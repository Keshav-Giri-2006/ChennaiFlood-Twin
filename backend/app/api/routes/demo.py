from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Response

from app.api.deps import get_container
from app.core.container import Container
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("", summary="Registered precomputed demonstration results")
def demo_catalogue(response: Response, container: Container = Depends(get_container)) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return container.demo.catalogue()


@router.post(
    "/{demoId}/load",
    status_code=202,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="Load the verified precomputed demonstration result (does not run SWMM)",
)
def load_demo(demoId: str = Path(..., max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$"), container: Container = Depends(get_container)) -> dict:
    return container.demo.load(demoId)
