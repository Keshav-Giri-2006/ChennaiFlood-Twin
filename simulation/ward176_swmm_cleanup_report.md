# Ward 176 SWMM Network Cleanup Report

## Cleanup objective

The first successful EPA SWMM 5.2.4 run completed, but reported minimum-elevation-drop
warnings for C017, C129, C146, C170, C173 and C190. The model also contained obvious
reconstructed self-loop / near-zero-length conduits and an exact duplicate conduit.

This cleanup is intentionally conservative: it removes only geometrically redundant
artefacts that do not provide a meaningful connection between distinct hydraulic nodes.
No inferred missing pipes, invert elevations, flow directions, outfalls, subcatchments,
Manning roughness, rainfall, or conduit dimensions were changed.

## Removed conduits

| Conduit | Reason |
|---|---|
| C017 | Self-loop: J213 -> J213; 1.400 m |
| C129 | Near-zero self-loop: J039 -> J039; 0.012 m |
| C146 | Self-loop: J085 -> J085; 1.263 m |
| C170 | Near-zero self-loop: J173 -> J173; 0.002 m |
| C173 | Self-loop: J173 -> J173; 1.642 m |
| C186 | Exact duplicate of C182 (J225 -> J224; 2.566 m) |

## Intentionally retained

**C190** was retained. It is not a self-loop: it connects J061 -> J057 and is a
25.777 m conduit with a very small reported slope. SWMM's minimum-elevation-drop
warning for C190 should therefore be treated separately rather than deleting a
potentially real drainage segment.

Other short conduits and negative/low slopes were also retained because deleting or
changing them without stronger GIS/hydraulic evidence would amount to inventing the
network.

## Structural verification

- Original links: 189
- Cleaned links: 183
- Removed: 6
- Remaining XSECTIONS: 183
- Dangling conduit XSECTION references: 0
- Removed IDs still present: 0

The cleaned file is intended to be run in EPA SWMM 5.2.4 as the next baseline test.
