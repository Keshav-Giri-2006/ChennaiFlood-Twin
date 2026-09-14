"""bottleneck-analysis-v1: SWMM-evidence screening of potential drainage bottlenecks.

Full documentation: docs/DECISION_SUPPORT_METHOD.md (section 2-3).

A conduit is a *potential drainage bottleneck* only if the SWMM results show
hydraulic loading on that conduit (criteria L1-L3). Visual intuition, numerical
solver sensitivity and connected-node flooding alone never flag a conduit.

Criteria (all values come from the SWMM 5.2.4 report of the simulation):

    L1 capacity limited     Conduit Surcharge Summary "Hours Capacity Limited" > 0.01 h
                            (SWMM: upstream end full and HGL slope > conduit slope)
    L2 sustained full bore  "Hours Full Both Ends" >= 1.0 h (two reporting intervals)
    L3 peak flow > capacity Link Flow Summary "Max/Full Flow" > 1.0
    S1 connected flooding   an end node floods for >= 1.0 h (Node Flooding Summary)

    score    = criteria met / 4 (0.25 .. 1.0), eligible only if >= 1 of L1-L3 is met
    severity = HIGH (>= 3 criteria), MODERATE (2), LOW (1)

A network component without any model outfall cannot drain, so conduit loading
there reflects the incomplete network rather than conduit capacity: severity is
capped at LOW and confidence is LOW. Classes are model-diagnostic, relative
screening classes, not engineering failure thresholds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.gis.network_mapping import NetworkMapping
from app.simulation.inp_reader import InpModel
from app.simulation.report_parser import SwmmReport
from app.utils.timeutil import to_iso_z

CAPACITY_LIMITED_MIN_HOURS = 0.01  # SWMM prints 0.01 as the display floor of the surcharge table
FULL_BOTH_ENDS_MIN_HOURS = 1.0
PEAK_FLOW_RATIO_MIN = 1.0
CONNECTED_FLOODING_MIN_HOURS = 1.0
DERIVED_CAPACITY_MIN_RATIO = 0.5  # below this the 2-decimal SWMM ratio is too coarse to back-calculate capacity
N_CRITERIA = 4

SEVERITY_ORDER = ("LOW", "MODERATE", "HIGH")
CLEAN_INVERT_DECISIONS = {"ACCEPT_PROVISIONALLY", "RETAIN_GCC_INVERT"}
_WARNING_02 = re.compile(r"maximum depth increased for Node (\S+)")


class BottleneckAnalysisError(Exception):
    pass


@dataclass(frozen=True)
class NetworkComponents:
    """Connectivity of the model node-link graph (undirected)."""

    node_component: dict[str, int]
    components: list[dict[str, Any]]

    def has_outfall(self, node_id: str) -> bool:
        return bool(self.components[self.node_component[node_id] - 1]["outfalls"])


def network_components(inp: InpModel) -> NetworkComponents:
    adjacency: dict[str, set[str]] = {n: set() for n in inp.node_ids}
    for c in inp.conduits.values():
        adjacency[c["fromNode"]].add(c["toNode"])
        adjacency[c["toNode"]].add(c["fromNode"])
    node_component: dict[str, int] = {}
    components: list[dict[str, Any]] = []
    for start in inp.node_ids:  # model order -> deterministic component numbering
        if start in node_component:
            continue
        cid = len(components) + 1
        stack, members = [start], []
        node_component[start] = cid
        while stack:
            node = stack.pop()
            members.append(node)
            for other in sorted(adjacency[node]):
                if other not in node_component:
                    node_component[other] = cid
                    stack.append(other)
        members.sort()
        member_set = set(members)
        components.append(
            {
                "modelComponentId": cid,
                "nodes": members,
                "links": sorted(lid for lid, c in inp.conduits.items() if c["fromNode"] in member_set),
                "outfalls": [n for n in members if n in inp.outfalls],
            }
        )
    return NetworkComponents(node_component, components)


def _round(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(float(value), digits)


def analyse_bottlenecks(
    *,
    simulation_id: str,
    scenario_id: str,
    model_version: str,
    analysis_version: str,
    report: SwmmReport,
    inp: InpModel,
    network: NetworkMapping,
    components: NetworkComponents,
    source_conduits: dict[str, dict[str, str]],
    invert_decisions: dict[int, str],
    diagnostic_context: dict[str, Any],
    conduit_geometry: dict[str, dict[str, Any]],
    node_lonlat: dict[str, list[float]],
    generated_at: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (bottlenecks document, bottlenecks GeoJSON FeatureCollection)."""
    link_flow = {r["id"]: r for r in report.link_flow}
    surcharge = {r["id"]: r for r in report.conduit_surcharge}
    node_flooding = {r["id"]: r for r in report.node_flooding}
    node_surcharge = {r["id"]: r for r in report.node_surcharge}
    ts_critical = {e["id"]: e["percent"] for e in report.time_step_critical_elements if e["elementType"] == "LINK"}
    instability = {e["id"]: e["index"] for e in report.highest_flow_instability_indexes if e["elementType"] == "LINK"}
    warning02_nodes = {m.group(1) for w in report.warnings if w["code"] == "02" for m in [_WARNING_02.search(w["message"])] if m}
    context_links: dict[str, Any] = diagnostic_context.get("links", {})
    for lid, ctx in context_links.items():
        expected = ctx.get("sourceObjectId")
        if lid in network.link_to_object_id and expected is not None and network.link_to_object_id[lid] != expected:
            raise BottleneckAnalysisError(f"Diagnostic context for {lid} refers to ObjectID {expected}, model maps {network.link_to_object_id[lid]}")
    missing = [lid for lid in inp.conduits if lid not in link_flow]
    if missing:
        raise BottleneckAnalysisError(f"Link Flow Summary lacks conduits: {missing[:5]}")

    def node_evidence(node_id: str, role: str) -> dict[str, Any]:
        f = node_flooding.get(node_id)
        s = node_surcharge.get(node_id)
        return {
            "nodeId": node_id,
            "role": role,
            "nodeType": "OUTFALL" if node_id in inp.outfalls else "JUNCTION",
            "flooding": None if f is None else {
                "hoursFlooded": f["hoursFlooded"], "maximumRateCms": f["maximumRateCms"], "timeOfMaximum": f["timeOfMaximum"],
                "totalFloodVolumeMillionLiters": f["totalFloodVolumeMillionLiters"],
            },
            "surcharge": None if s is None else {"hoursSurcharged": s["hoursSurcharged"], "maxHeightAboveCrownM": s["maxHeightAboveCrownM"]},
            "swmmWarning02": node_id in warning02_nodes,
            "location": node_lonlat.get(node_id),
        }

    records: list[dict[str, Any]] = []
    for lid, conduit in inp.conduits.items():
        flow = link_flow[lid]
        sur = surcharge.get(lid)
        hours = {
            "hoursFullBothEnds": sur["hoursFullBothEnds"] if sur else 0.0,
            "hoursFullUpstream": sur["hoursFullUpstream"] if sur else 0.0,
            "hoursFullDownstream": sur["hoursFullDownstream"] if sur else 0.0,
            "hoursAboveFullNormalFlow": sur["hoursAboveFullNormalFlow"] if sur else 0.0,
            "hoursCapacityLimited": sur["hoursCapacityLimited"] if sur else 0.0,
        }
        ratio = flow["maxOverFullFlow"] or 0.0
        from_node, to_node = conduit["fromNode"], conduit["toNode"]
        ends = [node_evidence(from_node, "upstream (model direction)"), node_evidence(to_node, "downstream (model direction)")]
        flooding_ends = [e for e in ends if e["flooding"] and e["flooding"]["hoursFlooded"] >= CONNECTED_FLOODING_MIN_HOURS]
        criteria = [
            {
                "id": "L1", "label": "Capacity limited (SWMM)", "met": hours["hoursCapacityLimited"] > CAPACITY_LIMITED_MIN_HOURS,
                "value": hours["hoursCapacityLimited"], "unit": "hr", "threshold": f"> {CAPACITY_LIMITED_MIN_HOURS} h",
                "source": "SWMM report: Conduit Surcharge Summary (Hours Capacity Limited)",
            },
            {
                "id": "L2", "label": "Sustained full-bore surcharge", "met": hours["hoursFullBothEnds"] >= FULL_BOTH_ENDS_MIN_HOURS,
                "value": hours["hoursFullBothEnds"], "unit": "hr", "threshold": f">= {FULL_BOTH_ENDS_MIN_HOURS} h",
                "source": "SWMM report: Conduit Surcharge Summary (Hours Full Both Ends)",
            },
            {
                "id": "L3", "label": "Peak flow above full-flow capacity", "met": ratio > PEAK_FLOW_RATIO_MIN,
                "value": ratio, "unit": "ratio", "threshold": f"> {PEAK_FLOW_RATIO_MIN}",
                "source": "SWMM report: Link Flow Summary (Max/Full Flow)",
            },
            {
                "id": "S1", "label": "Connected node flooding", "met": bool(flooding_ends),
                "value": [e["nodeId"] for e in flooding_ends], "unit": "nodes", "threshold": f"end node floods >= {CONNECTED_FLOODING_MIN_HOURS} h",
                "source": "SWMM report: Node Flooding Summary",
            },
        ]
        if not any(c["met"] for c in criteria[:3]):
            continue
        met = sum(1 for c in criteria if c["met"])
        severity = "HIGH" if met >= 3 else "MODERATE" if met == 2 else "LOW"
        component_id = components.node_component[from_node]
        has_outfall = components.has_outfall(from_node)
        object_id = network.link_to_object_id[lid]
        src = source_conduits[lid]
        confidence_reasons: list[str] = []
        if not has_outfall:
            confidence_reasons.append("The conduit's network component has no model outfall, so water can only leave by overflow; loading reflects the incomplete network rather than conduit capacity.")
        decision = invert_decisions.get(object_id)
        if decision is not None and decision not in CLEAN_INVERT_DECISIONS:
            confidence_reasons.append(f"The GCC source invert of ObjectID {object_id} is flagged in the invert screening ({decision}).")
        if src.get("flow_direction") not in (None, "", "START_TO_END"):
            confidence_reasons.append(f"Source flow direction is {src.get('flow_direction')}.")
        warned = [e["nodeId"] for e in ends if e["swmmWarning02"]]
        if warned:
            confidence_reasons.append(f"SWMM raised the maximum depth of end node(s) {', '.join(warned)} to the conduit crown (Warning 02), i.e. the junction/conduit elevations are inconsistent.")
        if lid in context_links:
            confidence_reasons.append(f"Listed in the project's hydraulic investigations: {context_links[lid]['finding']}")
        uncapped = severity
        capped = not has_outfall and severity != "LOW"
        if not has_outfall:
            severity = "LOW"
        confidence = "LOW" if confidence_reasons else "MEDIUM"
        derived_capacity = flow["maximumFlowCms"] / ratio if ratio >= DERIVED_CAPACITY_MIN_RATIO else None
        xs = inp.xsections.get(lid, {})
        interpretation = _interpretation(hours, ratio, has_outfall)
        record = {
            "linkId": lid,
            "sourceObjectId": object_id,
            "identifierNote": "sourceObjectId is the GCC storm-water-drain ObjectID; linkId is the SWMM conduit that represents (part of) it.",
            "fromNodeId": from_node,
            "toNodeId": to_node,
            "severity": severity,
            "severityCappedByNetworkContext": capped,
            "uncappedSeverity": uncapped,
            "score": round(met / N_CRITERIA, 2),
            "criteriaMet": met,
            "criteria": criteria,
            "confidence": confidence,
            "confidenceReasons": confidence_reasons,
            "interpretation": interpretation["code"],
            "reason": interpretation["reason"],
            "conduit": {
                "modelLengthM": _round(conduit["lengthM"]),
                "sourceWidthM": _round(_float(src.get("width_m"))),
                "sourceDepthM": _round(_float(src.get("depth_m"))),
                "modelShape": xs.get("shape"),
                "modelFullDepthM": _round(xs.get("fullDepthM")),
                "roughness": conduit.get("roughness"),
            },
            "hydraulics": {
                "maximumFlowCms": flow["maximumFlowCms"],
                "timeOfMaximumFlow": flow["timeOfMaximum"],
                "maximumVelocityMps": flow["maximumVelocityMps"],
                "maxOverFullFlow": flow["maxOverFullFlow"],
                "maxOverFullDepth": flow["maxOverFullDepth"],
                "derivedFullFlowCapacityCms": _round(derived_capacity, 4),
                "derivedFullFlowCapacityNote": "Back-calculated as maximum flow / (Max/Full Flow); omitted when the ratio is < 0.5." if derived_capacity else None,
                **hours,
            },
            "numericalDiagnostics": {"timeStepCriticalPercent": ts_critical.get(lid), "flowInstabilityIndex": instability.get(lid)},
            "connectedNodes": ends,
            "networkContext": {
                "modelComponentId": component_id,
                "componentHasOutfall": has_outfall,
                "componentOutfalls": components.components[component_id - 1]["outfalls"],
                "componentNodeCount": len(components.components[component_id - 1]["nodes"]),
                "outfallNote": "Model outfalls are provisional boundary terminals, not confirmed physical outfalls.",
            },
            "sourceAttributes": {
                "objectId": object_id,
                "status": src.get("status") or None,
                "puccaKacha": src.get("puca_kacha") or None,
                "drainDetail": src.get("drain_detail") or None,
                "invertScreeningDecision": decision,
            },
            "projectInvestigation": context_links.get(lid),
            "explanation": _explanation(lid, object_id, severity, criteria, hours, ratio, flooding_ends, has_outfall, interpretation),
        }
        records.append(record)

    records.sort(key=lambda r: (-SEVERITY_ORDER.index(r["severity"]), -r["score"], -r["hydraulics"]["hoursCapacityLimited"], -r["hydraulics"]["hoursFullBothEnds"], -(r["hydraulics"]["maxOverFullFlow"] or 0), r["linkId"]))
    for rank, r in enumerate(records, start=1):
        r["rank"] = rank

    numerical = []
    for lid in sorted(set(ts_critical) | set(instability) | set(context_links), key=lambda x: (-(ts_critical.get(x) or 0), -(instability.get(x) or 0), x)):
        if lid not in inp.conduits:
            continue
        c = inp.conduits[lid]
        flow = link_flow[lid]
        sur = surcharge.get(lid)
        has_outfall = components.has_outfall(c["fromNode"])
        numerical.append(
            {
                "linkId": lid,
                "sourceObjectId": network.link_to_object_id[lid],
                "fromNodeId": c["fromNode"],
                "toNodeId": c["toNode"],
                "timeStepCriticalPercent": ts_critical.get(lid),
                "flowInstabilityIndex": instability.get(lid),
                "isPotentialBottleneck": any(r["linkId"] == lid for r in records),
                "maxOverFullFlow": flow["maxOverFullFlow"],
                "maxOverFullDepth": flow["maxOverFullDepth"],
                "hoursFullBothEnds": sur["hoursFullBothEnds"] if sur else 0.0,
                "hoursCapacityLimited": sur["hoursCapacityLimited"] if sur else 0.0,
                "modelComponentId": components.node_component[c["fromNode"]],
                "componentHasOutfall": has_outfall,
                "interpretation": (
                    "Numerical diagnostic of the Dynamic Wave solver (short conduit / junction elevation sensitivity). "
                    "It is not evidence of hydraulic capacity limitation"
                    + ("" if any(r["linkId"] == lid for r in records) else "; SWMM loading criteria L1-L3 are not met for this link")
                    + ("." if has_outfall else "; its network component has no model outfall.")
                ),
                "projectInvestigation": context_links.get(lid),
            }
        )

    metadata = {
        "simulationId": simulation_id,
        "scenarioId": scenario_id,
        "modelVersion": model_version,
        "bottleneckAnalysisVersion": analysis_version,
        "dataType": "model-derived",
        "method": "docs/DECISION_SUPPORT_METHOD.md",
        "generatedAt": to_iso_z(generated_at),
    }
    counts = {s: sum(1 for r in records if r["severity"] == s) for s in SEVERITY_ORDER}
    document = {
        **metadata,
        "terminology": "Potential drainage bottleneck: a model-derived diagnostic based on SWMM hydraulic loading. Not a confirmed or field-verified drainage failure.",
        "criteriaDefinition": {
            "L1": f"SWMM Hours Capacity Limited > {CAPACITY_LIMITED_MIN_HOURS} h (upstream end full and hydraulic gradient steeper than the conduit slope)",
            "L2": f"SWMM Hours Full Both Ends >= {FULL_BOTH_ENDS_MIN_HOURS} h",
            "L3": f"SWMM Max/Full Flow > {PEAK_FLOW_RATIO_MIN}",
            "S1": f"An end node floods for >= {CONNECTED_FLOODING_MIN_HOURS} h (supporting evidence only)",
            "eligibility": "At least one of L1-L3 must be met.",
            "score": "criteria met / 4",
            "severity": "HIGH >= 3 criteria, MODERATE = 2, LOW = 1; capped at LOW when the component has no model outfall",
            "confidence": "MEDIUM when no data-quality or network caveat applies, otherwise LOW. HIGH is not assigned in v1 (uncalibrated model, provisional outfalls).",
        },
        "legend": [
            {"severity": "HIGH", "label": "High diagnostic concern"},
            {"severity": "MODERATE", "label": "Moderate diagnostic concern"},
            {"severity": "LOW", "label": "Low diagnostic concern"},
        ],
        "summary": {
            "conduitsScreened": len(inp.conduits),
            "potentialBottlenecks": len(records),
            "bySeverity": counts,
            "inComponentsWithoutOutfall": sum(1 for r in records if not r["networkContext"]["componentHasOutfall"]),
            "modelComponents": len(components.components),
            "modelComponentsWithOutfall": sum(1 for c in components.components if c["outfalls"]),
        },
        "bottlenecks": records,
        "derivedFullFlowCapacities": {
            lid: round(link_flow[lid]["maximumFlowCms"] / link_flow[lid]["maxOverFullFlow"], 4)
            for lid in inp.conduits
            if (link_flow[lid]["maxOverFullFlow"] or 0) >= DERIVED_CAPACITY_MIN_RATIO
        },
        "numericalDiagnostics": numerical,
        "limitations": [
            "Evidence is from one uncalibrated SWMM simulation of a reconstructed, fragmented network with provisional outfalls.",
            "SWMM report durations are integrated at routing-step resolution; hours below 0.01 are displayed as 0.01 by SWMM.",
            "Surcharge caused by downstream (backwater) conditions can make a conduit full without that conduit being the restriction; L1 is the only criterion that isolates the conduit itself.",
            "Numerical solver diagnostics (time-step criticality, flow instability) are reported separately and never raise a bottleneck.",
        ],
    }

    features = []
    for r in records:
        geometry = conduit_geometry.get(r["linkId"])
        if geometry is None:
            raise BottleneckAnalysisError(f"No model geometry for conduit {r['linkId']}")
        features.append(
            {
                "type": "Feature",
                "id": r["linkId"],
                "geometry": geometry,
                "properties": {
                    "featureType": "potentialBottleneck",
                    "linkId": r["linkId"],
                    "sourceObjectId": r["sourceObjectId"],
                    "fromNodeId": r["fromNodeId"],
                    "toNodeId": r["toNodeId"],
                    "severity": r["severity"],
                    "score": r["score"],
                    "confidence": r["confidence"],
                    "rank": r["rank"],
                    "componentHasOutfall": r["networkContext"]["componentHasOutfall"],
                    "floodingNodeIds": r["criteria"][3]["value"],
                },
            }
        )
    geojson = {"type": "FeatureCollection", "metadata": {**metadata, "crs": "OGC:CRS84 (RFC 7946 longitude, latitude)", "featureCount": len(features)}, "features": features}
    return document, geojson


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _interpretation(hours: dict[str, float], ratio: float, has_outfall: bool) -> dict[str, str]:
    if not has_outfall:
        return {
            "code": "LOADING_IN_COMPONENT_WITHOUT_OUTFALL",
            "reason": "Hydraulic loading in a drainage component that has no outlet in the model; likely a consequence of missing network connectivity.",
        }
    if hours["hoursCapacityLimited"] > CAPACITY_LIMITED_MIN_HOURS:
        return {"code": "CAPACITY_LIMITED", "reason": "SWMM reports this conduit as capacity limited: its upstream end is full while the hydraulic gradient exceeds the conduit slope."}
    if hours["hoursFullBothEnds"] >= FULL_BOTH_ENDS_MIN_HOURS:
        return {
            "code": "SUSTAINED_SURCHARGE",
            "reason": "The conduit runs full at both ends for a sustained period, but SWMM does not classify it as capacity limited; downstream conditions may control the surcharge.",
        }
    return {"code": "PEAK_FLOW_ABOVE_FULL_FLOW", "reason": "Peak flow exceeds the conduit's full normal-flow capacity without sustained surcharge."}


