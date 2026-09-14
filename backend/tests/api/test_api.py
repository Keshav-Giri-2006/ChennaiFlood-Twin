import json

import pytest

from app.core.container import Container
from tests.conftest import REPO_ROOT, FailingRunner

API = "/api/v1"


# --- health ------------------------------------------------------------------------------
def test_health(build_client):
    client, *_ = build_client()
    r = client.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "chennaiflood-twin-api", "version": "0.1.0"}
    assert r.headers["X-Request-ID"]


def test_readiness_reports_missing_swmm(build_client, make_settings, tmp_path):
    client, *_ = build_client(settings=make_settings(SWMM_EXECUTABLE=str(tmp_path / "missing-runswmm")))
    r = client.get(f"{API}/health/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["swmm"] == "error"
    assert body["checks"]["model"] == "ok" and body["checks"]["data"] == "ok"
    assert str(tmp_path) not in r.text  # no server paths leaked


# --- scenarios -------------------------------------------------------------------------------
def test_scenario_list_and_detail(build_client):
    client, *_ = build_client()
    listing = client.get(f"{API}/scenarios").json()["scenarios"]
    assert [s["scenarioId"] for s in listing] == ["michaung-2023"]
    item = listing[0]
    assert item["totalRainfallMm"] == 282.835 and item["peakIntensityMmHr"] == 23.35
    assert item["startTime"] == "2023-12-02T00:00:00Z" and item["endTime"] == "2023-12-05T23:30:00Z"

    detail = client.get(f"{API}/scenarios/michaung-2023").json()
    assert detail["source"]["variable"] == "GPM_3IMERGHH v07"
    assert detail["rainfall"]["records"] == 192
    assert detail["rainfall"]["dailyTotalsMm"]["2023-12-04"] == 152.36
    assert detail["limitations"]

    rain = client.get(f"{API}/scenarios/michaung-2023/rainfall").json()
    assert len(rain["records"]) == 192
    assert sum(r["depthMm"] for r in rain["records"]) == pytest.approx(282.835, abs=0.001)


def test_unknown_scenario(build_client):
    client, *_ = build_client()
    r = client.get(f"{API}/scenarios/unknown-2099")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "SCENARIO_NOT_FOUND"
    assert r.json()["error"]["requestId"]


# --- simulation creation & validation -------------------------------------------------------------
@pytest.mark.parametrize(
    "payload,status,code",
    [
        ({"scenarioId": "unknown-2099"}, 404, "SCENARIO_NOT_FOUND"),
        ({"scenarioId": "michaung-2023", "modelVersion": "not-a-model"}, 404, "MODEL_NOT_FOUND"),
        ({"scenarioId": "michaung-2023", "parameters": {"rainfallMultiplier": 1.2}}, 422, "UNSUPPORTED_PARAMETER"),
        ({"scenarioId": "michaung-2023", "swmmExecutable": "/bin/sh"}, 422, "INVALID_REQUEST"),
        ({"scenarioId": "../../etc/passwd"}, 422, "INVALID_REQUEST"),
        ({}, 422, "INVALID_REQUEST"),
    ],
)
def test_create_simulation_rejects_invalid_requests(build_client, payload, status, code):
    client, _container, executor = build_client()
    r = client.post(f"{API}/simulations", json=payload)
    assert r.status_code == status
    assert r.json()["error"]["code"] == code
    assert executor.jobs == []


def test_simulation_lifecycle_with_replayed_artifacts(build_client):
    client, container, executor = build_client()
    r = client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023", "modelVersion": "ward176-hydraulic-reconstructed-v1"})
    assert r.status_code == 202
    created = r.json()
    sid = created["simulationId"]
    assert created["status"] == "CREATED"
    assert r.headers["Location"] == f"{API}/simulations/{sid}"

    status = client.get(f"{API}/simulations/{sid}").json()
    assert status["status"] == "CREATED" and status["progress"] == 0 and status["stage"] == "QUEUED"
    assert client.get(f"{API}/simulations/{sid}/summary").status_code == 409

    executor.run_all()

    status = client.get(f"{API}/simulations/{sid}").json()
    assert status["status"] == "COMPLETED", status
    assert status["progress"] == 100 and status["error"] is None
    assert status["startedAt"] and status["completedAt"]

    summary = client.get(f"{API}/simulations/{sid}/summary").json()
    assert summary["rainfall"] == {"totalMm": 282.835, "peakMmHr": 23.35, "dataType": "source"}
    assert summary["flood"]["maximumDepthM"] is None and summary["flood"]["available"] is False
    assert summary["drainage"]["floodedNodes"] == 22
    assert summary["hydraulics"]["simulatedFloodingVolumeL"] == 197_876_000.0
    assert summary["modelDiagnostics"]["routingContinuityErrorPercent"] == 0.068
    assert summary["limitations"]

    kpis = client.get(f"{API}/simulations/{sid}/kpis").json()
    assert kpis["rainfall"]["total"] == {"value": 282.835, "unit": "mm", "source": "source", "description": kpis["rainfall"]["total"]["description"], "methodVersion": None}
    assert kpis["hydraulics"]["simulatedFloodingVolume"]["unit"] == "L"
    assert kpis["hydraulics"]["simulatedFloodingVolume"]["source"] == "model-derived"
    assert kpis["drainage"]["potentialBottlenecks"]["value"] is None

    diagnostics = client.get(f"{API}/simulations/{sid}/diagnostics").json()
    critical = {e["id"]: e["sourceObjectId"] for e in diagnostics["timeStepCriticalElements"]}
    assert critical["C162"] == 5902

    products = client.get(f"{API}/simulations/{sid}/results").json()["products"]
    assert products["summary"] and products["kpis"] and products["flood"] and products["timeline"] and not products["risk"]

    listing = client.get(f"{API}/simulations", params={"scenarioId": "michaung-2023", "status": "COMPLETED"}).json()
    assert [s["simulationId"] for s in listing["simulations"]] == [sid]

    workspace = container.settings.workdir / sid
    for name in ("input.inp", "report.rpt", "output.out", "stdout.log", "stderr.log", "metadata.json"):
        assert (workspace / name).is_file()
    metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "COMPLETED" and metadata["model"]["sha256"] == container.registry.models["ward176-hydraulic-reconstructed-v1"].sha256

    for text in (json.dumps(summary), json.dumps(kpis), json.dumps(diagnostics)):
        assert str(REPO_ROOT) not in text and "observedFlood" not in text


def test_swmm_failure_marks_simulation_failed(build_client):
    client, container, executor = build_client(runner=FailingRunner())
    sid = client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023"}).json()["simulationId"]
    executor.run_all()
    status = client.get(f"{API}/simulations/{sid}").json()
    assert status["status"] == "FAILED"
    assert status["stage"] == "SWMM_EXECUTION"
    assert status["error"]["code"] == "SIMULATION_FAILED"
    assert status["error"]["message"] == "Simulation failed during SWMM execution."
    assert status["completedAt"] is not None
    r = client.get(f"{API}/simulations/{sid}/kpis")
    assert r.status_code == 409 and r.json()["error"]["code"] == "SIMULATION_NOT_COMPLETED"
    assert (container.settings.workdir / sid / "metadata.json").is_file()


def test_missing_swmm_fails_during_validation(build_client, make_settings, tmp_path):
    from app.services.simulation_service import default_runner_factory

    settings = make_settings(SWMM_EXECUTABLE=str(tmp_path / "missing-runswmm"))
    client, _container, executor = build_client(settings=settings, runner_factory=default_runner_factory)
    sid = client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023"}).json()["simulationId"]
    executor.run_all()
    status = client.get(f"{API}/simulations/{sid}").json()
    assert status["status"] == "FAILED" and status["stage"] == "VALIDATION"
    assert status["error"]["code"] == "SWMM_UNAVAILABLE"


def test_interrupted_runs_are_failed_on_restart(build_client, make_settings):
    settings = make_settings()
    client, _container, _executor = build_client(settings=settings)
    sid = client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023"}).json()["simulationId"]
    client.__exit__(None, None, None)  # "crash" before the queued job runs

    client2, *_ = build_client(settings=settings)
    status = client2.get(f"{API}/simulations/{sid}").json()
    assert status["status"] == "FAILED"
    assert status["error"]["code"] == "SIMULATION_INTERRUPTED"


@pytest.mark.parametrize("sid", ["not-a-uuid", "00000000-0000-0000-0000-000000000000"])
def test_unknown_simulation(build_client, sid):
    client, *_ = build_client()
    for suffix in ("", "/summary", "/kpis", "/diagnostics", "/results"):
        r = client.get(f"{API}/simulations/{sid}{suffix}")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "SIMULATION_NOT_FOUND"


# --- GIS ------------------------------------------------------------------------------------------
EXPECTED_COUNTS = {"ward": 1, "buildings": 6428, "roads": 301, "drains": 135, "subcatchments": 35, "model/conduits": 182, "model/nodes": 228}


@pytest.mark.parametrize("layer,count", EXPECTED_COUNTS.items())
def test_gis_layers(build_client, layer, count):
    client, *_ = build_client()
    r = client.get(f"{API}/gis/{layer}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/geo+json")
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == count
    meta = body["metadata"]
    assert meta["crs"].startswith("OGC:CRS84") and meta["invalidSourceGeometryCount"] == 0
    minx, miny, maxx, maxy = meta["bbox"]
    assert 80.20 < minx < maxx < 80.23 and 12.96 < miny < maxy < 12.99  # Ward 176, lon/lat order
    assert "crs" not in body  # RFC 7946
    etag = r.headers["ETag"]
    assert client.get(f"{API}/gis/{layer}", headers={"If-None-Match": etag}).status_code == 304


def test_drain_detail_keeps_source_and_model_ids_separate(build_client):
    client, *_ = build_client()
    drain = client.get(f"{API}/gis/drains/5902").json()
    assert drain["objectId"] == 5902 and drain["modelLinkIds"] == ["C162"]
    anomalous = client.get(f"{API}/gis/drains/5793").json()
    assert anomalous["inHydraulicModel"] is False
    assert anomalous["dataQuality"][0]["flag"] == "SUSPICIOUS_INVERT"
    assert client.get(f"{API}/gis/drains/1").status_code == 404


def test_unknown_route_uses_error_format(build_client):
    client, *_ = build_client()
    r = client.get(f"{API}/does-not-exist")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"


def test_cors_allows_only_configured_origins(build_client):
    client, *_ = build_client()
    ok = client.get(f"{API}/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.get(f"{API}/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in bad.headers
