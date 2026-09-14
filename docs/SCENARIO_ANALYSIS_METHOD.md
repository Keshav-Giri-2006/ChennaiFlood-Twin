# ChennaiFlood-Twin — Scenario Analysis Method (`scenario-analysis-v1`)

Status: implemented 2026-09-14 · Code: `backend/app/simulation/scenario_transform.py`, `backend/app/services/simulation_service.py`, `backend/app/analysis/scenario_comparison.py`, `backend/app/services/comparison_service.py`

> **What-if rainfall sensitivity scenarios.** A rainfall multiplier run answers "how does *this model* respond if every rainfall intensity of the historical Michaung series were M times larger?". It is **not** a forecast, an official warning, a climate projection or a design storm.

## 1. Rainfall representation (inspected)

`ward176_hydraulic_reconstructed_candidate.inp` binds every subcatchment to rain gage `GAGE_MICH` (`INTENSITY`, 00:30 interval, `TIMESERIES Michaung`). The `[TIMESERIES]` section holds 192 records `Michaung M/D/YYYY HH:MM value` in mm/hr with 6 decimals (145 non-zero). The gage `SCF` (snow catch factor) only affects snowfall and is not used.

## 2. Transformation

For multiplier M, only the isolated workspace copy is changed:

```text
immutable approved master model (SHA-256 bb54b576…2b5c, verified)
  → copy to simulation_runs/<id>/input.inp (verified identical)
  → rewrite the value token of each "Michaung" TIMESERIES line: round(value × M, 6)  (decimal arithmetic, half-even)
  → independent verification against the master text
  → SWMM 5.2.4 → result processing (+ SWMM-applied rainfall cross-check) → flood / bottleneck / exposure / recommendation products
```

- Timestamps, interval, duration, gage definition and **every other line** stay byte-identical (verified line by line; any other difference fails the run).
- For **M = 1.00** the transformed file is byte-identical to the master model (checksum enforced).
- Maximum rounding error per value: 5 × 10⁻⁷ mm/hr.
- **Proof SWMM used the transformed rainfall:** result processing fails (`crosscheck.swmmRainfallPeakMatchesInput`, tolerance 0.001 mm/hr) if SWMM's system rainfall peak differs from the prepared series peak. This also stops a what-if run from ever being processed with baseline outputs (tested with the replay test double).

## 3. Parameter validation

`POST /simulations {"scenarioId": "michaung-2023", "parameters": {"rainfallMultiplier": M}}`

| Rule | Response |
|---|---|
| Unknown parameter keys | `422 UNSUPPORTED_PARAMETER` |
| Not a JSON number (string, boolean, null) | `422 INVALID_PARAMETER` |
| NaN / ±infinity | `422 INVALID_PARAMETER` |
| ≤ 0, < 0.5 or > 2.0 | `422 INVALID_PARAMETER` |
| More than 2 decimals | `422 INVALID_PARAMETER` |

Range and presets are configuration (`backend/config/scenarios.json` → `whatIf`): minimum 0.5, maximum 2.0, 2 decimals, presets 1.00× (baseline), 1.25×, 1.50×. The range keeps runs within a plausible sensitivity band for a single historical event; widen it only with a documented reason.

## 4. Metadata (stored per run: `artifacts.scenarioRun`, `metadata.json`, `/simulations/{id}` → `scenarioRun`)

`scenarioAnalysisVersion`, `type: rainfall-multiplier`, `parentScenarioId`, `rainfallMultiplier`, `rainfallSource {name, file, sha256}`, `baselineModelSha256`, `transformedModelSha256`, `transformedModelIdenticalToBaseline`, `transformation`, `verification {changedLines, maxAbsRoundingErrorMmHr}`, `rainfall {records, baselineTotalMm, scenarioTotalMm, baselinePeakMmHr, scenarioPeakMmHr}`, `createdAt`, plus the run's `simulationId`, `modelVersion`, processing and method versions, timestamps and `inputPreparation: rainfall-multiplier`.

## 5. Caching and isolation

- Every run has its own workspace and result directory keyed by its UUID, so a 1.25× result can never overwrite or be served as a 1.00× result.
- Completed runs are re-used, not re-run: `GET /simulations?status=COMPLETED&rainfallMultiplier=M` lists stored runs; the UI offers "Load stored M× result".
- Comparisons are cached at `results/<scenario>/comparisons/<baseline>.json` with a key of the scenario-analysis version, both runs' method versions and both SWMM output checksums.

## 6. Comparison (`GET /comparisons?baseline=&scenario=` · `POST /comparisons`)

Compatibility (else `422 COMPARISON_NOT_COMPATIBLE`): different runs, same `modelVersion`, same parent `scenarioId`, same processing version, identical flood/bottleneck/exposure/decision-support versions, identical reporting timestamps.

