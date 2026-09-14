# ChennaiFlood-Twin — Frontend

React 19 + TypeScript + Vite 8 + CesiumJS 1.145 Digital Twin of Ward 176, Velachery.
The browser only visualises backend results. No hydraulics, flood processing or risk logic runs here.
See `docs/07_FRONTEND_DESIGN.md` and `docs/08_CESIUM_DIGITAL_TWIN.md`.

## Run (development)

Start the backend first (see `backend/README.md`, port 8000), then:

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173 — /api is proxied to http://127.0.0.1:8000
```

The app shows the most recent **completed** Michaung simulation from the backend, if one exists, and can start a new run with **Run simulation**.

## Checks

```powershell
npm run typecheck
npm run lint
npm run test
npm run build
```

## Structure

| Path | Responsibility |
|---|---|
| `src/api/client.ts`, `src/api/endpoints.ts` | The only place that talks HTTP; typed `scenariosApi`, `simulationsApi`, `floodApi`, `gisApi`; structured `ApiError` |
| `src/types/` | TypeScript types mirroring `docs/06_API_CONTRACT.md` (§81–82) |
| `src/hooks/queries.ts` | TanStack Query hooks. Server state is keyed by simulationId/timestamp; status polling stops at COMPLETED/FAILED |
| `src/state/viewerStore.ts` | Layer visibility, flood opacity, terrain exaggeration, selection |
| `src/state/simulationStore.ts` | Selected scenario, tracked run, active simulation (ignores late completions) |
| `src/state/floodStore.ts` | Selected reporting timestamp per simulation, playback (play/pause, 0.5–4× speed) |
| `src/hooks/useTimeline.ts` | Active timeline entry, flood-state label, playback driver (advances only to preloaded actual timestamps) |
| `src/cesium/DigitalTwinController.ts` | Single viewer lifecycle, static layers, flood layer replacement, selection/highlight, camera (`fitWard`, `resetView`) |
| `src/cesium/terrain.ts` | `CustomHeightmapTerrainProvider` backed by `/gis/terrain` (project Copernicus DEM; masked cells get no elevation) |
| `src/components/` | Shell, viewer, layer controls, scenario/simulation panels, live KPI panel, timeline bar, Flood/Hydraulics/Exposure/Actions tabs, explainability inspector, Methodology & Limitations dialog |
| `src/components/decision/` | Potential bottlenecks, model-derived exposure, recommendations (backend results only) and their Cesium sync |
| `src/test/fixtures.tsx` | Clearly marked synthetic API-shaped fixtures for component tests only |

## Visualisation conventions (documented, not data changes)

- **Buildings:** a uniform 6 m extrusion for 3D context, because the project has no height data. They turn semi-transparent while a flood slice is shown, so ground-draped flood zones remain visible.
- **Terrain:**
  - Heights are the Copernicus GLO-30 values as delivered, not converted to ellipsoidal height, and used consistently for all layers.
  - Outside the Ward 176 DEM mask the surface stays at height 0 ("no data"), which creates a small edge step.
  - Exaggeration is a labelled visual aid only.
- **Flood:** "Simulated node flooding (model-derived)".
  - Colours map the backend `state`/`overflowClass`; the frontend holds no thresholds.
  - Shaded polygons are nearest-node influence zones, not flood extent, and there is no ground depth (see `docs/FLOOD_PROCESSING_METHOD.md`).
- **Base map:** OpenStreetMap tiles (no Cesium Ion token needed).

## Demo flow

Load verified demo result → play the timeline → Go to Peak Flood (Flood tab: rainfall / overflow chart) → Hydraulics (time-aware potential bottlenecks, C169 evidence) → Exposure → Actions → switch to 1.25× (run or load the stored result) → Compare (scenario overview chart 1.00× / 1.25× / 1.50×, changes, comparison layer) → Methodology & Limitations (presenter questions) → Reset demo (returns to the verified demo result).

- **Header:** backend connectivity and the displayed result (multiplier + source).
- **Map legend:** follows the visible layers.
- **Errors:** offer Retry / Reload result / Resume rendering / Restart 3D viewer.

The full runbook is in the root [`README.md`](../README.md).

## Charts

`src/components/charts/` contains dependency-free SVG charts:
- `EventCharts` plots the backend flood timeline (rainfall applied in SWMM, simulated system overflow rate).
- `ScenarioOverviewChart` plots values from backend comparisons.

Neither computes scientific values; only axis scaling and bar lengths are derived.

## Container build

`frontend/Dockerfile` builds the production bundle (`VITE_API_BASE_URL=/api/v1`) and serves it with nginx, which proxies `/api` to the backend service (`frontend/docker/nginx.conf`). See `docs/DOCKER_DEPLOYMENT.md`.

## Known limitations

- Playback steps one 30-minute SWMM reporting timestamp per second at 1×; it never interpolates states and waits for the next slice if it is not loaded.
- Static roads, drains, subcatchments and the ward outline are drawn at DEM-sampled heights instead of ground-clamped geometry (≈ 4× faster on the demo iGPU: 4.3–5.2 → 19–20 fps with all layers; see `docs/PERFORMANCE_NOTES.md`). Buildings remain entities; 3D Tiles are not needed at current measurements.
- Bottleneck, exposure and recommendation logic lives in the backend; the frontend only displays, highlights and filters.
- In development, React StrictMode mounts the viewer twice (create → destroy → create); production mounts it once.
