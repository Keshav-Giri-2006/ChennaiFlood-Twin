# ChennaiFlood-Twin — SWMM Model Specification

## 1. Purpose

This document is the authoritative context for the **EPA SWMM hydraulic/simulation component** of ChennaiFlood-Twin.

It tells developers:

- which SWMM version is being used,
- what the current model contains,
- how the model was constructed,
- which assumptions are intentional,
- which anomalies were investigated,
- which changes were accepted/rejected,
- how simulations should be executed,
- how results should be interpreted,
- and which modelling claims must not be made.

Read this together with:

```text
00_PROJECT_CONTEXT.md
01_PRODUCT_REQUIREMENTS.md
02_ARCHITECTURE.md
03_DATA_AND_GIS.md
```

This document is specifically about **SWMM modelling and simulation**. Frontend/API implementation details belong in the other documents.

---

# 2. Simulation Engine

The project uses:

> **EPA SWMM 5.2.4**

SWMM is used for:

- rainfall-runoff modelling,
- urban drainage representation,
- conduit hydraulic routing,
- node flooding analysis,
- and simulation of the reconstructed Ward 176 storm-water network.

The current routing method is:

> **Dynamic Wave**

The model is intended as an academic urban drainage/hydraulic prototype.

---

# 3. Scientific Scope

The model should be described as:

> **Hydrological/hydraulic urban drainage simulation.**

It is not:

- a full 3D CFD model,
- a Navier-Stokes flood solver,
- a complete 2D surface-water model,
- a surveyed municipal hydraulic model,
- or an operational flood forecast.

Dynamic Wave SWMM provides a one-dimensional hydraulic representation of the drainage network.

The Digital Twin's 3D flood visualization is a **separate spatial visualization/post-processing layer**.

The correct overall chain is:

```text
Rainfall
   ↓
SWMM rainfall-runoff
   ↓
1D drainage/hydraulic response
   ↓
Spatial flood-depth/extent post-processing
   ↓
3D Digital Twin visualization
```

Never claim that SWMM directly produces the final 3D flood surface displayed in CesiumJS.

---

# 4. Current Working Model

The current working SWMM model is:

```text
simulation/
└── ward176_hydraulic_reconstructed_candidate.inp
```

This is the **baseline model for Digital Twin integration**.

Do not casually replace it with an older baseline.

Earlier models exist for historical/debugging purposes, but the reconstructed candidate is the current working model.

---

# 5. Current Model Size

The current model contains approximately:

```text
35 subcatchments
228 nodes
182 links
1 rainfall gage
```

The model contains:

```text
35 rainfall-linked subcatchments
182 conduits/links
```

The current model was produced after conservative drainage reconstruction and targeted hydraulic elevation reconstruction.

---

# 6. Model Components

The principal SWMM components are:

```text
Rainfall
   ↓
Rain Gage
   ↓
Subcatchments
   ↓
Junctions
   ↓
Conduits
   ↓
Outfalls / boundary terminals
```

The model also includes:

- infiltration parameters,
- conduit cross-sections,
- roughness,
- node depths,
- rainfall time series,
- routing settings,
- reporting settings.

---

# 7. Rainfall Scenario

## 7.1 Current Scenario

The primary scenario is:

> **Michaung 2023**

Event period:

```text
December 2–5, 2023
```

Source:

> NASA GPM IMERG Final Run

Variable:

```text
GPM_3IMERGHH v07
```

Temporal resolution:

```text
30 minutes
```

---

# 8. Rainfall Characteristics

The processed event contains approximately:

```text
Total rainfall:          282.835 mm
Peak interval intensity: 23.35 mm/hr
```

Approximate daily totals:

```text
Dec 2:   13.51 mm
Dec 3:  114.78 mm
Dec 4:  152.36 mm
Dec 5:    2.185 mm
```

The model rainfall series contains:

```text
192 temporal records
```

after metadata handling.

---

# 9. Rainfall Spatial Limitation

The rainfall extraction effectively provides a coarse rainfall field for the study area.

It is not a dense network of local rain gauges.

Therefore:

> Do not describe the input as high-resolution street-level rainfall measurement.

It is a historical scenario input.

---

# 10. Rain Gage

The current model uses:

```text
GAGE_MICH
```

