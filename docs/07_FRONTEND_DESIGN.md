# ChennaiFlood-Twin — Frontend Design Specification

## 1. Purpose

This document defines how the **ChennaiFlood-Twin frontend** should be designed and implemented.

It is the primary frontend implementation guide for Claude.

Read this together with:

```text
00_PROJECT_CONTEXT.md
01_PRODUCT_REQUIREMENTS.md
02_ARCHITECTURE.md
03_DATA_AND_GIS.md
04_SWMM_MODEL.md
05_BACKEND_DESIGN.md
06_API_CONTRACT.md
```

This document defines:

- frontend technology,
- application structure,
- component architecture,
- state management,
- CesiumJS integration,
- GIS layer handling,
- simulation UX,
- timeline behaviour,
- dashboard design,
- API integration,
- performance rules,
- error/loading states,
- accessibility,
- and frontend coding rules.

The frontend should present the complex simulation system as a **clear, convincing, interactive Smart City Digital Twin**.

---

# 2. Frontend Mission

The frontend transforms:

```text
BACKEND DATA
     ↓
INTERACTIVE DIGITAL TWIN
     +
DASHBOARD
     +
DECISION SUPPORT
```

The user's experience should feel simple:

```text
SELECT SCENARIO
      ↓
RUN
      ↓
WATCH PROGRESS
      ↓
SEE FLOOD
      ↓
MOVE THROUGH TIME
      ↓
UNDERSTAND RISK
      ↓
INSPECT
      ↓
DECIDE
```

The frontend should hide unnecessary technical complexity while preserving scientific transparency.

---

# 3. Recommended Technology

Preferred stack:

```text
React
TypeScript
CesiumJS
Vite
```

Recommended supporting libraries may include:

```text
React Query / TanStack Query
Zustand
Tailwind CSS
```

The exact library selection can change if a simpler alternative is justified.

Do not add dependencies without a clear purpose.

---

# 4. Core Frontend Principles

## 4.1 TypeScript first

Use TypeScript throughout the application.

Avoid:

```typescript
any
```

unless there is a documented reason.

Prefer explicit interfaces/types.

---

## 4.2 Componentized UI

Break the interface into logical components.

Do not create one giant `App.tsx`.

---

## 4.3 Centralized API access

All backend communication should go through a centralized API layer.

Do not scatter:

```typescript
fetch(...)
```

through UI components.

---

## 4.4 Server state vs UI state

Separate:

### Server state

Examples:

- scenarios,
- simulation status,
- KPIs,
- flood results,
- risk,
- bottlenecks.

### UI state

Examples:

- selected layer,
- camera position,
- panel visibility,
- timeline position,
- selected asset,
- active scenario tab.

Use appropriate tools for each.

---

## 4.5 No hardcoded simulation outputs

Never write:

```typescript
const maxFloodDepth = 1.42;
```

when the value should come from the backend.

Static labels are fine.

Static simulation results are not.

---

# 5. Recommended Frontend Structure

Suggested structure:

```text
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   │
│   ├── api/
│   │   ├── client.ts
│   │   ├── scenarios.ts
│   │   ├── simulations.ts
│   │   ├── flood.ts
│   │   ├── gis.ts
│   │   ├── risk.ts
│   │   └── assets.ts
│   │
│   ├── components/
│   │   ├── layout/
│   │   ├── viewer/
│   │   ├── simulation/
│   │   ├── dashboard/
│   │   ├── flood/
│   │   ├── risk/
│   │   ├── bottlenecks/
│   │   ├── recommendations/
│   │   └── common/
│   │
│   ├── cesium/
│   │   ├── viewer.ts
│   │   ├── layers.ts
│   │   ├── terrain.ts
│   │   ├── buildings.ts
│   │   ├── roads.ts
│   │   ├── drains.ts
│   │   ├── flood.ts
│   │   └── camera.ts
│   │
│   ├── hooks/
│   │   ├── useScenarios.ts
│   │   ├── useSimulation.ts
│   │   ├── useFlood.ts
│   │   ├── useRisk.ts
│   │   └── useAssets.ts
│   │
│   ├── store/
│   │   ├── uiStore.ts
│   │   ├── viewerStore.ts
│   │   └── simulationStore.ts
│   │
│   ├── types/
│   │   ├── api.ts
│   │   ├── gis.ts
│   │   ├── simulation.ts
│   │   └── risk.ts
│   │
│   ├── utils/
│   │   ├── formatting.ts
│   │   ├── dates.ts
│   │   └── geo.ts
│   │
│   └── styles/
│       └── ...
│
├── public/
├── package.json
├── tsconfig.json
└── vite.config.ts
```

This is a recommended organization, not a requirement that every file be created immediately.

