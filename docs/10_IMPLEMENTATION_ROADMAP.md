# ChennaiFlood-Twin — Implementation Roadmap

## 1. Purpose

This document is the **master execution roadmap for building ChennaiFlood-Twin from the current project state to the final working Digital Twin**.

It is written primarily for Claude, which will be used to vibecode the project.

Read this together with:

```text
00_PROJECT_CONTEXT.md
01_PRODUCT_REQUIREMENTS.md
02_ARCHITECTURE.md
03_DATA_AND_GIS.md
04_SWMM_MODEL.md
05_BACKEND_DESIGN.md
06_API_CONTRACT.md
07_FRONTEND_DESIGN.md
08_CESIUM_DIGITAL_TWIN.md
09_AWS_DEPLOYMENT.md
```

This document answers:

- What should be built first?
- What depends on what?
- When should Claude stop and ask for verification?
- What counts as a successful phase?
- What should not be built yet?
- What is the minimum viable Digital Twin?
- How should local development transition to AWS?
- How should the final demo be prepared?

---

# 2. Current Project State

The project is **not starting from zero**.

The following major groundwork has already been completed:

```text
Project definition
        ✓

DA1 requirements
        ✓

Smart City problem framing
        ✓

Study area selection
        ✓

GCC GIS data acquisition
        ✓

Ward 176 drainage extraction
        ✓

Ward 176 building extraction
        ✓

Ward 176 road extraction
        ✓

Copernicus DEM acquisition
        ✓

NASA GPM IMERG rainfall acquisition
        ✓

Rainfall processing
        ✓

Drainage network audit
        ✓

Candidate topology reconstruction
        ✓

Subcatchment generation
        ✓

Hydraulic network reconstruction
        ✓

SWMM baseline construction
        ✓

SWMM cleanup
        ✓

Targeted hydraulic investigation
        ✓

Hydraulic reconstruction candidate
        ✓

Reconstructed candidate SWMM run
        ✓
```

The next major objective is:

```text
PROCESSED DATA
      ↓
BACKEND
      ↓
API
      ↓
CESIUM DIGITAL TWIN
      ↓
DECISION SUPPORT
      ↓
AWS DEPLOYMENT
```

---

# 3. Current Scientific Model Status

The current working hydraulic model is:

```text
ward176_hydraulic_reconstructed_candidate.inp
```

It contains:

```text
35 subcatchments
228 nodes
182 links
```

The model uses:

```text
EPA SWMM 5.2.4
Dynamic Wave
CMS
30-minute rainfall
```

The current model is a **candidate model**, not a claim of complete hydraulic truth.

---

# 4. Important Model Limitations

The current drainage network remains fragmented.

Some downstream terminals are provisional.

Therefore:

> Model-generated flooding loss must not be presented as observed flood volume.

Similarly:

```text
simulated flood depth
simulated flood extent
potential bottleneck
model-derived risk
```

must remain clearly labelled.

These limitations must survive into:

```text
backend
API
frontend
Digital Twin
presentation
```

---

# 5. Master Development Principle

Build from:

```text
FOUNDATION
   ↓
DATA
   ↓
BACKEND
   ↓
API
   ↓
FRONTEND
   ↓
DIGITAL TWIN
   ↓
DECISION SUPPORT
   ↓
AWS
   ↓
POLISH
```

Do not reverse this order.

In particular:

> **Do not build a visually impressive frontend around unverified or fabricated backend outputs.**

---

# 6. Development Phases

The recommended sequence is:

```text
Phase 0  Repository + Environment
Phase 1  Data/Asset Packaging
Phase 2  Backend Foundation
Phase 3  SWMM Execution Service
Phase 4  API Contract Implementation
Phase 5  Static GIS API
Phase 6  React Application Shell
Phase 7  Cesium Static Digital Twin
Phase 8  Simulation Workflow
Phase 9  Flood Visualization
Phase 10 Timeline
Phase 11 KPIs
Phase 12 Risk + Bottlenecks
Phase 13 Recommendations
Phase 14 Integration + Testing
Phase 15 UI/UX Polish
Phase 16 Dockerization
Phase 17 AWS Deployment
Phase 18 Final Demo Hardening
```

The phases can overlap slightly after their dependencies are verified.

---

# 7. Phase 0 — Repository and Environment

## Objective

Create the clean development foundation.

Expected repository structure:

```text
ChennaiFlood-Twin/
├── docs/
├── data_raw/
├── data_processed/
├── gis/
├── simulation/
├── backend/
└── frontend/
```

Additional folders may be added as implementation begins.

---

# 8. Phase 0 Tasks

Claude should:

1. Inspect the repository.
2. Confirm the existing folder structure.
3. Confirm available model/data artifacts.
4. Create backend project.
5. Create frontend project.
6. Configure Git.
7. Create environment templates.
8. Create basic README/developer instructions.
9. Avoid modifying source data.

---

# 9. Phase 0 Backend Setup

Recommended:

```text
Python
FastAPI
Pydantic
Uvicorn
```

Potential:

```text
pytest
httpx
```

Create:

```text
backend/
├── app/
├── tests/
├── requirements.txt
└── ...
```

---

# 10. Phase 0 Frontend Setup

Recommended:

```text
React
TypeScript
Vite
```

Create:

```text
frontend/
├── src/
├── public/
├── package.json
└── ...
```

Do not build the full UI yet.

---

# 11. Phase 0 Environment Gate

Before continuing:

```text
[ ] backend starts
[ ] frontend starts
[ ] Git works
[ ] environment configuration works
[ ] no secrets committed
[ ] source data untouched
```

If this fails:

> Stop and fix Phase 0.

---

# 12. Phase 1 — Data and Asset Packaging

## Objective

Make the already-created project data accessible to the application without modifying its scientific meaning.

Important artifacts include:

```text
ward176_dem.tif

ward176_buildings.geojson

ward176_carriageways.geojson

ward176_subcatchments.geojson

ward176_drain_network_audit.csv

ward176_reconstructed_conduits.geojson

ward176_hydraulic_reconstruction_junction_audit.csv

ward176_hydraulic_reconstruction_offsets.csv

michaung rainfall CSV

ward176_hydraulic_reconstructed_candidate.inp
```

The exact filesystem paths should be discovered rather than assumed.

---

# 13. Phase 1 Rules

Claude must:

- inspect actual files,
- validate file existence,
- preserve source files,
- create controlled application-facing copies/assets if needed,
- document paths,
- avoid inventing missing datasets.

---

# 14. Web-Ready Spatial Assets

Where practical, create web-ready versions of:

```text
Ward boundary
Buildings
Roads
Drains
Subcatchments
```

The backend or preprocessing pipeline should provide correct web CRS.

Do not make the browser perform heavy GIS processing unnecessarily.

---

# 15. Phase 1 Data Gate

Verify:

```text
[ ] Ward boundary loads
[ ] Buildings load
[ ] Roads load
[ ] Drains load
[ ] Subcatchments load
[ ] DEM is readable
[ ] Rainfall is readable
[ ] SWMM model exists
```

If any required asset is missing:

> Stop before building dependent features.

---

# 16. Phase 2 — Backend Foundation

## Objective

Create the FastAPI application architecture.

Recommended:

```text
backend/app/
├── main.py
├── api/
├── core/
├── models/
├── schemas/
├── services/
├── repositories/
├── simulation/
├── gis/
├── analysis/
└── utils/
```

The exact organization may evolve.

---

# 17. Phase 2 Services

Initially create:

```text
ScenarioService
SimulationService
GISService
ResultService
```

Later:

```text
FloodService
RiskService
BottleneckService
RecommendationService
```

---

# 18. Phase 2 Health Endpoints

Implement:

```text
GET /api/v1/health
GET /api/v1/health/ready
```

These should work before any simulation code is added.

---

# 19. Phase 2 Configuration

Create controlled configuration for:

```text
data directory
model directory
results directory
SWMM executable
API port
database
AWS settings
```

Do not hardcode:

```text
F:\ChennaiFlood-Twin\
```

into production code.

---

# 20. Phase 2 Gate

Claude should stop for verification when:

```text
GET /health → 200
GET /health/ready → expected readiness response
backend starts cleanly
configuration loads correctly
```

Only then continue.

---

# 21. Phase 3 — SWMM Execution Service

## Objective

Make the backend capable of running the approved SWMM model safely.

---

# 22. SWMM Service Responsibilities

Create a controlled service that:

1. receives a validated scenario,
2. selects the approved model,
3. creates an isolated working directory,
4. prepares required input files,
5. runs SWMM,
6. captures output,
7. validates execution,
8. parses required results,
9. stores artifacts,
10. returns structured metadata.

---

# 23. SWMM Execution Rule

The backend must never accept arbitrary:

```text
executable path
shell command
filesystem path
```

from the frontend.

Use server-side mappings.

---

# 24. Simulation Working Directory

Each simulation should have:

```text
simulationId/
```

with its own:

```text
.inp
.rpt
.out
```

and processing artifacts.

This prevents collisions between simulations.

---

# 25. SWMM Validation

Before execution:

```text
model exists
rainfall scenario exists
model version is approved
input files exist
```

After execution:

```text
process exited successfully
report exists
output exists where required
results can be parsed
```

---

# 26. Phase 3 First Test

Before connecting the frontend:

> Run one real Michaung simulation through the backend.

Expected:

```text
API/service
   ↓
SWMM
   ↓
actual model output
```

No mock simulation.

---

# 27. Phase 3 Gate

Do not continue until:

```text
[ ] backend starts simulation
[ ] SWMM executes
[ ] simulation completes
[ ] report is generated
[ ] output is parsed
[ ] no arbitrary command execution exists
[ ] isolated simulation directory works
```

---

# 28. Phase 4 — API Contract Implementation

## Objective

Implement the contract in:

```text
06_API_CONTRACT.md
```

Do not invent a second API design.

---

# 29. Phase 4 Minimum Endpoints

Implement:

```text
GET  /health
GET  /health/ready

GET  /scenarios
GET  /scenarios/{scenarioId}

POST /simulations
GET  /simulations/{simulationId}

GET  /simulations/{simulationId}/summary
GET  /simulations/{simulationId}/kpis
```

Then spatial/result endpoints.

---

# 30. Simulation Lifecycle

Implement explicit state transitions:

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

