# ChennaiFlood-Twin — Backend Design Specification

## 1. Purpose

This document defines how the **backend of ChennaiFlood-Twin** should be designed and implemented.

It is the implementation guide between the high-level architecture and the detailed API contract.

Read this document together with:

```text
00_PROJECT_CONTEXT.md
01_PRODUCT_REQUIREMENTS.md
02_ARCHITECTURE.md
03_DATA_AND_GIS.md
04_SWMM_MODEL.md
```

This document defines:

- backend responsibilities,
- project structure,
- service/module boundaries,
- simulation orchestration,
- SWMM execution,
- result processing,
- data access,
- configuration,
- validation,
- error handling,
- logging,
- security,
- local development,
- and AWS deployment considerations.

The backend should be a **modular monolith for the MVP**, not a collection of prematurely separated microservices.

---

# 2. Backend Mission

The backend is the bridge between:

```text
USER INTERFACE
      ↓
     API
      ↓
APPLICATION LOGIC
      ↓
SWMM + GIS PROCESSING
      ↓
RESULTS
      ↓
API
      ↓
DIGITAL TWIN
```

Its job is to transform a user scenario request into a reproducible simulation and useful application-level results.

The backend must hide implementation details from the frontend.

The frontend should not need to know:

- where SWMM is installed,
- where input files are stored,
- how `.inp` files are generated,
- how `.rpt`/`.out` files are parsed,
- how flood products are derived,
- how risk scores are calculated,
- or where AWS storage resides.

---

# 3. Backend Design Principles

The following principles are mandatory.

## 3.1 Backend owns computation

Simulation, processing, KPI calculation, risk analysis, and recommendation logic belong in the backend.

## 3.2 Frontend owns presentation

The frontend consumes backend results and renders them.

## 3.3 Preserve the model baseline

The master SWMM model must never be modified directly by a normal simulation request.

## 3.4 Make simulations reproducible

A simulation must be associated with its:

- scenario,
- model version,
- processing version,
- input,
- outputs,
- timestamps,
- status.

## 3.5 Prefer simple architecture

Use a modular monolith first.

Do not create microservices unless a real requirement emerges.

## 3.6 Never fabricate data

Missing GIS/hydraulic information must not be invented to make a simulation or visualization appear complete.

## 3.7 Fail explicitly

Simulation failures, processing failures, missing files, and invalid requests must produce explicit errors.

## 3.8 Keep source data immutable

Never overwrite `data_raw/` during application execution.

---

# 4. Recommended Backend Technology

The backend technology may be finalized during implementation, but the preferred direction is:

> **Python-based backend**

Reasons:

- strong geospatial ecosystem,
- straightforward SWMM process integration,
- strong data-processing libraries,
- easy CSV/JSON/GeoJSON handling,
- suitable for scientific processing,
- straightforward AWS container deployment.

A practical stack is:

```text
Python
FastAPI
Pydantic
Uvicorn
GeoPandas
Shapely
Rasterio
Pandas
```

For SWMM execution, use the installed EPA SWMM executable as an external process unless a verified Python SWMM integration is deliberately adopted.

Do not add libraries merely because they are popular. Every dependency should have a purpose.

---

# 5. Recommended Project Structure

The backend should be organized approximately as:

```text
backend/
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   ├── scenarios.py
│   │   │   ├── simulations.py
│   │   │   ├── results.py
│   │   │   ├── flood.py
│   │   │   ├── risk.py
│   │   │   └── assets.py
│   │   │
│   │   └── dependencies.py
│   │
│   ├── services/
│   │   ├── scenario_service.py
│   │   ├── simulation_service.py
│   │   ├── result_service.py
│   │   ├── geospatial_service.py
│   │   ├── kpi_service.py
│   │   ├── risk_service.py
│   │   └── recommendation_service.py
│   │
│   ├── simulation/
│   │   ├── runner.py
│   │   ├── input_builder.py
│   │   ├── parser.py
│   │   └── validator.py
│   │
│   ├── processing/
│   │   ├── flood.py
│   │   ├── exposure.py
│   │   ├── risk.py
│   │   └── spatial.py
│   │
│   ├── models/
│   │   ├── scenario.py
│   │   ├── simulation.py
│   │   ├── results.py
│   │   └── risk.py
│   │
│   ├── repositories/
│   │   ├── scenarios.py
│   │   ├── simulations.py
│   │   └── results.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   │
│   └── utils/
│       ├── filesystem.py
│       ├── subprocess.py
│       └── geospatial.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── api/
│
├── requirements.txt
├── .env.example
└── README.md
```

