# ChennaiFlood-Twin

**AI-Powered Urban Flood Digital Twin and Decision Support System** · BCSE355L — Design of Smart Cities

A 100% software academic prototype for **Ward 176, Velachery, Chennai**. It is a 3D urban flood Digital Twin that combines EPA SWMM hydrological/hydraulic simulation with 3D geospatial visualisation in CesiumJS.

```text
GCC Ward 176 GIS  +  NASA GPM IMERG rainfall (Cyclone Michaung, Dec 2023)  +  Copernicus DEM
        ↓
EPA SWMM 5.2.4 (1D dynamic-wave drainage simulation)
        ↓
FastAPI backend: result parsing, flood influence zones, potential bottlenecks, exposure, recommendations, what-if scenarios
        ↓
React + TypeScript + CesiumJS: 3D Digital Twin, flood timeline, KPIs, charts, scenario comparison
```

> **What the results are.**
> - Everything on the timeline is **simulated by EPA SWMM** or **derived from SWMM output**. Nothing is a sensor reading, an observation or a forecast.
> - The shaded flood areas are *nearest-node influence zones* of overflowing drainage nodes. They are not a 2D flood surface, not an observed flood extent, and they carry no water depth.
> - The drainage model is an uncalibrated candidate with provisional outfalls.
> - "Simulated flooding volume" is a model diagnostic, not an observed volume.
> - 1.25× and 1.50× are what-if rainfall sensitivity runs, not forecasts.
> - No AI model generates results or recommendations; they are rule-based and traceable.
>
> See **Methodology & Limitations** in the app, and [`docs/`](docs).

---

# How to Run

There are two ways to run the project. Both start from the project root, **`F:\ChennaiFlood-Twin`**; use your own clone path if it is different.

| | Option A — Local development | Option B — Docker |
|---|---|---|
| Terminals | **2** (backend + frontend) | **1** |
| Open | <http://localhost:5173> | <http://localhost:8080> |
| SWMM engine | Windows EPA SWMM 5.2.4 install | Built from EPA source inside the image |
| Best for | Development, the fastest reload | A clean, reproducible run / presentation machine |

Commands below are for **Windows PowerShell**.

## A. Prerequisites

| Tool | Version | Needed for | Check |
|---|---|---|---|
| Git | any recent | cloning | `git --version` |
| **Python** | **3.13 or 3.14** (tested 3.14.7 locally, 3.13 in Docker) | Option A backend | `python --version` |
| **Node.js** | **22.19+ (22 LTS) or 24+** (tested 26.7.0 locally, 22.23 in Docker); npm is included (tested 11.19) | Option A frontend | `node -v` |
| **EPA SWMM 5.2.4** (64-bit, Windows installer) | exactly **5.2.4** | Option A, to *run* simulations | `Test-Path "C:\Program Files\EPA SWMM 5.2.4 (64-bit)\runswmm.exe"` |
| **Docker Desktop** | Engine running, Compose v2 (tested Docker 29.7.2, Compose 5.5.1) | Option B only | `docker compose version` |
| Internet access | — | map tiles (OpenStreetMap), first `npm ci`/`pip install`, first Docker build | — |

- **Without SWMM:** in Option A, the backend still starts and **Load verified demo result** works. Only *Run simulation* needs the SWMM executable.
- **Why those versions:**
  - Node: Vite 8 needs Node `^22.13 || >=24`, and the jsdom test tooling needs Node ≥ 22.19.
  - SWMM: the backend refuses results from any engine other than 5.2.4.
- **No accounts or tokens:** no API keys, cloud accounts or a Cesium ion token are needed.

## B. Option A — Local development (2 terminals)

### One-time setup

Run each part once, in a PowerShell window.

**Backend: create the virtual environment and install packages**

```powershell
cd F:\ChennaiFlood-Twin\backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

**Backend: point the app at SWMM.** Open `backend\.env` and set:

```text
SWMM_EXECUTABLE=C:\Program Files\EPA SWMM 5.2.4 (64-bit)\runswmm.exe
```

`backend\.env` is git-ignored and contains no secrets.

**Frontend: install packages**

```powershell
cd F:\ChennaiFlood-Twin\frontend
npm ci
```

### Every time

**Terminal 1 — Backend (FastAPI, port 8000)**

```powershell
cd F:\ChennaiFlood-Twin\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Wait for `Application startup complete.`

**Terminal 2 — Frontend (Vite dev server, port 5173)**

```powershell
cd F:\ChennaiFlood-Twin\frontend
npm run dev
```

