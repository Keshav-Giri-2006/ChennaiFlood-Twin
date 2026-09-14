# Ward 176 Final Candidate SWMM Model — Change Log

## Change made

Removed **C182** from the SWMM model.

- C182 represented GCC ObjectID 5917.
- It was identified as an exact duplicate of C186 / GCC ObjectID 5920.
- C186 was removed in the previous cleanup.
- C182 was therefore removed now as the remaining duplicate representation.

Its matching `[XSECTIONS]` record was also removed.

## No other hydraulic changes

The following were intentionally left unchanged:

- C162
- C166
- C174
- C175
- C180
- C086
- C190
- all node elevations
- all conduit dimensions
- all Manning roughness values
- all subcatchments
- rainfall data
- outfalls
- Dynamic Wave routing
- Green-Ampt infiltration
- reporting / wet / routing timesteps

This is important because the next SWMM run should isolate the effect of removing
the duplicated C182 segment.

## Structural verification

- Previous cleaned-model conduits: 183
- Candidate-model conduits: 182
- Candidate-model XSECTION records: 182
- Subcatchments: 35
- Outfalls: 6
- Dangling conduit → XSECTION references: 0
- Dangling XSECTION → conduit references: 0
- C182 still present: False

Expected result:

- **182 active conduits**
- **182 XSECTION records**
- zero C182 references

## Next validation

Run this candidate model in EPA SWMM 5.2.4 and compare it against the immediately
previous cleaned run.

The key comparison is not merely whether the warning count decreases. Check:

1. Runoff continuity error.
2. Flow-routing continuity error.
3. Minimum and average routing timestep.
4. Percentage of non-converging steps.
5. Highest continuity-error nodes.
6. Highest flow-instability links.
7. Total flooding loss.
8. External outflow.

Do not change additional elevations or delete C162/C175/C180/C190 based only on the
next numerical report. Those links require source/GIS-level evidence.
