# CLAUDE.md — ChennaiFlood-Twin

## 1. Role of This File

You are **Claude Code**, the primary implementation agent for the ChennaiFlood-Twin project.

This file sits at the **project root** and is your operational instruction manual.

Before making substantial changes, read this file and the relevant numbered context documents in `docs/`.

The numbered documents define the project's detailed technical and scientific context.

---

# 2. Project

**Project name:**

> ChennaiFlood-Twin

**Academic course:**

> BCSE355L — Design of Smart Cities

**Project concept:**

> AI-Powered Urban Flood Digital Twin and Decision Support System

**Pilot study area:**

> Ward 176, Velachery, Chennai

**Primary goal:**

Build a software-only urban flood Digital Twin that combines real GIS data, historical rainfall, EPA SWMM hydraulic simulation, spatial post-processing, CesiumJS 3D visualization, and decision-support outputs.

---

# 3. Non-Negotiable Project Positioning

This project is:

- software-only,
- cloud-ready,
- GIS-driven,
- simulation-driven,
- 3D geospatial,
- decision-support oriented.

It is **not**:

- an IoT project,
- an Arduino/Raspberry Pi project,
- a sensor deployment,
- a drone system,
- a physical embedded system,
- a full 3D CFD/Navier-Stokes urban flood solver.

Use the academically accurate terminology:

> **Hydrological/hydraulic simulation + 3D geospatial Digital Twin visualization**

Do not describe the system as a full 3D Navier-Stokes flood solver.

---

# 4. Read These Documents

The project context is organized as:

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
10_IMPLEMENTATION_ROADMAP.md
```

These should normally be located under:

```text
docs/
```

Read them according to the task.

### Minimum reading rules

For backend work:

```text
00
02
04
05
06
10
```

For frontend work:

```text
00
02
06
07
08
10
```

For GIS/spatial work:

```text
00
03
08
10
```

For SWMM/model work:

```text
00
03
04
10
```

For AWS/deployment work:

```text
00
02
05
06
09
10
```

For major architectural changes:

> Read all relevant documents before changing the architecture.

---

# 5. Source of Truth Hierarchy

When making implementation decisions, use this priority:

```text
1. Explicit user instruction
2. CLAUDE.md
3. Relevant numbered project context document
4. Existing verified project implementation/data
5. Reasonable engineering judgment
6. General knowledge
```

If two project documents appear to conflict:

> Do not silently choose one.

Identify the conflict and resolve it using the newest/relevant project decision or ask the user when the difference materially affects the system.

---

# 6. Current Project State

A substantial amount of groundwork has already been completed.

Existing work includes:

```text
Ward 176 study-area selection
GCC GIS data acquisition
Ward 176 drainage extraction
Ward 176 building extraction
Ward 176 road extraction
Copernicus DEM acquisition
NASA GPM IMERG rainfall acquisition
Rainfall processing
Drainage network audit
Topology reconstruction
Subcatchment generation
SWMM baseline construction
SWMM cleanup
Hydraulic investigation
Hydraulic reconstruction
Reconstructed SWMM candidate
```

Do not redo these from scratch unless specifically requested.

---

# 7. Current Working Hydraulic Model

The current working model is:

```text
ward176_hydraulic_reconstructed_candidate.inp
```

The model currently represents approximately:

```text
35 subcatchments
228 nodes
182 links
```

with:

```text
EPA SWMM 5.2.4
Dynamic Wave
CMS
Michaung rainfall
```

Treat this as the current **candidate model**.

Do not silently replace it with an older baseline.

---

# 8. Important Hydraulic Caveat

The drainage network is still fragmented and some downstream terminals/outfalls are provisional.

Therefore:

> Do not present model-generated flooding volume as observed flood volume.

In particular, values such as model-reported flooding loss are:

> **simulation diagnostics under the current network representation**

not field observations.

The frontend, API, documentation, and presentation must preserve this distinction.

---

# 9. Scientific Integrity

Never silently modify:

```text
rainfall
DEM
drain geometry
drain connectivity
junction elevations
Manning values
infiltration parameters
outfalls
SWMM routing parameters
```

simply to:

- reduce flooding,
- reduce warnings,
- make the visualization look better,
- make the model converge more easily,
- make the demo more impressive.

If a scientific/model change is genuinely necessary:

```text
1. explain why,
2. document the change,
3. preserve the previous version,
4. run the model,
5. compare results,
6. report the effect.
```

---

# 10. No Fabricated Data

Never fabricate final-project:

```text
rainfall
flood polygons
flood depths
risk scores
bottleneck locations
building exposure
drain connections
outfalls
recommendations
```

Mock data is acceptable only for:

- isolated UI development,
- component testing,
- temporary prototypes.

It must be clearly marked and must not accidentally reach the final demo.

---

# 11. No Fake Scientific Claims

Do not claim:

```text
observed flood depth
observed flood volume
real-time sensor data
real-time IoT data
field-confirmed bottleneck
full 2D hydraulic simulation
full CFD simulation
```

unless such evidence is actually available.

Use:

```text
simulated
model-derived
potential
candidate
provisional
```

where appropriate.

---

# 12. Source and Model Traceability

Always preserve the distinction between:

```text
source GIS feature
```

and:

```text
model representation
```

For drainage:

```text
source ObjectID
```

and:

```text
SWMM model link ID
```

are not necessarily the same.

A source drain may become multiple model conduits.

Never collapse these identifiers into one field without explicit justification.

---

# 13. Repository Rules

Expected high-level structure:

```text
ChennaiFlood-Twin/
├── CLAUDE.md
├── docs/
├── data_raw/
├── data_processed/
├── gis/
├── simulation/
├── backend/
└── frontend/
```

Additional folders may be introduced when justified.

Do not reorganize the entire repository merely for stylistic preference.

---

# 14. Protected Data Principle

Treat these as source/controlled assets:

```text
data_raw/
data_processed/
simulation/
```

Do not casually overwrite them.

Prefer:

```text
new version
new candidate
new processing artifact
```

when changing important scientific artifacts.

---

# 15. Windows Path Rule

Development may occur on Windows.

Never hardcode:

```text
F:\ChennaiFlood-Twin\
```

inside application code.

Use:

```python
pathlib.Path
```

and configuration/environment variables.

Code should also work in Linux containers.

---

# 16. Development Philosophy

Work incrementally:

```text
Inspect
 ↓
