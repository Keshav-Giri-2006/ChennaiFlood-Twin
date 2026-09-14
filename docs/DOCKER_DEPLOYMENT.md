# ChennaiFlood-Twin — Docker Deployment (local groundwork)

Status 2026-09-14 (Prompt 5): **built, run and validated locally** on Docker Desktop (Engine 29.7.2, Compose 5.5.1, WSL 2, linux/amd64). Three defects found during the first real build were fixed (§7). This is a local container deployment, not an AWS deployment.

## 1. Architecture

```text
browser ──► frontend (nginx:1.27-alpine, :80 → host 8080)
              ├── /            static Vite build + Cesium assets
              ├── /healthz     frontend health
              └── /api/*  ───► backend (python:3.13-slim + EPA SWMM 5.2.4, :8000)
                                  ├── FastAPI (1 uvicorn worker, in-process simulation queue)
                                  ├── /opt/swmm/bin/runswmm   (built from USEPA source)
                                  ├── /app/{data_processed, gis, simulation, data_raw/rainfall}  (read-only, baked)
                                  └── /app/runtime  ◄── named volume backend-runtime (SQLite, workspaces, results)
```

The browser bundle always calls the same-origin path `/api/v1`; nginx forwards it to the `backend` service, so no `localhost:8000` is compiled into the bundle and CORS is not needed for the UI.

## 2. Files

| File | Purpose |
|---|---|
| `backend/Dockerfile` | Stage 1 builds `runswmm` from `USEPA/Stormwater-Management-Model` tag `v5.2.4`, pinned to commit `7952ca837988b1c32f791812eccc9fd64547e093` (CMake, Release, tests off). Stage 2: Python 3.13 runtime, `requirements.txt`, app code, registries, checksum-pinned data, non-root `app` user, healthcheck on `/api/v1/health`. |
| `frontend/Dockerfile` | `node:22-alpine` build (`npm ci`, `npm run build` with `VITE_API_BASE_URL=/api/v1`) → `nginx:1.27-alpine` with only `dist/` (no `node_modules`). |
| `frontend/docker/nginx.conf` | SPA fallback, `/api` reverse proxy (300 s read timeout), gzip, cache headers, `/healthz`. |
| `compose.yaml` | `backend` + `frontend`, named volume, healthchecks, `frontend` waits for a healthy backend. |
| `.dockerignore`, `frontend/.dockerignore` | Exclude `.git`, `.env*`, `node_modules`, `.venv`, `dist`, runtime outputs, tests, logs, the Copernicus DEM archive and raw GCC downloads. |
| `.env.example` (root) | Public-safe compose overrides (ports, CORS, log level, concurrency, optional `DATABASE_URL`). |

## 3. Data strategy

| Data | Strategy | Why |
|---|---|---|
| `data_processed/` (≈ 25 MB), `gis/ward176_reconstructed_conduits.geojson`, `data_raw/rainfall/…csv`, approved model `.inp` + verified demo `.rpt/.out` (≈ 4 MB) | **Baked** into the backend image | Read-only, checksum-pinned by `backend/config/*.json`; image is self-contained and reproducible |
| Copernicus DEM archive/tiles (> 200 MB), raw GCC downloads | **Not included** | Not used at runtime (the clipped DEM is in `data_processed`) |
| SQLite DB, simulation workspaces, results, web GIS assets | **Volume** `backend-runtime` → `/app/runtime` | Generated at runtime; survives container restarts |
| Secrets | **None in images** | SQLite needs none; a PostgreSQL `DATABASE_URL` must be injected at run time (never committed) |

## 4. Configuration (environment)

Backend (defaults set in the image): `DATA_DIR=/app`, `RUNTIME_DIR=/app/runtime`, `SWMM_EXECUTABLE=/opt/swmm/bin/runswmm`, `LD_LIBRARY_PATH=/opt/swmm/lib`, `SIMULATION_MAX_CONCURRENT=1`, `OPENBLAS_NUM_THREADS=1`. Compose-overridable: `CORS_ALLOW_ORIGINS`, `LOG_LEVEL`, `SWMM_TIMEOUT_SECONDS`, `DATABASE_URL`, all `*_VERSION` settings (see `backend/.env.example`). Frontend: `VITE_API_BASE_URL` at build time (default `/api/v1`). No Windows paths are used anywhere in the images.