Failure:

```text
any stage
 ↓
FAILED
```

---

# 31. Simulation Polling

The frontend will poll:

```text
GET /simulations/{simulationId}
```

while the simulation is active.

The backend is authoritative.

---

# 32. Phase 4 Gate

Test with an API client before building the frontend.

Verify:

```text
scenario discovery
scenario metadata
simulation creation
simulation status
simulation completion
summary
KPI
error handling
```

If API behaviour is unstable:

> Stop.

Do not compensate for backend instability with frontend hacks.

---

# 33. Phase 5 — Static GIS API

## Objective

Expose the Digital Twin's base city data.

Implement:

```text
GET /gis/ward
GET /gis/buildings
GET /gis/roads
GET /gis/drains
```

Optional:

```text
GET /gis/subcatchments
```

---

# 34. Static GIS Requirements

Verify:

```text
correct CRS
correct coordinates
valid GeoJSON
valid geometry
stable IDs
reasonable payload size
```

---

# 35. Static GIS Gate

Before Cesium:

> Open every spatial response independently and verify its geometry.

The first Cesium debugging session should not also be the first GIS validation session.

---

# 36. Phase 6 — React Application Shell

## Objective

Create the application's visual structure.

Build:

```text
Header
Viewer container
Scenario panel
Simulation controls
Layer controls
Timeline placeholder
KPI placeholder
Side panels
```

At this point the UI can still use placeholder content for sections that have no backend integration yet.

---

# 37. Phase 6 Design Goal

The user should already recognize:

```text
ChennaiFlood-Twin
Ward 176
Digital Twin
```

before simulation integration exists.

---

# 38. Phase 6 Gate

Verify:

```text
[ ] layout works
[ ] responsive desktop layout
[ ] no console errors
[ ] controls are readable
[ ] viewer area has sufficient space
```

---

# 39. Phase 7 — Cesium Static Digital Twin

## Objective

Connect the real spatial data to Cesium.

Build in this order:

```text
Cesium Viewer
    ↓
Ward boundary
    ↓
Terrain
    ↓
Buildings
    ↓
Roads
    ↓
Drains
```

---

# 40. Phase 7 Rule

Do not add flood yet.

First make the static Digital Twin correct.

---

# 41. Phase 7 Camera

Implement:

```text
fitWard()
resetView()
```

The initial camera should clearly frame Ward 176.

---

# 42. Phase 7 Layer Controls

Implement:

```text
Terrain
Buildings
Roads
Drains
Ward Boundary
```

with show/hide functionality.

---

# 43. Phase 7 Selection

Implement basic:

```text
click
→ select feature
→ highlight
→ show identifier
```

Start with drains/buildings.

---

# 44. Phase 7 Gate

Visually verify:

```text
[ ] terrain aligned
[ ] buildings aligned
[ ] roads aligned
[ ] drains aligned
[ ] ward boundary aligned
[ ] selection works
[ ] camera works
```

If spatial alignment is wrong:

> Stop and fix the spatial pipeline before continuing.

---

# 45. Phase 8 — Simulation Workflow

## Objective

Connect:

```text
Scenario
→ Run
→ Backend
→ Status
→ Completion
```

to the UI.

---

# 46. Scenario Selector

Display actual scenario metadata.

Initial scenario:

```text
Michaung 2023
```

Do not fabricate additional scenarios.

---

# 47. Run Button

Implement:

```text
Run Simulation
```

with proper state transitions:

```text
idle
→ validating
→ running
→ processing
→ completed
```

---

# 48. Progress UI

Show backend-driven progress/state.

Example:

```text
Preparing...
Running SWMM...
Processing results...
Complete
```

Do not fake progress.

---

# 49. Phase 8 Gate

Complete one end-to-end run:

```text
Frontend
 ↓
POST /simulations
 ↓
Backend
 ↓
SWMM
 ↓
Backend status
 ↓
Frontend
 ↓
COMPLETED
```

This is the first major end-to-end milestone.

---

# 50. Phase 9 — Flood Result Processing

## Objective

Transform SWMM output into a usable spatial flood product.

This is primarily a backend/data-processing phase.

---

# 51. Flood Processing Principle

Do not claim a full 2D hydraulic solver.

The project uses:

```text
SWMM urban drainage/hydraulic simulation
+
spatial post-processing
+
3D geospatial visualization
```

---

# 52. Flood Processing Pipeline

Conceptually:

```text
SWMM output
   ↓
node/link flooding information
   ↓
spatial association
   ↓
terrain/building/road context
   ↓
flood-depth/extent derivation
   ↓
web-ready spatial product
```

The exact algorithm must use documented assumptions.

---

# 53. Flood Product Requirements

At minimum, produce:

```text
flood summary
flood timeline
flood time slice
```

Potentially:

```text
flood extent GeoJSON
flood depth raster/vector
```

depending on the selected processing method.

---

# 54. Phase 9 Gate

Before Cesium flood integration:

```text
[ ] flood result exists
[ ] timestamp is correct
[ ] spatial geometry is valid
[ ] depth values are sensible
[ ] CRS is correct
[ ] model-derived label is preserved
```

---

# 55. Phase 10 — Cesium Flood Visualization

## Objective

