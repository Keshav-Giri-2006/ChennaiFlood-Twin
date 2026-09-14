"""Scenario comparison service (scenario-analysis-v1) with per-pair caching.

Cached at ``RESULTS_DIR/<scenarioSimulationId>/comparisons/<baselineSimulationId>.json`` and
re-used only when the scenario-analysis version and both runs' decision-product manifests
(method versions + SWMM output checksums) are unchanged.
"""

from __future__ import annotations

import threading
from typing import Any

from app.analysis.scenario_comparison import ComparisonError, compare_runs
from app.core.config import Settings
from app.core.errors import UnprocessableError
from app.repositories.results import ResultStore, validate_simulation_id
from app.utils.files import read_json, write_json_atomic
from app.utils.timeutil import utcnow


class ComparisonService:
    def __init__(self, settings: Settings, simulations: Any, results: ResultStore, result_service: Any, flood: Any, decision: Any) -> None:
        self.settings = settings
        self.simulations = simulations
        self.results = results
        self.result_service = result_service
        self.flood = flood
        self.decision = decision
        self._lock = threading.Lock()

    def _bundle(self, simulation_id: str) -> dict[str, Any]:
        record = self.simulations.ensure_completed(simulation_id)
        sid = record.simulation_id
        manifest = self.decision.store.ensure(sid, record.scenario_id, record.model_version)
        return {
            "run": {
                "simulationId": sid,
                "scenarioId": record.scenario_id,
                "modelVersion": record.model_version,
                "processingVersion": record.processing_version,
                "rainfallMultiplier": float(record.parameters.get("rainfallMultiplier", 1.0)),
                "executionMode": record.artifacts.get("executionMode", "swmm"),
                "completedAt": record.completed_at.isoformat() if record.completed_at else None,
                "transformedModelSha256": (record.artifacts.get("scenarioRun") or {}).get("transformedModelSha256"),
            },
            "manifest": manifest,
            "kpis": self.result_service.kpis(sid),
            "flood": self.flood.summary(sid),
            "results": self.results.read(sid, ResultStore.RESULTS),
            "bottlenecks": self.decision.bottlenecks(sid),
            "exposure": self.decision.exposure(sid),
            "assets": self.decision._load(sid, "exposure_assets.json")[2],
            "recommendations": self.decision.recommendations(sid),
        }

    def compare(self, baseline_id: str, scenario_id: str) -> dict[str, Any]:
        baseline = self._bundle(baseline_id)
        scenario = self._bundle(scenario_id)
        key = {
            "scenarioAnalysisVersion": self.settings.scenario_analysis_version,
            "baseline": [baseline["run"]["simulationId"], baseline["manifest"]["versions"], baseline["manifest"]["inputs"]["outputSha256"]],
            "scenario": [scenario["run"]["simulationId"], scenario["manifest"]["versions"], scenario["manifest"]["inputs"]["outputSha256"]],
        }
        path = self.results.root / validate_simulation_id(scenario["run"]["simulationId"]) / "comparisons" / f"{validate_simulation_id(baseline['run']['simulationId'])}.json"
        with self._lock:
            if path.is_file():
                cached = read_json(path)
                if cached.get("cacheKey") == key:
                    return cached["comparison"]
            try:
                comparison = compare_runs(baseline, scenario, self.settings.scenario_analysis_version, utcnow())
            except ComparisonError as exc:
                raise UnprocessableError("COMPARISON_NOT_COMPATIBLE", str(exc), details=exc.details) from exc
            write_json_atomic(path, {"cacheKey": key, "comparison": comparison})
            return comparison
