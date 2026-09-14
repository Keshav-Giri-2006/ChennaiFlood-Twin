"""Filesystem-backed stores for simulation workspaces and processed results.

Keys are always ``<simulationId>/<artifact>``, so the same layout maps directly
to S3 object keys later. Simulation IDs are validated UUIDs, which prevents
path traversal.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from app.utils.files import read_json, write_json_atomic


def validate_simulation_id(simulation_id: str) -> str:
    try:
        return str(uuid.UUID(simulation_id))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError("Invalid simulation ID") from exc


class WorkspaceStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path(self, simulation_id: str) -> Path:
        return self.root / validate_simulation_id(simulation_id)

    def create(self, simulation_id: str) -> Path:
        path = self.path(simulation_id)
        path.mkdir(parents=True, exist_ok=False)  # never reuse another run's directory
        return path

    def key(self, simulation_id: str, name: str) -> str:
        return f"{validate_simulation_id(simulation_id)}/{name}"


class ResultStore:
    RESULTS = "results.json"
    TIMESERIES = "hydraulics_timeseries.json"

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _dir(self, simulation_id: str) -> Path:
        return self.root / validate_simulation_id(simulation_id)

    def write(self, simulation_id: str, name: str, payload: Any) -> str:
        write_json_atomic(self._dir(simulation_id) / name, payload)
        return f"{validate_simulation_id(simulation_id)}/{name}"

    def exists(self, simulation_id: str, name: str) -> bool:
        return (self._dir(simulation_id) / name).is_file()

    def read(self, simulation_id: str, name: str) -> Any:
        return read_json(self._dir(simulation_id) / name)
