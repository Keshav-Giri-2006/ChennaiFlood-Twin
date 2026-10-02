"""location-check-v1: model-derived flood response around a user-selected location.

Location-specific historical flood analysis using the model-derived response
around a user-selected point. Nothing new is simulated: the result is a spatial
query over the flood-processing-v1 node states of one completed SWMM run.

Method (full documentation: docs/LOCATION_CHECK_METHOD.md)

1. The selected WGS 84 position is projected to EPSG:32644 (metres); every
   distance, buffer and intersection is computed there. Points outside the
   Ward 176 boundary are rejected: the model has no data outside the ward.
2. Nearest modelled drainage node = the model node at the smallest planar
   distance. By construction it is also the node whose nearest-node influence
   zone (flood-processing-v1) contains the location.
3. Surrounding area = circle of ``radius`` metres around the location,
   clipped to Ward 176. Nodes are associated with it through their influence
   zones: a node is associated when its zone overlaps the surrounding area.
4. Node responses use the flood-processing-v1 state definitions (FLOODING =
   SWMM node overflow rate > 0; SURCHARGED = water above the highest connected
   conduit crown without overflow) at the SWMM reporting timestamps.

Not derived: ground flood depth and flood extent (see flood-processing-v1), and
anything property-specific. The result is not an observation, a property
assessment, a flood certification or a prediction.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from app.analysis.flood_processing import NodeStates
from app.utils.timeutil import to_iso_z

MIN_ASSOCIATION_AREA_M2 = 1.0  # ignore numerical slivers where a zone only touches the surrounding area

CONDITION_OVERFLOW = "OVERFLOW"
CONDITION_SURCHARGE_ONLY = "SURCHARGE_ONLY"
CONDITION_NO_REPORTED_STRESS = "NO_REPORTED_STRESS"
CONDITION_OUTFALL = "OUTFALL"

RESPONSE_DESCRIPTIONS = {
    "OVERFLOW_AT_NEAREST_NODE": "The modelled drainage node nearest to the selected location overflowed (SWMM node flooding) during this simulation.",
    "OVERFLOW_IN_SURROUNDING_AREA": "The nearest modelled drainage node did not overflow, but at least one node associated with the surrounding area did.",
    "SURCHARGE_ONLY": "No modelled node overflow in the surrounding area; at least one associated node was surcharged (water above the pipe crown, without overflow).",
    "NO_REPORTED_STRESS": (
        "No modelled overflow or surcharge at the drainage nodes associated with the surrounding area in this simulation. "
        "This does not show that the location cannot flood: the model has no surface flow or ponding and represents an incomplete drainage network."
    ),
}

CONDITION_DESCRIPTIONS = {
    CONDITION_OVERFLOW: "Overflow (SWMM node flooding) at one or more reporting timestamps.",
    CONDITION_SURCHARGE_ONLY: "Surcharged (water above the pipe crown) without overflow.",
    CONDITION_NO_REPORTED_STRESS: "No overflow or surcharge at any reporting timestamp.",
    CONDITION_OUTFALL: "Model outfall (system exit); outfalls cannot overflow in this model.",
}


class LocationOutsideStudyAreaError(ValueError):
    pass


def _r(value: float, digits: int) -> float:
    return round(float(value), digits)


def _node_response(j: int | None, states: NodeStates, step_hours: float) -> dict[str, Any]:
    if j is None:
        return {"condition": CONDITION_OUTFALL, "description": CONDITION_DESCRIPTIONS[CONDITION_OUTFALL]}
    flooding = states.flooding[:, j]
    overflow_periods = int(states.is_flooding[:, j].sum())
    surcharge_periods = int(states.is_surcharged[:, j].sum())
    condition = CONDITION_OVERFLOW if overflow_periods else CONDITION_SURCHARGE_ONLY if surcharge_periods else CONDITION_NO_REPORTED_STRESS
    max_depth = float(states.depth[:, j].max())
    full = float(states.effective_full[j])
    response: dict[str, Any] = {
        "condition": condition,
        "description": CONDITION_DESCRIPTIONS[condition],
        "overflowPeriods": overflow_periods,
        "overflowHours": _r(overflow_periods * step_hours, 2),
        "surchargePeriods": surcharge_periods,
        "surchargeHours": _r(surcharge_periods * step_hours, 2),
        "peakOverflowRateCms": None,
        "peakOverflowTime": None,
        "firstOverflowTime": None,
        "lastOverflowTime": None,
        "highestOverflowClass": None,
        "approxCumulativeOverflowM3": None,
        "maxNodeWaterDepthM": _r(max_depth, 3),
        "maxFillRatio": _r(max_depth / full, 3) if full > 0 else None,
    }
    if overflow_periods:
        periods = np.where(states.is_flooding[:, j])[0]
        peak = int(np.argmax(flooding))
        response.update(
            peakOverflowRateCms=_r(flooding[peak], 6),
            peakOverflowTime=to_iso_z(states.times[peak]),
            firstOverflowTime=to_iso_z(states.times[int(periods[0])]),
            lastOverflowTime=to_iso_z(states.times[int(periods[-1])]),
            highestOverflowClass=states.overflow_class(float(flooding[peak])),
            approxCumulativeOverflowM3=_r(states.cumulative[-1, j], 1),
        )
    return response


def analyse_location(
    *,
    latitude: float,
    longitude: float,
    point_utm: tuple[float, float],
    radius_m: float,
    ward_utm: BaseGeometry,
    zones_utm: dict[str, BaseGeometry],
    node_xy: dict[str, tuple[float, float]],
    node_lonlat: dict[str, tuple[float, float]],
    states: NodeStates,
    interval_minutes: int,
    bottlenecks: list[dict[str, Any]] | None,
    processing_crs: str,
) -> dict[str, Any]:
    point = Point(point_utm)
    if not ward_utm.covers(point):
        raise LocationOutsideStudyAreaError("The selected location is outside the study area.")

    step_hours = interval_minutes / 60.0
    junction_index = {n: j for j, n in enumerate(states.junction_ids)}
    distance = {n: math.dist(point_utm, xy) for n, xy in node_xy.items()}

    # Nearest node (ties broken by node order, deterministic).
    nearest_id = min(node_xy, key=lambda n: distance[n])

    circle = point.buffer(radius_m, quad_segs=64)
    surrounding = circle.intersection(ward_utm)
    surrounding_area = surrounding.area

    associated: list[dict[str, Any]] = []
    responses: dict[str, dict[str, Any]] = {}
    for node_id, zone in zones_utm.items():
        if zone.is_empty:
            continue
        overlap = zone.intersection(surrounding).area
        if overlap < MIN_ASSOCIATION_AREA_M2 and node_id != nearest_id:
            continue
        responses[node_id] = _node_response(junction_index.get(node_id), states, step_hours)
        lon, lat = node_lonlat[node_id]
        associated.append(
            {
                "nodeId": node_id,
                "nodeType": "JUNCTION" if node_id in junction_index else "OUTFALL",
                "location": [_r(lon, 7), _r(lat, 7)],
                "distanceM": _r(distance[node_id], 1),
                "withinRadius": distance[node_id] <= radius_m,
                "zoneOverlapM2": _r(overlap, 1),
                "zoneOverlapShare": _r(overlap / surrounding_area, 4) if surrounding_area else 0.0,
                "isNearest": node_id == nearest_id,
                "response": responses[node_id],
            }
        )
    associated.sort(key=lambda a: (a["distanceM"], a["nodeId"]))

    overflowing = [a for a in associated if a["response"]["condition"] == CONDITION_OVERFLOW]
    surcharge_only = [a for a in associated if a["response"]["condition"] == CONDITION_SURCHARGE_ONLY]
    quiet = [a for a in associated if a["response"]["condition"] == CONDITION_NO_REPORTED_STRESS]
    overlap_of = {a["nodeId"]: a["zoneOverlapM2"] for a in associated}

    # Time-resolved response of the associated junctions at the SWMM reporting timestamps.
    j_rel = [junction_index[a["nodeId"]] for a in associated if a["nodeId"] in junction_index]
    peak: dict[str, Any] | None = None
    first_time = last_time = None
    overflow_duration = 0.0
    if j_rel and overflowing:
        rate_t = states.flooding[:, j_rel].sum(axis=1)
        count_t = states.is_flooding[:, j_rel].sum(axis=1)
        active = np.where(count_t > 0)[0]
        p = int(np.argmax(rate_t))
        at_peak = [states.junction_ids[j] for j in j_rel if states.is_flooding[p, j]]
        peak_area = sum(overlap_of[n] for n in at_peak)
        peak = {
            "time": to_iso_z(states.times[p]),
            "index": p,
            "combinedOverflowRateCms": _r(rate_t[p], 6),
            "overflowingNodeCount": len(at_peak),
            "overflowingNodeIds": at_peak,
            "areaAssociatedWithOverflowM2": _r(peak_area, 1),
            "shareAssociatedWithOverflow": _r(peak_area / surrounding_area, 4) if surrounding_area else 0.0,
        }
        first_time = to_iso_z(states.times[int(active[0])])
        last_time = to_iso_z(states.times[int(active[-1])])
        overflow_duration = _r(active.size * step_hours, 2)

    event_area = sum(a["zoneOverlapM2"] for a in overflowing)
    nearest_condition = responses[nearest_id]["condition"]
    if nearest_condition == CONDITION_OVERFLOW:
        code = "OVERFLOW_AT_NEAREST_NODE"
    elif overflowing:
        code = "OVERFLOW_IN_SURROUNDING_AREA"
    elif surcharge_only:
        code = "SURCHARGE_ONLY"
    else:
        code = "NO_REPORTED_STRESS"

    nearest = next(a for a in associated if a["nodeId"] == nearest_id)
    nearby_bottlenecks = None
    if bottlenecks is not None:
        nearby_bottlenecks = []
        for b in bottlenecks:
            ends = [distance[n] for n in (b.get("fromNodeId"), b.get("toNodeId")) if n in distance]
            if ends and min(ends) <= radius_m:
                nearby_bottlenecks.append(
                    {
                        "linkId": b["linkId"],
                        "sourceObjectId": b.get("sourceObjectId"),
                        "severity": b.get("severity"),
                        "confidence": b.get("confidence"),
                        "fromNodeId": b.get("fromNodeId"),
                        "toNodeId": b.get("toNodeId"),
                        "nearestEndNodeDistanceM": _r(min(ends), 1),
                    }
                )
        nearby_bottlenecks.sort(key=lambda b: (b["nearestEndNodeDistanceM"], b["linkId"]))

    return {
        "location": {
            "latitude": _r(latitude, 7),
            "longitude": _r(longitude, 7),
            "withinStudyArea": True,
            "crs": "EPSG:4326",
            "processingCrs": processing_crs,
            "eastingM": _r(point_utm[0], 2),
            "northingM": _r(point_utm[1], 2),
        },
        "radiusMeters": _r(radius_m, 1),
        "response": {"code": code, "description": RESPONSE_DESCRIPTIONS[code]},
        "nearestNode": {**nearest, "zoneContainsLocation": bool(zones_utm[nearest_id].covers(point))},
        "surroundingArea": {
            "circleAreaM2": _r(circle.area, 1),
            "areaWithinStudyAreaM2": _r(surrounding_area, 1),
            "shareWithinStudyArea": _r(surrounding_area / circle.area, 4),
            "associatedNodeCount": len(associated),
            "overflowingNodeCount": len(overflowing),
            "surchargeOnlyNodeCount": len(surcharge_only),
            "noReportedStressNodeCount": len(quiet),
            "outfallNodeCount": sum(1 for a in associated if a["nodeType"] == "OUTFALL"),
            "areaAssociatedWithOverflowM2": _r(event_area, 1),
            "shareAssociatedWithOverflow": _r(event_area / surrounding_area, 4) if surrounding_area else 0.0,
            "firstOverflowTime": first_time,
            "lastOverflowTime": last_time,
            "overflowDurationHours": overflow_duration,
            "peak": peak,
        },
        "nodes": associated,
        "potentialBottlenecks": nearby_bottlenecks,
        "intervalMinutes": interval_minutes,
    }


__all__ = ["analyse_location", "LocationOutsideStudyAreaError", "RESPONSE_DESCRIPTIONS", "CONDITION_DESCRIPTIONS"]
