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

## 2026-09-14 — Prompt 3: interactive timeline, potential bottlenecks, exposure, recommendations

**What changed**
- **Repository:** initialised Git; checkpoint commit `3c1ca01` of Prompt 1 + 2 (runtime outputs, venv, node_modules, `.env`, logs and >50 MB Copernicus tiles ignored; controlled data stored byte-exact via `.gitattributes`).
- **Backend:**
  - `bottleneck-analysis-v1` (`app/analysis/bottleneck_analysis.py`): SWMM-report screening (capacity limited, sustained full-bore surcharge, peak flow > full-flow capacity, connected node flooding), component-without-outfall cap, confidence caveats, numerical diagnostics kept separate.
  - `exposure-analysis-v1` (`app/analysis/exposure_analysis.py`): building/carriageway intersection with influence zones of overflowing nodes, per timestamp / peak / event.
  - `decision-support-v1` (`app/analysis/recommendations.py`): six evidence-triggered rules R1–R6.
  - `DecisionProductStore`/`DecisionService`, generated in PROCESSING after flood products, cached by versions + output checksum; new routes (API contract §83); risk endpoints return `404 RISK_PRODUCT_NOT_AVAILABLE`.
  - `models.json` `diagnosticContext` curated from the existing hydraulic investigation documents (no model change).
- **Frontend:** timeline controller (play/pause, first/prev/next/peak, slider, 0.5–4× speed, preloading, no interpolation); live KPI panel; Flood / Hydraulics / Exposure / Actions tabs; potential-bottleneck layer with View Hotspots and selection; exposure highlighting by diffing existing building/road entities; recommendation cards with evidence and "Show on map"; explainability inspector; Methodology & Limitations dialog; OSM imagery capped at zoom 19.
- **Documentation:** `docs/DECISION_SUPPORT_METHOD.md`; API contract §83; READMEs.

**Scientific decisions**
- C162, C175, C180, C086 (time-step critical) and C166 (instability, component without outfall) meet no loading criterion and are not potential bottlenecks; they appear as numerical diagnostics / data-verification recommendations.
- Only 4 of 48 model components contain an outfall; 57 % of simulated overflow volume occurs in components without one. Loading there is capped at LOW and converted to connectivity-verification recommendations.
- A hazard × exposure risk indicator was not implemented (no ground depth/extent; zones are associations).
- No change to the SWMM model, rainfall, DEM, GIS source data or network.

## 2026-09-14 — Prompt 4: demo hardening, performance, dynamic hydraulics, rainfall scenarios, Docker groundwork

**What changed**
- **Demo hardening:** verified precomputed demo result (`backend/config/demo.json`, archived SWMM 5.2.4 outputs byte-identical to a live run) loaded without running SWMM and re-used on later loads; "Load verified demo result"; clear labels (Precomputed demonstration result / Simulated now / Stored result); backend status indicator (`/health` every 20 s); Reset demo; request timeouts and friendly error messages with Retry / Reload result / Resume rendering / Restart 3D viewer; panel error boundaries with Retry.
- **Performance:** measured with an in-app frame profiler in headless Edge (hardware GPU). Ground-clamped roads/drains cost ≈ 95 ms per frame; they, subcatchments and the ward outline are now terrain-sampled primitives. All layers 4.3–5.2 → 19–20 fps (p50 235 → 52 ms), no data removed. No 3D Tiles. See `docs/PERFORMANCE_NOTES.md`.
- **Dynamic hydraulics:** `bottleneck-timeline-v1` (`GET /bottlenecks/timeline`) from SWMM link time series; time-aware Hydraulics panel (active bottlenecks, highest severity, most loaded conduit, View on map) and map restyling that follows the timeline.
- **Scenarios:** `scenario-analysis-v1` rainfall multiplier (0.5–2.0) applied only to isolated workspace copies with independent verification and a SWMM-applied-rainfall cross-check; scenario metadata; comparison API with categorical flood-influence comparison, bottleneck / exposure / recommendation changes and cached results; Compare tab and comparison map layer; "Load stored M× result".
- **Docker:** backend (EPA SWMM 5.2.4 built from the pinned USEPA commit), frontend (nginx + /api proxy), `compose.yaml`, healthchecks, `.dockerignore`, root `.env.example`. **Not built or run:** the Docker Desktop engine fails to start on this machine (see `docs/DOCKER_DEPLOYMENT.md` §7).
- **Documentation:** `docs/SCENARIO_ANALYSIS_METHOD.md`, `docs/PERFORMANCE_NOTES.md`, `docs/DOCKER_DEPLOYMENT.md`, `DECISION_SUPPORT_METHOD.md` §3.2, API contract §84.

**Scientific decisions / regression**
- 1.00× scenario: transformed model byte-identical to the approved model; SWMM output byte-identical to the archived baseline; all baseline KPIs, bottlenecks, exposure and recommendations unchanged.
- 1.25× and 1.50×: rainfall totals exactly +25 % / +50 %; responses non-linear (e.g. peak overflow +33.4 % / +75.8 %); comparisons report new, persisting and increased potential bottlenecks (C169 persists HIGH; C156 new HIGH).
- Event-level bottleneck, exposure and recommendation methods unchanged (versions unchanged); the timeline product is separately versioned.
- No change to the SWMM model, rainfall, DEM, GIS source data or network; checksums verified.
