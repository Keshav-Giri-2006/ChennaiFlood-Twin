"""CRS handling for web delivery.

Source layers arrive either in EPSG:32644 (UTM 44N, metres) or OGC CRS84
(lon/lat). Web GeoJSON is always RFC 7946 lon/lat (CRS84 / EPSG:4326 axis order
lon,lat). Transformations are explicit; unknown CRS declarations are rejected.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pyproj import Transformer

CRS84 = "OGC:CRS84"
UTM44N = "EPSG:32644"

_CRS_ALIASES = {
    "urn:ogc:def:crs:EPSG::32644": UTM44N,
    "EPSG:32644": UTM44N,
    "urn:ogc:def:crs:OGC:1.3:CRS84": CRS84,
}

# Web coordinate precision: 7 decimal degrees is ~1.1 cm; this is a
# serialisation precision, not geometric simplification.
WEB_COORD_DECIMALS = 7

# Plausibility envelope for Ward 176, Chennai (lon/lat), used to catch CRS errors.
CHENNAI_ENVELOPE = (80.0, 12.8, 80.5, 13.3)


class CrsError(ValueError):
    pass


def declared_crs(collection: dict[str, Any]) -> str:
    name = (collection.get("crs") or {}).get("properties", {}).get("name")
    if not name:
        raise CrsError("Source GeoJSON does not declare a CRS")
    try:
        return _CRS_ALIASES[name]
    except KeyError as exc:
        raise CrsError(f"Unsupported source CRS: {name}") from exc


@lru_cache(maxsize=4)
def _transformer(source: str) -> Transformer:
    return Transformer.from_crs(source, "EPSG:4326", always_xy=True)


def transform_xy(source: str, xs: list[float], ys: list[float]) -> tuple[list[float], list[float]]:
    if source == CRS84:
        return xs, ys
    lons, lats = _transformer(source).transform(xs, ys)
    return list(lons), list(lats)


def _flatten(coords: Any, out: list[list[float]]) -> None:
    if coords and isinstance(coords[0], (int, float)):
        out.append(coords)
    else:
        for c in coords:
            _flatten(c, out)


def _rebuild(coords: Any, it: Any) -> Any:
    if coords and isinstance(coords[0], (int, float)):
        return next(it)
    return [_rebuild(c, it) for c in coords]


def geometry_to_web(geometry: dict[str, Any], source: str) -> dict[str, Any]:
    """Transform a GeoJSON geometry to lon/lat, dropping Z/M and rounding."""
    positions: list[list[float]] = []
    _flatten(geometry["coordinates"], positions)
    lons, lats = transform_xy(source, [p[0] for p in positions], [p[1] for p in positions])
    rounded = iter([[round(x, WEB_COORD_DECIMALS), round(y, WEB_COORD_DECIMALS)] for x, y in zip(lons, lats, strict=True)])
    return {"type": geometry["type"], "coordinates": _rebuild(geometry["coordinates"], rounded)}


def bbox_of(features: list[dict[str, Any]]) -> list[float]:
    xs: list[float] = []
    ys: list[float] = []
    for f in features:
        positions: list[list[float]] = []
        _flatten(f["geometry"]["coordinates"], positions)
        xs.extend(p[0] for p in positions)
        ys.extend(p[1] for p in positions)
    return [min(xs), min(ys), max(xs), max(ys)]


def within_envelope(bbox: list[float], envelope: tuple[float, float, float, float] = CHENNAI_ENVELOPE) -> bool:
    return envelope[0] <= bbox[0] and envelope[1] <= bbox[1] and bbox[2] <= envelope[2] and bbox[3] <= envelope[3]
