from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.simulation.inp_reader import InpFormatError, read_inp
from app.simulation.rainfall import RainfallFormatError, read_giovanni_csv
from tests.conftest import MODEL_INP, RAINFALL_CSV

COLUMN = "mean_GPM_3IMERGHH_07_precipitation"


def test_real_model_structure():
    inp = read_inp(MODEL_INP)
    assert len(inp.subcatchments) == 35
    assert len(inp.node_ids) == 228
    assert len(inp.link_ids) == 182
    assert inp.options["FLOW_ROUTING"] == "DYNWAVE"
    assert inp.options["FLOW_UNITS"] == "CMS"
    assert inp.rain_gages["GAGE_MICH"]["source"] == "Michaung"
    assert len(inp.timeseries["Michaung"]) == 192
    assert "C182" not in inp.conduits  # confirmed duplicate removed from the candidate
    for retained in ("C162", "C166", "C174", "C175", "C180", "C086", "C190"):
        assert retained in inp.conduits
    assert inp.simulation_start() == datetime(2023, 12, 2, tzinfo=UTC)


def test_inp_reader_rejects_bad_numbers(tmp_path: Path):
    bad = tmp_path / "bad.inp"
    bad.write_text("[JUNCTIONS]\nJ1 abc 1.0 0 0 0\n", encoding="utf-8")
    with pytest.raises(InpFormatError):
        read_inp(bad)


def test_real_rainfall_metadata_matches_documented_event():
    series = read_giovanni_csv(RAINFALL_CSV, COLUMN, 30)
    assert len(series.times) == 192
    assert series.total_mm == pytest.approx(282.835, abs=0.001)
    assert series.peak_mm_hr == pytest.approx(23.35, abs=1e-6)
    assert series.start_time == datetime(2023, 12, 2, tzinfo=UTC)
    assert series.end_time == datetime(2023, 12, 5, 23, 30, tzinfo=UTC)
    daily = series.daily_totals_mm()
    assert daily["2023-12-03"] == pytest.approx(114.78, abs=0.01)
    assert daily["2023-12-04"] == pytest.approx(152.36, abs=0.01)


def _csv(tmp_path: Path, rows: list[str], column: str = COLUMN) -> Path:
    path = tmp_path / "rain.csv"
    path.write_text("Title:,test\nFill Value (x):, -9999.9\n\ntime, " + column + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_rainfall_rejects_irregular_interval(tmp_path: Path):
    path = _csv(tmp_path, ["2023-12-02 00:00:00,1", "2023-12-02 01:00:00,2"])
    with pytest.raises(RainfallFormatError, match="Irregular"):
        read_giovanni_csv(path, COLUMN, 30)


def test_rainfall_rejects_fill_values(tmp_path: Path):
    path = _csv(tmp_path, ["2023-12-02 00:00:00,1", "2023-12-02 00:30:00,-9999.9"])
    with pytest.raises(RainfallFormatError):
        read_giovanni_csv(path, COLUMN, 30)


def test_rainfall_rejects_wrong_column(tmp_path: Path):
    path = _csv(tmp_path, ["2023-12-02 00:00:00,1"], column="other_variable")
    with pytest.raises(RainfallFormatError, match="Expected value column"):
        read_giovanni_csv(path, COLUMN, 30)
