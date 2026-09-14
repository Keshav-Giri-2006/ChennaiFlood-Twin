# ChennaiFlood-Twin — Data and GIS Specification

## 1. Purpose

This document defines the **authoritative data and geospatial context** for ChennaiFlood-Twin.

It tells developers:

- what datasets already exist,
- where they are stored,
- what each dataset represents,
- how the datasets relate to one another,
- which coordinate systems are involved,
- which data is raw versus processed,
- what assumptions were made,
- what limitations remain,
- and what must never be fabricated.

Read this document together with:

```text
00_PROJECT_CONTEXT.md
01_PRODUCT_REQUIREMENTS.md
02_ARCHITECTURE.md
```

This document is specifically concerned with **data, GIS, spatial processing, provenance, and geospatial visualization**.

---

# 2. Study Area

## 2.1 Primary Area

The project focuses on:

> **Ward 176, Velachery, Chennai, Tamil Nadu, India**

The pilot area includes the broader Ram Nagar / Tansi Nagar / Velachery context.

The Ward 176 boundary is the primary spatial constraint for the current prototype.

### Important rule

Do not silently expand the study area.

Any expansion must be explicitly justified and documented.

---

# 3. Project Data Flow

The overall geospatial data pipeline is:

```text
AUTHORITATIVE / SOURCE DATA
          ↓
RAW DATA
          ↓
VALIDATION / CLEANING
          ↓
PROCESSING / REPROJECTION / CLIPPING
          ↓
MODEL-READY DATA
          ↓
WEB-READY DATA
          ↓
CESIUMJS DIGITAL TWIN
```

Simulation data follows:

```text
Rainfall + GIS + Drainage
          ↓
SWMM Model
          ↓
Simulation Results
          ↓
Spatial Post-processing
          ↓
Flood / Risk Products
          ↓
CesiumJS
```

---

# 4. Directory Structure

Current project root:

```text
F:\ChennaiFlood-Twin\
```

High-level structure:

```text
ChennaiFlood-Twin/
├── docs/
├── data_raw/
│   └── gcc/
│
├── data_processed/
│
├── gis/
│
├── simulation/
│
├── backend/
│
└── frontend/
```

Recommended logical data organization:

```text
data_raw/
├── gcc/
├── rainfall/
└── dem/

data_processed/
├── gis/
├── network/
└── rainfall/

simulation/
├── *.inp
└── simulation artifacts
```

Do not assume every future directory already exists.

---

# 5. Data Classification

Every dataset should be classified as one of:

## 5.1 Raw source data

Original downloaded/source files.

Examples:

- GCC storm-water drain GeoJSON
- NASA rainfall CSV
- Copernicus DEM

Raw files should be treated as **immutable**.

Never overwrite them during processing.

---

## 5.2 Processed data

Data produced by:

- clipping,
- reprojection,
- topology processing,
- cleaning,
- spatial overlays,
- aggregation,
- or other documented transformations.

Processed data may be regenerated.

---

## 5.3 Model data

Data explicitly prepared for SWMM or another simulation process.

Examples:

- subcatchments,
- reconstructed nodes,
- reconstructed conduits,
- junction elevations,
- rainfall input,
- SWMM `.inp`.

---

## 5.4 Web-ready data

Data optimized for frontend/CesiumJS consumption.

Examples:

- simplified GeoJSON,
- 3D Tiles if later introduced,
- time-indexed flood products,
- risk polygons,
- bottleneck layers.

Web optimization must preserve spatial meaning.

---

# 6. Coordinate Reference Systems

The project uses both geographic and projected coordinate systems.

## 6.1 EPSG:4326

WGS 84 geographic coordinates.

Used by:
- some source datasets,
- web-oriented geographic data,
- certain DEM products.

Coordinates are longitude/latitude in degrees.

Do not use degree distances for engineering distance calculations.

---

## 6.2 EPSG:32644

WGS 84 / UTM Zone 44N.

This is the preferred projected CRS for metric spatial operations in the Ward 176 workflow.

Use it where appropriate for:

- distances,
- areas,
- buffering,
- nearest-neighbour analysis,
- topology thresholds,
- spatial intersections,
- geometry measurements.

---

## 6.3 CRS rule

Every geospatial processing function should know the CRS of its input.

Do not silently assume that two datasets use the same CRS.

Before spatial operations:

```text
Check CRS
   ↓
Transform if necessary
   ↓
Perform operation
```

After transformation, preserve the CRS metadata.

---

# 7. Ward 176 Boundary

