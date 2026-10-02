"""POST /simulations/{id}/location-check against a replayed run of the approved model (archived SWMM 5.2.4 outputs).

Expected values are not hard-coded: every node response is cross-checked against the
flood-processing-v1 product files written by the pipeline for the same simulation.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict

import pytest
from pyproj import Transformer
from shapely.geometry import Point, shape

from tests.conftest import REPO_ROOT, FailingRunner

API = "/api/v1"


@pytest.fixture
def completed(build_client):
    client, container, executor = build_client()
    sid = client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023"}).json()["simulationId"]
    executor.run_all()
    assert client.get(f"{API}/simulations/{sid}").json()["status"] == "COMPLETED"
    return client, container, sid


def _product_node_states(container, sid):
    """Per node, the (time, state, rate) samples in the flood time-slice product files."""
    directory = container.settings.results_root / sid / "flood"
    timeline = json.loads((directory / "timeline.json").read_text(encoding="utf-8"))
    samples: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    for entry in timeline["entries"]:
        fc = json.loads((directory / "timeslices" / f"{entry['key']}.geojson").read_text(encoding="utf-8"))
        for f in fc["features"]:
            p = f["properties"]
            if p["featureType"] == "node":
                samples[p["nodeId"]].append((entry["time"], p["state"], p["floodingRateCms"]))
    return timeline, samples


def _flooding_node_at_peak(client, sid):
    ts = client.get(f"{API}/simulations/{sid}/flood/timeslice", params={"time": "2023-12-03T22:00:00Z"}).json()
    node = next(f for f in ts["influence"]["features"] if f["properties"]["featureType"] == "node" and f["properties"]["state"] == "FLOODING")
    return node["properties"]["nodeId"], node["geometry"]["coordinates"]


def test_location_check_is_derived_from_the_flood_products(completed):
    client, container, sid = completed
    node_id, (lon, lat) = _flooding_node_at_peak(client, sid)
    lat, lon = lat + 0.0001, lon + 0.0001  # ~15 m from the node
    r = client.post(f"{API}/simulations/{sid}/location-check", json={"latitude": lat, "longitude": lon})
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["simulationId"] == sid and body["scenarioId"] == "michaung-2023" and body["rainfallMultiplier"] == 1.0
    assert body["dataType"] == "model-derived" and body["locationCheckVersion"] == "location-check-v1"
    assert body["location"] == {**body["location"], "latitude": round(lat, 7), "longitude": round(lon, 7), "withinStudyArea": True, "processingCrs": "EPSG:32644"}
    assert body["radiusMeters"] == 250.0

    # Nearest node: independent planar distance in EPSG:32644 from the published node locations.
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)
    px, py = to_utm.transform(lon, lat)
    nodes = client.get(f"{API}/gis/model/nodes").json()["features"]
    dist = {f["properties"]["modelNodeId"]: math.dist((px, py), to_utm.transform(*f["geometry"]["coordinates"][:2])) for f in nodes}
    nearest = min(dist, key=dist.get)
    assert body["nearestNode"]["nodeId"] == nearest == node_id
    assert body["nearestNode"]["distanceM"] == pytest.approx(dist[nearest], abs=0.2)
    # ...and it owns the influence zone (flood product) containing the location.
    zones = client.get(f"{API}/simulations/{sid}/flood/zones").json()["features"]
    owner = [z["properties"]["nodeId"] for z in zones if shape(z["geometry"]).covers(Point(lon, lat))]
    assert owner == [nearest] and body["nearestNode"]["zoneContainsLocation"] is True

    # Every associated node's response agrees with the time-slice product files.
    timeline, samples = _product_node_states(container, sid)
    step_h = timeline["intervalMinutes"] / 60
    for n in body["nodes"]:
        s = samples.get(n["nodeId"], [])
        flooding = [x for x in s if x[1] == "FLOODING"]
        surcharged = [x for x in s if x[1] == "SURCHARGED"]
        resp = n["response"]
        if n["nodeType"] == "OUTFALL":
            assert resp["condition"] == "OUTFALL" and not s
            continue
        expected = "OVERFLOW" if flooding else "SURCHARGE_ONLY" if surcharged else "NO_REPORTED_STRESS"
        assert resp["condition"] == expected, n["nodeId"]
        assert resp["overflowPeriods"] == len(flooding) and resp["surchargePeriods"] == len(surcharged)
        assert resp["overflowHours"] == pytest.approx(len(flooding) * step_h)
        if flooding:
            top = max(flooding, key=lambda x: x[2])
            assert resp["peakOverflowRateCms"] == pytest.approx(top[2], abs=1e-6)
            assert resp["peakOverflowTime"] == top[0]
            assert resp["firstOverflowTime"] == flooding[0][0] and resp["lastOverflowTime"] == flooding[-1][0]
        else:
            assert resp["peakOverflowRateCms"] is None and resp["approxCumulativeOverflowM3"] is None

    area = body["surroundingArea"]
    assert area["associatedNodeCount"] == len(body["nodes"])
    assert area["overflowingNodeCount"] + area["surchargeOnlyNodeCount"] + area["noReportedStressNodeCount"] + area["outfallNodeCount"] == len(body["nodes"])
    assert 0 < area["areaWithinStudyAreaM2"] <= area["circleAreaM2"]

    # Peak of the surrounding area = timestamp with the largest combined overflow of associated nodes.
    peak = area["peak"]
    associated = {n["nodeId"] for n in body["nodes"]}
    at_peak = {nid: x[2] for nid, s in samples.items() if nid in associated for x in s if x[0] == peak["time"] and x[1] == "FLOODING"}
    assert set(peak["overflowingNodeIds"]) == set(at_peak)
    assert peak["combinedOverflowRateCms"] == pytest.approx(sum(at_peak.values()), abs=1e-5)
    per_time = defaultdict(float)
    for nid, s in samples.items():
        if nid in associated:
            for t, state, rate in s:
                if state == "FLOODING":
                    per_time[t] += rate
    assert peak["combinedOverflowRateCms"] == pytest.approx(max(per_time.values()), abs=1e-5)

    # Nothing is invented: no ground depth, no extent; bottlenecks are real bottleneck-analysis records.
    assert body["groundFloodDepthM"] is None and body["floodExtentAvailable"] is False
    assert "groundFloodDepth" in body["notDerived"]
    listed = {b["linkId"]: b for b in client.get(f"{API}/simulations/{sid}/bottlenecks").json()["bottlenecks"]}
    for b in body["potentialBottlenecks"]:
        assert listed[b["linkId"]]["severity"] == b["severity"]
        assert b["nearestEndNodeDistanceM"] <= 250.0

    # No filesystem paths or internals in the response.
    text = r.text
    for secret in (str(container.settings.runtime_dir), str(REPO_ROOT), REPO_ROOT.as_posix(), "sqlite", "output.out", "report.rpt", "input.inp", "\\\\"):
        assert secret not in text


def test_moving_the_location_changes_the_result_without_re_running(completed):
    client, container, sid = completed
    _node, (lon, lat) = _flooding_node_at_peak(client, sid)
    runs_before = len(client.get(f"{API}/simulations").json()["simulations"])
    first = client.post(f"{API}/simulations/{sid}/location-check", json={"latitude": lat, "longitude": lon}).json()
    boundary = client.get(f"{API}/gis/ward").json()["features"][0]["geometry"]
    cx, cy = shape(boundary).representative_point().coords[0]
    second = client.post(f"{API}/simulations/{sid}/location-check", json={"latitude": cy, "longitude": cx, "radiusMeters": 400}).json()
    assert second["location"]["latitude"] == round(cy, 7) and second["radiusMeters"] == 400.0
    assert first["location"] != second["location"]
    assert len(client.get(f"{API}/simulations").json()["simulations"]) == runs_before  # no new simulation was created


def test_location_check_rejects_invalid_input(completed):
    client, _container, sid = completed
    url = f"{API}/simulations/{sid}/location-check"
    for body in (
        {"latitude": 95, "longitude": 80.22},
        {"latitude": 12.97, "longitude": -181},
        {"longitude": 80.22},
        {"latitude": "north", "longitude": 80.22},
        {"latitude": 12.97, "longitude": 80.22, "radiusMeters": 10},
        {"latitude": 12.97, "longitude": 80.22, "radiusMeters": 5000},
        {"latitude": 12.97, "longitude": 80.22, "path": "/etc/passwd"},
    ):
        r = client.post(url, json=body)
        assert r.status_code == 422, body
        assert r.json()["error"]["code"] == "INVALID_REQUEST"
    nan = client.post(url, content='{"latitude": NaN, "longitude": 80.22}', headers={"Content-Type": "application/json"})
    assert nan.status_code == 422

    for lat, lon in ((13.05, 80.25), (0.0, 0.0)):  # in Chennai but outside Ward 176; far away
        r = client.post(url, json={"latitude": lat, "longitude": lon})
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "LOCATION_OUTSIDE_STUDY_AREA"

    for bad in ("not-a-simulation", "00000000-0000-0000-0000-000000000000", "..%2F..%2Fetc"):
        r = client.post(f"{API}/simulations/{bad}/location-check", json={"latitude": 12.97, "longitude": 80.22})
        assert r.status_code == 404
        assert r.json()["error"]["code"] in ("SIMULATION_NOT_FOUND", "NOT_FOUND")


def test_location_check_requires_a_completed_simulation(build_client):
    client, _container, executor = build_client()
    sid = client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023"}).json()["simulationId"]
    r = client.post(f"{API}/simulations/{sid}/location-check", json={"latitude": 12.97, "longitude": 80.22})
    assert r.status_code == 409 and r.json()["error"]["code"] == "SIMULATION_NOT_COMPLETED"
    assert r.json()["error"]["details"] == {"status": "CREATED"}
    executor.jobs.clear()

    failing, _c, failing_executor = build_client(runner=FailingRunner())
    fid = failing.post(f"{API}/simulations", json={"scenarioId": "michaung-2023"}).json()["simulationId"]
    failing_executor.run_all()
    r = failing.post(f"{API}/simulations/{fid}/location-check", json={"latitude": 12.97, "longitude": 80.22})
    assert r.status_code == 409 and r.json()["error"]["details"] == {"status": "FAILED"}

    # Existing health endpoints are unaffected.
    assert failing.get(f"{API}/health").json()["status"] == "ok"
    assert failing.get(f"{API}/health/ready").status_code in (200, 503)