- **Metrics** (only those available in both): total rainfall, peak intensity, nodes with overflow, peak flooding nodes, peak overflow rate, maximum in-network node depth, flooding duration, simulated flooding volume (diagnostic), potential bottlenecks (all / HIGH), building exposure (event / peak), carriageway exposure (count / area), recommendations (all / HIGH); each with absolute and percentage change (percentage omitted when the baseline is 0).
- **Shared scale:** flood-processing-v1 overflow classes are percentile classes *per run* (baseline HIGH > 0.189 m³/s, 1.25× HIGH > 0.229 m³/s), so they are **not** compared. The map uses a categorical per-node layer (overflowing in both / only in the scenario = "additional model-derived flood influence" / only in the baseline), per timestamp or for the event, and absolute node maximum overflow rates are reported for both runs. Timeline semantics, map extent (same model nodes and zones) and KPI units are identical.
- **Bottlenecks** by SWMM link ID: New / Persisting (severity increased · unchanged · reduced) / not flagged in the scenario.
- **Exposure:** event and peak counts, buildings additionally associated in the scenario.
- **Recommendations** are generated independently for each run from its own evidence and matched by deterministic rule IDs: New / Persisting (priority change) / not triggered.
- **Statements** are generated only from these values (e.g. "C169 remains a high-concern potential bottleneck under both runs").

## 7. Results (real SWMM 5.2.4 runs, Windows build)

| Run | Model SHA-256 | Total rainfall | Peak intensity | Output |
|---|---|---|---|---|
| 1.00× `45fd5eef` | = master (`bb54b576…`) | 282.835 mm | 23.35 mm/hr | **byte-identical** to the archived baseline output (`60edc539…`) |
| 1.25× `d7c06f2f` | transformed | 353.544 mm (+25.0 %) | 29.188 mm/hr | new |
| 1.50× `2b72af92` | transformed | 424.252 mm (+50.0 %) | 35.025 mm/hr | new |

Baseline reproduction (1.00× vs archived baseline): identical routing continuity error 0.068 %, runoff continuity −0.018 %, flooding loss 197.876 ML, peak 2023-12-03 22:00 UTC (19 flooding / 4 surcharged nodes, 5.435 m³/s), 12 potential bottlenecks (C169 HIGH), 783 / 948 exposed buildings, 32 recommendations. Tolerance: exact (byte-identical output); any future SWMM build must match within the result cross-check tolerances in `result_processing.py`.

| Metric | 1.00× | 1.25× | 1.50× |
|---|---|---|---|
| Nodes with overflow (event) | 22 | 23 | 25 |
| Peak flooding nodes | 19 | 21 | 22 |
| Peak overflow rate (m³/s) | 5.435 | 7.250 (+33.4 %) | 9.556 (+75.8 %) |
| Max in-network node depth (m) | 1.358 | 1.348 | 1.406 |
| Flooding duration (h) | 90.0 | 87.5 | 92.5 |
| Simulated flooding volume (ML, diagnostic) | 197.876 | 264.649 (+33.7 %) | 336.899 (+70.3 %) |
| Routing continuity error (%) | 0.068 | 0.094 | 0.073 |
| Potential bottlenecks (HIGH/MOD/LOW) | 12 (1/0/11) | 13 (2/2/9) | 18 (2/4/12) |
| Buildings exposed peak / event | 783 / 948 | 964 / 964 | 986 / 986 |
| Recommendations (HIGH) | 32 (2) | 37 (3) | 38 (3) |

1.25× vs baseline: C169 remains HIGH; **new** C156 (GCC 5898, HIGH, low confidence); C012 and C171 increase LOW → MODERATE; additional influence at node J111 (and J140 at the peak timestamp); +16 buildings (event); 5 new recommendations (R1 C156, C012, C171; R3 J017; R5 ObjectID 5803); none withdrawn. Responses are not linear and not monotonic (duration and node depth decrease at 1.25×); no monotonic increase was assumed.

## 8. Limitations

- One uncalibrated candidate model with provisional outfalls and an incomplete network; differences are model sensitivities.
- A uniform multiplier scales intensities only; spatial pattern, timing and antecedent conditions are unchanged.
- Overflow leaves the model (no ponding), so larger rainfall mostly increases lost overflow and disconnected-component artefacts.
- Percentile overflow classes remain per-run; cross-run comparison relies on absolute values and categories.

## 9. Versioning

`SCENARIO_ANALYSIS_VERSION=scenario-analysis-v1`. Any change to the transformation, validation range semantics, compatibility rules or comparison content must bump it (cached comparisons are keyed on it).