---

# 6. Application Layout

The application should generally use:

```text
┌─────────────────────────────────────────────────────────┐
│ HEADER                                                   │
│ ChennaiFlood-Twin | Scenario | Status                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                                                         │
│                  3D DIGITAL TWIN                       │
│                                                         │
│                                                         │
│              Terrain + City + Flood                    │
│                                                         │
│                                      ┌───────────────┐  │
│                                      │ Layer Control │  │
│                                      └───────────────┘  │
├─────────────────────────────────────────────────────────┤
│ Timeline / Playback                                     │
├──────────────────────────────┬──────────────────────────┤
│ KPIs                         │ Risk / Bottlenecks       │
├──────────────────────────────┴──────────────────────────┤
│ Recommendations / Decision Support                      │
└─────────────────────────────────────────────────────────┘
```

The actual layout may be adapted for screen size.

The 3D viewer should remain the visual center of the product.

---

# 7. Main Application Areas

The frontend should logically contain:

```text
Application Shell
├── Header
├── Digital Twin Viewer
├── Layer Controls
├── Scenario Controls
├── Simulation Controls
├── Timeline
├── KPI Panel
├── Risk Panel
├── Bottleneck Panel
├── Recommendation Panel
└── Asset Inspector
```

---

# 8. Application Shell

`App.tsx` should primarily compose major areas.

It should not contain:

- SWMM logic,
- API parsing,
- complex GIS processing,
- risk formulas.

Conceptually:

```tsx
<AppShell>
  <Header />
  <DigitalTwinViewer />
  <LayerControls />
  <ScenarioPanel />
  <SimulationControls />
  <Timeline />
  <KpiPanel />
  <RiskPanel />
  <BottleneckPanel />
  <RecommendationPanel />
  <AssetInspector />
</AppShell>
```

---

# 9. Header

The header should provide:

- project name,
- current scenario,
- simulation status,
- optional project subtitle.

Avoid filling the header with technical details.

A good demonstration header might show:

```text
ChennaiFlood-Twin
Urban Flood Digital Twin
Ward 176 • Velachery
```

and a status indicator.

---

# 10. Digital Twin Viewer

The 3D viewer is the primary application component.

It should support:

- terrain,
- buildings,
- roads,
- drains,
- ward boundary,
- flood visualization,
- risk visualization,
- bottlenecks.

The viewer should support:

- pan,
- zoom,
- orbit,
- tilt,
- reset camera,
- selection.

---

# 11. CesiumJS Integration

CesiumJS should be isolated from ordinary React components as much as practical.

Prefer:

```text
React UI
   ↓
Cesium controller/service
   ↓
Cesium Viewer
```

rather than putting all Cesium imperative code directly inside JSX.

React manages application state.

Cesium manages the 3D scene.

---

# 12. Cesium Viewer Lifecycle

The viewer should be initialized once per page/view lifecycle.

Avoid recreating the Cesium Viewer every time React state changes.

Conceptually:

```text
Component mount
    ↓
create Viewer
    ↓
load static layers
    ↓
retain viewer reference
    ↓
update dynamic layers
    ↓
component unmount
    ↓
destroy viewer
```

---

# 13. Cesium References

The viewer instance may be stored in a controlled reference:

```typescript
const viewerRef = useRef<Cesium.Viewer | null>(null);
```

Do not store large Cesium objects in a global state store unless necessary.

---

# 14. Cesium Layer Architecture

Use a layer manager.

Conceptually:

```text
LayerManager
├── Terrain
├── Ward Boundary
├── Buildings
├── Roads
├── Drains
├── Flood
├── Risk
└── Bottlenecks
```

Each layer should have:

- load,
- show/hide,
- update,
- remove/cleanup

behaviour where appropriate.

---

# 15. Static Layers

Static layers include:

```text
Terrain
Ward Boundary
Buildings
Roads
Base Drainage Network
```

These should be loaded once and reused.

Do not reload them every time the simulation timeline changes.

---

# 16. Dynamic Layers

Dynamic layers include:

```text
Flood
Flood Depth
Risk
Bottlenecks
```

These depend on the selected simulation.

The flood layer must update when the timeline changes.

---

# 17. Layer State

Maintain explicit visibility state.

Example:

```typescript
interface LayerVisibility {
  terrain: boolean;
  boundary: boolean;
  buildings: boolean;
  roads: boolean;
  drains: boolean;
  flood: boolean;
  risk: boolean;
  bottlenecks: boolean;
}
```

Layer state belongs to UI/viewer state, not backend state.

---

# 18. Terrain

The terrain layer should:

- load the prepared terrain,
- position it correctly,
- support camera navigation,
- avoid reloading unnecessarily.

