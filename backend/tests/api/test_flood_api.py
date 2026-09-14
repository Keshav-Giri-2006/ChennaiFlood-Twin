import pytest
from shapely.geometry import shape

API = "/api/v1"


@pytest.fixture
def completed(build_client):
    client, container, executor = build_client()
    sid = client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023"}).json()["simulationId"]
    executor.run_all()
    assert client.get(f"{API}/simulations/{sid}").json()["status"] == "COMPLETED"
    return client, container, sid


def test_flood_products_are_created_during_processing(completed):
    _client, container, sid = completed
    directory = container.settings.results_root / sid / "flood"
    assert (directory / "manifest.json").is_file() and (directory / "timeline.json").is_file()
    assert (directory / "zones.geojson").is_file() and (directory / "diagnostics.json").is_file()
    assert len(list((directory / "timeslices").glob("*.geojson"))) == 190
    record = container.simulations.get(sid)
    assert record.artifacts["floodProcessingVersion"] == "flood-processing-v1"


def test_flood_summary(completed):
    client, _container, sid = completed
    body = client.get(f"{API}/simulations/{sid}/flood").json()
    assert body["available"] is True
    assert body["extentAvailable"] is False and body["depthAvailable"] is False and body["maximumDepthM"] is None
    assert body["influenceZonesAvailable"] is True
    assert body["peakTime"] == "2023-12-03T22:00:00Z"
    m = body["metrics"]
    assert m["peakConcurrentFloodingNodes"]["value"] == 19
    assert m["floodedNodesEvent"]["value"] == 22
    assert m["simulatedFloodingVolume"] == {**m["simulatedFloodingVolume"], "value": 197_876_000.0, "unit": "L", "source": "model-derived"}
    assert "Not a ground flood depth" in m["maximumNodeWaterDepth"]["description"]
    assert body["metadata"]["floodProcessingVersion"] == "flood-processing-v1"
    kpis = client.get(f"{API}/simulations/{sid}/kpis").json()
    assert kpis["flood"]["maximumDepth"]["value"] is None
    assert kpis["flood"]["peakConcurrentFloodingNodes"]["methodVersion"] == "flood-processing-v1"


def test_timeline_and_timeslice(completed):
    client, _container, sid = completed
    timeline = client.get(f"{API}/simulations/{sid}/flood/timeline").json()
    assert timeline["intervalMinutes"] == 30
    assert len(timeline["timestamps"]) == 190
    peak = timeline["entries"][timeline["peakIndex"]]
    assert peak["time"] == "2023-12-03T22:00:00Z" and peak["floodingNodeCount"] == 19

    ts = client.get(f"{API}/simulations/{sid}/flood/timeslice", params={"time": peak["time"]}).json()
    assert ts["time"] == peak["time"] and ts["index"] == timeline["peakIndex"]
    assert ts["flood"]["floodingNodeCount"] == 19
    assert ts["metadata"]["dataType"] == "model-derived"
    features = ts["influence"]["features"]
    assert sum(1 for f in features if f["properties"]["featureType"] == "influenceZone") == 19
    assert all(shape(f["geometry"]).is_valid for f in features)

    # Same instant expressed with an offset resolves to the same slice.
    same = client.get(f"{API}/simulations/{sid}/flood/timeslice", params={"time": "2023-12-04T03:30:00+05:30"}).json()
    assert same["index"] == ts["index"]

    asset = client.get(ts["asset"]["url"])
    assert asset.status_code == 200 and asset.headers["content-type"].startswith("application/geo+json")
    assert asset.json()["features"] == features
    assert client.get(ts["asset"]["url"], headers={"If-None-Match": asset.headers["ETag"]}).status_code == 304


@pytest.mark.parametrize(
    "time,status,code",
    [
        ("not-a-time", 422, "INVALID_TIMESTAMP"),
        ("2023-12-03T22:00:00", 422, "INVALID_TIMESTAMP"),
        ("2023-12-03T22:15:00Z", 404, "TIMESTAMP_NOT_FOUND"),
        ("2023-12-02T00:00:00Z", 404, "TIMESTAMP_NOT_FOUND"),
        ("2024-01-01T00:00:00Z", 404, "TIMESTAMP_NOT_FOUND"),
    ],
)
def test_invalid_timestamps(completed, time, status, code):
    client, _container, sid = completed
    r = client.get(f"{API}/simulations/{sid}/flood/timeslice", params={"time": time})
    assert r.status_code == status
    assert r.json()["error"]["code"] == code