Display the actual model-derived flood product in the 3D scene.

---

# 56. Flood Integration Order

Build:

```text
simulation complete
     ↓
flood summary
     ↓
flood extent
     ↓
flood depth
     ↓
legend
```

---

# 57. Flood Layer Requirements

Support:

```text
show/hide
opacity
legend
timestamp
```

The flood should not obscure the whole Digital Twin.

---

# 58. Flood Gate

Verify:

```text
[ ] flood appears
[ ] flood is spatially aligned
[ ] depth/extent terminology is correct
[ ] legend is correct
[ ] no fake polygons
[ ] buildings/roads remain understandable
```

---

# 59. Phase 11 — Timeline

## Objective

Turn the static flood result into a temporal Digital Twin.

---

# 60. Timeline API

Use:

```text
GET /simulations/{id}/flood/timeline
```

Do not create arbitrary timestamps.

---

# 61. Timeline UI

Implement:

```text
previous
play
pause
next
slider
timestamp
speed
```

---

# 62. Timeline Behaviour

The selected timestamp controls the flood state.

Static layers remain unchanged.

```text
Timeline
   ↓
Flood slice
   ↓
Cesium
```

---

# 63. Timeline Gate

Verify:

```text
[ ] timeline timestamps match simulation
[ ] play works
[ ] pause works
[ ] seek works
[ ] flood changes correctly
[ ] camera remains stable
[ ] no duplicate layers accumulate
```

---

# 64. Phase 12 — KPI Dashboard

## Objective

Expose the most important simulation information.

---

# 65. Initial KPIs

Use actual backend results.

Possible:

```text
Total rainfall
Peak intensity
Maximum simulated flood depth
Affected area
Affected buildings
Potential bottlenecks
```

Only display metrics that are actually available and defensible.

---

# 66. KPI Rule

Every value must come from:

```text
API
```

not:

```text
frontend hardcoding
```

---

# 67. KPI Gate

Verify:

```text
[ ] units shown
[ ] values correct
[ ] model-derived values labelled appropriately
[ ] no fake values
[ ] formatting readable
```

---

# 68. Phase 13 — Risk Analysis

## Objective

Create the decision-support layer.

Risk processing belongs primarily in the backend.

---

# 69. Risk Pipeline

Conceptually:

```text
Flood
+
Asset exposure
+
Drainage/hydraulic indicators
       ↓
Risk processing
       ↓
Risk locations
       ↓
API
       ↓
Cesium + panel
```

---

# 70. Risk API

Implement:

```text
GET /simulations/{id}/risk
```

and optionally:

```text
GET /simulations/{id}/risk/geojson
```

---

# 71. Risk UI

Provide:

```text
risk categories
risk locations
risk score
drivers
```

where available.

---

# 72. Risk Gate

Verify:

```text
[ ] risk is backend-derived
[ ] categories are consistent
[ ] map and panel agree
[ ] no unsupported certainty claims
```

---

# 73. Phase 13B — Bottleneck Analysis

## Objective

Highlight potential hydraulic hotspots.

---

# 74. Bottleneck Pipeline

Use model-derived evidence such as:

```text
hydraulic stress
flow/capacity indicators
continuity behaviour
simulation outputs
```

The exact scoring method must be documented.

---

# 75. Current Investigation Context

Important current model segments include:

```text
C162
C166
C175
C180
C190
```

These are investigation/diagnostic context.

Do not automatically declare them:

```text
failed drains
```

because they are not field-confirmed failures.

---

# 76. Bottleneck API

Implement:

```text
GET /simulations/{id}/bottlenecks
```

and optionally:

```text
GET /simulations/{id}/bottlenecks/geojson
```

---

# 77. Bottleneck Gate

Verify:

```text
[ ] evidence is available
[ ] terminology says potential bottleneck
[ ] map location matches actual link
[ ] source/model IDs are preserved
```

---

# 78. Phase 13C — Recommendations

## Objective

Convert analytical results into understandable decision support.

---

# 79. Recommendation Principles

Recommendations should be:

```text
evidence-based
specific
prioritized
non-authoritative
```

Example:

```text
Investigate high-stress drainage segment
```

is preferable to:

```text
Replace drain immediately
```

unless engineering evidence supports the stronger claim.

---

# 80. Recommendation API

Implement:

```text
GET /simulations/{id}/recommendations
```

---

# 81. Recommendation UI

Display:

```text
Priority
Category
Title
Description
Drivers
```

---

# 82. Phase 14 — Full Integration

## Objective

Connect every major system.

Final flow:

```text
React
 ↓
API
 ↓
Simulation
 ↓
SWMM
 ↓
Processing
 ↓
Results
 ↓
API
 ↓
React
 ↓
Cesium
```

---

# 83. Integration Test

Perform:

```text
Open application
 ↓
Ward 176 appears
 ↓
Select Michaung
 ↓
Run simulation
 ↓
Wait
 ↓
Simulation completes
 ↓
Flood appears
 ↓
Timeline plays
 ↓
KPIs update
 ↓
Risk appears
 ↓
Bottleneck appears
 ↓
Recommendation appears
```

---

# 84. Phase 14 Gate

This is the most important project gate.

The entire core workflow must work without manual developer intervention.