If a local terrain representation is used during development, the implementation should preserve the same geographic extent as the processed project terrain.

---

# 19. Terrain Exaggeration

Optional visual exaggeration may be used for presentation.

If used:

> It is a visualization aid, not a modification to the underlying terrain data.

Do not describe exaggerated terrain as measured elevation.

---

# 20. Building Visualization

Buildings should be rendered efficiently.

Potential approaches:

- GeoJSON,
- extruded polygons,
- 3D Tiles,
- other Cesium primitives.

Choose based on actual performance.

The initial implementation may use GeoJSON/extruded geometry if the dataset performs adequately.

---

# 21. Building Height

Do not assume building heights are authoritative.

If extrusion height is estimated:

```text
visualization approximation
```

must be treated differently from:

```text
surveyed building height
```

Do not display fabricated heights as real data.

---

# 22. Building Flood Exposure

Buildings can be visually highlighted based on simulation-derived exposure.

Possible states:

```text
Not affected
Affected
High exposure
```

The exact categories should come from backend data.

Do not calculate complex exposure logic independently in React.

---

# 23. Road Visualization

Roads should be visually recognizable but should not overpower buildings or flood layers.

Road visibility should be toggleable.

Flood-affected roads may be highlighted using backend-derived information.

---

# 24. Drainage Visualization

The base drainage network should be a dedicated layer.

It should:

- be visually distinguishable,
- be toggleable,
- support selection,
- show source ObjectID where useful,
- show hydraulic stress after simulation.

Do not visually connect drainage lines that are not connected in the model/source representation.

---

# 25. Drainage Styling

Potential visual states:

```text
Normal
Potentially stressed
Potential bottleneck
```

The exact thresholds should come from backend analysis.

Do not put hardcoded hydraulic thresholds inside the visual layer unless they are part of the documented API/model contract.

---

# 26. Flood Visualization

Flood visualization is the most important dynamic layer.

It should make the following visually clear:

```text
No flood
     ↓
Low flood
     ↓
Moderate flood
     ↓
High flood
```

The legend must clearly identify the quantity being visualized.

Example:

```text
Simulated Flood Depth (m)
```

Do not label model-derived depth simply as:

```text
Water Level
```

unless that is actually what the data represents.

---

# 27. Flood Extent

Flood extent should be rendered as a spatial overlay.

The implementation should support:

- show/hide,
- timeline updates,
- legend,
- opacity control if useful.

Avoid opaque overlays that completely hide buildings and roads.

---

# 28. Flood Depth

If the backend provides a spatial depth product, display it using an appropriate visual mapping.

The legend should show:

```text
0.0 m
...
maximum
```

The exact range must come from actual result data or a documented visualization scale.

Do not hardcode a misleading maximum.

---

# 29. Flood Animation

The timeline controls the dynamic flood layer.

Conceptually:

```text
timeline time
      ↓
selected timestamp
      ↓
fetch/use result
      ↓
update Cesium flood layer
```

The update should be efficient.

Do not reload all static layers.

---

# 30. Timeline

The timeline should support:

- play,
- pause,
- seek,
- previous,
- next,
- current timestamp,
- optional playback speed.

Example:

```text
◀   ▶   ━━━━━━━●━━━━━━━━   2×
                  Dec 4 08:00
```

The timeline should be driven by backend-provided timestamps.

---

# 31. Timeline State

Store:

```text
currentTimestamp
isPlaying
playbackSpeed
availableTimestamps
```

The timeline should not invent timestamps.

---

# 32. Timeline Data Loading

Prefer prefetching or caching adjacent time slices.

Example:

```text
current
   +
next
   +
previous
```

This makes playback smoother.

Do not download the entire simulation's full spatial dataset into browser memory if unnecessary.

---

# 33. Simulation Controls

The simulation panel should allow:

- scenario selection,
- scenario metadata inspection,
- run simulation,
- status display.

Example:

```text
Scenario
[Michaung 2023 ▼]

Rainfall
282.835 mm

[ Run Simulation ]
```

---

# 34. Simulation Button Behaviour

When idle:

```text
RUN SIMULATION
```

During execution:

```text
RUNNING...
```

After completion:

```text
SIMULATION COMPLETE
```

On failure:

```text
RETRY SIMULATION
```

Do not allow repeated accidental simulation submissions while one is already running unless concurrency is explicitly supported.

---

# 35. Simulation Progress

Show a clear progress indicator.

Example:

```text
Preparing model
████░░░░░░░░

Running SWMM
████████░░░░

Processing flood results
██████████░░
```

Progress should reflect backend state.

Do not fake rapid progress merely to make the UI look responsive.

---

# 36. Scenario Metadata

