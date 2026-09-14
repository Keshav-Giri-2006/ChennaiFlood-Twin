# ChennaiFlood-Twin — Product Requirements

## 1. Purpose of This Document

This document defines **what the ChennaiFlood-Twin application must do** from a user and product perspective.

It is the functional requirements and MVP scope document for the implementation team.

The project is a software-only academic Smart City prototype. The objective is not to build a production-grade flood forecasting platform, but to demonstrate an end-to-end workflow:

```text
Urban data
   ↓
Rainfall scenario
   ↓
Hydrological / hydraulic simulation
   ↓
Flood result processing
   ↓
3D Digital Twin
   ↓
Risk analysis
   ↓
Decision support
```

This document should be used to decide whether a proposed feature belongs in the product and whether an implementation is complete.

---

# 2. Product Vision

ChennaiFlood-Twin should provide an interactive 3D representation of a localized Chennai urban area and allow users to explore how a rainfall event can affect the area's drainage network and built environment.

The application should turn technically complex simulation data into an understandable Smart City interface.

The final experience should answer questions such as:

- What rainfall scenario is being simulated?
- Where does flooding occur?
- How severe is the simulated flooding?
- How does the flood evolve over time?
- Which buildings and roads are exposed?
- Which drainage locations appear hydraulically stressed?
- Which areas should be prioritized?
- What actions could potentially reduce flood risk?
- How does one rainfall scenario compare with another?

---

# 3. Primary Users

The initial product is primarily designed for:

### 3.1 Academic examiner / evaluator

The examiner should be able to understand the project quickly through the interface and see:

- the 3D Digital Twin,
- the study area,
- urban infrastructure,
- a rainfall scenario,
- simulation execution,
- flood evolution,
- KPIs,
- risk areas,
- drainage bottlenecks,
- and recommendations.

### 3.2 Student / project demonstrator

The demonstrator should be able to:

- select scenarios,
- run simulations,
- inspect results,
- control visualization layers,
- explain model outputs,
- and demonstrate the Smart City decision-support workflow.

### 3.3 Future technical user

A future version could support planners, researchers, or municipal decision-makers, but the current implementation should not claim to be an operational municipal system.

---

# 4. Product Scope

## 4.1 Core MVP

The MVP must provide the following capabilities:

1. Interactive 3D Ward 176 visualization.
2. Terrain visualization.
3. Building visualization.
4. Road visualization.
5. Storm-water drain visualization.
6. Rainfall scenario selection.
7. SWMM simulation execution.
8. Simulation status/progress.
9. Flood result visualization.
10. Flood depth visualization where defensibly derived.
11. Flood timeline / animation.
12. Key performance indicators.
13. High-risk location identification.
14. Drainage bottleneck identification.
15. Basic decision-support recommendations.
16. Scenario comparison.

These features constitute the core demonstrable product.

---

# 5. Product Experience

The intended user journey is:

```text
OPEN APPLICATION
       ↓
VIEW 3D CITY
       ↓
SELECT SCENARIO
       ↓
REVIEW SCENARIO INPUTS
       ↓
RUN SIMULATION
       ↓
WAIT / VIEW PROGRESS
       ↓
SIMULATION COMPLETES
       ↓
EXPLORE FLOOD RESULTS
       ↓
MOVE THROUGH TIME
       ↓
INSPECT LOCATIONS / ASSETS
       ↓
VIEW KPIs
       ↓
VIEW RISK + BOTTLENECKS
       ↓
READ RECOMMENDATIONS
       ↓
COMPARE SCENARIOS
```

The user should not need to understand SWMM internals to use the main interface.

---

# 6. Digital Twin Requirements

## 6.1 3D scene

The main application view should contain a 3D Digital Twin of the study area.

At minimum, the scene should support:

- terrain,
- buildings,
- roads,
- storm-water drains,
- ward boundary,
- flood visualization.

The 3D viewer should be the **primary visual element** of the application.

The dashboard and controls should support the viewer rather than dominate the screen.

---

## 6.2 Terrain

The application should display the prepared Ward 176 terrain.

Requirements:

- load terrain efficiently,
- maintain correct geographic positioning,
- support camera navigation,
- avoid obvious spatial misalignment with buildings and roads,
- provide appropriate terrain exaggeration only if needed for visual comprehension.

Terrain exaggeration is a visualization aid and must not be presented as physically measured elevation amplification.

---

## 6.3 Buildings

