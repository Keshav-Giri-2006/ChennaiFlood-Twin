"""Decision-support endpoints: potential bottlenecks, model-derived exposure, recommendations, risk."""

from __future__ import annotations

import hashlib
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import FileResponse, Response

from app.api.deps import get_container
from app.core.container import Container
from app.core.errors import NotFoundError
from app.schemas.api import BottleneckDetailResponse, BottleneckListResponse, ExposureAssetsResponse, ExposureResponse, RecommendationListResponse
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/simulations", tags=["decision-support"])

GEOJSON = "application/geo+json"
_ERRORS = {404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}
_TIME_ONE = Query(None, min_length=10, max_length=40, description="Reporting timestamp (ISO 8601 with offset); omitted = all timestamps")
_TIME = Query(None, min_length=10, max_length=40, description="Reporting timestamp (ISO 8601 with offset); omitted = any reporting timestamp of the event")


@router.get("/{simulationId}/bottlenecks", response_model=BottleneckListResponse, responses=_ERRORS, summary="Potential drainage bottlenecks (bottleneck-analysis-v1)")
def bottlenecks(
    simulationId: str,
    severity: Literal["HIGH", "MODERATE", "LOW"] | None = Query(None, description="Filter by diagnostic severity class"),
    container: Container = Depends(get_container),
) -> dict:
    return container.decision.bottlenecks(simulationId, severity)


@router.get("/{simulationId}/bottlenecks/geojson", responses={200: {"content": {GEOJSON: {}}}, **_ERRORS}, response_class=Response, summary="Potential bottleneck conduit geometry (GeoJSON)")
def bottlenecks_geojson(request: Request, simulationId: str, container: Container = Depends(get_container)) -> Response:
    path = container.decision.bottlenecks_geojson_path(simulationId)
    tag = '"' + hashlib.sha256(container.decision.etag(simulationId).encode()).hexdigest()[:32] + '"'
    headers = {"Cache-Control": "private, max-age=3600", "ETag": tag}
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304, headers=headers)
    return FileResponse(path, media_type=GEOJSON, headers=headers)


@router.get("/{simulationId}/bottlenecks/timeline", responses=_ERRORS, summary="Time-varying state of potential bottlenecks (bottleneck-timeline-v1)")
def bottleneck_timeline(simulationId: str, time: str | None = _TIME_ONE, container: Container = Depends(get_container)) -> dict:
    return container.decision.bottleneck_timeline(simulationId, time)


@router.get("/{simulationId}/bottlenecks/{linkId}", response_model=BottleneckDetailResponse, responses=_ERRORS, summary="Evidence record of one potential bottleneck")
def bottleneck(simulationId: str, linkId: str = Path(..., max_length=32, pattern=r"^[A-Za-z0-9_]+$"), container: Container = Depends(get_container)) -> dict:
    return container.decision.bottleneck(simulationId, linkId)


@router.get("/{simulationId}/exposure", response_model=ExposureResponse, responses=_ERRORS, summary="Model-derived exposure (exposure-analysis-v1)")
def exposure(simulationId: str, container: Container = Depends(get_container)) -> dict:
    return container.decision.exposure(simulationId)


@router.get("/{simulationId}/exposure/buildings", response_model=ExposureAssetsResponse, responses=_ERRORS, summary="Buildings intersecting flood influence zones of overflowing nodes")
def exposure_buildings(simulationId: str, time: str | None = _TIME, container: Container = Depends(get_container)) -> dict:
    return container.decision.exposure_assets(simulationId, "buildings", time)


@router.get("/{simulationId}/exposure/roads", response_model=ExposureAssetsResponse, responses=_ERRORS, summary="Carriageways intersecting flood influence zones of overflowing nodes")
def exposure_roads(simulationId: str, time: str | None = _TIME, container: Container = Depends(get_container)) -> dict:
    return container.decision.exposure_assets(simulationId, "roads", time)


@router.get("/{simulationId}/recommendations", response_model=RecommendationListResponse, responses=_ERRORS, summary="Evidence-based recommendations (decision-support-v1)")
def recommendations(
    simulationId: str,
    priority: Literal["HIGH", "MEDIUM", "LOW"] | None = Query(None, description="Filter by priority"),
    container: Container = Depends(get_container),
) -> dict:
    return container.decision.recommendations(simulationId, priority)


def _risk_not_available(simulation_id: str) -> None:
    raise NotFoundError(
        "RISK_PRODUCT_NOT_AVAILABLE",
        "A risk indicator is not derived in decision-support-v1. Its hazard term would rest on node overflow without ground flood depth or extent, "
        "and on influence zones that are spatial associations rather than inundated areas, so hazard x exposure would not be defensible. "
        "Model-derived exposure and evidence-based recommendations are available instead.",
        details={"alternatives": [f"/api/v1/simulations/{simulation_id}/exposure", f"/api/v1/simulations/{simulation_id}/recommendations"], "method": "docs/DECISION_SUPPORT_METHOD.md"},
        simulation_id=simulation_id,
    )


@router.get("/{simulationId}/risk", responses=_ERRORS, summary="Not available in decision-support-v1")
def risk(simulationId: str, container: Container = Depends(get_container)) -> dict:
    container.simulations.ensure_completed(simulationId)
    _risk_not_available(simulationId)
    return {}


@router.get("/{simulationId}/risk/geojson", responses=_ERRORS, summary="Not available in decision-support-v1")
def risk_geojson(simulationId: str, container: Container = Depends(get_container)) -> dict:
    container.simulations.ensure_completed(simulationId)
    _risk_not_available(simulationId)
    return {}
