import struct
from pathlib import Path

import pytest

from app.analysis.result_processing import ResultProcessingError, process_results
from app.simulation.inp_reader import read_inp
from app.simulation.output_reader import MAGIC, OutputFormatError, read_output
from app.simulation.rainfall import read_giovanni_csv
from app.simulation.report_parser import ReportParseError, parse_report
from tests.conftest import ARCHIVED_OUT, ARCHIVED_RPT, MODEL_INP, RAINFALL_CSV


def test_report_parser_extracts_documented_candidate_metrics():
    r = parse_report(ARCHIVED_RPT)
    assert r.engine_version == "5.2.4"
    assert r.errors == []
    assert [w["code"] for w in r.warnings] == ["02"] * 7
    assert r.element_count["nodes"] == 228 and r.element_count["links"] == 182
    assert r.runoff_continuity["Total Precipitation"]["depthMm"] == 282.835
    assert r.runoff_continuity["continuityErrorPercent"] == -0.018
    assert r.routing_continuity["Flooding Loss"]["volumeMillionLiters"] == 197.876
    assert r.routing_continuity["External Outflow"]["volumeMillionLiters"] == 67.405
    assert r.routing_continuity["Wet Weather Inflow"]["volumeMillionLiters"] == 271.424
    assert r.routing_continuity["Final Stored Volume"]["volumeMillionLiters"] == 5.958
    assert r.routing_continuity["continuityErrorPercent"] == 0.068
    assert r.routing_time_step["Minimum Time Step"] == 0.5
    assert r.routing_time_step["% of Steps Not Converging"] == 0.37
    assert [e["id"] for e in r.time_step_critical_elements] == ["C162", "C180", "C175", "C086"]
    assert r.highest_flow_instability_indexes[0] == {"elementType": "LINK", "id": "C166", "index": 11.0}
    assert len(r.node_depth) == 228 and len(r.link_flow) == 182 and len(r.subcatchment_runoff) == 35
    assert len(r.node_flooding) == 22
    assert r.outfall_system["totalVolumeMillionLiters"] == 67.404
    j006 = next(n for n in r.node_flooding if n["id"] == "J006")
    assert j006["timeOfMaximum"] == "2023-12-03T21:59:00Z"
    assert sum(n["totalFloodVolumeMillionLiters"] for n in r.node_flooding) == pytest.approx(197.876, abs=0.05)


def test_report_parser_reports_swmm_errors(tmp_path: Path):
    rpt = tmp_path / "err.rpt"
    rpt.write_text("\n  EPA STORM WATER MANAGEMENT MODEL - VERSION 5.2 (Build 5.2.4)\n\n  ERROR 200: one or more errors detected in input file.\n", encoding="utf-8")
    r = parse_report(rpt)
    assert r.errors == [{"code": "200", "message": "one or more errors detected in input file."}]


def test_report_parser_rejects_unparseable_numbers(tmp_path: Path):
    text = ARCHIVED_RPT.read_text(encoding="utf-8").replace("Flooding Loss ............        19.787       197.876", "Flooding Loss ............        19.787       ###")
    rpt = tmp_path / "bad.rpt"
    rpt.write_text(text, encoding="utf-8")
    with pytest.raises(ReportParseError):
        parse_report(rpt)


def test_output_reader_reads_archived_binary():
    out = read_output(ARCHIVED_OUT)
    assert out.version == 52004 and out.flow_units == "CMS"
    assert len(out.node_ids) == 228 and len(out.link_ids) == 182 and len(out.subcatchment_ids) == 35
    assert out.n_periods == 190 and out.report_step_seconds == 1800
    rain = out.system_series("rainfall")
    assert max(rain) == pytest.approx(23.35, abs=1e-4)


def test_output_reader_rejects_truncated_file(tmp_path: Path):
    data = ARCHIVED_OUT.read_bytes()
    truncated = tmp_path / "trunc.out"
    truncated.write_bytes(data[: len(data) // 2])
    with pytest.raises(OutputFormatError):
        read_output(truncated)


def test_output_reader_rejects_error_code(tmp_path: Path):
    data = bytearray(ARCHIVED_OUT.read_bytes())
    struct.pack_into("<i", data, len(data) - 8, 1)  # closing-record error code
    bad = tmp_path / "error.out"
    bad.write_bytes(bytes(data))
    with pytest.raises(OutputFormatError, match="error code"):
        read_output(bad)
    assert struct.unpack_from("<i", data, len(data) - 4)[0] == MAGIC


def _process(inp):
    return process_results(
        simulation_id="00000000-0000-0000-0000-000000000001",
        scenario_id="michaung-2023",
        model_version="ward176-hydraulic-reconstructed-v1",
        processing_version="swmm-results-v1",
        report=parse_report(ARCHIVED_RPT),
        output=read_output(ARCHIVED_OUT),
        inp=inp,
        rainfall=read_giovanni_csv(RAINFALL_CSV, "mean_GPM_3IMERGHH_07_precipitation", 30),
    )


def test_result_processing_produces_labelled_units():
    results, series = _process(read_inp(MODEL_INP))
    routing = results["routingContinuity"]
    assert routing["simulatedFloodingVolumeL"] == 197_876_000.0
    assert routing["dataType"] == "model-derived"
    assert "not an observed flood volume" in routing["note"]
    assert all(c["passed"] for c in results["processingChecks"])
    assert results["simulationPeriod"]["firstReportTime"] == "2023-12-02T00:30:00Z"
    assert len(series["timestamps"]) == 190
    assert len(series["nodes"]["depthM"][0]) == 228
    assert "observed" not in "".join(results.keys()).lower()


def test_result_processing_rejects_mismatched_model():
    inp = read_inp(MODEL_INP)
    inp.junctions.pop("J001")
    with pytest.raises(ResultProcessingError):
        _process(inp)
