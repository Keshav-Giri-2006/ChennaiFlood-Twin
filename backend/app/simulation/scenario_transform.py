"""scenario-analysis-v1: rainfall-multiplier what-if transformation of an isolated model copy.

The approved master model is never modified. For multiplier M the rainfall
TIMESERIES bound to the scenario rain gage is rewritten in the *workspace copy*:

    intensity_new(t) = round(intensity_baseline(t) * M, 6)     [mm/hr, 6 decimals as in the master]

Timestamps, interval, duration and every other line of the model stay byte-identical.
For M = 1.00 the transformed file is therefore byte-identical to the master model
(verified by checksum). Full documentation: docs/SCENARIO_ANALYSIS_METHOD.md.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

VALUE_DECIMALS = 6
_SECTION = re.compile(r"^\s*\[(?P<name>[^\]]+)\]\s*$")
# name, date, time, value (+ optional trailing whitespace); the value span is replaced in place.
_SERIES_LINE = re.compile(r"^(?P<prefix>\s*(?P<name>\S+)\s+(?P<date>\S+)\s+(?P<time>\S+)\s+)(?P<value>\S+)(?P<suffix>\s*)$")


class ScenarioParameterError(ValueError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.details = details


class ScenarioTransformError(ValueError):
    pass


@dataclass(frozen=True)
class RainfallTransform:
    text: str
    multiplier: float
    records: int
    baseline_total_mm: float
    transformed_total_mm: float
    baseline_peak_mm_hr: float
    transformed_peak_mm_hr: float


def validate_multiplier(value: Any, spec: dict[str, Any]) -> float:
    """Validate a client-supplied rainfall multiplier against the scenario's documented range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScenarioParameterError("rainfallMultiplier must be a number.", {"value": repr(value)})
    number = float(value)
    if not math.isfinite(number):
        raise ScenarioParameterError("rainfallMultiplier must be a finite number.", {"value": repr(value)})
    minimum, maximum = float(spec["minimum"]), float(spec["maximum"])
    if number <= 0 or number < minimum or number > maximum:
        raise ScenarioParameterError(
            f"rainfallMultiplier must be between {minimum:g} and {maximum:g}.",
            {"value": number, "minimum": minimum, "maximum": maximum},
        )
    decimals = int(spec.get("decimals", 2))
    if round(number, decimals) != number:
        raise ScenarioParameterError(f"rainfallMultiplier may have at most {decimals} decimal places.", {"value": number})
    return number


def _format(value: Decimal) -> str:
    return f"{value.quantize(Decimal(1).scaleb(-VALUE_DECIMALS), rounding=ROUND_HALF_EVEN):.{VALUE_DECIMALS}f}"


def scaled_value(baseline_text: str, multiplier: float) -> str:
    """Decimal arithmetic avoids binary float artefacts, so M = 1 reproduces the text exactly."""
    return _format(Decimal(baseline_text) * Decimal(repr(multiplier)))


def apply_rainfall_multiplier(master_text: str, series_name: str, multiplier: float, interval_hours: float) -> RainfallTransform:
    lines = master_text.splitlines(keepends=True)
    section = None
    out: list[str] = []
    base_values: list[float] = []
    new_values: list[float] = []
    for raw in lines:
        body = raw.rstrip("\r\n")
        ending = raw[len(body):]
        m = _SECTION.match(body)
        if m:
            section = m.group("name").strip().upper()
            out.append(raw)
            continue
        if section == "TIMESERIES" and body.strip() and not body.lstrip().startswith(";"):
            s = _SERIES_LINE.match(body)
            if s and s.group("name") == series_name:
                try:
                    base = Decimal(s.group("value"))
                except ArithmeticError as exc:
                    raise ScenarioTransformError(f"Non-numeric rainfall value in line: {body!r}") from exc
                if base < 0:
                    raise ScenarioTransformError(f"Negative rainfall value in line: {body!r}")
                new_text = scaled_value(s.group("value"), multiplier)
                base_values.append(float(base))
                new_values.append(float(new_text))
                out.append(f"{s.group('prefix')}{new_text}{s.group('suffix')}{ending}")
                continue
        out.append(raw)
    if not base_values:
        raise ScenarioTransformError(f"Rainfall time series '{series_name}' not found in the model")
    return RainfallTransform(
        text="".join(out),
        multiplier=multiplier,
        records=len(base_values),
        baseline_total_mm=sum(base_values) * interval_hours,
        transformed_total_mm=sum(new_values) * interval_hours,
        baseline_peak_mm_hr=max(base_values),
        transformed_peak_mm_hr=max(new_values),
    )


def verify_transform(master_text: str, transformed_text: str, series_name: str, multiplier: float) -> dict[str, Any]:
    """Independent check: only the series' value tokens differ, timestamps are identical, values = round(base*M, 6)."""
    a, b = master_text.splitlines(), transformed_text.splitlines()
    if len(a) != len(b):
        raise ScenarioTransformError("Transformed model has a different number of lines than the master model")
    changed = 0
    max_abs_error = 0.0
    section = None
    for la, lb in zip(a, b, strict=True):
        m = _SECTION.match(la)
        if m:
            section = m.group("name").strip().upper()
        if la == lb:
            if section == "TIMESERIES":
                s = _SERIES_LINE.match(la)
                if s and s.group("name") == series_name and scaled_value(s.group("value"), multiplier) != s.group("value"):
                    raise ScenarioTransformError(f"Rainfall value was not transformed: {la!r}")
            continue
        sa, sb = _SERIES_LINE.match(la), _SERIES_LINE.match(lb)
        if section != "TIMESERIES" or not sa or not sb or sa.group("name") != series_name:
            raise ScenarioTransformError(f"Unexpected change outside the rainfall series: {la!r} -> {lb!r}")
        if (sa.group("name"), sa.group("date"), sa.group("time")) != (sb.group("name"), sb.group("date"), sb.group("time")):
            raise ScenarioTransformError(f"Rainfall timestamp changed: {la!r} -> {lb!r}")
        expected = float(sa.group("value")) * multiplier
        error = abs(float(sb.group("value")) - expected)
        if error > 0.5 * 10 ** -VALUE_DECIMALS + 1e-12:
            raise ScenarioTransformError(f"Rainfall value differs from baseline x multiplier: {la!r} -> {lb!r}")
        max_abs_error = max(max_abs_error, error)
        changed += 1
    return {"changedLines": changed, "maxAbsRoundingErrorMmHr": max_abs_error, "otherLinesIdentical": True}
