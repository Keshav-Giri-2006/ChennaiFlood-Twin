"""Read-only registries of approved models and scenarios (backend/config/*.json)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.utils.files import read_json


@dataclass(frozen=True)
class ModelDefinition:
    model_version: str
    name: str
    description: str
    approved: bool
    engine: str
    engine_version: str
    inp_file: str
    sha256: str
    expected_elements: dict[str, int]
    network_mapping: dict[str, str]
    routing: str
    flow_units: str
    limitations: list[str]
    diagnostic_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    name: str
    event: str
    description: str
    rainfall_type: str
    source: dict[str, str]
    rainfall: dict[str, Any]
    compatible_models: dict[str, dict[str, str]]
    limitations: list[str]
    what_if: dict[str, Any] | None = None


@dataclass(frozen=True)
class DemoResultDefinition:
    demo_id: str
    label: str
    description: str
    scenario_id: str
    model_version: str
    report: dict[str, str]
    output: dict[str, str]
    verification: str


class Registry:
    def __init__(self, registry_dir: Path) -> None:
        models = read_json(registry_dir / "models.json")["models"]
        scenarios = read_json(registry_dir / "scenarios.json")["scenarios"]
        self.models: dict[str, ModelDefinition] = {
            m["modelVersion"]: ModelDefinition(
                model_version=m["modelVersion"],
                name=m["name"],
                description=m["description"],
                approved=bool(m["approved"]),
                engine=m["engine"],
                engine_version=m["engineVersion"],
                inp_file=m["inpFile"],
                sha256=m["sha256"],
                expected_elements=m["expectedElements"],
                network_mapping=m["networkMapping"],
                routing=m["routing"],
                flow_units=m["flowUnits"],
                limitations=list(m.get("limitations", [])),
                diagnostic_context=dict(m.get("diagnosticContext", {})),
            )
            for m in models
        }
        self.scenarios: dict[str, ScenarioDefinition] = {
            s["scenarioId"]: ScenarioDefinition(
                scenario_id=s["scenarioId"],
                name=s["name"],
                event=s["event"],
                description=s["description"],
                rainfall_type=s["rainfallType"],
                source=s["source"],
                rainfall=s["rainfall"],
                compatible_models=s["compatibleModels"],
                limitations=list(s.get("limitations", [])),
                what_if=s.get("whatIf"),
            )
            for s in scenarios
        }
        demo_file = registry_dir / "demo.json"
        demos = read_json(demo_file)["demoResults"] if demo_file.is_file() else []
        self.demo_results: dict[str, DemoResultDefinition] = {
            d["demoId"]: DemoResultDefinition(
                demo_id=d["demoId"], label=d["label"], description=d["description"], scenario_id=d["scenarioId"],
                model_version=d["modelVersion"], report=d["report"], output=d["output"], verification=d["verification"],
            )
            for d in demos
        }
        for demo in self.demo_results.values():
            for name in (demo.report["file"], demo.output["file"]):
                if Path(name).is_absolute() or ".." in Path(name).parts:
                    raise ValueError("Demo result paths must be relative to MODEL_DIR")
        for model_file in (m.inp_file for m in self.models.values()):
            if Path(model_file).is_absolute() or ".." in Path(model_file).parts:
                raise ValueError("Model registry paths must be relative to MODEL_DIR")
        for s in self.scenarios.values():
            raw = Path(s.rainfall["rawFile"])
            if raw.is_absolute() or ".." in raw.parts:
                raise ValueError("Scenario rainfall paths must be relative to RAW_DATA_DIR")