This is a recommended structure, not a requirement that every file must exist immediately.

---

# 6. Layer Responsibilities

The backend should have clear conceptual layers.

```text
API
 ↓
SERVICE
 ↓
PROCESSING / DOMAIN
 ↓
REPOSITORY / DATA
```

### API layer

Handles:

- HTTP,
- request parsing,
- response serialization,
- status codes.

### Service layer

Handles:

- application workflows,
- orchestration,
- business logic.

### Processing/domain layer

Handles:

- SWMM processing,
- GIS processing,
- KPI calculations,
- risk calculations.

### Repository/data layer

Handles:

- reading/writing metadata,
- object storage,
- database access where applicable.

---

# 7. API Layer Rules

API route handlers should be thin.

Bad:

```text
POST /simulations
    ↓
300 lines of SWMM + GIS + business logic
```

Good:

```text
POST /simulations
    ↓
validate request
    ↓
simulation_service.create(...)
```

The route should not directly contain:

- subprocess logic,
- large GIS operations,
- SWMM parsing,
- risk formulas.

---

# 8. Scenario Service

The scenario service manages rainfall/scenario definitions.

Responsibilities:

- list available scenarios,
- retrieve scenario metadata,
- validate scenario IDs,
- validate scenario parameters,
- resolve the rainfall input.

Initial scenario:

```text
michaung-2023
```

Metadata should include information such as:

```text
scenario_id
name
event
source
start_time
end_time
interval
total_rainfall_mm
peak_intensity_mm_hr
```

The scenario service should not execute SWMM.

---

# 9. Simulation Service

The simulation service is the main orchestration layer.

Responsibilities:

1. Create simulation ID.
2. Validate scenario.
3. resolve model version.
4. create isolated run directory.
5. prepare input.
6. execute SWMM.
7. detect success/failure.
8. parse output.
9. invoke post-processing.
10. calculate KPIs.
11. calculate risk.
12. calculate bottlenecks.
13. generate recommendations.
14. persist results.
15. update status.

Conceptually:

```text
create_simulation()
       ↓
validate()
       ↓
prepare()
       ↓
run_swmm()
       ↓
parse()
       ↓
postprocess()
       ↓
analyze()
       ↓
persist()
       ↓
complete()
```

---

# 10. Simulation State Machine

Use explicit states:

```text
CREATED
   ↓
VALIDATING
   ↓
PREPARING
   ↓
RUNNING
   ↓
PROCESSING
   ↓
COMPLETED
```

Failure from any stage should transition to:

```text
FAILED
```

The backend should record the stage at which failure occurred.

---

# 11. Simulation IDs

Every simulation must receive a unique ID.

Example:

```text
sim-20260913-001
```

or a UUID.

UUIDs are preferred for production/cloud environments.

The ID is used to associate:

- input,
- output,
- logs,
- metadata,
- KPIs,
- flood products,
- risk products.

---

# 12. Simulation Isolation

Every simulation must have its own workspace.

Example:

```text
simulation_runs/
└── <simulation_id>/
    ├── input.inp
    ├── report.rpt
    ├── output.out
    ├── stdout.log
    ├── stderr.log
    ├── metadata.json
    └── processed/
        ├── flood_extent.geojson
        ├── flood_depth.geojson
        ├── risk.geojson
        ├── bottlenecks.geojson
        └── kpis.json
```

The exact artifact set can evolve.

The important rule is:

> **Simulation runs must never overwrite each other.**

---

# 13. Master Model Protection

The master model:

```text
simulation/ward176_hydraulic_reconstructed_candidate.inp
```

must be treated as read-only during normal execution.

Workflow:

```text
MASTER MODEL
     ↓
COPY / CONTROLLED DERIVATION
     ↓
SCENARIO INPUT
     ↓
SIMULATION
```

Never edit the master `.inp` because a user clicked "Run Simulation".

---

