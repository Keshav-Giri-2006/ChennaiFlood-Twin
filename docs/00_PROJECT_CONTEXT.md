# ChennaiFlood-Twin — Project Context

## 1. Project Identity

**Project name:** ChennaiFlood-Twin  
**Full title:** AI-Powered Urban Flood Digital Twin and Decision Support System  
**Course:** BCSE355L — Design of Smart Cities  
**Project type:** 100% software-based academic Smart City prototype

ChennaiFlood-Twin is a localized urban flood simulation, 3D geospatial Digital Twin, and decision-support prototype focused on **Ward 176 in Velachery, Chennai**, with particular relevance to the Ram Nagar / Tansi Nagar area.

The system combines:
- rainfall data,
- terrain/elevation data,
- buildings,
- roads,
- storm-water drainage infrastructure,
- urban subcatchments,
- EPA SWMM hydraulic simulation,
- flood-depth/extent post-processing,
- 3D geospatial visualization,
- risk analysis,
- and decision-support recommendations.

The final system should demonstrate how a Smart City platform can combine heterogeneous urban data and simulation outputs into an interactive Digital Twin for flood scenario analysis.

---

## 2. Core Project Positioning

### What this project IS

ChennaiFlood-Twin is a:

> **localized, scenario-based urban flood Digital Twin and Decision Support System prototype.**

Its main purpose is to allow a user to:
1. select or configure a rainfall scenario,
2. run an urban drainage/hydraulic simulation,
3. process the resulting hydraulic response,
4. visualize flood conditions in a 3D representation of the study area,
5. identify high-risk locations and drainage issues,
6. and obtain decision-support recommendations.

### What this project IS NOT

Do **not** describe or implement it as:
- a physical IoT system,
- an Arduino/Raspberry Pi project,
- a sensor network,
- a drone-based system,
- a real-time physical flood-monitoring network,
- a full CFD/Navier-Stokes 3D flood solver,
- or a replacement for Chennai's official operational flood forecasting systems.

The project is intentionally **software-only**.

The scientifically appropriate terminology is:

> **Hydrological/hydraulic simulation + 3D geospatial Digital Twin visualization.**

Do not claim that SWMM itself performs a full 3D flood simulation.

The intended processing chain is:

```text
Rainfall Scenario
      ↓
EPA SWMM
      ↓
Urban drainage / hydraulic response
      ↓
Flood-depth / flood-extent post-processing
      ↓
3D geospatial Digital Twin
      ↓
Risk analysis + Decision Support
```

---

## 3. Study Area

### Primary study area

**Ward 176, Velachery, Chennai, Tamil Nadu, India**

The pilot area is associated particularly with:
- Ram Nagar,
- Tansi Nagar,
- Velachery,
- and surrounding Ward 176 drainage infrastructure.

The GCC storm-water-drain dataset used for the prototype is primarily associated with **Velachery AGS Colony, Chennai**, with one source feature associated with Puzhuthivakkam.

Ward 176 is used as the initial bounded study area because the available GCC GIS infrastructure data can be spatially connected to the ward boundary.

### Important scope rule

Do not silently expand the study area.

If additional areas are required later, explicitly document:
- why they are required,
- what data is being added,
- and how the expanded spatial extent affects the model.

---

## 4. Technology Direction

The intended technology stack is approximately:

### Frontend
- React
- TypeScript
- CesiumJS
- browser-based interactive visualization
- dashboard/UI components

### Backend
- API-driven application backend
- SWMM execution
- simulation orchestration
- result parsing
- spatial post-processing
- KPI/risk/recommendation generation

### Simulation
- **EPA SWMM 5.2.4**
- Dynamic Wave routing
- urban rainfall-runoff and drainage/hydraulic modelling

### Cloud target
AWS-oriented architecture, potentially including:
- S3
- CloudFront
- API Gateway
- Lambda and/or containerized compute where appropriate
- database/storage services where useful

AWS deployment should follow the needs of the working prototype. Do not add cloud services merely for architectural decoration.

---

## 5. Current Development Status

The project is **past the raw-data acquisition and hydraulic-network cleanup stage**.

The following major stages have already been completed:

### Completed

1. Project directory structure created.
2. GCC GIS drainage data acquired.
3. Ward 176 storm-water-drain dataset extracted.
4. Ward 176 building and carriageway data prepared.
5. Copernicus DEM GLO-30 acquired and clipped to Ward 176.
6. NASA GPM IMERG Final Run rainfall data acquired for the December 2023 Michaung event.
7. Drainage network topology audited.
8. Candidate junctions and conduits reconstructed.
9. Candidate outlets identified conservatively.
10. Subcatchments generated.
11. Initial SWMM model generated.
12. Obvious self-loops / duplicate geometry investigated.
13. Duplicate conduit C182 was removed.
14. Hydraulic reconstruction was performed for selected elevation-conflict junctions.
15. Final targeted hydraulic investigation was completed.
16. Current reconstructed hydraulic candidate was established as the working baseline.

