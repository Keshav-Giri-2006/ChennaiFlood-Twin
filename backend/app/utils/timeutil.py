from __future__ import annotations

from datetime import UTC, datetime, timedelta


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_iso_z(value: datetime | None) -> str | None:
    """ISO 8601 with a trailing Z. Naive datetimes are treated as UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    value = value.astimezone(UTC)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


_OLE_EPOCH = datetime(1899, 12, 30, tzinfo=UTC)


def from_swmm_datetime(days: float) -> datetime:
    """SWMM stores dates as fractional days since 1899-12-30 (the time basis of the model input).

    Rounded to the nearest second to remove float drift.
    """
    seconds = round(days * 86400.0)
    return _OLE_EPOCH + timedelta(seconds=seconds)