# 14. Scenario Input Builder

The input builder creates a simulation-specific SWMM input.

For the initial historical scenario, this may simply involve copying the baseline model and ensuring the expected rainfall input is available.

For future scenario customization, it may:

- replace rainfall series,
- alter controlled scenario parameters,
- generate scenario metadata.

Any parameter changed from baseline must be explicit.

---

# 15. Scenario Override Rules

Scenario overrides must be:

- validated,
- explicit,
- reproducible,
- isolated.

Never allow arbitrary user input to modify arbitrary SWMM sections.

Bad:

```text
user sends:
section = "[JUNCTIONS]"
value = arbitrary text
```

Good:

```text
user sends:
rainfall_multiplier = 1.20
```

and the backend knows exactly how that parameter is translated into the model.

---

# 16. SWMM Runner

The SWMM runner is responsible only for executing SWMM and collecting execution information.

Responsibilities:

- locate executable,
- execute command,
- enforce timeout,
- capture stdout/stderr,
- return exit status,
- verify expected output files.

It should not calculate flood risk.

Conceptually:

```python
result = swmm_runner.run(
    input_file=...,
    report_file=...,
    output_file=...
)
```

The runner should be independently testable.

---

# 17. Subprocess Safety

Never construct arbitrary shell commands directly from user input.

Use structured subprocess arguments.

Validate:

- executable path,
- input path,
- output path,
- timeout.

Never accept a user-provided executable path through the public API.

---

# 18. SWMM Execution Failure

A simulation should fail cleanly if:

- executable is missing,
- input file is missing,
- SWMM exits unsuccessfully,
- output file is missing,
- report is missing,
- timeout occurs,
- output cannot be parsed.

The backend should retain the execution logs for debugging.

---

# 19. SWMM Parser

The parser converts SWMM output into structured application data.

Potential outputs:

```text
system results
subcatchment results
node time series
link time series
simulation metadata
warnings
```

The parser should not modify the underlying output.

---

# 20. Parser Validation

After parsing:

```text
[ ] expected sections present
[ ] timestamps valid
[ ] units known
[ ] numeric values parse correctly
[ ] no unexpected nulls
[ ] node IDs recognized
[ ] link IDs recognized
[ ] simulation ID attached
```

Parsing failures should be explicit.

Never silently substitute zero for an unparseable value.

---

# 21. Result Service

The result service provides application-level access to simulation results.

Responsibilities:

- retrieve simulation summary,
- retrieve time series,
- retrieve flood products,
- retrieve KPIs,
- retrieve risk,
- retrieve bottlenecks,
- retrieve recommendations.

The result service should not force the frontend to understand raw SWMM output formats.

---

# 22. Geospatial Service

The geospatial service handles spatial operations required by the application.

Potential responsibilities:

- load project spatial data,
- spatial intersections,
- asset exposure,
- coordinate transformations,
- flood spatial processing,
- web-ready product generation.

The service should explicitly track CRS.

---

# 23. CRS Handling

All geospatial functions must know their input CRS.

For metric calculations, use an appropriate projected CRS such as:

```text
EPSG:32644
```

where appropriate.

For web-facing geographic data, use:

```text
EPSG:4326
```

where appropriate.

Do not blindly convert everything to one CRS.

The appropriate CRS depends on the operation.

---

# 24. Flood Processing Service

The flood processing service converts hydraulic results into spatial products.

Conceptually:

```text
SWMM node/link results
       +
Terrain
       +
Urban spatial data
       ↓
Flood processing
       ↓
Flood depth / extent
```

The exact scientific method must be documented separately when implemented.

The service must record that the resulting flood surface is **derived/modelled**, not directly observed.

---

# 25. Flood Product Formats

Potential products include:

```text
flood_extent.geojson
flood_depth.geojson
flood_timeseries.json
```

For large or high-frequency products, other formats may be introduced.

The frontend should consume optimized products rather than raw SWMM files.

---

# 26. Time-Series Processing

SWMM results contain multiple timestamps.

The backend should normalize them into a consistent timeline.

Example:

```json
{
  "time": "2023-12-03T12:00:00",
  "nodes": {...},
  "links": {...}
}
```

The exact response structure belongs in:

```text
06_API_CONTRACT.md
```