Before running, display useful information:

```text
Michaung 2023
Historical rainfall
Dec 2–5, 2023
Total rainfall: 282.835 mm
Peak intensity: 23.35 mm/hr
Source: NASA GPM IMERG
```

Exact metadata should come from the API.

---

# 37. KPI Dashboard

The KPI dashboard should prioritize a small number of important values.

Possible cards:

```text
TOTAL RAINFALL
282.835 mm

PEAK INTENSITY
23.35 mm/hr

MAX SIMULATED DEPTH
...

AFFECTED BUILDINGS
...

POTENTIAL BOTTLENECKS
...
```

Do not overload the dashboard with every SWMM statistic.

---

# 38. KPI Formatting

Use consistent formatting.

Examples:

```text
282.8 mm
23.35 mm/hr
1.42 m
1,245 buildings
```

Keep units visible.

---

# 39. KPI Provenance

Where appropriate, display a subtle indicator such as:

```text
Model-derived
```

or provide a tooltip/details section.

This is particularly important for flood depth, affected assets, and risk metrics.

---

# 40. Risk Panel

The risk panel should answer:

> "Where should attention be focused?"

It may show:

```text
HIGH
8 locations

MEDIUM
15 locations

LOW
...
```

and a ranked list of important locations.

Clicking a location should ideally focus the 3D camera on it.

---

# 41. Risk Visualization

Risk locations should be represented in the 3D scene.

Possible representations:

- highlighted polygons,
- markers,
- coloured building groups,
- risk zones.

The visual representation must match the backend risk category.

---

# 42. Risk Explanation

For a selected risk location, show the drivers.

Example:

```text
HIGH RISK

Drivers:
• High simulated flood depth
• Significant building exposure
• Drainage stress
```

This is more useful than showing an unexplained score alone.

---

# 43. Bottleneck Panel

The bottleneck panel should show:

```text
Potential Drainage Bottlenecks

C162
High hydraulic stress

C180
High hydraulic stress

...
```

Clicking a bottleneck should focus the camera on its location.

---

# 44. Bottleneck Terminology

Use:

```text
Potential bottleneck
Model-derived
Requires further investigation
```

Avoid:

```text
Confirmed failed drain
```

unless external evidence supports it.

---

# 45. Recommendation Panel

The recommendation panel should translate analysis into actions.

Example:

```text
Priority 1
Investigate high-stress drainage segments.

Priority 2
Prioritize flood-mitigation assessment for highly exposed assets.

Priority 3
Evaluate alternative rainfall scenarios.
```

Recommendations should originate from backend logic.

---

# 46. Asset Inspector

Selecting a building, drain, road, risk location, or flood feature should open an information panel.

Example:

```text
Drain C162

Source ObjectID
5902

Length
3.03 m

Status
Good

Hydraulic status
Potentially stressed
```

The panel should distinguish:

```text
source attribute
```

from:

```text
model-derived result
```

where relevant.

---

# 47. Camera Behaviour

Useful camera actions include:

```text
Reset view
Fit Ward 176
Zoom to selected building
Zoom to selected drain
Zoom to selected risk location
Zoom to flood extent
```

Camera operations should be centralized in:

```text
cesium/camera.ts
```

rather than scattered through components.

---

# 48. Selection Behaviour

The application should have one consistent selection model.

For example:

```text
selectedAsset = {
  type: "drain",
  id: "5902"
}
```

The selected object can then drive:

- inspector,
- highlighting,
- camera focus.

---

# 49. Hover vs Click

Use hover for lightweight information.

Use click for persistent selection.

Example:

```text
Hover → tooltip
Click → details panel
```

Do not require users to hover over thousands of features to find important information.

---

# 50. Viewer Controls

Useful controls:

```text
+ Zoom
− Zoom
Home
Reset Camera
Layer Controls
Legend
Fullscreen
```

Keep controls compact.

---

# 51. Legend

The legend should change based on active visualization.

Examples:

```text
SIMULATED FLOOD DEPTH
0.0 m
0.5 m
1.0 m
1.5 m
...

DRAINAGE STATUS
Normal
Potential stress
Potential bottleneck
```

Never display a legend for a layer that is not active.

---

# 52. Responsive Design

The application should support:

### Desktop

Primary target.

### Laptop

Fully usable.

### Tablet

Basic usability where practical.

Mobile is not a priority for the MVP because the 3D Digital Twin benefits from a larger screen.

---

# 53. Panel Behaviour

Panels should not permanently obscure the Digital Twin.

Use:

- collapsible panels,
- drawers,
- floating cards,
- tabs,
- compact sidebars.

The viewer should remain visible during most interactions.

---

# 54. Loading States

