"""Reader for the SWMM 5.x binary output (``.out``) file.

Implements the documented SWMM 5 binary layout (opening records, object IDs,
object properties, reporting variables, per-period results, closing records)
without third-party dependencies. The reader validates the magic numbers,
error code and file size against the declared period count, so a truncated or
failed output file is rejected rather than partially read.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.utils.timeutil import from_swmm_datetime

MAGIC = 516114522
_INT = struct.Struct("<i")
_REC = 4

# Variable indices for the SWMM 5.2 fixed (non-pollutant) reporting variables.
SUBCATCH_VARS = ["rainfall", "snow_depth", "evap_loss", "infil_loss", "runoff", "gw_flow", "gw_elev", "soil_moisture"]
NODE_VARS = ["depth", "head", "volume", "lateral_inflow", "total_inflow", "flooding"]
LINK_VARS = ["flow", "depth", "velocity", "volume", "capacity"]
SYSTEM_VARS = [
    "air_temp",
    "rainfall",
    "snow_depth",
    "infil_loss",
    "runoff",
    "dry_weather_inflow",
    "gw_inflow",
    "rdii_inflow",
    "external_inflow",
    "total_lateral_inflow",
    "flooding",
    "outfall_flow",
    "storage_volume",
    "evaporation",
    "pet",
]

FLOW_UNITS = ["CFS", "GPM", "MGD", "CMS", "LPS", "MLD"]


class OutputFormatError(ValueError):
    pass


@dataclass
class SwmmOutput:
    version: int
    flow_units: str
    subcatchment_ids: list[str]
    node_ids: list[str]
    link_ids: list[str]
    n_pollutants: int
    report_start: datetime
    report_step_seconds: int
    n_periods: int
    times: list[datetime]
    node_var_count: int
    link_var_count: int
    subcatch_var_count: int
    system_var_count: int
    _data: bytes
    _output_start: int

    @property
    def _period_bytes(self) -> int:
        n = (
            len(self.subcatchment_ids) * self.subcatch_var_count
            + len(self.node_ids) * self.node_var_count
            + len(self.link_ids) * self.link_var_count
            + self.system_var_count
        )
        return 8 + _REC * n

    def _floats(self, offset: int, count: int) -> tuple[float, ...]:
        return struct.unpack_from(f"<{count}f", self._data, offset)

    def _period_offset(self, period: int) -> int:
        return self._output_start + period * self._period_bytes + 8

    def node_series(self, variable: str) -> list[list[float]]:
        """Return [period][node] values for a node variable."""
        idx = NODE_VARS.index(variable)
        n_sub = len(self.subcatchment_ids) * self.subcatch_var_count
        n_nodes = len(self.node_ids)
        series = []
        for p in range(self.n_periods):
            base = self._period_offset(p) + _REC * n_sub
            values = self._floats(base, n_nodes * self.node_var_count)
            series.append([values[i * self.node_var_count + idx] for i in range(n_nodes)])
        return series

    def link_series(self, variable: str) -> list[list[float]]:
        idx = LINK_VARS.index(variable)
        n_before = len(self.subcatchment_ids) * self.subcatch_var_count + len(self.node_ids) * self.node_var_count
        n_links = len(self.link_ids)
        series = []
        for p in range(self.n_periods):
            base = self._period_offset(p) + _REC * n_before
            values = self._floats(base, n_links * self.link_var_count)
            series.append([values[i * self.link_var_count + idx] for i in range(n_links)])
        return series

    def system_series(self, variable: str) -> list[float]:
        idx = SYSTEM_VARS.index(variable)
        n_before = (
            len(self.subcatchment_ids) * self.subcatch_var_count
            + len(self.node_ids) * self.node_var_count
            + len(self.link_ids) * self.link_var_count
        )
        return [self._floats(self._period_offset(p) + _REC * n_before, self.system_var_count)[idx] for p in range(self.n_periods)]


def read_output(path: Path) -> SwmmOutput:
    data = path.read_bytes()
    if len(data) < 7 * _REC + 6 * _REC:
        raise OutputFormatError("SWMM output file is too small")

    def i32(offset: int) -> int:
        return _INT.unpack_from(data, offset)[0]

    magic_start = i32(0)
    version, flow_code, n_sub, n_nodes, n_links, n_poll = (i32(_REC * k) for k in range(1, 7))
    closing = len(data) - 6 * _REC
    id_pos, prop_pos, output_pos, n_periods, error_code, magic_end = (i32(closing + _REC * k) for k in range(6))

    if magic_start != MAGIC or magic_end != MAGIC:
        raise OutputFormatError("SWMM output file has invalid magic numbers (incomplete or corrupt run)")
    if error_code != 0:
        raise OutputFormatError(f"SWMM output file reports error code {error_code}")
    if n_periods <= 0:
        raise OutputFormatError("SWMM output file contains no reporting periods")
    if not 0 <= flow_code < len(FLOW_UNITS):
        raise OutputFormatError("Unknown flow units code in SWMM output file")

    pos = id_pos

    def read_ids(count: int) -> list[str]:
        nonlocal pos
        ids = []
        for _ in range(count):
            length = i32(pos)
            pos += _REC
            ids.append(data[pos : pos + length].decode("utf-8"))
            pos += length
        return ids

    sub_ids = read_ids(n_sub)
    node_ids = read_ids(n_nodes)
    link_ids = read_ids(n_links)

    # Reporting variable codes follow the object property blocks.
    pos = prop_pos
    n_sub_props = i32(pos)
    pos += _REC * (1 + n_sub_props) + _REC * n_sub_props * n_sub
    n_node_props = i32(pos)
    pos += _REC * (1 + n_node_props) + _REC * n_node_props * n_nodes
    n_link_props = i32(pos)
    pos += _REC * (1 + n_link_props) + _REC * n_link_props * n_links

    n_sub_vars = i32(pos)
    pos += _REC * (1 + n_sub_vars)
    n_node_vars = i32(pos)
    pos += _REC * (1 + n_node_vars)
    n_link_vars = i32(pos)
    pos += _REC * (1 + n_link_vars)
    n_sys_vars = i32(pos)
    pos += _REC * (1 + n_sys_vars)
    report_start_days = struct.unpack_from("<d", data, pos)[0]
    pos += 8
    report_step = i32(pos)
    pos += _REC

    if n_node_vars < len(NODE_VARS) or n_link_vars < len(LINK_VARS) or n_sys_vars < len(SYSTEM_VARS):
        raise OutputFormatError("SWMM output file has fewer reporting variables than expected for SWMM 5.2")
    if pos != output_pos:
        raise OutputFormatError("SWMM output file section offsets are inconsistent")

    period_bytes = 8 + _REC * (n_sub * n_sub_vars + n_nodes * n_node_vars + n_links * n_link_vars + n_sys_vars)
    if output_pos + period_bytes * n_periods != closing:
        raise OutputFormatError("SWMM output file size does not match the declared number of periods")

    times = [
        from_swmm_datetime(struct.unpack_from("<d", data, output_pos + p * period_bytes)[0]) for p in range(n_periods)
    ]

    return SwmmOutput(
        version=version,
        flow_units=FLOW_UNITS[flow_code],
        subcatchment_ids=sub_ids,
        node_ids=node_ids,
        link_ids=link_ids,
        n_pollutants=n_poll,
        report_start=from_swmm_datetime(report_start_days),
        report_step_seconds=report_step,
        n_periods=n_periods,
        times=times,
        node_var_count=n_node_vars,
        link_var_count=n_link_vars,
        subcatch_var_count=n_sub_vars,
        system_var_count=n_sys_vars,
        _data=data,
        _output_start=output_pos,
    )
