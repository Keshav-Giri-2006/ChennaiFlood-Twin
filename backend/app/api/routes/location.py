from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import Field

from app.api.deps import get_container
from app.core.container import Container
from app.schemas.common import ApiModel, ErrorResponse

router = APIRouter(prefix="/simulations", tags=["location-check"])

_ERRORS = {404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}

DEFAULT_RADIUS_M = 250.0


class LocationCheckRequest(ApiModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False, description="WGS 84 latitude (EPSG:4326), decimal degrees")
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False, description="WGS 84 longitude (EPSG:4326), decimal degrees")
    radiusMeters: float = Field(default=DEFAULT_RADIUS_M, ge=50, le=1000, allow_inf_nan=False, description="Radius of the surrounding area (metres, evaluated in EPSG:32644)")


@router.post(
    "/{simulationId}/location-check",
    responses=_ERRORS,
    summary="Model-derived flood response around a selected location (location-check-v1)",
)
def location_check(simulationId: str, body: LocationCheckRequest, container: Container = Depends(get_container)) -> dict:
    return container.location.check(simulationId, body.latitude, body.longitude, body.radiusMeters)
