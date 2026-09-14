# ChennaiFlood-Twin — Change Log

## 2026-09-13 — Backend foundation (Prompt 1)

**What changed**
- Added `backend/` FastAPI modular monolith: configuration, logging, structured errors, health/readiness, scenario API, simulation lifecycle, controlled SWMM runner, `.rpt` parser, binary `.out` reader, result processing, SQLite persistence (SQLAlchemy Core, PostgreSQL-ready), summary/KPI/diagnostics APIs, web GIS layer builder and GIS APIs, tests.
- Added `backend/config/models.json` (approved model `ward176-hydraulic-reconstructed-v1`, SHA-256 `bb54b576…2b5c`) and `backend/config/scenarios.json` (`michaung-2023`, raw IMERG CSV SHA-256 `78fa8453…eb6a`).
- Added implementation addendum §81 to `docs/06_API_CONTRACT.md` (additive endpoints/fields only).

**Why**
- Phases 2–5 of `10_IMPLEMENTATION_ROADMAP.md`.

**Scientific artifacts**
- No changes to `data_raw/`, `data_processed/`, `gis/` or `simulation/`. The master model is copied unmodified per run and its checksum is verified before and after execution.
- Web GIS layers are derived artifacts written to `backend/runtime/web_assets/` (CRS transformation only).

**Tests performed / result**
- 66 unit + API tests passed; real-SWMM integration test passed (two concurrent runs).
- Real runs reproduce the documented candidate outputs exactly: runoff continuity −0.018 %, routing continuity 0.068 %, wet-weather inflow 271.424 ML, external outflow 67.405 ML, SWMM flooding loss 197.876 ML (model diagnostic), final storage 5.958 ML.

## 2026-09-13 — Flood processing, time-series API, frontend Digital Twin foundation (Prompt 2)

**What changed**
- **Backend:**
  - `flood-processing-v1`: node flooding/surcharge states plus nearest-node flood influence zones; products cached per simulation and version, and generated in the PROCESSING stage (lazily for older runs).
  - New endpoints: flood summary, timeline, timeslice, timeslices, zones; node/link/system time series; DEM terrain grid. KPIs/summary extended.
  - `inp_reader` now reads conduit offsets and cross-sections. `rasterio` added for DEM reading.
- **Documentation:** `docs/FLOOD_PROCESSING_METHOD.md`; API contract §82.
- **Frontend (new):**
  - React 19 + TypeScript + Vite 8 + CesiumJS 1.145 app with TanStack Query and Zustand stores (viewer / simulation / flood).
  - Single Cesium controller: project DEM terrain, ward, buildings, roads, drains, subcatchments, flood layer, selection, camera.
  - Typed API client, scenario/simulation/flood/KPI/inspector panels, Vitest tests.

**Why**
- Roadmap phases 6, 7, 9 and the first part of 10.

**Scientific decisions**
- Ground flood depth and flood extent are **not** derived. Reasons: SWMM ran without ponding, and the DEM − model rim offset has a median of +3.7 m (datum inconsistency). See the method doc §4.
- No change to the SWMM model, rainfall, DEM, GIS source data or network.

**Tests / result**
- Backend: 89 unit/API tests passed; real-SWMM integration test passed, including flood products.
- Frontend: `tsc -b`, oxlint and `vite build` clean; 23 Vitest tests passed; app run in the browser with real data (layers aligned, selection, toggles, timestamp stepping).
