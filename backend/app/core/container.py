"""Explicit wiring of repositories and services for one application instance."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from sqlalchemy.engine import Engine

from app.core.config import Settings
from app.gis.network_mapping import NetworkMapping, load_network_mapping
from app.gis.web_assets import WebAssetBuilder
from app.repositories.database import create_db_engine
from app.repositories.registry import Registry
from app.repositories.results import ResultStore, WorkspaceStore
from app.repositories.simulations import SimulationRepository
from app.services.decision_service import DecisionProductStore, DecisionService
from app.services.demo_service import DemoService
from app.services.comparison_service import ComparisonService
from app.services.gis_service import GisService
from app.services.flood_service import FloodProductStore, FloodService
from app.services.health_service import HealthService
from app.services.result_service import ResultService
from app.services.scenario_service import ScenarioService
from app.services.timeseries_service import TimeseriesService
from app.services.simulation_service import LocalThreadExecutor, RunnerFactory, SimulationExecutor, SimulationService, default_runner_factory
from app.simulation.inp_reader import InpModel, read_inp
from app.simulation.validator import model_path_for


class _ModelContext:
    """Lazily loaded, cached structure of the configured approved model."""

    def __init__(self, settings: Settings, registry: Registry) -> None:
        self.model = registry.models[settings.model_version]
        self.inp_path = model_path_for(self.model, settings.models_dir)
        self._settings = settings
        self._inp: InpModel | None = None
        self._mapping: NetworkMapping | None = None
        self._lock = threading.Lock()

    def inp(self) -> InpModel:
        with self._lock:
            if self._inp is None:
                self._inp = read_inp(self.inp_path)
            return self._inp

    def mapping(self) -> NetworkMapping:
        inp = self.inp()
        with self._lock:
            if self._mapping is None:
                files = self.model.network_mapping
                self._mapping = load_network_mapping(inp, self._settings.processed_dir / files["conduitsCsv"], self._settings.processed_dir / files["nodesCsv"])
            return self._mapping


@dataclass
class Container:
    settings: Settings
    registry: Registry
    engine: Engine
    scenarios: ScenarioService
    simulations: SimulationService
    results: ResultService
    gis: GisService
    flood: FloodService
    decision: DecisionService
    demo: DemoService
    comparisons: ComparisonService
    timeseries: TimeseriesService
    health: HealthService
    executor: SimulationExecutor

    @classmethod
    def build(cls, settings: Settings, *, executor: SimulationExecutor | None = None, runner_factory: RunnerFactory | None = None) -> Container:
        settings.ensure_runtime_dirs()
        registry = Registry(settings.registry_dir)
        if settings.model_version not in registry.models:
            raise ValueError(f"MODEL_VERSION '{settings.model_version}' is not in the model registry")
        engine = create_db_engine(settings.resolved_database_url)
        repository = SimulationRepository(engine)
        workspaces = WorkspaceStore(settings.workdir)
        result_store = ResultStore(settings.results_root)
        executor = executor or LocalThreadExecutor(settings.simulation_max_concurrent)
        model_ctx = _ModelContext(settings, registry)
        builder = WebAssetBuilder(
            settings,
            model_inp_path=model_ctx.inp_path,
            model_version=model_ctx.model.model_version,
            network_mapping_files=model_ctx.model.network_mapping,
            inp_loader=model_ctx.inp,
            mapping_loader=model_ctx.mapping,
        )
        flood_store = FloodProductStore(settings, registry, workspaces, result_store)
        decision_store = DecisionProductStore(settings, registry, workspaces, result_store, flood_store, builder)
        simulations = SimulationService(
            settings, registry, repository, workspaces, result_store, executor, runner_factory or default_runner_factory,
            flood_products=flood_store, decision_products=decision_store,
        )
        flood = FloodService(simulations, flood_store)
        decision = DecisionService(simulations, decision_store, flood)
        results = ResultService(simulations, result_store, registry, model_ctx.mapping, flood, decision)
        return cls(
            settings=settings,
            registry=registry,
            engine=engine,
            scenarios=ScenarioService(settings, registry),
            simulations=simulations,
            results=results,
            gis=GisService(builder, settings.processed_dir / "gis" / "ward176_dem.tif"),
            flood=flood,
            decision=decision,
            demo=DemoService(simulations, registry, result_store),
            comparisons=ComparisonService(settings, simulations, result_store, results, flood, decision),
            timeseries=TimeseriesService(simulations, workspaces, model_ctx.mapping),
            health=HealthService(settings, registry, engine, builder),
            executor=executor,
        )