The Ward 176 boundary is the primary spatial mask for the project.

It is used to:

- clip the DEM,
- clip/build study-area datasets,
- generate subcatchments,
- constrain visualization,
- perform spatial statistics.

The authoritative boundary source is the GCC administrative boundary data used during project preparation.

The relevant GCC administrative service contains:

- Region Boundary,
- Zone Boundary,
- Ward Boundary.

The service supports GeoJSON output.

### Rule

Do not create a hand-drawn replacement boundary if the official processed Ward 176 boundary is available.

---

# 8. GCC Storm-Water Drain Dataset

## 8.1 Source

The drainage data originates from the **Greater Chennai Corporation GIS** system.

The relevant GCC GIS layer is the storm-water-drain layer.

It is a polyline feature layer containing storm-water-drain infrastructure.

---

## 8.2 Source Dataset Characteristics

The Ward 176 extraction contains:

```text
135 source drain features
```

The features include:

- drain geometry,
- dimensions,
- invert information,
- condition,
- material,
- water-flow information,
- drainage details,
- location,
- start/end coordinate information.

The majority of Ward 176 extracted records are associated with:

> Velachery AGS Colony, Chennai

One record is associated with:

> Puzhuthivakkam, Chennai

---

## 8.3 Important Fields

Important source fields include:

```text
objectid
zone
ward
location
drain_type
cover
drain_len
drain_wid
drain_dep
mh_shape
mh_size
typ_mat
water_flow
puca_kacha
status
swd_mat
drain_detl
invert_sp
invert_ep
inlet_shp
strt_east
strt_north
end_east
end_north
obstacles
dlen_km
shape
st_length(shape)
```

Not every application feature needs to expose all of these.

---

# 9. GCC Drain Data Quality

The source drainage dataset contains known inconsistencies.

Examples include:

- inconsistent invert elevations,
- source features that meet geometrically but disagree in elevation,
- suspicious invert values,
- topology ambiguity,
- fragmented connectivity.

### Major known anomaly

GCC ObjectID:

```text
5793
```

has a suspicious end invert:

```text
20869.0
```

This is clearly anomalous relative to the surrounding Ward 176 elevation scale.

It was therefore excluded from hydraulic modelling as an anomalous invert record while preserving its source geometry for audit purposes.

### Rule

Do not silently "fix" source attributes.

If an anomaly is handled:

1. preserve the source value,
2. document the anomaly,
3. create a processed/model-specific treatment,
4. explain the reason.

---

# 10. Drainage Network Reconstruction

The original 135 source features were processed into a reconstructed network representation.

The reconstruction created:

- reconstructed nodes,
- reconstructed conduit pieces,
- topology relationships,
- node mappings,
- subcatchment mappings,
- provisional outlet information.

The reconstruction was necessary because source drain lines do not always contain explicit manhole/junction objects.

---

# 11. Reconstruction Principles

The network reconstruction followed these principles:

### Preserve source geometry

Do not redraw drainage geometry unnecessarily.

### Split at meaningful intersections

Where source geometry indicated a genuine intersection, split the feature into hydraulic pieces where necessary.

### Avoid invented long connections

Do not connect two drainage features merely because they are nearby.

### Preserve ambiguity

If topology/elevation is uncertain, retain the uncertainty rather than inventing a definitive interpretation.

---

# 12. Network Reconstruction Results

The reconstruction produced approximately:

```text
229 reconstructed nodes
190 reconstructed conduit pieces
```

Before conservative connection resolution, the network remained fragmented.

After conservative resolution:

- one high-confidence node merge was accepted,
- other candidate gap connections were rejected,
- the network remained intentionally fragmented.

The high-confidence accepted merge was:

```text
ObjectID 5807 END
        →
existing junction at
ObjectID 5899 START / 5901 END
```

with an endpoint separation of approximately 2.14 m.

No other long-distance connections were fabricated.

---

# 13. Final Hydraulic Network State

The current SWMM working model contains:

```text
35 subcatchments
228 nodes
182 links
```

C182 was removed as a confirmed duplicate.

The working hydraulic model is:

```text
simulation/
└── ward176_hydraulic_reconstructed_candidate.inp
```

The current model is the baseline for Digital Twin integration.

---

# 14. Important Drainage Links

The following links have been investigated and intentionally retained:

```text
C162
C166
C174
C175
C180
C086
C190
```

### C162

GCC ObjectID 5902.

Real short segment.

Source inverts:

```text
2.192 → 2.072 m
```