### Current phase

The project is now moving to:

> **Digital Twin + Visualization + Backend/API integration**

Do not restart the drainage reconstruction process unless new evidence requires it.

---

## 6. Project Directory

The current project root is:

```text
F:\ChennaiFlood-Twin\
```

Current high-level structure:

```text
ChennaiFlood-Twin/
├── docs/
├── data_raw/
│   └── gcc/
│
├── data_processed/
│
├── gis/
│
├── simulation/
│
├── backend/
│
└── frontend/
```

The `docs/` directory is the authoritative location for project context, architecture, modelling decisions, and development documentation.

---

## 7. Existing Data

The project currently uses several major data classes.

### 7.1 GCC storm-water drainage

Source:
Chennai Corporation GIS / ArcGIS REST services.

The Ward 176 storm-water-drain dataset contains:
- 135 source drain features,
- polyline geometry,
- drain dimensions,
- start/end coordinates,
- invert elevations,
- material/condition attributes,
- water-flow information,
- drainage detail,
- and related infrastructure attributes.

Important source fields include:

```text
objectid
zone
ward
location
drain_type
cover
drain_len
drain_wid
drain_dep
status
swd_mat
drain_detl
invert_sp
invert_ep
inlet_shp
start/end coordinates
obstacles
```

The source dataset has known inconsistencies in some invert attributes. These have been documented rather than silently corrected.

---

### 7.2 Buildings

Ward 176 building geometry has been prepared.

Current dataset characteristics:
- approximately 6,428 building features,
- approximately 992,000 m² total footprint area,
- predominantly polygon footprints.

Buildings are intended primarily for:
- 3D Digital Twin visualization,
- flood exposure analysis,
- affected-building identification,
- and contextual risk visualization.

---

### 7.3 Roads

Ward 176 carriageway geometry has been prepared.

Current dataset:
- approximately 301 carriageway polygons,
- approximately 268,000 m² total area.

Roads are intended for:
- 3D visualization,
- spatial context,
- flood exposure analysis,
- and decision-support presentation.

---

### 7.4 DEM / Terrain

Source:
**Copernicus DEM GLO-30**

The source DEM is DSM-derived and may include effects from:
- buildings,
- vegetation,
- and other above-ground structures.

Therefore:

> Do not describe the Copernicus DEM as a perfect bare-earth terrain model.

Ward 176 has a clipped DEM prepared for the study area.

The eventual modelling workflow should use an appropriate projected CRS such as **EPSG:32644** where metric spatial calculations are required.

Keep geographic and projected coordinate systems explicit.

Do not replace NoData/outside-mask areas with arbitrary elevation values.

---

### 7.5 Rainfall

Primary historical event:

**Cyclone Michaung — December 2023**

Source:
NASA GPM IMERG Final Run.

Processed rainfall characteristics used in the model include:
- temporal resolution: 30 minutes,
- total event rainfall: approximately **282.835 mm**,
- peak interval intensity: approximately **23.35 mm/hr**,
- event period: December 2–5, 2023.

The rainfall data is currently used as a historical scenario for simulation and demonstration.

Do not describe this single GPM grid cell as a complete dense city-wide rainfall observation network.

---

## 8. SWMM Hydraulic Baseline

The current working hydraulic model is:

```text
simulation/
└── ward176_hydraulic_reconstructed_candidate.inp
```

The model uses:
- EPA SWMM 5.2.4,
- Dynamic Wave routing,
- 35 subcatchments,
- 228 nodes,
- 182 links,
- one rainfall gage,
- the Michaung rainfall series,
- rectangular closed conduit representations based on available GCC dimensions,
- Manning roughness assumptions,
- Green-Ampt infiltration assumptions.

### Important model history

The modelling process included:
- an initial baseline,
- cleanup of obvious self-loops,
- removal of duplicate C182,
- and targeted hydraulic reconstruction.

C182 was removed because it was identified as duplicate geometry.

The following investigated links were deliberately retained:

```text
C162
C166
C174
C175
C180
C086
C190
```

Do not remove or modify these merely because they appear in numerical warning/instability lists.

---

## 9. Hydraulic Reconstruction Decisions

The final targeted investigation established the following:

| Link | Decision |
|---|---|
| C182 | REMOVE — confirmed duplicate |
| C162 | RETAIN — elevation conflict remains |
| C166 | RETAIN — disconnected/incomplete component |
| C174 | RETAIN |
| C175 | RETAIN — source-invert ambiguity |
| C180 | RETAIN — legitimate split geometry |
| C086 | RETAIN |
| C190 | RETAIN |

