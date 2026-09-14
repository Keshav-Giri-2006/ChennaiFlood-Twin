"""Scenario catalogue. Metadata is computed from the scenario's rainfall source file."""

from __future__ import annotations

import threading
from typing import Any

from app.core.config import Settings
from app.core.errors import ErrorCode, NotFoundError, ServiceUnavailableError
from app.repositories.registry import Registry, ScenarioDefinition
from app.simulation.rainfall import RainfallFormatError, RainfallSeries
from app.simulation.validator import load_rainfall, rainfall_path_for
from app.utils.timeutil import to_iso_z


def _bbox(text: str | None) -> list[float] | None:
    if not text:
        return None
    try:
        values = [float(v) for v in text.split(",")]
    except ValueError:
        return None
    return values if len(values) == 4 else None


class ScenarioService:
    def __init__(self, settings: Settings, registry: Registry) -> None:
        self._settings = settings
        self._registry = registry
        self._cache: dict[str, RainfallSeries] = {}
        self._lock = threading.Lock()

    def definition(self, scenario_id: str) -> ScenarioDefinition:
        scenario = self._registry.scenarios.get(scenario_id)
        if scenario is None:
            raise NotFoundError(ErrorCode.SCENARIO_NOT_FOUND, "The requested rainfall scenario does not exist.", details={"scenarioId": scenario_id})
        return scenario

    def rainfall(self, scenario_id: str) -> RainfallSeries:
        scenario = self.definition(scenario_id)
        with self._lock:
            if scenario_id not in self._cache:
                if not rainfall_path_for(scenario, self._settings.raw_dir).is_file():
                    raise ServiceUnavailableError(ErrorCode.RAINFALL_NOT_FOUND, "The scenario rainfall source data is not available.")
                try:
                    self._cache[scenario_id] = load_rainfall(scenario, self._settings.raw_dir)
                except RainfallFormatError as exc:
                    raise ServiceUnavailableError(ErrorCode.RAINFALL_VALIDATION_FAILED, "The scenario rainfall source data could not be read.") from exc
            return self._cache[scenario_id]

    def list_summaries(self) -> list[dict[str, Any]]:
        items = []
        for scenario in self._registry.scenarios.values():
            series = self.rainfall(scenario.scenario_id)
            items.append(
                {
                    "scenarioId": scenario.scenario_id,
                    "name": scenario.name,
                    "description": scenario.description,
                    "source": scenario.source["name"],
                    "rainfallType": scenario.rainfall_type,
                    "startTime": to_iso_z(series.start_time),
                    "endTime": to_iso_z(series.end_time),
                    "intervalMinutes": series.interval_minutes,
                    "totalRainfallMm": round(series.total_mm, 3),
                    "peakIntensityMmHr": round(series.peak_mm_hr, 3),
                }
            )
        return items

    def detail(self, scenario_id: str) -> dict[str, Any]:
        scenario = self.definition(scenario_id)
        series = self.rainfall(scenario_id)
        meta = series.metadata
        return {
            "scenarioId": scenario.scenario_id,
            "name": scenario.name,
            "event": scenario.event,
            "description": scenario.description,
            "rainfallType": scenario.rainfall_type,
            "dataType": "source",
            "source": {
                "name": scenario.source["name"],
                "variable": scenario.source["variable"],
                "retrieval": scenario.source.get("retrieval"),
                "title": meta.get("Title"),
            },
            "rainfall": {
                "type": scenario.rainfall["valueType"],
                "unit": scenario.rainfall["unit"],
                "intervalMinutes": series.interval_minutes,
                "records": len(series.times),
                "startTime": to_iso_z(series.start_time),
                "endTime": to_iso_z(series.end_time),
                "coverageEndTime": to_iso_z(series.coverage_end_time),
                "timeBasis": scenario.rainfall["timeBasis"],
                "timestampConvention": scenario.rainfall["timestampConvention"],
                "totalMm": round(series.total_mm, 3),
                "peakMmHr": round(series.peak_mm_hr, 3),
                "peakIntervalStart": to_iso_z(series.peak_time),
                "dailyTotalsMm": {day: round(v, 3) for day, v in series.daily_totals_mm().items()},
            },
            "spatial": {
                "representation": "area-averaged satellite precipitation estimate",
                "requestedBoundingBox": _bbox(meta.get("User Bounding Box")),
                "dataBoundingBox": _bbox(meta.get("Data Bounding Box")),
                "bboxOrder": "minLon,minLat,maxLon,maxLat (EPSG:4326)",
            },
            "compatibleModelVersions": sorted(scenario.compatible_models),
            "whatIf": (
                {**scenario.what_if, "scenarioAnalysisVersion": self._settings.scenario_analysis_version, "terminology": "What-if rainfall sensitivity scenario (not a forecast, warning or climate projection)."}
                if scenario.what_if
                else None
            ),
            "provenance": {
                "file": rainfall_path_for(scenario, self._settings.raw_dir).name,
                "sha256": scenario.rainfall["sha256"],
            },
            "limitations": scenario.limitations,
        }

    def rainfall_series(self, scenario_id: str) -> dict[str, Any]:
        scenario = self.definition(scenario_id)
        series = self.rainfall(scenario_id)
        hours = series.interval_hours
        return {
            "scenarioId": scenario.scenario_id,
            "dataType": "source",
            "source": scenario.source["name"],
            "unit": "mm/hr",
            "intervalMinutes": series.interval_minutes,
            "timeBasis": scenario.rainfall["timeBasis"],
            "timestampConvention": scenario.rainfall["timestampConvention"],
            "records": [
                {"time": to_iso_z(t), "intensityMmHr": round(v, 6), "depthMm": round(v * hours, 6)}
                for t, v in zip(series.times, series.intensities_mm_hr, strict=True)
            ],
        }