If a developer must:

```text
copy files manually
restart services manually
edit JSON
run hidden scripts
```

during the normal demo flow:

> Fix the integration before proceeding.

---

# 85. Phase 15 — UI/UX Polish

Only after the full workflow works.

Improve:

```text
spacing
typography
icons
animations
loading states
empty states
error messages
tooltips
legends
panel organization
```

---

# 86. Polish Rule

Do not spend major time polishing:

```text
a feature that does not work end-to-end.
```

Correctness comes first.

---

# 87. Demo Mode

Create a polished default state.

Recommended:

```text
Ward 176
Michaung 2023
simulation available
flood ready
timeline ready
```

If practical, cache a completed simulation result.

---

# 88. Demo Reliability

The final demo should not depend entirely on:

```text
live SWMM cold execution
```

A precomputed completed result may be retained.

The live run capability should still exist if stable.

---

# 89. Phase 16 — Dockerization

## Objective

Make backend deployment reproducible.

---

# 90. Docker Tasks

Create:

```text
Dockerfile
.dockerignore
```

Ensure:

```text
FastAPI starts
SWMM exists
simulation runs
results process
```

inside the container.

---

# 91. Docker Gate

Run:

```text
Docker
 ↓
FastAPI
 ↓
SWMM
 ↓
actual simulation
```

before AWS deployment.

---

# 92. Phase 17 — AWS Deployment

Follow:

```text
09_AWS_DEPLOYMENT.md
```

Do not design a second cloud architecture.

---

# 93. AWS Deployment Order

```text
S3
 ↓
ECR
 ↓
RDS
 ↓
ECS/Fargate
 ↓
API
 ↓
Frontend S3
 ↓
CloudFront
 ↓
HTTPS
```

Optional later:

```text
SQS
worker
```

---

# 94. AWS Gate

Verify:

```text
[ ] API reachable
[ ] database reachable
[ ] S3 readable/writable
[ ] SWMM executes
[ ] results persist
[ ] frontend reaches API
[ ] Cesium loads
[ ] simulation workflow works
```

---

# 95. Phase 18 — Final Demo Hardening

## Objective

Turn the working application into a reliable academic project.

---

# 96. Final Demo Checklist

```text
[ ] frontend builds
[ ] backend builds
[ ] no fatal console errors
[ ] no broken API endpoints
[ ] Cesium initializes
[ ] Ward 176 aligned
[ ] scenario loads
[ ] simulation runs
[ ] results load
[ ] flood animates
[ ] KPIs display
[ ] risk displays
[ ] bottlenecks display
[ ] recommendations display
[ ] methodology visible
[ ] limitations visible
[ ] source attribution visible
```

---

# 97. Final Demo Sequence

The recommended live demonstration:

```text
1. Open ChennaiFlood-Twin

2. Show Ward 176
   - terrain
   - buildings
   - roads
   - drainage

3. Select Michaung 2023

4. Show rainfall metadata

5. Run simulation

6. Show progress

7. Simulation completes

8. Show flood extent/depth

9. Play timeline

10. Stop around peak flooding

11. Show KPIs

12. Toggle risk

13. Select high-risk location

14. Show bottleneck

15. Show recommendation

16. Open methodology/model note
```

---

# 98. Academic Explanation Sequence

If asked:

> "How does your system work?"

Answer through:

```text
GCC GIS
   ↓
Ward 176 infrastructure data

NASA GPM
   ↓
Historical rainfall

Copernicus DEM
   ↓
Terrain context

SWMM
   ↓
Urban drainage/hydraulic simulation

Backend
   ↓
Result processing

API
   ↓
Application integration

CesiumJS
   ↓
3D Digital Twin

Risk + Bottlenecks
   ↓
Decision support
```

---

# 99. Claude's Development Behaviour

Claude should work in small verified increments.

For each feature:

```text
Plan
 ↓
Implement
 ↓
Run
 ↓
Inspect output
 ↓
Test
 ↓
Report
 ↓
Continue
```

Do not generate hundreds of files before running anything.

---

# 100. One Major Change at a Time

When debugging:

Prefer:

```text
one change
→ test
→ evaluate
```

rather than:

```text
change backend
+
change model
+
change API
+
change Cesium
+
change data
```

simultaneously.

This is particularly important for hydraulic debugging.

---

# 101. No Silent Scientific Changes

Claude must not silently change:

```text
DEM
rainfall
drain geometry
drain connectivity
junction elevations
SWMM parameters
Manning values
infiltration
outfalls
```

to make the application "look better."

If a scientific/model change is required:

```text
stop
explain
document
test
```

---

# 102. No Fake Data

Never create fake:

```text
flood polygons
rainfall values
risk scores
bottleneck locations
building exposure
```

for the final integrated application.

Mock data is acceptable only for isolated UI development and must be explicitly marked.

---

# 103. No Premature AWS

Do not deploy to AWS while:

```text
local backend
+
local SWMM
+
local API
```

are unstable.

AWS should not become the debugging environment for basic application bugs.

---

# 104. No Premature AI

An AI chatbot or LLM assistant is optional.

Do not build it before:

```text
Digital Twin
simulation
flood
risk
bottlenecks
recommendations
```

work reliably.

