"""API tests for potential bottlenecks, model-derived exposure, recommendations and risk (real archived SWMM artifacts)."""

import json

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


def test_decision_products_created_during_processing(completed):
    _client, container, sid = completed
    directory = container.settings.results_root / sid / "decision"
    for name in ("manifest.json", "bottlenecks.json", "bottlenecks.geojson", "exposure.json", "exposure_assets.json", "recommendations.json"):
        assert (directory / name).is_file(), name
    record = container.simulations.get(sid)
    assert record.artifacts["bottleneckAnalysisVersion"] == "bottleneck-analysis-v1"
    assert record.artifacts["exposureAnalysisVersion"] == "exposure-analysis-v1"
    assert record.artifacts["decisionSupportVersion"] == "decision-support-v1"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["versions"]["floodProcessingVersion"] == "flood-processing-v1"


def test_bottleneck_list_detail_and_geojson(completed):
    client, _container, sid = completed
    body = client.get(f"{API}/simulations/{sid}/bottlenecks").json()
    assert body["bottleneckAnalysisVersion"] == "bottleneck-analysis-v1" and body["dataType"] == "model-derived"
    assert "not a confirmed" in body["terminology"].lower()
    assert body["summary"]["potentialBottlenecks"] == 12 and body["summary"]["modelComponentsWithOutfall"] == 4
    assert client.get(f"{API}/simulations/{sid}/bottlenecks", params={"severity": "HIGH"}).json()["bottlenecks"][0]["linkId"] == "C169"
    assert client.get(f"{API}/simulations/{sid}/bottlenecks", params={"severity": "EXTREME"}).status_code == 422

    detail = client.get(f"{API}/simulations/{sid}/bottlenecks/C169").json()
    assert detail["sourceObjectId"] == 5909 and detail["fromNodeId"] == "J161" and detail["toNodeId"] == "J177"
    assert detail["connectedNodes"][0]["flooding"]["hoursFlooded"] == 74.33
    assert "rec-r1-C169" in detail["relatedRecommendationIds"]
    assert detail["explanation"]["disclaimer"].startswith("Model-derived diagnostic")

    missing = client.get(f"{API}/simulations/{sid}/bottlenecks/C162")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "BOTTLENECK_NOT_FOUND"
    assert missing.json()["error"]["details"]["numericalDiagnostic"]["timeStepCriticalPercent"] == 35.7
    assert client.get(f"{API}/simulations/{sid}/bottlenecks/C162;drop").status_code == 422

    geo = client.get(f"{API}/simulations/{sid}/bottlenecks/geojson")
    assert geo.status_code == 200 and geo.headers["content-type"].startswith("application/geo+json")
    features = geo.json()["features"]
    assert len(features) == 12
    for f in features:
        g = shape(f["geometry"])
        assert g.is_valid and 80.19 < g.bounds[0] < g.bounds[2] < 80.23 and 12.96 < g.bounds[1] < g.bounds[3] < 12.99
    assert client.get(f"{API}/simulations/{sid}/bottlenecks/geojson", headers={"If-None-Match": geo.headers["ETag"]}).status_code == 304


def test_exposure_summary_and_assets(completed):
    client, _container, sid = completed
    e = client.get(f"{API}/simulations/{sid}/exposure").json()
    assert e["totals"]["buildings"]["count"] == 6428 and e["totals"]["roads"]["count"] == 301
    assert e["event"]["buildings"]["intersectingCount"] == 948
    assert e["peak"]["time"] == "2023-12-03T22:00:00Z" and e["peak"]["buildings"]["intersectingCount"] == 783
    assert len(e["timeline"]) == 190 and e["timeline"][e["peak"]["index"]]["buildingsIntersecting"] == 783
    assert "not flooded" in e["terminology"].lower()

    peak = client.get(f"{API}/simulations/{sid}/exposure/buildings", params={"time": "2023-12-03T22:00:00Z"}).json()
    assert peak["scope"] == "timestamp" and peak["count"] == 783 and len(set(peak["objectIds"])) == 783
    event = client.get(f"{API}/simulations/{sid}/exposure/buildings").json()
    assert event["scope"] == "event" and event["count"] == 948 and set(peak["objectIds"]) <= set(event["objectIds"])
    roads = client.get(f"{API}/simulations/{sid}/exposure/roads", params={"time": "2023-12-04T03:30:00+05:30"}).json()
    assert roads["count"] == e["peak"]["roads"]["intersectingCount"]

    first = client.get(f"{API}/simulations/{sid}/exposure/buildings", params={"time": e["timeline"][0]["time"]}).json()
    assert first["count"] == e["timeline"][0]["buildingsIntersecting"] == 0 and first["objectIds"] == []

    assert client.get(f"{API}/simulations/{sid}/exposure/buildings", params={"time": "2023-12-03T22:00:00"}).json()["error"]["code"] == "INVALID_TIMESTAMP"
    assert client.get(f"{API}/simulations/{sid}/exposure/roads", params={"time": "2023-12-03T22:10:00Z"}).json()["error"]["code"] == "TIMESTAMP_NOT_FOUND"


