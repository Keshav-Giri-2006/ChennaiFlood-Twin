# ChennaiFlood-Twin — Backend

FastAPI modular monolith that runs the approved Ward 176 EPA SWMM model for a
rainfall scenario and serves structured, model-derived results and web-ready
GIS layers. See `docs/05_BACKEND_DESIGN.md` and `docs/06_API_CONTRACT.md`.

```text
API (app/api) → services (app/services) → SWMM / GIS / analysis → repositories (SQLite + files)
```

## Layout

| Path | Purpose |
|---|---|
| `app/main.py` | App factory, CORS, request IDs, lifespan (startup recovery) |
| `app/core/` | Settings (env-based), logging, structured errors, dependency container |
| `app/api/routes/` | `health`, `scenarios`, `simulations`, `flood`, `decision`, `demo`, `comparisons`, `gis` |
| `app/schemas/` | Pydantic request/response models (contract field names) |
| `app/models/simulation.py` | Status/stage enums and the allowed state transitions |
| `app/simulation/` | `.inp` reader, rainfall reader, validator, SWMM runner, `.rpt` parser, binary `.out` reader |
| `app/analysis/result_processing.py` | Report + output → `results.json` / `hydraulics_timeseries.json` with cross-checks |
| `app/services/` | Scenario, simulation orchestration, result views (summary/KPIs/diagnostics), GIS, health |
| `app/gis/` | CRS transformation, model↔source ID mapping, web GeoJSON builder |
| `app/repositories/` | SQLAlchemy simulation metadata, workspace/result stores, model/scenario registry |
| `config/models.json` | Approved model registry (file, pinned SHA-256, expected element counts, limitations) |
| `config/scenarios.json` | Scenario registry (rainfall source file, checksum, model binding, what-if rainfall multiplier range) |
| `config/demo.json` | Verified precomputed demonstration result (archived SWMM outputs, SHA-256 pinned) |
| `Dockerfile` | Container image with EPA SWMM 5.2.4 built from source (see `docs/DOCKER_DEPLOYMENT.md`) |
| `runtime/` (git-ignored) | SQLite DB, `simulation_runs/<id>/`, `results/<id>/`, `web_assets/` |