The AI layer should explain existing results, not replace the underlying analytical pipeline.

---

# 105. No Premature Scenario Explosion

Start with:

```text
Michaung 2023
```

one reliable scenario.

Then add:

```text
synthetic rainfall multiplier
```

or additional scenarios only after the core workflow is stable.

---

# 106. No Premature Microservices

Start with a modular monolith:

```text
FastAPI
├── scenarios
├── simulations
├── GIS
├── flood
├── risk
└── recommendations
```

Split into separate services only if there is a genuine need.

---

# 107. No Premature Kubernetes

Do not introduce:

```text
EKS
```

for the academic MVP.

ECS/Fargate is sufficient.

---

# 108. No Frontend Hydraulic Calculations

Do not implement SWMM-equivalent calculations in React.

The browser visualizes results.

---

# 109. No Frontend GIS Reconstruction

Do not reconstruct the drainage network in Cesium.

The backend/processed data is authoritative.

---

# 110. No Arbitrary Coordinate Shifts

If a layer is misaligned:

```text
inspect CRS
→ inspect transformation
→ inspect GeoJSON
→ inspect Cesium interpretation
```

Do not apply:

```text
+0.001 longitude
-0.002 latitude
```

as a guess.

---

# 111. Testing Strategy

Testing should occur at four levels.

## Level 1 — Unit

Examples:

```text
formatters
parsers
state transitions
```

## Level 2 — Service

Examples:

```text
SWMM runner
scenario loader
result processor
```

## Level 3 — API

Examples:

```text
POST /simulations
GET /simulations/{id}
```

## Level 4 — End-to-End

Example:

```text
UI
→ API
→ SWMM
→ results
→ Cesium
```

---

# 112. Test Data Strategy

Use the real:

```text
Michaung rainfall
Ward 176 data
current candidate SWMM model
```

for integration tests where practical.

Small synthetic fixtures can be used for unit tests.

---

# 113. Regression Testing

Whenever changing:

```text
SWMM model
flood processing
API
spatial transformation
```

rerun the relevant regression tests.

Do not assume previous results remain valid.

---

# 114. Hydraulic Regression

For model changes, compare:

```text
run success
continuity
warnings
timestep behaviour
critical links
flooding diagnostics
```

Do not optimize solely for:

```text
lower flooding volume
```

because that can reward physically incorrect changes.

---

# 115. Spatial Regression

For spatial changes, verify:

```text
extent
CRS
feature count
geometry validity
alignment
```

---

# 116. API Regression

Verify:

```text
endpoint paths
status codes
response fields
units
identifiers
error structure
```

against:

```text
06_API_CONTRACT.md
```

---

# 117. Frontend Regression

Verify:

```text
viewer startup
layer loading
simulation flow
timeline
selection
panel state
```

after significant changes.

---

# 118. Performance Checkpoints

Measure performance after:

```text
Static Cesium
Flood layer
Timeline
Risk layer
Final integration
```

Do not wait until the end to discover the viewer is unusable.

---

# 119. Performance Targets

The exact target depends on hardware.

The practical goal is:

```text
responsive UI
smooth camera interaction
acceptable 3D rendering
usable flood timeline
```

Do not pursue arbitrary FPS numbers at the expense of data fidelity.

---

# 120. Project Milestones

Recommended milestones:

### M1 — Foundation

```text
backend + frontend start
```

### M2 — Data

```text
all required project assets accessible
```

### M3 — Simulation

```text
backend runs real SWMM
```

### M4 — API

```text
simulation lifecycle accessible through API
```

### M5 — Static Digital Twin

```text
Ward 176 in Cesium
```

### M6 — First Full Demo

```text
scenario
→ run
→ flood
```

### M7 — Temporal Twin

```text
flood + timeline
```

### M8 — Decision Support

```text
KPI
risk
bottlenecks
recommendations
```

### M9 — Cloud

```text
AWS deployment
```

### M10 — Final

```text
stable academic demo
```

---

# 121. MVP Definition

The project can be considered a strong MVP when:

```text
Ward 176 3D scene
        +
Michaung rainfall scenario
        +
real SWMM simulation
        +
flood visualization
        +
timeline
        +
KPIs
```

work end-to-end.

---

# 122. Strong Final Version

The ideal final version adds:

```text
risk
bottlenecks
recommendations
asset inspection
methodology
data provenance
AWS deployment
```

---

# 123. Optional Final Features

Only after everything above:

```text
scenario comparison
AI assistant
advanced filtering
historical event library
additional rainfall scenarios
advanced 3D Tiles
```

---

# 124. Priority Matrix

## P0 — Must Work

```text
React
Cesium
Ward 176
GIS layers
Michaung
SWMM
API
Flood
Timeline
```

## P1 — Strongly Recommended

```text
KPI
Risk
Bottlenecks
Recommendations
Asset inspector
```

## P2 — Nice to Have

```text
Scenario comparison
AI assistant
advanced analytics
```

---

# 125. Stop/Go Rules

Claude should use these rules.

### GO

If:

```text
current phase passes gate
```

continue.

### STOP

If:

```text
spatial alignment incorrect
SWMM execution unreliable
API contract inconsistent
real data unavailable
results are fabricated
security issue exists
```

