"""Controlled SWMM subprocess runner.

The runner only executes SWMM and collects execution facts. The executable
comes exclusively from server configuration; the command is a fixed argument
list (no shell), and all file arguments must live inside the simulation
workspace.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from app.utils.files import is_within


class SwmmUnavailableError(RuntimeError):
    pass


class SwmmExecutionError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int | None = None, timed_out: bool = False) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.timed_out = timed_out


@dataclass(frozen=True)
class SwmmRunResult:
    exit_code: int
    elapsed_seconds: float
    report_file: Path
    output_file: Path
    stdout_file: Path
    stderr_file: Path


def resolve_swmm_executable(configured: str | None) -> Path:
    """Resolve the configured SWMM executable, or find ``runswmm`` on PATH."""
    candidate: str | None
    if configured:
        candidate = configured
    else:
        candidate = shutil.which("runswmm") or shutil.which("swmm5")
    if not candidate:
        raise SwmmUnavailableError("SWMM executable is not configured and was not found on PATH.")
    path = Path(candidate)
    if not path.is_file():
        raise SwmmUnavailableError("Configured SWMM executable does not exist.")
    return path


class SwmmRunner:
    def __init__(self, executable: Path, timeout_seconds: int) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def run(self, workspace: Path, input_name: str = "input.inp") -> SwmmRunResult:
        workspace = workspace.resolve()
        input_file = workspace / input_name
        report_file = workspace / "report.rpt"
        output_file = workspace / "output.out"
        stdout_file = workspace / "stdout.log"
        stderr_file = workspace / "stderr.log"

        for f in (input_file, report_file, output_file):
            if not is_within(f, workspace):
                raise SwmmExecutionError("Simulation file path escapes the workspace.")
        if not input_file.is_file():
            raise SwmmExecutionError("SWMM input file is missing from the workspace.")
        if not self.executable.is_file():
            raise SwmmUnavailableError("SWMM executable is not available.")

        # Relative names + cwd=workspace keep paths out of SWMM's report text.
        command = [str(self.executable), input_file.name, report_file.name, output_file.name]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

        started = time.monotonic()
        with stdout_file.open("wb") as out, stderr_file.open("wb") as err:
            try:
                completed = subprocess.run(
                    command,
                    cwd=workspace,
                    stdout=out,
                    stderr=err,
                    stdin=subprocess.DEVNULL,
                    timeout=self.timeout_seconds,
                    shell=False,
                    check=False,
                    creationflags=creationflags,
                )
            except subprocess.TimeoutExpired as exc:
                raise SwmmExecutionError(
                    f"SWMM did not finish within {self.timeout_seconds} seconds.", timed_out=True
                ) from exc
            except OSError as exc:
                raise SwmmUnavailableError("SWMM executable could not be started.") from exc
        elapsed = time.monotonic() - started

        if completed.returncode != 0:
            raise SwmmExecutionError(f"SWMM exited with code {completed.returncode}.", exit_code=completed.returncode)
        if not report_file.is_file() or report_file.stat().st_size == 0:
            raise SwmmExecutionError("SWMM finished but produced no report file.", exit_code=completed.returncode)
        if not output_file.is_file() or output_file.stat().st_size == 0:
            raise SwmmExecutionError("SWMM finished but produced no binary output file.", exit_code=completed.returncode)

        return SwmmRunResult(
            exit_code=completed.returncode,
            elapsed_seconds=round(elapsed, 3),
            report_file=report_file,
            output_file=output_file,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
        )