Do not independently invent competing API formats.

---

# 27. KPI Service

The KPI service computes high-level metrics.

Potential metrics:

### Rainfall

- total rainfall,
- peak rainfall,
- duration.

### Flood

- maximum simulated depth,
- affected area,
- affected buildings,
- affected roads,
- flood duration where defensible.

### Drainage

- stressed links,
- flooded nodes,
- potential bottlenecks.

All KPI calculations should have clear formulas and units.

---

# 28. KPI Provenance

Every KPI should be traceable to:

```text
source data
+
simulation
+
processing method
```

If a KPI is model-derived, the UI should not imply it is measured.

---

# 29. Risk Service

The risk service converts simulation/exposure information into a structured risk representation.

Conceptually:

```text
Flood severity
      +
Exposure
      +
Drainage stress
      ↓
Risk score/category
```

The exact scoring method must be documented and versioned.

Avoid unexplained magic thresholds.

---

# 30. Risk Output

Potential output:

```json
{
  "locationId": "...",
  "riskLevel": "HIGH",
  "score": 0.82,
  "drivers": [
    "high simulated depth",
    "building exposure"
  ]
}
```

The exact contract belongs in `06_API_CONTRACT.md`.

---

# 31. Bottleneck Service

Potential drainage bottlenecks should be generated from hydraulic evidence.

Potential inputs:

- flow,
- conduit capacity,
- surcharge,
- hydraulic stress,
- repeated flooding relationships.

The service should return evidence alongside the classification where practical.

Example:

```text
Potential bottleneck
Link: C162
Reason: high hydraulic stress
```

A model-derived bottleneck is not automatically a confirmed physical infrastructure defect.

---

# 32. Recommendation Service

The recommendation service converts structured findings into decision-support actions.

The initial implementation should preferably use deterministic rules.

Example:

```text
IF high simulated depth
AND high building exposure
THEN
  recommend priority flood-mitigation assessment
```

Recommendations should reference their drivers.

Do not invent recommendations unrelated to model evidence.

---

# 33. Optional AI Layer

An AI/LLM layer may be added later.

If added, it should primarily:

- explain results,
- summarize findings,
- translate technical outputs into plain language,
- answer questions about already-generated results.

It should not:

- invent flood measurements,
- invent infrastructure,
- override the hydraulic model,
- create unsupported claims.

The core product must work without an AI service.

---

# 34. Repository Layer

Repositories abstract storage.

Possible repositories:

```text
ScenarioRepository
SimulationRepository
ResultRepository
```

They may initially use local filesystem/JSON.

Later they may use:

- S3,
- DynamoDB,
- PostgreSQL/RDS,
- another appropriate storage system.

Services should not depend heavily on the storage implementation.

---

# 35. Local Storage Strategy

For local MVP development, a simple filesystem-backed store is acceptable.

Example:

```text
backend/data/
backend/simulation_runs/
```

Do not commit generated simulation outputs to source control unless deliberately required.

---

# 36. Cloud Storage Strategy

For AWS:

```text
S3
 ├── static/
 ├── scenarios/
 ├── models/
 ├── simulations/
 │   └── <simulation_id>/
 └── products/
```

Exact bucket/key organization may evolve.

The important principle is that large artifacts belong in object storage rather than API responses.

---

# 37. Metadata Storage

Structured metadata can initially be stored as JSON.

If database functionality becomes useful, use a database for:

- simulation metadata,
- status,
- scenario metadata,
- KPI summaries,
- indexes.

Do not put large GeoJSON or SWMM output blobs into a relational database unnecessarily.

---

# 38. Background Execution

SWMM simulations should preferably execute asynchronously.

Recommended workflow:

```text
POST /simulations
       ↓
create simulation
       ↓
return simulation_id
       ↓
background worker/process
       ↓
RUNNING
       ↓
PROCESSING
       ↓
COMPLETED
```

The HTTP request should not remain open for the entire simulation if the simulation can take substantial time.

---

# 39. Local Async Strategy

For local development, the first implementation can use a simple background execution mechanism.

Possible approaches include:

- process/thread background execution,
- a lightweight task queue,
- a dedicated local worker.

Do not introduce a distributed queue unless the project actually needs it.

The architecture should preserve the ability to replace the worker later.

