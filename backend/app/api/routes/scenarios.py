from __future__ import annotations

from fastapi import APIRouter, Depends, Path

from app.api.deps import get_container
from app.core.container import Container
from app.schemas.api import RainfallSeriesResponse, ScenarioDetail, ScenarioListResponse
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

ScenarioIdPath = Path(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9-]*$")


@router.get("", response_model=ScenarioListResponse, summary="List rainfall scenarios")
def list_scenarios(container: Container = Depends(get_container)) -> dict:
    return {"scenarios": container.scenarios.list_summaries()}


@router.get("/{scenarioId}", response_model=ScenarioDetail, responses={404: {"model": ErrorResponse}}, summary="Get scenario metadata")
def get_scenario(scenarioId: str = ScenarioIdPath, container: Container = Depends(get_container)) -> dict:
    return container.scenarios.detail(scenarioId)


@router.get("/{scenarioId}/rainfall", response_model=RainfallSeriesResponse, responses={404: {"model": ErrorResponse}}, summary="Get scenario rainfall series (source data)")
def get_scenario_rainfall(scenarioId: str = ScenarioIdPath, container: Container = Depends(get_container)) -> dict:
    return container.scenarios.rainfall_series(scenarioId)
