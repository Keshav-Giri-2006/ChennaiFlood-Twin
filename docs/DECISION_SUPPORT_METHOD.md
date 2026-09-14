# ChennaiFlood-Twin — Decision Support Method

Versions: `bottleneck-analysis-v1` · `exposure-analysis-v1` · `decision-support-v1` (built on `flood-processing-v1`)
Status: implemented 2026-09-14 · Code: `backend/app/analysis/{bottleneck_analysis,exposure_analysis,recommendations}.py`, `backend/app/services/decision_service.py`

> **Academic prototype decision-support rules.** Everything in this document is derived from one uncalibrated EPA SWMM 5.2.4 simulation of a reconstructed, fragmented drainage network with provisional outfalls. The outputs are **not** official municipal engineering assessments, hazard zoning, damage estimates or field-confirmed diagnoses.

## 1. Inputs actually available (inspected before design)

| Source | Variables used | Notes |
|---|---|---|
| SWMM report `.rpt` — Link Flow Summary | max flow, time of max, max velocity, **Max/Full Flow**, Max/Full Depth | Max/Full Flow = peak flow ÷ full normal-flow capacity (2 decimals) |
| SWMM report — Conduit Surcharge Summary | **Hours Full Both Ends / Upstream / Downstream**, Hours Above Full Normal Flow, **Hours Capacity Limited** | SWMM lists only conduits with any full-flow condition; values below 0.01 h are printed as 0.01 |
| SWMM report — Node Flooding / Node Surcharge Summary | hours flooded, max rate, volume; hours surcharged | routing-step resolution |
| SWMM report — Time-Step Critical Elements, Highest Flow Instability Indexes, Warnings | numerical diagnostics | **never** used as bottleneck evidence |
| SWMM `.out` | node flooding per 30-min reporting step (via flood-processing-v1 slices), link capacity series (served by `/timeseries/links`) | |
| SWMM `.inp` | conduit endpoints, lengths, cross-sections, outfalls | connectivity components |
| `data_processed/network/ward176_resolved_conduits.csv` | GCC ObjectID ↔ model link, source width/depth, `status` (Good/Bad), `puca_kacha`, `flow_direction` | traceability, condition |
| `ward176_invert_resolution_decisions.csv` | invert screening decision per ObjectID | confidence |
| `ward176_storm_water_drains.geojson` | `obstacles` attribute (e.g. "Electric Pole") | maintenance rule |
| `ward176_buildings.geojson` (6,428), `ward176_carriageways.geojson` (301 polygons), EPSG:32644 | footprints | exposure |
| `backend/config/models.json` → `diagnosticContext` | curated decisions of the project hydraulic investigations for C162, C166, C175, C180, C190 | context only |

Not available (so not used): field observations, pipe condition surveys with dates, observed flooding, building heights/use/occupancy, road centre-lines, ground flood depth or extent.

## 2. Potential bottleneck definition (`bottleneck-analysis-v1`)

A **potential drainage bottleneck** is a SWMM conduit whose simulated results show *hydraulic loading on that conduit*. It is a model diagnostic, not a confirmed failure.

Screening criteria (all from the report of the same simulation):

| ID | Criterion | Threshold | Why |
|---|---|---|---|
| L1 | Capacity limited (SWMM) | Hours Capacity Limited > 0.01 h | SWMM's own conduit-restriction flag: upstream end full **and** hydraulic gradient steeper than the conduit slope. The only criterion that isolates the conduit itself from backwater. |
| L2 | Sustained full-bore surcharge | Hours Full Both Ends ≥ 1.0 h | ≥ two 30-min reporting intervals; excludes transient surcharge |
| L3 | Peak flow above full-flow capacity | Max/Full Flow > 1.0 | peak demand exceeds full normal-flow capacity |
| S1 | Connected node flooding (supporting) | an end node floods ≥ 1.0 h | links the conduit to simulated overflow; cannot flag a conduit on its own |

Eligibility: at least one of L1–L3. Connected flooding alone, visual appearance, or numerical instability never flag a conduit.

## 3. Scoring, classes and confidence