---

# 40. AWS Async Strategy

For cloud deployment, simulation execution may use:

- containerized worker,
- ECS/Fargate,
- AWS Batch,
- or another appropriate compute mechanism.

Do not force SWMM into Lambda simply because Lambda is serverless.

The correct choice depends on:
- runtime,
- executable packaging,
- memory,
- filesystem needs,
- simulation duration,
- concurrency.

---

# 41. Simulation Concurrency

The backend must prevent simulations from corrupting each other.

Each run needs:

```text
unique simulation ID
unique workspace
unique output filenames
```

If concurrency is not supported initially, explicitly serialize simulations rather than pretending to support concurrent execution.

---

# 42. Configuration

Use environment-based configuration.

Example:

```text
APP_ENV
API_HOST
API_PORT
SWMM_EXECUTABLE
PROJECT_ROOT
DATA_ROOT
SIMULATION_ROOT
RESULTS_ROOT
S3_BUCKET
DATABASE_URL
```

The exact variable names can evolve.

Never hardcode:

```text
F:\ChennaiFlood-Twin\
```

into application logic.

---

# 43. Environment Files

Provide:

```text
.env.example
```

with placeholder values.

Never commit actual:

- credentials,
- API keys,
- AWS secrets,
- database passwords.

---

# 44. Application Startup

The application should:

1. load configuration,
2. validate required configuration,
3. initialize logging,
4. initialize repositories/services,
5. expose health endpoint.

If a required dependency is missing, fail clearly.

---

# 45. Health Endpoint

Provide a basic endpoint such as:

```text
GET /health
```

It should indicate whether the backend is alive.

A deeper readiness check may verify:

- SWMM executable availability,
- required data directories,
- storage availability.

Do not make the basic health endpoint depend on an expensive simulation.

---

# 46. Error Model

Use structured errors.

Conceptually:

```json
{
  "error": {
    "code": "SIMULATION_FAILED",
    "message": "SWMM simulation failed.",
    "simulationId": "sim-001"
  }
}
```

The exact contract belongs in:

```text
06_API_CONTRACT.md
```

---

# 47. Error Categories

Useful categories include:

```text
INVALID_REQUEST
SCENARIO_NOT_FOUND
SIMULATION_NOT_FOUND
SIMULATION_FAILED
SIMULATION_TIMEOUT
MODEL_NOT_FOUND
RAINFALL_NOT_FOUND
RESULT_NOT_FOUND
PROCESSING_FAILED
GEOSPATIAL_ERROR
INTERNAL_ERROR
```

Do not expose stack traces in production API responses.

---

# 48. Logging

Log important lifecycle events.

Example:

```text
simulation.created
simulation.validating
simulation.preparing
simulation.running
simulation.processing
simulation.completed
simulation.failed
```

Include:

```text
simulation_id
scenario_id
model_version
stage
timestamp
```

Avoid logging secrets.

---

# 49. Auditability

For each simulation, preserve enough information to answer:

- What scenario ran?
- Which model ran?
- Which rainfall input was used?
- When did it run?
- Did it succeed?
- What processing version was used?
- What results were generated?

This is important both technically and academically.

---

# 50. Model Version Resolution

The backend should resolve the model by an explicit model identifier.

Example:

```text
ward176-hydraulic-reconstructed-v1
```

The model registry can initially be simple.

Example:

```json
{
  "id": "ward176-hydraulic-reconstructed-v1",
  "path": "...",
  "description": "Current reconstructed Ward 176 SWMM model"
}
```

The exact implementation can evolve.

---

# 51. Processing Version

Derived flood/risk products should also have a processing version.

Example:

```text
flood-processing-v1
risk-processing-v1
```

If the algorithm changes, results should be distinguishable.

---

# 52. Result Caching

Completed simulations should be reusable.

If the same simulation result is requested again:

```text
return stored result
```

Do not rerun SWMM unnecessarily.

If the scenario/model/processing version changes, treat it as a different result.

---

# 53. Security

Basic security requirements:

- validate all API input,
- restrict file paths,
- prevent path traversal,
- never execute arbitrary user commands,
- never accept arbitrary SWMM executable paths,
- protect credentials,
- avoid exposing internal filesystem paths.

