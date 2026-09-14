import re
import shutil
import sys
from pathlib import Path

import pytest

from app.core.config import Settings
from app.gis.network_mapping import load_network_mapping
from app.gis.transform import UTM44N, CrsError, declared_crs, transform_xy
from app.repositories.registry import Registry
from app.simulation.inp_reader import read_inp
from app.simulation.runner import SwmmExecutionError, SwmmRunner, SwmmUnavailableError, resolve_swmm_executable
from app.simulation.validator import ValidationFailure, validate_inputs
from tests.conftest import MODEL_INP, REPO_ROOT

BACKEND = Path(__file__).resolve().parents[2]


# --- SWMM runner -------------------------------------------------------------------
# The runner invokes [executable, input, report, output]. Using the Python
# interpreter as the "executable" makes input.inp a script we control, which
# exercises exit-code, timeout and missing-output handling without SWMM.
def _workspace(tmp_path: Path, script: str) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "input.inp").write_text(script, encoding="utf-8")
    return ws


def test_runner_rejects_missing_executable(tmp_path: Path):
    with pytest.raises(SwmmUnavailableError):
        resolve_swmm_executable(str(tmp_path / "no-such-runswmm"))


def test_runner_requires_input_file(tmp_path: Path):
    ws = tmp_path / "empty"
    ws.mkdir()
    with pytest.raises(SwmmExecutionError, match="input file is missing"):
        SwmmRunner(Path(sys.executable), 30).run(ws)


def test_runner_detects_nonzero_exit(tmp_path: Path):
    ws = _workspace(tmp_path, "import sys\nsys.exit(3)\n")
    with pytest.raises(SwmmExecutionError) as info:
        SwmmRunner(Path(sys.executable), 30).run(ws)
    assert info.value.exit_code == 3


def test_runner_detects_missing_outputs(tmp_path: Path):
    ws = _workspace(tmp_path, "print('no outputs written')\n")
    with pytest.raises(SwmmExecutionError, match="no report"):
        SwmmRunner(Path(sys.executable), 30).run(ws)
    assert "no outputs written" in (ws / "stdout.log").read_text()


def test_runner_enforces_timeout(tmp_path: Path):
    ws = _workspace(tmp_path, "import time\ntime.sleep(20)\n")
    with pytest.raises(SwmmExecutionError) as info:
        SwmmRunner(Path(sys.executable), 1).run(ws)
    assert info.value.timed_out


def test_runner_rejects_paths_outside_workspace(tmp_path: Path):
    ws = _workspace(tmp_path, "")
    with pytest.raises(SwmmExecutionError, match="escapes"):
        SwmmRunner(Path(sys.executable), 30).run(ws, input_name="../outside.inp")


# --- input validation ----------------------------------------------------------------
def _registry_items():
    settings = Settings(DATA_DIR=REPO_ROOT)
    registry = Registry(settings.registry_dir)
    return settings, registry.scenarios["michaung-2023"], registry.models["ward176-hydraulic-reconstructed-v1"]


def test_real_inputs_pass_validation():
    settings, scenario, model = _registry_items()
    result = validate_inputs(scenario, model, settings.models_dir, settings.raw_dir)
    assert all(c["passed"] for c in result.checks)
    assert result.model_sha256 == model.sha256


def test_modified_model_copy_fails_checksum(tmp_path: Path):
    settings, scenario, model = _registry_items()
    models = tmp_path / "models"
    models.mkdir()
    text = MODEL_INP.read_text(encoding="utf-8") + "\n;; modified\n"
    (models / model.inp_file).write_text(text, encoding="utf-8")
    with pytest.raises(ValidationFailure) as info:
        validate_inputs(scenario, model, models, settings.raw_dir)
    assert info.value.code == "MODEL_VALIDATION_FAILED"


def test_missing_rainfall_fails_validation(tmp_path: Path):
    settings, scenario, model = _registry_items()
    with pytest.raises(ValidationFailure) as info:
        validate_inputs(scenario, model, settings.models_dir, tmp_path)
    assert info.value.code == "RAINFALL_NOT_FOUND"


def test_master_model_is_unchanged():
    settings, _scenario, model = _registry_items()
    from app.utils.files import sha256_file

    assert sha256_file(settings.models_dir / model.inp_file) == model.sha256


# --- GIS / traceability ----------------------------------------------------------------
def test_network_mapping_preserves_source_and_model_ids():
    settings, _scenario, model = _registry_items()
    inp = read_inp(MODEL_INP)
    files = model.network_mapping
    mapping = load_network_mapping(inp, settings.processed_dir / files["conduitsCsv"], settings.processed_dir / files["nodesCsv"])
    assert len(mapping.link_to_object_id) == 182
    assert mapping.link_to_object_id["C162"] == 5902
    assert mapping.link_to_object_id["C175"] == 5913
    assert mapping.link_to_object_id["C180"] == 5916
    assert len(mapping.node_locations) == 228
    assert any(len(links) > 1 for links in mapping.object_id_to_links.values())  # one source drain -> several model links


def test_utm_transform_matches_independent_reference():
    # Reference lon/lat for reconstructed node 1 recorded in ward176_junction_elevations.csv.
    lons, lats = transform_xy(UTM44N, [414999.398], [1433833.842])
    assert lons[0] == pytest.approx(80.21628010069084, abs=1e-8)
    assert lats[0] == pytest.approx(12.96896217261977, abs=1e-8)


def test_unknown_crs_is_rejected():
    with pytest.raises(CrsError):
        declared_crs({"crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::3857"}}})
    with pytest.raises(CrsError):
        declared_crs({"type": "FeatureCollection"})


# --- portability ------------------------------------------------------------------------------
def test_no_hardcoded_windows_paths_in_application_code():
    pattern = re.compile(r"[A-Za-z]:[\\/](?!/)")
    offenders = []
    for path in list((BACKEND / "app").rglob("*.py")) + list((BACKEND / "config").rglob("*.json")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line) and "http" not in line:
                offenders.append(f"{path.name}:{lineno}")
    assert offenders == []


@pytest.mark.parametrize(
    "raw",
    ["http://localhost:8080,http://127.0.0.1:8080", " http://localhost:8080 , http://127.0.0.1:8080 ", '["http://localhost:8080", "http://127.0.0.1:8080"]'],
)
def test_cors_origins_from_environment_accept_comma_separated_and_json(monkeypatch: pytest.MonkeyPatch, raw: str):
    # The container (compose.yaml) and .env.example pass a comma-separated list; this used to fail at startup.
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", raw)
    settings = Settings(_env_file=None)
    assert settings.cors_allow_origins == ["http://localhost:8080", "http://127.0.0.1:8080"]
