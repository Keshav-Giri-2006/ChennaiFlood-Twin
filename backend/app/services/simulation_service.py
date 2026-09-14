"""Simulation orchestration: validate -> prepare -> run SWMM -> process -> complete.

Execution happens off the request thread through a ``SimulationExecutor``. The
local implementation is a bounded thread pool (``SIMULATION_MAX_CONCURRENT``,
default 1, so runs are explicitly serialised); an SQS/ECS worker can replace
it later without changing the pipeline.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Protocol

from app.analysis.flood_processing import FloodProcessingError
from app.analysis.result_processing import ResultProcessingError, process_results
from app.core.config import APP_VERSION, Settings
from app.core.errors import ConflictError, ErrorCode, NotFoundError, ServiceUnavailableError, UnprocessableError
from app.core.logging import log_event
from app.models.simulation import (
    STATUS_PROGRESS,
    STATUS_STAGE,
    SimulationRecord,
    SimulationStage,
    SimulationStatus,
)
from app.repositories.registry import ModelDefinition, Registry, ScenarioDefinition
from app.repositories.results import ResultStore, WorkspaceStore, validate_simulation_id
from app.repositories.simulations import SimulationRepository
from app.simulation.output_reader import OutputFormatError, read_output
from app.simulation.report_parser import ReportParseError, parse_report
from app.simulation.runner import SwmmExecutionError, SwmmRunner, SwmmUnavailableError, resolve_swmm_executable
from app.simulation.validator import ValidationFailure, model_path_for, rainfall_path_for, validate_inputs
from app.utils.files import sha256_file, write_json_atomic
from app.utils.timeutil import to_iso_z, utcnow

logger = logging.getLogger("app.simulation")


class SimulationExecutor(Protocol):
    def submit(self, fn: Callable[[str], None], simulation_id: str) -> None: ...
    def shutdown(self) -> None: ...


class LocalThreadExecutor:
    def __init__(self, max_workers: int) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="simulation")

    def submit(self, fn: Callable[[str], None], simulation_id: str) -> None:
        self._pool.submit(fn, simulation_id)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)


class _StageFailure(Exception):
    def __init__(self, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


RunnerFactory = Callable[[Settings], SwmmRunner]


def default_runner_factory(settings: Settings) -> SwmmRunner:
    return SwmmRunner(resolve_swmm_executable(settings.swmm_executable), settings.swmm_timeout_seconds)


class SimulationService:
    def __init__(
        self,
        settings: Settings,
        registry: Registry,
        repository: SimulationRepository,
        workspaces: WorkspaceStore,
        results: ResultStore,
        executor: SimulationExecutor,
        runner_factory: RunnerFactory = default_runner_factory,
        flood_products: Any = None,
    ) -> None:
        self.settings = settings
        self.registry = registry
        self.repository = repository
        self.workspaces = workspaces
        self.results = results
        self.executor = executor
        self.runner_factory = runner_factory
        self.flood_products = flood_products

    # -- queries --------------------------------------------------------------
    def get(self, simulation_id: str) -> SimulationRecord:
        try:
            sid = validate_simulation_id(simulation_id)
        except ValueError:
            sid = None
        record = self.repository.get(sid) if sid else None
        if record is None:
            raise NotFoundError(ErrorCode.SIMULATION_NOT_FOUND, "The requested simulation does not exist.", simulation_id=simulation_id)
        return record

    def list(self, *, scenario_id: str | None, status: SimulationStatus | None, limit: int, offset: int) -> list[SimulationRecord]:
        return self.repository.list(scenario_id=scenario_id, status=status, limit=limit, offset=offset)

    # -- creation -------------------------------------------------------------
    def create(self, scenario_id: str, model_version: str | None, parameters: dict[str, Any] | None) -> SimulationRecord:
        scenario = self.registry.scenarios.get(scenario_id)
        if scenario is None:
            raise NotFoundError(ErrorCode.SCENARIO_NOT_FOUND, "The requested rainfall scenario does not exist.", details={"scenarioId": scenario_id})
        version = model_version or self.settings.model_version
        model = self.registry.models.get(version)
        if model is None or not model.approved:
            raise NotFoundError(ErrorCode.MODEL_NOT_FOUND, "The requested model version does not exist or is not approved.", details={"modelVersion": version})
        if version not in scenario.compatible_models:
            raise UnprocessableError(ErrorCode.MODEL_NOT_COMPATIBLE, "The scenario cannot be run with the requested model version.", details={"scenarioId": scenario_id, "modelVersion": version})
        if parameters:
            raise UnprocessableError(
                ErrorCode.UNSUPPORTED_PARAMETER,
                "Scenario parameters are not supported yet; the historical scenario runs unmodified.",
                details={"parameters": sorted(parameters)},
            )
        if not model_path_for(model, self.settings.models_dir).is_file():
            raise ServiceUnavailableError(ErrorCode.MODEL_NOT_FOUND, "The approved model file is not available on the server.")
        if not rainfall_path_for(scenario, self.settings.raw_dir).is_file():
            raise ServiceUnavailableError(ErrorCode.RAINFALL_NOT_FOUND, "The scenario rainfall data is not available on the server.")

        now = utcnow()
        record = SimulationRecord(
            simulation_id=str(uuid.uuid4()),
            scenario_id=scenario_id,
            model_version=version,
            processing_version=self.settings.processing_version,
            application_version=APP_VERSION,
            status=SimulationStatus.CREATED,
            stage=SimulationStage.QUEUED,
            progress=STATUS_PROGRESS[SimulationStatus.CREATED],
            parameters={},
            created_at=now,
            updated_at=now,
        )
        self.repository.add(record)
        log_event(logger, "simulation.created", simulation_id=record.simulation_id, scenario_id=scenario_id, model_version=version)
        self.executor.submit(self.execute, record.simulation_id)
        return record

    # -- startup recovery -------------------------------------------------------
    def recover_interrupted(self) -> list[str]:
        """Mark runs left active by a previous process as FAILED (never as completed)."""
        recovered = []
        for sid in self.repository.active_ids():
            record = self.repository.get(sid)
            if record is None:
                continue
            self.repository.transition(
                sid,
                SimulationStatus.FAILED,
                stage=record.stage,
                progress=record.progress,
                completed_at=utcnow(),
                error_code=ErrorCode.SIMULATION_INTERRUPTED,
                error_message="The simulation was interrupted because the backend restarted before it finished.",
            )
            log_event(logger, "simulation.failed", simulation_id=sid, code=ErrorCode.SIMULATION_INTERRUPTED)
            recovered.append(sid)
        return recovered

    # -- pipeline ---------------------------------------------------------------
    def _advance(self, sid: str, status: SimulationStatus, **fields: Any) -> SimulationRecord:
        record = self.repository.transition(sid, status, stage=STATUS_STAGE[status], progress=STATUS_PROGRESS[status], **fields)
        log_event(logger, f"simulation.{status.value.lower()}", simulation_id=sid, stage=record.stage.value)
        return record

    def execute(self, simulation_id: str) -> None:
        record = self.repository.get(simulation_id)
        if record is None or record.status != SimulationStatus.CREATED:
            return
        scenario = self.registry.scenarios[record.scenario_id]
        model = self.registry.models[record.model_version]
        workspace: Path | None = None
        artifacts: dict[str, Any] = {}
        started = utcnow()
        try:
            record = self._advance(simulation_id, SimulationStatus.VALIDATING, started_at=started)
            try:
                validated = validate_inputs(scenario, model, self.settings.models_dir, self.settings.raw_dir)
            except ValidationFailure as exc:
                raise _StageFailure(exc.code, exc.message, exc.details) from exc
            try:
                runner = self.runner_factory(self.settings)
            except SwmmUnavailableError as exc:
                raise _StageFailure(ErrorCode.SWMM_UNAVAILABLE, "The SWMM simulation engine is not available on the server.") from exc
            self.repository.update_fields(simulation_id, model_sha256=validated.model_sha256, rainfall_sha256=validated.rainfall_sha256)

            record = self._advance(simulation_id, SimulationStatus.PREPARING)
            workspace = self.workspaces.create(simulation_id)
            input_file = workspace / "input.inp"
            # "copy-baseline": the approved master model is copied unmodified.
            shutil.copyfile(validated.model_path, input_file)
            if sha256_file(input_file) != model.sha256:
                raise _StageFailure(ErrorCode.MODEL_VALIDATION_FAILED, "The prepared model input does not match the approved model.")
            artifacts = {name: self.workspaces.key(simulation_id, name) for name in ("input.inp", "report.rpt", "output.out", "stdout.log", "stderr.log", "metadata.json")}
            self.repository.update_fields(simulation_id, artifacts=artifacts)
            self._write_metadata(simulation_id, record, scenario, model, validated.checks, None)

            record = self._advance(simulation_id, SimulationStatus.RUNNING)
            try:
                run = runner.run(workspace)
            except SwmmUnavailableError as exc:
                raise _StageFailure(ErrorCode.SWMM_UNAVAILABLE, "The SWMM simulation engine could not be started.") from exc
            except SwmmExecutionError as exc:
                code = ErrorCode.SIMULATION_TIMEOUT if exc.timed_out else ErrorCode.SIMULATION_FAILED
                details: dict[str, Any] = {"exitCode": exc.exit_code}
                report_file = workspace / "report.rpt"
                if report_file.is_file():
                    try:
                        details["swmmErrors"] = parse_report(report_file).errors
                    except ReportParseError:
                        pass
                self.repository.update_fields(simulation_id, swmm_exit_code=exc.exit_code)
                raise _StageFailure(code, "Simulation failed during SWMM execution." if not exc.timed_out else "SWMM execution timed out.", details) from exc
            self.repository.update_fields(simulation_id, swmm_exit_code=run.exit_code, swmm_elapsed_seconds=run.elapsed_seconds)

            record = self._advance(simulation_id, SimulationStatus.PROCESSING)
            try:
                report = parse_report(run.report_file)
                if report.errors:
                    raise _StageFailure(ErrorCode.SIMULATION_FAILED, "SWMM reported input or runtime errors.", {"swmmErrors": report.errors})
                if report.engine_version != model.engine_version:
                    raise _StageFailure(
                        ErrorCode.PROCESSING_FAILED,
                        "The SWMM engine version differs from the version registered for this model.",
                        {"expected": model.engine_version, "actual": report.engine_version},
                    )
                output = read_output(run.output_file)
                results, timeseries = process_results(
                    simulation_id=simulation_id,
                    scenario_id=record.scenario_id,
                    model_version=record.model_version,
                    processing_version=record.processing_version,
                    report=report,
                    output=output,
                    inp=validated.inp,
                    rainfall=validated.rainfall,
                )
            except (ReportParseError, OutputFormatError) as exc:
                raise _StageFailure(ErrorCode.PROCESSING_FAILED, "SWMM results could not be parsed.", {"reason": str(exc)}) from exc
            except ResultProcessingError as exc:
                raise _StageFailure(ErrorCode.PROCESSING_FAILED, "SWMM results failed validation.", {"reason": str(exc), "details": exc.details}) from exc

            artifacts["results.json"] = self.results.write(simulation_id, ResultStore.RESULTS, results)
            artifacts["hydraulics_timeseries.json"] = self.results.write(simulation_id, ResultStore.TIMESERIES, timeseries)
            if self.flood_products is not None:
                try:
                    flood_manifest = self.flood_products.ensure(simulation_id, record.scenario_id, record.model_version)
                except FloodProcessingError as exc:
                    raise _StageFailure(ErrorCode.PROCESSING_FAILED, "Flood post-processing failed.", {"reason": str(exc), "details": exc.details}) from exc
                artifacts["flood/manifest.json"] = f"{simulation_id}/flood/manifest.json"
                artifacts["floodProcessingVersion"] = flood_manifest["floodProcessingVersion"]
            self.repository.update_fields(simulation_id, artifacts=artifacts, engine_version=report.engine_version)
            record = self._advance(simulation_id, SimulationStatus.COMPLETED, completed_at=utcnow())
            self._write_metadata(simulation_id, record, scenario, model, validated.checks, None)
        except _StageFailure as failure:
            self._fail(simulation_id, failure.code, failure.message, failure.details, scenario, model)
        except Exception as exc:  # noqa: BLE001 - must never leave a run in an active state
            logger.exception("simulation.unexpected_error simulation_id=%s", simulation_id)
            self._fail(simulation_id, ErrorCode.INTERNAL_ERROR, "The simulation failed because of an internal error.", {"exception": type(exc).__name__}, scenario, model)

    def _fail(self, sid: str, code: str, message: str, details: Any, scenario: ScenarioDefinition, model: ModelDefinition) -> None:
        current = self.repository.get(sid)
        if current is None or current.is_terminal:
            return
        record = self.repository.transition(
            sid,
            SimulationStatus.FAILED,
            stage=current.stage,
            progress=current.progress,
            completed_at=utcnow(),
            error_code=code,
            error_message=message,
            error_details=details,
        )
        log_event(logger, "simulation.failed", simulation_id=sid, stage=record.stage.value, code=code)
        if self.workspaces.path(sid).is_dir():
            self._write_metadata(sid, record, scenario, model, None, {"code": code, "message": message, "details": details})

    def _write_metadata(self, sid: str, record: SimulationRecord, scenario: ScenarioDefinition, model: ModelDefinition, checks: list[dict[str, Any]] | None, error: dict[str, Any] | None) -> None:
        fresh = self.repository.get(sid) or record
        payload = {
            "simulationId": sid,
            "scenarioId": fresh.scenario_id,
            "modelVersion": fresh.model_version,
            "processingVersion": fresh.processing_version,
            "applicationVersion": fresh.application_version,
            "status": fresh.status.value,
            "stage": fresh.stage.value,
            "createdAt": to_iso_z(fresh.created_at),
            "startedAt": to_iso_z(fresh.started_at),
            "completedAt": to_iso_z(fresh.completed_at),
            "model": {"file": model.inp_file, "sha256": fresh.model_sha256, "engine": model.engine, "engineVersion": model.engine_version},
            "rainfall": {"file": Path(scenario.rainfall["rawFile"]).name, "sha256": fresh.rainfall_sha256, "source": scenario.source["name"]},
            "inputPreparation": scenario.compatible_models[model.model_version]["inputPreparation"],
            "parameters": fresh.parameters,
            "swmm": {"exitCode": fresh.swmm_exit_code, "elapsedSeconds": fresh.swmm_elapsed_seconds, "engineVersion": fresh.engine_version},
            "validationChecks": checks,
            "artifacts": fresh.artifacts,
            "error": error,
        }
        write_json_atomic(self.workspaces.path(sid) / "metadata.json", payload)

    def ensure_completed(self, simulation_id: str) -> SimulationRecord:
        record = self.get(simulation_id)
        if record.status != SimulationStatus.COMPLETED:
            raise ConflictError(
                ErrorCode.SIMULATION_NOT_COMPLETED,
                "Results are only available for completed simulations.",
                details={"status": record.status.value},
                simulation_id=record.simulation_id,
            )
        return record
