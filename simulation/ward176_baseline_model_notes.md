# Ward 176 SWMM Baseline Model Notes

## Model
- File: `ward176_baseline.inp`
- Subcatchments: 35
- Usable reconstructed conduit records: 189
- Resolved nodes represented in links: 228
- Provisional outfalls: 7
- Rainfall records: 192

## Important data treatment
- Original GCC ObjectID 5793 is excluded from hydraulic links because its `invert_end` is 20869 m and was flagged anomalous during validation.
- The seven outlets remain provisional boundary-terminal candidates.
- The mapped GCC network remains fragmented; no unverified long-distance synthetic pipes were added.
- Node hydraulic elevations are based primarily on incident GCC invert elevations where available. Nodes without usable incident invert values use a placeholder and must be reviewed before final calibration.
- Conduit cross-sections are rectangular closed sections using GCC width/depth attributes.
- Concrete conduits use a first-pass Manning n assumption.
- Green-Ampt parameters are first-pass assumptions and are not field-calibrated.
- 35 subcatchment polygons/parameters are first-pass GIS-derived regions and should be retained as the current baseline unless later validation indicates changes.

## Rainfall
NASA GPM IMERG Final Run Michaung 2023 30-minute rainfall-rate series is included as the `Michaung` time series and assigned to `GAGE_MICH`.

## Validation status
This is a **first-pass baseline model file**, not yet a validated hydraulic prediction. The next step is to run an SWMM parser/solver and fix any structural or hydraulic errors before interpreting flooding results.
