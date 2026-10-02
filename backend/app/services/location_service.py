"""Location Flood Check (location-check-v1): spatial query over a completed simulation.

Reuses the existing pipeline outputs only: the simulation must be COMPLETED and
its flood products valid (FloodService); node states are computed from the same
SWMM binary output with the same flood-processing-v1 definitions, and the
influence zones are the flood-processing-v1 zones. No SWMM run happens here.
"""

from __future__ import annotations

import threading
from typing import Any

from app.analysis.flood_processing import FloodProcessingError, NodeStates, compute_node_states, influence_zones
from app.analysis.location_check import LocationOutsideStudyAreaError, analyse_location
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode, UnprocessableError
from app.gis.network_mapping import load_network_mapping
from app.gis.transform import UTM44N, lonlat_to, transform_xy
from app.repositories.registry import Registry
from app.repositories.results import WorkspaceStore
from app.simulation.inp_reader import read_inp
from app.simulation.output_reader import read_output

LIMITATIONS = [
    "Model-derived result for the selected historical rainfall scenario. It is not an observation, a property assessment, a flood certification or a prediction for any property.",
    "Drainage nodes are associated with the surrounding area through nearest-node influence zones (flood-processing-v1). Zones are spatial associations, not flood extents.",
    "Ground flood depth and flood extent are not derived: SWMM ran without surface ponding, so overflow leaves the model. Node water depth is an in-network value, not a ground depth.",
    "The drainage network representation is incomplete and some outfalls are provisional; overflow rates and volumes are simulation diagnostics.",
    "Only the part of the surrounding area inside Ward 176 is analysed; the model holds no data outside the ward.",
    "States are evaluated at the SWMM reporting timestamps; short overflows between reporting times may not be listed.",
]


class _Context:
    def __init__(self, states: NodeStates, zones: dict[str, Any], node_xy: dict[str, tuple[float, float]], node_lonlat: dict[str, tuple[float, float]]) -> None:
        self.states = states
        self.zones = zones
        self.node_xy = node_xy
        self.node_lonlat = node_lonlat


class LocationService:
    def __init__(self, settings: Settings, registry: Registry, workspaces: WorkspaceStore, flood: Any, decision: Any) -> None:
        self.settings = settings
        self.registry = registry
        self.workspaces = workspaces
        self.flood = flood
        self.decision = decision
        self._contexts: dict[tuple[str, str], _Context] = {}
        self._lock = threading.Lock()

    def _context(self, record: Any, output_sha: str) -> _Context:
        key = (record.simulation_id, output_sha)
        with self._lock:
            cached = self._contexts.get(key)
            if cached is not None:
                return cached
            workspace = self.workspaces.path(record.simulation_id)
            inp = read_inp(workspace / "input.inp")
            files = self.registry.models[record.model_version].network_mapping
            network = load_network_mapping(inp, self.settings.processed_dir / files["conduitsCsv"], self.settings.processed_dir / files["nodesCsv"])
            node_ids = inp.node_ids
            node_xy = {n: (network.node_locations[n].easting_m, network.node_locations[n].northing_m) for n in node_ids}
            lons, lats = transform_xy(UTM44N, [node_xy[n][0] for n in node_ids], [node_xy[n][1] for n in node_ids])
            context = _Context(
                states=compute_node_states(read_output(workspace / "output.out"), inp),
                zones=influence_zones(node_ids, network, self.flood.store.ward_utm()),
                node_xy=node_xy,
                node_lonlat={n: (x, y) for n, x, y in zip(node_ids, lons, lats, strict=True)},
            )
            self._contexts[key] = context
            return context

    def _bottlenecks(self, simulation_id: str) -> list[dict[str, Any]] | None:
        # Graceful degradation: the flood response is still valid if decision products are unavailable.
        try:
            return self.decision.bottlenecks(simulation_id)["bottlenecks"]
        except AppError:
            return None

    def check(self, simulation_id: str, latitude: float, longitude: float, radius_m: float) -> dict[str, Any]:
        record, manifest = self.flood.products(simulation_id)
        try:
            context = self._context(record, manifest["inputs"]["outputSha256"])
        except (FloodProcessingError, KeyError, ValueError) as exc:
            raise AppError(ErrorCode.PROCESSING_FAILED, "The location flood check could not be computed for this simulation.", status_code=500, simulation_id=record.simulation_id) from exc
        try:
            result = analyse_location(
                latitude=latitude,
                longitude=longitude,
                point_utm=lonlat_to(UTM44N, longitude, latitude),
                radius_m=radius_m,
                ward_utm=self.flood.store.ward_utm(),
                zones_utm=context.zones,
                node_xy=context.node_xy,
                node_lonlat=context.node_lonlat,
                states=context.states,
                interval_minutes=int(manifest["summary"]["intervalMinutes"]),
                bottlenecks=self._bottlenecks(record.simulation_id),
                processing_crs=UTM44N,
            )
        except LocationOutsideStudyAreaError as exc:
            raise UnprocessableError(
                ErrorCode.LOCATION_OUTSIDE_STUDY_AREA,
                "The selected location is outside Ward 176, the study area of the hydraulic model.",
                details={"latitude": latitude, "longitude": longitude},
                simulation_id=record.simulation_id,
            ) from exc
        summary = manifest["summary"]
        return {
            "simulationId": record.simulation_id,
            "scenarioId": record.scenario_id,
            "modelVersion": record.model_version,
            "rainfallMultiplier": float((record.parameters or {}).get("rainfallMultiplier", 1.0)),
            "locationCheckVersion": self.settings.location_check_version,
            "floodProcessingVersion": manifest["floodProcessingVersion"],
            "dataType": "model-derived",
            "terminology": "Location-specific historical flood analysis using the model-derived response around a user-selected point.",
            **result,
            "groundFloodDepthM": None,
            "floodExtentAvailable": False,
            "notDerived": summary.get("notDerived", {}),
            "timeConvention": "SWMM reporting timestamps (UTC).",
            "method": {
                "version": self.settings.location_check_version,
                "stateDefinitions": manifest["floodProcessingVersion"],
                "association": "Nodes whose nearest-node influence zones overlap the surrounding area (circle of radiusMeters around the location, clipped to Ward 176).",
                "processingCrs": UTM44N,
                "document": "docs/LOCATION_CHECK_METHOD.md",
            },
            "limitations": LIMITATIONS,
        }
