# ChennaiFlood-Twin — CesiumJS Digital Twin Specification

## 1. Purpose

This document defines the implementation rules for the **3D Digital Twin visualization layer** of ChennaiFlood-Twin.

It is the detailed CesiumJS context document for Claude.

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
```

This document focuses specifically on:

- CesiumJS,
- 3D city visualization,
- terrain,
- buildings,
- roads,
- drainage,
- flood visualization,
- time animation,
- risk overlays,
- bottlenecks,
- selection,
- camera behaviour,
- performance,
- and Digital Twin presentation.

---

# 2. Digital Twin Definition

For this project, the Digital Twin is:

> **A geospatial 3D representation of the Ward 176 urban environment linked to simulation-derived flood, drainage, risk, and decision-support information.**

It consists of:

```text
Physical/geospatial representation
          +
Hydraulic simulation
          +
Temporal state
          +
Analytical overlays
          +
Interactive decision support
```

It is not a claim that every physical process in Chennai is represented in real time.

---

# 3. Core Digital Twin Scene

The primary scene should represent:

```text
Ward 176
│
├── Terrain
├── Buildings
├── Roads
├── Storm-water drains
├── Ward boundary
├── Flood extent/depth
├── Risk
└── Bottlenecks
```

The scene should feel like one integrated system rather than separate map layers.

---

# 4. Geographic Focus

The pilot study area is:

> **Ward 176, Velachery, Chennai**

The Digital Twin should initially frame the Ward 176 study area.

The broader Chennai context may be shown when useful, but the detailed Digital Twin should remain focused on the selected pilot area.

---

# 5. Primary Technology

Use:

> **CesiumJS**

The application is primarily a web-based 3D Digital Twin.

React controls:

- application state,
- panels,
- buttons,
- data fetching,
- interaction state.

Cesium controls:

- globe/scene,
- camera,
- geographic primitives,
- terrain,
- spatial entities,
- 3D visualization.

---

# 6. Architectural Boundary

Use this separation:

```text
React
  │
  ├── UI
  ├── state
  └── API
       │
       ▼
Cesium Controller
  │
  ├── viewer
  ├── layers
  ├── camera
  ├── selection
  └── animation
```

Do not put large amounts of Cesium imperative logic directly inside React JSX.

---

# 7. Viewer Lifecycle

The Cesium Viewer should normally be created once.

Conceptually:

```text
React mount
     ↓
initialize viewer
     ↓
configure scene
     ↓
load static layers
     ↓
retain viewer
     ↓
update dynamic layers
     ↓
React unmount
     ↓
