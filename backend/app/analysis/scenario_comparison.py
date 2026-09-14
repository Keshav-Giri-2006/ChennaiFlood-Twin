"""scenario-analysis-v1: comparison of two completed simulations of the same model and scenario family.

Full documentation: docs/SCENARIO_ANALYSIS_METHOD.md. Every compared value is read from each
run's own stored products (results, flood, bottleneck, exposure and recommendation products);
nothing is re-derived with the other run's parameters. Recommendations are compared by their
deterministic rule IDs, bottlenecks by SWMM link ID.

Flood influence is compared categorically per model node (overflowing in both runs, only in the
scenario, only in the baseline), because the LOW/MODERATE/HIGH overflow classes of
flood-processing-v1 are percentile classes relative to each run and must not be compared as a
shared scale. Absolute overflow rates (m3/s) are reported for both runs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.utils.timeutil import to_iso_z

SEVERITY_RANK = {"LOW": 1, "MODERATE": 2, "HIGH": 3}
PRIORITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


class ComparisonError(ValueError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.details = details


def _change(baseline: float | int | None, scenario: float | int | None, digits: int = 3) -> tuple[float | None, float | None]:
    if baseline is None or scenario is None:
        return None, None
    absolute = round(scenario - baseline, digits)
    percent = round(100.0 * (scenario - baseline) / baseline, 1) if baseline else None
    return absolute, percent


def _label(run: dict[str, Any]) -> str:
    if run["executionMode"] == "precomputed-demo":
        return "Baseline 1.00× (precomputed demonstration result)"
    m = run["rainfallMultiplier"]
    return "Baseline 1.00× (historical rainfall)" if m == 1.0 else f"{m:.2f}× rainfall multiplier (what-if)"


def _rank_change(a: str, b: str, ranks: dict[str, int]) -> str:
    return "unchanged" if ranks[a] == ranks[b] else "increased" if ranks[b] > ranks[a] else "reduced"


def compare_runs(baseline: dict[str, Any], scenario: dict[str, Any], version: str, generated_at: datetime) -> dict[str, Any]:
    """``baseline``/``scenario``: dicts with keys run, kpis, flood, results, bottlenecks, exposure, assets, recommendations."""
    b_run, s_run = baseline["run"], scenario["run"]
    if b_run["simulationId"] == s_run["simulationId"]:
        raise ComparisonError("A simulation cannot be compared with itself.")
    for key in ("modelVersion", "scenarioId", "processingVersion"):
        if b_run[key] != s_run[key]:
            raise ComparisonError(f"Simulations differ in {key} and cannot be compared.", {key: [b_run[key], s_run[key]]})
    versions = {
        "floodProcessingVersion": (baseline["flood"]["metadata"]["floodProcessingVersion"], scenario["flood"]["metadata"]["floodProcessingVersion"]),
        "bottleneckAnalysisVersion": (baseline["bottlenecks"]["bottleneckAnalysisVersion"], scenario["bottlenecks"]["bottleneckAnalysisVersion"]),
        "exposureAnalysisVersion": (baseline["exposure"]["exposureAnalysisVersion"], scenario["exposure"]["exposureAnalysisVersion"]),
        "decisionSupportVersion": (baseline["recommendations"]["decisionSupportVersion"], scenario["recommendations"]["decisionSupportVersion"]),
    }
    mismatched = {k: v for k, v in versions.items() if v[0] != v[1]}
    if mismatched:
        raise ComparisonError("Simulations were processed with different method versions and cannot be compared.", mismatched)
    if baseline["assets"]["times"] != scenario["assets"]["times"]:
        raise ComparisonError("Simulations have different reporting timestamps and cannot be compared.")

    def q(doc: dict[str, Any], group: str, key: str) -> Any:
        item = doc["kpis"].get(group, {}).get(key)
        return None if item is None else item.get("value")

    def fm(doc: dict[str, Any], key: str) -> Any:
        return doc["flood"]["metrics"][key]["value"]

    metric_specs = [
        ("totalRainfall", "Total rainfall", "mm", lambda d: q(d, "rainfall", "total"), "source × multiplier"),
        ("peakRainfallIntensity", "Peak rainfall intensity", "mm/hr", lambda d: q(d, "rainfall", "peakIntensity"), "source × multiplier"),
        ("floodedNodesEvent", "Nodes with overflow (event)", "count", lambda d: q(d, "drainage", "floodedNodes"), "model-derived"),
        ("peakConcurrentFloodingNodes", "Peak flooding nodes", "count", lambda d: fm(d, "peakConcurrentFloodingNodes"), "model-derived"),
        ("peakSystemFloodingRate", "Peak overflow rate", "m3/s", lambda d: fm(d, "peakSystemFloodingRate"), "model-derived"),
        ("maximumNodeWaterDepth", "Maximum simulated node water depth (in-network, not ground depth)", "m", lambda d: fm(d, "maximumNodeWaterDepth"), "model-derived"),
        ("floodingDuration", "Flooding duration", "hr", lambda d: fm(d, "floodingDuration"), "model-derived"),
        ("simulatedFloodingVolume", "Simulated flooding volume (model diagnostic, not observed)", "L", lambda d: q(d, "hydraulics", "simulatedFloodingVolume"), "model-derived"),
        ("potentialBottlenecks", "Potential bottlenecks", "count", lambda d: d["bottlenecks"]["summary"]["potentialBottlenecks"], "model-derived"),
        ("highPotentialBottlenecks", "High-concern potential bottlenecks", "count", lambda d: d["bottlenecks"]["summary"]["bySeverity"]["HIGH"], "model-derived"),
        ("buildingsExposedEvent", "Model-derived building exposure (any timestamp)", "count", lambda d: d["exposure"]["event"]["buildings"]["intersectingCount"], "model-derived"),
        ("buildingsExposedPeak", "Model-derived building exposure (peak timestamp)", "count", lambda d: d["exposure"]["peak"]["buildings"]["intersectingCount"], "model-derived"),
        ("roadFeaturesExposedEvent", "Model-derived road exposure (carriageways, any timestamp)", "count", lambda d: d["exposure"]["event"]["roads"]["intersectingCount"], "model-derived"),
        ("roadAreaExposedEvent", "Model-derived road exposure area (any timestamp)", "m2", lambda d: d["exposure"]["event"]["roads"]["areaWithinZonesM2"], "model-derived"),
        ("recommendations", "Recommendations", "count", lambda d: d["recommendations"]["summary"]["total"], "model-derived"),
        ("highPriorityRecommendations", "High-priority recommendations", "count", lambda d: d["recommendations"]["summary"]["byPriority"]["HIGH"], "model-derived"),
    ]
    metrics = []
    for key, label, unit, getter, source in metric_specs:
        try:
            bv, sv = getter(baseline), getter(scenario)
        except (KeyError, TypeError):
            continue
        if bv is None or sv is None:
            continue  # only metrics available in both runs
        absolute, percent = _change(bv, sv)
        metrics.append({"key": key, "label": label, "unit": unit, "source": source, "baseline": bv, "scenario": sv, "absoluteChange": absolute, "percentChange": percent})

    # ---- flood influence (categorical per node) ---------------------------------------------------
    def split(b_nodes: list[str], s_nodes: list[str]) -> dict[str, list[str]]:
        bs, ss = set(b_nodes), set(s_nodes)
        return {"both": sorted(bs & ss), "scenarioOnly": sorted(ss - bs), "baselineOnly": sorted(bs - ss)}

    b_periods, s_periods = baseline["assets"]["periods"], scenario["assets"]["periods"]
    timeline = [{"index": i, "time": t, **split(b_periods[i], s_periods[i])} for i, t in enumerate(baseline["assets"]["times"])]
    event = split(sorted({n for p in b_periods for n in p}), sorted({n for p in s_periods for n in p}))
    peak_rates = {}
    for label, doc in (("baseline", baseline), ("scenario", scenario)):
        for row in doc["results"]["nodes"]["flooding"]:
            peak_rates.setdefault(row["id"], {"nodeId": row["id"], "baselineMaximumRateCms": None, "scenarioMaximumRateCms": None})[f"{label}MaximumRateCms"] = row["maximumRateCms"]

    # ---- bottlenecks ---------------------------------------------------------------------------------
    b_bn = {b["linkId"]: b for b in baseline["bottlenecks"]["bottlenecks"]}
    s_bn = {b["linkId"]: b for b in scenario["bottlenecks"]["bottlenecks"]}
    bottlenecks = {
        "new": [{"linkId": l, "sourceObjectId": s_bn[l]["sourceObjectId"], "scenarioSeverity": s_bn[l]["severity"], "confidence": s_bn[l]["confidence"]} for l in sorted(s_bn, key=lambda x: (-SEVERITY_RANK[s_bn[x]["severity"]], x)) if l not in b_bn],
        "persisting": [
            {"linkId": l, "sourceObjectId": s_bn[l]["sourceObjectId"], "baselineSeverity": b_bn[l]["severity"], "scenarioSeverity": s_bn[l]["severity"], "change": _rank_change(b_bn[l]["severity"], s_bn[l]["severity"], SEVERITY_RANK)}
            for l in sorted(s_bn, key=lambda x: (-SEVERITY_RANK[s_bn[x]["severity"]], x)) if l in b_bn
        ],
        "notFlaggedInScenario": [{"linkId": l, "sourceObjectId": b_bn[l]["sourceObjectId"], "baselineSeverity": b_bn[l]["severity"]} for l in sorted(b_bn) if l not in s_bn],
    }

    # ---- exposure ------------------------------------------------------------------------------------
    b_ids = {oid for n in event["both"] + event["baselineOnly"] for oid, _a in baseline["assets"]["nodes"][n]["buildings"]}
    s_ids = {oid for n in event["both"] + event["scenarioOnly"] for oid, _a in scenario["assets"]["nodes"][n]["buildings"]}
    exposure = {
        "buildingsEvent": {"baseline": len(b_ids), "scenario": len(s_ids), "additionalInScenario": len(s_ids - b_ids), "notAssociatedInScenario": len(b_ids - s_ids)},
        "buildingsPeak": {"baseline": baseline["exposure"]["peak"]["buildings"]["intersectingCount"], "scenario": scenario["exposure"]["peak"]["buildings"]["intersectingCount"]},
        "roadAreaEventM2": {"baseline": baseline["exposure"]["event"]["roads"]["areaWithinZonesM2"], "scenario": scenario["exposure"]["event"]["roads"]["areaWithinZonesM2"]},
        "linkedToComponentsWithoutOutfall": {
            "baseline": baseline["exposure"]["event"]["buildings"]["intersectingZonesOfNodesWithoutOutfallCount"],
            "scenario": scenario["exposure"]["event"]["buildings"]["intersectingZonesOfNodesWithoutOutfallCount"],
        },
        "terminology": "Model-derived exposure (spatial intersection with flood influence zones of overflowing nodes); not damage.",
    }

    # ---- recommendations -------------------------------------------------------------------------------
    b_rec = {r["id"]: r for r in baseline["recommendations"]["recommendations"]}
    s_rec = {r["id"]: r for r in scenario["recommendations"]["recommendations"]}
    order = lambda ids, src: sorted(ids, key=lambda x: (-PRIORITY_RANK[src[x]["priority"]], x))  # noqa: E731
    recommendations = {
        "new": [{"id": i, "rule": s_rec[i]["rule"], "title": s_rec[i]["title"], "scenarioPriority": s_rec[i]["priority"]} for i in order([i for i in s_rec if i not in b_rec], s_rec)],
        "persisting": [
            {"id": i, "rule": s_rec[i]["rule"], "title": s_rec[i]["title"], "baselinePriority": b_rec[i]["priority"], "scenarioPriority": s_rec[i]["priority"], "change": _rank_change(b_rec[i]["priority"], s_rec[i]["priority"], PRIORITY_RANK)}
            for i in order([i for i in s_rec if i in b_rec], s_rec)
        ],
        "notTriggeredInScenario": [{"id": i, "rule": b_rec[i]["rule"], "title": b_rec[i]["title"], "baselinePriority": b_rec[i]["priority"]} for i in order([i for i in b_rec if i not in s_rec], b_rec)],
        "note": "Recommendations are generated independently from each run's own evidence and matched by their deterministic rule IDs.",
    }

    # ---- plain-language statements (only from the values above) ----------------------------------------
    s_label = f"{s_run['rainfallMultiplier']:.2f}× rainfall scenario"
    statements = []
    for p in bottlenecks["persisting"]:
        if p["scenarioSeverity"] == "HIGH" and p["baselineSeverity"] == "HIGH":
            statements.append(f"{p['linkId']} remains a high-concern potential bottleneck under both runs.")
    if bottlenecks["new"]:
        listed = ", ".join(f"{n['linkId']} ({n['scenarioSeverity'].lower()})" for n in bottlenecks["new"])
        statements.append(f"Additional potential hydraulic constraint(s) under the {s_label}: {listed}.")
    raised = [p for p in bottlenecks["persisting"] if p["change"] == "increased"]
    if raised:
        statements.append("Higher diagnostic concern under the " + s_label + ": " + ", ".join(f"{p['linkId']} ({p['baselineSeverity'].lower()} → {p['scenarioSeverity'].lower()})" for p in raised) + ".")
    if event["scenarioOnly"]:
        statements.append(f"Additional model-derived flood influence at node(s) {', '.join(event['scenarioOnly'])} (overflowing only under the {s_label}).")
    if exposure["buildingsEvent"]["additionalInScenario"]:
        statements.append(f"{exposure['buildingsEvent']['additionalInScenario']} additional buildings are associated with overflowing-node influence zones under the {s_label} (model-derived exposure, not damage).")
    if recommendations["new"]:
        statements.append(f"{len(recommendations['new'])} additional recommendation(s) are triggered by the {s_label} evidence.")

    runs = {"baseline": {**b_run, "label": _label(b_run)}, "scenario": {**s_run, "label": _label(s_run)}}
    return {
        "comparisonId": f"{b_run['simulationId']}__{s_run['simulationId']}",
        "scenarioAnalysisVersion": version,
        "generatedAt": to_iso_z(generated_at),
        "dataType": "model-derived",
        "method": "docs/SCENARIO_ANALYSIS_METHOD.md",
        "terminology": "What-if rainfall sensitivity comparison of two model runs. Not a forecast, warning or climate projection.",
        "simulations": [b_run["simulationId"], s_run["simulationId"]],
        **runs,
        "methodVersions": {k: v[0] for k, v in versions.items()},
        "metrics": metrics,
        "floodInfluence": {
            "definition": "Per model node: overflowing in both runs, only in the scenario ('additional model-derived flood influence') or only in the baseline. Influence zones are nearest-node associations, not flood extent.",
            "event": event,
            "peak": {"index": baseline["flood"]["peakIndex"], "scenarioPeakIndex": scenario["flood"]["peakIndex"], **split(b_periods[baseline["flood"]["peakIndex"]], s_periods[baseline["flood"]["peakIndex"]])},
            "timeline": timeline,
            "nodeMaximumOverflowRates": sorted(peak_rates.values(), key=lambda r: r["nodeId"]),
            "sharedScale": {
                "note": "Overflow classes (LOW/MODERATE/HIGH) are percentile classes relative to each run and are NOT a shared scale. Compare absolute overflow rates (m3/s) or the categorical comparison layer.",
                "baselineOverflowClasses": baseline["flood"]["legend"]["overflowClasses"],
                "scenarioOverflowClasses": scenario["flood"]["legend"]["overflowClasses"],
            },
        },
        "bottlenecks": bottlenecks,
        "exposure": exposure,
        "recommendations": recommendations,
        "statements": statements,
        "limitations": [
            "Both runs use the same uncalibrated candidate model, provisional outfalls and incomplete network; differences are model sensitivities, not predictions.",
            "A uniform rainfall multiplier changes intensities only; spatial and temporal rainfall patterns are unchanged.",
            "Hydraulic responses need not scale linearly with rainfall; overflow is lost from the model (no ponding).",
        ],
    }