It has conflicting source invert references around J122/J124.

Decision:

> Retain; do not fabricate an elevation correction.

---

### C175

GCC ObjectID 5913.

Length approximately:

```text
6.114 m
```

Its source invert attributes exactly duplicate those of C174 despite different geometry.

Possible interpretations include:

- genuine steep/drop connection,
- source attribute duplication,
- geometric crossing.

Decision:

> Retain and flag ambiguity.

Do not invent corrected invert values.

---

### C180

GCC ObjectID 5916 split segment.

Length approximately:

```text
6.468 m
```

It is a legitimate split of source geometry.

Decision:

> Retain.

The remaining issue concerns surrounding junction elevation conflicts rather than the existence of C180 itself.

---

### C166

GCC ObjectID 5906.

Length approximately:

```text
10.062 m
```

It belongs to a disconnected/incomplete component.

Decision:

> Retain.

Do not fabricate a downstream connection.

---

### C190

GCC ObjectID 5923.

Length approximately:

```text
25.777 m
```

Source inverts:

```text
3.845 → 3.419 m
```

The hydraulic reconstruction uses conduit offsets to represent the source/reconstructed pipe-end elevations.

Decision:

> Retain.

---

# 15. Provisional Outlets

Network analysis identified seven provisional downstream boundary terminals:

```text
node125
node98
node140
node94
node88
node97
node213
```

These are:

> **provisional downstream boundary terminals, not confirmed physical outfalls.**

They should not be labelled as confirmed municipal outfalls in the UI.

---

# 16. Subcatchments

A first-pass subcatchment dataset exists:

```text
data_processed/gis/ward176_subcatchments.geojson
```

and an associated CSV exists under:

```text
data_processed/network/
```

Current characteristics:

```text
35 subcatchments
```

They were generated by spatial partitioning and clipped to Ward 176.

Attributes include:

- area,
- imperviousness,
- DEM statistics,
- slope proxy,
- width,
- roughness assumptions,
- storage assumptions,
- infiltration assumptions.

---

# 17. Subcatchment Interpretation

The current subcatchments are **model constructs**, not official hydrological catchment boundaries.

Imperviousness was estimated using building and road overlays.

The model currently uses assumptions including:

```text
Impervious Manning n ≈ 0.013
Pervious Manning n ≈ 0.24
Impervious depression storage ≈ 1.5 mm
Pervious depression storage ≈ 5 mm
```

Green-Ampt infiltration assumptions are also used by the SWMM model.

These are modelling assumptions and must not be described as field-measured parameters.

---

# 18. Buildings Dataset

The Ward 176 building dataset contains approximately:

```text
6,428 features
```

Approximate total footprint:

```text
~991,968 m²
```

The building polygons are used for:

- Digital Twin visualization,
- exposure analysis,
- flood impact identification,
- contextual mapping.

---

# 19. Building Height Rule

Reliable measured building heights are not currently established as part of the core project dataset.

Therefore:

> Do not present an arbitrary extrusion height as surveyed building height.

If buildings are extruded for 3D visualization, clearly treat the extrusion as a visualization representation unless authoritative height data is introduced.

---

# 20. Roads / Carriageways Dataset

Ward 176 carriageway data contains approximately:

```text
301 polygon features
```

Approximate total area:

```text
~267,919 m²
```

Roads are used for:

- 3D context,
- flood exposure,
- spatial interpretation,
- visualization.

The road dataset is not a complete traffic network.

Do not infer traffic-flow data from geometry alone.

---

# 21. DEM / Terrain

## 21.1 Source

The terrain dataset is:

> **Copernicus DEM GLO-30**

The downloaded source tile is:

```text
Copernicus_DSM_10_N12_00_E080_00_DEM.tif
```

It is a Float32 GeoTIFF.

Source CRS:

```text
EPSG:4326
```

Source resolution is approximately:

```text
30 m
```

---

# 22. DEM Characteristics

The original tile covers a much larger region than Ward 176.

The Ward 176 clipped DEM is:

```text
data_processed/gis/ward176_dem.tif
```

The clipped raster has approximately:

```text
50 × 69 pixels
```

The valid Ward 176 elevation statistics are approximately:

```text
Minimum: ~1.705 m
Maximum: ~14.42 m
Mean:    ~7.97 m
Median:  ~8.10 m
```

These statistics describe the processed raster and should not be interpreted as a high-resolution survey.

---

# 23. DEM Limitation

Copernicus GLO-30 is DSM-derived.

It may contain elevation contributions from:

- buildings,
- vegetation,
- and other above-ground objects.

Therefore:

> Do not describe the DEM as a perfect bare-earth terrain survey.

This matters when interpreting flood-depth results.

---

# 24. DEM Masking Rule

The clipped DEM contains a spatial mask.

Outside the Ward 176 valid area, zeros may be present as mask values.

Do not treat those zeros as real elevations.

For calculations:

```text
mask outside-study-area values
```

rather than assigning arbitrary elevations.

---

# 25. Rainfall Dataset

## 25.1 Primary Event

The initial rainfall scenario is:

> **Michaung 2023**

Event period:

```text
December 2–5, 2023
```

Source:

> NASA GPM IMERG Final Run

Variable:

```text
GPM_3IMERGHH v07
```

---

# 26. Rainfall Data Characteristics

The processed rainfall dataset contains:

```text
192 temporal records
```

after metadata handling.

Temporal resolution:

```text
30 minutes
```

Approximate event total:

```text
282.835 mm
```

Approximate maximum interval intensity:

```text
23.35 mm/hr
```

Approximate daily totals:

```text
Dec 2:  13.51 mm
Dec 3: 114.78 mm
Dec 4: 152.36 mm
Dec 5:   2.185 mm
```

---

# 27. Rainfall File Locations

Raw rainfall file:

```text
data_raw/rainfall/michaung_2023/imerg_michaung_2023_raw.csv
```

Processed rainfall file:

```text
data_processed/imerg_michaung_2023_processed.csv
```

Exact filenames should be verified before code assumes a path.

---

# 28. Rainfall Spatial Limitation

The downloaded GPM rainfall data effectively represents a very coarse spatial rainfall field for this prototype.

The selected region resulted in effectively one 0.1° grid cell relevant to the study area.

Therefore:

> Do not describe the rainfall dataset as dense station-level rainfall observations across Ward 176.

The temporal series is useful for the historical scenario, but its spatial resolution is limited.

---

# 29. Rainfall Data Usage

The rainfall data should be treated as:

```text
Historical scenario input
```

not as a live rainfall monitoring feed.

Future synthetic or forecast scenarios can be added through the scenario architecture.

---

# 30. Flood Result Spatial Data

The SWMM model primarily produces hydraulic/network results.

The Digital Twin requires an additional spatial processing stage:

```text
SWMM results
     ↓
spatial processing
     ↓
flood-depth / flood-extent representation
     ↓
web-ready spatial product
```

The exact methodology used to derive spatial flood depth must be documented.

---

# 31. Flood Depth Scientific Rule

Do not claim:

> "SWMM directly generated a complete 2D/3D flood surface."

Instead describe the workflow as:

> **SWMM hydraulic simulation followed by flood-depth/flood-extent spatial post-processing and 3D geospatial visualization.**

This distinction is important for academic accuracy.

---

# 32. Digital Twin Spatial Layers

The initial CesiumJS scene should use:

```text
1. Terrain
2. Ward boundary
3. Buildings
4. Roads
5. Storm-water drains
6. Flood extent
7. Flood depth
8. Risk areas
9. Bottleneck highlights
```

Layers 1–5 are predominantly static.

Layers 6–9 are simulation-dependent.

---

# 33. Static vs Dynamic Geospatial Data

## Static

```text
Terrain
Buildings
Roads
Ward boundary
Base drainage network
Subcatchments
```

These can be cached and reused between simulations.

## Dynamic

```text
Flood extent
Flood depth
Hydraulic state
Risk
Bottlenecks
Simulation KPIs
```

These are associated with a scenario/simulation ID.

---

# 34. Web GIS Data Strategy

The frontend should not necessarily consume the exact same files used for modelling.

The preferred pipeline is:

```text
Model/source dataset
       ↓
Processing
       ↓
Web optimization
       ↓
Frontend asset
```

For example:

```text
Large source GeoJSON
       ↓
simplification / tiling / optimization
       ↓
Cesium-friendly asset
```

The source dataset must remain preserved.

---

# 35. Cesium Performance Considerations

The building layer contains thousands of features.

Therefore:

- avoid unnecessary duplication,
- avoid repeatedly parsing large GeoJSON files,
- cache static assets,
- consider tiling/3D Tiles if required,
- simplify geometry only when visually safe,
- avoid excessive per-feature JavaScript work,
- load large layers progressively where appropriate.

Do not sacrifice spatial correctness merely to improve frame rate.

---

# 36. Spatial Alignment Requirements

All major layers must align spatially.

