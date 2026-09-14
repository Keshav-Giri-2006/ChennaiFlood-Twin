from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_container
from app.core.container import Container
from app.schemas.api import HealthResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse, summary="Liveness check")
def health(container: Container = Depends(get_container)) -> dict:
    return container.health.liveness()


@router.get("/ready", response_model=ReadinessResponse, responses={503: {"model": ReadinessResponse}}, summary="Readiness check")
def ready(container: Container = Depends(get_container)) -> JSONResponse:
    body = container.health.readiness()
    return JSONResponse(status_code=200 if body["status"] == "ready" else 503, content=ReadinessResponse(**body).model_dump(exclude_none=True))
