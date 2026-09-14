# ChennaiFlood-Twin — Flood Processing Method (`flood-processing-v1`)

Status: implemented 2026-09-13 · Code: `backend/app/analysis/flood_processing.py`, `backend/app/services/flood_service.py`

## 1. What this product is — and is not

`flood-processing-v1` turns the EPA SWMM 5.2.4 output of the current candidate
model into a **time-indexed, spatially associated representation of simulated
node flooding** for the Digital Twin.

It produces, for every SWMM reporting timestamp:

- **Simulated node states** at model drainage nodes: `FLOODING` (overflow) or `SURCHARGED`.
- **Flood influence zones** — the area whose nearest modelled drainage node is overflowing.

It deliberately does **not** produce:

| Not produced | Why |
|---|---|
| Ground (surface) flood depth | See §4. SWMM ran with `ALLOW_PONDING NO`: overflowing water leaves the model and node depth is capped at the rim, so no surface water depth exists in the output. Model rim elevations and the Copernicus DSM are not vertically consistent. |
| Flood extent | A 1D drainage model with sparse nodes does not simulate where surface water spreads. Influence zones are an *association*, not an extent. |
| 2D/3D hydraulic solution | SWMM is a 1D network model. No overland-flow computation is performed here. |

API: `/api/v1/simulations/{id}/flood/extent` and `/flood/depth` return `404 FLOOD_PRODUCT_NOT_AVAILABLE` with this explanation.

## 2. Inputs

### 2.1 SWMM variables (binary `.out`, per reporting period)

| Variable | SWMM meaning | Unit (CMS model) | Use |
|---|---|---|---|
| Node depth | Water depth above node invert | m | Surcharge test, fill ratio, inspection |
| Node head | Invert elevation + depth (model datum) | m | Inspection only |
| Node flooding | Overflow rate lost from the node | m³/s | `FLOODING` state, classes, cumulative volume |
| System rainfall | Rainfall intensity applied | mm/hr | Timeline context |
| System flooding | Total overflow rate | m³/s | Timeline, peak detection |

Also read (report `.rpt`): Node Flooding Summary, Node Surcharge Summary, Flow Routing Continuity (flooding loss) — used only for cross-checks.

Link flow/depth/velocity/capacity are exposed separately via `/timeseries/links/{linkId}`; they are not used by v1.

### 2.2 Model structure (`input.inp` of the simulation workspace)

- Junction invert elevation and max depth; outfalls.
- Conduit endpoints, `InOffset`/`OutOffset` (`LINK_OFFSETS DEPTH`), cross-section full depth.

### 2.3 Spatial inputs

| Dataset | CRS | Use |
|---|---|---|
| `data_processed/network/ward176_resolved_nodes.csv` | EPSG:32644 | Model node locations (`Jnnn`/`OUTnnn` = resolved node `nnn`; mapping validated against the `.inp`) |
| `data_processed/gis/ward176_boundary.geojson` | EPSG:32644 (declared, checked) | Clipping |

The Copernicus DEM is **not** used by v1 (see §4).

## 3. Algorithm

Temporal resolution: SWMM reporting step, 30 minutes. The Michaung run has **190 reporting timestamps**, 2023-12-02T00:30Z to 2023-12-05T23:00Z. All times are UTC, inherited from the IMERG rainfall time basis. The first report time is one step after the simulation start; no timestamp is invented.

1. **Crown height per junction:** the maximum over connected conduits of (end offset + full cross-section depth).
   **Effective full depth:** max(max depth, crown). SWMM Warning 02 raises max depth to the crown, as for J057, J061, J122, J180, J181, J203 and J204.
2. **Node state at timestamp *t*** (junctions only, because free outfalls cannot flood):
   - `FLOODING` if the flooding rate is > 0 m³/s.
   - `SURCHARGED` if the node is not flooding and depth > crown + 0.001 m.
3. **Overflow class:** assigned to `FLOODING` nodes only.
   - Breaks are the 50th and 90th percentiles (linear interpolation) of all non-zero node flooding-rate samples in the simulation.
   - LOW ≤ p50 < MODERATE ≤ p90 < HIGH.
   - These are **visualisation classes relative to this simulation**, not hazard thresholds. Michaung: p50 = 0.0152, p90 = 0.1893, max = 0.9231 m³/s.
4. **Fill ratio:** depth / effective full depth.
5. **Approximate cumulative overflow volume** per node: trapezoidal integration of the reporting-period flooding rates, with zero flooding at the simulation start. This is labelled *approximate*: SWMM integrates at routing steps (0.5–30 s), so events shorter than 30 minutes can be missed.
6. **Flood influence zones:**
   - Voronoi (nearest-node) cells of all 228 model nodes, computed in EPSG:32644 and clipped to the Ward 176 boundary.
   - This is the same nearest-collector-node principle used to generate the project's first-pass subcatchments.
   - No distance cap or other tuning parameter is applied.
   - Nodes outside the ward keep only the in-ward part of their cell. J035's cell lies entirely outside the ward and has no zone.
   - Zones were **not** clipped to subcatchments: those cover only 77% of the ward, and 63 nodes (including flooding nodes J006 and J009) lie outside every subcatchment.