Plan
 ↓
Implement
 ↓
Run
 ↓
Test
 ↓
Inspect output
 ↓
Fix
 ↓
Report
```

Do not generate a huge amount of code and assume it works.

---

# 17. Inspect Before Editing

Before modifying an existing feature:

1. inspect the repository,
2. inspect relevant files,
3. inspect current implementation,
4. inspect actual data if relevant,
5. understand dependencies,
6. then modify.

Do not overwrite working implementation blindly.

---

# 18. One Major Change at a Time

Prefer:

```text
one meaningful change
→ test
→ evaluate
```

over:

```text
backend change
+
database change
+
API change
+
Cesium change
+
SWMM change
```

all at once.

This is especially important for hydraulic and spatial debugging.

---

# 19. No Silent Refactors

Do not perform large unrelated refactors while implementing a feature.

If a refactor is required:

```text
state why
keep scope controlled
test before/after
```

---

# 20. Backend Technology

Primary backend direction:

```text
Python
FastAPI
Pydantic
Uvicorn
```

Recommended architecture:

```text
backend/app/
├── main.py
├── api/
├── core/
├── schemas/
├── models/
├── repositories/
├── services/
├── simulation/
├── gis/
├── analysis/
└── utils/
```

The exact structure may evolve.

---

# 21. Backend Architecture Rule

Prefer a modular monolith initially.

Conceptually:

```text
FastAPI
├── scenarios
├── simulations
├── GIS
├── flood
├── risk
├── bottlenecks
└── recommendations
```

Do not introduce microservices without a real requirement.

---

# 22. API Contract Is Binding

The API contract in:

```text
06_API_CONTRACT.md
```

is the frontend/backend integration contract.

Do not casually rename:

```text
endpoint
field
identifier
status
enum
```

because it is convenient.

If the contract must change:

```text
update the contract
update backend
update frontend
test both
```

---

# 23. Backend Is Authoritative

The backend is authoritative for:

```text
simulation status
simulation results
risk
bottlenecks
recommendations
scientific calculations
```

The frontend must not invent or override these.

---

# 24. No Frontend Hydraulics

Never implement SWMM-equivalent hydraulic calculations in React.

The browser visualizes backend results.

---

# 25. No Frontend Scientific Risk Engine

Do not independently reproduce risk scoring in TypeScript.

The frontend may format:

```text
82%
```

from a backend value.

It must not independently decide:

```text
depth > X → HIGH
```

unless that rule is explicitly part of the API contract.

---

# 26. SWMM Execution

SWMM execution must be controlled.

The backend should:

```text
validate scenario
 ↓
