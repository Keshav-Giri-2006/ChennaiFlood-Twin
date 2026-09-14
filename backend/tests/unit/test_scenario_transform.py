"""scenario-analysis-v1 rainfall transformation and parameter validation."""

import math

import pytest

from app.simulation.scenario_transform import ScenarioParameterError, ScenarioTransformError, apply_rainfall_multiplier, scaled_value, validate_multiplier, verify_transform
from app.utils.files import sha256_file
from tests.conftest import MODEL_INP

SPEC = {"parameter": "rainfallMultiplier", "minimum": 0.5, "maximum": 2.0, "decimals": 2}


@pytest.fixture(scope="module")
def master_text():
    return MODEL_INP.read_bytes().decode("utf-8")


def test_multiplier_one_reproduces_the_master_model_byte_for_byte(master_text, tmp_path):
    t = apply_rainfall_multiplier(master_text, "Michaung", 1.0, 0.5)
    assert t.text == master_text
    out = tmp_path / "copy.inp"
    out.write_bytes(t.text.encode("utf-8"))
    assert sha256_file(out) == sha256_file(MODEL_INP)
    assert verify_transform(master_text, t.text, "Michaung", 1.0)["changedLines"] == 0


def test_multiplier_scales_only_rainfall_values(master_text):
    t = apply_rainfall_multiplier(master_text, "Michaung", 1.25, 0.5)
    assert t.records == 192
    assert t.baseline_total_mm == pytest.approx(282.835, abs=1e-3)
    assert t.transformed_total_mm == pytest.approx(282.835 * 1.25, abs=192 * 0.5e-6 * 0.5 + 1e-9)
    assert t.transformed_peak_mm_hr == pytest.approx(23.35 * 1.25, abs=1e-6)
    report = verify_transform(master_text, t.text, "Michaung", 1.25)
    nonzero = sum(1 for line in master_text.splitlines() if line.startswith("Michaung ") and float(line.split()[-1]) != 0.0)
    assert report["changedLines"] == nonzero == 145 and report["maxAbsRoundingErrorMmHr"] <= 5e-7
    changed = [(a, b) for a, b in zip(master_text.splitlines(), t.text.splitlines()) if a != b]
    assert all(a.startswith("Michaung ") and a.rsplit(" ", 1)[0] == b.rsplit(" ", 1)[0] for a, b in changed)


def test_verification_rejects_changed_timestamps_or_other_lines(master_text):
    t = apply_rainfall_multiplier(master_text, "Michaung", 1.5, 0.5)
    with pytest.raises(ScenarioTransformError):
        verify_transform(master_text, t.text.replace("Michaung 12/3/2023 22:00", "Michaung 12/3/2023 22:30", 1), "Michaung", 1.5)
    with pytest.raises(ScenarioTransformError):
        verify_transform(master_text, t.text.replace("DYNWAVE", "KINWAVE", 1), "Michaung", 1.5)
    with pytest.raises(ScenarioTransformError):
        verify_transform(master_text, master_text, "Michaung", 1.5)  # untransformed copy is detected
    with pytest.raises(ScenarioTransformError):
        apply_rainfall_multiplier(master_text, "NoSuchSeries", 1.5, 0.5)


def test_decimal_scaling_has_no_float_artefacts():
    assert scaled_value("0.340000", 1.0) == "0.340000"
    assert scaled_value("23.350000", 1.25) == "29.187500"
    assert scaled_value("0.000001", 1.5) == "0.000002"  # 0.0000015 -> half-even


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, -1.0, 0.0, 0.49, 2.01, 1_000_000, True, "1.25", None, 1.255])
def test_invalid_multipliers_are_rejected(value):
    with pytest.raises(ScenarioParameterError):
        validate_multiplier(value, SPEC)


@pytest.mark.parametrize("value", [0.5, 1, 1.0, 1.25, 1.5, 2.0])
def test_valid_multipliers(value):
    assert validate_multiplier(value, SPEC) == float(value)
