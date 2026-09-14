"""Reader for the NASA Giovanni IMERG area-averaged CSV export.

The file has a metadata preamble ("Key:,Value" rows), a blank line, then a
``time, <variable>`` table. Values are precipitation rates in mm/hr, one per
30-minute interval, timestamped at the interval start in UTC.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path


class RainfallFormatError(ValueError):
    pass


@dataclass
class RainfallSeries:
    times: list[datetime]
    intensities_mm_hr: list[float]
    interval_minutes: int
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def interval_hours(self) -> float:
        return self.interval_minutes / 60.0

    @property
    def total_mm(self) -> float:
        return sum(self.intensities_mm_hr) * self.interval_hours

    @property
    def peak_mm_hr(self) -> float:
        return max(self.intensities_mm_hr)

    @property
    def peak_time(self) -> datetime:
        return self.times[self.intensities_mm_hr.index(self.peak_mm_hr)]

    @property
    def start_time(self) -> datetime:
        return self.times[0]

    @property
    def end_time(self) -> datetime:
        """Timestamp of the last record (start of the final interval)."""
        return self.times[-1]

    @property
    def coverage_end_time(self) -> datetime:
        return self.times[-1] + timedelta(minutes=self.interval_minutes)

    def daily_totals_mm(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for t, v in zip(self.times, self.intensities_mm_hr, strict=True):
            key = t.strftime("%Y-%m-%d")
            totals[key] = totals.get(key, 0.0) + v * self.interval_hours
        return totals


def read_giovanni_csv(path: Path, value_column: str, interval_minutes: int, fill_value: float | None = None) -> RainfallSeries:
    metadata: dict[str, str] = {}
    times: list[datetime] = []
    values: list[float] = []
    in_table = False
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if not row or all(not c.strip() for c in row):
                continue
            first = row[0].strip()
            if not in_table:
                if first.lower() == "time":
                    header = [c.strip() for c in row]
                    if len(header) < 2 or header[1] != value_column:
                        raise RainfallFormatError(f"Expected value column '{value_column}', found {header[1:]}")
                    in_table = True
                    continue
                if first.endswith(":") and len(row) >= 2:
                    metadata[first[:-1].strip()] = row[1].strip()
                continue
            if len(row) < 2:
                raise RainfallFormatError(f"Malformed rainfall row: {row}")
            try:
                t = datetime.strptime(first, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
                v = float(row[1])
            except ValueError as exc:
                raise RainfallFormatError(f"Unparseable rainfall row: {row}") from exc
            times.append(t)
            values.append(v)

    if not times:
        raise RainfallFormatError("No rainfall records found")

    fill_key = next((k for k in metadata if k.lower().startswith("fill value")), None)
    if fill_value is None and fill_key is not None:
        try:
            fill_value = float(metadata[fill_key])
        except ValueError:
            fill_value = None
    if fill_value is not None and any(abs(v - fill_value) < 1e-6 for v in values):
        raise RainfallFormatError("Rainfall series contains fill values (missing data)")
    if any(v < 0 for v in values):
        raise RainfallFormatError("Rainfall series contains negative values")

    step = timedelta(minutes=interval_minutes)
    for a, b in zip(times, times[1:]):
        if b - a != step:
            raise RainfallFormatError(f"Irregular rainfall interval between {a.isoformat()} and {b.isoformat()}")

    return RainfallSeries(times=times, intensities_mm_hr=values, interval_minutes=interval_minutes, metadata=metadata)