select approved model
 ↓
create isolated simulation directory
 ↓
prepare files
 ↓
run SWMM
 ↓
capture output
 ↓
parse results
 ↓
process results
```

Never accept arbitrary:

```text
shell command
executable path
filesystem path
```

from the user.

---

# 27. Simulation Isolation

Each simulation must have its own workspace:

```text
{simulationId}/
```

Never allow simultaneous simulations to overwrite:

```text
model.inp
report.rpt
output.out
```

from another simulation.

---

# 28. Simulation States

Use explicit state transitions.

Preferred:

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
FAILED
```

The frontend must reflect actual backend state.

Do not fake progress.

---

# 29. Simulation Reproducibility

Record where possible:

```text
simulationId
scenarioId
modelVersion
processingVersion
applicationVersion
parameters
timestamps
```

A result should be traceable back to the model and scenario that generated it.

---

# 30. GIS Rules

GIS data is scientifically important.

Do not:

- shift geometries arbitrarily,
- invent connections,
- change CRS without understanding it,
- silently simplify important geometry,
- discard source IDs.

---

# 31. CRS Debugging

If spatial layers do not align:

```text
1. inspect source CRS
2. inspect processed CRS
3. inspect API coordinates
4. inspect GeoJSON
5. inspect Cesium interpretation
6. fix the actual transformation
```

Never solve alignment problems with arbitrary coordinate offsets.

---

# 32. Web Spatial Data

Prefer backend/preprocessing to produce web-ready spatial assets.

The browser should not perform large-scale GIS transformations unless necessary.

---

# 33. Cesium Technology

Primary 3D engine:

> CesiumJS

React owns:

```text
UI
application state
API integration
```

Cesium owns:

```text
3D scene
camera
geographic visualization
spatial interaction
```

---

# 34. Cesium Viewer Lifecycle

Create the viewer once.

Do not recreate it whenever:

```text
timeline changes
KPI changes
panel opens
layer toggles
simulation status changes
```

Centralize viewer lifecycle.

---

# 35. Cesium Static Layers

Static layers:

```text
Terrain
Ward boundary
Buildings
Roads
Drains
```

should normally be loaded once and retained.

---

# 36. Cesium Dynamic Layers

Dynamic layers:

```text
Flood
Risk
Bottlenecks
```

may change with simulation/timeline state.

Do not reload static layers on every timestamp.

---

# 37. Cesium No-Fabrication Rule

Never fabricate:

```text
flood polygons
drain connections
outfalls
building geometry
roads
```

for the final system.

---

# 38. Flood Visualization

Flood visualization must come from:

```text
SWMM output
+
documented spatial post-processing
```

It must be labelled appropriately.

Use:

```text
Simulated Flood Depth
```

rather than:

```text
Actual Flood Depth
```

unless actual observations are available.

---

# 39. Flood Timeline

Timeline timestamps must come from actual simulation results/API data.

Do not invent a timeline in the frontend.

The selected timestamp must control the displayed flood state.

---

# 40. Timeline Camera Rule

Changing the flood timestamp should not automatically move the camera.

The user's viewpoint should remain stable during playback.

---

# 41. Risk Layer

Risk is:

```text
backend-derived analytical output
```

The frontend visualizes it.

Do not independently recalculate it.

---

# 42. Bottleneck Layer

Use terminology:

> **Potential drainage bottleneck**

or:

> **Potential hydraulic hotspot**

unless independently confirmed.

Current diagnostic links such as:

```text
C162
C166
C175
C180
C190
```

are investigation context, not automatically confirmed failed drains.

---

# 43. Recommendations

Recommendations should be:

```text
evidence-based
specific
prioritized
non-authoritative
```

Prefer:

```text
Investigate high-stress drainage segment
```

over:

```text
Replace drain immediately
```

unless engineering evidence justifies the stronger statement.

---

# 44. Frontend Technology

Primary frontend direction:

```text
React
TypeScript
Vite
CesiumJS
```

Keep the frontend modular.

---

# 45. Frontend State Separation

Keep separate:

### Viewer state

```text
camera
layers
selection
```

### Simulation state

```text
simulationId
scenario
status
timestamp
results
```

Do not create one giant state object containing everything.

---

# 46. API Data Fetching

