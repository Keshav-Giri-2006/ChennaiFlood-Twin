"""Decision-support products: potential bottlenecks, model-derived exposure, recommendations.

Artifacts live in ``RESULTS_DIR/<simulationId>/decision/``::

    manifest.json            versions + input checksums
    bottlenecks.json         bottleneck-analysis-v1 evidence records + numerical diagnostics
    bottlenecks.geojson      conduit geometry of potential bottlenecks (lon/lat)
    exposure.json            exposure-analysis-v1 summary, timeline, per-node exposure
    exposure_assets.json     per-node building/road ObjectID associations (for asset queries)
    recommendations.json     decision-support-v1 recommendations

Products depend on the flood products (influence zones, flooding states), so
they are regenerated when the SWMM output checksum or any of the flood,
bottleneck, exposure or decision-support versions change.
"""

from __future__ import annotations

import csv
import logging
import shutil
import threading
from datetime import UTC
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.validation import make_valid

from app.analysis.bottleneck_analysis import BottleneckAnalysisError, analyse_bottlenecks, network_components
from app.analysis.exposure_analysis import Asset, ExposureAnalysisError, analyse_exposure
from app.analysis.flood_processing import FloodProcessingError, influence_zones, parse_time_query, timestamp_key
from app.analysis.recommendations import generate_recommendations
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode, NotFoundError, UnprocessableError
from app.core.logging import log_event
from app.gis.network_mapping import load_network_mapping
from app.gis.transform import UTM44N, declared_crs
from app.gis.web_assets import WebAssetBuilder
from app.repositories.registry import Registry
from app.repositories.results import ResultStore, WorkspaceStore, validate_simulation_id
from app.services.flood_service import FloodProductStore
from app.simulation.inp_reader import read_inp
from app.simulation.report_parser import parse_report
from app.utils.files import read_json, sha256_file, write_json_atomic
from app.utils.timeutil import utcnow

logger = logging.getLogger("app.decision")

DECISION_DIR = "decision"


class DecisionProcessingError(Exception):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.details = details


