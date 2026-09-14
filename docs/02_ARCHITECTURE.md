# ChennaiFlood-Twin — System Architecture

## 1. Purpose

This document defines the **technical architecture** of ChennaiFlood-Twin.

It explains how the frontend, backend, simulation engine, geospatial data, processing pipeline, storage, and AWS deployment fit together.

This document should be read after:

```text
00_PROJECT_CONTEXT.md
01_PRODUCT_REQUIREMENTS.md
```

Those documents define what the project is and what it must do.

This document defines **how the system should be structured to do it**.

---

# 2. Architecture Goals

The architecture must prioritize:

1. Clear separation of responsibilities.
2. Reproducible simulation workflows.
3. Reliable communication between frontend and backend.
4. Efficient geospatial visualization.
5. Safe execution of SWMM.
6. Easy local development.
7. Straightforward AWS deployment.
8. Ability to add future scenarios without rewriting the system.
9. Ability to replace individual components without rewriting the entire application.
10. Academic/demo reliability over unnecessary infrastructure complexity.

The architecture should be simple enough to understand and robust enough to demonstrate an end-to-end Smart City system.

---

# 3. High-Level Architecture

The system is divided into six major functional layers:

```text
┌──────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                        │
│                    React + TypeScript                        │
│                                                              │
│  Dashboard │ Scenario Controls │ Timeline │ Analytics        │
│                    CesiumJS 3D Viewer                        │
└──────────────────────────────┬───────────────────────────────┘
                               │
                         HTTPS / JSON
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                         API LAYER                             │
│                  REST API / HTTP Interface                    │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                       APPLICATION BACKEND                     │
│                                                              │
│ Scenario Service │ Simulation Service │ Results Service      │
│ Risk Service     │ KPI Service        │ Recommendation       │
└──────────────────────────────┬───────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
┌───────────────────────────┐   ┌──────────────────────────────┐
│      SIMULATION LAYER     │   │     GEOSPATIAL PROCESSING    │
│                           │   │                              │
│      EPA SWMM 5.2.4      │   │ Flood depth/extent           │
│      Dynamic Wave         │   │ Spatial intersections        │
│                           │   │ Risk calculations             │
└──────────────┬────────────┘   └──────────────┬───────────────┘
               │                               │
               └───────────────┬───────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                         DATA LAYER                            │
│                                                              │
│ Raw data │ Processed GIS │ SWMM models │ Simulation results  │
│ Scenario metadata │ Derived geospatial products              │
└──────────────────────────────────────────────────────────────┘
```

---

# 4. Core Architectural Principle

The most important architectural rule is:

> **The frontend visualizes and interacts; the backend orchestrates and computes.**

The frontend should not become a second backend.

The backend should not become a rendering engine.

The simulation engine should remain independent of the UI.

---

# 5. Frontend Responsibilities

The frontend is responsible for:

- rendering the application UI,
- rendering the CesiumJS Digital Twin,
- requesting data from APIs,
- submitting simulation requests,
- displaying simulation status,
- controlling the timeline,
- visualizing flood results,
- displaying KPIs,
- displaying risk information,
- displaying bottlenecks,
- displaying recommendations,
- handling user interaction,
- managing client-side presentation state.

The frontend should **not**:

- execute SWMM,
- generate authoritative hydraulic model data,
- contain hardcoded simulation outputs,
- modify raw GIS data,
- calculate complex server-side risk metrics,
- contain AWS credentials,
- make direct database connections,
- bypass the API layer.

---

# 6. Backend Responsibilities

The backend is responsible for:

- API endpoints,
- request validation,
- scenario management,
- simulation orchestration,
- SWMM execution,
- SWMM input preparation where required,
- SWMM output parsing,
- result post-processing,
- geospatial processing,
- KPI generation,
- risk analysis,
- bottleneck analysis,
- recommendation generation,
- result storage/retrieval,
- error reporting,
- logging.

