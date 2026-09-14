"""Convert raw SWMM artifacts into validated, structured result products.

Inputs: parsed ``.rpt`` report, binary ``.out`` output, the ``.inp`` structure
and the scenario rainfall. Outputs: ``results.json`` (event summaries and
diagnostics) and ``hydraulics_timeseries.json`` (reporting-period series).

Units: SWMM runs in CMS, so flows are m3/s, depths/heads m, node/storage
volumes m3. Report volumes given in 10^6 litres are converted to litres.

Scientific labelling: SWMM "Flooding Loss" is exposed as a *simulated
flooding volume* - water leaving the 1D network at overflowing nodes under the
current incomplete network representation - never as observed flood volume.
Node depths are in-network water depths, not surface flood depths.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.simulation.inp_reader import InpModel
from app.simulation.output_reader import SwmmOutput
from app.simulation.rainfall import RainfallSeries
from app.simulation.report_parser import SwmmReport
from app.utils.timeutil import to_iso_z

RESULTS_SCHEMA_VERSION = "1"
# The report prints depths to 2 decimals; allow half a centimetre of rounding.
MAX_DEPTH_CROSSCHECK_TOLERANCE_M = 0.0055
LITERS_PER_MILLION = 1_000_000.0


class ResultProcessingError(Exception):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.details = details


def _ml_to_l(value: float) -> float:
    return round(value * LITERS_PER_MILLION, 3)


def _peak(values: list[float], times: list[str]) -> dict[str, Any]:
    peak = max(values)
    return {"value": round(peak, 6), "time": times[values.index(peak)]}


def _round_matrix(matrix: list[list[float]], digits: int) -> list[list[float]]:
    return [[round(v, digits) for v in row] for row in matrix]


def process_results(
    *,
    simulation_id: str,
    scenario_id: str,
    model_version: str,
    processing_version: str,
    report: SwmmReport,
    output: SwmmOutput,
    inp: InpModel,
    rainfall: RainfallSeries,
) -> tuple[dict[str, Any], dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, message: str, details: Any = None) -> None:
        checks.append({"check": name, "passed": passed})
        if not passed:
            raise ResultProcessingError(message, details)

    check("report.noErrors", not report.errors, "SWMM report contains errors.", report.errors)
    check("report.engineVersion", report.engine_version is not None, "SWMM report engine version not found.")
    expected_counts = {"subcatchments": len(inp.subcatchments), "nodes": len(inp.node_ids), "links": len(inp.link_ids)}
    actual_counts = {k: report.element_count.get(k) for k in expected_counts}
    check("report.elementCounts", actual_counts == expected_counts, "Report element counts differ from the model input.", {"expected": expected_counts, "actual": actual_counts})

    node_set, link_set, sub_set = set(inp.node_ids), set(inp.link_ids), set(inp.subcatchments)
    check("report.nodeDepthIds", {r["id"] for r in report.node_depth} == node_set, "Node Depth Summary IDs do not match model nodes.")
    check("report.linkFlowIds", {r["id"] for r in report.link_flow} == link_set, "Link Flow Summary IDs do not match model links.")
    check("report.subcatchmentIds", {r["id"] for r in report.subcatchment_runoff} == sub_set, "Subcatchment Runoff IDs do not match model subcatchments.")
    check("report.floodingIdsKnown", all(r["id"] in node_set for r in report.node_flooding), "Node Flooding Summary contains unknown node IDs.")
    check("report.surchargeIdsKnown", all(r["id"] in link_set for r in report.conduit_surcharge), "Conduit Surcharge Summary contains unknown link IDs.")

    check("output.flowUnits", output.flow_units == inp.options.get("FLOW_UNITS"), "Binary output flow units differ from model input.")
    check("output.nodeIds", output.node_ids == inp.node_ids, "Binary output node IDs differ from model input.")
    check("output.linkIds", output.link_ids == inp.link_ids, "Binary output link IDs differ from model input.")
    check("output.subcatchmentIds", output.subcatchment_ids == list(inp.subcatchments), "Binary output subcatchment IDs differ from model input.")
    step = timedelta(seconds=output.report_step_seconds)
    check(
        "output.timestampsRegular",
        all(b - a == step for a, b in zip(output.times, output.times[1:])) and output.times[0] > inp.simulation_start() and output.times[-1] <= inp.simulation_end(),
        "Binary output timestamps are irregular or outside the simulation period.",
    )

    depth = output.node_series("depth")
    flooding = output.node_series("flooding")
    reported_max = {r["id"]: r["reportedMaximumDepthM"] for r in report.node_depth}
    worst = max(abs(max(depth[p][n] for p in range(output.n_periods)) - reported_max[nid]) for n, nid in enumerate(output.node_ids))
    check(
        "crosscheck.reportedMaxDepth",
        worst <= MAX_DEPTH_CROSSCHECK_TOLERANCE_M,
        "Binary output node depths are inconsistent with the report.",
        {"maxAbsDifferenceM": worst},
    )

    rc = report.runoff_continuity
    fr = report.routing_continuity
    for key in ("Total Precipitation", "Infiltration Loss", "Surface Runoff", "Final Storage"):
        check(f"report.runoff.{key}", key in rc, f"Runoff continuity row '{key}' missing.")
    for key in ("Wet Weather Inflow", "External Outflow", "Flooding Loss", "Final Stored Volume", "Initial Stored Volume"):
        check(f"report.routing.{key}", key in fr, f"Flow routing continuity row '{key}' missing.")
    check("report.continuityErrors", "continuityErrorPercent" in rc and "continuityErrorPercent" in fr, "Continuity error values missing.")

    times = [to_iso_z(t) for t in output.times]
    sys_rain = output.system_series("rainfall")
    sys_runoff = output.system_series("runoff")
    sys_flood = output.system_series("flooding")
    sys_outfall = output.system_series("outfall_flow")
    sys_storage = output.system_series("storage_volume")
    sys_lateral = output.system_series("total_lateral_inflow")

    flooded = sorted(report.node_flooding, key=lambda r: r["totalFloodVolumeMillionLiters"], reverse=True)

    results: dict[str, Any] = {
        "schemaVersion": RESULTS_SCHEMA_VERSION,
        "simulationId": simulation_id,
        "scenarioId": scenario_id,
        "modelVersion": model_version,
        "processingVersion": processing_version,
        "engine": {"name": "EPA SWMM", "version": report.engine_version, "analysisBegun": report.analysis_begun, "analysisEnded": report.analysis_ended},
        "simulationPeriod": {
            "start": to_iso_z(inp.simulation_start()),
            "end": to_iso_z(inp.simulation_end()),
            "reportStepSeconds": output.report_step_seconds,
            "reportingPeriods": output.n_periods,
            "firstReportTime": times[0],
            "lastReportTime": times[-1],
            "timeBasis": "UTC (inherited from the IMERG rainfall input)",
        },
        "rainfallInput": {
            "dataType": "source",
            "totalMm": round(rainfall.total_mm, 3),
            "peakIntensityMmHr": round(rainfall.peak_mm_hr, 3),
            "peakIntervalStart": to_iso_z(rainfall.peak_time),
            "intervalMinutes": rainfall.interval_minutes,
            "records": len(rainfall.times),
        },
        "runoffContinuity": {
            "dataType": "model-derived",
            "totalPrecipitationMm": rc["Total Precipitation"]["depthMm"],
            "infiltrationLossMm": rc["Infiltration Loss"]["depthMm"],
            "surfaceRunoffMm": rc["Surface Runoff"]["depthMm"],
            "finalSurfaceStorageMm": rc["Final Storage"]["depthMm"],
            "continuityErrorPercent": rc["continuityErrorPercent"],
        },
        "routingContinuity": {
            "dataType": "model-derived",
            "wetWeatherInflowL": _ml_to_l(fr["Wet Weather Inflow"]["volumeMillionLiters"]),
            "externalOutflowL": _ml_to_l(fr["External Outflow"]["volumeMillionLiters"]),
            "simulatedFloodingVolumeL": _ml_to_l(fr["Flooding Loss"]["volumeMillionLiters"]),
            "initialStoredVolumeL": _ml_to_l(fr["Initial Stored Volume"]["volumeMillionLiters"]),
            "finalStoredVolumeL": _ml_to_l(fr["Final Stored Volume"]["volumeMillionLiters"]),
            "continuityErrorPercent": fr["continuityErrorPercent"],
            "note": "simulatedFloodingVolumeL is SWMM flooding loss: water overflowing network nodes under the current incomplete network representation. It is a model diagnostic, not an observed flood volume.",
        },
        "systemPeaks": {
            "dataType": "model-derived",
            "basis": "reporting-period values from the SWMM binary output",
            "systemFloodingRateCms": _peak(sys_flood, times),
            "outfallFlowCms": _peak(sys_outfall, times),
            "runoffCms": _peak(sys_runoff, times),
        },
        "nodes": {
            "count": len(inp.node_ids),
            "flooding": flooded,
            "surcharge": report.node_surcharge,
            "depth": report.node_depth,
            "inflow": report.node_inflow,
        },
        "links": {"count": len(inp.link_ids), "flow": report.link_flow, "conduitSurcharge": report.conduit_surcharge},
        "subcatchments": {"count": len(inp.subcatchments), "runoff": report.subcatchment_runoff},
        "outfalls": {
            "note": "Model outfalls are provisional downstream boundary terminals, not confirmed physical outfalls.",
            "loading": report.outfall_loading,
            "system": report.outfall_system,
        },
        "diagnostics": {
            "warnings": report.warnings,
            "routingTimeStep": report.routing_time_step,
            "highestContinuityErrors": report.highest_continuity_errors,
            "timeStepCriticalElements": report.time_step_critical_elements,
            "highestFlowInstabilityIndexes": report.highest_flow_instability_indexes,
            "nonconvergingNodes": report.nonconverging_nodes,
            "note": "Numerical diagnostics indicate solver behaviour; they are not evidence of physical defects in the source drainage data.",
        },
        "processingChecks": checks,
    }

    timeseries: dict[str, Any] = {
        "schemaVersion": RESULTS_SCHEMA_VERSION,
        "simulationId": simulation_id,
        "dataType": "model-derived",
        "timeConvention": "Values are SWMM reporting-period values at each timestamp (UTC).",
        "timestamps": times,
        "units": {
            "rainfall": "mm/hr",
            "flow": "m3/s",
            "depth": "m",
            "storageVolume": "m3",
            "capacity": "fraction of full depth (0-1)",
        },
        "system": {
            "rainfallMmHr": [round(v, 4) for v in sys_rain],
            "runoffCms": [round(v, 5) for v in sys_runoff],
            "floodingCms": [round(v, 5) for v in sys_flood],
            "outfallFlowCms": [round(v, 5) for v in sys_outfall],
            "totalLateralInflowCms": [round(v, 5) for v in sys_lateral],
            "storageVolumeM3": [round(v, 3) for v in sys_storage],
        },
        "nodes": {
            "ids": output.node_ids,
            "depthM": _round_matrix(depth, 4),
            "floodingCms": _round_matrix(flooding, 5),
        },
        "links": {
            "ids": output.link_ids,
            "flowCms": _round_matrix(output.link_series("flow"), 5),
            "capacity": _round_matrix(output.link_series("capacity"), 4),
        },
    }
    return results, timeseries
