"""End-to-end test with the real EPA SWMM 5.2.4 executable and the approved model.

API -> scenario validation -> isolated workspace -> SWMM subprocess -> parsing -> API results.
The expected values are the documented outputs of the reconstructed candidate
model (docs/04_SWMM_MODEL.md §35/§40) and act as a hydraulic regression check.
"""

import time

import pytest
from fastapi.testclient import TestClient

from app.core.container import Container
from app.main import create_app
from app.simulation.report_parser import parse_report
from app.utils.files import sha256_file
from tests.conftest import MODEL_INP, swmm_available

pytestmark = [pytest.mark.integration, pytest.mark.skipif(not swmm_available(), reason="SWMM executable not configured")]

API = "/api/v1"


def _wait(client: TestClient, sid: str, timeout: float = 600) -> dict:
    seen = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"{API}/simulations/{sid}").json()
        if not seen or seen[-1] != body["status"]:
            seen.append(body["status"])
        if body["status"] in ("COMPLETED", "FAILED"):
            body["_seen"] = seen
            return body
        time.sleep(0.25)
    raise AssertionError(f"simulation {sid} did not finish; states seen {seen}")


def test_real_swmm_simulations_run_isolated_and_reproduce_candidate_results(make_settings):
    master_sha = sha256_file(MODEL_INP)
    settings = make_settings(SIMULATION_MAX_CONCURRENT=2)
    container = Container.build(settings)
    with TestClient(create_app(settings, container)) as client:
        assert client.get(f"{API}/health/ready").json()["status"] == "ready"

        ids = [client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023", "modelVersion": "ward176-hydraulic-reconstructed-v1"}).json()["simulationId"] for _ in range(2)]
        assert len(set(ids)) == 2
        finals = [_wait(client, sid) for sid in ids]

        for sid, final in zip(ids, finals):
            assert final["status"] == "COMPLETED", final
            assert final["_seen"][-1] == "COMPLETED"
            workspace = settings.workdir / sid
            report = parse_report(workspace / "report.rpt")
            assert report.errors == [] and report.engine_version == "5.2.4"
            assert (workspace / "output.out").stat().st_size > 0

            kpis = client.get(f"{API}/simulations/{sid}/kpis").json()
            assert kpis["rainfall"]["total"]["value"] == 282.835
            assert kpis["rainfall"]["peakIntensity"]["value"] == 23.35
            assert kpis["hydraulics"]["wetWeatherInflow"]["value"] == 271_424_000.0
            assert kpis["hydraulics"]["externalOutflow"]["value"] == 67_405_000.0
            assert kpis["hydraulics"]["simulatedFloodingVolume"]["value"] == 197_876_000.0
            assert kpis["hydraulics"]["finalStoredVolume"]["value"] == 5_958_000.0
            assert kpis["modelDiagnostics"]["runoffContinuityError"]["value"] == -0.018
            assert kpis["modelDiagnostics"]["routingContinuityError"]["value"] == 0.068
            assert kpis["flood"]["maximumDepth"]["value"] is None

            summary = client.get(f"{API}/simulations/{sid}/summary").json()
            assert summary["status"] == "COMPLETED"
            assert summary["model"]["engineVersion"] == "5.2.4"

            # flood-processing-v1 products generated inside the pipeline from the real output
            assert (settings.results_root / sid / "flood" / "manifest.json").is_file()
            timeline = client.get(f"{API}/simulations/{sid}/flood/timeline").json()
            assert len(timeline["timestamps"]) == 190
            peak = timeline["entries"][timeline["peakIndex"]]
            assert peak["time"] == "2023-12-03T22:00:00Z" and peak["floodingNodeCount"] == 19
            flood = client.get(f"{API}/simulations/{sid}/flood").json()
            assert all(c["passed"] for c in flood["validation"] if c["hard"])
            assert client.get(peak["asset"]["url"]).status_code == 200

            # decision-support products derived from the real SWMM run
            bottlenecks = client.get(f"{API}/simulations/{sid}/bottlenecks").json()
            assert bottlenecks["bottlenecks"][0]["linkId"] == "C169" and bottlenecks["bottlenecks"][0]["severity"] == "HIGH"
            assert "C162" not in {b["linkId"] for b in bottlenecks["bottlenecks"]}
            exposure = client.get(f"{API}/simulations/{sid}/exposure").json()
            assert exposure["peak"]["buildings"]["intersectingCount"] == 783
            recs = client.get(f"{API}/simulations/{sid}/recommendations").json()
            assert recs["recommendations"][0]["id"] == "rec-r1-C169"

        # Separate workspaces, identical deterministic results.
        assert settings.workdir / ids[0] != settings.workdir / ids[1]
        a, b = (container.results.results.read(sid, "results.json") for sid in ids)
        assert a["routingContinuity"] == b["routingContinuity"]
        assert a["nodes"]["flooding"] == b["nodes"]["flooding"]

    assert sha256_file(MODEL_INP) == master_sha  # the master model was never modified


def test_real_swmm_rainfall_scenarios_reproduce_baseline_and_scale_rainfall(make_settings):
    """scenario-analysis-v1 with the real SWMM executable: 1.00x must reproduce the baseline, 1.25x must use scaled rainfall."""
    from tests.conftest import ARCHIVED_OUT

    master_sha = sha256_file(MODEL_INP)
    settings = make_settings(SIMULATION_MAX_CONCURRENT=2)
    container = Container.build(settings)
    with TestClient(create_app(settings, container)) as client:
        post = lambda m: client.post(f"{API}/simulations", json={"scenarioId": "michaung-2023", "parameters": {"rainfallMultiplier": m}}).json()["simulationId"]  # noqa: E731
        base, scen = post(1.0), post(1.25)
        fb, fs = _wait(client, base), _wait(client, scen)
        assert fb["status"] == "COMPLETED" and fs["status"] == "COMPLETED", (fb, fs)

        # Baseline reproduction: identical model bytes and identical SWMM binary output.
        assert fb["scenarioRun"]["transformedModelSha256"] == master_sha
        assert sha256_file(settings.workdir / base / "output.out") == sha256_file(ARCHIVED_OUT)
        kb = client.get(f"{API}/simulations/{base}/kpis").json()
        assert kb["hydraulics"]["simulatedFloodingVolume"]["value"] == 197_876_000.0
        assert kb["modelDiagnostics"]["routingContinuityError"]["value"] == 0.068
        assert client.get(f"{API}/simulations/{base}/flood").json()["peakTime"] == "2023-12-03T22:00:00Z"

        # Scenario: rainfall scaled exactly, SWMM used it, results differ from baseline.
        ks = client.get(f"{API}/simulations/{scen}/kpis").json()
        assert ks["rainfall"]["total"]["value"] == pytest.approx(282.835 * 1.25, abs=1e-3)
        assert ks["rainfall"]["peakIntensity"]["value"] == pytest.approx(23.35 * 1.25, abs=1e-3)
        assert sha256_file(settings.workdir / scen / "output.out") != sha256_file(ARCHIVED_OUT)
        assert ks["hydraulics"]["simulatedFloodingVolume"]["value"] > kb["hydraulics"]["simulatedFloodingVolume"]["value"]

        comparison = client.post(f"{API}/comparisons", json={"simulationIds": [base, scen]}).json()
        metrics = {m["key"]: m for m in comparison["metrics"]}
        assert metrics["totalRainfall"]["percentChange"] == 25.0
        assert "C169" in {p["linkId"] for p in comparison["bottlenecks"]["persisting"]}
    assert sha256_file(MODEL_INP) == master_sha