### C162

C162 is a genuine short GCC segment.

Its source invert information conflicts with neighboring source segments around J122/J124.

The reconstruction was intended to preserve source pipe-end information without inventing a new hydraulic structure.

### C175

C175 is a genuine short segment but its source invert attributes exactly duplicate those of C174 despite different geometry and length.

Possible interpretations include:
- a genuine steep/drop connection,
- inconsistent source metadata,
- or a geometric crossing that should not have been interpreted as a hydraulic junction.

There is insufficient authoritative evidence to choose one.

Therefore:

> **Retain C175. Do not fabricate a correction.**

### C180

C180 is a legitimate split of GCC ObjectID 5916.

It must not be deleted simply because it is short or hydraulically sensitive.

The main uncertainty is at the surrounding junction elevations, particularly J203/J204.

### C166

C166 belongs to an incomplete/disconnected network component.

Its numerical instability must not automatically be interpreted as evidence that the geometry is wrong.

Do not invent a long connection to an outlet.

### C190

C190 is a genuine source segment.

The reconstruction removed the previous SWMM Warning 04 associated with nearly equal node elevations by representing the source/reconstructed pipe-end elevations through conduit offsets.

---

## 10. Current SWMM Run Characteristics

The latest reconstructed candidate run produced approximately:

```text
Runoff continuity error:        -0.018%
Flow routing continuity error:  0.068%

Minimum routing timestep:       0.50 sec
Average routing timestep:       2.39 sec
Maximum routing timestep:      30.00 sec

Average iterations:             2.20
Non-converging steps:           ~0.37%
```

The model produced approximately:

```text
Wet-weather inflow:   271.424 million L
External outflow:       67.405 million L
Flooding loss:         197.876 million L
Final stored volume:     5.958 million L
```

### Critical interpretation rule

**DO NOT call the 197.876 million L SWMM flooding-loss value the observed flood volume of Ward 176.**

The drainage network is still incomplete:
- multiple components are disconnected,
- several outlets are provisional,
- not every physical outfall is known,
- and source drainage data contains elevation/topology uncertainties.

Therefore the flooding-loss value is:

> **model-generated flooding under the current incomplete network representation.**

It may be used as an internal simulation diagnostic, but not as a validated real-world observation.

---

## 11. Provisional Outlets

The drainage-network analysis identified several provisional downstream boundary terminals.

These are:

```text
node125
node98
node140
node94
node88
node97
node213
```

These are **not confirmed physical outfalls**.

Do not describe them as verified real-world discharge points unless new authoritative evidence is obtained.

---

## 12. Subcatchments

A first-pass subcatchment layer has been generated:

```text
data_processed/gis/ward176_subcatchments.geojson
```

and an associated CSV exists under the processed network data.

Current characteristics:
- 35 subcatchments,
- clipped to Ward 176,
- generated using a first-pass spatial partitioning approach,
- imperviousness estimated from building + road overlays,
- DEM/slope-derived attributes included,
- infiltration assumptions included.

These subcatchments are appropriate for the current academic prototype, but should not be presented as official hydrological catchment boundaries.

---

## 13. Digital Twin Goal

The Digital Twin should visually represent the Ward 176 urban environment and overlay dynamic simulation information.

The intended 3D scene is:

```text
Ward boundary
      +
Terrain
      +
Buildings
      +
Roads
      +
Storm-water drains
      +
Flood extent/depth
      +
Simulation timeline
```

The primary 3D technology is:

> **CesiumJS**

The Digital Twin should allow the user to understand:

- where flooding develops,
- how flooding changes over time,
- which buildings/roads are affected,
- where drainage bottlenecks occur,
- and what decisions could reduce risk.

---

## 14. Intended User Experience

The final application should approximately follow this flow:

```text
Open ChennaiFlood-Twin
        ↓
View 3D Ward 176
        ↓
Select rainfall scenario
        ↓
Run simulation
        ↓
Show simulation progress
        ↓
Display flood evolution
        ↓
Move through timeline
        ↓
Inspect depth / affected assets
        ↓
View KPIs
        ↓
View high-risk areas
        ↓
View drainage bottlenecks
        ↓
View recommendations
        ↓
Compare scenarios
```

The 3D Digital Twin should be the main visual focus.

The dashboard should support the scene rather than replace it.

---

## 15. Decision-Support Layer

The eventual application should derive useful indicators such as:

### Flood KPIs
- rainfall total,
- peak rainfall,
- maximum simulated flood depth,
- affected area,
- number/percentage of affected buildings,
- affected road area/length where defensible,
- duration of flooding where defensible.