At minimum:

```text
Ward boundary
     ↕
Buildings
     ↕
Roads
     ↕
Drains
     ↕
Terrain
     ↕
Flood result
```

If a layer appears offset:

1. check CRS,
2. check coordinate order,
3. check transformation,
4. check units,
5. check source extent.

Do not manually shift geometry to "make it look right" without documenting the reason.

---

# 37. Spatial Processing Rules

For any GIS operation:

1. Validate geometry.
2. Validate CRS.
3. Reproject where necessary.
4. Perform the operation.
5. Validate the output.
6. Preserve metadata.
7. Save to a processed location.
8. Document assumptions.

Examples:

```text
intersection
buffer
nearest feature
distance
area
clip
raster sampling
```

must use an appropriate projected CRS when metric calculations are involved.

---

# 38. Topology Rules

Drainage topology is particularly sensitive.

Do not:

- connect nearby endpoints automatically without evidence,
- infer flow direction solely from visual appearance,
- treat every geometric crossing as a hydraulic junction,
- delete a conduit solely because it creates numerical instability,
- create an outlet solely because a component is inconvenient.

A topology change must have a defensible basis.

---

# 39. Flow Direction

The drainage reconstruction contains a provisional flow direction based on available source geometry/invert evidence.

Most source features have a START_TO_END interpretation.

However, direction should not be treated as absolute physical truth when source elevations/topology are contradictory.

The hydraulic model is the authoritative representation for the current simulation run.

---

# 40. Data Quality Flags

Known data issues should be represented explicitly.

Examples:

```text
SUSPICIOUS_INVERT
ELEVATION_CONFLICT
DISCONNECTED_COMPONENT
PROVISIONAL_OUTLET
SOURCE_ATTRIBUTE_AMBIGUITY
```

Do not delete problematic records merely to make the dataset appear clean.

A data-quality flag is preferable to silent correction.

---

# 41. Provenance Metadata

Where practical, processed files should have metadata containing:

```text
source
source_version/date
processing_date
processing_method
CRS
study_area
model_version
notes
```

For example:

```json
{
  "source": "GCC",
  "studyArea": "Ward 176",
  "crs": "EPSG:32644",
  "processing": "network reconstruction",
  "notes": "Conservative topology; no fabricated long connections"
}
```

Exact metadata format may evolve.

---

# 42. Data Immutability Rule

Never modify:

```text
data_raw/
```

in-place.

If cleaning is necessary:

```text
data_raw/
     ↓
data_processed/
```

If a source dataset needs a different representation:

```text
source
  ↓
derived version
```

not:

```text
source
  ↓
overwrite source
```

---

# 43. Simulation Result Provenance

Every result should be associated with:

```text
simulation ID
scenario ID
model version
processing version
timestamp
```

Example:

```json
{
  "simulationId": "sim-001",
  "scenarioId": "michaung-2023",
  "modelVersion": "ward176-hydraulic-reconstructed-v1",
  "processingVersion": "flood-processing-v1"
}
```

This prevents confusion when multiple versions of the model exist.

---

# 44. Important Model Output Caveat

The current model produces a substantial SWMM flooding-loss volume.

This should **not** be interpreted as measured real-world flood volume.

Reasons include:

- incomplete drainage connectivity,
- provisional outlets,
- fragmented network components,
- uncertain source invert attributes,
- simplified modelling assumptions.

Therefore, all application labels should use language such as:

> Simulated flooding

or:

> Model-derived flood response

rather than:

> Observed flood volume

unless independently validated.

---

# 45. Asset Exposure Analysis

The spatial layers allow future intersections such as:

```text
Flood polygon
      ×
Building polygon
```

and:

```text
Flood polygon
      ×
Road polygon
```

These can produce:

- affected building count,
- affected building area,
- affected road area,
- affected road length where geometry supports it.

These are derived metrics.

They must be clearly associated with the simulation scenario and flood-processing method.

---

# 46. Risk Data

Risk products may combine:

```text
Flood depth
+
Flood duration
+
Asset exposure
+
Drainage stress
```

The exact scoring methodology must be defined in the risk/service documentation.

Do not put unexplained risk formulas into GIS processing code.

---

# 47. Bottleneck Data

Potential drainage bottlenecks should be generated from hydraulic evidence.

Potential inputs include:

- flow,
- capacity,
- surcharge,
- flooding relationships,
- repeated hydraulic stress.

The output should be described as:

> Potential drainage bottleneck

unless independently verified.

---

# 48. File Naming Principles

