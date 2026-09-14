from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import get_container
from app.core.container import Container
from app.models.simulation import SimulationRecord, SimulationStatus
from app.schemas.api import (
    CreateSimulationRequest,
    DiagnosticsResponse,
    KpiResponse,
    ResultProductsResponse,
    SimulationCreatedResponse,
    SimulationListResponse,
    SimulationStatusResponse,
    SummaryResponse,
)
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/simulations", tags=["simulations"])

_ERRORS = {404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}}


def _status(record: SimulationRecord) -> SimulationStatusResponse:
    return SimulationStatusResponse(
        simulationId=record.simulation_id,
        scenarioId=record.scenario_id,
        modelVersion=record.model_version,
        processingVersion=record.processing_version,
        applicationVersion=record.application_version,
        status=record.status,
        stage=record.stage,
        progress=record.progress,
        createdAt=record.created_at,
        startedAt=record.started_at,
        completedAt=record.completed_at,
        error=(
            {"code": record.error.code, "message": record.error.message, "details": record.error.details}
            if record.error
            else None
        ),
        parameters=record.parameters,
        executionMode=record.artifacts.get("executionMode", "swmm"),
        demoId=record.artifacts.get("demoId"),
        scenarioRun=record.artifacts.get("scenarioRun"),
    )


def _cache_completed(response: Response, record: SimulationRecord) -> None:
    # Completed results are immutable; active runs must never be cached.
    response.headers["Cache-Control"] = "private, max-age=300" if record.status == SimulationStatus.COMPLETED else "no-store"


@router.post(
    "",
    status_code=202,
    response_model=SimulationCreatedResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="Create and start a simulation",
)
def create_simulation(body: CreateSimulationRequest, response: Response, container: Container = Depends(get_container)) -> SimulationCreatedResponse:
    record = container.simulations.create(body.scenarioId, body.modelVersion, body.parameters)
    response.headers["Location"] = f"/api/v1/simulations/{record.simulation_id}"
    return SimulationCreatedResponse(
        simulationId=record.simulation_id,
        scenarioId=record.scenario_id,
        modelVersion=record.model_version,
        status=record.status,
        createdAt=record.created_at,
    )


@router.get("", response_model=SimulationListResponse, summary="List simulations (newest first)")
def list_simulations(
    scenarioId: str | None = Query(default=None, max_length=128),
    status: SimulationStatus | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    rainfallMultiplier: float | None = Query(default=None, gt=0, le=100, description="Only runs with this rainfall multiplier (1.0 matches baseline runs without parameters)"),
    executionMode: str | None = Query(default=None, pattern=r"^(swmm|precomputed-demo)$"),
    container: Container = Depends(get_container),
) -> SimulationListResponse:
    if rainfallMultiplier is None and executionMode is None:
        records = container.simulations.list(scenario_id=scenarioId, status=status, limit=limit, offset=offset)
    else:
        candidates = container.simulations.list(scenario_id=scenarioId, status=status, limit=1000, offset=0)
        records = [
            r for r in candidates
            if (rainfallMultiplier is None or float(r.parameters.get("rainfallMultiplier", 1.0)) == rainfallMultiplier)
            and (executionMode is None or r.artifacts.get("executionMode", "swmm") == executionMode)
        ][offset : offset + limit]
    return SimulationListResponse(simulations=[_status(r) for r in records], limit=limit, offset=offset)


@router.get("/{simulationId}", response_model=SimulationStatusResponse, responses=_ERRORS, summary="Get simulation status")
def get_simulation(simulationId: str, response: Response, container: Container = Depends(get_container)) -> SimulationStatusResponse:
    record = container.simulations.get(simulationId)
    response.headers["Cache-Control"] = "no-store"
    return _status(record)


@router.get("/{simulationId}/results", response_model=ResultProductsResponse, responses=_ERRORS, summary="Discover available result products")
def get_products(simulationId: str, response: Response, container: Container = Depends(get_container)) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return container.results.products(simulationId)


@router.get("/{simulationId}/summary", response_model=SummaryResponse, responses=_ERRORS, summary="Simulation summary")
def get_summary(simulationId: str, response: Response, container: Container = Depends(get_container)) -> dict:
    body = container.results.summary(simulationId)
    _cache_completed(response, container.simulations.get(simulationId))
    return body


@router.get("/{simulationId}/kpis", response_model=KpiResponse, responses=_ERRORS, summary="Simulation KPIs with units and provenance")
def get_kpis(simulationId: str, response: Response, container: Container = Depends(get_container)) -> dict:
    body = container.results.kpis(simulationId)
    _cache_completed(response, container.simulations.get(simulationId))
    return body


@router.get("/{simulationId}/diagnostics", response_model=DiagnosticsResponse, responses=_ERRORS, summary="SWMM model diagnostics")
def get_diagnostics(simulationId: str, response: Response, container: Container = Depends(get_container)) -> dict:
    body = container.results.diagnostics(simulationId)
    _cache_completed(response, container.simulations.get(simulationId))
    return body