Scenario/event:

```text
Michaung
```

Rainfall type:

```text
Intensity
```

Recording interval:

```text
30 minutes
```

The rain gage is linked to all 35 model subcatchments according to the current SWMM model.

---

# 11. Subcatchments

The model contains:

```text
35 subcatchments
```

They were generated as a first-pass spatial representation for the Ward 176 drainage model.

They are not official municipal hydrological catchment boundaries.

Each subcatchment has associated parameters including:

- area,
- imperviousness,
- width,
- slope-related information,
- roughness,
- depression storage,
- infiltration parameters.

---

# 12. Imperviousness

Imperviousness was estimated using the prepared:

- building footprints,
- road/carriageway geometry.

The model therefore uses an urban land-cover approximation.

Do not describe the impervious percentages as directly measured land-cover survey values.

---

# 13. Manning Roughness

Current model assumptions include approximately:

```text
Impervious: 0.013
Pervious:   0.24
```

These are modelling assumptions.

They are not field-calibrated values unless later calibration evidence is obtained.

Do not silently change them because another value appears more realistic.

Any change must be documented and compared against the baseline.

---

# 14. Depression Storage

Current assumptions include approximately:

```text
Impervious: 1.5 mm
Pervious:   5.0 mm
```

Again, these are model assumptions rather than surveyed values.

---

# 15. Infiltration

The current model uses a:

> **Green-Ampt infiltration representation**

The model uses parameters approximately equivalent to:

```text
Suction head:          110 mm
Hydraulic conductivity: 10 mm/hr
Initial moisture deficit: 0.25
```

These values are part of the current modelling assumption set.

Do not change them without documenting the reason.

---

# 16. Conduits

The drainage network is represented using SWMM conduits.

Where GCC drain dimensions are available, rectangular closed conduit cross-sections are used.

The conduit representation uses source/processed information such as:

- drain width,
- drain depth,
- length,
- invert elevations,
- reconstructed endpoints.

Current roughness is based on the model's Manning assumption.

---

# 17. Dynamic Wave Routing

The model uses:

> **Dynamic Wave routing**

This is appropriate for representing complex urban drainage behaviour within the one-dimensional network model.

The model can therefore represent hydraulic phenomena such as:

- backwater effects,
- flow reversal,
- surcharge/pressurization behaviour,
- and dynamically varying network flow.

Do not interpret this as a 2D overland-flow model.

---

# 18. Routing Settings

The current model uses approximately:

```text
Routing method: Dynamic Wave
Flow units:     CMS
Report step:    30 minutes
Wet step:       5 minutes
Routing step:   30 seconds
```

The actual `.inp` file is the authoritative source for exact SWMM options.

Do not rely on this document instead of inspecting the model when exact parameter values matter.

---

# 19. Subcatchment / Rainfall Input

All 35 model subcatchments are associated with the current rainfall gage.

The model therefore provides a complete rainfall-to-subcatchment input chain for the current historical scenario.

---

# 20. Network Reconstruction Background

The original GCC storm-water dataset contained:

```text
135 source drain features
```

These were reconstructed into a hydraulic network.

The reconstruction produced approximately:

```text
229 reconstructed nodes
190 reconstructed conduit pieces
```

before final model selection.

After conservative connection resolution and duplicate cleanup, the current SWMM model contains:

```text
228 nodes
182 links
```

---

# 21. Conservative Topology Rule

The reconstruction deliberately avoided inventing network connections.

A nearby endpoint is not automatically considered connected.

Only connections supported by:

- geometry,
- source information,
- spatial relationship,
- or a defensible hydraulic interpretation

should be accepted.

This principle must continue during future development.

---

# 22. Accepted High-Confidence Node Merge

One high-confidence connection was accepted:

```text
ObjectID 5807 END
        →
existing junction at
ObjectID 5899 START / 5901 END
```

The endpoint separation was approximately:

```text
2.14 m
```

This was considered defensible based on the available network geometry.

Other candidate gap connections were conservatively rejected.

---

# 23. C182 Duplicate Removal

GCC ObjectID 5917 was represented as C182.

C182 was identified as duplicate geometry corresponding to another source feature represented as C186.

C186 had already been removed during cleanup, so:

> **C182 was removed from the final candidate model.**

