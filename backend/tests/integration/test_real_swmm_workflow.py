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

        # Separate workspaces, identical deterministic results.
        assert settings.workdir / ids[0] != settings.workdir / ids[1]
        a, b = (container.results.results.read(sid, "results.json") for sid in ids)
        assert a["routingContinuity"] == b["routingContinuity"]
        assert a["nodes"]["flooding"] == b["nodes"]["flooding"]

    assert sha256_file(MODEL_INP) == master_sha  # the master model was never modified
