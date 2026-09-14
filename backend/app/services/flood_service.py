"""Flood products: generation, caching and API views.

Artifacts live in ``RESULTS_DIR/<simulationId>/flood/``::

    manifest.json        processing version, input checksum, legend, summary
    timeline.json        one entry per SWMM reporting timestamp
    zones.geojson        nearest-node influence zones (all nodes)
    diagnostics.json     validation checks and statistics
    timeslices/<key>.geojson

Products are regenerated only if the flood processing version or the SWMM
binary output checksum changes (same inputs + same version -> same result).
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
from datetime import UTC
from pathlib import Path
from typing import Any

from shapely.geometry import shape

from app.analysis.flood_processing import FloodProcessingError, generate_flood_products, parse_time_query, timestamp_key
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode, NotFoundError, UnprocessableError
from app.core.logging import log_event
from app.gis.network_mapping import load_network_mapping
from app.gis.transform import UTM44N, declared_crs
from app.repositories.registry import Registry
from app.repositories.results import ResultStore, WorkspaceStore, validate_simulation_id
from app.simulation.inp_reader import read_inp
from app.simulation.output_reader import read_output
from app.simulation.report_parser import parse_report
from app.utils.files import read_json, sha256_file, write_json_atomic
from app.utils.timeutil import utcnow

logger = logging.getLogger("app.flood")

FLOOD_DIR = "flood"


class FloodProductStore:
    def __init__(self, settings: Settings, registry: Registry, workspaces: WorkspaceStore, results: ResultStore) -> None:
        self.settings = settings
        self.registry = registry
        self.workspaces = workspaces
        self.results = results
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self._verified: dict[str, dict[str, Any]] = {}

    @property
    def version(self) -> str:
        return self.settings.flood_processing_version

    def directory(self, simulation_id: str) -> Path:
        return self.results.root / validate_simulation_id(simulation_id) / FLOOD_DIR

    def _lock(self, simulation_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(simulation_id, threading.Lock())

    def _ward_utm(self):  # type: ignore[no-untyped-def]
        collection = read_json(self.settings.processed_dir / "gis" / "ward176_boundary.geojson")
        if declared_crs(collection) != UTM44N:
            raise FloodProcessingError("Ward boundary is not in EPSG:32644 as expected")
        geoms = [shape(f["geometry"]) for f in collection["features"]]
        if len(geoms) != 1:
            raise FloodProcessingError("Expected exactly one Ward 176 boundary feature")
        return geoms[0]

    def ward_utm(self):  # type: ignore[no-untyped-def]
        return self._ward_utm()

    def ensure(self, simulation_id: str, scenario_id: str, model_version: str) -> dict[str, Any]:
        """Return a valid manifest, generating products when missing or stale."""
        sid = validate_simulation_id(simulation_id)
        with self._lock(sid):
            if sid in self._verified:
                return self._verified[sid]
            workspace = self.workspaces.path(sid)
            output_file = workspace / "output.out"
            if not output_file.is_file():
                raise FloodProcessingError("SWMM binary output is missing for this simulation")
            output_sha = sha256_file(output_file)
            directory = self.directory(sid)
            manifest_path = directory / "manifest.json"
            if manifest_path.is_file():
                manifest = read_json(manifest_path)
                if manifest.get("floodProcessingVersion") == self.version and manifest.get("inputs", {}).get("outputSha256") == output_sha:
                    self._verified[sid] = manifest
                    return manifest
            manifest = self._generate(sid, scenario_id, model_version, workspace, output_sha)
            self._verified[sid] = manifest
            return manifest

    def _generate(self, sid: str, scenario_id: str, model_version: str, workspace: Path, output_sha: str) -> dict[str, Any]:
        model = self.registry.models[model_version]
        inp = read_inp(workspace / "input.inp")
        files = model.network_mapping
        network = load_network_mapping(inp, self.settings.processed_dir / files["conduitsCsv"], self.settings.processed_dir / files["nodesCsv"])
        products = generate_flood_products(
            simulation_id=sid,
            scenario_id=scenario_id,
            model_version=model_version,
            flood_processing_version=self.version,
            output=read_output(workspace / "output.out"),
            report=parse_report(workspace / "report.rpt"),
            inp=inp,
            network=network,
            ward_utm=self._ward_utm(),
            generated_at=utcnow(),
        )
        directory = self.directory(sid)
        staging = directory.with_name(f"{FLOOD_DIR}.staging")
        if staging.exists():
            shutil.rmtree(staging)
        (staging / "timeslices").mkdir(parents=True)
        for key, fc in products.timeslices.items():
            write_json_atomic(staging / "timeslices" / f"{key}.geojson", fc)
        write_json_atomic(staging / "timeline.json", products.timeline)
        write_json_atomic(staging / "zones.geojson", products.zones)
        write_json_atomic(staging / "diagnostics.json", products.diagnostics)
        manifest = {**products.manifest, "inputs": {"outputSha256": output_sha, "networkNodes": files["nodesCsv"], "wardBoundary": "gis/ward176_boundary.geojson"}}
        write_json_atomic(staging / "manifest.json", manifest)
        # Swap in atomically-ish: old products are removed only after the new set is complete.
        if directory.exists():
            shutil.rmtree(directory)
        staging.rename(directory)
        log_event(logger, "flood.generated", simulation_id=sid, version=self.version, periods=manifest["reportingPeriods"])
        return manifest


class FloodService:
    def __init__(self, simulations: Any, store: FloodProductStore) -> None:
        self.simulations = simulations
        self.store = store
        self._timeline_cache: dict[str, dict[str, Any]] = {}

    def _manifest(self, simulation_id: str) -> tuple[Any, dict[str, Any]]:
        record = self.simulations.ensure_completed(simulation_id)
        try:
            manifest = self.store.ensure(record.simulation_id, record.scenario_id, record.model_version)
        except FloodProcessingError as exc:
            raise AppError(ErrorCode.PROCESSING_FAILED, "Flood products could not be generated for this simulation.", status_code=500, details={"reason": str(exc)}, simulation_id=record.simulation_id) from exc
        return record, manifest

    def _timeline(self, record: Any) -> dict[str, Any]:
        sid = record.simulation_id
        if sid not in self._timeline_cache:
            self._timeline_cache[sid] = read_json(self.store.directory(sid) / "timeline.json")
        return self._timeline_cache[sid]

    def summary(self, simulation_id: str) -> dict[str, Any]:
        record, manifest = self._manifest(simulation_id)
        diagnostics = read_json(self.store.directory(record.simulation_id) / "diagnostics.json")
        return {
            "simulationId": record.simulation_id,
            **manifest["summary"],
            "maximumDepthM": None,
            "representation": manifest["representation"],
            "legend": manifest["legend"],
            "metadata": {k: manifest[k] for k in ("scenarioId", "modelVersion", "floodProcessingVersion", "dataType", "crs", "method", "generatedAt")},
            "validation": [{"check": c["check"], "passed": c["passed"], "hard": c["hard"], "details": c["details"]} for c in diagnostics["checks"]],
        }

    def timeline(self, simulation_id: str) -> dict[str, Any]:
        record, manifest = self._manifest(simulation_id)
        tl = self._timeline(record)
        base = f"/api/v1/simulations/{record.simulation_id}/flood/timeslices"
        return {
            "simulationId": record.simulation_id,
            "intervalMinutes": tl["intervalMinutes"],
            "timeConvention": tl["timeConvention"],
            "timestamps": [e["time"] for e in tl["entries"]],
            "peakIndex": tl["peakIndex"],
            "entries": [{**e, "asset": {"type": "geojson", "url": f"{base}/{e['key']}"}} for e in tl["entries"]],
            "legend": tl["legend"],
            "metadata": {k: manifest[k] for k in ("scenarioId", "modelVersion", "floodProcessingVersion", "dataType", "method")},
        }

    def _entry_for_time(self, record: Any, time_text: str) -> dict[str, Any]:
        try:
            parsed = parse_time_query(time_text)
        except ValueError as exc:
            raise UnprocessableError("INVALID_TIMESTAMP", "The time parameter must be an ISO 8601 timestamp with a UTC offset, e.g. 2023-12-03T22:00:00Z.", details={"time": time_text}) from exc
        key = timestamp_key(parsed.astimezone(UTC))
        entries = self._timeline(record)["entries"]
        match = next((e for e in entries if e["key"] == key), None)
        if match is None:
            raise NotFoundError(
                "TIMESTAMP_NOT_FOUND",
                "The requested time is not a reporting timestamp of this simulation.",
                details={"time": time_text, "firstTime": entries[0]["time"], "lastTime": entries[-1]["time"], "intervalMinutes": self._timeline(record)["intervalMinutes"]},
                simulation_id=record.simulation_id,
            )
        return match

    def timeslice(self, simulation_id: str, time_text: str) -> dict[str, Any]:
        record, manifest = self._manifest(simulation_id)
        entry = self._entry_for_time(record, time_text)
        fc = read_json(self.store.directory(record.simulation_id) / "timeslices" / f"{entry['key']}.geojson")
        return {
            "simulationId": record.simulation_id,
            "time": entry["time"],
            "index": entry["index"],
            "flood": {k: v for k, v in entry.items() if k not in ("index", "time", "key")},
            "influence": fc,
            "asset": {"type": "geojson", "url": f"/api/v1/simulations/{record.simulation_id}/flood/timeslices/{entry['key']}"},
            "metadata": {k: manifest[k] for k in ("floodProcessingVersion", "dataType", "representation", "method")},
        }

    def timeslice_path(self, simulation_id: str, key: str) -> Path:
        record, _manifest = self._manifest(simulation_id)
        entries = self._timeline(record)["entries"]
        if not any(e["key"] == key for e in entries):
            raise NotFoundError("TIMESTAMP_NOT_FOUND", "The requested time slice does not exist for this simulation.", details={"key": key}, simulation_id=record.simulation_id)
        return self.store.directory(record.simulation_id) / "timeslices" / f"{key}.geojson"

    def zones_path(self, simulation_id: str) -> Path:
        record, _manifest = self._manifest(simulation_id)
        return self.store.directory(record.simulation_id) / "zones.geojson"

    def etag(self, simulation_id: str) -> str:
        _record, manifest = self._manifest(simulation_id)
        return json.dumps([manifest["floodProcessingVersion"], manifest["inputs"]["outputSha256"]])