The backend is the authoritative application layer.

---

# 7. Simulation Engine

The simulation engine is:

> **EPA SWMM 5.2.4**

Current working model:

```text
simulation/
└── ward176_hydraulic_reconstructed_candidate.inp
```

The simulation engine should be treated as an external computational component from the application architecture's perspective.

The backend should invoke it rather than embedding SWMM logic throughout the application.

Conceptually:

```text
Backend
   │
   ├── Prepare input
   │
   ├── Execute SWMM
   │
   ├── Check exit status
   │
   ├── Parse report/output
   │
   └── Pass results to processing layer
```

---

# 8. Simulation Isolation

Each simulation should ideally have an isolated working directory.

Example:

```text
simulation_runs/
└── <simulation_id>/
    ├── input.inp
    ├── report.rpt
    ├── output.out
    ├── metadata.json
    └── processed/
```

The exact filesystem structure may change during implementation.

The important requirement is:

> **One simulation must not overwrite another simulation's files.**

This becomes especially important when simulations are executed concurrently in AWS.

---

# 9. Data Architecture

The project data should be separated into logical categories.

```text
data_raw/
    ↓
data_processed/
    ↓
simulation/
    ↓
derived results
    ↓
frontend-ready products
```

### Raw data

Original downloaded/source datasets.

These should be treated as immutable.

### Processed data

Cleaned, clipped, reprojected, or derived datasets prepared for modelling and visualization.

### Simulation data

SWMM input models and simulation artifacts.

### Derived results

Results produced from simulation and spatial processing.

---

# 10. Data Provenance

Every important derived dataset should have a traceable origin.

For example:

```text
GCC drain data
      ↓
processed drainage network
      ↓
SWMM model
      ↓
simulation
      ↓
flood result
      ↓
risk analysis
```

The application should never obscure whether information is:

- source data,
- processed data,
- model assumption,
- simulation output,
- or derived analysis.

Where practical, metadata should identify:
- source,
- processing step,
- timestamp/version,
- scenario,
- model version.

---

# 11. Geospatial Architecture

The geospatial workflow has three major stages:

```text
SOURCE GIS
    ↓
PROCESSING
    ↓
WEB VISUALIZATION
```

The project currently uses:

- GCC GIS data,
- Copernicus DEM,
- Ward 176 boundary,
- building polygons,
- road polygons,
- storm-water drains,
- generated subcatchments,
- reconstructed drainage network.

The backend/process layer should convert these into efficient web-consumable representations where required.

---

# 12. Coordinate Reference Systems

The project uses both geographic and projected coordinate systems.

### Geographic

EPSG:4326 is used by some source and web-oriented datasets.

### Projected

EPSG:32644 should be used where metric spatial calculations are required for the Ward 176 modelling workflow.

The architecture must not silently mix coordinate systems.

Before spatial calculations such as:
- distances,
- areas,
- buffering,
- intersection thresholds,
- flood polygons,

the code must know which CRS the data is in.

---

# 13. 3D Digital Twin Architecture

CesiumJS is the primary 3D visualization engine.

The conceptual scene is:

```text
Cesium Viewer
│
├── Terrain
├── Ward Boundary
├── Buildings
├── Roads
├── Storm-water Drains
├── Flood Extent
├── Flood Depth
├── Risk Areas
└── Bottleneck Highlights
```

The scene should use a combination of:

- static geospatial assets,
- dynamically loaded simulation products,
- interactive entities/primitives as appropriate.

Do not force every dataset into the same Cesium representation.

Choose the most appropriate representation based on:
- geometry size,
- update frequency,
- interaction requirements,
- performance.

---

# 14. Static vs Dynamic Data

A key distinction is:

### Static data

Changes rarely:

- ward boundary,
- terrain,
- buildings,
- roads,
- base drainage network.

These should be cached aggressively.

### Dynamic data

Changes per simulation:

