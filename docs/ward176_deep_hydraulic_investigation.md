# Ward 176 — Deep Hydraulic Investigation

## Purpose

This investigation follows the C182-removal SWMM run and focuses on the remaining hydraulic hotspots:
C162, C175, C180, with C166 and C190 reviewed as controls.

## Key conclusion

**No additional conduit should be deleted at this stage.**

The remaining instability is primarily associated with **conflicting source invert attributes at reconstructed junctions**, not with obvious duplicate geometry.

### 1. C162 — J122 to J124

- GCC ObjectID: 5902
- Length: 3.026 m
- Width/depth: 1.13 m
- Source invert: 2.192 -> 2.072 m
- SWMM slope: -3.5051%
- SWMM timestep criticality in final-candidate run: 41.06%

The segment is geometrically real and should be retained.

However, its endpoints conflict with neighboring source records:

- At J122, C115 (ObjectID 5870) ends at 1.932 m while C162 starts at 2.192 m.
- At J124, C159 (ObjectID 5900) ends at 2.168 m, C160 (ObjectID 5901) starts at 2.192 m, while C162 ends at 2.072 m.

Thus the current SWMM junction elevations are necessarily compromises. This is a **junction/invert-data problem**, not enough evidence for deletion.

**Action:** retain C162; do not fabricate an elevation correction yet.

### 2. C175 — J181 to J180

- GCC ObjectID: 5913
- Length: 6.114 m
- Source invert: 3.568 -> 2.466 m
- SWMM slope: +2.1104%
- Final-candidate instability index: 12
- Final-candidate timestep criticality: 19.04%

The geometry is unusual: C175 is a short lateral-looking segment whose endpoint is clustered with the start of C174 (ObjectID 5912), while its other endpoint is connected to C176.

Most importantly, C175's source invert attributes are **exactly the same as C174's**, despite C175 being only 6.1 m long and representing different geometry.

That is strong evidence of a possible source-attribute artifact.

However, there is not enough evidence to replace its inverts or reverse its direction automatically.

**Action:** retain C175 and investigate the J181/J180 structure before editing.

### 3. C180 — J203 to J204

- GCC ObjectID: 5916
- Length: 6.468 m
- SWMM slope: +1.4009%
- Final-candidate timestep criticality: 30.29%
- Final-candidate instability index: 8

C180 is a genuine split piece of ObjectID 5916.

The problem is at its junctions:

**J203**
- C179 ends at interpolated invert ~3.029 m.
- C183 (ObjectID 5918) starts at 3.703 m.
- Therefore two connected source segments disagree by ~0.674 m.

**J204**
- C014 (ObjectID 5799) ends at 2.876 m.
- C180 ends at 3.001 m.
- Difference ~0.125 m.

The SWMM model uses compromise junction elevations rather than fabricating separate hydraulic structures.

**Action:** retain C180; investigate J203/J204 as possible manhole/drop structures.

### 4. C166

C166 remains a real segment in a disconnected network component. Its instability should not be treated as proof of bad geometry.

**Action:** retain. Do not invent long connections to an outlet.

### 5. C190

C190 remains the only SWMM Warning 04.

EPA documents Warning 04 as the minimum elevation drop of 0.00035 m being used when the end-node elevation drop is smaller.

**Action:** retain for now and revisit with better invert/manhole data.

## Overall decision

### Remove
- None.

### Retain
- C162
- C166
- C174
- C175
- C180
- C086
- C190

### High-priority investigation zones
1. J122/J124 — C162
2. J181/J180 — C175/C174/C176
3. J203/J204 — C180/C179/C183/C014

## Why we are not making arbitrary fixes

EPA SWMM Dynamic Wave solves the one-dimensional Saint Venant equations and permits adverse conduit slopes. Therefore a negative or unusual slope by itself is not sufficient evidence that a conduit is wrong.

The correct next step is to resolve the underlying elevation/topology ambiguity rather than forcing every segment to have a positive slope.