7. **Time-slice product:** for each timestamp, a GeoJSON FeatureCollection with:
   - a point feature per `FLOODING`/`SURCHARGED` node;
   - an influence-zone polygon per `FLOODING` node.
8. **Web CRS:** products are transformed to lon/lat (OGC:CRS84, RFC 7946) with pyproj (EPSG:32644 → EPSG:4326, `always_xy`) and rounded to 7 decimals (~1 cm).

## 4. Why ground flood depth is not derived (evidence)

A common post-processing approach is *depth = water-surface elevation − terrain elevation*. It is not defensible with the current data:

1. **No surface water in SWMM output:** with `ALLOW_PONDING NO`, SWMM discards overflow. At every flooding node the node depth equals the (effective) max depth, i.e. head = rim elevation. For example, J006 depth is 1.070 m (max depth 1.07) at peak overflow, and node stored volume is 0.
2. **Vertical datum inconsistency:** at the 212 junctions with valid DEM cells, DEM − model rim elevation has a median of **+3.7 m** (p10 +1.1 m, p90 +5.6 m, range −1.9 to +9.1 m). A drain rim should lie near ground level. The GCC invert datum and Copernicus GLO-30 (EGM2008, DSM) are therefore not consistent, so head − DEM would be negative at almost every flooding node.
3. **Resolution:** the DEM is a 30 m DSM that includes buildings. The median influence zone (≈6,400 m²) spans only ~7 DEM cells, too coarse to justify a terrain-refined extent within zones.

A terrain-aware product could become `flood-processing-v2` if datum-consistent elevations and a ponding-enabled (or 2D) model become available. That would require a documented model change (CLAUDE.md §9).

## 5. Validation performed on every run

Hard checks (processing fails if violated):

- zones valid, within the ward, non-overlapping, and exactly partitioning the ward area;
- output timestamps strictly increasing;
- nodes flooding in output samples ⊆ the SWMM report Node Flooding Summary;
- |approximate cumulative overflow − report flooding loss| ≤ 5%;
- all product coordinates inside the Chennai lon/lat envelope (catches CRS errors).

Soft checks (recorded in `diagnostics.json` and exposed via `GET /flood` → `validation`):

- report flooding nodes not seen in 30-min samples;
- surcharge detection vs the report Node Surcharge Summary.

Michaung candidate run results (simulation `3107a60b…`, also the integration tests):

| Check | Result |
|---|---|
| Zones | 227 valid zones; sum = union = ward area 1,786,224 m² |
| Cumulative overflow vs report | 200,125 m³ vs 197,876 m³ (+1.14%) |
| Flooding nodes | 20 in samples ⊆ 22 in report; J130 (0.01 h) and J135 (0.08 h) overflow only between reporting times |
| Surcharge | Sampled set ⊆ report set; report-only nodes are J130 and J135 |
| Peak | 2023-12-03T22:00Z: 19 overflowing and 4 surcharged nodes; system overflow 5.435 m³/s |
| Flooding duration | 90 h (180 of 190 timestamps have ≥ 1 overflowing node) |

## 6. Terminology (use exactly)

| Term | Meaning |
|---|---|
| Simulated node flooding / overflow rate | SWMM node flooding variable (m³/s) |
| Node water depth | SWMM node depth inside the drainage node, **not** ground flood depth |
| Flood influence zone | Nearest-model-node cell of an overflowing node; association, **not** extent |
| Simulated flooding volume | SWMM flooding loss; model diagnostic under an incomplete network, **not** observed flood volume |

Never use: observed flood depth or volume, flood extent (for zones), water level (for node depth).

## 7. Limitations

- All limitations of the candidate model apply: fragmented network, provisional outfalls, uncalibrated parameters, first-pass subcatchments.
- Overflow at a node is lost from the model. Real water would spread, pond or re-enter drains, which is not represented.
- Influence zones depend on where drainage nodes exist. Sparse drainage produces large zones, and areas far from any drain are associated with the nearest node regardless of distance.
- 30-minute sampling misses short overflow events (J130, J135) and approximates cumulative volume.
- Overflow classes are relative to one simulation. They are not comparable across scenarios without a shared scale.

## 8. Provenance and versioning

- Every artifact records `simulationId`, `scenarioId`, `modelVersion`, `floodProcessingVersion` and `generatedAt`. The manifest also stores the SHA-256 of the SWMM output it was generated from.
- Storage: `RESULTS_DIR/<simulationId>/flood/{manifest.json, timeline.json, zones.geojson, diagnostics.json, timeslices/<YYYYMMDDTHHMMSSZ>.geojson}`.
- Caching: products are regenerated only if `FLOOD_PROCESSING_VERSION` or the output checksum changes. The same inputs and version produce byte-identical products (tested).
- Any change to the algorithm's meaning must create `flood-processing-v2`, not silently alter v1.