def test_invalid_timeslice_key_and_unavailable_products(completed):
    client, _container, sid = completed
    assert client.get(f"{API}/simulations/{sid}/flood/timeslices/20231203T221500Z").json()["error"]["code"] == "TIMESTAMP_NOT_FOUND"
    assert client.get(f"{API}/simulations/{sid}/flood/timeslices/..%2Fmanifest").status_code == 404
    for product in ("extent", "depth"):
        r = client.get(f"{API}/simulations/{sid}/flood/{product}")
        assert r.status_code == 404 and r.json()["error"]["code"] == "FLOOD_PRODUCT_NOT_AVAILABLE"


def test_flood_endpoints_require_completed_simulation(build_client):
    client, _container, _executor = build_client()
    sid = client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023"}).json()["simulationId"]
    for path in ("/flood", "/flood/timeline", "/flood/zones", "/timeseries/system"):
        r = client.get(f"{API}/simulations/{sid}{path}")
        assert r.status_code == 409 and r.json()["error"]["code"] == "SIMULATION_NOT_COMPLETED"


def test_flood_products_are_cached_and_versioned(completed):
    client, container, sid = completed
    manifest = container.settings.results_root / sid / "flood" / "manifest.json"
    first_mtime = manifest.stat().st_mtime_ns
    store = container.flood.store
    store._verified.clear()
    store.ensure(sid, "michaung-2023", "ward176-hydraulic-reconstructed-v1")
    assert manifest.stat().st_mtime_ns == first_mtime  # reused, not regenerated

    store._verified.clear()
    container.settings.flood_processing_version = "flood-processing-test"
    try:
        regenerated = store.ensure(sid, "michaung-2023", "ward176-hydraulic-reconstructed-v1")
        assert regenerated["floodProcessingVersion"] == "flood-processing-test"
    finally:
        container.settings.flood_processing_version = "flood-processing-v1"
        store._verified.clear()


def test_zones_endpoint(completed):
    client, _container, sid = completed
    zones = client.get(f"{API}/simulations/{sid}/flood/zones").json()
    assert len(zones["features"]) == 227
    assert "spatial association only" in zones["metadata"]["description"]


def test_timeseries_endpoints(completed):
    client, _container, sid = completed
    node = client.get(f"{API}/simulations/{sid}/timeseries/nodes/J161").json()
    assert len(node["timestamps"]) == 190 and set(node["series"]) == {"depthM", "headM", "lateralInflowCms", "totalInflowCms", "floodingCms"}
    assert max(node["series"]["floodingCms"]) > 0
    link = client.get(f"{API}/simulations/{sid}/timeseries/links/C162").json()
    assert link["sourceObjectId"] == 5902 and link["modelLinkId"] == "C162"
    assert link["variables"]["velocityMps"]["unit"] == "m/s"
    system = client.get(f"{API}/simulations/{sid}/timeseries/system").json()
    assert max(system["series"]["rainfallMmHr"]) == pytest.approx(23.35, abs=1e-3)
    assert client.get(f"{API}/simulations/{sid}/timeseries/nodes/J999").status_code == 404


def test_terrain_grid(build_client):
    client, *_ = build_client()
    r = client.get(f"{API}/gis/terrain")
    assert r.status_code == 200
    grid = r.json()
    assert (grid["width"], grid["height"]) == (50, 69) and grid["crs"] == "EPSG:4326"
    heights = grid["heights"]
    assert len(heights) == 50 * 69
    valid = [h for h in heights if h is not None]
    assert len(valid) == 1924 and heights.count(None) == 1526
    assert min(valid) == pytest.approx(1.705, abs=0.001) and max(valid) == pytest.approx(14.416, abs=0.001)
    assert 80.20 < grid["bounds"]["west"] < grid["bounds"]["east"] < 80.23
    assert client.get(f"{API}/gis/terrain", headers={"If-None-Match": r.headers["ETag"]}).status_code == 304