Every data-dependent UI component should have a loading state.

Examples:

```text
Loading scenarios...
Loading Digital Twin...
Loading flood results...
Loading risk analysis...
```

Avoid blank panels that look broken.

---

# 55. Empty States

If data is genuinely unavailable:

```text
Flood results are not available for this simulation.
```

Do not substitute:

```text
0
```

for missing results.

---

# 56. Error States

Example:

```text
Simulation failed

SWMM execution could not be completed.

[ View Details ]
[ Retry ]
```

Do not expose technical stack traces in the primary UI.

An optional developer/details view may expose more information.

---

# 57. Simulation State Synchronization

The frontend should treat the backend as authoritative.

Example:

```text
Backend:
RUNNING

Frontend:
show RUNNING
```

Do not locally assume:

```text
button clicked → simulation completed
```

---

# 58. Polling

The initial MVP may poll:

```text
GET /simulations/{simulationId}
```

at a reasonable interval while the simulation is active.

Stop polling when:

```text
COMPLETED
```

or:

```text
FAILED
```

Do not poll indefinitely.

---

# 59. Query Caching

If using TanStack Query or a similar library:

- cache scenario metadata,
- cache completed simulation summaries,
- cache static GIS data,
- cache risk/bottleneck results,
- cache timeline metadata.

Dynamic time slices may use shorter cache lifetimes.

---

# 60. State Management

A reasonable division is:

### TanStack Query

For:

```text
server state
```

### Zustand or React state

For:

```text
viewer/UI state
```

Example UI state:

```text
layer visibility
selected asset
active panel
current timestamp
camera mode
```

Avoid putting every piece of application state into one global store.

---

# 61. API Types

The frontend should use TypeScript types corresponding to:

```text
06_API_CONTRACT.md
```

Examples:

```typescript
interface Scenario {}
interface Simulation {}
interface SimulationStatus {}
interface SimulationKpis {}
interface RiskLocation {}
interface Bottleneck {}
interface Recommendation {}
```

Do not duplicate incompatible versions of these types.

---

# 62. API Client

Create a centralized client.

Conceptually:

```typescript
apiClient.get(...)
apiClient.post(...)
```

Then feature-specific modules:

```text
scenariosApi
simulationsApi
floodApi
gisApi
riskApi
```

The UI should call these modules/hooks rather than raw HTTP.

---

# 63. API Error Handling

Convert backend errors into user-friendly messages.

Example backend:

```text
SIMULATION_TIMEOUT
```

Frontend:

```text
The flood simulation took too long to complete.
Please try again.
```

Keep the original error code available for debugging.

---

# 64. GeoJSON Loading

When loading GeoJSON:

1. validate response,
2. verify geometry type,
3. verify expected properties,
4. transform if required,
5. add to Cesium,
6. retain a reference for cleanup.

Do not repeatedly create duplicate data sources.

---

# 65. Layer Cleanup

When replacing a dynamic layer:

```text
old flood layer
     ↓
remove
     ↓
new flood layer
```

Do not continuously append new entities on every timeline update.

Otherwise the viewer will accumulate thousands of stale objects.

---

# 66. Flood Timeline Optimization

A bad implementation:

```text
Every slider movement
→ download huge GeoJSON
→ destroy viewer layer
→ recreate everything
```

A better implementation:

```text
Timeline
   ↓
cached/prepared time slice
   ↓
update existing visualization
```

The exact strategy depends on the chosen flood product format.

---

# 67. Large Building Dataset

The building dataset contains approximately:

```text
6,428 features
```

The frontend should be tested with the actual dataset.

If GeoJSON rendering is too slow:

1. measure,
2. optimize,
3. consider tiling,
4. consider 3D Tiles,
5. simplify only when defensible.

Do not prematurely optimize without evidence.

---

# 68. Drainage Dataset

The current Ward 176 source extraction contains:

```text
135 source drain features
```

The web-ready representation may contain more segments because the hydraulic network was reconstructed/split.

Keep source IDs where possible so users can trace model features back to source records.

---

# 69. Data Attribution

The UI should provide a way to inspect data sources.

Potential:

```text
Data Sources
• GCC GIS
• NASA GPM IMERG
• Copernicus DEM
• EPA SWMM
```

Do not claim a source provided a derived product it did not directly provide.

---

# 70. Scientific Transparency

A small "About Model" or "Methodology" panel is recommended.

It can state:

```text
Rainfall:
NASA GPM IMERG

Drainage:
GCC GIS

Terrain:
Copernicus DEM GLO-30

Hydraulic simulation:
EPA SWMM 5.2.4

Flood visualization:
Model-output spatial post-processing
```

This is valuable during academic demonstration.

---

