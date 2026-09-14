# ChennaiFlood-Twin — Docker Deployment (local groundwork)

Status 2026-09-14: **Dockerfiles, compose file and configuration are written but have NOT been built or run.** The Docker engine could not be started on the development machine (see §7). Nothing here claims validated container support yet. This is local groundwork, not an AWS deployment.

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

## 5. Build and run (once the engine works)

```bash
docker compose build
docker compose up -d
docker compose ps          # both services should report "healthy"
# UI: http://localhost:8080   API docs: http://localhost:8000/docs
docker compose logs -f backend
docker compose down        # keeps the runtime volume; add -v to discard results
```

Validation checklist to run and record: frontend loads; `/api/v1/health/ready` = ready (checks `swmm`, `model`, `rainfall`, `data`, `storage`); scenario and GIS APIs; **Load verified demo result** (no SWMM needed); a real 1.00× run whose results match the native baseline within the result cross-check tolerances (a Linux/GCC build may differ from the Windows build in the last floating-point digits, so byte-identical output is not expected); a 1.25× run and comparison; flood, bottleneck, exposure and recommendation endpoints.

## 6. SWMM in the container

The engine is compiled from the official EPA source at the exact 5.2.4 tag commit (no substitute solver, no mock outputs). The backend's existing safeguards apply unchanged: engine version must be `5.2.4` in the report, model checksum, rainfall checksum and all result cross-checks. If the build or runtime ever fails, `/health/ready` reports `swmm: error`, simulation creation fails with `SWMM_UNAVAILABLE`, and the precomputed demo result still works because it does not execute SWMM.

## 7. Blocker encountered (2026-09-14)

- Docker CLI 29.7.2 and Docker Desktop 4.90.0 are installed (per-user install, `%LOCALAPPDATA%\Programs\DockerDesktop`), but the engine was stopped.
- Starting Docker Desktop failed: its backend crashed with `starting services: initializing Ingest server: listening on unix://…/Docker/run/sailor-ingest.sock: rename … sailor-ingest.sock.stale: The file cannot be accessed by the system.` Stale AF_UNIX socket placeholders in `%LOCALAPPDATA%\Docker\run` (`sailor-ingest.sock.stale`, `dockerInference.stale`, dated 2026-09-12) cannot be renamed or deleted from a normal process ("The file cannot be accessed by the system"). The `docker-desktop` WSL distribution stays `Stopped`.
- Not attempted (needs the user): rebooting Windows (normally releases the stale socket placeholders), Docker Desktop *Troubleshoot → Restart* or *Reset to factory defaults* (erases local images/volumes).
- Consequently none of the images were built, `runswmm` was not compiled for Linux, and the container checklist in §5 is still open. The native Windows execution path (`SWMM_EXECUTABLE=C:\Program Files\EPA SWMM 5.2.4 (64-bit)\runswmm.exe` in `backend/.env`) remains the verified path.

## 8. Known limitations

- Single backend replica (SQLite + in-process queue); horizontal scaling needs PostgreSQL and a job queue (later prompt).
- First requests after a fresh volume build GIS web assets and decision products (a few seconds).
- The frontend image needs internet access at build time for `npm ci`; the backend build needs GitHub access for the SWMM source.
