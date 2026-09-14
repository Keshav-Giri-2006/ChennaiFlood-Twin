// Minimal RFC 7946 GeoJSON types plus the property schemas served by /api/v1/gis.

export type Position = [number, number] | [number, number, number]

export type Geometry =
  | { type: 'Point'; coordinates: Position }
  | { type: 'LineString'; coordinates: Position[] }
  | { type: 'MultiLineString'; coordinates: Position[][] }
  | { type: 'Polygon'; coordinates: Position[][] }
  | { type: 'MultiPolygon'; coordinates: Position[][][] }

export interface Feature<P = Record<string, unknown>> {
  type: 'Feature'
  id?: string | number
  geometry: Geometry
  properties: P
}

export interface LayerMetadata {
  layer?: string
  title?: string
  dataType?: string
  crs?: string
  sourceCrs?: string
  featureCount?: number
  bbox?: [number, number, number, number]
  [key: string]: unknown
}

export interface FeatureCollection<P = Record<string, unknown>> {
  type: 'FeatureCollection'
  metadata?: LayerMetadata
  features: Feature<P>[]
}

export interface DrainProperties {
  objectId: number
  zone: string | null
  ward: string | null
  location: string | null
  drainType: string | null
  lengthM: number | null
  widthM: number | null
  depthM: number | null
  sizeLabel: string | null
  status: string | null
  material: string | null
  drainDetail: string | null
  sourceInvertStartM: number | null
  sourceInvertEndM: number | null
  modelLinkIds: string[]
  inHydraulicModel: boolean
  dataQuality: { flag: string; decision: string; note: string }[]
}

export interface TerrainGrid {
  source: string
  crs: 'EPSG:4326'
  width: number
  height: number
  rowOrder: 'north-to-south'
  firstCellCenter: { lon: number; lat: number }
  cellSizeDeg: { lon: number; lat: number }
  bounds: { west: number; east: number; north: number; south: number }
  verticalReference: string
  maskNote: string
  statistics: { validCells: number; maskedCells: number; min: number; max: number; mean: number }
  heights: (number | null)[]
}

export interface FloodFeatureProperties {
  featureType: 'node' | 'influenceZone'
  nodeId: string
  state: 'FLOODING' | 'SURCHARGED'
  overflowClass: 'LOW' | 'MODERATE' | 'HIGH' | null
  floodingRateCms: number
  approxCumulativeOverflowM3: number
  nodeWaterDepthM: number
  nodeHeadM: number
  fillRatio: number | null
  zoneAreaM2?: number
}
