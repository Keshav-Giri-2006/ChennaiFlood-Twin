# Ward 176 — Targeted Hydraulic Reconstruction

## Purpose

This candidate reconstructs the hydraulic representation at the eight junctions where the deep
investigation found conflicting source invert values.

The source drain geometry and reconstructed endpoint inverts are preserved. Instead of averaging
different pipe inverts into a single SWMM node elevation, the node is assigned the **minimum
incident invert** and each higher pipe end is represented with a SWMM conduit offset.

This is a targeted candidate, not yet the final model.

## Why this representation is defensible

EPA SWMM defines a junction elevation as the invert (bottom) elevation of the junction/manhole,
while conduit inlet/outlet offsets can represent a conduit invert above that junction elevation.
EPA also notes that Dynamic Wave can represent adverse slopes and pressurized flow. citeturn0search0

The reconstruction therefore avoids silently forcing several source pipe inverts to one averaged
elevation.

## Target junctions

- J122 / J124 — C162 conflict
- J180 / J181 — C174/C175/C176 conflict
- J203 / J204 — C179/C180/C183/C014 conflict
- J061 / J057 — C190 Warning 04

For each target node:
1. New node invert = minimum incident reconstructed pipe invert.
2. Existing ground elevation was preserved by increasing/decreasing Ymax so
   `new invert + new Ymax = old invert + old Ymax`.
3. Incident conduit offsets were set so the reconstructed pipe-end invert remains equal to
   the source/reconstructed invert value.

## Important outcome

This changes the SWMM hydraulic representation without deleting any additional source drain.

C182 remains removed.

No new conduit or fabricated network connection was created.

## Expected effects

- C162 should now use its source drop of 2.192 -> 2.072 m instead of the artificial
  node-elevation rise that previously produced the -3.505% SWMM slope.
- C180 should use its reconstructed 3.0291 -> 3.001 m drop.
- C190 should no longer have identical end-node elevations; its source end inverts
  are preserved through offsets.
- C175 remains source-data suspicious: its duplicated 3.568 -> 2.466 m attributes are
  preserved rather than overwritten. This is deliberate and must be evaluated after the run.

## Do not interpret this candidate as ground truth

C175 still has suspicious source attributes. The candidate preserves them because we do not
have authoritative manhole/drop-structure data. If the run remains unstable around C175, the
next investigation should focus specifically on whether C175 is a real lateral/drop connection.

## Validation required

Run this candidate in EPA SWMM 5.2.4 and compare:
- Warning 04 count
- C162/C180/C175/C190 timestep criticality
- instability indexes
- minimum/average timestep
- non-converging steps
- routing continuity
- flooding loss

A numerical improvement does not by itself prove the source elevations are correct.