destroy viewer
```

Do not recreate the viewer whenever:

- a KPI changes,
- a panel opens,
- the selected timestamp changes,
- a layer toggles.

---

# 8. Viewer Manager

Create a centralized viewer manager/controller.

Possible responsibilities:

```text
createViewer()
destroyViewer()
getViewer()
resize()
setBaseView()
```

The exact implementation can vary.

The important rule is that viewer lifecycle is centralized.

---

# 9. Layer Manager

Use a dedicated layer manager.

Conceptually:

```text
DigitalTwinLayerManager
│
├── terrain
├── wardBoundary
├── buildings
├── roads
├── drains
├── flood
├── risk
└── bottlenecks
```

The manager should know how to:

```text
load
show
hide
update
remove
```

each layer.

---

# 10. Static vs Dynamic Layers

## Static

Loaded once:

```text
Terrain
Ward boundary
Buildings
Roads
Base drains
```

## Dynamic

Changed by simulation/timeline:

```text
Flood
Risk
Bottlenecks
Hydraulic stress
```

Never reload static layers on every timeline update.

---

# 11. Layer State

The application should maintain explicit visibility state.

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

This is UI/viewer state.

It is not SWMM state.

---

# 12. Terrain Source

The current prepared terrain is based on:

> **Copernicus DEM GLO-30**

The Ward 176 clipped terrain is:

```text
ward176_dem.tif
```

The source DEM is:

```text
EPSG:4326
```

The modelling workflow may use:

```text
EPSG:32644
```

for metric spatial processing.

The web visualization should use the coordinate system expected by the chosen Cesium terrain representation.

---

# 13. DEM Limitation

Copernicus GLO-30 is a DSM-derived product.

Therefore it may contain:

- buildings,
- vegetation,
- surface objects.

Do not describe it as a perfectly surveyed bare-earth terrain model.

---

# 14. Terrain Visualization

The terrain should provide:

- recognizable local relief,
- correct geographic placement,
- a useful 3D foundation for buildings and flood visualization.

If terrain exaggeration is used:

> It is only a visual aid.

Never modify the underlying elevation values solely to make the scene look dramatic.

---

# 15. Terrain Exaggeration

If used, expose it as a visualization setting.

Example:

```text
Terrain exaggeration: 1.5×
```

The UI should not imply that the real terrain is 1.5× steeper.

For academic presentation, subtle exaggeration is preferable to extreme distortion.

---

# 16. Ward Boundary

The Ward 176 boundary should be displayed as a clean reference layer.

Recommended behaviour:

```text
default: visible
toggle: available
```

It can use:

- polygon outline,
- translucent fill,
- or both.

Do not use a heavy fill that obscures the city.

---

# 17. Buildings

The current source building dataset contains approximately:

```text
6,428 features
```

The Digital Twin should display these buildings as 3D/extruded urban objects where performance permits.

---

# 18. Building Rendering Strategy

Start with the simplest performant approach.

Potential options:

```text
GeoJSON + polygon extrusion
```

or:

```text
Cesium primitives
```

If performance becomes inadequate, evaluate:

```text
3D Tiles
```

Do not introduce 3D Tiles prematurely without profiling.

---

# 19. Building Geometry

Buildings should preserve the source footprint geometry as closely as practical.

Do not:

- randomly simplify footprints,
- shift footprints,
- invent building geometry.

Any simplification should be a documented visualization optimization.

---

# 20. Building Heights

The current project data does not establish authoritative surveyed building heights.

Therefore:

> Do not present estimated building extrusion heights as measured building heights.

If heights are needed for 3D visualization, label the representation appropriately or use a conservative visualization strategy.

---

# 21. Building Selection

A building should be selectable.

Selection should allow:

```text
click building
      ↓
highlight
      ↓
open Asset Inspector
```

The inspector may display:

- asset ID,
- source attributes,
- simulation-derived exposure,
- risk information.

---

# 22. Building Flood Exposure

Buildings may be visually updated after simulation.

Possible states:

```text
Not affected
Affected
High exposure
```

The backend should provide the underlying classification.

Do not duplicate the complete exposure algorithm in the frontend.

---

# 23. Road Layer

The current Ward 176 carriageway dataset contains approximately:

```text
301 polygon features
```

Roads should be visible enough to provide urban context.

They should remain visually subordinate to:

- flood,
- risk,
- selected assets.

---

# 24. Road Flood Exposure

If backend processing identifies affected roads, the frontend may highlight them.

Possible representation:

```text
normal road
     ↓
affected road
```

Do not infer affected status solely from visual proximity to flood polygons unless the backend contract explicitly defines that method.

---

# 25. Drainage Layer

The source Ward 176 drainage extraction contains:

```text
135 source features
```

The hydraulic model uses reconstructed/split conduit representations.

The visualization should preserve source identifiers where possible.

---

# 26. Drainage Geometry

The displayed drainage network should reflect the actual processed network.

Do not draw artificial connections merely because two drain endpoints are visually close.

This is especially important because the current network remains fragmented.

---

# 27. Drainage Network Styling

Possible states:

```text
Base drain
Potentially stressed
Potential bottleneck
Selected
```

The base drainage network should be visually subtle when flood results are active.

---

# 28. Drain Selection

Clicking a drain should identify:

```text
source ObjectID
model link ID where available
length
width
depth
status
hydraulic state
```

Source and model identifiers should not be conflated.

---

# 29. Model Link vs Source Object

A single source drain may become:

```text
multiple model conduit pieces
```

Therefore:

```text
sourceObjectId
```

and:

```text
modelLinkId
```

are different concepts.

The frontend must preserve this distinction.

---

# 30. Flood Layer

The flood layer is the primary dynamic Digital Twin layer.

It should communicate:

```text
where flooding occurs
how deep it is
how it changes over time
```

---

# 31. Flood Data Source

Flood visualization must originate from:

```text
SWMM simulation
+
spatial post-processing
```

The frontend does not calculate the hydraulic simulation.

---

# 32. Flood Product

The backend may provide:

```text
flood extent
flood depth
time slices
```

through API endpoints defined in:

```text
06_API_CONTRACT.md
```

The Cesium layer consumes these products.

---

# 33. Flood Visualization Architecture

Conceptually:

```text
Simulation
    ↓