stop and fix the underlying problem.

---

# 126. When to Ask the User

Claude should ask the user for confirmation when:

```text
a scientific assumption must change
a source dataset must be replaced
a major architecture decision changes
a model parameter must be altered
a destructive operation is proposed
```

Do not ask unnecessary questions for ordinary implementation choices covered by these documents.

---

# 127. When Claude Can Decide Independently

Claude can make ordinary engineering decisions involving:

```text
component naming
file organization
CSS implementation
API client organization
logging structure
test organization
reasonable library selection
refactoring
```

provided they do not contradict the context documents.

---

# 128. Change Documentation

For meaningful changes, record:

```text
what changed
why
files affected
test performed
result
```

Especially for:

```text
SWMM model
flood processing
API contract
AWS architecture
spatial transformations
```

---

# 129. Suggested Change Log

Maintain:

```text
docs/CHANGELOG.md
```

with entries such as:

```text
2026-09-13
- Added hydraulic reconstruction candidate.
- Removed duplicate C182.
- Added backend/frontend implementation context.
```

The exact format can be simple.

---

# 130. Git Commit Strategy

Prefer meaningful commits:

```text
feat: add scenario API
feat: add SWMM runner
feat: add Cesium ward layers
feat: add flood timeline
fix: correct GeoJSON CRS handling
fix: prevent duplicate flood layers
```

Avoid giant commits such as:

```text
finished project
```

---

# 131. Claude Prompting Strategy

When asking Claude to implement a phase, provide:

```text
1. Phase number
2. Objective
3. Relevant context documents
4. Existing files
5. Required output
6. Test requirement
```

Example:

```text
Implement Phase 7 of 10_IMPLEMENTATION_ROADMAP.md.

Read:
03_DATA_AND_GIS.md
07_FRONTEND_DESIGN.md
08_CESIUM_DIGITAL_TWIN.md

First inspect the existing frontend.

Implement only the static Cesium Digital Twin.

Do not implement flood yet.

Run the application and verify alignment.
```

---

# 132. Claude Should Inspect Before Editing

Before modifying a feature:

```text
inspect repository
inspect relevant files
inspect current implementation
inspect actual data
```

Do not overwrite working code blindly.

---

# 133. Claude Should Run After Editing

Every meaningful implementation step should be followed by:

```text
build
lint
test
run
inspect
```

as appropriate.

---

# 134. No "Looks Correct" Without Testing

For code involving:

```text
Cesium
GIS
SWMM
API
```

Claude should not conclude success solely from static code inspection.

Run the relevant workflow.

---

# 135. Backend Debugging Order

If simulation fails:

```text
1. inspect API request
2. inspect scenario
3. inspect model path
4. inspect generated input
5. run SWMM directly
6. inspect report
7. inspect parser
8. inspect result processing
```

Do not immediately change SWMM parameters.

---

# 136. Cesium Debugging Order

If the scene is wrong:

```text
1. inspect API spatial response
2. inspect CRS
3. inspect coordinates
4. inspect Cesium loading
5. inspect camera
6. inspect layer styling
```

Do not immediately change source geometry.

---

# 137. API Debugging Order

If frontend data is wrong:

```text
1. inspect API response
2. inspect TypeScript type
3. inspect API client
4. inspect hook
5. inspect component
```

This prevents frontend hacks from masking backend problems.

---

# 138. Flood Debugging Order

If flood visualization is wrong:

```text
1. inspect SWMM result
2. inspect flood processing
3. inspect spatial product
4. inspect API response
5. inspect Cesium rendering
```

Do not modify Cesium geometry to compensate for bad flood processing.

---

# 139. Final System Validation

Before final presentation, perform:

```text
DATA VALIDATION
      ↓
MODEL VALIDATION
      ↓
BACKEND VALIDATION
      ↓
API VALIDATION
      ↓
SPATIAL VALIDATION
      ↓
CESIUM VALIDATION
      ↓
END-TO-END VALIDATION
      ↓
AWS VALIDATION
      ↓
DEMO VALIDATION
```

---

# 140. Final Scientific Checklist

```text
[ ] Rainfall source identified
[ ] DEM source identified
[ ] GIS source identified
[ ] SWMM version identified
[ ] Model version identified
[ ] Processing version identified
[ ] Model limitations documented
[ ] Flood labelled model-derived
[ ] Risk labelled model-derived
[ ] Bottlenecks labelled potential
[ ] No observed claims without observations
```

---

# 141. Final Technical Checklist

```text
[ ] Backend starts
[ ] Frontend starts
[ ] API documented
[ ] SWMM runs
[ ] GIS loads
[ ] Cesium loads
[ ] Simulation works
[ ] Flood works
[ ] Timeline works
[ ] KPIs work
[ ] Risk works
[ ] Bottlenecks work
[ ] Recommendations work
[ ] Docker works
[ ] AWS works
```

---

# 142. Final Presentation Checklist

```text
[ ] Demo scenario prepared
[ ] Backup completed result available
[ ] Internet checked
[ ] AWS services running
[ ] Browser tested
[ ] Camera starts correctly
[ ] Flood state looks clear
[ ] Timeline works
[ ] KPIs readable
[ ] Methodology explanation ready
[ ] Limitations explanation ready
```

