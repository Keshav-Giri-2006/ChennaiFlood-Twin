from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.container import Container
from app.main import create_app
from app.simulation.runner import SwmmExecutionError, SwmmRunResult, SwmmUnavailableError, resolve_swmm_executable

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "simulation"
MODEL_INP = MODEL_DIR / "ward176_hydraulic_reconstructed_candidate.inp"
# Archived outputs of a previous SWMM 5.2.4 run of the same approved model.
ARCHIVED_RPT = MODEL_DIR / "ward176_hydraulic_reconstructed_candidate.rpt"
ARCHIVED_OUT = MODEL_DIR / "ward176_hydraulic_reconstructed_candidate.out"
RAINFALL_CSV = REPO_ROOT / "data_raw" / "rainfall" / "michaung_2023" / "imerg_michaung_2023_raw.csv"


def swmm_available() -> bool:
    try:
        resolve_swmm_executable(Settings().swmm_executable)
        return True
    except SwmmUnavailableError:
        return False


@pytest.fixture(scope="session")
def shared_web_assets(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # Building web GIS layers takes a few seconds; share them across tests.
    return tmp_path_factory.mktemp("web_assets")


@pytest.fixture
def make_settings(tmp_path: Path, shared_web_assets: Path) -> Callable[..., Settings]:
    def _make(**overrides: object) -> Settings:
        values: dict[str, object] = {
            "RUNTIME_DIR": tmp_path / "runtime",
            "WEB_ASSETS_DIR": shared_web_assets,
            "DATA_DIR": REPO_ROOT,
        }
        values.update(overrides)
        return Settings(**values)  # type: ignore[arg-type]

    return _make


class ManualExecutor:
    """Test executor: queues jobs so tests can observe CREATED before running them."""

    def __init__(self) -> None:
        self.jobs: list[tuple[Callable[[str], None], str]] = []

    def submit(self, fn: Callable[[str], None], simulation_id: str) -> None:
        self.jobs.append((fn, simulation_id))

    def run_all(self) -> None:
        while self.jobs:
            fn, sid = self.jobs.pop(0)
            fn(sid)

    def shutdown(self) -> None:
        self.jobs.clear()


class ReplayRunner:
    """TEST DOUBLE - does not run SWMM.

    Copies archived SWMM 5.2.4 report/output files of the same approved model
    into the workspace so the API lifecycle and result processing can be tested
    quickly. The real SWMM path is covered by tests/integration.
    """

    def run(self, workspace: Path, input_name: str = "input.inp") -> SwmmRunResult:
        shutil.copyfile(ARCHIVED_RPT, workspace / "report.rpt")
        shutil.copyfile(ARCHIVED_OUT, workspace / "output.out")
        (workspace / "stdout.log").write_text("replayed archived artifacts (test double)\n", encoding="utf-8")
        (workspace / "stderr.log").write_text("", encoding="utf-8")
        return SwmmRunResult(0, 0.0, workspace / "report.rpt", workspace / "output.out", workspace / "stdout.log", workspace / "stderr.log")


class FailingRunner:
    def run(self, workspace: Path, input_name: str = "input.inp") -> SwmmRunResult:
        (workspace / "stdout.log").write_text("", encoding="utf-8")
        raise SwmmExecutionError("SWMM exited with code 200.", exit_code=200)


@pytest.fixture
def build_client(make_settings: Callable[..., Settings]) -> Iterator[Callable[..., tuple[TestClient, Container, ManualExecutor]]]:
    clients: list[TestClient] = []

    def _build(runner: object | None = None, settings: Settings | None = None, runner_factory: object | None = None) -> tuple[TestClient, Container, ManualExecutor]:
        settings = settings or make_settings()
        executor = ManualExecutor()
        factory = runner_factory or (lambda _s: runner or ReplayRunner())
        container = Container.build(settings, executor=executor, runner_factory=factory)  # type: ignore[arg-type]
        client = TestClient(create_app(settings, container))
        client.__enter__()
        clients.append(client)
        return client, container, executor

    yield _build
    for client in clients:
        client.__exit__(None, None, None)