Flood time series
    ↓
Spatial flood product
    ↓
API
    ↓
Cesium flood layer
```

---

# 34. Flood Time Slice

At any selected timestamp:

```text
currentTimestamp
      ↓
flood/timeslice
      ↓
Cesium flood visualization
```

The displayed layer must correspond to that timestamp.

---

# 35. Timeline

The timeline is a core Digital Twin interaction.

It should support:

```text
play
pause
seek
previous
next
speed
```

and display:

```text
current date/time
```

---

# 36. Timeline Source of Truth

The timeline timestamps must come from:

```text
GET /simulations/{simulationId}/flood/timeline
```

or the final equivalent API.

Do not generate arbitrary timeline intervals in the frontend.

---

# 37. Timeline State

Maintain:

```text
availableTimestamps
currentTimestamp
isPlaying
playbackSpeed
```

The timestamp should be represented consistently across:

- React state,
- API queries,
- Cesium animation.

---

# 38. Timeline Playback

Conceptual loop:

```text
PLAY
 ↓
advance timestamp
 ↓
load/use flood slice
 ↓
update Cesium
 ↓
wait appropriate interval
 ↓
next timestamp
```

Do not reload the entire Digital Twin on every frame.

---

# 39. Playback Speed

Possible controls:

```text
0.5×
1×
2×
4×
```

These are playback speeds, not simulation speeds.

The SWMM simulation has already completed.

---

# 40. Timeline Prefetching

To improve playback:

```text
current slice
+
next slice
```

may be prefetched/cached.

Do not preload every large spatial slice by default.

---

# 41. Flood Layer Update Strategy

Avoid:

```text
remove everything
→ recreate all entities
→ repeat
```

on every timestamp.

Prefer:

```text
reuse existing data source/primitives
→ update geometry/properties
```

where practical.

---

# 42. Flood Opacity

Flood overlays should normally be semi-transparent enough to preserve:

- buildings,
- roads,
- drainage,
- terrain.

Allowing the user to adjust opacity is optional but useful.

---

# 43. Flood Legend

The legend should clearly state:

```text
SIMULATED FLOOD DEPTH
```

with units:

```text
m
```

Example:

```text
0.0 m
0.25 m
0.50 m
1.00 m
1.50 m+
```

The actual scale should reflect real result ranges.

Do not hardcode a scale that contradicts the simulation.

---

# 44. Flood Extent vs Depth

These are different products.

### Flood extent

Answers:

> Where is flooding present?

### Flood depth

Answers:

> How deep is the simulated flooding?

Do not use the terms interchangeably.

---

# 45. Flood Depth Representation

Depending on backend output, flood depth may be represented using:

```text
polygons
grid/raster
particles
surface
```

Choose the representation based on the actual backend product.

Do not invent a physically realistic water surface if the backend only provides sparse node-based information.

---

# 46. Node-Based Flood Limitation

SWMM fundamentally models the drainage network in one dimension.

If flood spatialization is derived from node flooding and terrain:

> The resulting spatial flood surface is a model-derived approximation.

The UI should not imply that every pixel/point represents a directly simulated 2D hydraulic cell.

---

# 47. Water Surface Visualization

A visually appealing water surface is acceptable if it represents the derived flood product.

It must not be presented as:

```text
full 2D CFD simulation
```

or:

```text
observed water surface
```

---

# 48. Flood Animation Quality

Animation should prioritize:

```text
smoothness
+
clarity
+
correct temporal ordering
```

It does not need physically continuous frame-by-frame CFD behaviour.

The simulation results are available at discrete timestamps.

---

# 49. Risk Layer

Risk is a secondary analytical overlay.

It should answer:

> Where should decision-makers focus attention?

Possible visual representations:

```text
risk zones
risk markers
building highlights
```

---

# 50. Risk Source

Risk must come from:

```text
backend risk processing
```

not an independent frontend formula.

---

# 51. Risk Categories

Possible categories:

```text
LOW
MEDIUM
HIGH
```

The exact categories are controlled by the backend contract.

---

# 52. Risk Tooltip

A selected risk location should show:

```text
Risk level
Score
Drivers
Timestamp
```

where available.

Example:

```text
HIGH RISK

