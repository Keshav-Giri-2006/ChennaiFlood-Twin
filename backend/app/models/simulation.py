"""Simulation domain model: explicit states, stages and allowed transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class SimulationStatus(StrEnum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    PREPARING = "PREPARING"
    RUNNING = "RUNNING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SimulationStage(StrEnum):
    QUEUED = "QUEUED"
    VALIDATION = "VALIDATION"
    WORKSPACE_PREPARATION = "WORKSPACE_PREPARATION"
    SWMM_EXECUTION = "SWMM_EXECUTION"
    RESULT_PROCESSING = "RESULT_PROCESSING"
    COMPLETE = "COMPLETE"


TERMINAL_STATUSES = frozenset({SimulationStatus.COMPLETED, SimulationStatus.FAILED})
ACTIVE_STATUSES = frozenset(set(SimulationStatus) - TERMINAL_STATUSES)

# Stage-based application progress (06_API_CONTRACT.md §22). These are
# lifecycle milestones, not a measure of simulated-time completion.
STATUS_PROGRESS: dict[SimulationStatus, int] = {
    SimulationStatus.CREATED: 0,
    SimulationStatus.VALIDATING: 10,
    SimulationStatus.PREPARING: 20,
    SimulationStatus.RUNNING: 30,
    SimulationStatus.PROCESSING: 75,
    SimulationStatus.COMPLETED: 100,
}

STATUS_STAGE: dict[SimulationStatus, SimulationStage] = {
    SimulationStatus.CREATED: SimulationStage.QUEUED,
    SimulationStatus.VALIDATING: SimulationStage.VALIDATION,
    SimulationStatus.PREPARING: SimulationStage.WORKSPACE_PREPARATION,
    SimulationStatus.RUNNING: SimulationStage.SWMM_EXECUTION,
    SimulationStatus.PROCESSING: SimulationStage.RESULT_PROCESSING,
    SimulationStatus.COMPLETED: SimulationStage.COMPLETE,
}

_ALLOWED: dict[SimulationStatus, frozenset[SimulationStatus]] = {
    SimulationStatus.CREATED: frozenset({SimulationStatus.VALIDATING, SimulationStatus.FAILED}),
    SimulationStatus.VALIDATING: frozenset({SimulationStatus.PREPARING, SimulationStatus.FAILED}),
    SimulationStatus.PREPARING: frozenset({SimulationStatus.RUNNING, SimulationStatus.FAILED}),
    SimulationStatus.RUNNING: frozenset({SimulationStatus.PROCESSING, SimulationStatus.FAILED}),
    SimulationStatus.PROCESSING: frozenset({SimulationStatus.COMPLETED, SimulationStatus.FAILED}),
    SimulationStatus.COMPLETED: frozenset(),
    SimulationStatus.FAILED: frozenset(),
}


class InvalidTransitionError(RuntimeError):
    pass


def ensure_transition(current: SimulationStatus, target: SimulationStatus) -> None:
    if target not in _ALLOWED[current]:
        raise InvalidTransitionError(f"Illegal simulation status transition {current} -> {target}")


@dataclass
class SimulationError:
    code: str
    message: str
    details: Any = None


@dataclass
class SimulationRecord:
    simulation_id: str
    scenario_id: str
    model_version: str
    processing_version: str
    application_version: str
    status: SimulationStatus
    stage: SimulationStage
    progress: int
    parameters: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: SimulationError | None = None
    model_sha256: str | None = None
    rainfall_sha256: str | None = None
    engine_version: str | None = None
    swmm_exit_code: int | None = None
    swmm_elapsed_seconds: float | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES
