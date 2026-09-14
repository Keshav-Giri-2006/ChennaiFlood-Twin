import json
from datetime import UTC, datetime

import numpy as np
import pytest
from shapely.geometry import Point, shape

from app.analysis.flood_processing import FloodProcessingError, generate_flood_products, node_crown_heights, parse_time_query, timestamp_key
from app.core.config import Settings
from app.gis.network_mapping import load_network_mapping
from app.gis.transform import UTM44N, declared_crs, transform_xy
from app.repositories.registry import Registry
from app.simulation.inp_reader import read_inp
from app.simulation.output_reader import read_output
from app.simulation.report_parser import parse_report
from app.utils.files import read_json
from tests.conftest import ARCHIVED_OUT, ARCHIVED_RPT, MODEL_INP, REPO_ROOT

FIXED_TIME = datetime(2026, 9, 13, tzinfo=UTC)


@pytest.fixture(scope="module")
def inputs():
    settings = Settings(DATA_DIR=REPO_ROOT)
    model = Registry(settings.registry_dir).models["ward176-hydraulic-reconstructed-v1"]
    inp = read_inp(MODEL_INP)
    network = load_network_mapping(inp, settings.processed_dir / model.network_mapping["conduitsCsv"], settings.processed_dir / model.network_mapping["nodesCsv"])
    ward_fc = read_json(settings.processed_dir / "gis" / "ward176_boundary.geojson")
    assert declared_crs(ward_fc) == UTM44N
    return {"inp": inp, "network": network, "ward": shape(ward_fc["features"][0]["geometry"]), "report": parse_report(ARCHIVED_RPT), "output": read_output(ARCHIVED_OUT)}


def _run(inputs, output=None, report=None):
    return generate_flood_products(
        simulation_id="00000000-0000-0000-0000-000000000001",
        scenario_id="michaung-2023",
        model_version="ward176-hydraulic-reconstructed-v1",
        flood_processing_version="flood-processing-v1",
        output=output or inputs["output"],
        report=report or inputs["report"],
        inp=inputs["inp"],
        network=inputs["network"],
        ward_utm=inputs["ward"],
        generated_at=FIXED_TIME,
    )


@pytest.fixture(scope="module")
def products(inputs):
    return _run(inputs)


def test_all_hard_checks_pass_on_real_output(products):
    hard = [c for c in products.diagnostics["checks"] if c["hard"]]
    assert hard and all(c["passed"] for c in hard)
    volume = next(c for c in products.diagnostics["checks"] if c["check"] == "crosscheck.cumulativeOverflowVsReport")
    assert abs(volume["details"]["relativeDifference"]) < 0.05
    # Nodes that overflow only between reporting timestamps are reported, not hidden.
    missed = next(c for c in products.diagnostics["checks"] if c["check"] == "crosscheck.reportFloodingNodesSeenInSamples")
    assert missed["passed"] is False and missed["hard"] is False
    assert set(missed["details"]["nodesFloodingOnlyBetweenReportTimes"]) == {"J130", "J135"}


def test_timeline_uses_actual_swmm_timestamps(products, inputs):
    entries = products.timeline["entries"]
    out = inputs["output"]
    assert len(entries) == out.n_periods == 190
    assert [e["time"] for e in entries] == [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in out.times]
    assert entries[0]["time"] == "2023-12-02T00:30:00Z"
    peak = entries[products.timeline["peakIndex"]]
    assert peak["time"] == "2023-12-03T22:00:00Z"
    assert peak["systemFloodingRateCms"] == pytest.approx(max(out.system_series("flooding")), abs=1e-6)
    cumulative = [e["approxCumulativeSystemOverflowM3"] for e in entries]
    assert cumulative == sorted(cumulative)


def test_timeslice_features_correspond_to_swmm_node_states(products, inputs):
    out = inputs["output"]
    flooding = np.asarray(out.node_series("flooding"))
    report_flooded = {r["id"] for r in inputs["report"].node_flooding}
    for entry in products.timeline["entries"]:
        fc = products.timeslices[entry["key"]]
        nodes = [f for f in fc["features"] if f["properties"]["featureType"] == "node"]
        zones = [f for f in fc["features"] if f["properties"]["featureType"] == "influenceZone"]
        flooding_nodes = {f["properties"]["nodeId"] for f in nodes if f["properties"]["state"] == "FLOODING"}
        expected = {out.node_ids[i] for i in np.where(flooding[entry["index"]] > 0)[0]}
        assert flooding_nodes == expected
        assert flooding_nodes <= report_flooded
        assert entry["floodingNodeCount"] == len(expected)
        assert {z["properties"]["nodeId"] for z in zones} <= flooding_nodes  # zones only for overflowing nodes
        for f in nodes:
            p = f["properties"]
            if p["state"] == "FLOODING":
                assert p["floodingRateCms"] > 0 and p["overflowClass"] in ("LOW", "MODERATE", "HIGH")
            else:
                assert p["floodingRateCms"] == 0 and p["overflowClass"] is None