Score: 0.82

Drivers:
• High simulated depth
• Building exposure
• Drainage stress
```

---

# 53. Bottleneck Layer

Potential drainage bottlenecks are model-derived.

The layer should highlight:

```text
potential hydraulic stress locations
```

---

# 54. Bottleneck Representation

Possible representations:

- highlighted drain segments,
- markers,
- icons,
- pulsing emphasis.

Avoid excessive animation.

A subtle highlight is usually more professional.

---

# 55. Bottleneck Selection

Clicking a bottleneck should display:

```text
Model link ID
Source ObjectID
Severity
Reason
Evidence
```

where available.

---

# 56. Bottleneck Disclaimer

Use wording such as:

```text
Potential drainage bottleneck
```

not:

```text
Failed drain
```

unless external evidence confirms failure.

---

# 57. Hydraulic Stress Visualization

If the backend provides link stress/utilization:

```text
low
medium
high
```

can be represented visually.

The thresholds should come from backend logic.

Do not create separate frontend threshold rules.

---

# 58. Risk + Flood Layer Interaction

Risk and flood can be shown simultaneously.

However, avoid visual overload.

Recommended priority:

```text
Flood
   ↓
Risk
   ↓
Bottlenecks
```

with optional toggles.

---

# 59. Layer Ordering

A reasonable visual ordering is:

```text
Terrain
   ↓
Buildings / Roads
   ↓
Drains
   ↓
Flood
   ↓
Risk
   ↓
Bottlenecks
   ↓
Selection highlight
```

The exact Cesium implementation may differ.

The intent is to preserve visibility of the important analytical overlays.

---

# 60. Selection Highlight

Selected objects should receive a strong visual indication.

For example:

```text
selected drain → highlighted segment
selected building → highlighted footprint
selected risk → highlighted marker
```

Do not permanently modify the underlying data.

---

# 61. Hover Tooltip

Hover may show concise information:

```text
C162
Potential hydraulic stress
```

Click should open the detailed inspector.

Do not show large panels on every mouse movement.

---

# 62. Camera Manager

Camera functionality should be centralized.

Potential functions:

```text
fitWard()
focusBuilding(id)
focusDrain(id)
focusRisk(id)
focusBottleneck(id)
focusFloodExtent()
resetView()
```

---

# 63. Initial Camera

The initial camera should frame Ward 176.

The user should immediately recognize:

```text
urban Chennai
+
Ward 176
```

Avoid starting at a globe-wide scale.

---

# 64. Camera During Timeline

Changing the timeline should not automatically move the camera.

The user's viewpoint should remain stable while the flood changes.

This is critical for comparing temporal changes.

---

# 65. Camera on Analysis Selection

Selecting:

```text
risk location
bottleneck
building
drain
```

may focus the camera.

However, this should be deliberate rather than triggered by every data refresh.

---

# 66. Reset View

Provide a clear:

```text
Reset View
```

action.

It should restore the predefined Ward 176 framing.

---

# 67. Entity Identification

Every rendered feature should have a stable identifier.

Examples:

```text
building:<id>
drain:<objectId>
link:<modelLinkId>
risk:<riskId>
```

This helps selection and debugging.

---

# 68. Source Traceability

Where possible, feature properties should preserve:

```text
sourceObjectId
```

and/or:

```text
modelLinkId
```

This allows:

```text
3D object
    ↓
backend result
    ↓
SWMM link
    ↓
source GIS feature
```

to be traced.

---

# 69. Coordinate Handling

Do not assume all source files use the same CRS.

The backend should ideally provide web-ready coordinates.

The frontend should not perform large-scale GIS reprojection in the browser unless necessary.

---

# 70. GeoJSON Loading

When consuming GeoJSON:

```text
fetch
 ↓
validate
 ↓
load into Cesium
 ↓
