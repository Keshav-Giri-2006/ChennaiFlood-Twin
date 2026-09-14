"""bottleneck-timeline-v1: time-varying state of the event-level potential bottlenecks.

Full documentation: docs/DECISION_SUPPORT_METHOD.md §3.2. This does NOT change the event-level
bottleneck-analysis-v1 classification; it answers "which of those potential bottlenecks are
hydraulically loaded at this SWMM reporting timestamp?" using the binary output samples.

Per 30-minute SWMM reporting sample t and conduit c (SWMM .out link variables only):

    T-FULL   SWMM link capacity variable (fraction of conduit filled) >= 0.999
    T-OVER   |flow(t)| > full-flow capacity of c, where the capacity is back-calculated from the
             report (maximum flow / Max-Full-Flow ratio, only when that ratio >= 0.5; otherwise
             unavailable and T-OVER is not evaluated)
    T-FLOOD  an end node of c is in flood-processing-v1 state FLOODING at t

    active(t)   = c is an event-level potential bottleneck AND (T-FULL or T-OVER)
    severity(t) = HIGH (3 criteria) / MODERATE (2) / LOW (1), never above c's event-level severity
                  (so the no-outlet cap and all event-level safeguards carry over).

SWMM's "capacity limited" condition (event criterion L1) is only reported as event hours and
cannot be evaluated per sample, so it is not part of the time-varying state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from app.simulation.inp_reader import InpModel
from app.simulation.output_reader import SwmmOutput
from app.utils.timeutil import to_iso_z

FULL_FRACTION = 0.999
SEVERITY_ORDER = ("LOW", "MODERATE", "HIGH")


def analyse_bottleneck_timeline(
    *,
    simulation_id: str,
    scenario_id: str,
    model_version: str,
    timeline_version: str,
    bottlenecks: dict[str, Any],
    output: SwmmOutput,
    inp: InpModel,
    flooding_nodes_by_period: list[list[str]],
    generated_at: datetime,
) -> dict[str, Any]:
    if output.link_ids != inp.link_ids:
        raise ValueError("Output link IDs differ from the model input")
    if len(flooding_nodes_by_period) != output.n_periods:
        raise ValueError("Flood periods differ from the SWMM output periods")
    index = {lid: i for i, lid in enumerate(output.link_ids)}
    flow = np.asarray(output.link_series("flow"), dtype=np.float64)
    depth = np.asarray(output.link_series("depth"), dtype=np.float64)
    velocity = np.asarray(output.link_series("velocity"), dtype=np.float64)
    capacity = np.asarray(output.link_series("capacity"), dtype=np.float64)
    times = [to_iso_z(t) for t in output.times]

    records = {b["linkId"]: b for b in bottlenecks["bottlenecks"]}
    # Full-flow capacity is only available where the report ratio allows a back-calculation.
    full_flow: dict[str, float] = {}
    for b in bottlenecks["bottlenecks"]:
        q = b["hydraulics"].get("derivedFullFlowCapacityCms")
        if q:
            full_flow[b["linkId"]] = float(q)
    extra = bottlenecks.get("derivedFullFlowCapacities", {})
    for lid, q in extra.items():
        full_flow.setdefault(lid, float(q))

    links_meta = {
        lid: {
            "linkId": lid,
            "sourceObjectId": b["sourceObjectId"],
            "fromNodeId": b["fromNodeId"],
            "toNodeId": b["toNodeId"],
            "eventSeverity": b["severity"],
            "componentHasOutfall": b["networkContext"]["componentHasOutfall"],
            "fullFlowCapacityCms": full_flow.get(lid),
        }
        for lid, b in records.items()
    }

    entries = []
    per_link = {lid: {"activeSteps": 0, "stepsBySeverity": {s: 0 for s in SEVERITY_ORDER}, "firstActive": None, "lastActive": None, "peakUtilization": None, "peakUtilizationTime": None} for lid in records}
    for p, time in enumerate(times):
        flooding = set(flooding_nodes_by_period[p])
        active = []
        for lid, b in records.items():
            i = index[lid]
            q_full = full_flow.get(lid)
            util = abs(flow[p, i]) / q_full if q_full else None
            full = bool(capacity[p, i] >= FULL_FRACTION)
            over = bool(util is not None and util > 1.0)
            flood_nodes = [n for n in (b["fromNodeId"], b["toNodeId"]) if n in flooding]
            stats = per_link[lid]
            if util is not None and (stats["peakUtilization"] is None or util > stats["peakUtilization"]):
                stats["peakUtilization"] = round(float(util), 3)
                stats["peakUtilizationTime"] = time
            if not (full or over):
                continue
            met = int(full) + int(over) + int(bool(flood_nodes))
            raw = SEVERITY_ORDER[min(met, 3) - 1]
            severity = SEVERITY_ORDER[min(SEVERITY_ORDER.index(raw), SEVERITY_ORDER.index(b["severity"]))]
            active.append(
                {
                    "linkId": lid,
                    "sourceObjectId": b["sourceObjectId"],
                    "severity": severity,
                    "eventSeverity": b["severity"],
                    "criteria": {"full": full, "aboveFullFlowCapacity": over if util is not None else None, "connectedNodeFlooding": bool(flood_nodes)},
                    "flowCms": round(float(flow[p, i]), 4),
                    "fullFlowCapacityCms": q_full,
                    "utilization": round(float(util), 3) if util is not None else None,
                    "fillFraction": round(float(capacity[p, i]), 3),
                    "depthM": round(float(depth[p, i]), 3),
                    "velocityMps": round(float(velocity[p, i]), 3),
                    "floodingNodeIds": flood_nodes,
                }
            )
            stats["activeSteps"] += 1
            stats["stepsBySeverity"][severity] += 1
            stats["firstActive"] = stats["firstActive"] or time
            stats["lastActive"] = time
        active.sort(key=lambda a: (-SEVERITY_ORDER.index(a["severity"]), -(a["utilization"] or 0), a["linkId"]))
        loaded = [
            (abs(flow[p, index[lid]]) / q, lid) for lid, q in full_flow.items() if lid in index and q > 0
        ]
        most = max(loaded) if loaded else None
        entries.append(
            {
                "index": p,
                "time": time,
                "activeCount": len(active),
                "highestSeverity": active[0]["severity"] if active else None,
                "active": active,
                "mostLoaded": (
                    {
                        "linkId": most[1],
                        "utilization": round(float(most[0]), 3),
                        "flowCms": round(float(flow[p, index[most[1]]]), 4),
                        "fullFlowCapacityCms": full_flow[most[1]],
                        "isPotentialBottleneck": most[1] in records,
                    }
                    if most and most[0] > 0
                    else None
                ),
            }
        )
    for stats in per_link.values():
        stats["activeHours"] = round(stats["activeSteps"] * output.report_step_seconds / 3600.0, 2)

    return {
        "simulationId": simulation_id,
        "scenarioId": scenario_id,
        "modelVersion": model_version,
        "bottleneckTimelineVersion": timeline_version,
        "bottleneckAnalysisVersion": bottlenecks["bottleneckAnalysisVersion"],
        "dataType": "model-derived",
        "method": "docs/DECISION_SUPPORT_METHOD.md",
        "generatedAt": to_iso_z(generated_at),
        "intervalMinutes": output.report_step_seconds // 60,
        "definition": {
            "T-FULL": f"SWMM link capacity variable (fraction filled) >= {FULL_FRACTION}",
            "T-OVER": "|flow| > full-flow capacity back-calculated from the SWMM report (only where Max/Full Flow >= 0.5)",
            "T-FLOOD": "an end node is overflowing at this timestamp (flood-processing-v1)",
            "active": "event-level potential bottleneck AND (T-FULL or T-OVER)",
            "severity": "HIGH 3 / MODERATE 2 / LOW 1 criteria, never above the event-level severity",
            "notEvaluated": "SWMM capacity-limited state (event criterion L1) is only reported as event hours, not per timestamp.",
            "mostLoaded": "conduit with the highest |flow| / full-flow capacity among conduits whose capacity can be back-calculated",
        },
        "links": links_meta,
        "summary": {
            "timestampsWithActiveBottlenecks": sum(1 for e in entries if e["activeCount"]),
            "firstActiveTime": next((e["time"] for e in entries if e["activeCount"]), None),
            "lastActiveTime": next((e["time"] for e in reversed(entries) if e["activeCount"]), None),
            "perLink": per_link,
            "conduitsWithFullFlowCapacity": len(full_flow),
        },
        "entries": entries,
    }
