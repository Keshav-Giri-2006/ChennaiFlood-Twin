# ChennaiFlood-Twin — API Contract

## 1. Purpose

This document defines the **formal API contract between the ChennaiFlood-Twin frontend and backend**.

It should be treated as the shared interface specification for implementation.

Read this together with:

```text
00_PROJECT_CONTEXT.md
01_PRODUCT_REQUIREMENTS.md
02_ARCHITECTURE.md
03_DATA_AND_GIS.md
04_SWMM_MODEL.md
05_BACKEND_DESIGN.md
```

The purpose of this document is to prevent the frontend and backend from independently inventing incompatible:

- endpoint names,
- request formats,
- response structures,
- identifiers,
- status values,
- units,
- timestamps,
- error formats,
- and spatial data representations.

---

# 2. API Design Principles

The API must be:

- predictable,
- versioned,
- explicit,
- JSON-first,
- typed,
- documented,
- stable enough for frontend development,
- and easy to test.

The API should expose **application-level information**, not force the frontend to understand SWMM internals.

---

# 3. Base URL

Development:

```text
http://localhost:<BACKEND_PORT>/api/v1
```

Production:

```text
https://<API_DOMAIN>/api/v1
```

The exact host/port is environment configuration.

The `/api/v1` prefix is the initial API version.

---

# 4. API Versioning

Initial version:

```text
v1
```

All public application endpoints should use:

```text
/api/v1/...
```

Breaking changes should result in a new API version rather than silently changing the existing contract.

---

# 5. Content Types

Requests and responses should primarily use:

```text
application/json
```

Spatial responses may use:

```text
application/geo+json
```

where appropriate.

Large downloadable files should not be embedded unnecessarily inside JSON.

---

# 6. Common Identifier Rules

Use stable identifiers.

### Scenario

```text
scenarioId
```

Example:

```text
michaung-2023
```

### Simulation

```text
simulationId
```

Prefer UUIDs in production.

Example:

```text
7f8d3f2a-...
```

### Model

```text
modelVersion
```

Example:

```text
ward176-hydraulic-reconstructed-v1
```

### Processing

```text
processingVersion
```

Example:

```text
flood-processing-v1
```

---

# 7. Timestamp Rules

Use ISO 8601 timestamps.

Example:

```text
2023-12-03T21:30:00Z
```

or an explicitly offset timestamp.

Do not send ambiguous timestamps such as:

```text
12/03/2023 21:30
```

The backend should standardize timestamps before returning them.

For the Michaung historical event, source timestamps should remain traceable to the rainfall data's time basis.

---

# 8. Units

API responses must include explicit units where values could be ambiguous.

Examples:

```json
{
  "value": 282.835,
  "unit": "mm"
}
```

For rates:

```text
mm/hr
```

For distance:

```text
m
```

For area:

```text
m2
```

For volume:

```text
L
```

For hydraulic flow:

```text
m3/s
```

Do not make the frontend infer units from variable names alone.

---

# 9. Standard Error Format

All API errors should follow a common structure.

Example:

```json
{
  "error": {
    "code": "SCENARIO_NOT_FOUND",
    "message": "The requested rainfall scenario does not exist.",
    "requestId": "req-123",
    "details": null
  }
}
```

Optional fields:

```text
simulationId
field
details
requestId
```

Do not expose:

- stack traces,
- local filesystem paths,
- credentials,
- internal secrets.

---

# 10. Recommended HTTP Status Codes

Use standard HTTP semantics.

```text
200 OK
201 Created
202 Accepted
204 No Content
400 Bad Request
404 Not Found
409 Conflict
422 Unprocessable Entity
500 Internal Server Error
502 Bad Gateway
503 Service Unavailable
504 Gateway Timeout
```

The exact status should match the failure type.

---

# 11. Health Endpoint

## `GET /health`

Purpose:

Check whether the backend is alive.

Example response:

```json
{
  "status": "ok",
  "service": "chennaiflood-twin-api",
  "version": "1.0.0"
}
```

This should be lightweight.

---

# 12. Readiness Endpoint

## `GET /health/ready`

Purpose:

Check whether the backend can perform its required work.

Potential checks:

- configuration,
- SWMM executable,
- required project data,
- result storage.

Example:

```json
{
  "status": "ready",
  "checks": {
    "swmm": "ok",
    "data": "ok",
    "storage": "ok"
  }
}
```

Do not make this endpoint run a full simulation.

---

# 13. Scenario API

The scenario API provides available rainfall scenarios.

---

# 14. List Scenarios

## `GET /scenarios`

Returns scenarios available to the application.

Example response:

```json
{
  "scenarios": [
    {
      "scenarioId": "michaung-2023",
      "name": "Michaung 2023",
      "description": "Historical rainfall scenario for the December 2023 Michaung event.",
      "source": "NASA GPM IMERG Final Run",
      "rainfallType": "historical",
      "startTime": "2023-12-02T00:00:00Z",
      "endTime": "2023-12-05T23:30:00Z",
      "intervalMinutes": 30,
      "totalRainfallMm": 282.835,
      "peakIntensityMmHr": 23.35
    }
  ]
}
```

Exact event start/end timestamps should come from the processed rainfall data.

Do not fabricate metadata.

---

# 15. Get Scenario

## `GET /scenarios/{scenarioId}`

Example:

```text
GET /api/v1/scenarios/michaung-2023
```

Example response:

```json
{
  "scenarioId": "michaung-2023",
  "name": "Michaung 2023",
  "description": "Historical rainfall scenario.",
  "source": {
    "name": "NASA GPM IMERG Final Run",
    "variable": "GPM_3IMERGHH v07"
  },
  "rainfall": {
    "type": "intensity",
    "intervalMinutes": 30,
    "totalMm": 282.835,
    "peakMmHr": 23.35
  }
}
```

---

# 16. Scenario Validation

Before creating a simulation, the backend must verify:

```text
scenario exists
rainfall input exists
model exists
required data exists
```

If not, return a structured error.

---

# 17. Simulation API

The simulation API manages:

- simulation creation,
- status,
- summary,
- results.

---

# 18. Create Simulation

## `POST /simulations`

Purpose:

Create and start a simulation request.

Request:

```json
{
  "scenarioId": "michaung-2023",
  "modelVersion": "ward176-hydraulic-reconstructed-v1"
}
```

Optional future scenario configuration:

```json
{
  "scenarioId": "michaung-2023",
  "modelVersion": "ward176-hydraulic-reconstructed-v1",
  "parameters": {
    "rainfallMultiplier": 1.2
  }
}
```