retain DataSource reference
```

Keep references so layers can be:

```text
shown
hidden
removed
updated
```

---

# 71. GeoJSON Feature Properties

Do not discard useful properties during loading.

At minimum preserve IDs required for:

- selection,
- inspection,
- backend lookup.

---

# 72. Static Data Caching

Static GIS datasets should be cached.

Example:

```text
Ward boundary → load once
Buildings → load once
Roads → load once
Drains → load once
```

Do not refetch these when:

```text
timeline changes
risk toggles
KPI panel changes
```

---

# 73. Dynamic Data Caching

Dynamic products should be cached by:

```text
simulationId
timestamp
productType
```

Conceptually:

```text
flood:
  sim123:
    08:00 → data
    08:30 → data
```

Do not allow stale results from another simulation to appear.

---

# 74. Simulation Switching

If the user switches simulations:

```text
old dynamic layers
      ↓
remove/clear
      ↓
new simulation
      ↓
load new dynamic products
```

Static city layers remain.

---

# 75. Race Conditions

The frontend must prevent old API responses from overwriting newer state.

Example:

```text
User selects simulation A
User immediately selects simulation B
```

If A finishes after B:

> A's result must not replace B's active view.

Use query cancellation, request keys, or equivalent mechanisms.

---

# 76. Viewer State vs Simulation State

Keep separate.

### Viewer state

```text
camera
layers
selection
```

### Simulation state

```text
simulationId
status
scenario
currentTimestamp
results
```

Do not merge these into one giant object.

---

# 77. Cesium Clock

Cesium's `Clock` can optionally be used for temporal animation.

However, application state remains the source of truth for the selected simulation timestamp.

Do not allow Cesium's clock to silently drift away from React/API state.

---

# 78. Cesium Animation

There are two valid approaches:

### Application-controlled

```text
React timer
→ timestamp
→ update layer
```

### Cesium Clock

```text
Cesium Clock
→ sampled/dynamic properties
```

Choose whichever produces the cleaner implementation for the selected flood representation.

Do not combine both unnecessarily.

---

# 79. Water/Flood Animation

If using Cesium time-dynamic properties, ensure:

```text
simulation start/end
```

match the actual simulation timeline.

Do not invent a separate visualization timeline.

---

# 80. 3D City Feel

The scene should communicate:

```text
CITY
+
TERRAIN
+
INFRASTRUCTURE
+
WATER
```

Useful visual details include:

- subtle building extrusion,
- clear roads,
- visible drains,
- terrain relief,
- translucent flood,
- selected asset highlights.

Do not overdecorate the scene.

---

# 81. Optional Base Map

A base map can provide geographic context.

However, it should not overpower the project-specific layers.

The primary story should remain:

> Ward 176 flood Digital Twin.

---

# 82. External Cesium Services

If Cesium Ion services are used:

- configure credentials through environment variables,
- never commit tokens,
- keep external dependencies documented.

If local/project-hosted assets are sufficient, prefer them where appropriate.

---

# 83. Building Performance Strategy

Start with:

```text
6,428 actual buildings
```

and test performance.

If acceptable:

> keep the straightforward representation.

If not:

```text
profile
 ↓
optimize
 ↓
consider tiling
```

Do not reduce the building count arbitrarily.

---

# 84. Drain Performance

The drainage dataset is comparatively small.

The current source has:

```text
135 features
```

so standard Cesium entities/primitives should generally be sufficient for the initial MVP.

The reconstructed model may contain more segments; still measure before introducing complex tiling.

---

# 85. Road Performance

Approximately:

```text
301 road/carriageway features
```

should be manageable in the initial Cesium representation.

---

# 86. Flood Performance

Flood products may become the largest dynamic visualization challenge.

Optimize:

```text
geometry size
time-slice loading
cache
entity count
update frequency
```

Do not sacrifice correctness just to achieve animation speed.

---

# 87. Progressive Loading

Recommended startup sequence:

```text
Initialize UI
    ↓
Initialize Cesium
    ↓
Frame Ward 176
    ↓
Load terrain
    ↓
Load buildings/roads
    ↓
Load drains
    ↓