class DecisionProductStore:
    def __init__(self, settings: Settings, registry: Registry, workspaces: WorkspaceStore, results: ResultStore, flood: FloodProductStore, builder: WebAssetBuilder) -> None:
        self.settings = settings
        self.registry = registry
        self.workspaces = workspaces
        self.results = results
        self.flood = flood
        self.builder = builder
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()
        self._verified: dict[str, dict[str, Any]] = {}

    @property
    def versions(self) -> dict[str, str]:
        return {
            "floodProcessingVersion": self.settings.flood_processing_version,
            "bottleneckAnalysisVersion": self.settings.bottleneck_analysis_version,
            "exposureAnalysisVersion": self.settings.exposure_analysis_version,
            "decisionSupportVersion": self.settings.decision_support_version,
        }

    def directory(self, simulation_id: str) -> Path:
        return self.results.root / validate_simulation_id(simulation_id) / DECISION_DIR

    def _lock(self, sid: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(sid, threading.Lock())

    def ensure(self, simulation_id: str, scenario_id: str, model_version: str) -> dict[str, Any]:
        sid = validate_simulation_id(simulation_id)
        flood_manifest = self.flood.ensure(sid, scenario_id, model_version)
        with self._lock(sid):
            if sid in self._verified:
                return self._verified[sid]
            output_sha = flood_manifest["inputs"]["outputSha256"]
            manifest_path = self.directory(sid) / "manifest.json"
            if manifest_path.is_file():
                manifest = read_json(manifest_path)
                if manifest.get("versions") == self.versions and manifest.get("inputs", {}).get("outputSha256") == output_sha:
                    self._verified[sid] = manifest
                    return manifest
            try:
                manifest = self._generate(sid, scenario_id, model_version, output_sha, flood_manifest)
            except (BottleneckAnalysisError, ExposureAnalysisError, FloodProcessingError, KeyError, ValueError) as exc:
                raise DecisionProcessingError(f"Decision-support processing failed: {exc}") from exc
            self._verified[sid] = manifest
            return manifest

    # -- inputs -------------------------------------------------------------------------------
    def _utm_assets(self, relative: str, name_field: str | None = None) -> list[Asset]:
        collection = read_json(self.settings.processed_dir / relative)
        if declared_crs(collection) != UTM44N:
            raise DecisionProcessingError(f"{relative} is not in EPSG:32644 as expected")
        assets = []
        for f in collection["features"]:
            geom = shape(f["geometry"])
            if not geom.is_valid:
                geom = make_valid(geom)  # documented: repairs self-intersections without moving vertices
            assets.append(Asset(int(f["properties"]["objectid"]), geom, (f["properties"].get(name_field) or None) if name_field else None))
        return assets

    def _generate(self, sid: str, scenario_id: str, model_version: str, output_sha: str, flood_manifest: dict[str, Any]) -> dict[str, Any]:
        model = self.registry.models[model_version]
        workspace = self.workspaces.path(sid)
        inp = read_inp(workspace / "input.inp")
        report = parse_report(workspace / "report.rpt")
        files = model.network_mapping
        conduits_csv = self.settings.processed_dir / files["conduitsCsv"]
        network = load_network_mapping(inp, conduits_csv, self.settings.processed_dir / files["nodesCsv"])
        with conduits_csv.open("r", encoding="utf-8", newline="") as handle:
            source_conduits = {row["recon_conduit_id"]: row for row in csv.DictReader(handle)}
        with (self.settings.processed_dir / files["invertDecisionsCsv"]).open("r", encoding="utf-8", newline="") as handle:
            invert_decisions = {int(row["objectid"]): row["decision"] for row in csv.DictReader(handle)}
        drains = read_json(self.builder.get("drains")[0])
        conduit_fc = read_json(self.builder.get("model-conduits")[0])
        nodes_fc = read_json(self.builder.get("model-nodes")[0])
        source_drains = read_json(self.settings.processed_dir / "gis" / "ward176_storm_water_drains.geojson")
        obstacles: dict[int, str | None] = {}
        for f in source_drains["features"]:
            value = str(f["properties"].get("obstacles") or "").strip()
            obstacles[int(f["properties"]["objectid"])] = None if value.upper() in ("", "NA", "NONE") else value
        del drains  # built to guarantee the drains layer (and its identifier mapping) is consistent
        components = network_components(inp)
        generated_at = utcnow()
        common = {"simulation_id": sid, "scenario_id": scenario_id, "model_version": model_version, "generated_at": generated_at}

        bottlenecks, bottleneck_geojson = analyse_bottlenecks(
            **common,
            analysis_version=self.settings.bottleneck_analysis_version,
            report=report,
            inp=inp,
            network=network,
            components=components,
            source_conduits=source_conduits,
            invert_decisions=invert_decisions,
            diagnostic_context=model.diagnostic_context,
            conduit_geometry={f["id"]: f["geometry"] for f in conduit_fc["features"]},
            node_lonlat={f["id"]: f["geometry"]["coordinates"] for f in nodes_fc["features"]},
        )

        flood_dir = self.flood.directory(sid)
        timeline = read_json(flood_dir / "timeline.json")
        periods: list[list[str]] = []
        for entry in timeline["entries"]:
            fc = read_json(flood_dir / "timeslices" / f"{entry['key']}.geojson")
            nodes = sorted(f["properties"]["nodeId"] for f in fc["features"] if f["properties"]["featureType"] == "node" and f["properties"]["state"] == "FLOODING")
            if len(nodes) != entry["floodingNodeCount"]:
                raise DecisionProcessingError(f"Flood time slice {entry['key']} is inconsistent with the timeline")
            periods.append(nodes)
        exposure, associations = analyse_exposure(
            **common,
            analysis_version=self.settings.exposure_analysis_version,
            flood_processing_version=flood_manifest["floodProcessingVersion"],
            zones_utm=influence_zones(inp.node_ids, network, self.flood.ward_utm()),
            times=[e["time"] for e in timeline["entries"]],
            flooding_nodes_by_period=periods,
            peak_index=timeline["peakIndex"],
            interval_minutes=timeline["intervalMinutes"],
            buildings=self._utm_assets("gis/ward176_buildings.geojson"),
            roads=self._utm_assets("gis/ward176_carriageways.geojson", "road_name"),
            node_component=components.node_component,
            component_has_outfall={c["modelComponentId"]: bool(c["outfalls"]) for c in components.components},
        )
        recommendations = generate_recommendations(
            **common,
            decision_version=self.settings.decision_support_version,
            bottlenecks=bottlenecks,
            exposure=exposure,
            report=report,
            inp=inp,
            network=network,
            components=components,
            source_conduits=source_conduits,
            drain_obstacles=obstacles,
        )

        directory = self.directory(sid)
        staging = directory.with_name(f"{DECISION_DIR}.staging")
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        write_json_atomic(staging / "bottlenecks.json", bottlenecks)
        write_json_atomic(staging / "bottlenecks.geojson", bottleneck_geojson)
        write_json_atomic(staging / "exposure.json", exposure)
        write_json_atomic(staging / "exposure_assets.json", associations)
        write_json_atomic(staging / "recommendations.json", recommendations)
        manifest = {
            "simulationId": sid,
            "scenarioId": scenario_id,
            "modelVersion": model_version,
            "versions": self.versions,
            "generatedAt": bottlenecks["generatedAt"],
            "inputs": {
                "outputSha256": output_sha,
                "reportSha256": sha256_file(workspace / "report.rpt"),
                "buildings": "gis/ward176_buildings.geojson",
                "roads": "gis/ward176_carriageways.geojson",
                "networkConduits": files["conduitsCsv"],
                "invertDecisions": files["invertDecisionsCsv"],
            },
            "summary": {
                "potentialBottlenecks": bottlenecks["summary"],
                "exposureEvent": exposure["event"],
                "recommendations": recommendations["summary"],
            },
        }
        write_json_atomic(staging / "manifest.json", manifest)
        if directory.exists():
            shutil.rmtree(directory)
        staging.rename(directory)
        log_event(logger, "decision.generated", simulation_id=sid, bottlenecks=len(bottlenecks["bottlenecks"]), recommendations=recommendations["summary"]["total"])
        return manifest


class DecisionService:
    def __init__(self, simulations: Any, store: DecisionProductStore, flood: Any) -> None:
        self.simulations = simulations
        self.store = store
        self.flood = flood
        self._cache: dict[tuple[str, str], Any] = {}
        self._cache_lock = threading.Lock()

    def _load(self, simulation_id: str, name: str) -> tuple[Any, dict[str, Any], Any]:
        record = self.simulations.ensure_completed(simulation_id)
        try:
            manifest = self.store.ensure(record.simulation_id, record.scenario_id, record.model_version)
        except DecisionProcessingError as exc:
            raise AppError(ErrorCode.PROCESSING_FAILED, "Decision-support products could not be generated for this simulation.", status_code=500, details={"reason": str(exc)}, simulation_id=record.simulation_id) from exc
        key = (record.simulation_id, name)
        with self._cache_lock:
            cached = self._cache.get(key)
            if cached is None or cached[0] != manifest["generatedAt"]:
                cached = (manifest["generatedAt"], read_json(self.store.directory(record.simulation_id) / name))
                self._cache[key] = cached
        return record, manifest, cached[1]

    def etag(self, simulation_id: str) -> str:
        record = self.simulations.ensure_completed(simulation_id)
        manifest = self.store.ensure(record.simulation_id, record.scenario_id, record.model_version)
        return f"{manifest['versions']}|{manifest['inputs']['outputSha256']}"

    # -- bottlenecks ---------------------------------------------------------------------------
    def bottlenecks(self, simulation_id: str, severity: str | None = None) -> dict[str, Any]:
        _record, _manifest, doc = self._load(simulation_id, "bottlenecks.json")
        if severity is None:
            return doc
        return {**doc, "bottlenecks": [b for b in doc["bottlenecks"] if b["severity"] == severity], "filter": {"severity": severity}}

    def bottleneck(self, simulation_id: str, link_id: str) -> dict[str, Any]:
        record, _manifest, doc = self._load(simulation_id, "bottlenecks.json")
        match = next((b for b in doc["bottlenecks"] if b["linkId"] == link_id), None)
        if match is None:
            numerical = next((n for n in doc["numericalDiagnostics"] if n["linkId"] == link_id), None)
            raise NotFoundError(
                "BOTTLENECK_NOT_FOUND",
                "The link is not a potential bottleneck under the bottleneck analysis criteria for this simulation.",
                details={"linkId": link_id, "numericalDiagnostic": numerical},
                simulation_id=record.simulation_id,
            )
        _r, _m, recs = self._load(simulation_id, "recommendations.json")
        related = [r["id"] for r in recs["recommendations"] if link_id in r["relatedBottleneckLinkIds"] or any(l["linkId"] == link_id for l in r["evidence"]["links"])]
        meta = {k: doc[k] for k in ("simulationId", "scenarioId", "modelVersion", "bottleneckAnalysisVersion", "dataType", "method", "generatedAt")}
        return {**match, "relatedRecommendationIds": related, "metadata": meta, "terminology": doc["terminology"]}

    def bottlenecks_geojson_path(self, simulation_id: str) -> Path:
        record, _manifest, _doc = self._load(simulation_id, "bottlenecks.json")
        return self.store.directory(record.simulation_id) / "bottlenecks.geojson"

    # -- exposure ------------------------------------------------------------------------------
    def exposure(self, simulation_id: str) -> dict[str, Any]:
        return self._load(simulation_id, "exposure.json")[2]

    def exposure_assets(self, simulation_id: str, asset_type: str, time_text: str | None) -> dict[str, Any]:
        record, _manifest, assoc = self._load(simulation_id, "exposure_assets.json")
        if time_text is None:
            nodes = sorted({n for period in assoc["periods"] for n in period})
            scope: dict[str, Any] = {"scope": "event", "time": None, "index": None}
        else:
            try:
                parsed = parse_time_query(time_text)
            except ValueError as exc:
                raise UnprocessableError("INVALID_TIMESTAMP", "The time parameter must be an ISO 8601 timestamp with a UTC offset, e.g. 2023-12-03T22:00:00Z.", details={"time": time_text}) from exc
            key = timestamp_key(parsed.astimezone(UTC))
            index = next((i for i, t in enumerate(assoc["times"]) if timestamp_key(parse_time_query(t)) == key), None)
            if index is None:
                raise NotFoundError("TIMESTAMP_NOT_FOUND", "The requested time is not a reporting timestamp of this simulation.", details={"time": time_text, "firstTime": assoc["times"][0], "lastTime": assoc["times"][-1]}, simulation_id=record.simulation_id)
            nodes = assoc["periods"][index]
            scope = {"scope": "timestamp", "time": assoc["times"][index], "index": index}
        collected: dict[int, dict[str, Any]] = {}
        for n in nodes:
            for oid, area in assoc["nodes"][n][asset_type]:
                item = collected.setdefault(oid, {"objectId": oid, "areaWithinZonesM2": 0.0, "nodeIds": []})
                item["areaWithinZonesM2"] = round(item["areaWithinZonesM2"] + area, 2)
                item["nodeIds"].append(n)
        items = sorted(collected.values(), key=lambda x: x["objectId"])
        return {
            "simulationId": record.simulation_id,
            "assetType": asset_type,
            **scope,
            "floodingNodeIds": nodes,
            "count": len(items),
            "objectIds": [i["objectId"] for i in items],
            "assets": items,
            "terminology": "Assets spatially intersecting flood influence zones of overflowing model nodes (model-derived exposure; not flooded or damaged assets).",
            "metadata": {k: assoc[k] for k in ("scenarioId", "modelVersion", "exposureAnalysisVersion", "floodProcessingVersion", "dataType", "method", "generatedAt")},
        }

    # -- recommendations -------------------------------------------------------------------------
    def recommendations(self, simulation_id: str, priority: str | None = None) -> dict[str, Any]:
        doc = self._load(simulation_id, "recommendations.json")[2]
        if priority is None:
            return doc
        return {**doc, "recommendations": [r for r in doc["recommendations"] if r["priority"] == priority], "filter": {"priority": priority}}

    def overview(self, simulation_id: str) -> dict[str, Any]:
        record, manifest, _doc = self._load(simulation_id, "bottlenecks.json")
        return {"simulationId": record.simulation_id, **manifest}
