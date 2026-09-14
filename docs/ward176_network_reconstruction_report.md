# Ward 176 Storm-Water Drain Network Reconstruction

## Method
- Used the 135 GCC Ward 176 storm-water drain geometries.
- Detected geometric intersections between drain lines.
- Split drain geometries at detected intersection points so junctions can exist inside a conduit.
- Clustered reconstructed endpoints within 2 m to represent digitization tolerance.
- Preserved original GCC ObjectIDs and dimensions.
- Interpolated invert values along split conduit pieces from the original start/end invert attributes.
- Did not fabricate long missing links. Endpoint gaps >2 m are not automatically connected.

## Result
- Original drain features: 135
- Reconstructed conduit pieces: 190
- Reconstructed nodes: 229
- Connected components: 47
- Nodes with degree >=3: 54
- Terminal nodes: 145
- Self-loop candidates: 5
- Conduit pieces flagged for geometric overlap: 2
- Provisional outlet nodes retained: 7

## Important unresolved items
- ObjectID 5793 retains its anomalous invert endpoint (20869 m) as unresolved and is flagged; it should not be used as a normal hydraulic conduit until the source value is verified.
- One pair of source drain geometries overlaps for about 2.57 m (ObjectIDs 5917 and 5920); this is flagged rather than silently deduplicated.
- Some endpoint gaps between disconnected components are >2 m. These are listed separately as candidate gaps up to 10 m and are NOT automatically connected.
- Self-loop candidates are retained as flagged geometry; they require review before SWMM import.

## SWMM implication
- The reconstructed network is suitable as the geometry/topology basis for a first-pass model, but it is not yet a claim of a fully connected physical drainage system.
- For the baseline SWMM model, unresolved/invalid elements should be explicitly excluded or represented as documented assumptions rather than silently corrected.