## Setup (Windows, PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env   # then set SWMM_EXECUTABLE
```

`SWMM_EXECUTABLE` must point at the SWMM 5.2.4 command-line runner, e.g.
`C:\Program Files\EPA SWMM 5.2.4 (64-bit)\runswmm.exe`. On Linux, set it to a
`runswmm` built from EPA SWMM 5.2.4 sources, or put `runswmm` on `PATH`.
Data paths default to the repository layout; override with `DATA_DIR` etc.

## Run

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

OpenAPI docs: <http://127.0.0.1:8000/docs>

Typical flow:

```bash
curl http://127.0.0.1:8000/api/v1/health/ready
curl http://127.0.0.1:8000/api/v1/scenarios/michaung-2023
curl -X POST http://127.0.0.1:8000/api/v1/simulations -H "Content-Type: application/json" -d "{\"scenarioId\":\"michaung-2023\",\"modelVersion\":\"ward176-hydraulic-reconstructed-v1\"}"
curl http://127.0.0.1:8000/api/v1/simulations/<simulationId>          # poll until COMPLETED
curl http://127.0.0.1:8000/api/v1/simulations/<simulationId>/kpis
curl http://127.0.0.1:8000/api/v1/gis/buildings -o buildings.geojson
```

A run of the Michaung scenario takes ~15–20 s (SWMM ~12–18 s).

## Test

```powershell
.venv\Scripts\python.exe -m pytest tests/unit tests/api     # fast; no SWMM needed
.venv\Scripts\python.exe -m pytest tests/integration        # real SWMM 5.2.4 run (skips if SWMM missing)
```

API lifecycle tests use a clearly marked `ReplayRunner` test double that copies
archived SWMM outputs of the same model; the integration test runs the real executable.

## Simulation pipeline

| Status | Stage | Progress | What happens |
|---|---|---|---|
| CREATED | QUEUED | 0 | Record persisted; job queued (`SIMULATION_MAX_CONCURRENT`, default 1) |
| VALIDATING | VALIDATION | 10 | Model approved + SHA-256 pinned, element counts, routing/units, gage↔timeseries binding, rainfall file checksum, model rainfall = source rainfall, SWMM executable resolvable |
| PREPARING | WORKSPACE_PREPARATION | 20 | New `simulation_runs/<uuid>/`, master model copied unmodified to `input.inp` and re-verified |
| RUNNING | SWMM_EXECUTION | 30 | `runswmm input.inp report.rpt output.out` (argument list, no shell, timeout, stdout/stderr captured) |
| PROCESSING | RESULT_PROCESSING | 75 | Report + binary output parsed and cross-validated; results persisted |
| COMPLETED | COMPLETE | 100 | Summary/KPIs/diagnostics available |
| FAILED | (stage where it failed) | — | Structured error code; artifacts kept |

Progress is stage-based (`progressBasis: "stage"`), not simulated-time completion.
Runs left active by a crashed process are marked `FAILED / SIMULATION_INTERRUPTED` on startup.

## Security

* Clients choose only `scenarioId` (+ optional registered `modelVersion`); unknown fields are rejected.
* Executable, model and data paths come only from server configuration/registries.
* Simulation IDs are server-generated UUIDs; workspaces are created with `exist_ok=False`.
* Errors never include stack traces or filesystem paths. CORS origins are an explicit list.

## Flood products (flood-processing-v1)

Generated during PROCESSING, or lazily for older completed runs, into `runtime/results/<id>/flood/` and cached by
processing version and SWMM output checksum. Node flooding/surcharge states and nearest-node influence zones
for all 190 reporting timestamps are included. Ground flood depth and extent are deliberately **not** derived;
see `docs/FLOOD_PROCESSING_METHOD.md`.

Endpoints: `/simulations/{id}/flood`, `/flood/timeline`, `/flood/timeslice?time=`, `/flood/timeslices/{key}`,
`/flood/zones`, `/timeseries/{system|nodes/{nodeId}|links/{linkId}}`, `/gis/terrain` (API contract §82).

## Decision-support products (bottleneck-analysis-v1, exposure-analysis-v1, decision-support-v1)

Generated during PROCESSING right after the flood products (lazily for older runs) into `runtime/results/<id>/decision/`,
cached by all method versions and the SWMM output checksum. Bump the corresponding `*_VERSION` setting whenever a
criterion, threshold or rule changes, otherwise cached products are reused. See `docs/DECISION_SUPPORT_METHOD.md`.

Endpoints: `/simulations/{id}/bottlenecks[/geojson|/{linkId}]`, `/exposure`, `/exposure/{buildings|roads}?time=`,
`/recommendations`; `/risk` returns `404 RISK_PRODUCT_NOT_AVAILABLE` (API contract §83).

## Demo result, what-if scenarios, comparison (Prompt 4)

* `POST /demo/michaung-2023-verified/load` registers the verified archived SWMM 5.2.4 result and processes it through the normal pipeline without running SWMM; later loads re-use it.
* `POST /simulations` accepts `{"parameters": {"rainfallMultiplier": 0.5–2.0}}`; only the workspace copy's rainfall series is scaled (1.00× reproduces the approved model byte-for-byte). See `docs/SCENARIO_ANALYSIS_METHOD.md`.
* `GET /simulations/{id}/bottlenecks/timeline` — time-varying potential-bottleneck state; `GET /comparisons?baseline=&scenario=` — cached scenario comparison.

## Known limitations (this phase)

* No flood depth/extent or risk score — the API returns `null` with `available: false` (or `404 FLOOD_PRODUCT_NOT_AVAILABLE` / `RISK_PRODUCT_NOT_AVAILABLE`). Bottlenecks, exposure and recommendations are model-derived decision support from one uncalibrated run.
* Only the registered `rainfallMultiplier` parameter is supported; other parameters are rejected with `UNSUPPORTED_PARAMETER`.
* Cancellation is not implemented.
* On memory-constrained hosts, numpy/OpenBLAS is limited to one thread (`app/__init__.py`).