Enable scenario controls
```

Heavy dynamic results can load after the core city is visible.

---

# 88. Viewer Loading Indicator

Show a compact status such as:

```text
Loading Digital Twin...
```

Optionally provide per-layer progress:

```text
Terrain       ✓
Buildings     ✓
Roads         ✓
Drainage      ...
```

Do not block the entire application unnecessarily while a secondary layer loads.

---

# 89. Graceful Layer Failure

If buildings fail but flood results work:

```text
Buildings unavailable
Flood available
```

The application should continue functioning.

---

# 90. Flood Failure

If flood results cannot load:

```text
Simulation completed
Flood visualization unavailable
```

The dashboard can still show:

- scenario,
- simulation status,
- available KPIs,
- other results.

Do not crash the entire viewer.

---

# 91. Risk Failure

If risk processing fails:

```text
Risk unavailable
```

while the flood Digital Twin remains usable.

---

# 92. Data Quality Indicators

Where useful, the UI can show a small data-quality indicator.

Example:

```text
Drainage connectivity: Incomplete
Outfalls: Provisional
Flood product: Model-derived
```

This increases academic credibility.

---

# 93. Methodology Overlay

Optional "Methodology" panel:

```text
Terrain
Copernicus DEM GLO-30

Drainage
GCC GIS

Rainfall
NASA GPM IMERG

Hydraulic model
EPA SWMM 5.2.4

Visualization
CesiumJS
```

This is strongly recommended for the project demo.

---

# 94. Flood Volume Presentation

Do not display:

```text
197.876 million L
```

as:

```text
Observed flood volume
```

if that model output is shown at all.

Use:

```text
Simulated flooding volume
```

and provide context that the current network representation is incomplete.

---

# 95. Model Limitations Panel

Recommended concise text:

```text
Model note:
Flood outputs are simulation-derived and depend on
the available drainage network, rainfall scenario,
terrain data, and modelling assumptions.
```

This should be accessible without dominating the main UI.

---

# 96. Visual Hierarchy During Demo

During a project demonstration, prioritize:

```text
1. Flood
2. Timeline
3. KPIs
4. Risk
5. Bottlenecks
6. Recommendations
7. Raw technical details
```

The technical details remain available through inspection/methodology panels.

---

# 97. Demo Scenario

The ideal demo sequence:

```text
1. Open Ward 176 Digital Twin
2. Show terrain/buildings/roads/drains
3. Select Michaung 2023
4. Show rainfall metadata
5. Run simulation
6. Show simulation progress
7. Simulation completes
8. Show flood extent
9. Start timeline
10. Watch flood evolve
11. Pause at peak
12. Show KPIs
13. Toggle risk
14. Inspect bottleneck
15. Show recommendation
```

This sequence should work smoothly.

---

# 98. Demo Camera Sequence

Recommended:

```text
Initial:
Ward overview

During flood:
same camera

At peak:
zoom to affected area

Risk:
focus high-risk location