Buildings should be displayed as 3D or extruded representations where practical.

Requirements:

- spatially align with the terrain,
- remain visually distinguishable,
- support selection/inspection where feasible,
- allow flood exposure visualization,
- avoid overwhelming the browser with unnecessary visual complexity.

Building height should only be displayed as real measured height if reliable height data exists.

Otherwise, use an explicitly labelled visualization approximation or a defensible extrusion method.

---

## 6.4 Roads

Roads should provide recognizable urban context.

Requirements:

- align with buildings and terrain,
- be toggleable,
- support flood exposure visualization,
- remain visually readable beneath/alongside flood overlays.

---

## 6.5 Storm-water drains

The drainage network should be visible as a dedicated Digital Twin layer.

Requirements:

- toggle visibility,
- distinguish drainage infrastructure from roads/buildings,
- allow inspection of individual drainage links where practical,
- visually highlight hydraulically stressed links,
- visually distinguish normal and flagged/bottleneck links.

The network must reflect the processed project data.

Do not fabricate missing connections simply to make the visualization appear continuous.

---

# 7. Rainfall Scenario Requirements

The application should support scenario-based rainfall input.

## 7.1 Initial scenario

The first scenario should be:

> **Michaung 2023 historical rainfall event**

Using the prepared NASA GPM IMERG rainfall series.

The application should expose understandable scenario information such as:

- scenario name,
- event period,
- total rainfall,
- temporal resolution,
- source,
- and other relevant metadata.

---

## 7.2 Future scenarios

The architecture should allow additional rainfall scenarios without rewriting the frontend.

Potential future scenarios include:

- modified rainfall intensity,
- alternative historical events,
- synthetic design rainfall,
- user-defined rainfall scenarios.

However, these should only be implemented when the underlying data and modelling methodology are available.

---

# 8. Simulation Requirements

## 8.1 Simulation execution

The user should be able to initiate a simulation from the application.

The frontend should send a scenario request to the backend.

The backend should:

1. validate the scenario,
2. prepare the simulation,
3. execute SWMM,
4. monitor success/failure,
5. parse outputs,
6. perform required post-processing,
7. store/retrieve results,
8. expose results through the API.

The frontend must **not** execute SWMM directly.

---

## 8.2 Simulation state

The UI should expose clear states:

```text
IDLE
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

Failure should be explicit:

```text
FAILED
```

A failed simulation must show an understandable error rather than leaving the interface in a permanent loading state.

---

# 9. Flood Visualization Requirements

The main purpose of the simulation output is to make flood behaviour understandable.

## 9.1 Flood extent

The application should visualize areas identified as flooded by the model/post-processing workflow.

The visualization should:

- be spatially aligned,
- be toggleable,
- support temporal updates,
- make the boundary between flooded and non-flooded areas understandable.

---

## 9.2 Flood depth

Where the post-processing methodology supports it, the application should visualize estimated/simulated flood depth.

Depth should be represented spatially rather than only as a number.

Possible interactions:

- hover,
- click,
- legend,
- depth information panel.

The interface should make clear that this is **simulated/derived flood depth**, not a measured flood-depth survey.

---

## 9.3 Flood animation

The application should provide a timeline.

Example:

```text
Dec 2 ───── Dec 3 ───── Dec 4 ───── Dec 5
  ●