**Open** <http://localhost:5173>. The dev server proxies `/api` to the backend on port 8000.

Backend API docs are at <http://127.0.0.1:8000/docs>. The readiness check <http://127.0.0.1:8000/api/v1/health/ready> should report `ready`, with `swmm: ok`.

**Stop:** press `Ctrl+C` in Terminal 2 and in Terminal 1.

## C. Option B — Docker (1 terminal)

Make sure Docker Desktop says **Engine running**.

**Terminal 1**

```powershell
cd F:\ChennaiFlood-Twin
docker compose up --build
```

- **First build:** takes several minutes. It compiles EPA SWMM 5.2.4 from the official source, installs Python packages and builds the frontend. Later starts reuse the cached images.
- **Ready when:** the log shows `Application startup complete.`, and `docker compose ps` in another window reports both services `healthy`.

**Open:**
- **App:** <http://localhost:8080>
- **API docs:** <http://localhost:8000/docs>
- **Health:** <http://localhost:8080/api/v1/health/ready>. The browser reaches the API through nginx at `/api`.

**Stop:**
- Press `Ctrl+C` in Terminal 1, then run:

  ```powershell
  cd F:\ChennaiFlood-Twin
  docker compose down
  ```

- **Stored results:** `docker compose down` keeps them in the `backend-runtime` volume. `docker compose down -v` also deletes them.
- **Background mode:** use `docker compose up --build -d`, then `docker compose logs -f` to follow logs.

Details are in [`docs/DOCKER_DEPLOYMENT.md`](docs/DOCKER_DEPLOYMENT.md).

## D. Demo mode (verified precomputed result)

**Load verified demo result** (left panel → *Simulation*) loads the archived EPA SWMM 5.2.4 output of the approved model for Michaung 2023.

- **Verification:** the output is byte-identical to a live Windows run and pinned by SHA-256 in `backend/config/demo.json`.
- **Processing:** it goes through the normal backend pipeline **without running SWMM**, so it works even if SWMM is unavailable.
- **Labelling:** it is labelled **Precomputed demonstration result**.
- **Reloading:** later loads re-use it instantly.
- **Reset demo** (header) restores the camera, layers, timestep and multiplier, and returns to this verified result once it has been loaded. No data is deleted.

## E. Recommended presentation launch

1. **15–30 minutes before**, start the stack you will present with (Option A or B). Open the app once and wait until the layer counts appear (buildings 6,428, drains 135).
2. Click **Load verified demo result**.
3. Prepare what-if results so nothing waits on SWMM during the talk.
   - In *Rainfall scenario*, choose **1.25×** and click **Run 1.25× what-if simulation** (about 15 s). If a stored run exists, **Load stored 1.25× result** re-uses it instead.
   - Repeat with **1.50×**.
   - Open the **Compare** tab once. The comparisons are then cached.
4. Click **Reset demo**. Keep this browser tab open; stored results survive restarts.

### Suggested flow

1. **Open:** the Ward 176 3D scene with terrain, buildings, roads and drains (**Layers**, **Map legend**).
2. **Rainfall scenario:** Michaung 2023 IMERG rainfall.
3. **Load verified demo result**, or **Run simulation** to show live progress.
4. **Timeline:** press ▶ to play, then **Go to Peak Flood** (03 Dec 2023 22:00 UTC). The heads-up display over the map shows the simulated time and rainfall intensity, and the rainfall visualisation over the scene follows it. Show the KPIs and the **rainfall / overflow chart** in the Flood tab.
5. **Hydraulics:** potential bottleneck **C169**, then **View on map**: the conduit is highlighted between its junctions J161 and J177, and the inspector explains which SWMM criteria were met.
6. **Exposure:** buildings in influence zones (783 at the peak).
7. **Actions:** the evidence-based recommendations.
7a. **Location:** open the *Location* tab, click a point in Ward 176 and press **Run Location Flood Check** (or **Check displayed result**). The panel shows the model-derived flood response around the pin: nearest drainage node, surrounding 250 m, peak time and nearby potential bottlenecks. It is not a property assessment.
8. **Scenarios:** switch to **1.25×** and load or run it. Then open the **Compare** tab: scenario overview chart (1.00× / 1.25× / 1.50×), new and persisting bottlenecks, and the comparison map layer.
9. **Methodology & Limitations:** it includes a *Presenter questions* section (for example "What exactly are the shaded flood polygons?").
10. **Reset demo.**

## F. Troubleshooting