This is a deliberate model-cleaning decision.

Do not reintroduce C182 unless new source evidence justifies it.

---

# 24. ObjectID 5793

GCC ObjectID:

```text
5793
```

contains a clearly suspicious invert value:

```text
invert endpoint ≈ 20869
```

This is inconsistent with the surrounding Ward 176 elevation range.

The anomaly was excluded from the hydraulic model.

The source geometry remains part of the source-data audit.

Do not reintroduce the anomalous invert into the model.

---

# 25. Hydraulic Reconstruction

Several junction elevations contained conflicts because different incident source conduits provided different invert values.

The targeted reconstruction changed selected junction representations by:

1. selecting the minimum relevant incident pipe-end invert,
2. preserving the original ground/top-depth relationship,
3. using conduit offsets to preserve source/reconstructed pipe-end elevations.

The goal was not to invent a new surveyed elevation.

The goal was to represent known source pipe-end elevations more faithfully within SWMM.

---

# 26. Reconstructed Junctions

The targeted reconstruction involved:

```text
J122
J124
J180
J181
J203
J204
J061
J057
```

The reconstruction was intentionally limited to these investigated locations.

Do not apply the same transformation globally without evidence.

---

# 27. C162

C162 represents GCC ObjectID 5902.

Approximate length:

```text
3.0 m
```

Source/reconstructed invert:

```text
2.192 → 2.072 m
```

The old node-average elevations made the segment appear hydraulically adverse.

The reconstruction represents the pipe-end elevations using offsets.

Observed model slope after reconstruction is approximately:

```text
+3.97%
```

C162 remains in the model.

---

# 28. C175

C175 represents GCC ObjectID 5913.

Approximate length:

```text
6.1 m
```

Source invert:

```text
3.568 → 2.466 m
```

This produces a steep approximate slope of:

```text
18.32%
```

The source invert attributes are suspicious because they exactly match those of C174 despite different geometry.

However, no authoritative evidence was found to justify changing them.

Therefore:

> **C175 is retained unchanged in the current model.**

Treat it as a documented source-data ambiguity.

---

# 29. C180

C180 is a legitimate split of GCC ObjectID 5916.

Approximate length:

```text
6.5 m
```

Source/reconstructed invert:

```text
3.029 → 3.001 m
```

Approximate reconstructed slope:

```text
+0.43%
```

C180 is retained.

It must not be deleted simply because it is hydraulically sensitive.

The main uncertainty is around J203/J204 elevations/topology.

---

# 30. C166

C166 represents GCC ObjectID 5906.

Approximate length:

```text
10.1 m
```

Approximate source/reconstructed slope:

```text
+1.81%
```

It belongs to an incomplete/disconnected network component.

C166 is retained.

Do not invent a long connection to another component merely to remove its numerical instability.

---

# 31. C190

C190 represents GCC ObjectID 5923.

Approximate length:

```text
25.8 m
```

Source/reconstructed invert:

```text
3.845 → 3.419 m
```

Approximate slope:

```text
+1.65%
```

The earlier representation generated a SWMM Warning 04 because the endpoint node elevations were too similar.

The reconstruction represents the source pipe-end elevations through conduit offsets.

The reconstructed run no longer produced the previous Warning 04.

C190 remains in the model.

---

# 32. C086

C086 represents GCC ObjectID 5849.

Approximate length:

```text
5.2 m
```

It is a genuine source segment and is retained.

It appeared among timestep-critical links in the latest run but there is no basis for deleting it.

---

# 33. Provisional Outlets

The network analysis identified provisional downstream boundary terminals including:

```text
node125
node98
node140
node94
node88
node97
node213
```

These are not confirmed physical outfalls.

The SWMM model may represent only a subset of these as outfall/boundary conditions depending on the current `.inp`.

Do not label them as verified municipal outfalls.

---

# 34. Network Fragmentation

The reconstructed network remains fragmented.

This is an important limitation.

There are disconnected network components because the available GCC data does not provide sufficient evidence for all physical connections and outfalls.

Do not "fix" fragmentation by creating arbitrary connections.

---

# 35. Latest Baseline Run

The latest reconstructed candidate run produced approximately:

```text
Runoff continuity error:        -0.018%
Flow routing continuity error:  0.068%
```