```

The user should be able to:

- play,
- pause,
- move forward,
- move backward,
- scrub through time,
- see the current simulation timestamp.

As the timeline changes, the flood visualization should update.

---

# 10. KPI Requirements

The application should provide a concise KPI panel.

Potential KPIs include:

### Rainfall

- total rainfall,
- peak rainfall intensity,
- scenario duration.

### Flood

- maximum simulated flood depth,
- affected area,
- flood duration where defensible,
- affected buildings,
- affected road area/length where defensible.

### Drainage

- stressed links,
- flooded nodes,
- bottleneck candidates,
- affected drainage components.

All KPIs must identify their provenance where ambiguity exists.

---

# 11. Risk Analysis Requirements

The system should identify areas requiring attention.

## 11.1 High-risk locations

A high-risk location may be identified using defensible combinations of:

- simulated flood depth,
- flood duration,
- exposure,
- drainage stress,
- and other available model outputs.

The exact scoring formula should be documented separately.

Do not invent arbitrary risk scores without documenting their basis.

---

## 11.2 Risk visualization

Risk should be represented both:

- spatially in the 3D Digital Twin,
- and textually through a dashboard/panel.

Users should be able to identify the highest-priority areas quickly.

---

# 12. Drainage Bottleneck Requirements

The system should identify drainage infrastructure that appears hydraulically stressed.

Potential indicators include:

- high simulated flow,
- repeated instability/stress,
- capacity utilization,
- surcharge/flooding relationships,
- or other defensible SWMM outputs.

A bottleneck is a **model-derived candidate**, not automatically a confirmed physical engineering defect.

The interface should use terminology such as:

> "Potential drainage bottleneck"

rather than:

> "Confirmed drainage failure"

unless external field evidence exists.

---

# 13. Decision-Support Requirements

The system should convert model results into understandable recommendations.

Example categories:

### Infrastructure

- inspect high-stress drainage segments,
- prioritize drainage-capacity studies,
- investigate junctions with significant hydraulic stress.

### Urban assets

- prioritize buildings/roads exposed to higher simulated flood depth,
- identify areas needing additional flood mitigation attention.

### Planning

- compare scenarios,
- evaluate the effect of rainfall severity,
- prioritize future engineering investigation.

Recommendations should be traceable to model evidence.

---

# 14. Scenario Comparison

The application should eventually allow two scenarios to be compared.

Example:

```text
Scenario A                 Scenario B
──────────                 ──────────
Rainfall                   Rainfall
Peak depth                 Peak depth
Affected area              Affected area
Affected buildings         Affected buildings
Bottlenecks                Bottlenecks
```

The comparison should support:

- numerical KPI comparison,
- spatial comparison,
- and, where feasible, synchronized 3D visualization.

Scenario comparison is an important Smart City feature but should not compromise the stability of the core MVP.

---

# 15. Layer Controls

The user should be able to toggle major layers.

At minimum:

```text
☑ Terrain
☑ Buildings
☑ Roads
☑ Storm-water drains
☑ Ward boundary
☑ Flood extent
☑ Flood depth
☑ Risk areas
☑ Bottlenecks
```

The exact UI can evolve, but layer control must remain easy to understand.

---

# 16. Location Inspection

Users should be able to inspect important objects.

Where feasible:

### Building

Show:
- identifier,
- flood status,
- simulated depth,
- relevant exposure information.

### Drain

Show:
- identifier,
- source ObjectID where available,
- length,
- dimensions,
- simulated hydraulic information,
- stress/bottleneck status.

### Flooded area

Show:
- timestamp,
- estimated depth,
- relevant scenario.

Avoid exposing unnecessary raw engineering attributes to the primary user.

Advanced information may be available in an expandable details panel.

---

# 17. UI Requirements

The interface should be:

- modern,
- clean,
- technically credible,
- visually focused,
- responsive,
- easy to demonstrate.

The layout should generally follow:

```text
┌──────────────────────────────────────────────┐
│ Header / Project / Scenario                   │
├──────────────────────────────────────────────┤
│                                              │
│             3D DIGITAL TWIN                 │
│                                              │
│        Terrain + City + Flood               │
│                                              │
├──────────────────────────────────────────────┤
│ Timeline / Simulation Controls               │
├─────────────────────┬────────────────────────┤
│ KPIs                │ Risk / Bottlenecks    │
├─────────────────────┴────────────────────────┤
│ Recommendations / Decision Support            │
└──────────────────────────────────────────────┘
```

The exact layout may change based on usability testing.

---

# 18. Loading and Error States

Every asynchronous operation must have a clear state.

Examples:

### Loading spatial data

> Loading Digital Twin...

### Running simulation

> Running flood simulation...

### Processing

> Processing hydraulic results...

### Success

> Simulation completed.

### Failure

> Simulation failed. View details.

The application must not silently fail.

---

# 19. Performance Requirements

The Digital Twin contains thousands of building features and substantial geospatial data.

The implementation should therefore:

- avoid unnecessary browser-side processing,
- avoid repeatedly downloading the same datasets,
- cache static data where appropriate,
- use efficient geospatial representations,
- avoid rendering unnecessary geometry,
- avoid blocking the main UI thread,
- load major layers progressively where useful.

Performance optimizations must not corrupt spatial accuracy.

---

# 20. Accessibility / Usability

The MVP should provide:

- readable labels,
- meaningful buttons,
- clear legends,
- obvious active states,
- keyboard-accessible controls where practical,
- sufficient contrast,
- understandable terminology.

The application is primarily a technical demonstration, but the interface should still be usable without developer knowledge.

---

# 21. Out of Scope for the Initial MVP

The following are **not required** for the initial implementation:

- physical IoT sensors,
- Arduino,
- Raspberry Pi,
- drone feeds,
- live CCTV integration,
- real-time sensor telemetry,
- full city-wide Chennai modelling,
- full CFD/Navier-Stokes simulation,
- operational emergency dispatch,
- automatic government warning issuance,
- guaranteed real-time flood forecasting,
- field-verified drainage capacity assessment,
- autonomous infrastructure control.

These may be discussed as future enhancements but must not become hidden dependencies of the MVP.

---

# 22. Scientific Integrity Requirements

The application must distinguish:

### Observed/source data

Examples:
- GCC infrastructure data,
- NASA rainfall data,
- Copernicus DEM.

### Assumptions

Examples:
- infiltration parameters,
- Manning coefficients,
- estimated imperviousness,
- subcatchment construction,
- simplified conduit representation.

### Simulated outputs

Examples:
- SWMM runoff,
- node flooding,
- conduit hydraulic response,
- simulated flood conditions.

### Derived visualization

Examples:
- flood-depth surface,
- flood extent,
- risk score,
- bottleneck ranking.

The UI should never imply that a derived/modelled quantity is a direct field measurement.

---

# 23. Important Hydraulic Model Limitation

The current hydraulic model contains incomplete network connectivity.

Specifically:
- multiple reconstructed network components remain disconnected,
- several outlets are provisional,
- not every physical outfall is known,
- some source invert attributes are internally inconsistent.

Therefore the product must not make claims such as:

> "This is the exact observed flood volume in Ward 176."

Instead use:

> "Simulated flood response under the current model representation."

Similarly, model-derived risk locations should be presented as **simulation-based candidates** until externally validated.

---

# 24. MVP Acceptance Criteria

The MVP can be considered functionally successful when an evaluator can perform the following without developer intervention:

### Step 1

Open the application and see the Ward 176 3D Digital Twin.

### Step 2

See:
- terrain,
- buildings,
- roads,
- drainage network.

### Step 3

Select the Michaung 2023 rainfall scenario.

### Step 4

Start a simulation.

### Step 5

Observe a clear simulation state/progress indicator.

### Step 6

After completion, see flood results in the 3D scene.

### Step 7

Move through the flood timeline and observe changing conditions.

### Step 8

Inspect simulated flood depth / affected assets.

### Step 9

View meaningful KPIs.

### Step 10

View high-risk locations.

### Step 11

View potential drainage bottlenecks.

### Step 12

View recommendations.

### Step 13

Compare scenarios if the scenario-comparison feature has been implemented.

---

# 25. Demonstration Priority

If implementation time becomes limited, prioritize features in this order:

## Priority 1 — Must work

1. 3D Digital Twin
2. Ward 176 spatial layers
3. Rainfall scenario
4. SWMM simulation
5. Flood visualization
6. Timeline

## Priority 2 — Strongly recommended

7. KPIs
8. Risk visualization
9. Drainage bottlenecks
10. Recommendations

## Priority 3 — Enhancement

11. Scenario comparison
12. advanced asset inspection
13. richer analytics
14. AWS deployment refinements
15. advanced AI assistance

A stable Priority 1 system is more valuable than a broken system containing many Priority 3 features.

---

# 26. Product Definition of Done

A feature is considered complete only when:

1. It works end-to-end.
2. It uses real project data where applicable.
3. It handles loading and failure states.
4. It does not introduce hardcoded simulation results.
5. It does not silently fabricate missing data.
6. It is integrated with the appropriate backend/API boundary.
7. It is visually understandable.
8. It has been tested with the actual project dataset.
9. Its assumptions are documented where necessary.
10. It does not contradict the scientific scope defined in `00_PROJECT_CONTEXT.md`.

---

# 27. Guiding Product Principle

The application should optimize for:

> **"A convincing, understandable, technically defensible Smart City demonstration."**

It does not need to simulate every physical process in Chennai.

It needs to demonstrate a coherent chain from:

```text
REAL URBAN DATA
      ↓
RAINFALL SCENARIO
      ↓
HYDRAULIC MODEL
      ↓
FLOOD RESPONSE
      ↓
3D DIGITAL TWIN
      ↓
RISK INFORMATION
      ↓
DECISION SUPPORT
```

Every major feature should strengthen this chain.
