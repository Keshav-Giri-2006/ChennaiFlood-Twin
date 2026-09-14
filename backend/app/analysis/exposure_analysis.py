"""exposure-analysis-v1: assets within model-derived flood influence zones.

Full documentation: docs/DECISION_SUPPORT_METHOD.md (section 4).

"Exposed" means only: the GCC building footprint / carriageway polygon spatially
intersects (positive area) the flood influence zone of a model node that is
overflowing (flood-processing-v1 state FLOODING) at the considered reporting
timestamp(s). Influence zones are nearest-drainage-node associations, not flood
extents, so exposure is NOT flooding, damage or impact.

All geometry operations run in EPSG:32644 on unsimplified source geometry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from shapely import STRtree
from shapely.geometry.base import BaseGeometry

from app.utils.timeutil import to_iso_z

MIN_INTERSECTION_AREA_M2 = 0.01  # numerical tolerance: shared zone edges produce zero-area touches


class ExposureAnalysisError(Exception):
    pass


@dataclass(frozen=True)
class Asset:
    object_id: int
    geometry: BaseGeometry
    name: str | None = None


def _intersections(zone: BaseGeometry, assets: list[Asset], tree: STRtree) -> dict[int, float]:
    hits: dict[int, float] = {}
    for i in tree.query(zone, predicate="intersects"):
        area = assets[int(i)].geometry.intersection(zone).area
        if area > MIN_INTERSECTION_AREA_M2:
            hits[assets[int(i)].object_id] = area
    return hits


def _pct(part: float, whole: float) -> float | None:
    return round(100.0 * part / whole, 2) if whole else None


def analyse_exposure(
    *,
    simulation_id: str,
    scenario_id: str,
    model_version: str,
    analysis_version: str,
    flood_processing_version: str,
    zones_utm: dict[str, BaseGeometry],
    times: list[str],
    flooding_nodes_by_period: list[list[str]],
    peak_index: int,
    interval_minutes: int,
    buildings: list[Asset],
    roads: list[Asset],
    node_component: dict[str, int],
    component_has_outfall: dict[int, bool],
    generated_at: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (exposure document, per-node asset association document)."""
    if len(times) != len(flooding_nodes_by_period):
        raise ExposureAnalysisError("Timeline and flooding node periods differ in length")
    for label, assets in (("buildings", buildings), ("roads", roads)):
        ids = [a.object_id for a in assets]
        if len(ids) != len(set(ids)):
            raise ExposureAnalysisError(f"Duplicate source ObjectIDs in {label}")
        if not all(a.geometry.is_valid for a in assets):
            raise ExposureAnalysisError(f"Invalid source geometry in {label}")

    b_tree, r_tree = STRtree([a.geometry for a in buildings]), STRtree([a.geometry for a in roads])
    building_area = {a.object_id: a.geometry.area for a in buildings}
    road_area = {a.object_id: a.geometry.area for a in roads}
    road_name = {a.object_id: a.name for a in roads}
    total_building_area = sum(building_area.values())
    total_road_area = sum(road_area.values())

    ever = sorted({n for period in flooding_nodes_by_period for n in period})
    node_assets: dict[str, dict[str, dict[int, float]]] = {}
    for node in ever:
        zone = zones_utm.get(node)
        if zone is None or zone.is_empty:
            node_assets[node] = {"buildings": {}, "roads": {}}
            continue
        node_assets[node] = {"buildings": _intersections(zone, buildings, b_tree), "roads": _intersections(zone, roads, r_tree)}

    def scope(nodes: list[str]) -> dict[str, Any]:
        b: dict[int, float] = {}
        r: dict[int, float] = {}
        b_no_outfall: set[int] = set()
        for n in nodes:
            no_outfall = not component_has_outfall[node_component[n]]
            for oid, area in node_assets[n]["buildings"].items():
                b[oid] = b.get(oid, 0.0) + area  # zones do not overlap: areas add without double counting
                if no_outfall:
                    b_no_outfall.add(oid)
            for oid, area in node_assets[n]["roads"].items():
                r[oid] = r.get(oid, 0.0) + area
        b_area = sum(b.values())
        r_area = sum(r.values())
        return {
            "floodingNodeCount": len(nodes),
            "buildings": {
                "intersectingCount": len(b),
                "percentOfBuildings": _pct(len(b), len(buildings)),
                "footprintAreaWithinZonesM2": round(b_area, 1),
                "percentOfFootprintArea": _pct(b_area, total_building_area),
                "intersectingZonesOfNodesWithoutOutfallCount": len(b_no_outfall),
            },
            "roads": {
                "intersectingCount": len(r),
                "percentOfRoadFeatures": _pct(len(r), len(roads)),
                "areaWithinZonesM2": round(r_area, 1),
                "percentOfRoadArea": _pct(r_area, total_road_area),
            },
        }

    timeline = []
    for index, (time, nodes) in enumerate(zip(times, flooding_nodes_by_period, strict=True)):
        s = scope(nodes)
        timeline.append(
            {
                "index": index,
                "time": time,
                "floodingNodeCount": s["floodingNodeCount"],
                "buildingsIntersecting": s["buildings"]["intersectingCount"],
                "buildingFootprintAreaM2": s["buildings"]["footprintAreaWithinZonesM2"],
                "roadsIntersecting": s["roads"]["intersectingCount"],
                "roadAreaM2": s["roads"]["areaWithinZonesM2"],
            }
        )
    event = scope(ever)
    for key, bucket in (("buildings", event["buildings"]), ("roads", event["roads"])):
        total_area = total_building_area if key == "buildings" else total_road_area
        if bucket.get("footprintAreaWithinZonesM2", bucket.get("areaWithinZonesM2")) > total_area + 1.0:
            raise ExposureAnalysisError(f"Exposed {key} area exceeds the total source area")

    step_hours = interval_minutes / 60.0
    periods_flooding = {n: sum(1 for p in flooding_nodes_by_period if n in p) for n in ever}
    by_node = []
    for n in ever:
        b = node_assets[n]["buildings"]
        r = node_assets[n]["roads"]
        names = sorted({road_name[oid] for oid in r if road_name.get(oid)})
        by_node.append(
            {
                "nodeId": n,
                "zoneAreaM2": round(zones_utm[n].area, 1) if n in zones_utm else None,
                "reportingPeriodsFlooding": periods_flooding[n],
                "hoursFloodingSampled": round(periods_flooding[n] * step_hours, 2),
                "buildingsIntersecting": len(b),
                "buildingFootprintAreaM2": round(sum(b.values()), 1),
                "roadsIntersecting": len(r),
                "roadAreaM2": round(sum(r.values()), 1),
                "roadNames": names,
                "modelComponentId": node_component[n],
                "componentHasOutfall": component_has_outfall[node_component[n]],
            }
        )
    by_node.sort(key=lambda x: (-x["buildingsIntersecting"], x["nodeId"]))

    max_b = max(timeline, key=lambda e: (e["buildingsIntersecting"], -e["index"]))
    max_r = max(timeline, key=lambda e: (e["roadAreaM2"], -e["index"]))
    metadata = {
        "simulationId": simulation_id,
        "scenarioId": scenario_id,
        "modelVersion": model_version,
        "exposureAnalysisVersion": analysis_version,
        "floodProcessingVersion": flood_processing_version,
        "dataType": "model-derived",
        "method": "docs/DECISION_SUPPORT_METHOD.md",
        "processingCrs": "EPSG:32644",
        "generatedAt": to_iso_z(generated_at),
    }
    document = {
        **metadata,
        "terminology": "Model-derived exposure: assets spatially intersecting flood influence zones of overflowing model nodes. Not flooded, damaged or affected assets.",
        "definition": {
            "influenceZone": "Nearest-model-node (Voronoi) cell clipped to Ward 176 (flood-processing-v1); a spatial association, not a flood extent.",
            "intersecting": f"Intersection area > {MIN_INTERSECTION_AREA_M2} m2 with at least one zone of a node in FLOODING state.",
            "eventScope": "Nodes overflowing at one or more 30-minute reporting timestamps.",
            "roadMeasure": "Carriageways are GCC polygons: exposure is reported as polygon area and feature count. A road length is not derived.",
        },
        "totals": {
            "buildings": {"count": len(buildings), "footprintAreaM2": round(total_building_area, 1)},
            "roads": {"count": len(roads), "areaM2": round(total_road_area, 1)},
        },
        "event": event,
        "peak": {"index": peak_index, "time": times[peak_index], **scope(flooding_nodes_by_period[peak_index])},
        "maxConcurrent": {
            "buildingsIntersecting": {"value": max_b["buildingsIntersecting"], "time": max_b["time"], "index": max_b["index"]},
            "roadAreaM2": {"value": max_r["roadAreaM2"], "time": max_r["time"], "index": max_r["index"]},
        },
        "timeline": timeline,
        "byNode": by_node,
        "limitations": [
            "Influence zones associate every location with its nearest modelled drainage node regardless of distance or terrain; sparse drainage produces large zones.",
            "No ground flood depth or extent exists in flood-processing-v1, so exposure cannot distinguish inundated from dry locations within a zone.",
            "Overflowing nodes in drainage components without a model outfall reflect missing network connectivity; exposure associated with them inherits that artifact (see intersectingZonesOfNodesWithoutOutfallCount and byNode.componentHasOutfall).",
            "Building heights, occupancy, use and value are not available; no damage, loss or casualty estimate is derived.",
        ],
    }
    associations = {
        **metadata,
        "periods": flooding_nodes_by_period,
        "times": times,
        "nodes": {
            n: {"buildings": sorted([oid, round(a, 2)] for oid, a in v["buildings"].items()), "roads": sorted([oid, round(a, 2)] for oid, a in v["roads"].items())}
            for n, v in node_assets.items()
        },
    }
    return document, associations