Bottleneck:
focus selected drain
```

Avoid excessive camera movement.

---

# 99. Screenshot-Friendly State

The application should have a visually strong state suitable for:

- project presentation,
- screenshots,
- demo videos.

A good state includes:

```text
3D city
+
visible flood
+
timeline
+
KPIs
+
selected risk/bottleneck
```

---

# 100. Digital Twin Visual Semantics

The frontend should make it visually obvious that:

```text
Buildings = city assets
Roads = transportation
Drains = drainage infrastructure
Flood = simulated water impact
Risk = analytical priority
Bottleneck = hydraulic hotspot
```

Do not make every layer use the same visual style.

---

# 101. Interaction Priority

Primary interactions:

```text
camera
layer toggles
scenario
run
timeline
selection
```

Secondary:

```text
advanced filters
comparison
methodology
debug
```

---

# 102. Avoid Visual Overload

Never enable every analytical layer with maximum opacity by default.

Recommended default:

```text
Terrain        ON
Buildings      ON
Roads          ON
Boundary       ON
Drains         ON/subtle
Flood          OFF until simulation
Risk           OFF
Bottlenecks    OFF
```

After simulation:

```text
Flood          ON
```

Risk/bottlenecks remain optional.

---

# 103. Layer Control Design

Layer controls should be simple:

```text
☑ Terrain
☑ Buildings
☑ Roads
☑ Drainage
☑ Ward Boundary
☑ Flood
☐ Risk
☐ Bottlenecks
```

The exact UI can be a panel/drawer.

---

# 104. Opacity Controls

Useful for:

```text
Flood
Buildings
Risk
```

but avoid exposing too many sliders.

A single flood-opacity slider is sufficient for the MVP.

---

# 105. Selection Persistence

When a user opens the inspector:

```text
selected asset remains highlighted
```

until:

```text
new asset selected
```

or:

```text
selection cleared
```

---

# 106. Selection Clearing

Provide:

```text
Clear Selection
```

or allow clicking empty space.

Do not leave stale inspector data visible after the selected object disappears.

---

# 107. API-Driven Digital Twin

The Cesium scene should be data-driven.

Bad:

```text
frontend contains hardcoded flood polygons
```

Good:

```text
backend result
→ API
→ Cesium
```

---

# 108. No Frontend Hydraulics

Do not implement SWMM equations in the browser.

Do not calculate:

- runoff,
- conduit flow,
- hydraulic continuity,
- infiltration,
- flood depth

in the frontend.

The frontend visualizes backend results.

---

# 109. No Frontend Risk Engine

Do not implement the official risk algorithm independently in React.

The frontend may perform trivial display calculations such as:

```text
format percentage
```

but not scientific classification.

---

# 110. No Geometry Fabrication

Do not:

- connect nearby drains,
- create fake outfalls,
- invent flood polygons,
- invent buildings,
- invent roads.

If a product is unavailable, show that it is unavailable.

---

# 111. Spatial Alignment Validation

Before declaring the Digital Twin ready:

```text
[ ] Ward boundary aligns
[ ] Buildings align with ward
[ ] Roads align with buildings
[ ] Drains align with roads/urban area
[ ] Terrain aligns with all layers
[ ] Flood aligns with study area
[ ] Risk aligns with flood/assets
[ ] Bottlenecks align with drainage
```

Spatial misalignment is a major defect.

---

# 112. Coordinate Validation

If layers appear shifted:

1. check source CRS,
2. check backend transformation,
3. check GeoJSON coordinates,
4. check Cesium interpretation,
5. verify axis order,
6. only then adjust code.

Do not compensate for an unknown CRS problem by manually shifting geometry.

---

# 113. Cesium Entity Cleanup

Every dynamically created:

```text
Entity
DataSource
Primitive
```

should have a lifecycle.

When no longer needed:

```text
remove
destroy
or reuse
```

as appropriate.

---

# 114. Memory Leak Prevention

Watch for:

```text
repeated DataSource.add()
repeated primitive creation
unremoved event handlers
unremoved clock listeners
```

especially during:

- timeline playback,
- simulation switching,
- layer toggling.

---

# 115. Event Handler Cleanup

Cesium event handlers/listeners must be removed when the relevant component/controller is destroyed.

Otherwise the same click may trigger multiple callbacks after repeated initialization.

---

# 116. Render Loop

Do not create custom animation/render loops unless required.

Cesium already manages rendering.

Use its lifecycle appropriately.

---

# 117. Mobile / Small Screens

The primary target is desktop.

On smaller screens:

```text
viewer remains usable
panels collapse
timeline remains accessible
```

Do not spend excessive development effort on mobile-specific 3D optimization.

---

# 118. Accessibility in 3D

The 3D viewer cannot communicate everything through visual geometry alone.

Important information should also be accessible through:

- panels,
- tables,
- text labels,
- legends.

For example, a high-risk building should have textual risk information available.

---

# 119. Keyboard Accessibility

All non-map controls should support keyboard interaction.

Examples:

```text
Run Simulation
Layer toggles
Play/Pause
Timeline
Inspector
```

Cesium mouse interactions are supplementary.

---

# 120. Performance Testing

Test with real project data:

```text
6,428 buildings
301 roads
135 source drains
35 subcatchments
182 SWMM links
```

Measure:

- initial load,
- scene FPS,
- memory,
- timeline performance,
- layer toggle performance.

---

# 121. Performance Optimization Order

If performance is poor:

```text
1. Profile
2. Identify bottleneck
3. Cache/reuse
4. Reduce duplicate objects
5. Optimize geometry
6. Consider tiling
7. Re-test
```

Do not immediately remove data.

---

# 122. Frontend / Backend Spatial Contract

The backend should provide web-ready spatial products where possible.

Preferred:

```text
backend
  ↓