Even in an academic prototype, these practices should be followed.

---

# 54. File Path Security

Never allow:

```text
../../some_file
```

or equivalent user-controlled paths to determine files read/executed by the backend.

Use:

```text
validated IDs
+
server-side path resolution
```

---

# 55. Input Validation

Validate:

- scenario IDs,
- numeric ranges,
- timestamps,
- rainfall multipliers,
- simulation options,
- requested asset IDs.

Reject malformed input early.

---

# 56. API Performance

Avoid returning huge datasets by default.

For large data:

```text
summary endpoint
      +
detail endpoint
      +
time-slice endpoint
```

For example, the dashboard should not download the entire building dataset every time it requests KPIs.

---

# 57. Pagination / Filtering

Where endpoints return many records, support appropriate:

- pagination,
- filtering,
- limits,
- time ranges.

This is especially relevant to:

- node time series,
- link results,
- affected assets,
- risk locations.

---

# 58. Frontend Data Needs

The backend should optimize responses around actual UI needs.

The frontend will primarily need:

```text
scenario metadata
simulation status
simulation summary
timeline
flood visualization
KPIs
risk
bottlenecks
recommendations
asset details
```

It does not need raw SWMM report text for normal operation.

---

# 59. API Contract Boundary

The backend implementation must follow:

```text
06_API_CONTRACT.md
```

once that document is created.

Do not independently create endpoint names or JSON structures in the frontend and backend.

The API contract is the shared interface.

---

# 60. Testing Strategy

## 60.1 Unit tests

Test:

- scenario validation,
- KPI calculations,
- risk calculations,
- input transformation,
- path handling,
- parser utilities.

## 60.2 Integration tests

Test:

```text
simulation service
    ↓
SWMM runner
    ↓
parser
    ↓
processing
```

## 60.3 API tests

Test:

- request validation,
- status codes,
- response schemas,
- error responses.

## 60.4 End-to-end test

At least one test should verify:

```text
Create simulation
    ↓
Run SWMM
    ↓
Process
    ↓
Complete
    ↓
Retrieve results
```

---

# 61. Testing Against the Real Model

The backend should eventually run against the actual project baseline:

```text
ward176_hydraulic_reconstructed_candidate.inp
```

Tests should verify that:

- SWMM executes,
- expected outputs exist,
- parser recognizes expected nodes/links,
- KPIs are generated,
- flood products are produced.

Do not replace the real model with fake data for all integration tests.

Synthetic fixtures are still appropriate for unit tests.

---

# 62. Determinism

Where possible, processing should be deterministic.

Given:

```text
same model
+
same rainfall
+
same processing version
```

the application should produce equivalent results.

Random algorithms should be avoided unless there is a documented reason.

---

# 63. Backend-to-Cesium Boundary

The backend should provide spatial products suitable for Cesium.

Potentially:

```text
GeoJSON
CZML
3D Tiles
vector/raster web assets
```

The exact format depends on performance and visualization requirements.

The backend should not assume GeoJSON is always optimal for large datasets.

---

# 64. Static GIS Data Endpoints

The backend may expose endpoints for:

```text
ward boundary
buildings
roads
drains
subcatchments
```

Alternatively, these can be served directly from static object storage.

The final decision should depend on:

- dataset size,
- caching,
- security,
- frontend requirements.

---

# 65. Dynamic GIS Data Endpoints

Simulation-specific endpoints should use the simulation ID.

Conceptually:

```text
/simulations/{id}/flood
/simulations/{id}/depth
/simulations/{id}/risk
/simulations/{id}/bottlenecks
```

The exact paths belong in the API contract.

---

# 66. Asset Inspection

The backend may support asset details.

Examples:

```text
GET building/{id}
GET drain/{id}
```

For drains, available source attributes may include:

- source ObjectID,
- length,
- width,
- depth,
- status,
- material,
- water-flow information.

Do not expose attributes that do not exist.

---

# 67. Source Data Protection

The public API should not necessarily expose every raw source attribute.

The backend should expose only what is needed for:

- visualization,
- analysis,
- inspection,
- academic demonstration.

Sensitive or unnecessary implementation details should remain internal.

---

# 68. Background Processing Failure Recovery

If processing fails after SWMM succeeds:

```text
simulation status = FAILED
stage = PROCESSING
```

Keep:

- SWMM input,
- SWMM report,
- SWMM output,
- processing logs.

This makes debugging possible without rerunning the entire simulation.

---

# 69. Cleanup Policy

Temporary files may be cleaned after successful processing if needed.

However, preserve enough artifacts for reproducibility.

A practical distinction is:

```text
temporary execution files
       vs
archival simulation artifacts
```

The retention policy can evolve for AWS.

---

# 70. Resource Limits

The backend should protect itself from:

- unlimited simulation requests,
- huge uploads,
- excessive concurrent simulations,
- runaway processes.

For the MVP, simple controls are sufficient.

Example:

```text
one simulation at a time
```

if concurrency has not yet been engineered.

---

# 71. Deployment Packaging

The backend should eventually support containerization.

Conceptually:

```text
Docker image
├── Python runtime
├── backend code
├── dependencies
└── SWMM executable
```

The exact packaging approach must respect SWMM licensing/distribution requirements and the project's chosen deployment environment.

Do not assume the local Windows executable can simply be copied into a Linux container.

---

# 72. Windows Development

Current project development occurs on Windows.

Local paths may look like:

```text
F:\ChennaiFlood-Twin\
```

Application code must remain portable.

Use:

```python
pathlib.Path
```

or equivalent path abstractions.

Do not concatenate Windows path strings manually.

---

# 73. Linux / AWS Compatibility

AWS deployment may use Linux containers.

Therefore avoid:

- Windows-only shell commands,
- hardcoded `.exe` assumptions in business logic,
- Windows-only filesystem behaviour.

The SWMM runner should abstract the executable invocation.

---

# 74. Environment Abstraction

Conceptually:

```text
SWMM Runner
    ↓
Environment-specific executable
```

Local:

```text
SWMM executable on Windows
```

Cloud:

```text
SWMM executable packaged into compatible compute environment
```

The application service should not care which environment is being used.

---

# 75. Recommended Implementation Sequence

Build the backend in this order:

### Phase 1

```text
Project skeleton
Health endpoint
Configuration
Logging
```

### Phase 2

```text
Scenario service
Scenario endpoint
```

### Phase 3

```text
Simulation service
Simulation state
Simulation IDs
```

### Phase 4

```text
SWMM runner
Real model execution
```

### Phase 5

```text
SWMM parser
Result storage
```

### Phase 6

```text
KPI processing
Flood processing
```

### Phase 7

```text
Risk
Bottlenecks
Recommendations
```

### Phase 8

```text
Frontend API integration
```

### Phase 9

```text
AWS deployment
```

Do not start with AWS before the local end-to-end workflow works.

---

# 76. Minimum Backend Demo

Before advanced features, the backend should successfully support:

```text
GET /health
        ↓
GET scenarios
        ↓
POST simulation
        ↓
GET simulation status
        ↓
GET simulation summary
        ↓
GET flood results
        ↓
GET KPIs
```

This is the minimum backend backbone for the Digital Twin.

---

# 77. Backend Definition of Done

The backend is considered ready for full frontend integration when:

1. It starts reliably.
2. Configuration is environment-based.
3. Health endpoint works.
4. Scenario metadata is available.
5. A simulation can be created.
6. Simulation status is trackable.
7. SWMM runs through the backend.
8. Simulation outputs are parsed.
9. Results are persisted.
10. Flood products are generated.
11. KPIs are generated.
12. Risk/bottleneck products are generated where implemented.
13. Errors are structured.
14. Logs are available.
15. Simulation runs are isolated.
16. Baseline model is protected.
17. API responses follow the API contract.
18. Local integration testing succeeds.

---

# 78. Backend Anti-Patterns

Avoid:

### Giant route handlers

```text
route.py
 └── 1500 lines
```

### Frontend-driven filesystem access

The browser should never know local server paths.

### Direct database access from route code

Use repositories/services.

### Global mutable simulation state

Do not rely on:

```python
CURRENT_SIMULATION = ...
```

### Hardcoded project paths

Do not embed:

```text
F:\ChennaiFlood-Twin\
```

in application logic.

### Hardcoded simulation results

Do not hardcode SWMM values into API responses.

