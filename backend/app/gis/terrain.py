"""Web terrain grid from the processed Ward 176 Copernicus DEM (read-only).

The clipped DEM uses 0.0 as its outside-ward mask (docs/03_DATA_AND_GIS.md
§24); masked cells are returned as ``null`` and are never replaced with an
elevation. Heights are the DEM values as delivered (Copernicus GLO-30 heights
relative to EGM2008); no geoid/ellipsoid conversion or smoothing is applied.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import rasterio

MASK_VALUE = 0.0


class TerrainError(ValueError):
    pass


def build_terrain_grid(dem_path: Path) -> dict[str, Any]:
    with rasterio.open(dem_path) as dataset:
        if dataset.crs is None or dataset.crs.to_epsg() != 4326:
            raise TerrainError(f"Expected an EPSG:4326 DEM, found {dataset.crs}")
        band = dataset.read(1)
        transform = dataset.transform
        if transform.b != 0 or transform.d != 0:
            raise TerrainError("Rotated DEM grids are not supported")
        registration = dataset.tags().get("AREA_OR_POINT", "Area")
        width, height = dataset.width, dataset.height

    # GDAL geotransforms are corner-based for both registrations; cell (r, c)
    # represents the sample at its centre.
    dx, dy = transform.a, transform.e  # dy < 0 (north-up)
    heights: list[float | None] = []
    valid = []
    for r in range(height):
        for c in range(width):
            v = float(band[r, c])
            if v == MASK_VALUE:
                heights.append(None)
            else:
                heights.append(round(v, 3))
                valid.append(v)
    if not valid:
        raise TerrainError("DEM contains no valid cells")
    return {
        "source": "Copernicus DEM GLO-30 (DSM), clipped to Ward 176",
        "dataType": "source",
        "crs": "EPSG:4326",
        "width": width,
        "height": height,
        "rowOrder": "north-to-south",
        "firstCellCenter": {"lon": transform.c + dx / 2, "lat": transform.f + dy / 2},
        "cellSizeDeg": {"lon": dx, "lat": -dy},
        "bounds": {"west": transform.c, "east": transform.c + dx * width, "north": transform.f, "south": transform.f + dy * height},
        "registration": registration,
        "heightUnit": "m",
        "verticalReference": "Copernicus DEM heights (EGM2008) as delivered; not converted to ellipsoidal height.",
        "maskedValue": None,
        "maskNote": "null = outside the Ward 176 DEM mask (no elevation data); not an elevation of zero.",
        "statistics": {"validCells": len(valid), "maskedCells": width * height - len(valid), "min": round(min(valid), 3), "max": round(max(valid), 3), "mean": round(sum(valid) / len(valid), 3)},
        "limitations": [
            "Copernicus GLO-30 is DSM-derived (~30 m) and may include buildings and vegetation; it is not a bare-earth survey.",
        ],
        "heights": heights,
    }