- flood extent,
- flood depth,
- risk,
- hydraulic state,
- scenario KPIs,
- timeline values.

These should be loaded according to the selected simulation.

Conceptually:

```text
STATIC
  ├── Terrain
  ├── Buildings
  ├── Roads
  └── Drains

DYNAMIC
  ├── Simulation
  ├── Flood
  ├── Risk
  ├── KPIs
  └── Timeline
```

---

# 15. Simulation Lifecycle

The complete simulation lifecycle should follow:

```text
User selects scenario
        ↓
POST simulation request
        ↓
Backend validates request
        ↓
Create simulation ID
        ↓
Prepare isolated simulation workspace
        ↓
Prepare SWMM input
        ↓
Run SWMM
        ↓
Check execution
        ↓
Parse SWMM results
        ↓
Generate derived flood products
        ↓
Calculate KPIs
        ↓
Calculate risk/bottlenecks
        ↓
Generate recommendations
        ↓
Persist results
        ↓
Mark simulation COMPLETED
        ↓
Frontend loads results
```

If any critical step fails:

```text
FAILED
```

with a meaningful error message.

---

# 16. Simulation State Machine

The backend should use an explicit simulation state.

Recommended states:

```text
CREATED
VALIDATING
PREPARING
RUNNING
PROCESSING
COMPLETED
FAILED
```

The frontend should poll or otherwise retrieve the simulation state.

The frontend should not infer completion merely because a request has returned successfully.

A simulation request can be accepted while the simulation itself is still running.

---

# 17. API Boundary

The API is the formal boundary between frontend and backend.

Conceptually:

```text
React / CesiumJS
        │
        │ HTTPS + JSON
        ▼
      REST API
        │
        ▼
Application Services
```

The frontend should know the API contract.

The frontend should not know:
- SWMM command-line details,
- filesystem paths,
- server-side processing implementation,
- database schema,
- AWS internal architecture.

Those are backend concerns.

---

# 18. Recommended Service Separation

The backend should logically separate services/modules even if the initial implementation is a single deployable application.

Suggested services:

```text
Scenario Service
Simulation Service
Results Service
Geospatial Service
KPI Service
Risk Service
Recommendation Service
```

### Scenario Service

Responsible for:
- available scenarios,
- scenario metadata,
- validation.

### Simulation Service

Responsible for:
- simulation creation,
- SWMM execution,
- simulation status.

### Results Service

Responsible for:
- SWMM result retrieval,
- time-series retrieval,
- result metadata.

### Geospatial Service

Responsible for:
- flood spatial products,
- spatial queries,
- asset intersections.

### KPI Service

Responsible for:
- rainfall metrics,
- flood metrics,
- drainage metrics.

### Risk Service

Responsible for:
- risk calculations,
- ranking,
- spatial risk products.

### Recommendation Service

Responsible for:
- turning model evidence into understandable recommendations.

These do not necessarily need separate microservices.

For the MVP, a **modular monolith** is preferred.

---

# 19. Modular Monolith Principle

Do not prematurely create many independently deployed services.

Preferred initial architecture:

```text
                Backend Application
┌────────────────────────────────────────┐
│                                        │
│ Scenario                               │
│ Simulation                             │
│ Results                                │
│ Geospatial                             │
│ KPI                                    │
│ Risk                                   │
│ Recommendation                         │
│                                        │
└────────────────────────────────────────┘
```

The modules should have clear boundaries internally.

If scaling requirements later justify separate services, they can be extracted.

---

# 20. Storage Architecture

The application needs to store several types of information.

### Object/file storage

Best suited for:

- GIS datasets,
- GeoJSON,
- terrain assets,
- SWMM input files,
- SWMM reports,
- SWMM output files,
- processed flood products.

AWS S3 is the preferred target for cloud object storage.

### Structured metadata

Potentially store:

- simulation metadata,
- scenario metadata,
- status,
- KPI summaries,
- timestamps.

A relational or key-value database can be introduced if needed.

Do not introduce a database simply because the architecture diagram contains one.

---

# 21. Local Development Architecture

The project must work locally before cloud deployment.

Conceptually:

```text
Browser
   │
   ▼
Frontend dev server
   │
   ▼
Backend dev server
   │
   ├── SWMM executable
   ├── local project data
   └── local simulation results
```

Local development should not require AWS for every iteration.

This is important for:
- rapid vibecoding,
- debugging,
- offline development,
- and academic demonstrations.

---

# 22. Cloud Architecture

The target AWS deployment can follow:

```text
                    INTERNET
                       │
                       ▼
                  CloudFront
                       │
                       ▼
                Frontend / S3
                       │
                     HTTPS
                       │
                       ▼
                  API Gateway
                       │
                       ▼
               Backend Compute
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
         S3         Database       SWMM
      Data/Files    Metadata      Compute
          │                         │
          └────────────┬────────────┘
                       ▼
                 Processed Results
                       │
                       ▼
                  Frontend API
```

The exact AWS services may change.

---

# 23. AWS Compute Considerations

SWMM execution is computational work.

Do not assume that every simulation should run in a short-lived serverless function.

The implementation should choose the compute mechanism based on:
- simulation duration,
- executable availability,
- memory,
- filesystem requirements,
- concurrency,
- deployment complexity.

For the academic MVP, a containerized backend/worker is acceptable and may be simpler than forcing SWMM into Lambda.

The architecture should remain AWS-compatible without making unsupported claims about exact deployment limits.

---

# 24. Asynchronous Simulation Architecture

Simulation execution should be treated as potentially asynchronous.

Recommended conceptual flow:

```text
POST /simulations
       ↓
return simulation_id
       ↓
background simulation
       ↓
frontend checks status
       ↓
COMPLETED
       ↓
frontend requests results
```

This prevents the browser from being blocked by a long-running simulation request.

---

# 25. Result Processing Pipeline

SWMM output should not be sent directly to Cesium.

The processing pipeline should be:

```text
SWMM output
    ↓
Parse
    ↓
Normalize
    ↓
Validate
    ↓
Spatially associate
    ↓
Generate flood products
    ↓
Generate KPIs
    ↓
Generate risk
    ↓
Generate bottlenecks
    ↓
Generate recommendations
    ↓
API-ready results
```

This ensures the frontend receives clean application-level information rather than raw SWMM internals.

---

# 26. Flood Visualization Architecture

The flood visualization should be derived from the simulation results using a documented method.

Conceptually:

```text
SWMM hydraulic results
       ↓
Node/link conditions
       ↓
Spatial flood estimation / processing
       ↓
Flood-depth representation
       ↓
Flood extent
       ↓
Time-indexed spatial products
       ↓
CesiumJS
```

The exact flood-depth interpolation/representation method must be documented before being treated as scientifically meaningful.

Do not claim that SWMM directly generated a complete 2D/3D flood surface.

---

# 27. Timeline Architecture

The timeline should be driven by simulation timestamps.

Conceptually:

```text
Simulation
│
├── t0 → results
├── t1 → results
├── t2 → results
├── t3 → results
└── ...
```

The frontend timeline should control which time slice is displayed.

The backend should provide either:
- time-indexed results,
- or a compact representation from which time slices can be reconstructed.

The frontend should not repeatedly request huge datasets for every small timeline movement.

---

# 28. Risk Architecture

Risk analysis should occur server-side.

Conceptually:

```text
Simulation outputs
       +
Exposure data
       +
Drainage indicators
       ↓
Risk calculation
       ↓
Risk score/category
       ↓
Spatial risk product
       ↓
API
       ↓
Cesium + Dashboard
```

Risk formulas must be explicit and versioned.

Do not hardcode unexplained magic numbers.

---