def test_zone_geometry_valid_contained_and_in_lonlat(products, inputs):
    ward_bbox = (80.2064, 12.9677, 80.2207, 12.9874)
    zones = {f["properties"]["nodeId"]: f for f in products.zones["features"]}
    assert len(zones) == 227  # J035's cell lies entirely outside the ward
    total = 0.0
    for f in products.zones["features"]:
        g = shape(f["geometry"])
        assert g.is_valid and not g.is_empty
        minx, miny, maxx, maxy = g.bounds
        assert ward_bbox[0] <= minx and maxx <= ward_bbox[2] and ward_bbox[1] <= miny and maxy <= ward_bbox[3]
        total += f["properties"]["zoneAreaM2"]
    assert total == pytest.approx(1_786_223.75, rel=1e-4)
    # Each in-ward node lies inside its own zone. Nodes outside the ward boundary
    # (13 provisional/boundary nodes) keep only the in-ward part of their cell.
    ward, network = inputs["ward"], inputs["network"]
    checked = 0
    for node_id, f in zones.items():
        loc = network.node_locations[node_id]
        point_utm = Point(loc.easting_m, loc.northing_m)
        if not ward.contains(point_utm):
            continue
        lons, lats = transform_xy(UTM44N, [loc.easting_m], [loc.northing_m])
        assert shape(f["geometry"]).buffer(1e-6).contains(Point(lons[0], lats[0])), node_id
        checked += 1
    assert checked == 215


def test_processing_is_reproducible(inputs, products):
    again = _run(inputs)
    assert json.dumps(again.timeline, sort_keys=True) == json.dumps(products.timeline, sort_keys=True)
    assert json.dumps(again.timeslices, sort_keys=True) == json.dumps(products.timeslices, sort_keys=True)
    assert json.dumps(again.zones, sort_keys=True) == json.dumps(products.zones, sort_keys=True)


def test_no_flood_state_produces_empty_slices(inputs):
    class NoFloodOutput:
        def __init__(self, real):
            self._real = real
            self.node_ids, self.times, self.report_step_seconds, self.n_periods = real.node_ids, real.times, real.report_step_seconds, real.n_periods

        def node_series(self, variable):
            series = self._real.node_series(variable)
            if variable in ("flooding",):
                return [[0.0] * len(row) for row in series]
            if variable in ("depth", "head"):
                base = self._real.node_series("depth") if variable == "depth" else self._real.node_series("head")
                return [[0.0 if variable == "depth" else v for v in row] for row in base]
            return series

        def system_series(self, variable):
            values = self._real.system_series(variable)
            return [0.0] * len(values) if variable == "flooding" else values

    report = parse_report(ARCHIVED_RPT)
    report.node_flooding = []
    report.node_surcharge = []
    report.routing_continuity = {**report.routing_continuity, "Flooding Loss": {"volumeHectareM": 0.0, "volumeMillionLiters": 0.0}}
    result = _run(inputs, output=NoFloodOutput(inputs["output"]), report=report)
    assert all(not e["hasFlooding"] and e["floodingNodeCount"] == 0 for e in result.timeline["entries"])
    assert all(fc["features"] == [] for fc in result.timeslices.values())
    metrics = result.manifest["summary"]["metrics"]
    assert metrics["firstFloodingTime"]["value"] is None
    assert metrics["floodingDuration"]["value"] == 0
    assert result.manifest["legend"]["overflowClasses"][2]["maxInclusiveCms"] == 0.0


def test_mismatched_output_is_rejected(inputs):
    class Wrong:
        node_ids = ["J001"]

    with pytest.raises(FloodProcessingError):
        _run(inputs, output=Wrong())


def test_crown_height_uses_offsets_and_full_depth(inputs):
    inp = inputs["inp"]
    crowns = node_crown_heights(inp)
    c149 = inp.conduits["C149"]
    assert c149["fromNode"] == "J057" and c149["inOffsetM"] == pytest.approx(0.426)
    assert crowns["J057"] >= 0.426 + inp.xsections["C149"]["fullDepthM"]


def test_time_parsing_and_keys():
    assert timestamp_key(parse_time_query("2023-12-03T22:00:00Z")) == "20231203T220000Z"
    assert timestamp_key(parse_time_query("2023-12-04T03:30:00+05:30").astimezone(UTC)) == "20231203T220000Z"
    with pytest.raises(ValueError):
        parse_time_query("2023-12-03T22:00:00")  # naive timestamps are ambiguous
    with pytest.raises(ValueError):
        parse_time_query("yesterday")