The initial MVP should keep optional parameters minimal.

Do not expose arbitrary SWMM configuration through the API.

---

# 19. Create Simulation Response

Recommended status:

```text
202 Accepted
```

Example:

```json
{
  "simulationId": "7f8d3f2a-...",
  "scenarioId": "michaung-2023",
  "modelVersion": "ward176-hydraulic-reconstructed-v1",
  "status": "CREATED",
  "createdAt": "2026-09-13T14:00:00Z"
}
```

The simulation may move to `VALIDATING` or `RUNNING` immediately after creation.

---

# 20. Simulation State Values

The frontend must support these states:

```text
CREATED
VALIDATING
PREPARING
RUNNING
PROCESSING
COMPLETED
FAILED
```

Do not invent alternate spellings such as:

```text
running_simulation
done
finished
```

without updating this contract.

---

# 21. Get Simulation Status

## `GET /simulations/{simulationId}`

Example response:

```json
{
  "simulationId": "7f8d3f2a-...",
  "scenarioId": "michaung-2023",
  "modelVersion": "ward176-hydraulic-reconstructed-v1",
  "processingVersion": "flood-processing-v1",
  "status": "RUNNING",
  "stage": "SWMM_EXECUTION",
  "progress": 62,
  "createdAt": "2026-09-13T14:00:00Z",
  "startedAt": "2026-09-13T14:00:08Z",
  "completedAt": null,
  "error": null
}
```

---

# 22. Progress Semantics

`progress` is an approximate application progress indicator.

It should be:

```text
0–100
```

It must not be presented as exact physical simulation-time completion unless that is actually known.

If precise progress cannot be calculated, use stage-based progress.

Example:

```text
VALIDATING  → 10
PREPARING   → 20
RUNNING     → 20–70
PROCESSING  → 70–95
COMPLETED   → 100
```

These percentages are implementation guidance, not scientific measurements.

---

# 23. Simulation Failure Response

Example:

```json
{
  "simulationId": "7f8d3f2a-...",
  "status": "FAILED",
  "stage": "SWMM_EXECUTION",
  "error": {
    "code": "SIMULATION_FAILED",
    "message": "SWMM execution failed."
  }
}
```

Do not expose raw command lines or server filesystem paths.

---

# 24. Cancel Simulation

Cancellation is optional for the first MVP.

If implemented:

## `POST /simulations/{simulationId}/cancel`

The backend must safely terminate the associated process.

Do not implement a fake cancellation that only changes the frontend state.

---

# 25. Simulation Summary

## `GET /simulations/{simulationId}/summary`

Purpose:

Return the dashboard-level summary after simulation completion.

Example:

```json
{
  "simulationId": "7f8d3f2a-...",
  "scenario": {
    "scenarioId": "michaung-2023",
    "name": "Michaung 2023"
  },
  "model": {
    "version": "ward176-hydraulic-reconstructed-v1"
  },
  "status": "COMPLETED",
  "rainfall": {
    "totalMm": 282.835,
    "peakMmHr": 23.35
  },
  "flood": {
    "maximumDepthM": 1.42,
    "affectedAreaM2": 125000
  },
  "drainage": {
    "potentialBottlenecks": 8,
    "floodedNodes": 23
  }
}
```

Values above such as `1.42`, `125000`, `8`, and `23` are examples only.

Never hardcode these values.

---

# 26. KPI API

## `GET /simulations/{simulationId}/kpis`

Purpose:

Return structured KPI information.

Recommended response:

```json
{
  "simulationId": "7f8d3f2a-...",
  "rainfall": {
    "total": {
      "value": 282.835,
      "unit": "mm"
    },
    "peakIntensity": {
      "value": 23.35,
      "unit": "mm/hr"
    }
  },
  "flood": {
    "maximumDepth": {
      "value": 1.42,
      "unit": "m"
    },
    "affectedArea": {
      "value": 125000,
      "unit": "m2"
    }
  }
}
```

The exact KPI list can evolve.

---

# 27. KPI Provenance

Where appropriate, KPIs should include:

```json
{
  "value": 1.42,
  "unit": "m",
  "source": "model-derived",
  "methodVersion": "flood-processing-v1"
}
```

Possible source labels:

```text
source
model-derived
derived
estimated
```

Use labels consistently.

---

# 28. Flood API

The flood API provides simulation-dependent spatial flood information.

---

# 29. Flood Summary

## `GET /simulations/{simulationId}/flood`

Returns a flood overview.

Example:

```json
{
  "simulationId": "7f8d3f2a-...",
  "available": true,
  "maximumDepthM": 1.42,
  "peakTime": "2023-12-04T08:00:00Z",
  "extentAvailable": true,
  "depthAvailable": true
}
```

Values are examples only.

---

# 30. Flood Extent

## `GET /simulations/{simulationId}/flood/extent`

Recommended response:

```text
application/geo+json
```