def test_recommendations(completed):
    client, _container, sid = completed
    body = client.get(f"{API}/simulations/{sid}/recommendations").json()
    assert body["decisionSupportVersion"] == "decision-support-v1" and "not an engineering order" in body["disclaimer"]
    recs = body["recommendations"]
    assert recs[0]["id"] == "rec-r1-C169" and recs[0]["priority"] == "HIGH"
    assert body["summary"]["total"] == len(recs) == 32
    assert body["summary"]["byRule"] == {"R1": 1, "R2": 11, "R3": 3, "R4": 2, "R5": 11, "R6": 4}
    for r in recs:
        assert r["evidence"]["metrics"] and r["why"] and r["rule"] in body["rules"]
    high = client.get(f"{API}/simulations/{sid}/recommendations", params={"priority": "HIGH"}).json()["recommendations"]
    assert {r["priority"] for r in high} == {"HIGH"} and len(high) == body["summary"]["byPriority"]["HIGH"]


def test_risk_is_not_derived(completed):
    client, _container, sid = completed
    for path in ("/risk", "/risk/geojson"):
        r = client.get(f"{API}/simulations/{sid}{path}")
        assert r.status_code == 404 and r.json()["error"]["code"] == "RISK_PRODUCT_NOT_AVAILABLE"


def test_decision_endpoints_invalid_ids_and_state(build_client):
    client, _container, _executor = build_client()
    for path in ("/bottlenecks", "/exposure", "/recommendations", "/risk"):
        assert client.get(f"{API}/simulations/not-a-uuid{path}").json()["error"]["code"] == "SIMULATION_NOT_FOUND"
        assert client.get(f"{API}/simulations/00000000-0000-4000-8000-000000000000{path}").status_code == 404
    sid = client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023"}).json()["simulationId"]
    for path in ("/bottlenecks", "/bottlenecks/geojson", "/exposure", "/exposure/buildings", "/recommendations", "/risk"):
        r = client.get(f"{API}/simulations/{sid}{path}")
        assert r.status_code == 409 and r.json()["error"]["code"] == "SIMULATION_NOT_COMPLETED", path


def test_decision_products_cached_versioned_and_reproducible(completed):
    client, container, sid = completed
    directory = container.settings.results_root / sid / "decision"
    before = {name: json.loads((directory / name).read_text(encoding="utf-8")) for name in ("bottlenecks.json", "exposure.json", "recommendations.json")}
    mtime = (directory / "manifest.json").stat().st_mtime_ns
    store = container.decision.store
    store._verified.clear()
    store.ensure(sid, "michaung-2023", "ward176-hydraulic-reconstructed-v1")
    assert (directory / "manifest.json").stat().st_mtime_ns == mtime  # cache hit

    store._verified.clear()
    container.settings.bottleneck_analysis_version = "bottleneck-analysis-test"
    try:
        manifest = store.ensure(sid, "michaung-2023", "ward176-hydraulic-reconstructed-v1")
        assert manifest["versions"]["bottleneckAnalysisVersion"] == "bottleneck-analysis-test"
        after = {name: json.loads((directory / name).read_text(encoding="utf-8")) for name in before}
        strip = lambda d: json.dumps({k: v for k, v in d.items() if k not in ("generatedAt", "bottleneckAnalysisVersion")}, sort_keys=True)  # noqa: E731
        for name in ("exposure.json",):
            assert strip(after[name]) == strip(before[name])  # same inputs -> same content
        assert [b["linkId"] for b in after["bottlenecks.json"]["bottlenecks"]] == [b["linkId"] for b in before["bottlenecks.json"]["bottlenecks"]]
        assert [r["id"] for r in after["recommendations.json"]["recommendations"]] == [r["id"] for r in before["recommendations.json"]["recommendations"]]
    finally:
        container.settings.bottleneck_analysis_version = "bottleneck-analysis-v1"
        store._verified.clear()


def test_summary_and_kpis_reference_decision_products(completed):
    client, _container, sid = completed
    summary = client.get(f"{API}/simulations/{sid}/summary").json()
    assert summary["drainage"]["potentialBottlenecks"] == 12 and summary["drainage"]["potentialBottlenecksAvailable"] is True
    kpis = client.get(f"{API}/simulations/{sid}/kpis").json()
    assert kpis["exposure"]["buildingsInInfluenceZonesPeak"]["value"] == 783
    assert kpis["exposure"]["buildingsInInfluenceZonesEvent"]["methodVersion"] == "exposure-analysis-v1"
    assert kpis["flood"]["affectedBuildings"]["value"] is None  # still no flood extent -> no "affected" buildings