---

# 143. Final Failure-Recovery Plan

If the live simulation fails during the presentation:

```text
Do not panic.
```

Switch to:

```text
precomputed completed simulation
```

and continue demonstrating:

```text
flood
timeline
KPI
risk
bottleneck
recommendations
```

The academic objective is demonstrating the integrated system, not proving that a cloud process can never fail.

---

# 144. Final Project Story

The final application should tell this story:

```text
Chennai has serious urban flooding challenges.
          ↓
Ward 176 / Velachery is a suitable pilot area.
          ↓
Real GCC GIS infrastructure data is available.
          ↓
Historical Michaung rainfall provides a real scenario.
          ↓
Copernicus DEM provides terrain context.
          ↓
EPA SWMM models the urban drainage response.
          ↓
The backend processes simulation outputs.
          ↓
Cesium turns the results into a 3D Digital Twin.
          ↓
Timeline shows how flooding evolves.
          ↓
Risk identifies priority areas.
          ↓
Bottlenecks identify potential drainage hotspots.
          ↓
Recommendations support decision-making.
          ↓
AWS provides deployable cloud infrastructure.
```

---

# 145. Final Architecture

The complete implementation should converge to:

```text
                           USER
                            │
                            ▼
                     React + TypeScript
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
             Dashboard              CesiumJS
                │                       │
                └───────────┬───────────┘
                            │
                           API
                            │
                            ▼
                         FastAPI
                            │
          ┌─────────────────┼──────────────────┐
          │                 │                  │
          ▼                 ▼                  ▼
       Scenario          Simulation          GIS
          │                 │                  │
          │                 ▼                  │
          │               SWMM                │
          │                 │                  │
          │                 ▼                  │
          │          Result Processing         │
          │                 │                  │
          └─────────────────┼──────────────────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
           Flood           Risk       Bottlenecks
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                    Recommendations
                            │
                            ▼
                         Results
                            │
                            ▼
                         Cesium
                            │
                            ▼
                    Digital Twin
```

AWS later wraps the deployable system with:

```text
S3
CloudFront
ECS/Fargate
RDS
ECR
VPC
IAM
Secrets Manager
CloudWatch
```

---

# 146. Final Non-Negotiable Rules

1. Build incrementally.
2. Test every major phase.
3. Use real project data for integration.
4. Do not fabricate missing data.
5. Do not silently alter scientific assumptions.
6. Keep the current SWMM candidate model controlled and versioned.
7. Treat model-derived flood as model-derived.
8. Treat bottlenecks as potential unless independently confirmed.
9. Keep the backend authoritative for simulation state.
10. Keep the API contract stable.
11. Keep Cesium responsible for visualization, not hydraulics.
12. Keep React responsible for UI/application state.
13. Keep large data out of ordinary API JSON where inappropriate.
14. Preserve source/model identifiers.
15. Never hide CRS problems with arbitrary coordinate shifts.
16. Never hardcode Windows paths.
17. Never expose secrets.
18. Never allow arbitrary command execution.
19. Do not over-engineer AWS.
20. Do not introduce AI before the core Digital Twin works.
21. Do not introduce microservices without a real requirement.
22. Do not optimize without measuring.
23. Do not polish broken functionality.
24. Do not make the final demo dependent on an unreliable cold simulation.
25. Keep scientific limitations visible.
26. Make the entire core workflow executable by a non-developer.
27. Document meaningful changes.
28. Use meaningful Git commits.
29. Ask the user only when a decision materially changes the project.
30. Always prefer correctness and credibility over superficial complexity.

---

# 147. Final Definition of Project Completion

ChennaiFlood-Twin is complete when a user can:

```text
OPEN THE APPLICATION
        ↓
SEE WARD 176 AS A 3D DIGITAL TWIN
        ↓
SELECT MICHAUNG 2023
        ↓
RUN THE HYDRAULIC SIMULATION
        ↓
SEE THE SIMULATION COMPLETE
        ↓
VISUALIZE MODEL-DERIVED FLOODING
        ↓
PLAY THE FLOOD TIMELINE
        ↓
INSPECT KPIs
        ↓
VIEW RISK
        ↓
IDENTIFY POTENTIAL BOTTLENECKS
        ↓
READ RECOMMENDATIONS
        ↓
INSPECT UNDERLYING DATA/METHODOLOGY
```

while the implementation remains:

```text
data-grounded
model-connected
API-driven
spatially aligned
versioned
testable
secure
deployable
```

---

# 148. Final Principle

The implementation should progress from:

> **"We have the data and model."**

to:

> **"We have a working API."**

to:

> **"We have a working 3D Digital Twin."**

to:

> **"We can simulate and visualize flooding over time."**

to:

> **"We can turn simulation results into decision support."**

to:

> **"The entire system is deployable and demonstrable on AWS."**

Do not skip the intermediate stages.

The strongest version of ChennaiFlood-Twin is not the one with the most code.

It is the one where every visible feature can be traced back through:

```text
SOURCE DATA
    ↓
PROCESSING
    ↓
MODEL
    ↓
RESULT
    ↓
API
    ↓
VISUALIZATION
    ↓
DECISION SUPPORT
```

and the complete chain works reliably from beginning to end.
