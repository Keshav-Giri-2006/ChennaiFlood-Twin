"""decision-support-v1: rule-based, evidence-traceable planning recommendations.

Full documentation: docs/DECISION_SUPPORT_METHOD.md (section 5).

Every recommendation is produced by one explicit rule from evidence already
computed by the SWMM report, bottleneck-analysis-v1, exposure-analysis-v1 and
GCC source attributes. No rule fires without its triggering evidence. Output is
academic prototype decision support, not municipal engineering direction.

    R1 CAPACITY_ASSESSMENT       potential bottleneck, HIGH/MODERATE, in a component with a model outfall
    R2 CONNECTIVITY_VERIFICATION overflowing nodes in a component without any model outfall
    R3 OVERFLOW_INSPECTION       node (component with outfall) overflowing >= 24 h or >= 5 % of simulated flooding,
                                 not already covered by R1
    R4 PREPAREDNESS_ACCESS       overflowing node (component with outfall, >= 6 h) whose influence zone intersects
                                 a top-quartile number of buildings
    R5 MAINTENANCE_INSPECTION    GCC drain recorded as Bad / Kacha or with recorded obstacles AND hydraulic evidence
    R6 DATA_VERIFICATION         SWMM time-step critical link (>= 10 %)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from app.analysis.bottleneck_analysis import NetworkComponents
from app.gis.network_mapping import NetworkMapping
from app.simulation.inp_reader import InpModel
from app.simulation.report_parser import SwmmReport
from app.utils.timeutil import to_iso_z

PERSISTENT_OVERFLOW_HOURS = 24.0
OVERFLOW_VOLUME_SHARE = 0.05
CONNECTIVITY_HIGH_SHARE = 0.10
CONNECTIVITY_MEDIUM_SHARE = 0.02
EXPOSURE_QUANTILE = 75
EXPOSURE_MIN_HOURS = 6.0
HYDRAULIC_EVIDENCE_HOURS = 1.0
TIMESTEP_CRITICAL_PERCENT = 10.0

PRIORITY_ORDER = ("HIGH", "MEDIUM", "LOW")
RULE_ORDER = ("R1", "R2", "R3", "R4", "R5", "R6")
DISCLAIMER = "Decision-support suggestion derived from an uncalibrated candidate model; not an engineering order, municipal directive or field-confirmed diagnosis."


def _metric(label: str, value: Any, unit: str, source: str) -> dict[str, Any]:
    return {"label": label, "value": value, "unit": unit, "source": source}


def generate_recommendations(
    *,
    simulation_id: str,
    scenario_id: str,
    model_version: str,
    decision_version: str,
    bottlenecks: dict[str, Any],
    exposure: dict[str, Any],
    report: SwmmReport,
    inp: InpModel,
    network: NetworkMapping,
    components: NetworkComponents,
    source_conduits: dict[str, dict[str, str]],
    drain_obstacles: dict[int, str | None],
    generated_at: datetime,
) -> dict[str, Any]:
    flooding = {r["id"]: r for r in report.node_flooding}
    surcharge = {r["id"]: r for r in report.conduit_surcharge}
    total_flood_ml = sum(r["totalFloodVolumeMillionLiters"] for r in report.node_flooding)
    recs: list[dict[str, Any]] = []
    bn_by_link = {b["linkId"]: b for b in bottlenecks["bottlenecks"]}

    def share(node_ids: list[str]) -> float:
        return sum(flooding[n]["totalFloodVolumeMillionLiters"] for n in node_ids if n in flooding) / total_flood_ml if total_flood_ml else 0.0

    def node_flood_metrics(n: str) -> list[dict[str, Any]]:
        f = flooding[n]
        return [
            _metric(f"{n} hours flooded", f["hoursFlooded"], "hr", "SWMM Node Flooding Summary"),
            _metric(f"{n} maximum overflow rate", f["maximumRateCms"], "m3/s", "SWMM Node Flooding Summary"),
            _metric(f"{n} simulated overflow volume", round(f["totalFloodVolumeMillionLiters"] * 1e6), "L", "SWMM Node Flooding Summary (model diagnostic, not observed volume)"),
        ]

    # ---- R1 capacity assessment -----------------------------------------------------------
    r1_nodes: set[str] = set()
    for b in bottlenecks["bottlenecks"]:
        if not b["networkContext"]["componentHasOutfall"] or b["severity"] not in ("HIGH", "MODERATE"):
            continue
        h = b["hydraulics"]
        met = [c for c in b["criteria"] if c["met"]]
        flooding_nodes = b["criteria"][3]["value"]
        r1_nodes.update(flooding_nodes)
        metrics = [_metric(c["label"], c["value"] if not isinstance(c["value"], list) else ", ".join(c["value"]), c["unit"], c["source"]) for c in met]
        metrics += [_metric("Maximum flow", h["maximumFlowCms"], "m3/s", "SWMM Link Flow Summary"), _metric("Maximum velocity", h["maximumVelocityMps"], "m/s", "SWMM Link Flow Summary")]
        for n in flooding_nodes:
            metrics += node_flood_metrics(n)
        recs.append(
            {
                "id": f"rec-r1-{b['linkId']}",
                "rule": "R1",
                "category": "DRAINAGE_CAPACITY",
                "priority": "HIGH" if b["severity"] == "HIGH" else "MEDIUM",
                "confidence": b["confidence"],
                "title": f"Assess drainage capacity of segment {b['linkId']} (GCC ObjectID {b['sourceObjectId']})",
                "recommendation": f"Inspect and assess the hydraulic capacity and condition of the drainage corridor {b['fromNodeId']} → {b['toNodeId']} (model conduit {b['linkId']}) and its downstream connection.",
                "why": b["explanation"]["whyFlagged"],
                "evidence": {"links": [{"linkId": b["linkId"], "sourceObjectId": b["sourceObjectId"]}], "nodes": [b["fromNodeId"], b["toNodeId"]], "metrics": metrics},
                "drivers": [c["label"] for c in met],
                "confidenceReasons": b["confidenceReasons"],
                "relatedBottleneckLinkIds": [b["linkId"]],
                "focus": {"linkIds": [b["linkId"]], "nodeIds": [b["fromNodeId"], b["toNodeId"]]},
            }
        )

    # ---- R2 connectivity verification --------------------------------------------------------
    context_links = {n["linkId"]: n for n in bottlenecks["numericalDiagnostics"]}
    for comp in components.components:
        if comp["outfalls"]:
            continue
        nodes = [n for n in comp["nodes"] if n in flooding]
        if not nodes:
            continue
        s = share(nodes)
        priority = "HIGH" if s >= CONNECTIVITY_HIGH_SHARE else "MEDIUM" if s >= CONNECTIVITY_MEDIUM_SHARE else "LOW"
        main = max(nodes, key=lambda n: flooding[n]["totalFloodVolumeMillionLiters"])
        object_ids = sorted({network.link_to_object_id[lid] for lid in comp["links"]})
        metrics = [
            _metric("Share of total simulated flooding", round(100 * s, 1), "%", "SWMM Node Flooding Summary"),
            _metric("Model outfalls in component", 0, "count", "SWMM model input"),
            _metric("Component nodes / conduits", f"{len(comp['nodes'])} / {len(comp['links'])}", "count", "SWMM model input"),
        ]
        for n in sorted(nodes, key=lambda n: -flooding[n]["totalFloodVolumeMillionLiters"]):
            metrics += node_flood_metrics(n)
        diag = [lid for lid in comp["links"] if lid in context_links]
        why = (
            f"Drainage component {comp['modelComponentId']} ({len(comp['nodes'])} nodes, {len(comp['links'])} conduit{'s' if len(comp['links']) != 1 else ''}) has no outlet in the reconstructed model, "
            f"so inflow beyond its storage can only leave as overflow. Its overflowing nodes ({', '.join(sorted(nodes))}) account for {100 * s:.1f}% of the simulated flooding. "
            "This overflow mainly reflects missing or unresolved network connectivity, not a verified capacity problem."
        )
        if diag:
            why += f" Numerical diagnostics in this component ({', '.join(diag)}) are consistent with an incomplete component."
        recs.append(
            {
                "id": f"rec-r2-component-{comp['modelComponentId']}",
                "rule": "R2",
                "category": "NETWORK_DATA_VERIFICATION",
                "priority": priority,
                "confidence": "MEDIUM",
                "title": f"Verify the downstream connection of the drainage component around {main}",
                "recommendation": f"Field-verify where drains of GCC ObjectID(s) {', '.join(map(str, object_ids))} discharge, and add the verified connection/outfall to the network data before interpreting flooding at {', '.join(sorted(nodes))}.",
                "why": why,
                "evidence": {"links": [{"linkId": lid, "sourceObjectId": network.link_to_object_id[lid]} for lid in comp["links"]], "nodes": sorted(nodes), "metrics": metrics},
                "drivers": ["no model outfall in component", "node overflow in component"],
                "confidenceReasons": ["The absence of an outfall in the model is certain; whether a real connection exists is unknown."],
                "relatedBottleneckLinkIds": [lid for lid in comp["links"] if lid in bn_by_link],
                "focus": {"linkIds": comp["links"], "nodeIds": sorted(nodes)},
            }
        )

    # ---- R3 persistent overflow inspection -------------------------------------------------------
    for n, f in sorted(flooding.items()):
        if n in r1_nodes or not components.has_outfall(n):
            continue
        s = share([n])
        if f["hoursFlooded"] < PERSISTENT_OVERFLOW_HOURS and s < OVERFLOW_VOLUME_SHARE:
            continue
        connected = sorted(lid for lid, c in inp.conduits.items() if n in (c["fromNode"], c["toNode"]))
        low_bn = [l for l in connected if l in bn_by_link]
        cause = (
            f"Connected conduit(s) {', '.join(low_bn)} meet only low-concern bottleneck criteria, so the overflow is not attributed to one constrained conduit."
            if low_bn
            else "None of its connected conduits meets the bottleneck loading criteria, so the overflow is not attributed to one constrained conduit."
        )
        drivers = []
        if f["hoursFlooded"] >= PERSISTENT_OVERFLOW_HOURS:
            drivers.append(f"overflow for >= {PERSISTENT_OVERFLOW_HOURS:.0f} h")
        if s >= OVERFLOW_VOLUME_SHARE:
            drivers.append(f">= {100 * OVERFLOW_VOLUME_SHARE:.0f}% of simulated flooding")
        recs.append(
            {
                "id": f"rec-r3-{n}",
                "rule": "R3",
                "category": "DRAINAGE_INSPECTION",
                "priority": "MEDIUM",
                "confidence": "MEDIUM",
                "title": f"Prioritise drainage inspection around node {n}",
                "recommendation": f"Inspect the drains connected at {n} (conduits {', '.join(connected)}; GCC ObjectID(s) {', '.join(str(network.link_to_object_id[l]) for l in connected)}) for blockage, condition and inlet capacity.",
                "why": f"Model node {n} overflows for {f['hoursFlooded']:.1f} h in the simulated event ({100 * s:.1f}% of simulated flooding), in a drainage component that has a model outfall. {cause}",
                "evidence": {"links": [{"linkId": l, "sourceObjectId": network.link_to_object_id[l]} for l in connected], "nodes": [n], "metrics": [*node_flood_metrics(n), _metric("Share of total simulated flooding", round(100 * s, 1), "%", "SWMM Node Flooding Summary")]},
                "drivers": drivers,
                "confidenceReasons": [],
                "relatedBottleneckLinkIds": [l for l in connected if l in bn_by_link],
                "focus": {"linkIds": connected, "nodeIds": [n]},
            }
        )

    # ---- R4 preparedness / access planning (model-derived exposure) --------------------------------
    eligible = [e for e in exposure["byNode"] if e["componentHasOutfall"] and e["hoursFloodingSampled"] >= EXPOSURE_MIN_HOURS and e["buildingsIntersecting"] > 0]
    if eligible:
        cut = float(np.percentile([e["buildingsIntersecting"] for e in eligible], EXPOSURE_QUANTILE))
        for e in sorted(eligible, key=lambda e: (-e["buildingsIntersecting"], e["nodeId"])):
            if e["buildingsIntersecting"] < cut:
                continue
            roads = e["roadNames"][:5]
            recs.append(
                {
                    "id": f"rec-r4-{e['nodeId']}",
                    "rule": "R4",
                    "category": "PREPAREDNESS_AND_ACCESS",
                    "priority": "MEDIUM",
                    "confidence": "LOW",
                    "title": f"Consider local flood preparedness and access planning near {e['nodeId']}",
                    "recommendation": "Include the buildings and carriageways associated with this node in local flood-preparedness, drainage-maintenance scheduling and emergency-access planning" + (f" (e.g. {', '.join(roads)})." if roads else "."),
                    "why": (
                        f"Node {e['nodeId']} overflows at {e['reportingPeriodsFlooding']} reporting timestamps ({e['hoursFloodingSampled']:.1f} h), and its flood influence zone intersects "
                        f"{e['buildingsIntersecting']} buildings ({e['buildingFootprintAreaM2']:.0f} m2 footprint) and {e['roadsIntersecting']} carriageway polygons — at or above the "
                        f"{EXPOSURE_QUANTILE}th percentile ({cut:.0f} buildings) of overflowing nodes in outfall-connected components. This is spatial association, not observed flooding."
                    ),
                    "evidence": {
                        "links": [],
                        "nodes": [e["nodeId"]],
                        "metrics": [
                            _metric("Buildings intersecting influence zone", e["buildingsIntersecting"], "count", "exposure-analysis-v1"),
                            _metric("Building footprint within zone", e["buildingFootprintAreaM2"], "m2", "exposure-analysis-v1"),
                            _metric("Carriageway polygons intersecting zone", e["roadsIntersecting"], "count", "exposure-analysis-v1"),
                            _metric("Carriageway area within zone", e["roadAreaM2"], "m2", "exposure-analysis-v1"),
                            _metric("Reporting timestamps overflowing", e["reportingPeriodsFlooding"], "count", "flood-processing-v1"),
                        ],
                    },
                    "drivers": ["model-derived exposure", "sustained node overflow"],
                    "confidenceReasons": ["Influence zones are nearest-node associations without ground depth or extent."],
                    "relatedBottleneckLinkIds": [],
                    "focus": {"linkIds": [], "nodeIds": [e["nodeId"]]},
                }
            )

    # ---- R5 maintenance inspection (GCC condition attributes + hydraulic evidence) ----------------------
    by_object: dict[int, list[str]] = {}
    for lid in inp.conduits:
        by_object.setdefault(network.link_to_object_id[lid], []).append(lid)
    for object_id, links in sorted(by_object.items()):
        src = source_conduits[links[0]]
        status, kacha = src.get("status"), src.get("puca_kacha")
        obstacles = drain_obstacles.get(object_id)
        condition = []
        if status == "Bad":
            condition.append("GCC condition status 'Bad'")
        if kacha == "Kacha":
            condition.append("unlined (Kacha) drain")
        if obstacles:
            condition.append(f"recorded obstacles: {obstacles}")
        if not condition:
            continue
        evidence_items: list[str] = []
        nodes: set[str] = set()
        for lid in links:
            c = inp.conduits[lid]
            if lid in bn_by_link:
                evidence_items.append(f"{lid} is a potential bottleneck ({bn_by_link[lid]['severity'].lower()} concern)")
            sur = surcharge.get(lid)
            full = max(sur["hoursFullUpstream"], sur["hoursFullDownstream"]) if sur else 0.0
            if full >= HYDRAULIC_EVIDENCE_HOURS:
                evidence_items.append(f"{lid} runs full at one or both ends for {full:.1f} h")
            for n in (c["fromNode"], c["toNode"]):
                if n in flooding and flooding[n]["hoursFlooded"] >= HYDRAULIC_EVIDENCE_HOURS:
                    evidence_items.append(f"connected node {n} overflows for {flooding[n]['hoursFlooded']:.1f} h")
                    nodes.add(n)
        if not evidence_items:
            continue
        evidence_items = list(dict.fromkeys(evidence_items))
        severe_condition = status == "Bad" or kacha == "Kacha"
        recs.append(
            {
                "id": f"rec-r5-{object_id}",
                "rule": "R5",
                "category": "MAINTENANCE",
                "priority": "MEDIUM" if severe_condition else "LOW",
                "confidence": "LOW",
                "title": f"Prioritise maintenance inspection of GCC drain ObjectID {object_id}",
                "recommendation": f"Schedule a maintenance/condition inspection of GCC drain ObjectID {object_id} (model conduit(s) {', '.join(links)}), including desilting and obstruction checks.",
                "why": f"The GCC source record notes {', '.join(condition)}, and the simulation shows hydraulic stress on this drain: {'; '.join(evidence_items)}.",
                "evidence": {
                    "links": [{"linkId": lid, "sourceObjectId": object_id} for lid in links],
                    "nodes": sorted(nodes),
                    "metrics": [_metric("GCC status", status, "attribute", "GCC storm-water drain dataset"), _metric("GCC lining", kacha, "attribute", "GCC storm-water drain dataset"), _metric("GCC recorded obstacles", obstacles or "none", "attribute", "GCC storm-water drain dataset")],
                },
                "drivers": [*condition, *evidence_items],
                "confidenceReasons": ["The survey date and current condition of the GCC attributes are unknown."],
                "relatedBottleneckLinkIds": [lid for lid in links if lid in bn_by_link],
                "focus": {"linkIds": links, "nodeIds": sorted(nodes)},
            }
        )

    # ---- R6 model data verification (numerical diagnostics) --------------------------------------------
    for d in bottlenecks["numericalDiagnostics"]:
        pct = d["timeStepCriticalPercent"]
        if pct is None or pct < TIMESTEP_CRITICAL_PERCENT:
            continue
        ctx = d.get("projectInvestigation")
        why = (
            f"{d['linkId']} controls the SWMM routing time step {pct:.1f}% of the time (a numerical sensitivity, typically a short conduit with inconsistent junction elevations). "
            f"It is {'also' if d['isPotentialBottleneck'] else 'not'} a potential bottleneck by the hydraulic loading criteria (Max/Full Flow {d['maxOverFullFlow']}, full at both ends {d['hoursFullBothEnds']} h)."
        )
        if ctx:
            why += f" Project investigation: {ctx['finding']}"
        recs.append(
            {
                "id": f"rec-r6-{d['linkId']}",
                "rule": "R6",
                "category": "MODEL_DATA_VERIFICATION",
                "priority": "LOW",
                "confidence": "MEDIUM" if ctx else "LOW",
                "title": f"Verify invert and manhole data at {d['linkId']} ({d['fromNodeId']}–{d['toNodeId']})",
                "recommendation": f"Survey invert levels / drop structures at {d['fromNodeId']} and {d['toNodeId']} (GCC ObjectID {d['sourceObjectId']}) to resolve the elevation ambiguity before relying on local model results.",
                "why": why,
                "evidence": {
                    "links": [{"linkId": d["linkId"], "sourceObjectId": d["sourceObjectId"]}],
                    "nodes": [d["fromNodeId"], d["toNodeId"]],
                    "metrics": [
                        _metric("Time-step critical", pct, "%", "SWMM Time-Step Critical Elements"),
                        _metric("Max/Full Flow", d["maxOverFullFlow"], "ratio", "SWMM Link Flow Summary"),
                        _metric("Hours full both ends", d["hoursFullBothEnds"], "hr", "SWMM Conduit Surcharge Summary"),
                    ],
                },
                "drivers": ["numerical time-step criticality", *(["documented source-data ambiguity"] if ctx else [])],
                "confidenceReasons": [f"Investigation decision: {ctx['decision']} ({ctx['source']})"] if ctx else ["No project investigation record for this link."],
                "relatedBottleneckLinkIds": [d["linkId"]] if d["isPotentialBottleneck"] else [],
                "focus": {"linkIds": [d["linkId"]], "nodeIds": [d["fromNodeId"], d["toNodeId"]]},
            }
        )

    for r in recs:
        r["disclaimer"] = DISCLAIMER
    recs.sort(key=lambda r: (PRIORITY_ORDER.index(r["priority"]), RULE_ORDER.index(r["rule"]), r["id"]))
    return {
        "simulationId": simulation_id,
        "scenarioId": scenario_id,
        "modelVersion": model_version,
        "decisionSupportVersion": decision_version,
        "bottleneckAnalysisVersion": bottlenecks["bottleneckAnalysisVersion"],
        "exposureAnalysisVersion": exposure["exposureAnalysisVersion"],
        "dataType": "model-derived",
        "method": "docs/DECISION_SUPPORT_METHOD.md",
        "generatedAt": to_iso_z(generated_at),
        "disclaimer": DISCLAIMER,
        "rules": {
            "R1": "Potential bottleneck with HIGH or MODERATE diagnostic concern in a component with a model outfall → capacity assessment (priority HIGH for HIGH concern, else MEDIUM).",
            "R2": f"Overflowing nodes in a component without a model outfall → verify connectivity (HIGH >= {100 * CONNECTIVITY_HIGH_SHARE:.0f}% of simulated flooding, MEDIUM >= {100 * CONNECTIVITY_MEDIUM_SHARE:.0f}%, else LOW).",
            "R3": f"Node in an outfall-connected component overflowing >= {PERSISTENT_OVERFLOW_HOURS:.0f} h or >= {100 * OVERFLOW_VOLUME_SHARE:.0f}% of simulated flooding, not covered by R1 → drainage inspection (MEDIUM).",
            "R4": f"Overflowing node (outfall-connected, >= {EXPOSURE_MIN_HOURS:.0f} h) whose influence zone intersects buildings at or above the {EXPOSURE_QUANTILE}th percentile → preparedness/access planning (MEDIUM, LOW confidence).",
            "R5": "GCC drain recorded Bad/Kacha (MEDIUM) or with obstacles (LOW) AND hydraulic evidence (bottleneck, >= 1 h full, or connected node overflowing >= 1 h) → maintenance inspection.",
            "R6": f"Link time-step critical >= {TIMESTEP_CRITICAL_PERCENT:.0f}% → verify invert/manhole data (LOW).",
        },
        "summary": {
            "total": len(recs),
            "byPriority": {p: sum(1 for r in recs if r["priority"] == p) for p in PRIORITY_ORDER},
            "byRule": {rule: sum(1 for r in recs if r["rule"] == rule) for rule in RULE_ORDER},
        },
        "recommendations": recs,
    }
