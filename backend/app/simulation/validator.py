"""Pre-execution validation of the approved model and scenario rainfall.

Validation confirms that what is about to run is exactly the approved,
unmodified model and that its embedded rainfall series matches the scenario's
raw source data. Nothing is corrected here; any mismatch fails validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.repositories.registry import ModelDefinition, ScenarioDefinition
from app.simulation.inp_reader import InpFormatError, InpModel, read_inp
from app.simulation.rainfall import RainfallFormatError, RainfallSeries, read_giovanni_csv
from app.utils.files import sha256_file

# The .inp stores rainfall rounded to 6 decimals; the raw CSV has float noise.
RAINFALL_MATCH_TOLERANCE_MM_HR = 1e-5


class ValidationFailure(Exception):
    def __init__(self, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


@dataclass
class ValidatedInputs:
    model_path: Path
    model_sha256: str
    inp: InpModel
    rainfall_path: Path
    rainfall_sha256: str
    rainfall: RainfallSeries
    checks: list[dict[str, Any]] = field(default_factory=list)


def model_path_for(model: ModelDefinition, models_dir: Path) -> Path:
    return (models_dir / model.inp_file).resolve()


def rainfall_path_for(scenario: ScenarioDefinition, raw_dir: Path) -> Path:
    return (raw_dir / scenario.rainfall["rawFile"]).resolve()


def load_rainfall(scenario: ScenarioDefinition, raw_dir: Path) -> RainfallSeries:
    return read_giovanni_csv(
        rainfall_path_for(scenario, raw_dir),
        value_column=scenario.rainfall["valueColumn"],
        interval_minutes=int(scenario.rainfall["intervalMinutes"]),
    )


def validate_inputs(scenario: ScenarioDefinition, model: ModelDefinition, models_dir: Path, raw_dir: Path) -> ValidatedInputs:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, code: str, message: str, details: Any = None) -> None:
        checks.append({"check": name, "passed": passed})
        if not passed:
            raise ValidationFailure(code, message, details)

    check("model.approved", model.approved, "MODEL_VALIDATION_FAILED", "The requested model version is not approved for execution.")
    binding = scenario.compatible_models.get(model.model_version)
    check("scenario.modelCompatible", binding is not None, "MODEL_NOT_COMPATIBLE", "The scenario is not configured for the requested model version.")
    assert binding is not None

    model_path = model_path_for(model, models_dir)
    check("model.exists", model_path.is_file(), "MODEL_NOT_FOUND", "The approved model file is not available.")
    model_sha = sha256_file(model_path)
    check(
        "model.checksum",
        model_sha == model.sha256,
        "MODEL_VALIDATION_FAILED",
        "The model file does not match the approved checksum; it may have been modified.",
    )

    try:
        inp = read_inp(model_path)
    except (InpFormatError, UnicodeDecodeError) as exc:
        raise ValidationFailure("MODEL_VALIDATION_FAILED", "The model input file could not be read.", str(exc)) from exc

    counts = {
        "subcatchments": len(inp.subcatchments),
        "nodes": len(inp.node_ids),
        "links": len(inp.link_ids),
        "rainGages": len(inp.rain_gages),
    }
    check(
        "model.elementCounts",
        counts == model.expected_elements,
        "MODEL_VALIDATION_FAILED",
        "The model element counts do not match the registered model definition.",
        {"expected": model.expected_elements, "actual": counts},
    )
    check("model.routing", inp.options.get("FLOW_ROUTING") == model.routing, "MODEL_VALIDATION_FAILED", "Model routing method differs from registry.")
    check("model.flowUnits", inp.options.get("FLOW_UNITS") == model.flow_units, "MODEL_VALIDATION_FAILED", "Model flow units differ from registry.")

    gage = inp.rain_gages.get(binding["rainGage"])
    check(
        "model.rainGage",
        gage is not None and gage["sourceType"].upper() == "TIMESERIES" and gage["source"] == binding["timeseriesName"],
        "MODEL_VALIDATION_FAILED",
        "The model rain gage is not bound to the scenario rainfall time series.",
    )
    check(
        "model.subcatchmentsUseGage",
        all(sc["rainGage"] == binding["rainGage"] for sc in inp.subcatchments.values()),
        "MODEL_VALIDATION_FAILED",
        "Not all subcatchments use the scenario rain gage.",
    )

    rainfall_path = rainfall_path_for(scenario, raw_dir)
    check("rainfall.exists", rainfall_path.is_file(), "RAINFALL_NOT_FOUND", "The scenario rainfall source file is not available.")
    rainfall_sha = sha256_file(rainfall_path)
    check("rainfall.checksum", rainfall_sha == scenario.rainfall["sha256"], "RAINFALL_VALIDATION_FAILED", "The rainfall source file does not match its registered checksum.")
    try:
        rainfall = load_rainfall(scenario, raw_dir)
    except RainfallFormatError as exc:
        raise ValidationFailure("RAINFALL_VALIDATION_FAILED", "The scenario rainfall file could not be parsed.", str(exc)) from exc

    series = inp.timeseries.get(binding["timeseriesName"], [])
    check(
        "rainfall.modelSeriesLength",
        len(series) == len(rainfall.times),
        "RAINFALL_VALIDATION_FAILED",
        "The model rainfall series length differs from the scenario source data.",
        {"model": len(series), "source": len(rainfall.times)},
    )
    mismatches = [
        rec.time.isoformat()
        for rec, t, v in zip(series, rainfall.times, rainfall.intensities_mm_hr, strict=True)
        if rec.time != t or abs(rec.value - v) > RAINFALL_MATCH_TOLERANCE_MM_HR
    ]
    check(
        "rainfall.modelSeriesMatchesSource",
        not mismatches,
        "RAINFALL_VALIDATION_FAILED",
        "The model rainfall series does not match the scenario source data.",
        {"mismatchedTimes": mismatches[:10]},
    )
    check(
        "model.simulationPeriodCoversRainfall",
        inp.simulation_start() <= rainfall.start_time and inp.simulation_end() >= rainfall.end_time,
        "MODEL_VALIDATION_FAILED",
        "The model simulation period does not cover the scenario rainfall period.",
    )

    return ValidatedInputs(model_path, model_sha, inp, rainfall_path, rainfall_sha, rainfall, checks)