Do not duplicate API calls unnecessarily.

Cache where appropriate.

Static:

```text
buildings
roads
drains
ward
```

should be cached.

Dynamic:

```text
flood
risk
bottlenecks
```

should be keyed by:

```text
simulationId
timestamp
product type
```

---

# 47. Race Condition Rule

If the user switches simulations quickly:

```text
Simulation A
Simulation B
```

and A finishes after B:

> A must not overwrite B's active state.

Use cancellation/request keys/query libraries as appropriate.

---

# 48. Cesium Memory Rule

Clean up:

```text
DataSources
Entities
Primitives
event handlers
clock listeners
```

when they are no longer needed.

Do not accumulate dynamic layers during timeline playback.

---

# 49. Performance Rule

Use real project data when testing:

```text
~6,428 buildings
~301 road features
135 source drain features
35 subcatchments
182 SWMM links
```

Profile before optimizing.

Do not arbitrarily delete data to make the viewer faster.

---

# 50. AWS Architecture

The target cloud stack is approximately:

```text
S3
CloudFront
ECS/Fargate
RDS PostgreSQL
ECR
VPC
IAM
Secrets Manager
CloudWatch
```

Optional later:

```text
SQS
dedicated simulation workers
```

---

# 51. AWS Complexity Rule

This is an academic project.

Do not introduce:

```text
Kubernetes
EKS
multi-region architecture
service mesh
complex microservices
```

without a genuine requirement.

Prefer:

```text
simple
managed
reproducible
cost-conscious
```

---

# 52. AWS Secrets

Never commit:

```text
AWS access keys
database passwords
Cesium private credentials
API secrets
```

Frontend environment variables must contain only public-safe configuration.

---

# 53. AWS Storage

Use S3 for large:

```text
GIS files
DEM
rainfall
SWMM artifacts
flood products
result files
```

Use PostgreSQL for:

```text
metadata
relationships
simulation state
result references
```

Do not put huge spatial files into relational tables by default.

---

# 54. Local-to-AWS Compatibility

The same application should conceptually work:

```text
LOCAL
React → FastAPI → local SWMM → local files

AWS
React → FastAPI → containerized SWMM → S3/RDS
```

Do not hardwire local assumptions into application logic.

---

# 55. Environment Configuration

Use configuration for:

```text
DATA_DIR
RESULTS_DIR
SWMM_EXECUTABLE
DATABASE_URL
AWS_REGION
S3_DATA_BUCKET
S3_RESULTS_BUCKET
MODEL_VERSION
PROCESSING_VERSION
```

Do not hardcode environment-specific values.

---

# 56. Testing Requirements

Use multiple levels:

```text
Unit
Service
API
End-to-end
```

At minimum, test:

```text
backend startup
API health
scenario retrieval
simulation creation
simulation status
SWMM execution
result parsing
GIS responses
frontend build
Cesium initialization
```

---

# 57. Hydraulic Regression Testing

When modifying the SWMM model, compare:

```text
execution success
runoff continuity
routing continuity
warnings
critical links
timestep behaviour
flooding diagnostics
```

Never optimize solely for:

```text
lower flooding
```

because that can encourage scientifically incorrect changes.

---

# 58. Spatial Regression Testing

After spatial changes, verify:

```text
CRS
extent
feature count
geometry validity
alignment
```

---

# 59. API Regression Testing

Verify:

```text
paths
status codes
field names
types
units
identifiers
errors
```

against:

```text
06_API_CONTRACT.md
```

---

# 60. Build/Lint/Test Rule

After meaningful code changes, run the appropriate checks.

Typical:

```text
backend:
pytest
lint/type checks where configured

frontend:
npm run build
npm run lint
```

Use the actual project scripts once established.

---

# 61. No "Looks Correct"

Do not claim a feature is complete merely because:

```text
the code looks reasonable
```

Run it.

For:

```text
SWMM
GIS
Cesium
API
```

execution/testing is part of implementation.

---

# 62. Debugging Order — Backend

If simulation fails:

```text
1. inspect API request
2. inspect scenario
3. inspect model path
4. inspect generated input
5. run SWMM directly
6. inspect report/output
7. inspect parser
8. inspect result processing
```

Do not immediately modify hydraulic parameters.

---

# 63. Debugging Order — Cesium

If the scene is wrong:

```text
1. inspect API spatial response
2. inspect CRS
3. inspect coordinates
4. inspect Cesium loading
5. inspect camera
6. inspect styling
```

