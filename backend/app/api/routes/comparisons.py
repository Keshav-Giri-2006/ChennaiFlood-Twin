from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from app.api.deps import get_container
from app.core.container import Container
from app.core.errors import UnprocessableError
from app.schemas.common import ApiModel, ErrorResponse

router = APIRouter(prefix="/comparisons", tags=["scenario-comparison"])

_ERRORS = {404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}
_ID = r"^[0-9a-fA-F-]{36}$"


class ComparisonRequest(ApiModel):
    simulationIds: list[str] = Field(min_length=2, max_length=2, description="[baselineSimulationId, scenarioSimulationId]")


@router.post("", responses=_ERRORS, summary="Compare two completed simulations (scenario-analysis-v1); first ID is the baseline")
def create_comparison(body: ComparisonRequest, container: Container = Depends(get_container)) -> dict:
    baseline, scenario = body.simulationIds
    if baseline == scenario:
        raise UnprocessableError("COMPARISON_NOT_COMPATIBLE", "A simulation cannot be compared with itself.")
    return container.comparisons.compare(baseline, scenario)


@router.get("", responses=_ERRORS, summary="Compare two completed simulations (cacheable GET form)")
def get_comparison(
    baseline: str = Query(..., pattern=_ID),
    scenario: str = Query(..., pattern=_ID),
    container: Container = Depends(get_container),
) -> dict:
    if baseline == scenario:
        raise UnprocessableError("COMPARISON_NOT_COMPATIBLE", "A simulation cannot be compared with itself.")
    return container.comparisons.compare(baseline, scenario)
