"""Precomputed demonstration result (backend/config/demo.json).

Loading the demo result never runs SWMM: the registered archived SWMM 5.2.4
report/output of the approved model are checksum-verified and processed by the
normal simulation pipeline (validation, result processing, flood and decision
products). A completed demo run is re-used on later loads, so repeated demos
need no manual runtime cleanup.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import ErrorCode, NotFoundError, ServiceUnavailableError
from app.models.simulation import ACTIVE_STATUSES, SimulationStatus
from app.repositories.registry import Registry
from app.repositories.results import ResultStore
from app.services.simulation_service import EXECUTION_PRECOMPUTED, SimulationService
from app.utils.files import sha256_file


class DemoService:
    def __init__(self, simulations: SimulationService, registry: Registry, results: ResultStore) -> None:
        self.simulations = simulations
        self.registry = registry
        self.results = results
        self._verified_files: set[str] = set()

    def _runs(self, demo_id: str) -> list[Any]:
        records = self.simulations.list(scenario_id=None, status=None, limit=500, offset=0)
        return [r for r in records if r.artifacts.get("executionMode") == EXECUTION_PRECOMPUTED and r.artifacts.get("demoId") == demo_id]

    def _files_ok(self, demo: Any) -> bool:
        ok = True
        for spec in (demo.report, demo.output):
            key = f"{spec['file']}|{spec['sha256']}"
            if key in self._verified_files:
                continue
            path = self.simulations.settings.models_dir / spec["file"]
            if path.is_file() and sha256_file(path) == spec["sha256"]:
                self._verified_files.add(key)
            else:
                ok = False
        return ok

    def _usable(self, record: Any) -> bool:
        return record.status == SimulationStatus.COMPLETED and self.results.exists(record.simulation_id, ResultStore.RESULTS)

    def catalogue(self) -> dict[str, Any]:
        items = []
        for demo in self.registry.demo_results.values():
            runs = self._runs(demo.demo_id)
            completed = next((r for r in runs if self._usable(r)), None)
            active = next((r for r in runs if r.status in ACTIVE_STATUSES), None)
            items.append(
                {
                    "demoId": demo.demo_id,
                    "label": demo.label,
                    "description": demo.description,
                    "scenarioId": demo.scenario_id,
                    "modelVersion": demo.model_version,
                    "rainfallMultiplier": 1.0,
                    "executionMode": EXECUTION_PRECOMPUTED,
                    "available": self._files_ok(demo),
                    "verification": demo.verification,
                    "loadedSimulationId": completed.simulation_id if completed else None,
                    "loadingSimulationId": active.simulation_id if active else None,
                }
            )
        return {"demoResults": items}

    def load(self, demo_id: str) -> dict[str, Any]:
        demo = self.registry.demo_results.get(demo_id)
        if demo is None:
            raise NotFoundError(ErrorCode.NOT_FOUND, "The requested demonstration result is not registered.", details={"demoId": demo_id})
        runs = self._runs(demo_id)
        completed = next((r for r in runs if self._usable(r)), None)
        if completed:
            return {"demoId": demo_id, "simulationId": completed.simulation_id, "status": completed.status.value, "reused": True}
        active = next((r for r in runs if r.status in ACTIVE_STATUSES), None)
        if active:
            return {"demoId": demo_id, "simulationId": active.simulation_id, "status": active.status.value, "reused": True}
        if not self._files_ok(demo):
            raise ServiceUnavailableError(ErrorCode.RESULT_NOT_FOUND, "The verified demonstration result files are missing or do not match their checksums.")
        record = self.simulations.create_precomputed(demo)
        return {"demoId": demo_id, "simulationId": record.simulation_id, "status": record.status.value, "reused": False}