def _explanation(
    lid: str, object_id: int, severity: str, criteria: list[dict[str, Any]], hours: dict[str, float], ratio: float,
    flooding_ends: list[dict[str, Any]], has_outfall: bool, interpretation: dict[str, str],
) -> dict[str, Any]:
    met = [c for c in criteria if c["met"]]
    evidence = []
    if criteria[0]["met"]:
        evidence.append(f"capacity limited for {hours['hoursCapacityLimited']:.2f} h")
    if criteria[1]["met"]:
        evidence.append(f"full at both ends for {hours['hoursFullBothEnds']:.2f} h")
    if criteria[2]["met"]:
        evidence.append(f"peak flow {ratio:.2f}x its full-flow capacity")
    for e in flooding_ends:
        evidence.append(f"connected node {e['nodeId']} floods for {e['flooding']['hoursFlooded']:.1f} h")
    why = f"{lid} meets {len(met)} of 4 screening criteria in the simulated event: " + "; ".join(evidence) + "."
    if not has_outfall:
        why += " Its drainage component has no outlet in the model, so the loading mainly reflects missing network connectivity."
    consider = (
        "Verify the downstream connection/outfall of this drainage component before assessing conduit capacity."
        if not has_outfall
        else "Assess the hydraulic capacity and condition of this drainage segment and its downstream corridor in the field before any intervention."
    )
    return {
        "whatIsThis": f"SWMM conduit {lid}, representing GCC storm-water drain ObjectID {object_id}, flagged as a potential drainage bottleneck ({severity.lower()} diagnostic concern).",
        "whyFlagged": why,
        "interpretation": interpretation["reason"],
        "sourceData": "GCC storm-water drain geometry and attributes → reconstructed conduit → EPA SWMM 5.2.4 simulation report of this run.",
        "plannerConsideration": consider,
        "disclaimer": "Model-derived diagnostic from an uncalibrated candidate model; not a confirmed real-world drainage failure.",
    }