### Drainage indicators
- high-flow links,
- hydraulically stressed conduits,
- flooding nodes,
- disconnected components,
- possible bottlenecks.

### Recommendations

Recommendations must be based on available model evidence.

Examples may include:
- prioritize drainage capacity improvements,
- inspect specific drainage segments,
- investigate local junction constraints,
- prioritize flood-prone urban assets,
- evaluate alternative rainfall scenarios.

Do not generate recommendations that imply field verification has already occurred when it has not.

---

## 16. AWS Direction

AWS is part of the intended cloud-native architecture.

A conceptual target is:

```text
User
 ↓
CloudFront
 ↓
Frontend / S3
 ↓
API Gateway
 ↓
Backend
 ↓
Simulation Engine
 ↓
SWMM
 ↓
Post-processing
 ↓
S3 / database
 ↓
API
 ↓
CesiumJS / dashboard
```

The exact AWS services may evolve.

### Rule

Do not add AWS components just to make the architecture diagram look sophisticated.

Every service must have a clear purpose.

For example:
- S3 → static assets, spatial datasets, simulation artifacts
- API Gateway → API entry point
- compute → simulation/backend execution
- CloudFront → frontend delivery
- database → metadata/KPI/scenario state if actually needed

---

## 17. Academic / Scientific Honesty Rules

This project is an academic prototype.

Always distinguish between:

### Source observations
Data directly obtained from:
- GCC GIS,
- NASA GPM,
- Copernicus DEM,
- other authoritative sources.

### Model assumptions
Examples:
- Manning coefficients,
- infiltration parameters,
- subcatchment imperviousness,
- DEM-derived attributes,
- simplified conduit representation.

### Derived results
Examples:
- SWMM runoff,
- simulated node flooding,
- derived flood depth,
- risk scores,
- bottleneck rankings.

### Visualization
The 3D Digital Twin is a visualization and decision-support representation of the above.

Never present:
- assumptions as measurements,
- model output as observed flood data,
- provisional outlets as confirmed outfalls,
- simplified geometry as surveyed infrastructure,
- or derived flood maps as official government flood forecasts.

---

## 18. Existing Documentation

The `docs/` directory contains or will contain detailed project documents.

The documentation set is intended to include:

```text
00_PROJECT_CONTEXT.md
01_PRODUCT_REQUIREMENTS.md
02_ARCHITECTURE.md
03_DATA_AND_GIS.md
04_SWMM_MODEL.md
05_BACKEND_DESIGN.md
06_API_CONTRACT.md
07_FRONTEND_DESIGN.md
08_DIGITAL_TWIN_VISUALIZATION.md
09_DEVELOPMENT_RULES.md
10_CHANGELOG.md
```

This file is the **highest-level project context document**.

Subsystem-specific details belong in the relevant documents rather than being duplicated everywhere.

---

## 19. Rules for Claude / Future Developers

When working on ChennaiFlood-Twin:

1. **Read this document first.**
2. Read the relevant subsystem document before modifying that subsystem.
3. Inspect the existing implementation before creating new code.
4. Reuse existing project data and artifacts.
5. Never overwrite raw data.
6. Never fabricate missing GIS or hydraulic connections.
7. Never silently change model assumptions.
8. Never hardcode simulation results into the frontend.
9. Keep frontend and backend responsibilities separated.
10. Keep API contracts explicit.
11. Preserve source-data provenance.
12. Document significant architectural/model changes.
13. Prefer targeted fixes over broad rewrites.
14. Validate generated data before integrating it.
15. Preserve the current hydraulic baseline unless a change is justified and documented.
16. Treat model limitations as part of the project, not something to hide.
17. Do not claim scientific accuracy beyond what the available data and modelling method support.
18. Optimize for a stable, demonstrable academic MVP before adding advanced features.

---

## 20. Current Baseline Principle

At the beginning of the Digital Twin implementation phase:

> **The hydraulic model is considered sufficiently stable for integration.**

The goal is now to **build around it**, not endlessly modify it.

The current development priority is:

```text
1. Spatial data preparation
2. CesiumJS 3D Digital Twin
3. Backend simulation execution
4. SWMM result parsing
5. Flood-depth/extent processing
6. API integration
7. Dashboard + decision support
8. Scenario comparison
9. AWS deployment
10. Final testing + documentation
```

The Digital Twin should therefore be treated as the next major engineering phase.

---

## 21. One-Sentence Project Description

Use the following description when a concise explanation is needed:

> **ChennaiFlood-Twin is a software-only Smart City prototype that combines rainfall, terrain, urban infrastructure, and EPA SWMM hydraulic simulation to create an interactive 3D Digital Twin of Ward 176, Velachery, for urban flood visualization, risk assessment, and decision support.**