validated spatial product
  ↓
frontend
  ↓
Cesium
```

rather than:

```text
raw source GIS
  ↓
browser performs complex GIS processing
```

---

# 123. Digital Twin Data Flow

Complete flow:

```text
GCC GIS
   │
   ├── buildings
   ├── roads
   └── drains
        │
        ▼
   processed spatial data
        │
        ├──────────────┐
        ▼              ▼
     backend        Cesium static
        │
        ▼
      SWMM
        │
        ▼
   hydraulic results
        │
        ▼
 spatial flood processing
        │
        ├───────┬────────┬──────────┐
        ▼       ▼        ▼          ▼
      Flood    Risk   Bottlenecks  KPIs
        │       │        │          │
        └───────┴────────┴──────────┘
                    │
                    ▼
                   API
                    │
                    ▼
                 Cesium
```

---

# 124. Digital Twin Definition of Done

The Cesium layer is MVP-ready when:

1. Viewer initializes reliably.
2. Ward 176 is correctly framed.
3. Terrain is correctly positioned.
4. Buildings align.
5. Roads align.
6. Drainage aligns.
7. Layers can be toggled.
8. Objects can be selected.
9. Simulation can be selected/run.
10. Flood results load.
11. Flood changes with timeline.
12. Flood legend is correct.
13. Risk can be displayed.
14. Bottlenecks can be displayed.
15. Camera focus works.
16. No duplicate dynamic layers accumulate.
17. Real project data is used.
18. Missing products fail gracefully.
19. Scientific labels are accurate.
20. Performance is acceptable on the target desktop.

---

# 125. Final Digital Twin Architecture

The final scene should conceptually be:

```text
                         CESIUMJS
                            │
                 ┌──────────┴──────────┐
                 │                     │
             STATIC                  DYNAMIC
                 │                     │
       ┌─────────┼─────────┐      ┌────┼─────────────┐
       ▼         ▼         ▼      ▼    ▼             ▼
    Terrain   Buildings   Roads  Flood Risk      Bottlenecks
                  │         │      │    │             │
                  └────┬────┘      └────┼─────────────┘
                       │                │
                       ▼                ▼
                    Drainage        Simulation
                       │                │
                       └───────┬────────┘
                               ▼
                              API
                               │
                               ▼
                            Backend
                               │
                               ▼
                           SWMM + GIS
```

---

# 126. Final Non-Negotiable Rules

1. CesiumJS is the 3D visualization engine.
2. React owns UI/application state.
3. Keep Cesium lifecycle centralized.
4. Do not recreate the viewer on ordinary state changes.
5. Keep static and dynamic layers separate.
6. Preserve source/model identifiers.
7. Do not fabricate spatial connections.
8. Do not fabricate flood geometry.
9. Do not perform hydraulic simulation in the browser.
10. Do not perform the official risk calculation in the browser.
11. Flood results must be labelled as simulated/model-derived.
12. Risk must be labelled as model-derived.
13. Bottlenecks must be labelled as potential/model-derived.
14. Keep the timeline tied to actual simulation timestamps.
15. Do not move the camera on every timeline update.
16. Do not accumulate duplicate Cesium entities.
17. Clean up event handlers and dynamic layers.
18. Test against the actual Ward 176 datasets.
19. Profile before optimizing.
20. Never solve CRS errors with arbitrary coordinate shifts.
21. Keep the Digital Twin visually centered on Ward 176.
22. Preserve enough textual UI to make visual information accessible.
23. Keep scientific limitations visible.
24. Do not sacrifice data integrity for visual polish.
25. Prefer a convincing, understandable Digital Twin over unnecessary technical complexity.

---

# 127. Final Principle

The Digital Twin should make the project's technical chain visible without making the user understand the underlying implementation.

The user should see:

```text
REAL CITY
   +
REAL GIS DATA
   +
REAL HISTORICAL RAINFALL
   +
HYDRAULIC SIMULATION
   +
TIME
   +
FLOOD
   +
RISK
   +
DECISION SUPPORT
```

and experience it as one coherent interactive system.

The goal is not to create the most complicated 3D scene possible.

The goal is to create the most **credible, understandable, responsive, and demonstrable Digital Twin possible from the available project data**.