# 29. Recommendation Architecture

Recommendations should be generated from structured evidence.

Conceptually:

```text
High flood depth
       +
Long duration
       +
Asset exposure
       +
Drainage stress
       ↓
Recommendation rules
       ↓
Prioritized actions
```

The initial implementation can use deterministic rules.

An AI/LLM layer is optional and should not be required for the core MVP.

If an AI component is later added, it should explain existing structured evidence rather than inventing facts.

---

# 30. Caching Strategy

Static data should be cached.

Examples:

- terrain,
- building geometry,
- road geometry,
- base drainage network,
- ward boundary.

Simulation results should be cached by simulation ID.

Example:

```text
simulation_id
      ↓
cached results
```

Repeated requests for the same completed simulation should not rerun SWMM.

---

# 31. Versioning

Simulation results should be associated with:

- scenario ID,
- model version,
- processing version,
- creation timestamp.

Example metadata:

```json
{
  "simulationId": "sim-001",
  "scenarioId": "michaung-2023",
  "modelVersion": "ward176-hydraulic-reconstructed-v1",
  "status": "completed"
}
```

If the SWMM model changes, the application should be able to distinguish old and new results.

---

# 32. Error Handling Architecture

Errors should be handled at every layer.

### Frontend

Show:
- loading state,
- error state,
- retry where appropriate.

### API

Return:
- meaningful HTTP status,
- machine-readable error code,
- human-readable message.

### Backend

Log:
- request,
- simulation ID,
- error,
- relevant stage.

### Simulation

Capture:
- executable failure,
- invalid input,
- SWMM warnings,
- missing output,
- parsing failure.

Do not expose raw server filesystem paths to the user.

---

# 33. Logging

Every simulation should have a traceable execution history.

At minimum log:

```text
simulation_id
scenario_id
start_time
end_time
status
simulation stage
error if any
model version
processing version
```

Avoid logging:
- secrets,
- credentials,
- unnecessary personal data.

---

# 34. Security Architecture

Even though this is an academic prototype, follow basic security practices.

Never:

- hardcode AWS credentials,
- commit `.env`,
- expose database credentials,
- expose private filesystem paths,
- trust arbitrary user-supplied file paths,
- execute arbitrary shell commands derived directly from user input.

Simulation scenarios should use validated identifiers/configuration.

---

# 35. Configuration

Environment-specific configuration should be separated from source code.

Examples:

```text
SWMM_EXECUTABLE
DATA_ROOT
RESULTS_ROOT
API_BASE_URL
S3_BUCKET
DATABASE_URL
```

Use environment variables or appropriate configuration files.

Do not hardcode local Windows paths such as:

```text
F:\ChennaiFlood-Twin\
```

inside application logic.

The existing path is project documentation context, not a portable runtime path.

---

# 36. Frontend ↔ Backend Data Flow

Typical flow:

```text
User
 ↓
React component
 ↓
API client
 ↓
REST endpoint
 ↓
Backend service
 ↓
Data/simulation processing
 ↓
JSON response
 ↓
Frontend state
 ↓
Cesium/dashboard
```

The frontend should use a centralized API client rather than scattered `fetch()` calls throughout components.

---

# 37. Static Asset Flow

Static Digital Twin assets should follow:

```text
Source datasets
      ↓
Processing pipeline
      ↓
Web-ready assets
      ↓
Object storage / static server
      ↓
CesiumJS
```

Large datasets should not automatically be embedded into JavaScript bundles.

---

# 38. Deployment Environments

At minimum, conceptually support:

```text
Development
Production
```

Development:
- local filesystem,
- local SWMM,
- local backend,
- local frontend.

Production:
- AWS storage,
- AWS compute,
- deployed frontend,
- deployed API,
- production simulation execution.

Do not require production infrastructure to test basic frontend functionality.

---

# 39. Testing Architecture

Testing should exist at multiple levels.

