"""Element time series read directly from a simulation's SWMM binary output.

Only variables that SWMM 5.2 actually writes (and whose CMS units are
unambiguous) are exposed.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any

from app.core.errors import ErrorCode, NotFoundError
from app.gis.network_mapping import NetworkMapping
from app.repositories.results import WorkspaceStore
from app.simulation.output_reader import SwmmOutput, read_output
from app.utils.timeutil import to_iso_z

NODE_VARIABLES = {
    "depth": ("depthM", "m", "Water depth above node invert (in-network; not ground flood depth)."),
    "head": ("headM", "m", "Hydraulic head (node invert elevation + depth), model elevation datum."),
    "lateral_inflow": ("lateralInflowCms", "m3/s", "Runoff and other lateral inflow."),
    "total_inflow": ("totalInflowCms", "m3/s", "Lateral plus upstream inflow."),
    "flooding": ("floodingCms", "m3/s", "Overflow rate lost from the node (ponding disabled)."),
}
LINK_VARIABLES = {
    "flow": ("flowCms", "m3/s", "Conduit flow rate (negative = against link direction)."),
    "depth": ("depthM", "m", "Average water depth in the conduit."),
    "velocity": ("velocityMps", "m/s", "Flow velocity."),
    "capacity": ("capacity", "fraction", "Ratio of water depth to full conduit depth (0-1)."),
}
SYSTEM_VARIABLES = {
    "rainfall": ("rainfallMmHr", "mm/hr", "Rainfall intensity applied to the model."),
    "runoff": ("runoffCms", "m3/s", "Total surface runoff."),
    "total_lateral_inflow": ("totalLateralInflowCms", "m3/s", "Total lateral inflow to the drainage network."),
    "flooding": ("floodingCms", "m3/s", "Total node overflow rate."),
    "outfall_flow": ("outfallFlowCms", "m3/s", "Total flow leaving through provisional outfalls."),
    "storage_volume": ("storageVolumeM3", "m3", "Total water stored in the network."),
}


class TimeseriesService:
    def __init__(self, simulations: Any, workspaces: WorkspaceStore, mapping_loader: Any, cache_size: int = 2) -> None:
        self.simulations = simulations
        self.workspaces = workspaces
        self._mapping_loader = mapping_loader
        self._cache: OrderedDict[str, SwmmOutput] = OrderedDict()
        self._cache_size = cache_size
        self._lock = threading.Lock()

    def _output(self, simulation_id: str) -> tuple[Any, SwmmOutput]:
        record = self.simulations.ensure_completed(simulation_id)
        sid = record.simulation_id
        with self._lock:
            if sid in self._cache:
                self._cache.move_to_end(sid)
            else:
                self._cache[sid] = read_output(self.workspaces.path(sid) / "output.out")
                while len(self._cache) > self._cache_size:
                    self._cache.popitem(last=False)
            return record, self._cache[sid]

    @staticmethod
    def _base(record: Any, out: SwmmOutput) -> dict[str, Any]:
        return {
            "simulationId": record.simulation_id,
            "dataType": "model-derived",
            "timestamps": [to_iso_z(t) for t in out.times],
            "intervalMinutes": out.report_step_seconds // 60,
            "metadata": {"scenarioId": record.scenario_id, "modelVersion": record.model_version, "source": "SWMM binary output (reporting periods)"},
        }

    @staticmethod
    def _describe(spec: dict[str, tuple[str, str, str]]) -> dict[str, Any]:
        return {name: {"unit": unit, "description": desc} for (name, unit, desc) in spec.values()}

    def node(self, simulation_id: str, node_id: str) -> dict[str, Any]:
        record, out = self._output(simulation_id)
        if node_id not in out.node_ids:
            raise NotFoundError(ErrorCode.NOT_FOUND, "The requested model node does not exist in this simulation.", details={"nodeId": node_id}, simulation_id=record.simulation_id)
        i = out.node_ids.index(node_id)
        series = {name: [round(row[i], 6) for row in out.node_series(var)] for var, (name, _u, _d) in NODE_VARIABLES.items()}
        return {**self._base(record, out), "elementType": "NODE", "modelNodeId": node_id, "variables": self._describe(NODE_VARIABLES), "series": series}

    def link(self, simulation_id: str, link_id: str) -> dict[str, Any]:
        record, out = self._output(simulation_id)
        if link_id not in out.link_ids:
            raise NotFoundError(ErrorCode.NOT_FOUND, "The requested model link does not exist in this simulation.", details={"linkId": link_id}, simulation_id=record.simulation_id)
        i = out.link_ids.index(link_id)
        series = {name: [round(row[i], 6) for row in out.link_series(var)] for var, (name, _u, _d) in LINK_VARIABLES.items()}
        mapping: NetworkMapping = self._mapping_loader()
        return {
            **self._base(record, out),
            "elementType": "LINK",
            "modelLinkId": link_id,
            "sourceObjectId": mapping.link_to_object_id.get(link_id),
            "variables": self._describe(LINK_VARIABLES),
            "series": series,
        }

    def system(self, simulation_id: str) -> dict[str, Any]:
        record, out = self._output(simulation_id)
        series = {name: [round(v, 6) for v in out.system_series(var)] for var, (name, _u, _d) in SYSTEM_VARIABLES.items()}
        return {**self._base(record, out), "elementType": "SYSTEM", "variables": self._describe(SYSTEM_VARIABLES), "series": series}
