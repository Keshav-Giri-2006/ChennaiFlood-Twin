# Location Flood Check — location-check-v1

Location-specific historical flood analysis using the model-derived response around a user-selected point.

The user places a pin in Ward 176 and runs the existing historical rainfall simulation (or reuses the displayed completed result). The backend then evaluates the flood response of that **one** simulation around the pin. Nothing new is simulated: there is no per-pin SWMM model and no second pipeline.

```text
Pin (WGS 84)
  → existing scenario (Michaung 2023, optional rainfall multiplier)
  → existing Ward 176 SWMM model and simulation
  → existing flood-processing-v1 node states and influence zones
  → spatial query around the pin (EPSG:32644)
  → location-specific, model-derived summary
```

**What it is not:** an observation, a property assessment, a flood certification, or a prediction for any property. It never reports "safe" or "flood-proof", and it does not say that a plot will flood.

## 1. Inputs

| Input | Source |
|---|---|
| Selected location | User click, WGS 84 latitude/longitude (EPSG:4326) |
| Node states per reporting timestamp | SWMM binary output of the simulation, using the flood-processing-v1 state definitions (`compute_node_states`, the same function that builds the flood products) |
| Node locations | Reconstructed node coordinates (network mapping, EPSG:32644) |
| Influence zones | flood-processing-v1 nearest-node (Voronoi) cells clipped to Ward 176 (`influence_zones`) |
| Ward boundary | `data_processed/gis/ward176_boundary.geojson` (EPSG:32644) |
| Potential bottlenecks | bottleneck-analysis-v1 records of the same simulation |

The simulation must be `COMPLETED` and its flood products valid; otherwise the request fails (`409 SIMULATION_NOT_COMPLETED`, or the existing processing errors).

## 2. Spatial method

1. The location is projected once from EPSG:4326 to **EPSG:32644** (UTM 44N, metres). All distances, buffers, intersections and areas are computed there. Nothing is computed in degrees.
2. **Study area:** points not covered by the Ward 176 boundary are rejected (`422 LOCATION_OUTSIDE_STUDY_AREA`). The model has no data outside the ward. (The browser runs a quick lon/lat pre-check on the loaded boundary for immediate feedback; the backend decides.)
3. **Nearest modelled drainage node:** the model node at the smallest planar distance. By the definition of the nearest-node influence zones, this is also the node whose zone contains the location (reported as `zoneContainsLocation`; the tests check it against the published zone product).
4. **Surrounding area:** a circle of **250 m** radius (default; the API accepts 50–1000 m) around the location, **clipped to Ward 176**. Only the part inside the ward is analysed, and its share is reported.
5. **Association:** a node is associated with the surrounding area when its influence zone overlaps it (overlap ≥ 1 m², which ignores numerical slivers). The nearest node is always included. This reuses the project's existing spatial association rule (flood-processing-v1 zones, also used by exposure-analysis-v1) instead of introducing a new one.

The 250 m radius is a presentation choice for "the surrounding area". It is not a hydraulic parameter.

## 3. Reported values (all taken from existing results)

Per associated node (flood-processing-v1 definitions, at the SWMM reporting timestamps):

| Field | Meaning |
|---|---|
| `condition` | `OVERFLOW` (node flooding rate > 0 at ≥ 1 timestamp), `SURCHARGE_ONLY` (water above the highest connected pipe crown, never overflowing), `NO_REPORTED_STRESS`, or `OUTFALL` (system exit; cannot overflow) |
| `overflowPeriods`, `overflowHours` | Reporting timestamps with overflow × reporting interval |
| `peakOverflowRateCms`, `peakOverflowTime` | Largest node flooding rate and its timestamp |
| `firstOverflowTime`, `lastOverflowTime` | First and last timestamps with overflow |
| `highestOverflowClass` | flood-processing-v1 display class of the peak rate (relative to this simulation; not a hazard class) |
| `approxCumulativeOverflowM3` | Trapezoidal cumulative overflow at the end of the simulation (model diagnostic) |
| `maxNodeWaterDepthM`, `maxFillRatio` | In-network SWMM node water depth and its ratio to full node depth. **Not a ground flood depth.** |

For the surrounding area: associated node counts by condition; the share of the area associated with overflowing nodes (**an influence-zone association, not a flooded area**); the **peak response** (the timestamp with the largest combined overflow rate of associated nodes, with the nodes overflowing then); the overflow period; and potential bottlenecks with an end node within the radius.

The headline `response.code` is derived only from those states:

| Code | Rule |
|---|---|
| `OVERFLOW_AT_NEAREST_NODE` | Nearest node overflowed |
| `OVERFLOW_IN_SURROUNDING_AREA` | Nearest node did not, but another associated node did |
| `SURCHARGE_ONLY` | No associated overflow, at least one surcharged node |
| `NO_REPORTED_STRESS` | No associated overflow or surcharge. The description states explicitly that this does **not** show that the location cannot flood. |

## 4. Not derived

- **Ground flood depth** (`groundFloodDepthM: null`): SWMM ran with `ALLOW_PONDING=NO`, so overflow leaves the model and node depth is capped at the rim. Model rims and the Copernicus DSM are not vertically consistent (see `FLOOD_PROCESSING_METHOD.md`).
- **Flood extent** (`floodExtentAvailable: false`): a 1D network model with sparse nodes does not define where surface water spreads.
- **Anything property-specific:** building elevation, plinth, local grading, blocked inlets, and field conditions are not modelled.

## 5. Limitations

- The drainage network representation is incomplete and some outfalls are provisional. Overflow values are simulation diagnostics, not observations.
- Short overflows between the 30-minute reporting timestamps may not be listed (the SWMM Node Flooding Summary covers them at routing-step resolution).
- A location near the ward boundary has part of its circle outside the model. The analysed share is reported.
- A what-if run (for example 1.25×) is a sensitivity scenario on the historical event. The result states which multiplier was evaluated.

## 6. API

`POST /api/v1/simulations/{simulationId}/location-check` with `{"latitude", "longitude", "radiusMeters"?}`. See `06_API_CONTRACT.md` §85.

## 7. Verification

- **Unit tests** (`backend/tests/unit/test_location_check.py`): synthetic geometry covering nearest-node/zone ownership, clipping, association, condition rules, peak selection, outfalls, bottleneck filtering, and rejection outside the study area.
- **API tests** (`backend/tests/api/test_location_api.py`): the response is cross-checked against the flood-processing-v1 product files of the same run (conditions, periods, peak rates and times, peak composition), the independently projected nearest node, and the published zone product. Also covered: invalid input, unknown and incomplete simulations, and no paths in responses.
- **Real SWMM** (`backend/tests/integration/test_real_swmm_workflow.py`): location check on a genuine SWMM 5.2.4 run of the approved model.
- The shared `compute_node_states` refactor leaves all flood-processing-v1 products byte-identical (manifest, timeline, zones, 190 time slices, diagnostics hashed before and after).