Example:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": []
      },
      "properties": {
        "time": "2023-12-04T08:00:00Z",
        "scenarioId": "michaung-2023"
      }
    }
  ]
}
```

The actual geometry must come from the flood-processing pipeline.

Do not generate fake polygons simply to satisfy the endpoint.

---

# 31. Flood Depth

## `GET /simulations/{simulationId}/flood/depth`

The exact representation depends on the chosen flood-depth processing method.

Possible response:

```text
application/geo+json
```

or a web-optimized raster/vector product.

If GeoJSON is used, each feature may include:

```json
{
  "depthM": 0.75,
  "time": "2023-12-04T08:00:00Z"
}
```

The API should not force a format that becomes inefficient for large raster-like datasets.

---

# 32. Flood Timeline

## `GET /simulations/{simulationId}/flood/timeline`

Purpose:

Return available timestamps for the frontend timeline.

Example:

```json
{
  "simulationId": "7f8d3f2a-...",
  "intervalMinutes": 30,
  "timestamps": [
    "2023-12-02T00:00:00Z",
    "2023-12-02T00:30:00Z",
    "2023-12-02T01:00:00Z"
  ]
}
```

The frontend should use this list to drive the timeline.

---

# 33. Flood Time Slice

## `GET /simulations/{simulationId}/flood/timeslice?time=<ISO_TIMESTAMP>`

Purpose:

Return the spatial flood state for one timestamp.

Example response:

```json
{
  "simulationId": "7f8d3f2a-...",
  "time": "2023-12-04T08:00:00Z",
  "flood": {
    "maximumDepthM": 1.42,
    "extent": {
      "type": "FeatureCollection",
      "features": []
    }
  }
}
```

The exact geometry representation may instead be delivered through a dedicated spatial asset URL.

---

# 34. Spatial Asset References

For large products, JSON should be able to return references instead of embedding all geometry.

Example:

```json
{
  "time": "2023-12-04T08:00:00Z",
  "asset": {
    "type": "geojson",
    "url": "/api/v1/simulations/7f8d.../flood/timeslices/2023-12-04T08-00-00Z"
  }
}
```

In production, the URL may point to signed object storage.

The frontend should treat asset URLs as opaque.

Do not construct S3 keys manually in frontend code.

---

# 35. Static GIS API

Static GIS can be served through the API or directly from object storage.

If API-served, conceptual endpoints include:

```text
GET /gis/ward
GET /gis/buildings
GET /gis/roads
GET /gis/drains
GET /gis/subcatchments
```

The final implementation can choose direct static asset hosting when more efficient.

---

# 36. Ward Boundary

## `GET /gis/ward`

Returns the Ward 176 boundary.

Recommended:

```text
application/geo+json
```

Properties may include:

```text
ward
zone
name
```

Do not add unsupported administrative information.

---

# 37. Buildings

## `GET /gis/buildings`

Returns web-ready Ward 176 building geometry.

Potential query parameters:

```text
bbox
limit
```

if needed.

The frontend should not request the raw source dataset unnecessarily.

---

# 38. Roads

## `GET /gis/roads`

Returns web-ready Ward 176 carriageway geometry.

Potential filters can be added later.

---

# 39. Drains

## `GET /gis/drains`

Returns the web-ready drainage network.

Each feature may expose selected attributes such as:

```json
{
  "objectId": 5902,
  "lengthM": 3.026,
  "widthM": 0.9,
  "depthM": 0.9,
  "status": "Good"
}
```

The exact values come from processed project data.

---

# 40. Drain Detail

## `GET /gis/drains/{objectId}`

Returns details for one source drain feature.

Potential response:

```json
{
  "objectId": 5902,
  "ward": "176",
  "zone": "N13",
  "drainType": "SWD",
  "lengthM": 3.026,
  "widthM": 0.9,
  "depthM": 0.9,
  "status": "Good",
  "dataQuality": []
}
```

Only expose attributes actually available.

---

# 41. Asset Exposure API

Optional endpoint:

## `GET /simulations/{simulationId}/exposure`

Purpose:

Return simulation-derived asset exposure.

Potential response:

```json
{
  "simulationId": "7f8d3f2a-...",
  "buildings": {
    "affectedCount": 123
  },
  "roads": {
    "affectedAreaM2": 45000
  }
}
```

These are derived values and must not be presented as observed damage.

---

# 42. Risk API

## `GET /simulations/{simulationId}/risk`

Purpose:

Return model-derived risk information.

Example:

```json
{
  "simulationId": "7f8d3f2a-...",
  "methodVersion": "risk-processing-v1",
  "locations": [
    {
      "locationId": "risk-001",
      "riskLevel": "HIGH",
      "score": 0.82,
      "drivers": [
        "high simulated depth",
        "asset exposure"
      ]
    }
  ]
}
```

The exact scoring system must be documented separately.

---

# 43. Risk Spatial Product

## `GET /simulations/{simulationId}/risk/geojson`

Recommended response:

```text
application/geo+json
```

Example properties:

```json
{
  "riskLevel": "HIGH",
  "score": 0.82,
  "time": "2023-12-04T08:00:00Z"
}
```

Risk geometry is model-derived.

---

# 44. Bottleneck API

## `GET /simulations/{simulationId}/bottlenecks`

Example:

```json
{
  "simulationId": "7f8d3f2a-...",
  "bottlenecks": [
    {
      "linkId": "C162",
      "sourceObjectId": 5902,
      "severity": "HIGH",
      "reason": "High hydraulic stress",
      "evidence": {
        "metric": "capacityUtilization",
        "value": 0.91
      }
    }
  ]
}
```

Example values are illustrative only.

---

# 45. Bottleneck Terminology

The API should use:

```text
potential bottleneck
```

or equivalent model-derived terminology.

Do not expose:

```text
confirmed failure
```

unless external evidence supports that claim.

---

# 46. Bottleneck Spatial API

Optional:

## `GET /simulations/{simulationId}/bottlenecks/geojson`

Recommended:

```text
application/geo+json
```

Properties should contain enough information for visualization and inspection.

---

# 47. Recommendation API

## `GET /simulations/{simulationId}/recommendations`

Example:

```json
{
  "simulationId": "7f8d3f2a-...",
  "recommendations": [
    {
      "id": "rec-001",
      "priority": "HIGH",
      "category": "DRAINAGE",
      "title": "Investigate high-stress drainage segment",
      "description": "Review the identified potential bottleneck for further hydraulic and field assessment.",
      "drivers": [
        "high simulated hydraulic stress"
      ]
    }
  ]
}
```

Recommendations must be based on available evidence.

---

# 48. Recommendation Disclaimer

Recommendations are:

> **decision-support suggestions derived from model results.**

They are not:

- engineering orders,
- municipal directives,
- emergency instructions,
- or field-confirmed infrastructure diagnoses.

---

# 49. Asset Inspection API

Optional general endpoint:

## `GET /assets/{assetType}/{assetId}`

Possible asset types:

```text
building
drain
road
```

However, specialized endpoints may be clearer.

Do not create a generic endpoint merely to reduce the number of route files if it makes the contract ambiguous.

---

# 50. Simulation Results Overview

## `GET /simulations/{simulationId}/results`

Purpose:

Return links/metadata for all available result products.

Example:

```json
{
  "simulationId": "7f8d3f2a-...",
  "status": "COMPLETED",
  "products": {
    "summary": true,
    "kpis": true,
    "flood": true,
    "timeline": true,
    "risk": true,
    "bottlenecks": true,
    "recommendations": true
  }
}
```

This can serve as a convenient frontend discovery endpoint.

---

# 51. Scenario Comparison API

Scenario comparison can be implemented after the core MVP.

## `POST /comparisons`

Request:

```json
{
  "simulationIds": [
    "simulation-a",
    "simulation-b"
  ]
}
```

Response:

```json
{
  "comparisonId": "comparison-001",
  "simulations": [
    "simulation-a",
    "simulation-b"
  ],
  "metrics": {
    "maximumDepthM": {
      "simulation-a": 0.8,
      "simulation-b": 1.2
    }
  }
}
```

Values are examples only.

---

# 52. Comparison Rule

Do not compare simulations generated from incompatible:

- model versions,
- processing versions,
- study areas,
- or data assumptions

without clearly indicating the difference.

---

# 53. Query Parameters

Use query parameters for:

- time,
- pagination,
- filtering,
- bounding boxes,
- result limits.

Do not overload URL paths with arbitrary dynamic JSON.

---

# 54. Pagination

For potentially large collections:

```text
?page=1&limit=100
```

or cursor-based pagination may be used.

The implementation should choose one consistent mechanism.

---

# 55. Bounding Box Filtering

Spatial endpoints may support:

```text
?bbox=minLon,minLat,maxLon,maxLat
```

The backend must validate the bounding box.

If implemented, document whether the bbox is interpreted in EPSG:4326.

---

# 56. Time Filtering

Time-series endpoints may support:

```text
?startTime=<ISO>
&endTime=<ISO>
```

The backend should validate:

```text
startTime <= endTime
```

and ensure timestamps belong to the simulation period.

---

# 57. API Response Design

Responses should be designed around frontend needs.

Prefer:

```json
{
  "simulationId": "...",
  "data": {...}
}
```

over dumping raw internal Python objects.

Use stable property names.

---

# 58. Null Handling

Use explicit:

```json
null
```

when a value is genuinely unavailable.

Do not use:

```text
0
-1
"unknown"
```

as a hidden substitute for missing numerical data.

---

# 59. Spatial CRS in API

Every spatial product should have a known CRS.

GeoJSON delivered to web clients will generally use geographic coordinates.

The backend must perform any necessary transformation before delivery.

Do not make the frontend guess the CRS.

---

# 60. GeoJSON Rules

GeoJSON must:

- contain valid geometry,
- use correct coordinate ordering,
- have consistent properties,
- use a documented CRS strategy,
- avoid invalid/null geometries where possible.

Do not put raw SWMM node/link data into GeoJSON without spatial interpretation.

---

# 61. API Data Provenance

Where useful, result responses should expose:

```json
{
  "metadata": {
    "scenarioId": "michaung-2023",
    "modelVersion": "ward176-hydraulic-reconstructed-v1",
    "processingVersion": "flood-processing-v1"
  }
}
```

This is especially important for simulation-derived data.

---

# 62. API Caching

Static GIS responses may be cached aggressively.

Simulation result responses may be cached when the simulation is complete.

Do not cache incomplete dynamic results as if they were final.

---

# 63. ETags / Conditional Requests

Optional for later optimization.

Static assets are good candidates for:

```text
ETag
Cache-Control
```

Do not implement complicated cache invalidation before the basic product works.

---

# 64. Authentication

Authentication is not required for the initial academic MVP unless deployment requirements introduce it.

If authentication is later added:

- keep it at the API boundary,
- do not expose credentials to the frontend unnecessarily,
- protect simulation creation,
- protect private result assets.

---

# 65. Rate Limiting

Optional for the initial local MVP.

For cloud deployment, consider limiting:

- simulation creation,
- expensive result queries,
- large spatial requests.

Do not rate-limit static map assets so aggressively that the Digital Twin becomes unusable.

---

# 66. CORS

Development may require:

```text
localhost frontend
        ↓
