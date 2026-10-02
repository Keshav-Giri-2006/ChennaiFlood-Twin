"""location-check-v1 on a small synthetic network (geometry and states are test inputs, not project data)."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from shapely.geometry import Point, box

from app.analysis.flood_processing import NodeStates, influence_zones
from app.analysis.location_check import LocationOutsideStudyAreaError, analyse_location
from app.gis.network_mapping import NetworkMapping, NodeLocation

WARD = box(0, 0, 1000, 1000)
NODES = {"A": (200.0, 200.0), "B": (800.0, 200.0), "C": (500.0, 800.0), "O": (990.0, 990.0)}
T0 = datetime(2023, 12, 3, 20, 0, tzinfo=UTC)
TIMES = [T0 + timedelta(minutes=30 * i) for i in range(4)]


def _states() -> NodeStates:
    # Junctions A, B, C (outfall O is not a junction). A overflows at periods 1-2, B is surcharged at 2, C is quiet.
    flooding = np.array([[0.0, 0.0, 0.0], [0.2, 0.0, 0.0], [0.5, 0.0, 0.0], [0.0, 0.0, 0.0]])
    depth = np.array([[0.1, 0.1, 0.1], [1.5, 0.3, 0.1], [1.5, 0.9, 0.2], [0.4, 0.2, 0.1]])
    is_flooding = flooding > 0
    is_surcharged = np.array([[False] * 3, [False] * 3, [False, True, False], [False] * 3])
    cumulative = np.cumsum(flooding * 1800.0, axis=0)
    return NodeStates(
        times=TIMES, junction_ids=["A", "B", "C"], depth=depth, head=depth + 3.0, flooding=flooding,
        is_flooding=is_flooding, is_surcharged=is_surcharged, cumulative=cumulative,
        effective_full=np.array([1.5, 1.2, 1.0]), p50=0.2, p90=0.4, event_max_rate=0.5,
    )


def _zones():
    mapping = NetworkMapping({}, {}, {}, {n: NodeLocation(i, x, y, 1) for i, (n, (x, y)) in enumerate(NODES.items())})
    return influence_zones(list(NODES), mapping, WARD)


ZONES = _zones()


def run(x: float, y: float, radius: float = 250.0, bottlenecks=None) -> dict:
    return analyse_location(
        latitude=13.0, longitude=80.2, point_utm=(x, y), radius_m=radius, ward_utm=WARD, zones_utm=ZONES,
        node_xy=NODES, node_lonlat={n: (80.2 + x / 1e5, 12.9 + y / 1e5) for n, (x, y) in NODES.items()},
        states=_states(), interval_minutes=30, bottlenecks=bottlenecks, processing_crs="EPSG:32644",
    )


def test_nearest_node_is_the_zone_owner_and_distance_is_planar():
    r = run(250, 260, radius=60)
    assert r["nearestNode"]["nodeId"] == "A"
    assert r["nearestNode"]["zoneContainsLocation"] is True
    assert r["nearestNode"]["distanceM"] == round(math.dist((250, 260), NODES["A"]), 1)


def test_node_response_is_taken_from_states_without_invented_values():
    a = run(210, 210, radius=60)["nearestNode"]["response"]
    assert a["condition"] == "OVERFLOW"
    assert a["overflowPeriods"] == 2 and a["overflowHours"] == 1.0
    assert a["peakOverflowRateCms"] == 0.5 and a["peakOverflowTime"] == "2023-12-03T21:00:00Z"
    assert a["firstOverflowTime"] == "2023-12-03T20:30:00Z" and a["lastOverflowTime"] == "2023-12-03T21:00:00Z"
    assert a["highestOverflowClass"] == "HIGH"
    assert a["approxCumulativeOverflowM3"] == round((0.2 + 0.5) * 1800.0, 1)
    assert a["maxNodeWaterDepthM"] == 1.5 and a["maxFillRatio"] == 1.0


@pytest.mark.parametrize(
    ("x", "y", "radius", "code"),
    [
        (210, 210, 60, "OVERFLOW_AT_NEAREST_NODE"),
        (700, 200, 450, "OVERFLOW_IN_SURROUNDING_AREA"),  # nearest is B (surcharged); A's zone reaches the area
        (790, 210, 60, "SURCHARGE_ONLY"),
        (500, 790, 60, "NO_REPORTED_STRESS"),
    ],
)
def test_headline_response(x, y, radius, code):
    assert run(x, y, radius)["response"]["code"] == code


def test_quiet_result_does_not_claim_the_location_cannot_flood():
    description = run(500, 790, 60)["response"]["description"]
    assert "does not show that the location cannot flood" in description


def test_surrounding_area_is_clipped_to_the_study_area():
    r = run(50, 50, radius=250)["surroundingArea"]
    expected = Point(50, 50).buffer(250, quad_segs=64).intersection(WARD).area
    assert r["areaWithinStudyAreaM2"] == round(expected, 1)
    assert r["areaWithinStudyAreaM2"] < r["circleAreaM2"]
    assert r["shareWithinStudyArea"] == round(expected / r["circleAreaM2"], 4)


def test_peak_of_surrounding_area_uses_associated_nodes_only():
    r = run(700, 200, 450)
    peak = r["surroundingArea"]["peak"]
    assert peak["time"] == "2023-12-03T21:00:00Z" and peak["combinedOverflowRateCms"] == 0.5
    assert peak["overflowingNodeIds"] == ["A"]
    assert r["surroundingArea"]["overflowDurationHours"] == 1.0
    # Area shares refer to influence-zone overlap, never exceeding the analysed area.
    assert 0 < peak["shareAssociatedWithOverflow"] <= 1


def test_no_overflow_means_no_peak():
    r = run(500, 790, 60)["surroundingArea"]
    assert r["peak"] is None and r["firstOverflowTime"] is None and r["overflowingNodeCount"] == 0


def test_outfall_has_no_derived_values():
    r = run(985, 985, 30)
    assert r["nearestNode"]["nodeId"] == "O" and r["nearestNode"]["nodeType"] == "OUTFALL"
    assert r["nearestNode"]["response"] == {"condition": "OUTFALL", "description": r["nearestNode"]["response"]["description"]}


def test_outside_study_area_is_rejected():
    with pytest.raises(LocationOutsideStudyAreaError):
        run(1500, 500)


def test_bottlenecks_are_filtered_by_end_node_distance():
    bottlenecks = [
        {"linkId": "CX", "fromNodeId": "A", "toNodeId": "B", "severity": "HIGH"},
        {"linkId": "CY", "fromNodeId": "C", "toNodeId": "O", "severity": "LOW"},
    ]
    r = run(210, 210, 100, bottlenecks)
    assert [b["linkId"] for b in r["potentialBottlenecks"]] == ["CX"]
    assert run(210, 210, 100, None)["potentialBottlenecks"] is None