Routing timestep statistics:

```text
Minimum: 0.50 sec
Average: 2.39 sec
Maximum: 30 sec
```

Average iterations:

```text
~2.20
```

Non-converging steps:

```text
~0.37%
```

These values indicate a numerically usable simulation for the current prototype.

They do not constitute hydraulic calibration or validation.

---

# 36. Latest Model Warning

The latest reconstructed run produced Warning 02 at selected reconstructed nodes because the maximum depth was exceeded and SWMM increased the allowable maximum depth.

Affected reconstructed locations included:

```text
J057
J061
J122
J180
J181
J203
J204
```

This is a warning to investigate, not automatic evidence that the model is invalid.

The warning locations correspond to deliberately investigated hydraulic hotspots.

---

# 37. Numerical Instability

The latest run reported highest instability around:

```text
C166
C136
C157
C022
C161
```

C166 was the highest of these in the reported run.

Do not automatically delete a link because it appears in an instability ranking.

Instability may arise from:
- incomplete network connectivity,
- boundary conditions,
- steep slopes,
- short links,
- abrupt elevation changes,
- or other hydraulic conditions.

Investigate before changing geometry.

---

# 38. Critical Timestep Links

The latest run identified links such as:

```text
C162
C180
C175
C086
```

among the most timestep-critical.

Approximate reported criticality:

```text
C162  ~35.70%
C180  ~33.03%
C175  ~17.85%
C086  ~12.64%
```

These are diagnostic indicators.

They are not proof that the corresponding source geometry is incorrect.

---

# 39. Solver Tuning Rule

Do not globally change SWMM solver settings merely to eliminate small amounts of non-convergence.

The current:

```text
~0.37% non-converging steps
```

is not by itself a reason to destabilize the model through aggressive parameter changes.

Prefer targeted investigation.

If solver settings are changed:

1. document the reason,
2. retain the old baseline,
3. compare continuity,
4. compare timestep behaviour,
5. compare major outputs,
6. document the result.

---

# 40. Flooding Output Interpretation

The latest run produced approximately:

```text
Wet-weather inflow:   271.424 million L
External outflow:      67.405 million L
Flooding loss:         197.876 million L
Final stored volume:     5.958 million L
```

These are SWMM model outputs.

### Critical rule

Do **not** describe:

```text
197.876 million L
```

as the observed flood volume in Ward 176.

It is:

> **model-generated flooding under the current incomplete network representation.**

The value is useful for model diagnostics and scenario comparison, but it is not independently validated real-world flood volume.

---

# 41. Calibration / Validation Status

The current model is:

> **not fully calibrated or field-validated.**

There is currently no authoritative observed flood-depth time series being used as a calibration target.

Therefore:

- do not claim calibrated hydraulic accuracy,
- do not claim exact prediction accuracy,
- do not report validation statistics that have not actually been calculated.

Future validation could use:
- observed flood depths,
- water-level observations,
- verified flood extents,
- municipal drainage records,
- or other authoritative evidence.

---

# 42. Simulation Reproducibility

A simulation should be reproducible from:

```text
Scenario
+
SWMM model version
+
Rainfall input
+
Model configuration
+
Processing version
```

Every simulation should ideally record:

```text
simulation_id
scenario_id
model_version
processing_version
start_time
end_time
status
```

---

# 43. Simulation Working Directory

When simulations are executed by the backend, use an isolated directory.

Conceptually:

```text
simulation_runs/
└── <simulation_id>/
    ├── input.inp
    ├── report.rpt
    ├── output.out
    ├── metadata.json
    └── processed/
```

Do not overwrite the baseline model during a run.

Do not let two simulations share the same temporary output files.

---

# 44. SWMM Execution

The backend should execute SWMM as a controlled process.

Conceptually:

```text
Scenario request
      ↓
Validate
      ↓
Create simulation directory
      ↓
Copy/use model
      ↓
Prepare scenario input
      ↓
Execute SWMM
      ↓
Check exit status
      ↓
Parse outputs
      ↓
Post-process
```

The exact command-line invocation should be discovered/verified against the installed SWMM executable rather than hardcoded from assumptions.

---

# 45. Input File Handling

The `.inp` file is a structured SWMM model/configuration file.

It is not application source code.

