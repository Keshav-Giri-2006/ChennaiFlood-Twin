from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from app.core.errors import AppError, ErrorCode, NotFoundError
from app.gis.transform import CrsError
from app.gis.web_assets import LAYERS, GisBuildError, WebAssetBuilder
from app.gis.terrain import TerrainError, build_terrain_grid
from app.utils.files import read_json, sha256_file


class GisService:
    def __init__(self, builder: WebAssetBuilder, dem_path: Path) -> None:
        self.builder = builder
        self.dem_path = dem_path
        self._terrain: tuple[dict[str, Any], str] | None = None
        self._drain_index: dict[int, dict[str, Any]] | None = None
        self._lock = threading.Lock()

    def layer(self, name: str) -> tuple[Path, dict[str, Any]]:
        if name not in LAYERS:
            raise NotFoundError(ErrorCode.NOT_FOUND, "The requested GIS layer does not exist.")
        try:
            return self.builder.get(name)
        except (GisBuildError, CrsError, OSError, ValueError) as exc:
            raise AppError(ErrorCode.GEOSPATIAL_ERROR, f"The '{name}' layer is currently unavailable.", status_code=503, details={"reason": str(exc)}) from exc

    def drain(self, object_id: int) -> dict[str, Any]:
        with self._lock:
            if self._drain_index is None:
                path, manifest = self.layer("drains")
                collection = read_json(path)
                self._drain_index = {f["id"]: {**f["properties"], "geometry": f["geometry"]} for f in collection["features"]}
                self._drain_meta = manifest["metadata"]
        drain = self._drain_index.get(object_id)
        if drain is None:
            raise NotFoundError(ErrorCode.NOT_FOUND, "The requested drain does not exist in the Ward 176 source dataset.", details={"objectId": object_id})
        return {**drain, "dataType": "source", "crs": self._drain_meta["crs"], "identifierNote": self._drain_meta["identifierNote"]}

    def terrain(self) -> tuple[dict[str, Any], str]:
        with self._lock:
            if self._terrain is None:
                if not self.dem_path.is_file():
                    raise AppError(ErrorCode.GEOSPATIAL_ERROR, "The terrain (DEM) layer is currently unavailable.", status_code=503)
                try:
                    grid = build_terrain_grid(self.dem_path)
                except (TerrainError, OSError) as exc:
                    raise AppError(ErrorCode.GEOSPATIAL_ERROR, "The terrain (DEM) layer is currently unavailable.", status_code=503, details={"reason": str(exc)}) from exc
                grid["provenance"] = {"file": self.dem_path.name, "sha256": sha256_file(self.dem_path)}
                self._terrain = (grid, grid["provenance"]["sha256"])
            return self._terrain

    def catalogue(self) -> list[dict[str, Any]]:
        return [
            {"layer": spec.name, "title": spec.title, "dataType": spec.data_type, "description": spec.description, "url": f"/api/v1/gis/{spec.name.replace('model-', 'model/')}"}
            for spec in LAYERS.values()
        ]
