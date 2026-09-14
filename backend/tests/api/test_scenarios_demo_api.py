"""Demo result, rainfall-multiplier safeguards, dynamic bottlenecks and scenario comparison (archived real SWMM artifacts)."""

import pytest

from app.simulation.runner import SwmmUnavailableError

API = "/api/v1"
DEMO = "michaung-2023-verified"


def _no_swmm(_settings):
    raise SwmmUnavailableError("SWMM must not be invoked for the precomputed demo result")


@pytest.fixture
def demo(build_client):
    client, container, executor = build_client(runner_factory=_no_swmm)
    body = client.post(f"{API}/demo/{DEMO}/load").json()
    executor.run_all()
    return client, container, executor, body["simulationId"]


def test_demo_result_loads_without_running_swmm_and_is_reused(demo):
    client, container, executor, sid = demo
    status = client.get(f"{API}/simulations/{sid}").json()
    assert status["status"] == "COMPLETED" and status["executionMode"] == "precomputed-demo" and status["demoId"] == DEMO
    assert (container.settings.workdir / sid / "stdout.log").read_text(encoding="utf-8").startswith("precomputed demonstration result")
    kpis = client.get(f"{API}/simulations/{sid}/kpis").json()
    assert kpis["hydraulics"]["simulatedFloodingVolume"]["value"] == 197_876_000.0
    assert kpis["metadata"]["executionMode"] == "precomputed-demo"
    assert client.get(f"{API}/simulations/{sid}/bottlenecks").json()["bottlenecks"][0]["linkId"] == "C169"

    again = client.post(f"{API}/demo/{DEMO}/load").json()
    assert again == {"demoId": DEMO, "simulationId": sid, "status": "COMPLETED", "reused": True}
    assert executor.jobs == []
    catalogue = client.get(f"{API}/demo").json()["demoResults"][0]
    assert catalogue["available"] is True and catalogue["loadedSimulationId"] == sid and catalogue["label"] == "Precomputed demonstration result"
    assert client.post(f"{API}/demo/unknown-demo/load").status_code == 404


def test_tampered_demo_file_is_never_presented(build_client, tmp_path):
    import shutil

    from tests.conftest import REPO_ROOT

    models = tmp_path / "models"
    shutil.copytree(REPO_ROOT / "simulation", models)
    (models / "ward176_hydraulic_reconstructed_candidate.out").write_bytes(b"not a swmm output")
    from app.core.config import Settings

    client, _container, executor = build_client(runner_factory=_no_swmm, settings=Settings(RUNTIME_DIR=tmp_path / "rt", WEB_ASSETS_DIR=tmp_path / "web", DATA_DIR=REPO_ROOT, MODEL_DIR=models))
    r = client.post(f"{API}/demo/{DEMO}/load")
    assert r.status_code == 503 and r.json()["error"]["code"] == "RESULT_NOT_FOUND"


def test_scenario_run_cannot_reuse_baseline_output(build_client):
    """The replay test double copies baseline outputs; a 1.25x run must detect that SWMM did not use its rainfall."""
    client, container, executor = build_client()
    sid = client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023", "parameters": {"rainfallMultiplier": 1.25}}).json()["simulationId"]
    executor.run_all()
    status = client.get(f"{API}/simulations/{sid}").json()
    assert status["status"] == "FAILED" and status["error"]["code"] == "PROCESSING_FAILED"
    run = status["scenarioRun"]
    assert run["rainfallMultiplier"] == 1.25 and run["transformedModelSha256"] != run["baselineModelSha256"]
    assert run["rainfall"]["scenarioTotalMm"] == pytest.approx(353.544, abs=1e-3)
    workspace_inp = (container.settings.workdir / sid / "input.inp").read_text(encoding="utf-8")
    assert "Michaung 12/3/2023 21:30 29.187500" in workspace_inp  # isolated copy transformed
    from tests.conftest import MODEL_INP

    assert "Michaung 12/3/2023 21:30 23.350000" in MODEL_INP.read_text(encoding="utf-8")  # master untouched


def test_baseline_multiplier_one_matches_unparameterised_run(build_client):
    client, _container, executor = build_client()
    a = client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023"}).json()["simulationId"]
    b = client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023", "parameters": {"rainfallMultiplier": 1.0}}).json()["simulationId"]
    executor.run_all()
    sb = client.get(f"{API}/simulations/{b}").json()
    assert sb["status"] == "COMPLETED" and sb["scenarioRun"]["transformedModelIdenticalToBaseline"] is True
    ka, kb = (client.get(f"{API}/simulations/{s}/kpis").json() for s in (a, b))
    for group in ("rainfall", "hydraulics", "drainage", "flood", "exposure"):
        for key, qa in ka[group].items():
            assert kb[group][key]["value"] == qa["value"], (group, key)
    listed = client.get(f"{API}/simulations", params={"rainfallMultiplier": 1.0, "status": "COMPLETED"}).json()["simulations"]
    assert {s["simulationId"] for s in listed} == {a, b}
    assert client.get(f"{API}/simulations", params={"rainfallMultiplier": 1.25}).json()["simulations"] == []

    comparison = client.get(f"{API}/comparisons", params={"baseline": a, "scenario": b}).json()
    assert comparison["scenarioAnalysisVersion"] == "scenario-analysis-v1"
    assert all(m["absoluteChange"] == 0 for m in comparison["metrics"])
    assert comparison["bottlenecks"]["new"] == [] and comparison["floodInfluence"]["event"]["scenarioOnly"] == []
    assert comparison["recommendations"]["new"] == [] and comparison["recommendations"]["notTriggeredInScenario"] == []
    assert "NOT a shared scale" in comparison["floodInfluence"]["sharedScale"]["note"]
    assert client.post(f"{API}/comparisons", json={"simulationIds": [a, a]}).json()["error"]["code"] == "COMPARISON_NOT_COMPATIBLE"


def test_bottleneck_timeline_is_evidence_backed(demo):
    client, _container, _executor, sid = demo
    doc = client.get(f"{API}/simulations/{sid}/bottlenecks/timeline").json()
    assert doc["bottleneckTimelineVersion"] == "bottleneck-timeline-v1" and len(doc["entries"]) == 190
    event = {b["linkId"]: b["severity"] for b in client.get(f"{API}/simulations/{sid}/bottlenecks").json()["bottlenecks"]}
    order = ["LOW", "MODERATE", "HIGH"]
    for entry in doc["entries"]:
        for a in entry["active"]:
            assert a["linkId"] in event  # only event-level potential bottlenecks
            assert order.index(a["severity"]) <= order.index(event[a["linkId"]])  # never above event severity
            assert a["criteria"]["full"] or a["criteria"]["aboveFullFlowCapacity"]
    c169 = doc["summary"]["perLink"]["C169"]
    assert c169["activeHours"] == 9.5 and c169["stepsBySeverity"]["HIGH"] == 19 and c169["peakUtilizationTime"] == "2023-12-03T22:00:00Z"
    one = client.get(f"{API}/simulations/{sid}/bottlenecks/timeline", params={"time": "2023-12-03T22:00:00Z"}).json()["entry"]
    assert one["highestSeverity"] == "HIGH" and one["active"][0]["linkId"] == "C169" and one["mostLoaded"]["linkId"] == "C169"
    assert client.get(f"{API}/simulations/{sid}/bottlenecks/timeline", params={"time": "2023-12-03T22:10:00Z"}).json()["error"]["code"] == "TIMESTAMP_NOT_FOUND"