The backend may generate a scenario-specific copy or modify a controlled copy when necessary.

Never modify the master baseline in-place during normal simulation execution.

Preferred approach:

```text
Master model
     ↓
Scenario-specific copy
     ↓
Simulation
```

---

# 46. Scenario Overrides

If the product supports modified rainfall scenarios, scenario parameters should be applied to a copy of the baseline model or through a controlled input-generation process.

Do not permanently alter:

```text
ward176_hydraulic_reconstructed_candidate.inp
```

for a temporary scenario.

---

# 47. SWMM Output Processing

SWMM output should be converted into application-level results.

The processing pipeline is:

```text
SWMM output
      ↓
Parse
      ↓
Validate
      ↓
Normalize
      ↓
Extract time series
      ↓
Generate KPIs
      ↓
Generate spatial associations
      ↓
Generate flood products
```

Raw SWMM output should remain available for debugging/reproducibility.

---

# 48. Important Result Types

The backend may need to expose:

### Node results

- depth,
- flooding,
- flow-related information,
- timestamps.

### Link results

- flow,
- velocity,
- depth,
- capacity/utilization where available,
- hydraulic state.

### Subcatchment results

- rainfall,
- runoff,
- infiltration,
- related hydrological values.

### System results

- rainfall total,
- runoff,
- inflow,
- outflow,
- flooding,
- storage,
- continuity.

---

# 49. Flood Spatial Post-Processing

SWMM's one-dimensional network results need a separate spatial interpretation layer for the 3D Digital Twin.

The conceptual workflow is:

```text
Node/link hydraulic results
        +
Terrain
        +
Urban spatial data
        ↓
Flood-depth / flood-extent processing
        ↓
Web-ready spatial product
```

The exact method must be explicitly documented when implemented.

Do not imply that the spatial flood surface is directly observed.

---

# 50. Risk Calculation

Risk calculations should use processed model outputs plus exposure data.

Potential inputs:

```text
Flood depth
Flood duration
Building exposure
Road exposure
Drainage stress
```

Risk scoring must be documented and reproducible.

Do not embed unexplained formulas in the frontend.

---

# 51. Bottleneck Calculation

Potential drainage bottlenecks should be identified using model evidence such as:

- high flow,
- high relative capacity use,
- surcharge,
- repeated hydraulic stress,
- flooding relationships.

A bottleneck is:

> **a model-derived candidate requiring further investigation.**

It is not automatically a confirmed engineering failure.

---

# 52. Model Modification Policy

Any modification to the baseline SWMM model must answer:

1. What is being changed?
2. Why is it being changed?
3. What evidence supports the change?
4. Is the change source-data-driven or an assumption?
5. What was the previous result?
6. What is the new result?
7. Does the change improve or degrade continuity?
8. Does the change affect scientific interpretation?

Changes must be documented in the project changelog.

---

# 53. What Must Not Be Modified Casually

Do not casually change:

```text
Network topology
Junction elevations
Conduit dimensions
Conduit slopes
Outfall definitions
Rainfall series
Manning coefficients
Infiltration parameters
Routing method
Solver settings
Subcatchment boundaries
```

Any such change can alter the scientific meaning of the model.

---

# 54. Baseline Preservation

The current baseline should be treated as:

> **frozen working hydraulic baseline**

unless a new evidence-based modelling decision is explicitly approved.

If experimentation is required:

```text
baseline
   ↓
experimental copy
```

Never destroy the baseline.

---

# 55. SWMM-to-Digital-Twin Contract

The SWMM layer should provide the backend with structured information rather than frontend-specific objects.

Conceptually:

```text
SWMM
 ↓
Simulation result model
 ↓
Processing services
 ↓
API response
 ↓
Frontend
```

The frontend should not parse `.rpt` or `.out` files directly.

---

# 56. SWMM Data Quality Principle

A successful SWMM run does not automatically mean the model is physically correct.

Always distinguish:

```text
Numerical success
      ≠
Physical validation
```

Good continuity and convergence indicate numerical usability.

They do not prove that:
- drainage topology is complete,
- outfalls are correct,
- elevations are surveyed,
- rainfall is spatially complete,
- or flood depths are observationally accurate.

---

# 57. Future Calibration

Calibration is a possible future enhancement.

