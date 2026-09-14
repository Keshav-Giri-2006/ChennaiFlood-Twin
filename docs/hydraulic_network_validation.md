# ChennaiFlood-Twin — Hydraulic Network Validation Report

**Study Area:** Ward 176, Velachery, Chennai  
**Project:** ChennaiFlood-Twin — AI-Powered Urban Flood Digital Twin and Decision Support System  
**Purpose:** Validate the processed GCC storm-water-drain network and DEM-derived elevations before constructing the first EPA SWMM model.

---

## 1. Validation Status

The initial GIS/network validation has been extended with a segment-level invert validation using the candidate conduit topology and DEM-derived junction elevations.

| Validation category | Segments |
|---|---:|
| VALID | 109 |
| BOUNDARY_OR_MISSING_DEM | 14 |
| INVERT_ABOVE_DEM | 6 |
| LARGE_JUNCTION_DISCONTINUITY | 4 |
| SUSPICIOUS_INVERT | 1 |
| MINOR_SLOPE_ANOMALY | 1 |

**Important:** These are screening classifications. They do not certify surveyed hydraulic elevations or field-verified drainage connectivity.

## 2. Inputs Used

The validation combines:

- `data_processed/network/ward176_conduits_candidate.csv`
- `data_processed/network/ward176_junctions_candidate.csv`
- `data_processed/network/ward176_topology_edges.csv`
- `data_processed/network/ward176_junction_elevations.csv`
- `data_processed/gis/ward176_dem.tif`
- the processed GCC Ward 176 storm-water-drain dataset

## 3. Invert-Slope Check

For each conduit, the screening slope was calculated as:

```text
invert_slope = (invert_start - invert_end) / length
```

- **133/135** segments have positive calculated invert slope.
- **2/135** segments have negative calculated invert slope.
- The negative-slope segments are not automatically treated as errors.
- One of them is classified as `MINOR_SLOPE_ANOMALY`; the other is flagged because it also meets another validation condition.

## 4. Provisional Flow Direction

| Provisional direction | Segments |
|---|---:|
| START_TO_END | 133 |
| END_TO_START | 1 |
| UNCERTAIN | 1 |

This direction is **provisional only** and is derived from the GCC invert gradient. It does not prove that the original GIS line direction represents actual hydraulic flow.

Before the final SWMM network is accepted, direction should also be checked against topology and outlet/boundary logic.

## 5. Junction Continuity Check

Where candidate topology connects a segment ending at a node to a segment beginning at the same node, the validation compares:

```text
upstream candidate invert_end
                ↕
downstream candidate invert_start
```

Large differences are flagged as `LARGE_JUNCTION_DISCONTINUITY` rather than being silently corrected.

The validation identified **4 segments associated with a large junction discontinuity** under the screening rule used for this audit.

These values require contextual inspection before final SWMM construction.

## 6. DEM vs Invert Check

For nodes with valid DEM samples, the screening check calculates:

```text
surface_minus_invert = DEM surface elevation - drain invert
```

A negative value indicates that the reported drain invert is above the sampled DEM surface and is therefore flagged as `INVERT_ABOVE_DEM`.

The audit identified **6 segments** meeting this screening condition.

This does not automatically prove the GCC value is wrong because the Copernicus DEM is a ~30 m DSM-derived surface product and may not represent exact local bare-earth/street elevation. The result is therefore treated as a review flag rather than an automatic correction.

## 7. Boundary / DEM Coverage

The junction dataset contains **223 candidate nodes**:

- 210 inside Ward 176
- 13 outside Ward 176

The outside nodes are retained because the associated drain segments can cross or touch the study boundary. Such nodes may represent connections to drainage infrastructure outside the pilot area.

Segments affected by missing/outside DEM context are classified as `BOUNDARY_OR_MISSING_DEM` where applicable.

## 8. Critical Anomaly — ObjectID 5793

**ObjectID 5793 remains the principal invalid/suspicious record.**

| Field | Value |
|---|---:|
| Start node | 155 |
| End node | 158 |
| Length | 95.87 m |
| Width | 0.90 m |
| Depth | 0.90 m |
| `invert_start` | 3.234 m |
| `invert_end` | **20,869 m** |
| Calculated slope | **−217.646 m/m** |

The value `20869` is an extreme outlier relative to the surrounding network values and produces an impossible screening result.

### Current decision

**Do not use `invert_end = 20869` in the SWMM model. Do not replace it with a guessed value yet.**

The value remains explicitly flagged as `SUSPICIOUS_INVERT` in the validation CSV.

The next investigation should examine the neighboring segments and available GCC attribute semantics before deciding whether a defensible replacement can be established.

## 9. What the Validation Does NOT Establish

This audit does not establish:

1. A surveyed vertical datum for the GCC invert attributes.
2. Confirmed hydraulic flow direction for every conduit.
3. Confirmed hydraulic connectivity at every geometric endpoint/intersection.
4. Confirmed outlet structures outside Ward 176.
5. Calibrated Manning's roughness coefficients.
6. Calibrated rainfall-runoff parameters.
7. Street-level flood depth accuracy from the ~30 m DEM.

These limitations must remain explicit in the academic project documentation.

## 10. SWMM Readiness

The network is **close to first-pass SWMM readiness**, but the following items should be resolved or explicitly parameterized first:

### Required before baseline model

- [ ] Investigate ObjectID 5793.
- [ ] Review the four large junction discontinuities.
- [ ] Review the six invert-above-DEM flags.
- [ ] Establish provisional outlet/boundary nodes.
- [ ] Confirm or document the interpretation/datum of the GCC invert fields.
- [ ] Choose and document first-pass Manning's roughness assumptions.
- [ ] Generate simplified SWMM subcatchments.

### Then

Construct the first-pass SWMM network using:

- candidate junction topology
- reliable GCC drain dimensions
- accepted/reviewed invert values
- DEM-derived surface elevations where valid
- documented hydraulic assumptions
- the Michaung 2023 IMERG rainfall scenario

## 11. Recommended Next Step

The immediate next step is **not frontend development** and not final SWMM construction.

> **Resolve the flagged invert records and identify provisional outlet/boundary nodes.**

Once those decisions are documented, the project can proceed to generating the first `ward176_baseline.inp` SWMM model.

## 12. File Outputs

Current network-validation artifacts:

```text
data_processed/
├── gis/
│   ├── ward176_boundary.geojson
│   ├── ward176_buildings.geojson
│   ├── ward176_carriageways.geojson
│   └── ward176_dem.tif
│
└── network/
    ├── ward176_drain_network_audit.csv
    ├── ward176_candidate_connections.csv
    ├── ward176_junctions_candidate.csv
    ├── ward176_conduits_candidate.csv
    ├── ward176_topology_edges.csv
    ├── ward176_junction_elevations.csv
    └── ward176_invert_validation.csv
```

## 13. Conclusion

The drainage dataset has a strong enough internal structure to support a first-pass academic hydraulic prototype. The geometry, dimensions, candidate topology, DEM sampling, and rainfall inputs are available.

The remaining work is primarily **hydraulic interpretation and validation**, not basic GIS acquisition.

The project should proceed conservatively: retain the real GCC data, flag anomalies, document assumptions, and avoid silently inventing hydraulic values.

---

**Status:** Invert validation complete; flagged records require review before baseline SWMM construction.