from __future__ import annotations

import hashlib
import re

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import FileResponse, Response

from app.api.deps import get_container
from app.core.container import Container
from app.core.errors import NotFoundError
from app.schemas.api import FloodSummaryResponse, FloodTimelineResponse, FloodTimesliceResponse, TimeseriesResponse
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/simulations", tags=["flood"])

GEOJSON = "application/geo+json"
_ERRORS = {404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}
_KEY = re.compile(r"^\d{8}T\d{6}Z$")
_CACHE = {"Cache-Control": "private, max-age=3600"}


def _geojson_file(path, request: Request, etag: str) -> Response:  # type: ignore[no-untyped-def]
    tag = '"' + hashlib.sha256(f"{etag}|{path.name}".encode()).hexdigest()[:32] + '"'
    headers = {**_CACHE, "ETag": tag}
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304, headers=headers)
    return FileResponse(path, media_type=GEOJSON, headers=headers)


@router.get("/{simulationId}/flood", response_model=FloodSummaryResponse, responses=_ERRORS, summary="Flood result overview (flood-processing-v1)")
def flood_summary(simulationId: str, container: Container = Depends(get_container)) -> dict:
    return container.flood.summary(simulationId)


@router.get("/{simulationId}/flood/timeline", response_model=FloodTimelineResponse, responses=_ERRORS, summary="Actual SWMM reporting timestamps with flood state summaries")
def flood_timeline(simulationId: str, container: Container = Depends(get_container)) -> dict:
    return container.flood.timeline(simulationId)


@router.get("/{simulationId}/flood/timeslice", response_model=FloodTimesliceResponse, responses=_ERRORS, summary="Flood state at one reporting timestamp")
def flood_timeslice(
    simulationId: str,
    time: str = Query(..., min_length=10, max_length=40, description="ISO 8601 reporting timestamp, e.g. 2023-12-03T22:00:00Z"),
    container: Container = Depends(get_container),
) -> dict:
    return container.flood.timeslice(simulationId, time)


@router.get("/{simulationId}/flood/timeslices/{key}", responses={200: {"content": {GEOJSON: {}}}, **_ERRORS}, response_class=Response, summary="Flood time-slice GeoJSON asset")
def flood_timeslice_asset(request: Request, simulationId: str, key: str = Path(..., max_length=16), container: Container = Depends(get_container)) -> Response:
    if not _KEY.match(key):
        raise NotFoundError("TIMESTAMP_NOT_FOUND", "The requested time slice does not exist for this simulation.", details={"key": key})
    path = container.flood.timeslice_path(simulationId, key)
    return _geojson_file(path, request, container.flood.etag(simulationId))


@router.get("/{simulationId}/flood/zones", responses={200: {"content": {GEOJSON: {}}}, **_ERRORS}, response_class=Response, summary="Nearest-node flood influence zones (all model nodes)")
def flood_zones(request: Request, simulationId: str, container: Container = Depends(get_container)) -> Response:
    return _geojson_file(container.flood.zones_path(simulationId), request, container.flood.etag(simulationId))


def _not_derived(simulation_id: str, product: str) -> None:
    raise NotFoundError(
        "FLOOD_PRODUCT_NOT_AVAILABLE",
        f"A flood {product} product is not derived by flood-processing-v1. SWMM ran without surface ponding and the model/DEM elevations are not vertically consistent; see /flood for the available influence-zone representation.",
        details={"product": product, "alternative": f"/api/v1/simulations/{simulation_id}/flood/timeline"},
        simulation_id=simulation_id,
    )


@router.get("/{simulationId}/flood/extent", responses=_ERRORS, summary="Not available in flood-processing-v1")
def flood_extent(simulationId: str, container: Container = Depends(get_container)) -> dict:
    container.flood.summary(simulationId)  # validates the simulation first
    _not_derived(simulationId, "extent")
    return {}


@router.get("/{simulationId}/flood/depth", responses=_ERRORS, summary="Not available in flood-processing-v1")
def flood_depth(simulationId: str, container: Container = Depends(get_container)) -> dict:
    container.flood.summary(simulationId)
    _not_derived(simulationId, "depth")
    return {}


@router.get("/{simulationId}/timeseries/system", response_model=TimeseriesResponse, responses=_ERRORS, summary="System-level SWMM time series")
def system_timeseries(simulationId: str, container: Container = Depends(get_container)) -> dict:
    return container.timeseries.system(simulationId)


@router.get("/{simulationId}/timeseries/nodes/{nodeId}", response_model=TimeseriesResponse, responses=_ERRORS, summary="SWMM node time series")
def node_timeseries(simulationId: str, nodeId: str = Path(..., max_length=32, pattern=r"^[A-Za-z0-9_]+$"), container: Container = Depends(get_container)) -> dict:
    return container.timeseries.node(simulationId, nodeId)


@router.get("/{simulationId}/timeseries/links/{linkId}", response_model=TimeseriesResponse, responses=_ERRORS, summary="SWMM link time series")
def link_timeseries(simulationId: str, linkId: str = Path(..., max_length=32, pattern=r"^[A-Za-z0-9_]+$"), container: Container = Depends(get_container)) -> dict:
    return container.timeseries.link(simulationId, linkId)