Do not modify source geometry first.

---

# 64. Debugging Order — Flood

If flood visualization is wrong:

```text
1. inspect SWMM output
2. inspect flood processing
3. inspect spatial product
4. inspect API response
5. inspect Cesium rendering
```

Do not change Cesium geometry to hide bad processing.

---

# 65. Debugging Order — API

If frontend data is wrong:

```text
1. inspect backend response
2. inspect TypeScript type
3. inspect API client
4. inspect data hook
5. inspect component
```

Do not patch the UI to compensate for incorrect backend data.

---

# 66. Implementation Workflow

For every meaningful task:

```text
STEP 1 — Understand
Read relevant docs and inspect existing implementation.

STEP 2 — Plan
State what will change.

STEP 3 — Implement
Make the smallest coherent change.

STEP 4 — Validate
Run tests/build/application.

STEP 5 — Inspect
Check actual output.

STEP 6 — Report
State what changed and what was verified.

STEP 7 — Continue
Only after the current step is stable.
```

---

# 67. Implementation Roadmap

Follow:

```text
10_IMPLEMENTATION_ROADMAP.md
```

The intended order is:

```text
0  Repository/environment
1  Data/assets
2  Backend foundation
3  SWMM service
4  API
5  GIS API
6  React shell
7  Static Cesium
8  Simulation workflow
9  Flood processing
10 Flood visualization
11 Timeline
12 KPIs
13 Risk/bottlenecks/recommendations
14 Integration
15 Polish
16 Docker
17 AWS
18 Demo hardening
```

Do not jump ahead without satisfying dependencies.

---

# 68. Phase Gates

A phase is not complete until its gate passes.

Examples:

### Backend

```text
/health works
/health/ready works
```

### SWMM

```text
real simulation completes
output parses
```

### GIS

```text
geometry validated
CRS validated
```

### Cesium

```text
layers spatially aligned
```

### Flood

```text
real simulation-derived product displayed
```

### Timeline

```text
actual timestamps drive flood state
```

### Full integration

```text
UI → API → SWMM → results → Cesium
```

works without hidden manual intervention.

---

# 69. MVP Priority

## P0 — Must Work

```text
React
Cesium
Ward 176
GIS layers
Michaung scenario
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

## P2 — Optional

```text
Scenario comparison
AI assistant
advanced analytics
```

---

# 70. Do Not Build AI First

An AI assistant is optional.

Do not build it before:

```text
Digital Twin
simulation
flood
timeline
KPI
risk
bottlenecks
recommendations
```

work.

AI should explain/assist with existing system outputs.

It must not replace the underlying analytical pipeline.

---

# 71. Do Not Build Scenario Explosion

Start with:

```text
Michaung 2023
```

one reliable scenario.

Additional synthetic scenarios may come later.

---

# 72. Do Not Build Microservices First

Start with a modular monolith.

Only split components if:

```text
real scaling
deployment
isolation
or maintenance
```

requires it.

---

# 73. Do Not Deploy AWS Too Early

AWS should not be the first debugging environment.

Stabilize:

```text
local backend
local SWMM
local API
local frontend
```

before deployment.

---

# 74. Git Rules

Use meaningful commits.

Examples:

```text
feat: add scenario API
feat: add SWMM runner
feat: add static Cesium layers
feat: add flood timeline
fix: correct spatial CRS handling
fix: prevent duplicate flood layers
```

Avoid meaningless commits such as:

```text
stuff
changes
final
done
```

---

# 75. Change Documentation

For meaningful scientific or architectural changes, record:

```text
what changed
why
files affected
test performed
result
```

Maintain a change log when appropriate.

---

# 76. Destructive Operations

Before destructive operations such as:

```text
delete
overwrite
mass rename
model replacement
dataset replacement
```

verify that the operation is actually required.

For important model/data artifacts:

> Prefer creating a new candidate/version.

---

# 77. User Confirmation Required

Ask the user before making a decision that materially changes:

```text
scientific assumptions
SWMM parameters
source datasets
model topology
major architecture
API contract
destructive data changes
```

Do not ask for permission for ordinary implementation details already covered by these instructions.

---

# 78. Claude's Engineering Judgment

You may decide independently about:

```text
component names
file organization
CSS
ordinary refactoring
API client organization
test organization
reasonable libraries
logging
internal abstractions
```

provided they do not conflict with the project documents.

---

# 79. When Something Is Missing

Do not invent it.

If a required input is genuinely unavailable:

```text
identify exactly what is missing
explain why it is required
state the smallest next step
```

Do not silently substitute unrelated data.

---

# 80. Error Handling

Errors should be:

```text
specific
actionable
safe
```

Prefer:

```text
Simulation failed during SWMM execution.
```

with internal diagnostic details available to developers.

Avoid:

```text
Something went wrong.
```

as the only message.

---

# 81. Frontend Error Behaviour

If one layer fails:

```text
Buildings unavailable
```

do not crash:

```text
Flood
Timeline
KPI
```

if they can continue.

Use graceful degradation.

---

# 82. Simulation Failure Behaviour

If simulation fails:

```text
FAILED
```

with a meaningful error state.

Do not show:

```text
COMPLETED
```

because the UI expected success.

---

# 83. Demo Reliability

The final demo should preferably retain a precomputed completed simulation result.

This protects against:

```text
network failure
AWS cold start
simulation delay
temporary backend failure
```

The live simulation feature can still be demonstrated if reliable.

---

# 84. Final Demo Flow

The preferred demo sequence is:

```text
1. Open application

