"""Request/response schemas for 06_API_CONTRACT.md (field names follow the contract)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.models.simulation import SimulationStage, SimulationStatus
from app.schemas.common import ApiModel, IsoDateTime, OpenModel, Quantity


# --- health ---------------------------------------------------------------------
class HealthResponse(ApiModel):
    status: Literal["ok"]
    service: str
    version: str


class ReadinessResponse(ApiModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, Literal["ok", "error"]]
    details: dict[str, str] | None = None


# --- scenarios --------------------------------------------------------------------
class ScenarioListItem(ApiModel):
    scenarioId: str
    name: str
    description: str
    source: str
    rainfallType: str
    startTime: str
    endTime: str
    intervalMinutes: int
    totalRainfallMm: float
    peakIntensityMmHr: float


class ScenarioListResponse(ApiModel):
    scenarios: list[ScenarioListItem]


class ScenarioSource(OpenModel):
    name: str
    variable: str


class ScenarioRainfall(OpenModel):
    type: str
    unit: str
    intervalMinutes: int
    totalMm: float
    peakMmHr: float
    startTime: str
    endTime: str
    dailyTotalsMm: dict[str, float]


class ScenarioDetail(OpenModel):
    scenarioId: str
    name: str
    description: str
    source: ScenarioSource
    rainfall: ScenarioRainfall
    limitations: list[str]


class RainfallRecord(ApiModel):
    time: str
    intensityMmHr: float
    depthMm: float


class RainfallSeriesResponse(OpenModel):
    scenarioId: str
    unit: str
    intervalMinutes: int
    records: list[RainfallRecord]


# --- simulations -------------------------------------------------------------------
class CreateSimulationRequest(ApiModel):
    scenarioId: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9-]*$")
    modelVersion: str | None = Field(default=None, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9.-]*$")
    parameters: dict[str, Any] | None = None


class SimulationErrorModel(ApiModel):
    code: str
    message: str
    details: Any = None


class SimulationCreatedResponse(ApiModel):
    simulationId: str
    scenarioId: str
    modelVersion: str
    status: SimulationStatus
    createdAt: IsoDateTime


class SimulationStatusResponse(ApiModel):
    simulationId: str
    scenarioId: str
    modelVersion: str
    processingVersion: str
    applicationVersion: str
    status: SimulationStatus
    stage: SimulationStage
    progress: int = Field(ge=0, le=100)
    progressBasis: Literal["stage"] = "stage"
    createdAt: IsoDateTime
    startedAt: IsoDateTime | None
    completedAt: IsoDateTime | None
    error: SimulationErrorModel | None
    parameters: dict[str, Any] = Field(default_factory=dict)
    executionMode: Literal["swmm", "precomputed-demo"] = "swmm"
    demoId: str | None = None
    scenarioRun: dict[str, Any] | None = None


class SimulationListResponse(ApiModel):
    simulations: list[SimulationStatusResponse]
    limit: int
    offset: int


class ResultProductsResponse(ApiModel):
    simulationId: str
    status: SimulationStatus
    products: dict[str, bool]


# --- results ------------------------------------------------------------------------
class SummaryResponse(OpenModel):
    simulationId: str
    scenario: dict[str, str]
    model: dict[str, Any]
    status: SimulationStatus
    rainfall: dict[str, Any]
    flood: dict[str, Any]
    drainage: dict[str, Any]
    hydraulics: dict[str, Any]
    modelDiagnostics: dict[str, Any]
    createdAt: IsoDateTime
    completedAt: IsoDateTime | None
    metadata: dict[str, Any]
    limitations: list[str]


class KpiResponse(OpenModel):
    simulationId: str
    rainfall: dict[str, Quantity]
    flood: dict[str, Quantity]
    hydraulics: dict[str, Quantity]
    drainage: dict[str, Quantity]
    modelDiagnostics: dict[str, Quantity]
    metadata: dict[str, Any]


class DiagnosticsResponse(OpenModel):
    simulationId: str
    dataType: str
    warnings: list[dict[str, Any]]
    continuity: dict[str, float]
    routingTimeStep: dict[str, float]
    metadata: dict[str, Any]


class FloodSummaryResponse(OpenModel):
    simulationId: str
    available: bool
    maximumDepthM: None
    peakTime: str
    extentAvailable: bool
    depthAvailable: bool
    influenceZonesAvailable: bool
    metrics: dict[str, Quantity]
    legend: dict[str, Any]
    metadata: dict[str, Any]


class FloodTimelineEntry(OpenModel):
    index: int
    time: str
    key: str
    hasFlooding: bool
    floodingNodeCount: int
    surchargedNodeCount: int
    systemFloodingRateCms: float
    asset: dict[str, str]


class FloodTimelineResponse(OpenModel):
    simulationId: str
    intervalMinutes: int
    timestamps: list[str]
    peakIndex: int
    entries: list[FloodTimelineEntry]
    legend: dict[str, Any]
    metadata: dict[str, Any]


class FloodTimesliceResponse(OpenModel):
    simulationId: str
    time: str
    index: int
    flood: dict[str, Any]
    influence: dict[str, Any]
    asset: dict[str, str]
    metadata: dict[str, Any]


class TimeseriesResponse(OpenModel):
    simulationId: str
    elementType: Literal["NODE", "LINK", "SYSTEM"]
    timestamps: list[str]
    intervalMinutes: int
    variables: dict[str, dict[str, str]]
    series: dict[str, list[float]]


class BottleneckRecord(OpenModel):
    linkId: str
    sourceObjectId: int
    fromNodeId: str
    toNodeId: str
    severity: Literal["HIGH", "MODERATE", "LOW"]
    score: float
    confidence: Literal["MEDIUM", "LOW"]
    criteria: list[dict[str, Any]]
    hydraulics: dict[str, Any]
    connectedNodes: list[dict[str, Any]]
    networkContext: dict[str, Any]
    explanation: dict[str, Any]


class BottleneckListResponse(OpenModel):
    simulationId: str
    bottleneckAnalysisVersion: str
    dataType: str
    summary: dict[str, Any]
    bottlenecks: list[BottleneckRecord]
    numericalDiagnostics: list[dict[str, Any]]
    limitations: list[str]


class BottleneckDetailResponse(BottleneckRecord):
    relatedRecommendationIds: list[str]
    metadata: dict[str, Any]


class ExposureResponse(OpenModel):
    simulationId: str
    exposureAnalysisVersion: str
    floodProcessingVersion: str
    dataType: str
    terminology: str
    totals: dict[str, Any]
    event: dict[str, Any]
    peak: dict[str, Any]
    timeline: list[dict[str, Any]]
    byNode: list[dict[str, Any]]
    limitations: list[str]


class ExposureAssetsResponse(OpenModel):
    simulationId: str
    assetType: Literal["buildings", "roads"]
    scope: Literal["event", "timestamp"]
    time: str | None
    count: int
    objectIds: list[int]
    assets: list[dict[str, Any]]
    metadata: dict[str, Any]


class RecommendationRecord(OpenModel):
    id: str
    rule: str
    category: str
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    confidence: Literal["MEDIUM", "LOW"]
    title: str
    recommendation: str
    why: str
    evidence: dict[str, Any]
    drivers: list[str]
    disclaimer: str


class RecommendationListResponse(OpenModel):
    simulationId: str
    decisionSupportVersion: str
    dataType: str
    disclaimer: str
    rules: dict[str, str]
    summary: dict[str, Any]
    recommendations: list[RecommendationRecord]


class GisLayerInfo(ApiModel):
    layer: str
    title: str
    dataType: str
    description: str
    url: str


class GisCatalogueResponse(ApiModel):
    layers: list[GisLayerInfo]