- `score = criteria met / 4` (0.25 … 1.0). Transparent count, no weights.
- Severity (diagnostic concern): **HIGH** ≥ 3 criteria, **MODERATE** = 2, **LOW** = 1.
- **Network-context cap:** if the conduit's model component (undirected node–link graph of the `.inp`) contains **no outfall**, water can only leave by overflow; loading there reflects the incomplete network, not conduit capacity. Severity is capped at LOW (`uncappedSeverity` keeps the uncapped class) and confidence is LOW.
- Confidence: **MEDIUM** when no caveat applies; **LOW** when any applies — component without outfall; GCC invert screening decision other than `ACCEPT_PROVISIONALLY`/`RETAIN_GCC_INVERT`; source flow direction not `START_TO_END`; SWMM Warning 02 at an end node; link listed in the project investigations. **HIGH is never assigned in v1** (uncalibrated model, provisional outfalls).
- These are relative screening classes, not engineering failure thresholds.

Numerical diagnostics (time-step critical %, flow instability index) are reported separately as `numericalDiagnostics` with the project investigation context.

### 3.1 Results — Michaung 2023 (simulations `3107a60b…`, `2ee95512…`, UI run `0ada7d8e…`; identical)

The undirected node–link graph of the current `.inp` has 48 connected components (the reconstruction table lists 47 `component_id_after` values; the one-component difference was not investigated further); **only 4 contain an outfall**. 182 conduits screened → **12 potential bottlenecks: 1 HIGH, 0 MODERATE, 11 LOW** (6 in components without outfall).

| # | Link | GCC ObjectID | Nodes | Severity | Score | Conf. | Capacity-limited h | Full both ends h | Max/Full Flow | S1 | Outfall |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | C169 | 5909 | J161→J177 | HIGH | 1.00 | MEDIUM | 9.47 | 9.47 | 2.20 | J161 (74.3 h) | yes |
| 2 | C020 | 5805 | J210→J205 | LOW (uncapped HIGH) | 0.75 | LOW | ≤0.01 | 81.79 | 1.39 | J205 | no |
| 3 | C021 | 5806 | J205→J210 | LOW (uncapped HIGH) | 0.75 | LOW | ≤0.01 | 81.79 | 1.39 | J205 | no |
| 4 | C014 | 5799 | J208→J204 | LOW (uncapped MODERATE) | 0.50 | LOW | ≤0.01 | 58.12 | 0.70 | J208 | no |
| 5–7 | C052, C099, C051 | 5828, 5857, 5828 | component of J006 | LOW | 0.25 | LOW | ≤0.01 | 66–69 | ≤0.07 | — | no |
| 8 | C171 | 5910 | J173→J171 | LOW | 0.25 | LOW (invert flag) | ≤0.01 | 6.17 | 0.79 | — | yes |
| 9 | C012 | 5797 | J185→J173 | LOW | 0.25 | MEDIUM | ≤0.01 | 2.85 | 0.18 | — | yes |
| 10–12 | C152, C172, C005 | 5895, 5911, 5791 | — | LOW | 0.25 | MEDIUM | — | — | 1.66 / 1.50 / 1.21 | — | yes |

**C169 evidence:** 123.8 m, 0.78 × 0.78 m closed rectangular; max flow 0.525 m³/s at 2023-12-03 21:51 UTC; max velocity 0.86 m/s; derived full-flow capacity 0.239 m³/s; full downstream 74.5 h; upstream node J161 overflows 74.3 h, max 0.593 m³/s, 26.97 ML simulated overflow; component drains to provisional outfall OUT218.

**Investigated links:** C162 (35.7 % time-step critical, Max/Full Flow 0.11, never full), C180 (33.0 %), C175 (17.9 %), C086 (12.6 %) and C166 (instability index 11, component without outfall) meet **no** loading criterion and are *not* potential bottlenecks. This supports the earlier investigations: their behaviour is numerical/elevation-data related, not capacity related.

### 3.2 Time-varying state (`bottleneck-timeline-v1`, added 2026-09-14)

A separate, additive product; the event-level classification above is unchanged. For every 30-minute SWMM reporting sample t (binary output link variables) and each event-level potential bottleneck:

| Criterion | Definition |
|---|---|
| T-FULL | SWMM link capacity variable (fraction of conduit filled) ≥ 0.999 |
| T-OVER | abs(flow) > full-flow capacity, back-calculated from the report (maximum flow ÷ Max/Full Flow; only where that ratio ≥ 0.5, otherwise not evaluated) |
| T-FLOOD | an end node is in flood-processing-v1 state FLOODING at t |