# 71. Flood Disclaimer

The UI should clearly distinguish:

```text
Simulated / model-derived
```

from:

```text
Observed
```

Especially for:

- flood depth,
- flood extent,
- affected assets,
- risk,
- bottlenecks.

---

# 72. Model Limitation UI

A concise methodology/disclaimer area may state:

> "Flood results are simulation-derived and depend on the current Ward 176 drainage representation, rainfall scenario, terrain data, and modelling assumptions."

This is preferable to hiding limitations.

---

# 73. Scenario Comparison UI

If implemented, comparison can use:

```text
Scenario A | Scenario B
```

with:

- rainfall,
- maximum depth,
- affected assets,
- bottlenecks,
- risk.

The 3D view may support synchronized comparison later.

Do not let comparison complexity delay the core simulation workflow.

---

# 74. Accessibility

Use:

- semantic buttons,
- readable labels,
- keyboard navigation where practical,
- ARIA labels for icon-only controls,
- sufficient contrast,
- visible focus states.

Do not rely exclusively on colour to communicate flood/risk categories.

---

# 75. Frontend Security

Never put:

```text
AWS_SECRET_ACCESS_KEY
database password
private credentials
```

in the frontend.

Anything shipped to the browser must be treated as public.

Use backend endpoints or signed URLs for protected resources.

---

# 76. Environment Configuration

Frontend environment variables may include:

```text
VITE_API_BASE_URL
VITE_CESIUM_ION_TOKEN
```

Only public/browser-safe values belong in the frontend environment.

Never expose backend secrets.

---

# 77. Cesium Token Handling

If a Cesium Ion token is required:

- store it as an environment variable,
- do not commit it to source control,
- use a restricted/public-safe token appropriate to the deployment.

If the implementation can avoid unnecessary external Cesium services for the academic MVP, that may simplify deployment.

---

# 78. Performance Budget Mindset

The frontend should prioritize:

```text
Fast initial UI
Fast 3D scene
Smooth timeline
Responsive controls
```

Avoid:

- unnecessary re-renders,
- repeated parsing,
- duplicate geometry,
- huge React state objects,
- expensive calculations in render functions.

---

# 79. React Performance

Avoid:

```tsx
useMemo(...)
useCallback(...)
memo(...)
```

everywhere without evidence.

First build correct code.

Then profile.

Optimize actual bottlenecks.

---

# 80. Cesium Performance

Prefer Cesium-native mechanisms for large spatial datasets.

Avoid creating thousands of independent React components for geographic features.

React should control the application.

Cesium should render the scene.

---

# 81. Browser Memory

Do not keep every historical flood time slice fully expanded in memory if the simulation contains many spatial features.

Prefer:

```text
current slice
+
small cache
```

unless profiling proves full preloading is safe.

---

# 82. Frontend Logging

During development, useful logs may include:

```text
simulation created
simulation status changed
flood layer loaded
timeline changed
asset selected
```

Avoid excessive console noise in production.

---

# 83. Debug Mode

A developer/debug panel can optionally expose:

```text
simulation ID
model version
processing version
current timestamp
API endpoint
Cesium layer states
```

This should not clutter the normal academic presentation.

---

# 84. Testing

## Unit tests

Test:

- formatting,
- state transitions,
- API transformations,
- timeline utilities.

## Component tests

Test:

- simulation button,
- KPI panel,
- layer controls,
- risk panel,
- error states.

## Integration tests

Test:

```text
frontend API client
      ↓
backend
```

## End-to-end

Test:

```text
open app
→ select scenario
→ run
→ wait
→ view flood
→ move timeline
→ inspect result
```

---

# 85. Frontend Development Order

Build in this order:

## Phase 1 — Shell

```text
React app
Header
layout
basic styling
```

## Phase 2 — Cesium

```text
Viewer
terrain
ward
buildings
roads
drains
```

## Phase 3 — Scenario

```text
scenario API
scenario selector
metadata
```

## Phase 4 — Simulation

```text
run button
simulation status
polling
```

## Phase 5 — Results

```text
flood
timeline
KPIs
```

## Phase 6 — Decision Support

```text
risk
bottlenecks
recommendations
```

## Phase 7 — Polish

```text
asset inspector
animations
loading/error states
responsive layout
```

## Phase 8 — Optimization

```text
profiling
caching
large-layer optimization
```

## Phase 9 — AWS

```text
production configuration
deployment
```

---

# 86. Demo-First Principle

The application must reach a demonstrable state quickly.

The first major milestone should be:

```text
3D Ward 176
+
Scenario selector
+
Run simulation
+
Flood result
+
Timeline
```

Do not spend days polishing dashboard cards before the Digital Twin works.

---