Potential future calibration targets include:

- observed flood depths,
- verified flood extents,
- drainage flow measurements,
- water levels,
- verified flood duration.

If calibration is introduced, record:

```text
parameter changed
observed data
objective function
calibration period
validation period
before/after performance
```

Do not claim calibration without actual calibration data.

---

# 58. SWMM Model Versioning

Recommended model version convention:

```text
ward176-hydraulic-reconstructed-v1
```

Future changes should increment the model version.

Examples:

```text
v1
v2
v3
```

or another documented semantic scheme.

A model version must correspond to a reproducible `.inp` configuration.

---

# 59. Current Model Acceptance Criteria

The current hydraulic model is acceptable as the Digital Twin integration baseline when:

1. SWMM executes successfully.
2. No fatal input errors occur.
3. Runoff continuity remains very small.
4. Flow-routing continuity remains very small.
5. Timestep behaviour remains stable enough for the prototype.
6. Known anomalies are documented.
7. C182 remains removed.
8. Investigated links remain intentionally retained.
9. No unsupported connections are fabricated.
10. Limitations are communicated honestly.

The latest reconstructed candidate satisfies the intended baseline role.

---

# 60. Developer Checklist Before Changing SWMM

Before changing the model:

```text
[ ] Read this document
[ ] Inspect current .inp
[ ] Identify exact section being changed
[ ] Check source data
[ ] Check previous modelling decision
[ ] State why change is necessary
[ ] Create experimental copy
[ ] Run SWMM
[ ] Check warnings
[ ] Check continuity
[ ] Check timestep behaviour
[ ] Compare major outputs
[ ] Document the change
```

---

# 61. Developer Checklist Before Using SWMM Results

Before exposing a result to the frontend:

```text
[ ] Identify source section
[ ] Identify units
[ ] Validate parsing
[ ] Check timestamps
[ ] Check missing values
[ ] Associate with simulation ID
[ ] Distinguish model output from observation
[ ] Apply spatial processing if needed
[ ] Document assumptions
```

---

# 62. Final SWMM Architecture

The intended simulation chain is:

```text
                    RAINFALL
                       │
                       ▼
                 SWMM Rain Gage
                       │
                       ▼
                 35 Subcatchments
                       │
                       ▼
                228-node network
                       │
                       ▼
                  182 links
                       │
                       ▼
               Dynamic Wave routing
                       │
                       ▼
                 SWMM results
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
     Hydraulic data           System metrics
          │                         │
          └────────────┬────────────┘
                       ▼
              Spatial post-processing
                       │
              ┌────────┴─────────┐
              ▼                  ▼
        Flood products      Risk / KPIs
              │                  │
              └────────┬─────────┘
                       ▼
                  REST API
                       │
                       ▼
               CesiumJS + UI
```

---

# 63. Final Non-Negotiable Rules

1. Use EPA SWMM 5.2.4 unless explicitly changed.
2. Preserve the reconstructed candidate as the current baseline.
3. Do not reintroduce C182.
4. Do not reintroduce ObjectID 5793's anomalous invert.
5. Do not fabricate drainage connections.
6. Do not fabricate physical outfalls.
7. Do not silently alter source invert values.
8. Do not delete hydraulically sensitive links without investigation.
9. Keep C162, C166, C175, C180, C086, and C190 unless new evidence justifies change.
10. Treat C175's source elevation as an unresolved ambiguity.
11. Treat C166 as part of an incomplete component.
12. Treat C180 as legitimate split geometry.
13. Treat C190 as a legitimate source segment.
14. Do not interpret model flooding loss as observed flood volume.
15. Do not claim calibration or field validation that has not occurred.
16. Do not describe SWMM as a complete 3D flood solver.
17. Keep scenario runs isolated from the master model.
18. Preserve raw SWMM outputs for reproducibility.
19. Version significant model changes.
20. Prefer targeted, evidence-based changes over global model manipulation.

---

# 64. Final Principle

The purpose of the SWMM layer is not to produce an artificially perfect-looking result.

Its purpose is to provide a:

> **reproducible, transparent, numerically usable urban drainage/hydraulic simulation that can feed the ChennaiFlood-Twin Digital Twin.**

The model's limitations are part of the project's technical context and should remain visible to developers and evaluators.