- Active at t = event-level potential bottleneck **and** (T-FULL or T-OVER). Conduits that are not event-level potential bottlenecks are never activated.
- Severity at t = HIGH (3) / MODERATE (2) / LOW (1) criteria, **never above the event-level severity** (so the no-outlet cap and confidence safeguards carry over).
- SWMM's capacity-limited condition (L1) exists only as event hours and is not evaluated per sample.
- "Most loaded conduit" = highest abs(flow) ÷ full-flow capacity among the 15 conduits with a back-calculable capacity.
- API: `GET /simulations/{id}/bottlenecks/timeline[?time=]`; the Hydraulics panel and the map follow the timeline without moving the camera.

Michaung baseline (demo result): 163 of 190 timestamps have ≥ 1 active potential bottleneck (first 2023-12-02 14:00 UTC). **C169 is active HIGH in 19 samples = 9.5 h** (consistent with the report's 9.47 h capacity limited / full at both ends): 03 Dec 18:30–19:00 and 20:30 → 04 Dec 03:30 UTC plus two isolated samples later on 04 Dec, with peak utilisation 2.20× at 2023-12-03 22:00 UTC; it is inactive at 19:30–20:00 UTC (at 19:30 not full, 85 % of capacity). At the peak, 12 potential bottlenecks are active (C169 HIGH, others LOW) and C169 is the most loaded conduit. The no-outlet conduits C020/C021 are active (LOW) for 81.5 h.

## 4. Model-derived exposure (`exposure-analysis-v1`)

- **Exposed** = a GCC building footprint or carriageway polygon intersects (area > 0.01 m², a numerical tolerance for shared zone edges) the flood influence zone of a node in state `FLOODING` at the considered timestamp(s).
- Zones: identical nearest-node Voronoi zones of flood-processing-v1, recomputed in EPSG:32644. Unsimplified source geometry; invalid polygons would be repaired with `make_valid` (none needed in this dataset).
- Scopes: per reporting timestamp (190), peak timestamp, and event (any timestamp). Footprint/road area within zones is summed per asset (zones do not overlap, so no double counting).
- Roads: carriageways are polygons → count and **area**; no road length is derived.
- Also reported: exposed buildings associated with nodes in components without an outfall.

Terminology: "model-derived exposure" / "assets within model-derived flood influence zones". Never "flooded", "damaged" or "affected".

### 4.1 Results (Michaung)

| Scope | Buildings intersecting | % of 6,428 | Footprint within zones | Carriageways | Carriageway area |
|---|---|---|---|---|---|
| Peak 2023-12-03 22:00 UTC | 783 | 12.2 % | 99,355 m² | 68 | 23,085 m² |
| Max concurrent (22:30 UTC) | 818 | — | — | — | 24,009 m² |
| Event (any timestamp, 20 nodes) | 948 | 14.8 % | 114,832 m² (11.6 %) | 81 (26.9 %) | 26,654 m² (10.0 %) |

552 of the 948 event buildings are associated with nodes in components **without** an outfall. Largest per-node exposure: J140 (165 buildings), J176 (85, no outfall), J205 (78, no outfall), J009 (76). Largest flooding-node zone 30,750 m² (J009); no zone extends outside the ward (validated in flood-processing-v1).

## 5. Recommendation rules (`decision-support-v1`)

Each recommendation carries `priority`, `confidence`, `title`, `recommendation`, `why`, `evidence` (metrics with source, SWMM link ↔ GCC ObjectID pairs, nodes), `drivers`, `confidenceReasons`, `focus` geometry IDs and a disclaimer. A rule fires only when its evidence exists.

| Rule | Trigger | Recommendation | Priority | Confidence |
|---|---|---|---|---|
| R1 | Potential bottleneck HIGH/MODERATE in a component with an outfall | Assess drainage capacity/condition of the corridor | HIGH for HIGH, else MEDIUM | bottleneck confidence |
| R2 | Overflowing nodes in a component **without** a model outfall | Field-verify downstream connection/outfall before interpreting flooding | HIGH ≥ 10 % of simulated flooding, MEDIUM ≥ 2 %, else LOW | MEDIUM |
| R3 | Node (outfall component) overflowing ≥ 24 h or ≥ 5 % of simulated flooding, not covered by R1 | Prioritise drainage inspection around the node | MEDIUM | MEDIUM |
| R4 | Overflowing node (outfall component, ≥ 6 h) whose zone intersects buildings ≥ 75th percentile of such nodes | Consider local preparedness/access planning | MEDIUM | LOW |
| R5 | GCC drain `status = Bad` or `Kacha` (MEDIUM) or recorded `obstacles` (LOW) **and** hydraulic evidence (potential bottleneck, ≥ 1 h full at an end, or connected node overflowing ≥ 1 h) | Maintenance/condition inspection | MEDIUM / LOW | LOW (attribute date unknown) |
| R6 | Link time-step critical ≥ 10 % | Verify invert/manhole data | LOW | MEDIUM with project investigation, else LOW |

Thresholds are documented prototype choices (≥ 1 h = two reporting intervals; ≥ 24 h = one day of the 4-day event; 5 %/10 % shares of simulated flooding; 75th percentile relative to this simulation). They are not standards.

### 5.1 Results (Michaung): 32 recommendations — HIGH 2, MEDIUM 13, LOW 17 (R1 1, R2 11, R3 3, R4 2, R5 11, R6 4)

- **HIGH · R1** Assess drainage capacity of C169 (GCC 5909), J161 → J177 — 4/4 criteria.
- **HIGH · R2** Verify downstream connection of the component around J176 (GCC 5818, 5912, 5913, 5914) — no outfall, 12.4 % of simulated flooding; contains C175.
- **MEDIUM · R2** components around J006 (8.8 %), J186 (7.3 %), J078 (6.9 %), J205/J210 (6.8 %), J208 (5.9 %, contains C180), J214 (3.2 %).
- **MEDIUM · R3** inspection around J009 (72.9 h, 12.2 %), J110 (20.5 h, 12.1 %), J140 (49.4 h).
- **MEDIUM · R4** preparedness near J140 (165 buildings) and J009 (76 buildings).
- **MEDIUM · R5** maintenance of GCC 5797 (C012; Bad, Kacha; full 79 h) and 5855 (C095/C096; Bad, Kacha; J009 overflows 72.9 h). LOW · R5 for 9 drains with recorded obstacles plus hydraulic evidence.
- **LOW · R2** components around J128 (incl. C166 / J130 / J135), J158, J142, J219.
- **LOW · R6** verify invert/manhole data at C162 (J122–J124), C180 (J203–J204), C175 (J181–J180), C086 (J085–J086).

## 6. Risk indicator — deliberately not derived

A `hazard × exposure` indicator was evaluated and **not implemented**. The hazard term would be node overflow without ground depth or extent (overflow is lost from the model with `ALLOW_PONDING NO`), 57 % of simulated overflow volume occurs in components without an outfall, and influence zones are associations rather than inundated areas. Multiplying two proxies would imply a spatial risk surface the data cannot support. `/risk` and `/risk/geojson` return `404 RISK_PRODUCT_NOT_AVAILABLE`; exposure and recommendations are provided instead. No monetary, casualty, probability or structural-damage values exist anywhere in the system.

## 7. Limitations

- Single uncalibrated simulation; provisional outfalls; first-pass roughness, infiltration and subcatchments.
- SWMM surcharge durations include backwater effects; L2/L3 may flag conduits whose restriction lies downstream (only L1 isolates the conduit).
- Component-without-outfall artifacts dominate many results; they are flagged, capped and turned into data-verification recommendations rather than capacity claims.
- GCC condition/obstacle attributes have unknown survey dates.
- Exposure inherits all influence-zone limitations (nearest-node association, sparse drainage → large zones, no depth).
- Classes and percentile thresholds are relative to one scenario; not comparable across scenarios without a shared scale.

## 8. Provenance, storage and versioning

- Storage: `RESULTS_DIR/<simulationId>/decision/{manifest.json, bottlenecks.json, bottlenecks.geojson, exposure.json, exposure_assets.json, recommendations.json}`; generated during PROCESSING (after flood products) or lazily for older completed runs.
- The manifest records all four versions (flood, bottleneck, exposure, decision support), the SWMM output SHA-256 and report SHA-256. Products are regenerated only if a version or the output checksum changes; the same inputs reproduce the same content (tested).
- Any change to criteria, thresholds or rules **must** bump the corresponding version (`BOTTLENECK_ANALYSIS_VERSION`, `EXPOSURE_ANALYSIS_VERSION`, `DECISION_SUPPORT_VERSION`); cached products of the old version are otherwise reused.
