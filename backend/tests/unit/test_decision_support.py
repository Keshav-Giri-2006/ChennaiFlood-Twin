"""Unit tests for bottleneck-analysis-v1, exposure-analysis-v1 and decision-support-v1 building blocks."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from shapely.geometry import box

from app.analysis.bottleneck_analysis import analyse_bottlenecks, network_components
from app.analysis.exposure_analysis import MIN_INTERSECTION_AREA_M2, Asset, ExposureAnalysisError, analyse_exposure
from app.analysis.recommendations import generate_recommendations
from app.gis.network_mapping import load_network_mapping
from app.simulation.inp_reader import read_inp
from app.simulation.report_parser import parse_report
from tests.conftest import ARCHIVED_RPT, MODEL_INP, REPO_ROOT

NOW = datetime(2026, 9, 14, tzinfo=UTC)
PROCESSED = REPO_ROOT / "data_processed"


@pytest.fixture(scope="module")
def model():
    inp = read_inp(MODEL_INP)
    network = load_network_mapping(inp, PROCESSED / "network" / "ward176_resolved_conduits.csv", PROCESSED / "network" / "ward176_resolved_nodes.csv")
    import csv

    with (PROCESSED / "network" / "ward176_resolved_conduits.csv").open(encoding="utf-8", newline="") as handle:
        source = {r["recon_conduit_id"]: r for r in csv.DictReader(handle)}
    geometry = {lid: {"type": "LineString", "coordinates": [[80.21, 12.98], [80.2101, 12.9801]]} for lid in inp.conduits}
    return inp, network, source, geometry, parse_report(ARCHIVED_RPT)


def _bottlenecks(model, report=None, context=None):
    inp, network, source, geometry, archived = model
    return analyse_bottlenecks(
        simulation_id="00000000-0000-0000-0000-000000000001", scenario_id="michaung-2023", model_version="ward176-hydraulic-reconstructed-v1",
        analysis_version="bottleneck-analysis-v1", report=report or archived, inp=inp, network=network, components=network_components(inp),
        source_conduits=source, invert_decisions={}, diagnostic_context=context or {}, conduit_geometry=geometry, node_lonlat={}, generated_at=NOW,
    )


def test_network_components_of_candidate_model(model):
    inp = model[0]
    comps = network_components(inp)
    assert len(comps.components) == 48
    assert sum(1 for c in comps.components if c["outfalls"]) == 4
    assert sorted(n for c in comps.components for n in c["nodes"]) == sorted(inp.node_ids)
    assert sum(len(c["links"]) for c in comps.components) == 182
    assert comps.has_outfall("J161") and not comps.has_outfall("J176") and not comps.has_outfall("J135")


def test_bottleneck_criteria_on_real_report(model):
    doc, geojson = _bottlenecks(model)
    by_id = {b["linkId"]: b for b in doc["bottlenecks"]}
    assert doc["summary"]["potentialBottlenecks"] == len(doc["bottlenecks"]) == 12
    assert doc["summary"]["bySeverity"] == {"LOW": 11, "MODERATE": 0, "HIGH": 1}

    c169 = by_id["C169"]
    assert c169["severity"] == "HIGH" and c169["score"] == 1.0 and c169["interpretation"] == "CAPACITY_LIMITED"
    assert [c["met"] for c in c169["criteria"]] == [True, True, True, True]
    assert c169["hydraulics"]["hoursCapacityLimited"] == 9.47 and c169["hydraulics"]["maxOverFullFlow"] == 2.2
    assert c169["criteria"][3]["value"] == ["J161"]
    assert c169["sourceObjectId"] == 5909 and doc["bottlenecks"][0]["linkId"] == "C169"

    for b in doc["bottlenecks"]:
        met = [c["met"] for c in b["criteria"]]
        assert any(met[:3]), "eligibility requires a hydraulic loading criterion"
        assert b["score"] == sum(met) / 4
        assert b["sourceObjectId"] == model[1].link_to_object_id[b["linkId"]]
        if not b["networkContext"]["componentHasOutfall"]:
            assert b["severity"] == "LOW" and b["confidence"] == "LOW"
    assert by_id["C020"]["severityCappedByNetworkContext"] and by_id["C020"]["uncappedSeverity"] == "HIGH"
    assert [f["id"] for f in geojson["features"]] == [b["linkId"] for b in doc["bottlenecks"]]


def test_numerical_diagnostics_are_not_bottlenecks(model):
    context = {"links": {"C162": {"sourceObjectId": 5902, "finding": "x", "decision": "RETAIN", "confidence": "Medium", "source": "doc"}}}
    doc, _ = _bottlenecks(model, context=context)
    ids = {b["linkId"] for b in doc["bottlenecks"]}
    for lid in ("C162", "C166", "C175", "C180", "C086"):
        assert lid not in ids
    numerical = {n["linkId"]: n for n in doc["numericalDiagnostics"]}
    assert numerical["C162"]["timeStepCriticalPercent"] == 35.7 and numerical["C162"]["isPotentialBottleneck"] is False
    assert numerical["C162"]["projectInvestigation"]["decision"] == "RETAIN"
    assert numerical["C166"]["flowInstabilityIndex"] == 11.0 and numerical["C166"]["componentHasOutfall"] is False


def test_context_with_wrong_object_id_is_rejected(model):
    from app.analysis.bottleneck_analysis import BottleneckAnalysisError

    with pytest.raises(BottleneckAnalysisError):
        _bottlenecks(model, context={"links": {"C162": {"sourceObjectId": 1, "finding": "x"}}})


def test_no_hydraulic_loading_gives_empty_result(model):
    archived = model[4]
    quiet = replace(
        archived,
        conduit_surcharge=[],
        node_flooding=[],
        link_flow=[{**r, "maxOverFullFlow": 0.2 if r["maxOverFullFlow"] is not None else None} for r in archived.link_flow],
    )
    doc, geojson = _bottlenecks(model, report=quiet)
    assert doc["bottlenecks"] == [] and geojson["features"] == []
    assert doc["summary"]["potentialBottlenecks"] == 0


def _exposure(periods, buildings, roads=None, component_has_outfall=None):
    zones = {"J1": box(0, 0, 10, 10), "J2": box(10, 0, 20, 10)}
    return analyse_exposure(
        simulation_id="s", scenario_id="sc", model_version="m", analysis_version="exposure-analysis-v1", flood_processing_version="flood-processing-v1",
        zones_utm=zones, times=[f"t{i}" for i in range(len(periods))], flooding_nodes_by_period=periods, peak_index=0, interval_minutes=30,
        buildings=buildings, roads=roads or [Asset(100, box(5, 4, 15, 6), "Main Rd")], node_component={"J1": 1, "J2": 2},
        component_has_outfall=component_has_outfall or {1: True, 2: False}, generated_at=NOW,
    )


def test_exposure_intersection_counts_and_areas():
    buildings = [
        Asset(1, box(1, 1, 3, 3)),        # inside J1 (4 m2)
        Asset(2, box(9, 1, 11, 3)),       # straddles J1/J2 (2 + 2 m2)
        Asset(3, box(20, 0, 22, 2)),      # touches J2 edge only -> not exposed
        Asset(4, box(30, 30, 31, 31)),    # far away
    ]
    doc, assoc = _exposure([["J1"], ["J1", "J2"], []], buildings)
    assert doc["totals"]["buildings"]["count"] == 4
    assert [e["buildingsIntersecting"] for e in doc["timeline"]] == [2, 2, 0]
    assert [e["buildingFootprintAreaM2"] for e in doc["timeline"]] == [6.0, 8.0, 0.0]
    event = doc["event"]["buildings"]
    assert event["intersectingCount"] == 2 and event["percentOfBuildings"] == 50.0 and event["footprintAreaWithinZonesM2"] == 8.0
    assert event["intersectingZonesOfNodesWithoutOutfallCount"] == 1  # building 2 via J2 (no outfall)
    assert doc["event"]["roads"] == {**doc["event"]["roads"], "intersectingCount": 1, "areaWithinZonesM2": 20.0}
    assert doc["maxConcurrent"]["buildingsIntersecting"]["index"] == 0
    assert assoc["nodes"]["J1"]["buildings"] == [[1, 4.0], [2, 2.0]]
    assert {n["nodeId"]: n["reportingPeriodsFlooding"] for n in doc["byNode"]} == {"J1": 2, "J2": 1}
    assert MIN_INTERSECTION_AREA_M2 > 0


def test_exposure_without_flooding_is_empty():
    doc, assoc = _exposure([[], []], [Asset(1, box(1, 1, 2, 2))])
    assert doc["event"]["buildings"]["intersectingCount"] == 0 and doc["byNode"] == [] and assoc["nodes"] == {}


def test_exposure_rejects_duplicate_ids():
    with pytest.raises(ExposureAnalysisError):
        _exposure([["J1"]], [Asset(1, box(1, 1, 2, 2)), Asset(1, box(3, 3, 4, 4))])


def test_recommendations_are_traceable_and_rule_based(model):
    inp, network, source, _geometry, report = model
    bottlenecks, _ = _bottlenecks(model)
    exposure = {"exposureAnalysisVersion": "exposure-analysis-v1", "byNode": []}
    doc = generate_recommendations(
        simulation_id="s", scenario_id="sc", model_version="m", decision_version="decision-support-v1", bottlenecks=bottlenecks, exposure=exposure,
        report=report, inp=inp, network=network, components=network_components(inp), source_conduits=source, drain_obstacles={}, generated_at=NOW,
    )
    recs = doc["recommendations"]
    assert [r["id"] for r in recs if r["rule"] == "R1"] == ["rec-r1-C169"]
    comps = network_components(inp)
    for r in recs:
        assert r["priority"] in ("HIGH", "MEDIUM", "LOW") and r["confidence"] in ("MEDIUM", "LOW")
        assert r["why"] and r["evidence"]["metrics"] and r["disclaimer"]
        for link in r["evidence"]["links"]:
            assert link["linkId"] in inp.conduits and network.link_to_object_id[link["linkId"]] == link["sourceObjectId"]
        if r["rule"] == "R2":
            assert all(not comps.has_outfall(n) for n in r["evidence"]["nodes"])
        if r["rule"] == "R3":
            assert all(comps.has_outfall(n) for n in r["evidence"]["nodes"])
    assert not any(r["rule"] == "R4" for r in recs)  # no exposure evidence -> no exposure recommendation
    assert not any(r["rule"] == "R5" and "obstacles" in r["why"] for r in recs)  # no obstacle records supplied
    priorities = [("HIGH", "MEDIUM", "LOW").index(r["priority"]) for r in recs]
    assert priorities == sorted(priorities)


def test_recommendations_need_evidence(model):
    inp, network, source, _geometry, report = model
    quiet = replace(report, conduit_surcharge=[], node_flooding=[], time_step_critical_elements=[], highest_flow_instability_indexes=[],
                    link_flow=[{**r, "maxOverFullFlow": 0.1} for r in report.link_flow])
    bottlenecks, _ = _bottlenecks(model, report=quiet)
    doc = generate_recommendations(
        simulation_id="s", scenario_id="sc", model_version="m", decision_version="decision-support-v1", bottlenecks=bottlenecks,
        exposure={"exposureAnalysisVersion": "exposure-analysis-v1", "byNode": []}, report=quiet, inp=inp, network=network,
        components=network_components(inp), source_conduits=source, drain_obstacles={5791: "Syntax Tank"}, generated_at=NOW,
    )
    assert doc["recommendations"] == [] and doc["summary"]["total"] == 0
