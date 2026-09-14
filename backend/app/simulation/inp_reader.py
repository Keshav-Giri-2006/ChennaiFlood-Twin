"""Read-only structural reader for SWMM ``.inp`` files.

Only what the backend needs for validation and ID mapping is extracted. This
module never writes or modifies a model file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


class InpFormatError(ValueError):
    pass


@dataclass
class TimeseriesRecord:
    time: datetime
    value: float


@dataclass
class InpModel:
    options: dict[str, str] = field(default_factory=dict)
    rain_gages: dict[str, dict[str, str]] = field(default_factory=dict)
    subcatchments: dict[str, dict[str, str]] = field(default_factory=dict)
    junctions: dict[str, dict[str, float]] = field(default_factory=dict)
    outfalls: dict[str, dict[str, float | str]] = field(default_factory=dict)
    conduits: dict[str, dict[str, str | float]] = field(default_factory=dict)
    xsections: dict[str, dict[str, str | float]] = field(default_factory=dict)
    timeseries: dict[str, list[TimeseriesRecord]] = field(default_factory=dict)
    sections: list[str] = field(default_factory=list)

    @property
    def node_ids(self) -> list[str]:
        return list(self.junctions) + list(self.outfalls)

    @property
    def link_ids(self) -> list[str]:
        return list(self.conduits)

    def simulation_start(self) -> datetime:
        return _parse_swmm_datetime(self.options["START_DATE"], self.options.get("START_TIME", "00:00"))

    def simulation_end(self) -> datetime:
        return _parse_swmm_datetime(self.options["END_DATE"], self.options.get("END_TIME", "00:00"))


def _parse_swmm_datetime(date_text: str, time_text: str) -> datetime:
    parts = time_text.split(":")
    while len(parts) < 3:
        parts.append("0")
    try:
        month, day, year = (int(p) for p in date_text.split("/"))
        hour, minute, second = (int(p) for p in parts[:3])
        return datetime(year, month, day, hour, minute, second, tzinfo=UTC)
    except (ValueError, TypeError) as exc:
        raise InpFormatError(f"Unparseable SWMM date/time: {date_text} {time_text}") from exc


def _num(value: str, context: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise InpFormatError(f"Non-numeric value '{value}' in {context}") from exc


def read_inp(path: Path) -> InpModel:
    model = InpModel()
    section: str | None = None
    last_ts_date: dict[str, str] = {}
    with path.open("r", encoding="utf-8", errors="strict") as handle:
        for raw_line in handle:
            line = raw_line.split(";", 1)[0].strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].upper()
                model.sections.append(section)
                continue
            tokens = line.split()
            if section == "OPTIONS" and len(tokens) >= 2:
                model.options[tokens[0].upper()] = tokens[1]
            elif section == "RAINGAGES" and len(tokens) >= 6:
                model.rain_gages[tokens[0]] = {
                    "format": tokens[1],
                    "interval": tokens[2],
                    "scf": tokens[3],
                    "sourceType": tokens[4],
                    "source": tokens[5],
                }
            elif section == "SUBCATCHMENTS" and len(tokens) >= 8:
                model.subcatchments[tokens[0]] = {"rainGage": tokens[1], "outlet": tokens[2], "areaHa": tokens[3]}
            elif section == "JUNCTIONS" and len(tokens) >= 3:
                model.junctions[tokens[0]] = {
                    "invertElevM": _num(tokens[1], f"JUNCTIONS {tokens[0]}"),
                    "maxDepthM": _num(tokens[2], f"JUNCTIONS {tokens[0]}"),
                }
            elif section == "OUTFALLS" and len(tokens) >= 3:
                model.outfalls[tokens[0]] = {
                    "invertElevM": _num(tokens[1], f"OUTFALLS {tokens[0]}"),
                    "type": tokens[2],
                }
            elif section == "CONDUITS" and len(tokens) >= 5:
                model.conduits[tokens[0]] = {
                    "fromNode": tokens[1],
                    "toNode": tokens[2],
                    "lengthM": _num(tokens[3], f"CONDUITS {tokens[0]}"),
                    "roughness": _num(tokens[4], f"CONDUITS {tokens[0]}"),
                    "inOffsetM": _num(tokens[5], f"CONDUITS {tokens[0]}") if len(tokens) > 5 else 0.0,
                    "outOffsetM": _num(tokens[6], f"CONDUITS {tokens[0]}") if len(tokens) > 6 else 0.0,
                }
            elif section == "XSECTIONS" and len(tokens) >= 3:
                model.xsections[tokens[0]] = {"shape": tokens[1], "fullDepthM": _num(tokens[2], f"XSECTIONS {tokens[0]}")}
            elif section == "TIMESERIES":
                name = tokens[0]
                # Either "name date time value" or "name time value" (continuation of date).
                if len(tokens) == 4:
                    date_text, time_text, value_text = tokens[1], tokens[2], tokens[3]
                    last_ts_date[name] = date_text
                elif len(tokens) == 3 and name in last_ts_date:
                    date_text, time_text, value_text = last_ts_date[name], tokens[1], tokens[2]
                else:
                    raise InpFormatError(f"Unsupported TIMESERIES row format for series '{name}'")
                model.timeseries.setdefault(name, []).append(
                    TimeseriesRecord(_parse_swmm_datetime(date_text, time_text), _num(value_text, f"TIMESERIES {name}"))
                )
    if not model.sections:
        raise InpFormatError("File contains no SWMM sections")
    return model