localhost backend
```

Configure CORS explicitly.

Do not use unrestricted wildcard origins in production unless deliberately justified.

---

# 67. API Documentation

The backend should expose automatically generated API documentation where supported.

For FastAPI, this can use the framework's OpenAPI documentation.

The generated documentation should match this contract.

If implementation differs from this document, update the contract rather than silently diverging.

---

# 68. Frontend API Client Rule

The frontend should use one centralized API client.

Preferred conceptual structure:

```text
frontend/
└── src/
    └── api/
        ├── client.ts
        ├── scenarios.ts
        ├── simulations.ts
        ├── flood.ts
        ├── risk.ts
        └── assets.ts
```

Do not scatter raw `fetch()` calls throughout UI components.

---

# 69. API Type Generation

If practical, generate or maintain TypeScript types from the OpenAPI schema.

This reduces frontend/backend contract drift.

Preferred flow:

```text
FastAPI / OpenAPI
       ↓
TypeScript API types
       ↓
Frontend
```

Do not manually maintain duplicate types if automated generation is reliable.

---

# 70. API Contract Change Procedure

If an endpoint must change:

1. identify the reason,
2. update this document,
3. update backend implementation,
4. update OpenAPI,
5. update frontend client,
6. run integration tests.

Never silently change a response field used by the frontend.

---

# 71. Example End-to-End API Flow

A normal user session should look like:

```text
GET /health
      ↓
GET /scenarios
      ↓
GET /scenarios/michaung-2023
      ↓
POST /simulations
      ↓
GET /simulations/{id}
      ↓
GET /simulations/{id}
      ↓
...
      ↓
status = COMPLETED
      ↓
GET /simulations/{id}/summary
      ↓
GET /simulations/{id}/kpis
      ↓
GET /simulations/{id}/flood/timeline
      ↓
GET /simulations/{id}/flood/timeslice?time=...
      ↓
GET /simulations/{id}/risk
      ↓
GET /simulations/{id}/bottlenecks
      ↓
GET /simulations/{id}/recommendations
```

---

# 72. Minimum API for MVP

The minimum implementation should include:

```text
GET  /health
GET  /scenarios
GET  /scenarios/{scenarioId}

POST /simulations
GET  /simulations/{simulationId}

GET  /simulations/{simulationId}/summary
GET  /simulations/{simulationId}/kpis

GET  /gis/ward
GET  /gis/buildings
GET  /gis/roads
GET  /gis/drains

GET  /simulations/{simulationId}/flood
GET  /simulations/{simulationId}/flood/timeline
GET  /simulations/{simulationId}/flood/timeslice

