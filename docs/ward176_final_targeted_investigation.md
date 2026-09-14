# Ward 176 — Final Targeted Hydraulic Investigation

## Scope
Prioritized investigation of C175/J180, C180/J203-J204, and C166 using the reconstructed network, original GCC drain attributes, reconstructed topology, and the reconstructed SWMM candidate. No hydraulic parameter was changed during this investigation.

## 1. C175 / J181-J180 — RETAIN, FLAG
- GCC ObjectID 5913; 6.114 m; source invert 3.568 -> 2.466 m.
- C175 starts exactly where ObjectID 5914 (C176) ends.
- ObjectID 5912 (C174) and ObjectID 5913 (C175) have a geometric intersection recorded by the reconstruction.
- The C175 endpoint is about 1.406 m from the C174 start, while the geometric intersection occurs about 1.406 m from the C175 endpoint. This means the topology is a short lateral/branch-like structure rather than a simple coincident endpoint.
- C175 and C174 have exactly the same source invert attributes despite very different lengths (6.114 m vs 36.105 m).

**Decision: RETAIN C175.** The geometry provides evidence for a real branch/crossing, but the source invert metadata remains suspicious. Do not delete it or overwrite its inverts without authoritative manhole/drop evidence.

## 2. C180 / J203-J204 — RETAIN
- GCC ObjectID 5916; C180 length 6.468 m.
- ObjectID 5916 geometrically intersects ObjectID 5918 at the C180 upstream node J203.
- The distance from the ObjectID 5916 endpoint to that intersection is approximately 6.468 m, matching C180's reconstructed length. Therefore C180 is a genuine split piece of ObjectID 5916, **not** a fabricated gap connection.
- J203 is a genuine 3-way geometric junction involving C179/C180/C183.
- J204 is the ObjectID 5916 endpoint and is also connected to C014 (ObjectID 5799), producing the local elevation conflict.
- The reconstructed C180 source/end profile is 3.029125 -> 3.001 m, giving +0.4345% in the candidate.

**Decision: RETAIN C180.** The investigation changes the earlier suspicion: C180 itself is not the problem. The remaining issue is the J203/J204 junction elevation interpretation.

## 3. C166 / J135-J130 — RETAIN / FLAG COMPONENT
- GCC ObjectID 5906; 10.062 m; source invert 2.689 -> 2.643 m.
- Component 27 contains C166 and C168 and has terminal J135; it has no verified outfall.
- Source geometry does not support a missing short connection to the nearby ObjectID 5907: endpoint-to-line distances are about 11.1 m and 21.1 m.
- In the reconstructed candidate, SC020 routes to J138, not J135, so C166 is not receiving the rainfall-runoff subcatchment in the current model.

**Decision: RETAIN C166.** Do not invent a connection or delete it based on instability. Its numerical behaviour should be treated as a property of an incomplete network component, not as evidence of a real-world flood hotspot.

## Final decisions
| Priority | Item | Decision | Confidence |
|---|---|---|---|
| 1 | C175 / J181-J180 | **RETAIN; FLAG source-invert ambiguity** | Medium |
| 2 | C180 / J203-J204 | **RETAIN; investigate junction elevation only** | High |
| 3 | C166 / J135-J130 | **RETAIN; flag incomplete component** | High |

## Final baseline recommendation
No further conduit deletion is justified from these three investigations. Keep the reconstructed candidate's C162/C190 offset reconstruction, C182 removal, C175, C180, and C166. The remaining C175 uncertainty is a source-data/manhole interpretation issue; C180 is a genuine geometric split; C166 is a genuine but incomplete network component.

The reconstructed SWMM run remains numerically usable: routing continuity error 0.068%, minimum timestep 0.50 s, average timestep 2.39 s, and 0.37% non-converging steps. These metrics should not be optimized by arbitrary geometry changes.

EPA SWMM documentation supports representing conduit end offsets above junction inverts and using Dynamic Wave for general networks, backwater, flow reversal and pressurized conditions.
