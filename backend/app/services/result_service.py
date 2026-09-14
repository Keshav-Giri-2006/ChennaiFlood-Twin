"""Application-level result views built from persisted, parsed SWMM results.

Nothing here recomputes hydraulics; values are read from ``results.json``
produced during the PROCESSING stage. Products that the pipeline does not yet
generate (spatial flood depth/extent, affected assets, risk, bottlenecks) are
returned as ``null`` with an explicit availability flag, never as zero.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import ErrorCode, NotFoundError
from app.gis.network_mapping import NetworkMapping
from app.models.simulation import SimulationRecord
from app.repositories.registry import Registry
from app.repositories.results import ResultStore
from app.services.simulation_service import SimulationService

FLOOD_NOT_AVAILABLE_REASON = (
    "Not derived by flood-processing-v1: SWMM ran without surface ponding (no surface water depth in the output) and "
    "model rim elevations are not vertically consistent with the Copernicus DSM. See docs/FLOOD_PROCESSING_METHOD.md; "
    "node flooding states and influence zones are available via /flood."
)


def _q(value: float | int | None, unit: str, source: str, description: str, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"value": value, "unit": unit, "source": source, "description": description}
    item.update(extra)
    return item


def _unavailable(unit: str, description: str) -> dict[str, Any]:
    return {"value": None, "unit": unit, "source": "model-derived", "description": description, "available": False, "reason": FLOOD_NOT_AVAILABLE_REASON, "methodVersion": None}


class ResultService:
    def __init__(self, simulations: SimulationService, results: ResultStore, registry: Registry, mapping_loader: Any, flood: Any = None, decision: Any = None) -> None:
        self.flood = flood
        self.decision = decision
        self.simulations = simulations
        self.results = results
        self.registry = registry
        self._mapping_loader = mapping_loader

    def _load(self, simulation_id: str) -> tuple[SimulationRecord, dict[str, Any]]:
        record = self.simulations.ensure_completed(simulation_id)
        if not self.results.exists(record.simulation_id, ResultStore.RESULTS):
            raise NotFoundError(ErrorCode.RESULT_NOT_FOUND, "Stored results for this simulation are missing.", simulation_id=record.simulation_id)
        return record, self.results.read(record.simulation_id, ResultStore.RESULTS)

    def _metadata(self, record: SimulationRecord, results: dict[str, Any]) -> dict[str, Any]:
        return {
            "scenarioId": record.scenario_id,
            "modelVersion": record.model_version,
            "processingVersion": record.processing_version,
            "engine": results["engine"],
            "simulationPeriod": results["simulationPeriod"],
            "executionMode": record.artifacts.get("executionMode", "swmm"),
            "parameters": record.parameters,
            "rainfallMultiplier": float(record.parameters.get("rainfallMultiplier", 1.0)),
            "scenarioRun": record.artifacts.get("scenarioRun"),
        }

    def _limitations(self, record: SimulationRecord) -> list[str]:
        model = self.registry.models[record.model_version]
        scenario = self.registry.scenarios[record.scenario_id]
        return [*model.limitations, *scenario.limitations]

    def _flood_metrics(self, simulation_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
        if self.flood is None:
            return None
        summary = self.flood.summary(simulation_id)
        return summary, summary["metrics"]

    def _flood_summary_block(self, simulation_id: str) -> dict[str, Any]:
        block: dict[str, Any] = {"maximumDepthM": None, "affectedAreaM2": None, "available": False, "reason": FLOOD_NOT_AVAILABLE_REASON}
        loaded = self._flood_metrics(simulation_id)
        if loaded:
            summary, metrics = loaded
            block.update(
                {
                    "nodeFloodingAvailable": True,
                    "floodProcessingVersion": summary["metadata"]["floodProcessingVersion"],
                    "peakTime": summary["peakTime"],
                    "peakConcurrentFloodingNodes": metrics["peakConcurrentFloodingNodes"]["value"],
                    "floodingDurationHr": metrics["floodingDuration"]["value"],
                    "representation": summary["representation"],
                }
            )
        return block

    def _flood_kpis(self, simulation_id: str) -> dict[str, Any]:
        loaded = self._flood_metrics(simulation_id)
        if not loaded:
            return {}
        summary, metrics = loaded
        version = summary["metadata"]["floodProcessingVersion"]
        return {
            name: {**metrics[name], "methodVersion": version}
            for name in ("peakConcurrentFloodingNodes", "floodingDuration", "firstFloodingTime", "maximumNodeWaterDepth")
        }

    def _bottleneck_summary(self, simulation_id: str) -> dict[str, Any]:
        if self.decision is None:
            return {"potentialBottlenecks": None, "potentialBottlenecksAvailable": False}
        doc = self.decision.bottlenecks(simulation_id)
        return {
            "potentialBottlenecks": doc["summary"]["potentialBottlenecks"],
            "potentialBottlenecksAvailable": True,
            "potentialBottlenecksBySeverity": doc["summary"]["bySeverity"],
            "bottleneckAnalysisVersion": doc["bottleneckAnalysisVersion"],
        }

    def _bottleneck_kpi(self, simulation_id: str) -> dict[str, Any]:
        if self.decision is None:
            return {"value": None, "unit": "count", "source": "model-derived", "description": "Potential drainage bottlenecks.", "available": False, "reason": "Bottleneck analysis is not configured.", "methodVersion": None}
        doc = self.decision.bottlenecks(simulation_id)
        return _q(
            doc["summary"]["potentialBottlenecks"], "count", "model-derived",
            "Conduits meeting at least one SWMM hydraulic-loading criterion (potential bottlenecks, not confirmed failures).",
            methodVersion=doc["bottleneckAnalysisVersion"], bySeverity=doc["summary"]["bySeverity"],
        )

    def _exposure_kpis(self, simulation_id: str) -> dict[str, Any]:
        if self.decision is None:
            return {}
        e = self.decision.exposure(simulation_id)
        v = e["exposureAnalysisVersion"]
        note = "Intersecting flood influence zones of overflowing model nodes (model-derived exposure; not flooded or damaged)."
        return {
            "exposure": {
                "buildingsInInfluenceZonesEvent": _q(e["event"]["buildings"]["intersectingCount"], "count", "model-derived", f"Buildings {note} Any reporting timestamp.", methodVersion=v, total=e["totals"]["buildings"]["count"]),
                "buildingsInInfluenceZonesPeak": _q(e["peak"]["buildings"]["intersectingCount"], "count", "model-derived", f"Buildings {note} At the peak flooding timestamp.", methodVersion=v, time=e["peak"]["time"], total=e["totals"]["buildings"]["count"]),
                "roadAreaInInfluenceZonesEvent": _q(e["event"]["roads"]["areaWithinZonesM2"], "m2", "model-derived", f"Carriageway area {note} Any reporting timestamp.", methodVersion=v),
            }
        }

    def summary(self, simulation_id: str) -> dict[str, Any]:
        record, r = self._load(simulation_id)
        scenario = self.registry.scenarios[record.scenario_id]
        routing = r["routingContinuity"]
        return {
            "simulationId": record.simulation_id,
            "scenario": {"scenarioId": scenario.scenario_id, "name": scenario.name},
            "model": {"version": record.model_version, "engine": r["engine"]["name"], "engineVersion": r["engine"]["version"]},
            "status": record.status.value,
            "rainfall": {"totalMm": r["rainfallInput"]["totalMm"], "peakMmHr": r["rainfallInput"]["peakIntensityMmHr"], "dataType": "source"},
            "flood": self._flood_summary_block(record.simulation_id),
            "drainage": {
                **self._bottleneck_summary(record.simulation_id),
                "floodedNodes": len(r["nodes"]["flooding"]),
                "surchargedNodes": len(r["nodes"]["surcharge"]),
                "totalNodes": r["nodes"]["count"],
                "dataType": "model-derived",
            },
            "hydraulics": {
                "dataType": "model-derived",
                "simulatedFloodingVolumeL": routing["simulatedFloodingVolumeL"],
                "wetWeatherInflowL": routing["wetWeatherInflowL"],
                "externalOutflowL": routing["externalOutflowL"],
                "finalStoredVolumeL": routing["finalStoredVolumeL"],
                "peakSystemFloodingRateCms": r["systemPeaks"]["systemFloodingRateCms"]["value"],
                "peakSystemFloodingTime": r["systemPeaks"]["systemFloodingRateCms"]["time"],
                "note": routing["note"],
            },
            "modelDiagnostics": {
                "runoffContinuityErrorPercent": r["runoffContinuity"]["continuityErrorPercent"],
                "routingContinuityErrorPercent": routing["continuityErrorPercent"],
                "warningCount": len(r["diagnostics"]["warnings"]),
                "nonConvergingStepsPercent": r["diagnostics"]["routingTimeStep"].get("% of Steps Not Converging"),
            },
            "createdAt": record.created_at,
            "completedAt": record.completed_at,
            "metadata": self._metadata(record, r),
            "limitations": self._limitations(record),
        }

    def kpis(self, simulation_id: str) -> dict[str, Any]:
        record, r = self._load(simulation_id)
        rain = r["rainfallInput"]
        runoff = r["runoffContinuity"]
        routing = r["routingContinuity"]
        peaks = r["systemPeaks"]
        mv = record.processing_version
        return {
            "simulationId": record.simulation_id,
            "rainfall": {
                "total": _q(rain["totalMm"], "mm", "source", "Event rainfall depth from the NASA GPM IMERG series."),
                "peakIntensity": _q(rain["peakIntensityMmHr"], "mm/hr", "source", "Highest 30-minute rainfall intensity.", time=rain["peakIntervalStart"]),
                "duration": _q(rain["records"] * rain["intervalMinutes"] / 60.0, "hr", "source", "Length of the rainfall record."),
            },
            "flood": {
                "maximumDepth": _unavailable("m", "Maximum simulated surface flood depth."),
                "affectedArea": _unavailable("m2", "Simulated flooded area."),
                "affectedBuildings": _unavailable("count", "Buildings intersecting the simulated flood extent."),
                **self._flood_kpis(record.simulation_id),
            },
            "hydraulics": {
                "simulatedFloodingVolume": _q(
                    routing["simulatedFloodingVolumeL"], "L", "model-derived",
                    "SWMM flooding loss (model-generated flooding diagnostic under the current incomplete network representation; not observed flood volume).",
                    methodVersion=mv,
                ),
                "wetWeatherInflow": _q(routing["wetWeatherInflowL"], "L", "model-derived", "Runoff volume entering the drainage network.", methodVersion=mv),
                "externalOutflow": _q(routing["externalOutflowL"], "L", "model-derived", "Volume leaving through provisional model outfalls.", methodVersion=mv),
                "finalStoredVolume": _q(routing["finalStoredVolumeL"], "L", "model-derived", "Water remaining in the network at the end of the simulation.", methodVersion=mv),
                "surfaceRunoffDepth": _q(runoff["surfaceRunoffMm"], "mm", "model-derived", "Area-weighted surface runoff depth over all subcatchments.", methodVersion=mv),
                "infiltrationLoss": _q(runoff["infiltrationLossMm"], "mm", "model-derived", "Area-weighted infiltration loss (Green-Ampt assumptions).", methodVersion=mv),
                "peakSystemFloodingRate": _q(peaks["systemFloodingRateCms"]["value"], "m3/s", "model-derived", "Peak total node overflow rate at a reporting time.", time=peaks["systemFloodingRateCms"]["time"], methodVersion=mv),
                "peakOutfallFlow": _q(peaks["outfallFlowCms"]["value"], "m3/s", "model-derived", "Peak total flow through provisional outfalls at a reporting time.", time=peaks["outfallFlowCms"]["time"], methodVersion=mv),
            },
            "drainage": {
                "floodedNodes": _q(len(r["nodes"]["flooding"]), "count", "model-derived", "Nodes listed in the SWMM Node Flooding Summary.", total=r["nodes"]["count"], methodVersion=mv),
                "surchargedNodes": _q(len(r["nodes"]["surcharge"]), "count", "model-derived", "Nodes listed in the SWMM Node Surcharge Summary.", total=r["nodes"]["count"], methodVersion=mv),
                "surchargedConduits": _q(len(r["links"]["conduitSurcharge"]), "count", "model-derived", "Conduits listed in the SWMM Conduit Surcharge Summary.", total=r["links"]["count"], methodVersion=mv),
                "potentialBottlenecks": self._bottleneck_kpi(record.simulation_id),
            },
            **self._exposure_kpis(record.simulation_id),
            "modelDiagnostics": {
                "runoffContinuityError": _q(runoff["continuityErrorPercent"], "%", "model-derived", "SWMM runoff quantity continuity error."),
                "routingContinuityError": _q(routing["continuityErrorPercent"], "%", "model-derived", "SWMM flow routing continuity error."),
                "nonConvergingSteps": _q(r["diagnostics"]["routingTimeStep"].get("% of Steps Not Converging"), "%", "model-derived", "Share of routing steps that did not converge."),
            },
            "metadata": self._metadata(record, r),
        }

    def diagnostics(self, simulation_id: str) -> dict[str, Any]:
        record, r = self._load(simulation_id)
        mapping: NetworkMapping = self._mapping_loader()

        def with_source(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            out = []
            for item in items:
                enriched = dict(item)
                if item.get("elementType") == "LINK" or item["id"] in mapping.link_to_object_id:
                    enriched["sourceObjectId"] = mapping.link_to_object_id.get(item["id"])
                out.append(enriched)
            return out

        d = r["diagnostics"]
        return {
            "simulationId": record.simulation_id,
            "dataType": "model-derived",
            "note": d["note"],
            "warnings": d["warnings"],
            "continuity": {
                "runoffErrorPercent": r["runoffContinuity"]["continuityErrorPercent"],
                "routingErrorPercent": r["routingContinuity"]["continuityErrorPercent"],
            },
            "routingTimeStep": d["routingTimeStep"],
            "highestContinuityErrors": d["highestContinuityErrors"],
            "timeStepCriticalElements": with_source(d["timeStepCriticalElements"]),
            "highestFlowInstabilityIndexes": with_source(d["highestFlowInstabilityIndexes"]),
            "nonconvergingNodes": d["nonconvergingNodes"],
            "floodedNodes": r["nodes"]["flooding"],
            "surchargedConduits": with_source(r["links"]["conduitSurcharge"]),
            "outfalls": r["outfalls"],
            "processingChecks": r["processingChecks"],
            "metadata": self._metadata(record, r),
        }

    def products(self, simulation_id: str) -> dict[str, Any]:
        record = self.simulations.get(simulation_id)
        done = record.status.value == "COMPLETED" and self.results.exists(record.simulation_id, ResultStore.RESULTS)
        return {
            "simulationId": record.simulation_id,
            "status": record.status.value,
            "products": {
                "summary": done,
                "kpis": done,
                "diagnostics": done,
                "hydraulicTimeseries": done and self.results.exists(record.simulation_id, ResultStore.TIMESERIES),
                "flood": done and self.flood is not None,
                "timeline": done and self.flood is not None,
                "risk": False,
                "bottlenecks": done and self.decision is not None,
                "exposure": done and self.decision is not None,
                "recommendations": done and self.decision is not None,
            },
        }