GET  /simulations/{simulationId}/risk
GET  /simulations/{simulationId}/bottlenecks
GET  /simulations/{simulationId}/recommendations
```

Some spatial endpoints may be served directly from static storage if that is more efficient.

---

# 73. API Non-Goals

The API does not need to expose:

- raw SWMM `.inp` editing,
- arbitrary command execution,
- arbitrary file-system access,
- internal Python objects,
- internal database schema,
- raw AWS infrastructure details,
- every source-data attribute,
- developer debugging endpoints to the public frontend.

---

# 74. Scientific Integrity Rules

The API must distinguish:

```text
observed/source
model-derived
estimated
derived
```

For example:

```json
{
  "floodDepthM": 1.42,
  "dataType": "model-derived"
}
```

is preferable to implying:

```text
observedDepthM
```

when no observation exists.

---

# 75. Important Flood-Volume Rule

If the API exposes SWMM flooding loss, it must not label it as:

```text
observedFloodVolume
```

The current model's flooding loss is model-generated under an incomplete network representation.

Use names such as:

```text
simulatedFloodingVolume
```

or equivalent.

---

# 76. Model Limitation Metadata

A simulation result may expose a concise limitation block.

Example:

```json
{
  "limitations": [
    "Drainage network connectivity is incomplete.",
    "Some downstream terminals are provisional.",
    "Flood spatial products are derived from model output."
  ]
}
```

This is strongly recommended for academic transparency.

---

# 77. API Security Rules

Never allow the public API to:

- execute arbitrary shell commands,
- select arbitrary filesystem paths,
- select arbitrary executables,
- modify raw source files,
- directly edit the master SWMM model.

User input must map to controlled server-side operations.

---

# 78. API Performance Rules

Avoid:

```text
GET /everything
```

Prefer:

```text
summary
kpis
spatial products
time slice
asset details
```

This keeps the Digital Twin responsive.

---

# 79. API Contract Success Criteria

The API contract is successful when:

1. Frontend and backend can be developed independently.
2. Both use the same identifiers.
3. Both use the same simulation states.
4. Both use the same units.
5. Spatial data has predictable formats.
6. Errors have predictable structures.
7. Simulation lifecycle is explicit.
8. Large data can be served efficiently.
9. Model provenance can be traced.
10. Contract changes are deliberate.

---

# 80. Final Contract Principle

The API is the **single shared language** between the Digital Twin frontend and the simulation backend.

The intended flow is:

```text
FRONTEND
   │
   │  "Run Michaung scenario"
   ▼
API
   │
   ▼
BACKEND
   │
   ├── SWMM
   ├── GIS processing
   ├── KPI
   ├── Risk
   └── Recommendations
   │
   ▼
API
   │
   │  "Here are the results"
   ▼
FRONTEND
   │
   ├── 3D flood
   ├── Timeline
   ├── KPIs
   ├── Risk
   └── Decision support
