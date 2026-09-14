"""Liveness and readiness checks. Readiness never runs a simulation."""

from __future__ import annotations

import os
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.core.config import APP_VERSION, SERVICE_NAME, Settings
from app.gis.web_assets import LAYERS, WebAssetBuilder
from app.repositories.registry import Registry
from app.simulation.runner import SwmmUnavailableError, resolve_swmm_executable
from app.simulation.validator import model_path_for, rainfall_path_for
from app.utils.files import sha256_file


class HealthService:
    def __init__(self, settings: Settings, registry: Registry, engine: Engine, gis_builder: WebAssetBuilder) -> None:
        self.settings = settings
        self.registry = registry
        self.engine = engine
        self.gis_builder = gis_builder
        self._model_checksum_ok: bool | None = None

    def liveness(self) -> dict[str, Any]:
        return {"status": "ok", "service": SERVICE_NAME, "version": APP_VERSION}

    def readiness(self) -> dict[str, Any]:
        checks: dict[str, str] = {}
        details: dict[str, str] = {}

        try:
            exe = resolve_swmm_executable(self.settings.swmm_executable)
            # os.access(X_OK) is only meaningful on POSIX; Windows grants it to any file.
            checks["swmm"] = "ok" if os.name == "nt" or os.access(exe, os.X_OK) else "error"
            if checks["swmm"] != "ok":
                details["swmm"] = "SWMM executable is not executable."
        except SwmmUnavailableError as exc:
            checks["swmm"] = "error"
            details["swmm"] = str(exc)

        model = self.registry.models.get(self.settings.model_version)
        if model is None:
            checks["model"] = "error"
            details["model"] = "Configured MODEL_VERSION is not registered."
        else:
            path = model_path_for(model, self.settings.models_dir)
            if not path.is_file():
                checks["model"] = "error"
                details["model"] = "Approved model file is missing."
            else:
                if self._model_checksum_ok is None:
                    self._model_checksum_ok = sha256_file(path) == model.sha256
                checks["model"] = "ok" if self._model_checksum_ok else "error"
                if not self._model_checksum_ok:
                    details["model"] = "Model file does not match the approved checksum."

        missing_rain = [s.scenario_id for s in self.registry.scenarios.values() if not rainfall_path_for(s, self.settings.raw_dir).is_file()]
        checks["rainfall"] = "ok" if not missing_rain else "error"
        if missing_rain:
            details["rainfall"] = f"Rainfall data missing for scenarios: {missing_rain}"

        missing_gis = sorted({p.name for layer in LAYERS for p in self.gis_builder.source_paths(layer) if not p.is_file()})
        checks["data"] = "ok" if not missing_gis else "error"
        if missing_gis:
            details["data"] = f"Missing GIS/network source files: {missing_gis}"

        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            for directory in (self.settings.workdir, self.settings.results_root, self.settings.web_assets_root):
                directory.mkdir(parents=True, exist_ok=True)
                probe = directory / f".ready-{uuid.uuid4().hex}"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink()
            checks["storage"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["storage"] = "error"
            details["storage"] = f"Storage check failed: {type(exc).__name__}"

        ready = all(v == "ok" for v in checks.values())
        body: dict[str, Any] = {"status": "ready" if ready else "not_ready", "checks": checks}
        if details:
            body["details"] = details
        return body
