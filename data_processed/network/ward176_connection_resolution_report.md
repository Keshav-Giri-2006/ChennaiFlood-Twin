# Ward 176 Storm-Water Network Connection Resolution

## Decision
A conservative connection-resolution pass was performed on the reconstructed GCC storm-water network.

### Accepted connection
- **5807 END → existing junction at 5899 START / 5901 END**
- Endpoint gap: **2.144 m**
- Action: **merge reconstructed node 123 into node 121**
- Rationale: the 5807 endpoint lies only 2.14 m from an existing reconstructed junction formed by the 5899 START and 5901 END endpoints. This is the strongest short-gap candidate and can be represented as a node merge without inventing a new hydraulic conduit.

The nearby 5807 END → 5901 END candidate (2.856 m) is treated as the same physical merge target, not as a second connection.

## Rejected candidates
All other short-gap candidates were rejected conservatively when endpoint roles, invert continuity, topology, or gap length did not provide enough evidence for a defensible synthetic connection. In particular, no large invert discontinuity was silently corrected.

## Anomalous conduit
Original GCC ObjectID **5793** retains its original anomalous invert value for provenance but is marked **hydraulically unusable/excluded from baseline calculations** until the source value is verified. No replacement elevation is fabricated.

## Result
The accepted merge reduces the number of disconnected active network components by one relative to the pre-resolution active network. The remaining disconnected components are retained because connecting them without stronger evidence would fabricate drainage topology.

## Files
- ward176_resolved_nodes.csv
- ward176_resolved_conduits.csv
- ward176_connection_resolution.csv
- ward176_rejected_gap_connections.csv
- ward176_resolved_outlets.csv
- ward176_subcatchment_resolved_mapping.csv

This is a conservative reconstruction suitable as the input network for the next SWMM modelling phase, subject to SWMM structural validation.