```

The API should remain simple, stable, explicit, and scientifically honest.

---

# 81. Implementation Addendum — Backend v0.1.0 (2026-09-13)

This section records how the first backend implementation realises this
contract, including additive extensions. No existing endpoint, field, status or
enum above was renamed or removed.

## 81.1 Implemented endpoints

```text
GET  /health                                  (§11)
GET  /health/ready                            (§12)  200 "ready" | 503 "not_ready"
GET  /scenarios                               (§14)
GET  /scenarios/{scenarioId}                  (§15)  + event, dataType, spatial, provenance, limitations
GET  /scenarios/{scenarioId}/rainfall         NEW    source rainfall series (mm/hr + mm per interval)
POST /simulations                             (§18)  202 Accepted
GET  /simulations                             NEW    list; filters scenarioId, status; limit/offset
GET  /simulations/{simulationId}              (§21)
GET  /simulations/{simulationId}/results      (§50)  product discovery
GET  /simulations/{simulationId}/summary      (§25)
GET  /simulations/{simulationId}/kpis         (§26)
GET  /simulations/{simulationId}/diagnostics  NEW    SWMM warnings, continuity, timestep/instability rankings, flooded nodes
GET  /gis                                     NEW    layer catalogue
GET  /gis/ward | /gis/buildings | /gis/roads | /gis/drains | /gis/subcatchments   (§35–39)
GET  /gis/drains/{objectId}                   (§40)
GET  /gis/model/conduits                      NEW    SWMM model conduit geometry (model representation)
GET  /gis/model/nodes                         NEW    SWMM model node locations (model representation)
```

Not yet implemented (later phases): flood, timeline, timeslice, exposure, risk,
bottlenecks, recommendations, comparisons, cancel.

## 81.2 Readiness

`checks` keys: `swmm`, `model` (file present + approved SHA-256), `rainfall`,
`data` (GIS/network source files), `storage` (database + writable runtime
directories). Values `ok` | `error`; optional `details` gives safe messages.

## 81.3 Create simulation

* `modelVersion` is optional; when omitted the server's configured `MODEL_VERSION` is used and echoed in the response.
* Unknown request fields → `422 INVALID_REQUEST`.
* Non-empty `parameters` → `422 UNSUPPORTED_PARAMETER` (historical scenario runs unmodified).
* Unknown scenario → `404 SCENARIO_NOT_FOUND`; unknown/unapproved model → `404 MODEL_NOT_FOUND`;
  scenario not bound to model → `422 MODEL_NOT_COMPATIBLE`; server-side data missing → `503`.
* Response header `Location: /api/v1/simulations/{simulationId}`.

## 81.4 Simulation status

Additional fields: `applicationVersion`, `progressBasis` (always `"stage"`).

`stage` values:

```text
QUEUED | VALIDATION | WORKSPACE_PREPARATION | SWMM_EXECUTION | RESULT_PROCESSING | COMPLETE
```

Progress: CREATED 0, VALIDATING 10, PREPARING 20, RUNNING 30, PROCESSING 75, COMPLETED 100.
A FAILED simulation keeps the `stage` and `progress` at which it failed.

Failure `error.code` values: `MODEL_VALIDATION_FAILED`, `MODEL_NOT_FOUND`,
`MODEL_NOT_COMPATIBLE`, `RAINFALL_NOT_FOUND`, `RAINFALL_VALIDATION_FAILED`,
`SWMM_UNAVAILABLE`, `SIMULATION_FAILED`, `SIMULATION_TIMEOUT`,
`PROCESSING_FAILED`, `SIMULATION_INTERRUPTED`, `INTERNAL_ERROR`.

Result endpoints on a simulation that is not COMPLETED → `409 SIMULATION_NOT_COMPLETED`.

## 81.5 Summary and KPIs

* Flood values that the pipeline does not yet produce are `null` with `available: false` and a `reason` (§58), never 0.
* Summary adds `hydraulics` (`simulatedFloodingVolumeL`, `wetWeatherInflowL`, `externalOutflowL`, `finalStoredVolumeL`, peak system flooding rate/time), `drainage.surchargedNodes`, `drainage.totalNodes`, `modelDiagnostics`, `metadata`, `limitations`.
* KPI groups: `rainfall`, `flood`, `hydraulics`, `drainage`, `modelDiagnostics`. Each KPI is `{value, unit, source, description, methodVersion?, time?}` with `source` ∈ `source` | `model-derived`.
* Volumes in `L`, flows in `m3/s`, depths in `mm`/`m`, counts in `count`, errors in `%`.
* SWMM flooding loss is exposed only as `simulatedFloodingVolume(L)` (§75).
* Timestamps are UTC `Z`, inherited from the IMERG rainfall time basis.

## 81.6 GIS responses

* `application/geo+json`, RFC 7946 FeatureCollection in lon/lat (OGC:CRS84); no legacy `crs` member.
* A `metadata` foreign member records `layer`, `dataType` (`source` | `model-construct` | `model-representation`), `sourceCrs`, `processingVersion` (`web-gis-v1`), `featureCount`, `invalidSourceGeometryCount`, `bbox`.
* Coordinates are rounded to 7 decimals; no simplification or feature removal.
* `ETag` + `Cache-Control: public, max-age=3600`; `If-None-Match` → `304`.
* Drains keep `objectId` (GCC source) and `modelLinkIds` (SWMM conduits) as separate fields, plus `inHydraulicModel` and `dataQuality` flags.
* `bbox`/pagination filters on GIS layers are not implemented.

---

# 82. Implementation Addendum — Flood Products, Time Series, Terrain (2026-09-13)

Additive only; method in `docs/FLOOD_PROCESSING_METHOD.md`.

## 82.1 Flood endpoints (require a COMPLETED simulation, else `409 SIMULATION_NOT_COMPLETED`)

```text
GET /simulations/{id}/flood                        (§29) overview + metrics + legend + validation
GET /simulations/{id}/flood/timeline               (§32) actual SWMM reporting timestamps
GET /simulations/{id}/flood/timeslice?time=<ISO>   (§33) state at one timestamp
GET /simulations/{id}/flood/timeslices/{key}       (§34) GeoJSON asset, key = YYYYMMDDTHHMMSSZ
GET /simulations/{id}/flood/zones                  NEW   influence zones of all nodes (GeoJSON)
GET /simulations/{id}/flood/extent                 (§30) 404 FLOOD_PRODUCT_NOT_AVAILABLE in flood-processing-v1
GET /simulations/{id}/flood/depth                  (§31) 404 FLOOD_PRODUCT_NOT_AVAILABLE in flood-processing-v1
```

`/flood`:
- `available`, `peakTime`, `peakIndex`;
- `extentAvailable: false`, `depthAvailable: false`, `influenceZonesAvailable: true`, `maximumDepthM: null`;
- `metrics` (Quantity objects with `value/unit/source/description`);
- `notDerived`, `legend`, `metadata.floodProcessingVersion`, `validation[]`.

`/flood/timeline`:
- `intervalMinutes`, `timestamps[]` (§32), `peakIndex`, `legend`, `metadata`;
- `entries[]` with `index, time, key, hasFlooding, floodingNodeCount, surchargedNodeCount, systemFloodingRateCms, maxNodeFloodingRateCms, rainfallMmHr, floodingInfluenceZoneAreaM2, approxCumulativeSystemOverflowM3, asset{type,url}`.
- The frontend treats `asset.url` as opaque.

`/flood/timeslice`:
- `time` must be ISO 8601 with Z or an offset. Naive or malformed values → `422 INVALID_TIMESTAMP`. A valid instant that is not a reporting timestamp → `404 TIMESTAMP_NOT_FOUND`, with `details.firstTime/lastTime/intervalMinutes`.
- Response: `time, index, flood{…entry summary}, influence (FeatureCollection), asset, metadata`.
- The contract example field `flood.extent` is intentionally not used, because v1 produces no extent.

Time-slice GeoJSON features: `properties.featureType` is `node` or `influenceZone`, plus:

```text
nodeId, state (FLOODING|SURCHARGED), overflowClass (LOW|MODERATE|HIGH|null),
floodingRateCms, approxCumulativeOverflowM3, nodeWaterDepthM, nodeHeadM, fillRatio, zoneAreaM2 (zones)
```

Overflow classes are backend-defined visualisation classes; the frontend only maps them to colours.

## 82.2 SWMM time series

```text
GET /simulations/{id}/timeseries/system
GET /simulations/{id}/timeseries/nodes/{nodeId}   series: depthM, headM, lateralInflowCms, totalInflowCms, floodingCms
GET /simulations/{id}/timeseries/links/{linkId}   series: flowCms, depthM, velocityMps, capacity; + sourceObjectId
```

Response: `timestamps[]`, `intervalMinutes`, `variables{name:{unit,description}}`, `series{name:[…]}`, `dataType: "model-derived"`. Unknown element → `404 NOT_FOUND`.

## 82.3 Terrain

`GET /gis/terrain`: the Ward 176 Copernicus DEM grid.
- Fields: `width, height, rowOrder: north-to-south, firstCellCenter, cellSizeDeg, bounds, heights[]`.
- `null` marks the outside-ward mask; masked cells never get an elevation.
- Also `verticalReference`, `statistics`, `limitations`, `provenance`; `ETag` caching.

## 82.4 Summary / KPI / products changes

- `/summary` `flood` block adds `nodeFloodingAvailable`, `floodProcessingVersion`, `peakTime`, `peakConcurrentFloodingNodes`, `floodingDurationHr`, `representation`. `maximumDepthM`/`affectedAreaM2` remain `null`.
- `/kpis` `flood` group adds `peakConcurrentFloodingNodes`, `floodingDuration`, `firstFloodingTime` (unit `ISO 8601`) and `maximumNodeWaterDepth` (explicitly not ground depth), each with `methodVersion: flood-processing-v1`.
- `/results` `products.flood` and `products.timeline` are `true` for completed simulations.

---

# 83. Implementation Addendum — Decision Support: Bottlenecks, Exposure, Recommendations (2026-09-14)

Additive only; no existing endpoint, field or enum was renamed or removed. Method: `docs/DECISION_SUPPORT_METHOD.md`.
All endpoints require a COMPLETED simulation (`409 SIMULATION_NOT_COMPLETED`); unknown/invalid IDs → `404 SIMULATION_NOT_FOUND`.

## 83.1 Endpoints

```text
GET /simulations/{id}/bottlenecks[?severity=HIGH|MODERATE|LOW]   (§44) bottleneck-analysis-v1
GET /simulations/{id}/bottlenecks/geojson                         (§46) conduit geometry of potential bottlenecks, ETag
GET /simulations/{id}/bottlenecks/{linkId}                        NEW   one evidence record; 404 BOTTLENECK_NOT_FOUND (details.numericalDiagnostic when applicable)
GET /simulations/{id}/exposure                                    (§41) exposure-analysis-v1 summary, 190-entry timeline, per-node exposure
GET /simulations/{id}/exposure/buildings[?time=<ISO>]             NEW   exposed building ObjectIDs (event scope when time omitted)
GET /simulations/{id}/exposure/roads[?time=<ISO>]                 NEW   exposed carriageway ObjectIDs
GET /simulations/{id}/recommendations[?priority=HIGH|MEDIUM|LOW]  (§47) decision-support-v1
GET /simulations/{id}/risk, /risk/geojson                         (§42–43) 404 RISK_PRODUCT_NOT_AVAILABLE (not derived, with alternatives)
```

`time` follows §82.1 rules: `422 INVALID_TIMESTAMP` / `404 TIMESTAMP_NOT_FOUND`.

## 83.2 Bottleneck record (§44 fields kept: `linkId`, `sourceObjectId`, `severity`, `reason`, `evidence` → `criteria`)

`rank, linkId, sourceObjectId, identifierNote, fromNodeId, toNodeId, severity (HIGH|MODERATE|LOW), uncappedSeverity, severityCappedByNetworkContext, score (0.25–1), criteriaMet, criteria[{id L1|L2|L3|S1, label, met, value, unit, threshold, source}], confidence (MEDIUM|LOW), confidenceReasons[], interpretation (CAPACITY_LIMITED|SUSTAINED_SURCHARGE|PEAK_FLOW_ABOVE_FULL_FLOW|LOADING_IN_COMPONENT_WITHOUT_OUTFALL), reason, conduit{}, hydraulics{maximumFlowCms, timeOfMaximumFlow, maximumVelocityMps, maxOverFullFlow, maxOverFullDepth, derivedFullFlowCapacityCms, hoursFullBothEnds, hoursFullUpstream, hoursFullDownstream, hoursAboveFullNormalFlow, hoursCapacityLimited}, numericalDiagnostics{}, connectedNodes[], networkContext{modelComponentId, componentHasOutfall, componentOutfalls}, sourceAttributes{}, projectInvestigation, explanation{whatIsThis, whyFlagged, interpretation, sourceData, plannerConsideration, disclaimer}`.

List response adds `terminology, criteriaDefinition, legend, summary{conduitsScreened, potentialBottlenecks, bySeverity, inComponentsWithoutOutfall, modelComponents, modelComponentsWithOutfall}, numericalDiagnostics[], limitations[]`. GeoJSON feature properties: `featureType: potentialBottleneck, linkId, sourceObjectId, fromNodeId, toNodeId, severity, score, confidence, rank, componentHasOutfall, floodingNodeIds`.

## 83.3 Exposure

`/exposure`: `terminology, definition, totals{buildings{count, footprintAreaM2}, roads{count, areaM2}}, event, peak{index, time, …}, maxConcurrent, timeline[{index, time, floodingNodeCount, buildingsIntersecting, buildingFootprintAreaM2, roadsIntersecting, roadAreaM2}], byNode[], limitations`.
Scope blocks: `buildings{intersectingCount, percentOfBuildings, footprintAreaWithinZonesM2, percentOfFootprintArea, intersectingZonesOfNodesWithoutOutfallCount}`, `roads{intersectingCount, percentOfRoadFeatures, areaWithinZonesM2, percentOfRoadArea}`.
The §41 example fields `affectedCount`/`affectedAreaM2` are intentionally not used: "affected" would imply impact; exposure is spatial intersection with model-derived influence zones.
Asset responses: `assetType, scope (event|timestamp), time, index, floodingNodeIds, count, objectIds[], assets[{objectId, areaWithinZonesM2, nodeIds}]`.

## 83.4 Recommendations (§47 fields kept: `id, priority, category, title, description → recommendation, drivers`)

`id, rule (R1–R6), category (DRAINAGE_CAPACITY|NETWORK_DATA_VERIFICATION|DRAINAGE_INSPECTION|PREPAREDNESS_AND_ACCESS|MAINTENANCE|MODEL_DATA_VERIFICATION), priority, confidence, title, recommendation, why, evidence{links[{linkId, sourceObjectId}], nodes[], metrics[{label, value, unit, source}]}, drivers[], confidenceReasons[], relatedBottleneckLinkIds[], focus{linkIds, nodeIds}, disclaimer`. List adds `rules{}, summary{total, byPriority, byRule}, disclaimer` and all three method versions.

## 83.5 Summary / KPI / products changes

- `/summary` `drainage.potentialBottlenecks` is now the count with `potentialBottlenecksAvailable: true`, `potentialBottlenecksBySeverity`, `bottleneckAnalysisVersion`.
- `/kpis` `drainage.potentialBottlenecks` is a Quantity (`methodVersion`, `bySeverity`); new group `exposure`: `buildingsInInfluenceZonesEvent`, `buildingsInInfluenceZonesPeak`, `roadAreaInInfluenceZonesEvent`. `flood.affectedBuildings` stays unavailable (no flood extent).
- `/results` `products.bottlenecks`, `products.exposure`, `products.recommendations` are `true` for completed simulations; `products.risk` stays `false`.
- Simulation `artifacts` record `bottleneckAnalysisVersion`, `exposureAnalysisVersion`, `decisionSupportVersion`.

---

# 84. Implementation Addendum — Demo Result, Rainfall Scenarios, Dynamic Bottlenecks, Comparison (2026-09-14)

Additive only; no existing endpoint, field or enum was renamed or removed. The previous `422 UNSUPPORTED_PARAMETER` for every `parameters` payload (§81.3) is narrowed: the registered `rainfallMultiplier` is now accepted. Methods: `docs/SCENARIO_ANALYSIS_METHOD.md`, `docs/DECISION_SUPPORT_METHOD.md` §3.2.

## 84.1 Rainfall-multiplier scenario runs

- `POST /simulations` body `{"scenarioId": "michaung-2023", "parameters": {"rainfallMultiplier": 1.25}}`.
- Validation: unknown keys → `422 UNSUPPORTED_PARAMETER`; non-number, NaN/infinity, outside 0.5–2.0, more than 2 decimals → `422 INVALID_PARAMETER` (`details.minimum/maximum`).
- `GET /scenarios/{id}` adds `whatIf {parameter, label, description, minimum, maximum, decimals, baseline, presets[{value,label}], scenarioAnalysisVersion, terminology}`.
- `GET /simulations/{id}` and list items add `parameters`, `executionMode` (`swmm` | `precomputed-demo`), `demoId`, `scenarioRun` (see method doc §4) — all optional for older clients.
- `GET /simulations` adds filters `rainfallMultiplier` (1.0 matches runs without parameters) and `executionMode`.
- `/summary` and `/kpis` `metadata` add `executionMode`, `parameters`, `rainfallMultiplier`, `scenarioRun`; rainfall KPIs are the scaled series of the run.

## 84.2 Precomputed demonstration result

```text
GET  /demo                     -> {demoResults: [{demoId, label, description, scenarioId, modelVersion, rainfallMultiplier, executionMode, available, verification, loadedSimulationId, loadingSimulationId}]}
POST /demo/{demoId}/load       -> 202 {demoId, simulationId, status, reused}   (never runs SWMM)
```

The registered archived SWMM outputs (`backend/config/demo.json`, SHA-256 pinned) are processed by the normal pipeline into a simulation with `executionMode: precomputed-demo`. A completed demo simulation is re-used. Missing or modified files → `503 RESULT_NOT_FOUND`; unknown `demoId` → `404 NOT_FOUND`.

## 84.3 Dynamic bottlenecks

`GET /simulations/{id}/bottlenecks/timeline[?time=<ISO>]` (bottleneck-timeline-v1): `definition`, `links{linkId: {sourceObjectId, eventSeverity, fullFlowCapacityCms, componentHasOutfall}}`, `summary{timestampsWithActiveBottlenecks, firstActiveTime, lastActiveTime, perLink{activeSteps, activeHours, stepsBySeverity, firstActive, lastActive, peakUtilization, peakUtilizationTime}}`, `entries[{index, time, activeCount, highestSeverity, active[{linkId, sourceObjectId, severity, eventSeverity, criteria{full, aboveFullFlowCapacity, connectedNodeFlooding}, flowCms, fullFlowCapacityCms, utilization, fillFraction, depthM, velocityMps, floodingNodeIds}], mostLoaded}]`. With `time`, `entries` is replaced by `entry`. Time errors as §82.1. `bottlenecks.json` adds `derivedFullFlowCapacities{linkId: m3/s}`. Decision manifests and simulation artifacts add `bottleneckTimelineVersion`.

## 84.4 Scenario comparison (§51)

```text
POST /comparisons   {"simulationIds": [baselineId, scenarioId]}
GET  /comparisons?baseline=<id>&scenario=<id>
```

Response: `comparisonId, scenarioAnalysisVersion, terminology, simulations[], baseline, scenario ({simulationId, scenarioId, modelVersion, processingVersion, rainfallMultiplier, executionMode, label}), methodVersions, metrics[{key, label, unit, source, baseline, scenario, absoluteChange, percentChange}], floodInfluence{definition, event{both, scenarioOnly, baselineOnly}, peak, timeline[], nodeMaximumOverflowRates[], sharedScale{note, baselineOverflowClasses, scenarioOverflowClasses}}, bottlenecks{new, persisting, notFlaggedInScenario}, exposure{buildingsEvent, buildingsPeak, roadAreaEventM2, linkedToComponentsWithoutOutfall, terminology}, recommendations{new, persisting, notTriggeredInScenario, note}, statements[], limitations[]`.

Errors: same ID, different model/scenario/processing or method versions, different timestamps → `422 COMPARISON_NOT_COMPATIBLE`; not completed → `409`; unknown → `404`. The §51 `metrics.maximumDepthM` example is not used (no ground depth exists).

## 84.5 Transport

Responses ≥ 2 KB are gzip-compressed when the client accepts it (e.g. bottleneck timeline 325 KB, comparison 48.5 KB → 5.6 KB).

---

# 85. Implementation Addendum — Location Flood Check (2026-09-22)

Location-specific historical flood analysis using the model-derived response around a user-selected point (location-check-v1, `docs/LOCATION_CHECK_METHOD.md`). A spatial query over one completed simulation; it never starts SWMM.

```text
POST /simulations/{simulationId}/location-check
{"latitude": 12.9712, "longitude": 80.2185, "radiusMeters": 250}
```

| Field | Type | Rule |
|---|---|---|
| `latitude` | number | WGS 84, −90…90, finite |
| `longitude` | number | WGS 84, −180…180, finite |
| `radiusMeters` | number | optional, default 250, 50…1000 (evaluated in EPSG:32644) |

Unknown fields are rejected.

**Response:** `simulationId, scenarioId, modelVersion, rainfallMultiplier, locationCheckVersion, floodProcessingVersion, dataType ("model-derived"), terminology, location{latitude, longitude, withinStudyArea, crs, processingCrs, eastingM, northingM}, radiusMeters, response{code, description}, nearestNode{nodeId, nodeType, location, distanceM, withinRadius, zoneOverlapM2, zoneOverlapShare, isNearest, zoneContainsLocation, response}, surroundingArea{circleAreaM2, areaWithinStudyAreaM2, shareWithinStudyArea, associatedNodeCount, overflowingNodeCount, surchargeOnlyNodeCount, noReportedStressNodeCount, outfallNodeCount, areaAssociatedWithOverflowM2, shareAssociatedWithOverflow, firstOverflowTime, lastOverflowTime, overflowDurationHours, peak{time, index, combinedOverflowRateCms, overflowingNodeCount, overflowingNodeIds, areaAssociatedWithOverflowM2, shareAssociatedWithOverflow} | null}, nodes[], potentialBottlenecks[] | null, intervalMinutes, groundFloodDepthM (always null), floodExtentAvailable (false), notDerived, timeConvention, method, limitations[]`.

Node `response`: `condition` (`OVERFLOW` | `SURCHARGE_ONLY` | `NO_REPORTED_STRESS` | `OUTFALL`), `description`, `overflowPeriods, overflowHours, surchargePeriods, surchargeHours, peakOverflowRateCms, peakOverflowTime, firstOverflowTime, lastOverflowTime, highestOverflowClass, approxCumulativeOverflowM3, maxNodeWaterDepthM, maxFillRatio` (outfalls carry only `condition` and `description`). `response.code`: `OVERFLOW_AT_NEAREST_NODE` | `OVERFLOW_IN_SURROUNDING_AREA` | `SURCHARGE_ONLY` | `NO_REPORTED_STRESS`.

`potentialBottlenecks` is `null` when decision-support products are unavailable (the flood response is still returned).

**Errors:** invalid body → `422 INVALID_REQUEST`; outside Ward 176 → `422 LOCATION_OUTSIDE_STUDY_AREA` (details: latitude, longitude); unknown or malformed simulation ID → `404 SIMULATION_NOT_FOUND`; not completed or failed → `409 SIMULATION_NOT_COMPLETED` (details: status). No filesystem paths are returned.