| Problem | What to do |
|---|---|
| **Backend won't start** | Run the command from `F:\ChennaiFlood-Twin\backend`. Make sure `.venv` exists (see *One-time setup*). `ModuleNotFoundError` means the packages are missing: rerun `.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`. |
| `/health/ready` shows `swmm: error` | `SWMM_EXECUTABLE` in `backend\.env` must be the full path to `runswmm.exe` of **EPA SWMM 5.2.4**. The demo result still works without it. |
| **Frontend won't start** | Run the command from `F:\ChennaiFlood-Twin\frontend`. Check `node -v` (22.19+ or 24+). Delete `node_modules` and run `npm ci` again. |
| **Port already in use** (8000, 5173 or 8080) | Find the process with `netstat -ano \| findstr :8000` and close it (`Stop-Process -Id <PID>`). Common causes: an old uvicorn still running, or Docker using 8000 while you start Option A. Stop Docker with `docker compose down` before running Option A. |
| **Docker isn't running** (`error during connect` / `cannot find the file specified`) | Start Docker Desktop and wait for **Engine running**. If it will not start, restart Windows or use *Docker Desktop → Troubleshoot → Restart*. |
| **Simulation fails** | The panel shows the failed stage and error code. Check `/api/v1/health/ready`, and the backend terminal (or `docker compose logs backend`). Use **Retry**, or **Load verified demo result** to continue the demo. |
| **Header says "Backend offline"** | The backend is not reachable. Start or restart Terminal 1 (or `docker compose up`), then click **Retry**. Data already loaded stays visible meanwhile. |
| **3D view is blank or frozen** | If the toolbar shows *3D rendering stopped*, click **Resume rendering** or **Restart 3D viewer**; otherwise reload the page. Enable hardware acceleration in the browser. |
| **Stale containers or old UI in Docker** | Run `docker compose down`, then `docker compose up --build` (rebuilds changed images). For a completely fresh state including stored results: `docker compose down -v`, then `docker compose build --no-cache`, then `docker compose up`. |
| **Map tiles missing** | OpenStreetMap tiles need internet access; the GIS layers and results still load. |

## Tests

```powershell
cd F:\ChennaiFlood-Twin\backend
.venv\Scripts\python.exe -m pytest
```

This includes the real SWMM integration tests, which are skipped if SWMM is not configured.

```powershell
cd F:\ChennaiFlood-Twin\frontend
npm run typecheck
npm run lint
npm test
npm run build
```

---

## Repository

| Path | Contents |
|---|---|
| `backend/` | FastAPI modular monolith, SWMM runner, analysis methods, tests ([`backend/README.md`](backend/README.md)) |
| `frontend/` | React + TypeScript + CesiumJS Digital Twin ([`frontend/README.md`](frontend/README.md)) |
| `simulation/` | Approved SWMM model `ward176_hydraulic_reconstructed_candidate.inp` and the verified demo outputs (protected) |
| `data_processed/`, `data_raw/rainfall/`, `gis/` | Processed Ward 176 GIS, DEM, network and IMERG rainfall (protected) |
| `docs/` | Project context `00`–`10`, methods (flood, decision support, scenarios), Docker, performance, API contract, changelog |
| `compose.yaml` | Local container stack (backend + nginx frontend) |

## Method documentation

- [`docs/FLOOD_PROCESSING_METHOD.md`](docs/FLOOD_PROCESSING_METHOD.md): node flooding states and influence zones.
- [`docs/DECISION_SUPPORT_METHOD.md`](docs/DECISION_SUPPORT_METHOD.md): potential bottlenecks, exposure, recommendations, time-varying bottlenecks.
- [`docs/SCENARIO_ANALYSIS_METHOD.md`](docs/SCENARIO_ANALYSIS_METHOD.md): rainfall multiplier and comparison.
- [`docs/LOCATION_CHECK_METHOD.md`](docs/LOCATION_CHECK_METHOD.md): Location Flood Check (model-derived response around a selected point).
- [`docs/DOCKER_DEPLOYMENT.md`](docs/DOCKER_DEPLOYMENT.md), [`docs/PERFORMANCE_NOTES.md`](docs/PERFORMANCE_NOTES.md), [`docs/06_API_CONTRACT.md`](docs/06_API_CONTRACT.md), [`docs/CHANGELOG.md`](docs/CHANGELOG.md).

Data: GCC GIS · NASA GPM IMERG · Copernicus DEM GLO-30 · © OpenStreetMap contributors. EPA SWMM is public-domain software of the U.S. EPA.