## 5. Build and run

From the repository root, in one terminal:

```bash
docker compose up --build          # foreground; Ctrl+C then `docker compose down` to stop
# or: docker compose up --build -d  (background) + docker compose logs -f
docker compose ps                  # both services "healthy"
# UI: http://localhost:8080   API docs: http://localhost:8000/docs   readiness: http://localhost:8080/api/v1/health/ready
docker compose down                # keeps the runtime volume; add -v to discard stored results
```

Ports can be changed with `BACKEND_PORT` / `FRONTEND_PORT` (see root `.env.example`). Option A (local development) also uses port 8000, so stop the stack before starting the local backend.

### 5.1 Validation performed (2026-09-14)

| Check | Result |
|---|---|
| `docker compose build` | Both images built: backend 599 MB (SWMM compiled from pinned commit `7952ca8…`), frontend 92 MB (nginx + `dist/` only) |
| `docker compose up --build -d` from a fresh volume | Backend `healthy`, frontend `healthy`; about 58 s including image rebuild |
| `/healthz` (nginx), `/api/v1/health`, `/api/v1/health/ready` | 200 / ok / `ready` with `swmm, model, rainfall, data, storage: ok` |
| API through the nginx proxy | scenarios, `/gis/ward`, buildings (517 kB), roads, drains, subcatchments, terrain, Cesium static assets: 200 |
| `runswmm` in the container | EPA SWMM 5.2.4 (Build 5.2.4) runs the approved model in ≈ 9 s |
| Verified demo result | `POST /demo/michaung-2023-verified/load` → COMPLETED (`precomputed-demo`, checksums verified); second load `reused: true` |
| Real SWMM runs via API | 1.00× 10.2 s, 1.25× 11.2 s, 1.50× 14.3 s: all COMPLETED with flood, bottleneck (event + timeline), exposure and recommendation products |
| Comparisons | 1.00× vs 1.25× and vs 1.50× (≈ 0.04 s cached); demo baseline vs 1.25×; invalid multiplier 7 → `422 INVALID_PARAMETER` |
| Browser end-to-end (headless Edge → http://localhost:8080) | Layers load (6,428 buildings, 301 roads, 135 drains, DEM); demo load; playback; Go to Peak (19 flooding / 4 surcharged, 5.435 m³/s, 783 buildings); chart click; Hydraulics C169 inspector; exposure; 32 recommendations; load stored 1.25× / 1.50×; Compare overview and statements; Methodology; Reset demo; page refresh; **0 console errors** |
| Backend stopped while the UI is open | Header shows *Backend offline* with Retry; map, KPIs and timeline keep working from cached data; reconnects ≈ 8 s after `docker compose start backend` |
| `docker compose down` + `up -d` | Healthy again in ≈ 21 s; all 4 stored runs still listed (named volume) |
| Logs | No errors or tracebacks after the fixes |

### 5.2 Linux (container) vs Windows SWMM results

Both are the same EPA SWMM 5.2.4 source, but the container binary is compiled with GCC on Linux and the reference results with the official Windows build. Floating-point differences change the last digits, and in one conduit a short transient:

| Metric | 1.00× Windows (verified demo) | 1.00× Linux container | 1.25× Windows | 1.25× Linux | 1.50× Windows | 1.50× Linux |
|---|---|---|---|---|---|---|
| Runoff / routing continuity (%) | −0.018 / 0.068 | −0.018 / 0.053 | −0.020 / 0.094 | −0.020 / 0.071 | −0.022 / 0.073 | −0.022 / 0.072 |
| Simulated flooding volume (ML, diagnostic) | 197.876 | 197.851 | 264.649 | 264.730 | 336.899 | 336.906 |
| Peak overflow rate (m³/s) | 5.435 | 5.425 | 7.250 | 7.252 | 9.556 | 9.567 |
| Peak time / peak flooding nodes | 22:00 UTC / 19 | 22:00 UTC / 19 | 22:00 / 21 | 22:00 / 21 | 22:00 / 22 | 22:00 / 22 |
| Flooding duration (h) | 90.0 | 90.0 | 87.5 | 90.0 | 92.5 | 92.5 |
| Potential bottlenecks (H/M/L) | 12 (1/0/11) | **13 (1/0/12)** | 13 (2/2/9) | **14 (2/2/10)** | 18 (2/4/12) | 18 (2/4/12) |
| Buildings exposed peak / event | 783 / 948 | 783 / 948 | 964 / 964 | 964 / 964 | 986 / 986 | 986 / 986 |
| Recommendations (HIGH) | 32 (2) | 32 (2) | 37 (3) | 37 (3) | 38 (3) | 38 (3) |

- The extra LOW potential bottleneck at 1.00× is **C159** (GCC 5900). The Linux run reports a single transient flow spike of 2.381 m³/s at 05 Dec 06:05 (Max/Full Flow 1.16, velocity 4.73 m/s, 0.01 h), where the Windows run reports 0.489 m³/s. This meets only criterion L3.
- At 1.25× the extra LOW one is **C189**.
- These are numerical sensitivities of the uncalibrated network, not a methodology change. HIGH/MODERATE classifications, exposure and recommendations are unchanged.
- **Reference:** the verified Windows result (the precomputed demonstration result, also available in the container) remains the reference. Container runs are reported as stored simulation results. Do not expect byte-identical outputs across platforms.

## 6. SWMM in the container

The engine is compiled from the official EPA source at the exact 5.2.4 tag commit (no substitute solver, no mock outputs). The backend's existing safeguards apply unchanged: engine version must be `5.2.4` in the report, model checksum, rainfall checksum and all result cross-checks. If the build or runtime ever fails, `/health/ready` reports `swmm: error`, simulation creation fails with `SWMM_UNAVAILABLE`, and the precomputed demo result still works because it does not execute SWMM.

## 7. Issues found and fixed during validation (2026-09-14)

The Prompt 4 blocker (Docker Desktop engine crash on stale `%LOCALAPPDATA%\Docker\run` socket files) was resolved on the machine; the engine now runs. The first real build/run then exposed three defects, each fixed minimally and re-verified:

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | `runswmm: error while loading shared libraries: libgomp.so.1` | The EPA SWMM engine is compiled with OpenMP; `python:3.13-slim` lacks the GCC OpenMP runtime | `backend/Dockerfile` installs `libgomp1`; the build now fails if `ldd` reports any unresolved engine library |
| 2 | Backend crash-loop: `ImportError: libexpat.so.1` (rasterio) | The rasterio wheel's bundled GDAL needs libexpat, absent from the slim image | Install `libexpat1`; the build imports numpy/pyproj/rasterio/shapely/SQLAlchemy/FastAPI/uvicorn to catch this at build time |
| 3 | Backend crash-loop: `SettingsError: error parsing value for field "cors_allow_origins"` | pydantic-settings JSON-decodes list-typed environment variables before validators run, so the documented comma-separated `CORS_ALLOW_ORIGINS` (set by `compose.yaml`) failed. Local runs did not set the variable | `app/core/config.py` marks the field `NoDecode`; the validator accepts comma-separated or JSON lists (unit test added) |

## 8. Known limitations

- Single backend replica (SQLite + in-process queue); horizontal scaling needs PostgreSQL and a job queue (later prompt).
- First requests after a fresh volume build GIS web assets and decision products (a few seconds).
- The frontend image needs internet access at build time for `npm ci`; the backend build needs GitHub access for the SWMM source.
- Container SWMM results differ slightly from the Windows reference build (§5.2).
- The in-app frame profiler (`window.__digitalTwin`) is exposed only in development builds, not in the nginx production bundle.