Use descriptive names.

Preferred examples:

```text
ward176_dem.tif
ward176_buildings.geojson
ward176_carriageways.geojson
ward176_subcatchments.geojson
ward176_reconstructed_conduits.geojson
ward176_reconstructed_nodes.csv
```

For scenario outputs:

```text
<simulation_id>_<product>.<extension>
```

Example:

```text
sim-001_flood_extent.geojson
sim-001_flood_depth.geojson
sim-001_kpis.json
```

---

# 49. Data Validation Checklist

Before using a geospatial dataset in the application:

### Geometry

- valid geometry,
- expected feature count,
- no unexpected null geometry.

### CRS

- known CRS,
- correct transformation.

### Extent

- overlaps Ward 176 where expected,
- no unexplained displacement.

### Attributes

- required fields exist,
- numeric values are plausible,
- units are known.

### Provenance

- source is recorded,
- processing step is documented.

---

# 50. Current Data Baseline

The Digital Twin implementation should initially rely on:

```text
Ward 176 boundary
       +
Copernicus DEM
       +
GCC buildings
       +
GCC carriageways
       +
GCC storm-water drains
       +
Ward 176 subcatchments
       +
Reconstructed drainage network
       +
Michaung 2023 rainfall
       +
SWMM hydraulic model
```

Do not add external datasets unless they provide a clear benefit.

---

# 51. External Data Addition Rule

If new external data is introduced:

1. Identify the source.
2. Confirm licensing/access.
3. Record date/version.
4. Record CRS.
5. Record spatial resolution.
6. Record limitations.
7. Save raw data separately.
8. Create processed data separately.
9. Update this document.

Do not silently introduce external data into the product.

---

# 52. Recommended Web Data Hierarchy

The frontend should eventually consume:

```text
/base/
    ward_boundary
    buildings
    roads
    drains
    terrain

/simulations/<id>/
    metadata
    flood
    depth
    risk
    bottlenecks
    kpis
    timeline
```

The exact API/storage paths are defined later by the API contract.

This is a conceptual organization, not a requirement to use these literal URLs.

---

# 53. GIS Architecture Principle

The application should maintain a clean distinction between:

```text
SOURCE GIS
      ↓
MODEL GIS
      ↓
WEB GIS
```

Source GIS preserves reality as supplied by the source.

Model GIS represents the assumptions needed for simulation.

Web GIS represents optimized visualization assets.

These layers must not be confused.

---

# 54. Final Data Rules

The following rules are mandatory:

1. Never overwrite raw source data.
2. Never fabricate drainage connections.
3. Never fabricate missing outfalls.
4. Never silently modify invert elevations.
5. Never silently shift spatial geometry.
6. Always know the CRS.
7. Use projected CRS for metric operations.
8. Preserve data provenance.
9. Keep model assumptions separate from observations.
10. Keep web optimization separate from source data.
11. Flag uncertainty instead of hiding it.
12. Validate geometry before visualization.
13. Validate spatial alignment before analysis.
14. Do not treat model output as field measurement.
15. Do not treat provisional outlets as confirmed physical outfalls.
16. Do not treat generated subcatchments as official hydrological boundaries.
17. Do not describe the Copernicus DEM as perfect bare-earth survey data.
18. Do not describe the GPM rainfall input as a dense local gauge network.
19. Keep the current Ward 176 scope unless expansion is explicitly justified.
20. Preserve reproducibility of all derived products.

---

# 55. Data Layer Success Criteria

The data/GIS layer is considered ready for Digital Twin integration when:

1. Ward 176 is correctly defined.
2. Terrain aligns with the study area.
3. Buildings align with terrain.
4. Roads align with buildings.
5. Drainage aligns with the urban environment.
6. Subcatchments are available for model context.
7. Static layers can be loaded efficiently by the frontend.
8. Simulation-dependent spatial products can be associated with a simulation ID.
9. CRS transformations are explicit.
10. Data provenance and limitations remain traceable.

---

# 56. Final Principle

The data architecture must preserve this chain:

```text
AUTHORITATIVE SOURCE
        ↓
RAW DATA
        ↓
VALIDATED / PROCESSED DATA
        ↓
MODEL INPUT
        ↓
SIMULATION OUTPUT
        ↓
DERIVED SPATIAL PRODUCT
        ↓
DIGITAL TWIN
```

The goal is not to make the data look perfect.

The goal is to make it:

> **traceable, spatially consistent, reproducible, scientifically defensible, and useful for the Smart City Digital Twin.**
