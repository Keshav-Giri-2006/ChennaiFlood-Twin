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
| `src/state/floodStore.ts` | Selected reporting timestamp per simulation |
| `src/cesium/DigitalTwinController.ts` | Single viewer lifecycle, static layers, flood layer replacement, selection/highlight, camera (`fitWard`, `resetView`) |
| `src/cesium/terrain.ts` | `CustomHeightmapTerrainProvider` backed by `/gis/terrain` (project Copernicus DEM; masked cells get no elevation) |
| `src/components/` | Shell, viewer, layer controls, scenario/simulation panels, flood panel + legend, KPI strip, inspector |

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

## Known limitations

- Timeline playback (play/pause/speed) is not built yet; the flood panel steps through the actual SWMM timestamps.
- Buildings are individual Cesium entities (6,428). Frame-rate profiling on a visible desktop browser is still to be done before considering 3D Tiles.
- In development, React StrictMode mounts the viewer twice (create → destroy → create); production mounts it once.