2. Show Ward 176 3D scene

3. Show terrain/buildings/roads/drains

4. Select Michaung 2023

5. Show rainfall metadata

6. Run simulation

7. Show actual progress

8. Simulation completes

9. Show flood

10. Play timeline

11. Pause around peak

12. Show KPIs

13. Toggle risk

14. Inspect high-risk location

15. Inspect potential bottleneck

16. Show recommendation

17. Show methodology/limitations
```

---

# 85. Final Scientific Story

The application should communicate:

```text
Real GCC GIS
      +
Historical NASA rainfall
      +
Copernicus terrain
      +
EPA SWMM
      ↓
Hydraulic simulation
      ↓
Spatial result processing
      ↓
3D Digital Twin
      ↓
Risk + bottlenecks
      ↓
Decision support
```

AWS provides the deployable cloud infrastructure around this chain.

---

# 86. Final Definition of Done

The project is functionally complete when a user can:

```text
open the application
      ↓
see Ward 176 as a 3D Digital Twin
      ↓
select Michaung 2023
      ↓
run the hydraulic simulation
      ↓
see simulation status
      ↓
see model-derived flooding
      ↓
play the flood timeline
      ↓
inspect KPIs
      ↓
view risk
      ↓
inspect potential bottlenecks
      ↓
read recommendations
      ↓
inspect methodology/limitations
```

with no hidden developer-only steps in the normal workflow.

---

# 87. Final Quality Standard

Every visible result should be traceable through:

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

If that chain cannot be explained:

> do not present the feature as final.

---

# 88. Absolute Rules — Quick Reference

Before every major change, remember:

```text
DO:
✓ inspect first
✓ use real project data
✓ preserve provenance
✓ follow the numbered docs
✓ implement incrementally
✓ test actual behaviour
✓ preserve model versions
✓ keep APIs consistent
✓ keep CRS correct
✓ keep Cesium performant
✓ document meaningful changes

DO NOT:
✗ fabricate data
✗ fabricate flood geometry
✗ invent drain connections
✗ invent outfalls
✗ silently change SWMM science
✗ hardcode Windows paths
✗ expose secrets
✗ allow arbitrary commands
✗ fake simulation progress
✗ calculate hydraulics in React
✗ calculate risk independently in React
✗ hide model limitations
✗ deploy Kubernetes unnecessarily
✗ build AI before the core system
✗ optimize without profiling
✗ polish broken features
```

---

# 89. Final Instruction

Build ChennaiFlood-Twin as a **credible academic Digital Twin**, not as a collection of disconnected demo screens.

When choosing between:

```text
more features
```

and:

```text
more reliable integration
```

choose:

> **more reliable integration.**

When choosing between:

```text
visual appearance
```

and:

```text
scientific correctness
```

choose:

> **scientific correctness.**

When choosing between:

```text
complex architecture
```

and:

```text
simple architecture that works
```

choose:

> **simple architecture that works.**

The final product should be impressive because the entire chain works:

```text
REAL DATA
   ↓
REAL MODEL
   ↓
REAL RESULTS
   ↓
REAL API
   ↓
REAL 3D DIGITAL TWIN
   ↓
REAL DECISION SUPPORT
```

—not because complexity has been added for its own sake.
