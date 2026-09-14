# Ward 176 Targeted Hydraulic Investigation

## Scope

This investigation targets the links identified by the cleaned SWMM run as numerically
important: C162, C166, C174, C175, C180, C182, C086, and C190.

The investigation cross-checks:
- the cleaned SWMM report,
- original GCC storm-water-drain ObjectIDs,
- reconstructed geometry,
- source invert attributes,
- reconstructed node/invert data,
- component topology,
- subcatchment outlet assignment.

EPA SWMM documentation confirms that Warning 04 means the end-node elevation drop is
below 0.00035 m, so SWMM substitutes that minimum drop when calculating conduit slope.
Adverse slopes are permitted under Dynamic Wave routing. citeturn0search0

## Findings

### C182 — REMOVE

**High-confidence finding.**

C182 is source ObjectID 5917, J225→J224, length 2.566 m.

The reconstruction records show that ObjectID 5920 produced C186 over the **exact same
2.566 m J225→J224 segment**. C186 was already removed in the first cleanup as a duplicate,
leaving C182 as the remaining copy of the duplicated physical segment.

The cleaned SWMM run still identifies C182 as highly problematic:
- 24.70% of time-step criticality
- instability index 10

Therefore C182 should be removed in the next model revision. This is not an arbitrary
hydraulic adjustment; it removes a geometrically duplicated source feature.

### C162 — RETAIN FOR NOW

C162 is ObjectID 5902, a real 3.026 m source segment.

Its source invert attributes are 2.192 m → 2.072 m, but the SWMM node elevations are
J122 = 2.062 m and J124 = 2.168 m, giving the model its -3.505% adverse slope.

The conflict is not safely resolvable by simply forcing the slope positive:
the neighboring source ObjectID 5870 also supplies a different invert at the shared
J122 area. Therefore the elevation evidence is internally inconsistent.

**Decision:** retain the pipe, flag the junction for future elevation reconciliation,
and do not fabricate a correction.

### C175 — RETAIN, FLAG AS VERTICAL-CONFLICT CANDIDATE

C175 is ObjectID 5913, a real 6.114 m segment.

Its source geometry shows that it runs from approximately
(414865.76, 1435421.94) to (414871.87, 1435421.75), meeting the end/start region of
ObjectID 5912 (C174).

Both source ObjectIDs 5912 and 5913 specify a 3.568 m → 2.466 m invert drop. For C175,
that is a 1.102 m drop over only 6.1 m. The cleaned SWMM model instead uses DEM-derived
node elevations and obtains a 2.11% slope.

This suggests one of three possibilities:
1. a genuine steep/drop connection,
2. inconsistent source invert metadata, or
3. a geometric crossing that should not have been treated as a hydraulic junction.

The available data do **not** prove which interpretation is correct.

**Decision:** do not delete or alter C175 yet.

### C174 — RETAIN

C174 is the 36.105 m ObjectID 5912 segment connected to the same junction region.
It is a real source segment, not a duplicate or self-loop.

Its relationship with C175 must be resolved together with the possible vertical conflict
described above.

### C180 — RETAIN, FLAG J204

C180 is a 6.468 m split piece of ObjectID 5916.

The source/reconstructed invert sequence gives approximately 3.029 m → 3.001 m across
this split piece, whereas the SWMM node elevation at J204 is approximately 2.939 m.
This creates the reported 1.40% local model slope.

J204 is also connected to C014, which comes from a different source feature with a
different invert sequence. Therefore J204 is a genuine multi-source elevation conflict.

**Decision:** retain C180 and investigate J204 as a junction-level elevation issue
rather than changing C180 itself.

### C166 — RETAIN, BUT FLAG COMPONENT 47

C166 is a genuine 10.062 m ObjectID 5906 segment.

It belongs to component 47 and terminates at J135. The subcatchment mapping assigns
SC020 to J135, so rainfall runoff is entering a drainage fragment with no modeled
outfall.

This is a **topology/completeness issue**, not evidence that C166 itself is wrong.

**Decision:** retain C166. Do not use its flooding output as evidence of a real-world
flood location until the component's downstream connectivity is resolved.

### C086 — RETAIN

C086 is a 5.205 m split piece of ObjectID 5849.

It is not a self-loop and is part of the connected main component. Its reconstructed
invert is nearly flat, and there is no strong evidence that it is a fabricated geometry
or duplicate.

**Decision:** retain.

### C190 — RETAIN

C190 is ObjectID 5923, J061→J057, length 25.777 m.

It is a genuine source segment and not a self-loop. Its source invert attributes are
3.845 m → 3.419 m, but both SWMM node elevations are 3.632 m, which explains the
remaining Warning 04.

EPA documents that Warning 04 is triggered when the end-node elevation drop is below
0.00035 m; SWMM then uses that minimum drop for the conduit slope. citeturn0search0

**Decision:** retain for now. It should be revisited if better pipe/manhole invert
data become available.

## Final investigation decisions

| Link | Decision | Confidence |
|---|---|---|
| C182 | **REMOVE** | High |
| C162 | Retain; investigate elevation conflict | Medium |
| C166 | Retain; flag disconnected component | High |
| C174 | Retain | High |
| C175 | Retain; investigate possible vertical/crossing issue | Medium |
| C180 | Retain; investigate J204 | Medium-High |
| C086 | Retain | High |
| C190 | Retain; Warning 04 accepted temporarily | High |

## Recommended next model revision

Only one modification is currently strongly justified:

**Remove C182.**

Do **not** yet modify C162, C174/C175, C180, C166, C086, or C190.

The next important task is not more blind cleanup. It is resolving the two localized
elevation/topology clusters:

1. **C174 ↔ C175 ↔ J180**
2. **C179 ↔ C180 ↔ C183 ↔ C014 ↔ J204**

This preserves the original GCC geometry while avoiding fabricated hydraulic corrections.

## Numerical context

The cleaned model already has excellent mass conservation:
runoff continuity error is -0.018% and flow-routing continuity error is 0.038%.
The cleaned run also improved the minimum routing time step from 0.04 s to 0.50 s and
reduced nonconverging steps from 0.51% to 0.30%. fileciteturn19file3L167-L189
fileciteturn19file0L43-L57

Therefore the model should **not** be aggressively altered just to eliminate every
numerical warning. The remaining issues are localized and should be resolved from
source evidence.
