"""Structured parser for the SWMM 5.2 text report (``.rpt``).

The parser is strict: a value that cannot be parsed raises
``ReportParseError`` instead of being replaced with zero. It reads only; the
report file is never modified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.utils.timeutil import to_iso_z


class ReportParseError(ValueError):
    pass


_RULE = re.compile(r"^\s*-{5,}\s*$")
_DOTS_KV = re.compile(r"^\s*(?P<key>[A-Za-z0-9%/().\- ]+?)\s*\.{2,}\s*(?P<values>.+?)\s*$")
_ELEMENT_PCT = re.compile(r"^\s*(?P<type>Node|Link|Subcatchment)\s+(?P<id>\S+)\s+\((?P<value>-?[\d.]+)%?\)\s*$")
_WARNING = re.compile(r"^\s*WARNING\s+(?P<code>\d+):\s*(?P<text>.+?)\s*$")
_ERROR = re.compile(r"^\s*ERROR\s+(?P<code>\d+):\s*(?P<text>.+?)\s*$")
_TIMESTEP_KV = re.compile(r"^\s*(?P<key>[A-Za-z%. ]+?)\s*:\s*(?P<value>-?[\d.]+)\s*(?P<unit>sec)?\s*$")


def _f(value: str, context: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ReportParseError(f"Unparseable numeric value '{value}' in {context}") from exc


@dataclass
class SwmmReport:
    engine_version: str | None
    warnings: list[dict[str, str]]
    errors: list[dict[str, str]]
    element_count: dict[str, int]
    analysis_options: dict[str, str]
    runoff_continuity: dict[str, Any]
    routing_continuity: dict[str, Any]
    highest_continuity_errors: list[dict[str, Any]]
    time_step_critical_elements: list[dict[str, Any]]
    highest_flow_instability_indexes: list[dict[str, Any]]
    nonconverging_nodes: list[dict[str, Any]]
    routing_time_step: dict[str, float]
    subcatchment_runoff: list[dict[str, Any]]
    node_depth: list[dict[str, Any]]
    node_inflow: list[dict[str, Any]]
    node_surcharge: list[dict[str, Any]]
    node_flooding: list[dict[str, Any]]
    outfall_loading: list[dict[str, Any]]
    outfall_system: dict[str, Any] | None
    link_flow: list[dict[str, Any]]
    conduit_surcharge: list[dict[str, Any]]
    analysis_begun: str | None
    analysis_ended: str | None
    simulation_start: datetime | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        data = dict(self.__dict__)
        data["simulation_start"] = to_iso_z(self.simulation_start)
        return data


def _split_sections(lines: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """Split the report into its preamble and ``{section title: body lines}``."""
    preamble: list[str] = []
    sections: dict[str, list[str]] = {}
    i = 0
    current: str | None = None
    while i < len(lines):
        # Section titles sit between two star rules; continuity headers carry
        # extra column-label text on the same lines, so match on the prefix.
        if lines[i].strip().startswith("*****") and i + 2 < len(lines) and lines[i + 2].strip().startswith("*****"):
            title = re.split(r"\s{2,}", lines[i + 1].strip())[0]
            current = title
            sections[current] = []
            i += 3
            continue
        if current is None:
            preamble.append(lines[i])
        else:
            sections[current].append(lines[i])
        i += 1
    return preamble, sections


def _table_rows(body: list[str]) -> list[list[str]]:
    """Return tokenised data rows that follow the header block of a summary table."""
    dash_idx = [k for k, line in enumerate(body) if _RULE.match(line)]
    if len(dash_idx) < 2:
        return []
    rows: list[list[str]] = []
    for line in body[dash_idx[1] + 1 :]:
        if not line.strip() or _RULE.match(line):
            break
        rows.append(line.split())
    return rows


def _row_after_last_dash(body: list[str]) -> list[str] | None:
    dash_idx = [k for k, line in enumerate(body) if _RULE.match(line)]
    if len(dash_idx) < 3:
        return None
    for line in body[dash_idx[2] + 1 :]:
        if line.strip():
            return line.split()
    return None


def _event_time(start: datetime | None, days: str, hhmm: str, context: str) -> str | None:
    if start is None:
        return None
    try:
        hours, minutes = (int(x) for x in hhmm.split(":"))
        offset = timedelta(days=int(days), hours=hours, minutes=minutes)
    except ValueError as exc:
        raise ReportParseError(f"Unparseable time of occurrence '{days} {hhmm}' in {context}") from exc
    return to_iso_z(start + offset)


def _continuity(body: list[str], columns: tuple[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in body:
        m = _DOTS_KV.match(line)
        if not m:
            continue
        key = m.group("key").strip()
        values = m.group("values").split()
        if key.startswith("Continuity Error"):
            result["continuityErrorPercent"] = _f(values[0], key)
            continue
        if len(values) != 2:
            raise ReportParseError(f"Unexpected continuity row '{line.strip()}'")
        result[key] = {columns[0]: _f(values[0], key), columns[1]: _f(values[1], key)}
    return result


def _ranked_elements(body: list[str], percent: bool) -> list[dict[str, Any]]:
    items = []
    for line in body:
        m = _ELEMENT_PCT.match(line)
        if m:
            value = _f(m.group("value"), "ranked elements")
            items.append({"elementType": m.group("type").upper(), "id": m.group("id"), ("percent" if percent else "index"): value})
    return items


def parse_report(path: Path) -> SwmmReport:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    preamble, sections = _split_sections(lines)

    engine_version = None
    for line in preamble:
        m = re.search(r"VERSION\s+([\d.]+)\s+\(Build\s+([\d.]+)\)", line)
        if m:
            engine_version = m.group(2)
    warnings = [{"code": m.group("code"), "message": m.group("text")} for m in map(_WARNING.match, lines) if m]
    errors = [{"code": m.group("code"), "message": m.group("text")} for m in map(_ERROR.match, lines) if m]

    if errors:
        # A report with ERROR lines has no valid results; return minimal structure.
        return SwmmReport(engine_version, warnings, errors, {}, {}, {}, {}, [], [], [], [], {}, [], [], [], [], [], [], None, [], [], None, None)

    required = ["Element Count", "Analysis Options", "Runoff Quantity Continuity", "Flow Routing Continuity"]
    missing = [s for s in required if s not in sections]
    if missing:
        raise ReportParseError(f"Report is missing required sections: {missing}")

    element_count: dict[str, int] = {}
    for line in sections["Element Count"]:
        m = _DOTS_KV.match(line)
        if m:
            key = m.group("key").replace("Number of", "").strip()
            element_count[key] = int(_f(m.group("values"), "Element Count"))

    options: dict[str, str] = {}
    for line in sections["Analysis Options"]:
        m = _DOTS_KV.match(line)
        if m:
            options[m.group("key").strip()] = m.group("values").strip()

    sim_start = None
    if "Starting Date" in options:
        try:
            sim_start = datetime.strptime(options["Starting Date"], "%m/%d/%Y %H:%M:%S").replace(tzinfo=UTC)
        except ValueError as exc:
            raise ReportParseError("Unparseable Starting Date in Analysis Options") from exc

    runoff = _continuity(sections["Runoff Quantity Continuity"], ("volumeHectareM", "depthMm"))
    routing = _continuity(sections["Flow Routing Continuity"], ("volumeHectareM", "volumeMillionLiters"))

    timestep: dict[str, float] = {}
    for line in sections.get("Routing Time Step Summary", []):
        m = _TIMESTEP_KV.match(line)
        if m:
            timestep[m.group("key").strip()] = _f(m.group("value"), "Routing Time Step Summary")

    subcatch = []
    for t in _table_rows(sections.get("Subcatchment Runoff Summary", [])):
        if len(t) != 11:
            raise ReportParseError(f"Unexpected Subcatchment Runoff row: {t}")
        n = [_f(v, f"Subcatchment Runoff {t[0]}") for v in t[1:]]
        subcatch.append(
            {
                "id": t[0], "totalPrecipMm": n[0], "totalRunonMm": n[1], "totalEvapMm": n[2], "totalInfilMm": n[3],
                "impervRunoffMm": n[4], "pervRunoffMm": n[5], "totalRunoffMm": n[6],
                "totalRunoffMillionLiters": n[7], "peakRunoffCms": n[8], "runoffCoefficient": n[9],
            }
        )

    node_depth = []
    for t in _table_rows(sections.get("Node Depth Summary", [])):
        if len(t) != 8:
            raise ReportParseError(f"Unexpected Node Depth row: {t}")
        node_depth.append(
            {
                "id": t[0], "type": t[1], "averageDepthM": _f(t[2], t[0]), "maximumDepthM": _f(t[3], t[0]),
                "maximumHglM": _f(t[4], t[0]), "timeOfMaximum": _event_time(sim_start, t[5], t[6], "Node Depth"),
                "reportedMaximumDepthM": _f(t[7], t[0]),
            }
        )

    node_inflow = []
    for t in _table_rows(sections.get("Node Inflow Summary", [])):
        if t and t[-1] == "ltr":  # balance error expressed in litres instead of percent
            t = t[:-1]
            balance_unit = "L"
        else:
            balance_unit = "%"
        if len(t) != 9:
            raise ReportParseError(f"Unexpected Node Inflow row: {t}")
        node_inflow.append(
            {
                "id": t[0], "type": t[1], "maximumLateralInflowCms": _f(t[2], t[0]), "maximumTotalInflowCms": _f(t[3], t[0]),
                "timeOfMaximum": _event_time(sim_start, t[4], t[5], "Node Inflow"),
                "lateralInflowVolumeMillionLiters": _f(t[6], t[0]), "totalInflowVolumeMillionLiters": _f(t[7], t[0]),
                "flowBalanceError": {"value": _f(t[8], t[0]), "unit": balance_unit},
            }
        )

    node_surcharge = []
    for t in _table_rows(sections.get("Node Surcharge Summary", [])):
        if len(t) != 5:
            raise ReportParseError(f"Unexpected Node Surcharge row: {t}")
        node_surcharge.append(
            {"id": t[0], "type": t[1], "hoursSurcharged": _f(t[2], t[0]), "maxHeightAboveCrownM": _f(t[3], t[0]), "minDepthBelowRimM": _f(t[4], t[0])}
        )

    node_flooding = []
    for t in _table_rows(sections.get("Node Flooding Summary", [])):
        if len(t) != 7:
            raise ReportParseError(f"Unexpected Node Flooding row: {t}")
        node_flooding.append(
            {
                "id": t[0], "hoursFlooded": _f(t[1], t[0]), "maximumRateCms": _f(t[2], t[0]),
                "timeOfMaximum": _event_time(sim_start, t[3], t[4], "Node Flooding"),
                "totalFloodVolumeMillionLiters": _f(t[5], t[0]), "maximumPondedDepthM": _f(t[6], t[0]),
            }
        )

    outfalls = []
    for t in _table_rows(sections.get("Outfall Loading Summary", [])):
        if len(t) != 5:
            raise ReportParseError(f"Unexpected Outfall Loading row: {t}")
        outfalls.append(
            {"id": t[0], "flowFrequencyPercent": _f(t[1], t[0]), "averageFlowCms": _f(t[2], t[0]), "maximumFlowCms": _f(t[3], t[0]), "totalVolumeMillionLiters": _f(t[4], t[0])}
        )
    outfall_system = None
    sys_row = _row_after_last_dash(sections.get("Outfall Loading Summary", []))
    if sys_row and sys_row[0] == "System" and len(sys_row) == 5:
        outfall_system = {
            "flowFrequencyPercent": _f(sys_row[1], "System"), "averageFlowCms": _f(sys_row[2], "System"),
            "maximumFlowCms": _f(sys_row[3], "System"), "totalVolumeMillionLiters": _f(sys_row[4], "System"),
        }

    link_flow = []
    for t in _table_rows(sections.get("Link Flow Summary", [])):
        if len(t) == 8:
            link_flow.append(
                {
                    "id": t[0], "type": t[1], "maximumFlowCms": _f(t[2], t[0]),
                    "timeOfMaximum": _event_time(sim_start, t[3], t[4], "Link Flow"),
                    "maximumVelocityMps": _f(t[5], t[0]), "maxOverFullFlow": _f(t[6], t[0]), "maxOverFullDepth": _f(t[7], t[0]),
                }
            )
        elif len(t) == 5:  # non-conduit links report only flow and time
            link_flow.append(
                {"id": t[0], "type": t[1], "maximumFlowCms": _f(t[2], t[0]), "timeOfMaximum": _event_time(sim_start, t[3], t[4], "Link Flow"),
                 "maximumVelocityMps": None, "maxOverFullFlow": None, "maxOverFullDepth": None}
            )
        else:
            raise ReportParseError(f"Unexpected Link Flow row: {t}")

    conduit_surcharge = []
    for t in _table_rows(sections.get("Conduit Surcharge Summary", [])):
        if len(t) != 6:
            raise ReportParseError(f"Unexpected Conduit Surcharge row: {t}")
        conduit_surcharge.append(
            {
                "id": t[0], "hoursFullBothEnds": _f(t[1], t[0]), "hoursFullUpstream": _f(t[2], t[0]),
                "hoursFullDownstream": _f(t[3], t[0]), "hoursAboveFullNormalFlow": _f(t[4], t[0]), "hoursCapacityLimited": _f(t[5], t[0]),
            }
        )

    begun = ended = None
    for line in lines:
        if "Analysis begun on:" in line:
            begun = line.split("on:", 1)[1].strip()
        elif "Analysis ended on:" in line:
            ended = line.split("on:", 1)[1].strip()

    return SwmmReport(
        engine_version=engine_version,
        warnings=warnings,
        errors=errors,
        element_count=element_count,
        analysis_options=options,
        runoff_continuity=runoff,
        routing_continuity=routing,
        highest_continuity_errors=_ranked_elements(sections.get("Highest Continuity Errors", []), True),
        time_step_critical_elements=_ranked_elements(sections.get("Time-Step Critical Elements", []), True),
        highest_flow_instability_indexes=_ranked_elements(sections.get("Highest Flow Instability Indexes", []), False),
        nonconverging_nodes=_ranked_elements(sections.get("Most Frequent Nonconverging Nodes", []), True),
        routing_time_step=timestep,
        subcatchment_runoff=subcatch,
        node_depth=node_depth,
        node_inflow=node_inflow,
        node_surcharge=node_surcharge,
        node_flooding=node_flooding,
        outfall_loading=outfalls,
        outfall_system=outfall_system,
        link_flow=link_flow,
        conduit_surcharge=conduit_surcharge,
        analysis_begun=begun,
        analysis_ended=ended,
        simulation_start=sim_start,
    )
