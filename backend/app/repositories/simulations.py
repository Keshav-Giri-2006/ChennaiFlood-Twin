"""Simulation metadata repository (SQLAlchemy Core)."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, insert, select, update
from sqlalchemy.engine import Engine, RowMapping

from app.models.simulation import (
    ACTIVE_STATUSES,
    SimulationError,
    SimulationRecord,
    SimulationStage,
    SimulationStatus,
    ensure_transition,
)
from app.repositories.database import simulations_table as t
from app.utils.timeutil import utcnow


def _aware(value: datetime | None) -> datetime | None:
    # SQLite drops tzinfo; all stored timestamps are UTC.
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _to_record(row: RowMapping) -> SimulationRecord:
    error = None
    if row["error_code"]:
        error = SimulationError(row["error_code"], row["error_message"] or "", row["error_details"])
    return SimulationRecord(
        simulation_id=row["simulation_id"],
        scenario_id=row["scenario_id"],
        model_version=row["model_version"],
        processing_version=row["processing_version"],
        application_version=row["application_version"],
        status=SimulationStatus(row["status"]),
        stage=SimulationStage(row["stage"]),
        progress=row["progress"],
        parameters=row["parameters"] or {},
        created_at=_aware(row["created_at"]),  # type: ignore[arg-type]
        updated_at=_aware(row["updated_at"]),  # type: ignore[arg-type]
        started_at=_aware(row["started_at"]),
        completed_at=_aware(row["completed_at"]),
        error=error,
        model_sha256=row["model_sha256"],
        rainfall_sha256=row["rainfall_sha256"],
        engine_version=row["engine_version"],
        swmm_exit_code=row["swmm_exit_code"],
        swmm_elapsed_seconds=row["swmm_elapsed_seconds"],
        artifacts=row["artifacts"] or {},
    )


class SimulationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._lock = threading.Lock()

    def add(self, record: SimulationRecord) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                insert(t).values(
                    simulation_id=record.simulation_id,
                    scenario_id=record.scenario_id,
                    model_version=record.model_version,
                    processing_version=record.processing_version,
                    application_version=record.application_version,
                    status=record.status.value,
                    stage=record.stage.value,
                    progress=record.progress,
                    parameters=record.parameters,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    artifacts=record.artifacts,
                )
            )

    def get(self, simulation_id: str) -> SimulationRecord | None:
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.simulation_id == simulation_id)).mappings().first()
        return _to_record(row) if row else None

    def list(self, *, scenario_id: str | None = None, status: SimulationStatus | None = None, limit: int = 50, offset: int = 0) -> list[SimulationRecord]:
        query = select(t).order_by(desc(t.c.created_at)).limit(limit).offset(offset)
        if scenario_id:
            query = query.where(t.c.scenario_id == scenario_id)
        if status:
            query = query.where(t.c.status == status.value)
        with self._engine.connect() as conn:
            return [_to_record(r) for r in conn.execute(query).mappings().all()]

    def transition(
        self,
        simulation_id: str,
        target: SimulationStatus,
        *,
        stage: SimulationStage,
        progress: int,
        **fields: Any,
    ) -> SimulationRecord:
        """Apply a validated status transition atomically."""
        with self._lock, self._engine.begin() as conn:
            row = conn.execute(select(t.c.status).where(t.c.simulation_id == simulation_id)).first()
            if row is None:
                raise KeyError(simulation_id)
            ensure_transition(SimulationStatus(row[0]), target)
            values: dict[str, Any] = {"status": target.value, "stage": stage.value, "progress": progress, "updated_at": utcnow()}
            values.update(fields)
            conn.execute(update(t).where(t.c.simulation_id == simulation_id).values(**values))
        record = self.get(simulation_id)
        assert record is not None
        return record

    def update_fields(self, simulation_id: str, **fields: Any) -> None:
        """Update non-status metadata (artifact references, engine facts)."""
        forbidden = {"status", "stage", "progress"} & fields.keys()
        if forbidden:
            raise ValueError(f"Use transition() to change {forbidden}")
        with self._lock, self._engine.begin() as conn:
            conn.execute(update(t).where(t.c.simulation_id == simulation_id).values(updated_at=utcnow(), **fields))

    def active_ids(self) -> list[str]:
        with self._engine.connect() as conn:
            rows = conn.execute(select(t.c.simulation_id).where(t.c.status.in_([s.value for s in ACTIVE_STATUSES]))).all()
        return [r[0] for r in rows]