### Silent fallback

Do not convert failures into fake zero-valued results.

---

# 79. Scientific Integrity in the Backend

The backend must preserve distinctions between:

```text
Source observation
      ↓
Model assumption
      ↓
Simulation output
      ↓
Derived analysis
      ↓
Visualization
```

For example:

```text
197.876 million L flooding loss
```

is a SWMM model output under an incomplete network representation.

It is not an observed Ward 176 flood volume.

The backend should preserve this distinction in metadata and, where appropriate, API responses.

---

# 80. Model Change Protection

The backend must not automatically "improve" the SWMM model.

It must not:

- remove unstable links automatically,
- invent missing connections,
- modify junction elevations automatically,
- invent outfalls,
- change Manning values,
- change infiltration parameters,
- change solver settings

just because a simulation produces a warning.

Model changes belong to a deliberate engineering workflow, not runtime automation.

---

# 81. Observability

A useful simulation log should allow developers to reconstruct:

```text
What was requested?
Which model ran?
Which rainfall was used?
What happened during execution?
Did SWMM succeed?
What processing occurred?
What products were generated?
Why did it fail if unsuccessful?
```

This is especially important for vibecoded systems where future code changes may occur rapidly.

---

# 82. Documentation Synchronization

If backend implementation changes:

- update `02_ARCHITECTURE.md` if architecture changes,
- update `06_API_CONTRACT.md` if endpoints/contracts change,
- update this document if backend structure/responsibilities change,
- update `10_CHANGELOG.md` for significant changes.

Do not let implementation and documentation drift apart.

---

# 83. Final Backend Architecture

The intended backend can be summarized as:

```text
                         FRONTEND
                            │
                            ▼
                         REST API
                            │
          ┌─────────────────┴──────────────────┐
          │                                    │
          ▼                                    ▼
   Scenario Service                    Simulation Service
                                               │
                                               ▼
                                         SWMM Runner
                                               │
                                               ▼
                                         SWMM 5.2.4
                                               │
                                               ▼
                                           Parser
                                               │
                                               ▼
                                      Processing Services
                                    ┌──────────┼──────────┐
                                    │          │          │
                                    ▼          ▼          ▼
                                  Flood      KPI       Risk
                                    │          │          │
                                    └──────────┼──────────┘
                                               ▼
                                      Bottlenecks /
                                      Recommendations
                                               │
                                               ▼
                                         Result Store
                                               │
                                               ▼
                                            REST API
                                               │
                                               ▼
                                    CesiumJS + Dashboard
```

---

# 84. Final Non-Negotiable Rules

1. Backend owns computation.
2. Frontend owns presentation.
3. API is the formal boundary.
4. Use a modular monolith for the MVP.
5. Protect the master SWMM model.
6. Give every simulation a unique ID.
7. Isolate simulation workspaces.
8. Never fabricate missing hydraulic/GIS information.
9. Never silently change model assumptions.
10. Never hardcode simulation results.
11. Keep raw data immutable.
12. Use explicit CRS handling.
13. Validate all inputs.
14. Execute SWMM through a controlled runner.
15. Preserve raw SWMM artifacts.
16. Make simulation execution asynchronous where appropriate.
17. Use structured errors.
18. Use environment-based configuration.
19. Keep the backend portable across Windows development and future Linux/AWS deployment.
20. Follow `06_API_CONTRACT.md` once defined.
21. Version model and processing changes.
22. Prefer simple, testable modules.
23. Do not introduce microservices prematurely.
24. Do not globally tune or modify SWMM at runtime.
25. Preserve scientific limitations in application metadata and outputs.

---

# 85. Final Principle

The backend should make the complex parts of ChennaiFlood-Twin **reliable and invisible to the user**.

The ideal user experience is:

```text
SELECT SCENARIO
      ↓
RUN
      ↓
WAIT
      ↓
SEE FLOOD
      ↓
UNDERSTAND RISK
      ↓
MAKE A DECISION
```

while the backend quietly handles:

```text
validation
→ model preparation
→ SWMM execution
→ parsing
→ geospatial processing
→ KPI calculation
→ risk analysis
→ result storage
→ API delivery
```

The backend succeeds when this entire chain is reproducible, testable, understandable, and scientifically honest.