# 87. Visual Design Principle

The product should look like a professional Smart City monitoring/decision-support application.

Aim for:

- restrained visual hierarchy,
- clear typography,
- meaningful icons,
- clean cards,
- subtle borders,
- readable map overlays,
- minimal clutter.

Avoid:

- excessive gradients,
- huge decorative animations,
- unnecessary glassmorphism,
- gaming-style interfaces,
- visual effects that obscure the map.

---

# 88. Colour Semantics

Use colour consistently.

For example:

```text
Flood severity → one coherent scale
Risk severity → consistent severity hierarchy
System status → consistent status colours
```

Do not use arbitrary colours for the same semantic category in different components.

The exact palette is a design decision and can evolve.

---

# 89. Flood Colour Accessibility

Flood depth should not rely solely on colour.

Where practical, pair colour with:

- legend values,
- labels,
- tooltips,
- numerical inspection.

Risk categories should also be understandable without colour alone.

---

# 90. Camera Starting Position

On application startup, the camera should frame Ward 176 and provide enough context to recognize:

- Velachery,
- the urban area,
- the Digital Twin extent.

Do not start with an arbitrary globe-wide view.

---

# 91. Camera After Simulation

After simulation completion, the application may optionally:

```text
fit flood extent
```

or keep the user's current view.

Prefer not to forcibly move the camera every time the timeline changes.

---

# 92. Camera on Selection

When the user selects:

```text
risk location
bottleneck
building
drain
```

provide a "focus" action or automatically focus only when appropriate.

Do not constantly jerk the camera during passive interactions.

---

# 93. URL / Navigation State

The MVP does not need a complex routing system.

However, if useful, the application may eventually encode:

```text
selected simulation
selected timestamp
```

in the URL.

This is optional.

---

# 94. Offline Development

The frontend should be able to develop against:

```text
localhost backend
```

without requiring AWS.

Static project assets should have a local development path.

---

# 95. Mock Data

Mock data may be used for isolated UI development.

However:

> **The final demo must use real backend/project data.**

Do not accidentally leave mock data enabled in production.

Use an explicit development flag if mocks are needed.

---

# 96. Frontend Scientific Integrity

The frontend must never visually imply greater scientific certainty than the backend provides.

Examples:

Bad:

```text
EXACT FLOOD DEPTH
```

Better:

```text
SIMULATED FLOOD DEPTH
```

Bad:

```text
FAILED DRAIN
```

Better:

```text
POTENTIAL DRAINAGE BOTTLENECK
```

Bad:

```text
OBSERVED FLOOD AREA
```

Better:

```text
MODEL-DERIVED FLOOD EXTENT
```

---

# 97. No Hidden Transformations

Do not silently:

- modify elevations,
- shift geometry,
- change flood depth,
- alter risk scores,
- invent missing assets.

If a visualization transformation is required, it should be documented.

---

# 98. Frontend ↔ API Contract

The frontend must follow:

```text
06_API_CONTRACT.md
```

Do not independently invent:

```text
GET /run
```

if the API contract says:

```text
POST /simulations
```

Do not rename fields casually.

---

# 99. Contract-First Development

Before implementing a frontend feature that depends on backend data:

1. identify the API endpoint,
2. identify the response schema,
3. create/use TypeScript types,
4. implement API client,
5. implement hook,
6. connect UI.

Conceptually:

```text
API Contract
    ↓
Type
    ↓
API Client
    ↓
Hook
    ↓
Component
```

---

# 100. Component Responsibility Rule

Each component should have one clear responsibility.

Examples:

```text
SimulationControls
    → simulation interaction

KpiPanel
    → KPI presentation

LayerControls
    → layer visibility

Timeline
    → temporal control

AssetInspector
    → selected asset details
```

Avoid components that perform unrelated backend and viewer work.

---

# 101. Hook Responsibility Rule

Hooks should encapsulate reusable state/data logic.

Examples:

```text
useScenarios()
useSimulation()
useFloodTimeline()
useRisk()
```

Do not put huge amounts of business logic inside hooks.

---

# 102. Utility Responsibility Rule

Utilities should be:

- small,
- deterministic,
- reusable.

Examples:

```text
formatDistance()
formatArea()
formatDepth()
formatTimestamp()
```

Do not hide major application workflows inside utility functions.

---

# 103. Type Safety

Avoid type assertions such as:

```typescript
data as SomeType
```

without validation when the data comes from an external API.

Runtime validation can be introduced with a schema library if necessary.

At minimum, API responses should be handled defensively.

---

# 104. Frontend Error Boundaries

Use an application-level error boundary where practical.

A broken optional panel should not necessarily crash the entire Digital Twin.

For example:

```text
Risk panel fails
      ↓
viewer remains usable
```

---

# 105. Optional Feature Failure

If risk analysis is unavailable but flood visualization works:

```text
Flood → available
Risk → unavailable
```

Do not make the entire application unusable.

The core workflow should degrade gracefully.

---

# 106. Core vs Optional Frontend Features

### Core

```text
3D viewer
scenario
simulation
flood
timeline
```

### Strongly recommended

```text
KPI
risk
bottleneck
recommendations
```

### Optional

```text
scenario comparison
AI assistant
advanced asset analytics
```

---

# 107. Frontend Definition of Done

The frontend is considered MVP-ready when:

1. Application loads without errors.
2. 3D viewer initializes reliably.
3. Ward 176 spatial layers align correctly.
4. Scenario list loads from API.
5. Scenario metadata is displayed.
6. Simulation can be started.
7. Simulation status is visible.
8. Completed results load.
9. Flood visualization appears.
10. Timeline changes the displayed flood state.
11. KPIs display actual backend values.
12. Risk/bottleneck results display where available.
13. Recommendations display where available.
14. Asset inspection works where implemented.
15. Loading/error states work.
16. No simulation values are hardcoded.
17. No raw server paths/secrets are exposed.
18. Performance is acceptable with the real dataset.

---

# 108. Frontend Anti-Patterns

Avoid:

### Giant App component

```text
App.tsx
└── everything
```

### Cesium recreation

```text
every React render
→ new Viewer()
```

### Duplicate layers

```text
every timeline update
→ add another flood layer
```

### API calls in render

Never perform network requests directly during render.

### Hardcoded model output

Never fake simulation results.

### Direct filesystem access

Browser code must never access:

```text
F:\ChennaiFlood-Twin\
```

### Backend knowledge leakage

Frontend should not know:

```text
SWMM command
SWMM executable path
```

---

# 109. Frontend Documentation Rule

If a frontend architectural decision changes:

- update this document,
- update `02_ARCHITECTURE.md` if the system architecture changes,
- update `06_API_CONTRACT.md` if the API changes,
- update the project changelog for significant changes.

---

# 110. Final Frontend Architecture

The intended frontend flow is:

```text
                         USER
                          │
                          ▼
                   React Application
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
       Controls        Dashboard       Cesium Viewer
          │               │                │
          └───────────────┼────────────────┘
                          │
                     API Client
                          │
                          ▼
                    REST API v1
                          │
                          ▼
                       Backend
                          │
                 ┌────────┴────────┐
                 ▼                 ▼
              SWMM/GIS          Results
                 │                 │
                 └────────┬────────┘
                          ▼
                    Frontend Data
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
        Flood            Risk             KPI
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                     Digital Twin
```

---

# 111. Final Non-Negotiable Rules

1. Use React + TypeScript.
2. Use CesiumJS for the 3D Digital Twin.
3. Keep Cesium logic isolated from ordinary React presentation logic.
4. Keep API access centralized.
5. Follow `06_API_CONTRACT.md`.
6. Never hardcode simulation outputs.
7. Never expose backend secrets.
8. Never access backend filesystem paths from the browser.
9. Treat the backend as authoritative for simulation state.
10. Keep static GIS layers separate from dynamic simulation layers.
11. Do not recreate Cesium viewers unnecessarily.
12. Do not accumulate duplicate flood entities during timeline playback.
13. Cache static GIS data.
14. Optimize large datasets based on measurement rather than guesswork.
15. Do not silently modify spatial data in the frontend.
16. Clearly label model-derived flood/risk information.
17. Use explicit loading/error/empty states.
18. Keep the 3D viewer visually central.
19. Prioritize the core simulation workflow before advanced UI features.
20. Keep UI state separate from server state.
21. Use TypeScript types matching the API contract.
22. Prefer deterministic, testable frontend utilities.
23. Make optional feature failures graceful.
24. Test with the actual Ward 176 datasets.
25. Keep the interface academically and scientifically honest.

---

# 112. Final Principle

The frontend should make ChennaiFlood-Twin feel like a coherent Digital Twin rather than a collection of unrelated charts.

The desired experience is:

```text
SEE THE CITY
      ↓
CHOOSE THE RAIN
      ↓
RUN THE MODEL
      ↓
WATCH THE FLOOD
      ↓
MOVE THROUGH TIME
      ↓
SEE WHAT IS AT RISK
      ↓
FIND DRAINAGE HOTSPOTS
      ↓
GET ACTIONABLE INSIGHT
```

The technology should remain behind the experience.

The frontend succeeds when a non-developer can understand the flood scenario and its implications within a few minutes while a technical evaluator can still see that the visualization is connected to the real project data and SWMM model.