### Unit tests

For:
- KPI calculations,
- risk scoring,
- data transformations,
- validation.

### Backend/API tests

For:
- scenario endpoints,
- simulation lifecycle,
- results endpoints,
- error handling.

### Integration tests

For:

```text
API → simulation → result parsing
```

### Frontend tests

For:
- component rendering,
- API state handling,
- timeline behaviour,
- layer controls.

### End-to-end test

At least one complete workflow should work:

```text
Select scenario
→ Run simulation
→ Complete
→ Load results
→ Show flood
→ Show KPIs
```

---

# 40. Architectural Anti-Patterns

Avoid:

### 40.1 Frontend doing backend work

Bad:

```text
React
 └── directly executes SWMM
```

### 40.2 Hardcoded results

Bad:

```javascript
const floodDepth = 1.42;
```

when the value is supposed to come from the simulation.

### 40.3 Giant monolithic component

Bad:

```text
App.tsx
 └── 2000 lines containing everything
```

### 40.4 Premature microservices

Bad:

```text
7 AWS services
12 independently deployed APIs
```

before the MVP even works locally.

### 40.5 Hidden data transformations

Never silently modify:
- elevations,
- drainage topology,
- rainfall,
- spatial coordinates,
- model parameters.

---

# 41. Architecture Change Rule

Before making a major architectural change, ask:

1. Does it solve a real current problem?
2. Is there a simpler solution?
3. Does it break the API contract?
4. Does it change scientific assumptions?
5. Does it affect existing simulation reproducibility?
6. Does the documentation need updating?

If yes, update the appropriate architecture/context document.

---

# 42. Current Architecture Baseline

At the beginning of Digital Twin implementation, the expected baseline is:

```text
Frontend
  React + TypeScript + CesiumJS

Backend
  Modular application/API

Simulation
  EPA SWMM 5.2.4

Spatial Processing
  GIS/geospatial processing pipeline

Data
  Existing Ward 176 datasets

Cloud Target
  AWS

Primary Model
  ward176_hydraulic_reconstructed_candidate.inp
```

This baseline should remain stable unless a justified engineering decision requires change.

---

# 43. Recommended Initial Implementation Architecture

For the first working implementation, prefer:

```text
                    ┌──────────────────┐
                    │     Browser      │
                    │ React + Cesium   │
                    └────────┬─────────┘
                             │
                            API
                             │
                    ┌────────▼─────────┐
                    │     Backend      │
                    │  Modular Monolith│
                    └────────┬─────────┘
                             │
             ┌───────────────┼────────────────┐
             │               │                │
             ▼               ▼                ▼
          Scenario        SWMM Runner     Postprocess
             │               │                │
             └───────────────┼────────────────┘
                             ▼
                       Results Store
```

This is intentionally simpler than a full enterprise architecture.

It is appropriate for a vibecoded academic MVP and can evolve later.

---

# 44. Architecture Success Criteria

The architecture is successful when:

1. The frontend can run independently of the SWMM internals.
2. The backend can execute a scenario without frontend knowledge of implementation details.
3. SWMM results can be processed into application-level results.
4. Cesium can consume spatial results efficiently.
5. Static and dynamic data are separated.
6. Simulations are reproducible.
7. Multiple simulations do not overwrite each other.
8. The system can run locally.
9. The system has a clear path to AWS.
10. A change in one subsystem does not require rewriting the entire application.

---

# 45. Final Architectural Principle

The entire system should preserve this chain:

```text
SOURCE DATA
    ↓
PROCESSED DATA
    ↓
SCENARIO
    ↓
SWMM SIMULATION
    ↓
RESULT PROCESSING
    ↓
API
    ↓
3D DIGITAL TWIN
    ↓
RISK + DECISION SUPPORT
```

Every implementation decision should strengthen this chain.

If a proposed feature makes the system more complicated without improving this chain, it should be questioned before implementation.
