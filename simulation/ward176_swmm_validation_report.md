# Ward 176 SWMM Baseline Validation Report — Corrected

## Static input validation

**Result: PASS (input structure corrected)**

The generated `ward176_baseline.inp` was corrected after EPA SWMM 5.2.4 reported **ERROR 209: undefined object 0** for every subcatchment. The cause was an extra `0` in each `[SUBCATCHMENTS]` record, which SWMM interpreted as a `SnowPack` object name. The model does not use snow modelling, so the optional SnowPack field has been removed.

- Subcatchments: 35
- Junctions: 222
- Outfalls: 6
- Conduits: 189
- Cross-sections: 189
- Infiltration records: 35
- Rainfall records: 192
- Undefined subcatchment outlets: 0
- Undefined conduit nodes: 0
- Missing conduit cross-sections: 0
- Duplicate primary IDs detected: 0
- Rainfall chronology errors: 0
- Negative/NaN rainfall values: 0
- ObjectID 5793 included hydraulically: NO
- SnowPack references: 0
- `[SUBCATCHMENTS]` data fields per record: 8 (correct for a model without SnowPack)

### Correct `[SUBCATCHMENTS]` format

Each record now contains:

`Name RainGage Outlet Area %Imperv Width %Slope CurbLen`

For example:

`SC001 GAGE_MICH OUT090 0.437725 73.908 66.161 3.1680 0`

There is **no trailing SnowPack field**.

## Hydraulic consistency checks

- Resolved conduit records used: 189
- Reconstructed network components: 47
- Components containing a provisional outfall: 4
- Components without a provisional outfall: 43
- Negative conduit slopes: 37/189
- Near-zero slopes: 6/189

Negative slopes are not automatically invalid under dynamic-wave routing, but they remain flagged for later hydraulic review.

## Outlet correction

The original candidate outlet corresponding to reconstructed node **96** was removed as an outfall because the reconstructed geometry shows conduit 5839 continuing from node 96 to node 90.

The baseline therefore uses six provisional outfalls:

`OUT090, OUT099, OUT100, OUT127, OUT143, OUT218`

Node 96 remains a junction.

## Important limitations

This is a **first-pass academic prototype**, not a calibrated operational flood model.

The GCC drainage network remains fragmented: 43 reconstructed components do not contain one of the provisional outfalls. These components have intentionally not been connected with invented long-distance pipes.

Manning roughness, Green-Ampt parameters, and some hydraulic interpretations are modelling assumptions.

The anomalous GCC ObjectID 5793 (`invert_end = 20869 m`) remains excluded.

## Solver validation status

The first local EPA SWMM 5.2.4 run reached input parsing but stopped immediately with ERROR 209 because of the invalid SnowPack placeholder. **No numerical hydraulic simulation was performed in that failed run.**

This corrected file is now ready for the next EPA SWMM 5.2.4 run.

### Expected next step

Run the corrected `ward176_baseline.inp` through EPA SWMM 5.2.4 again. If the engine completes successfully, inspect the `.rpt` for continuity, flooding, routing, and warning statistics before interpreting flood depths or volumes.
