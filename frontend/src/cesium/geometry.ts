import { Cartesian3, PolygonHierarchy } from 'cesium'
import type { Geometry, Position } from '../types/gis'

/** Convert GeoJSON lon/lat positions (RFC 7946, backend-transformed) to Cartesian3 at height 0. */
export function positions(coords: Position[]): Cartesian3[] {
  const flat: number[] = []
  for (const p of coords) flat.push(p[0], p[1])
  return Cartesian3.fromDegreesArray(flat)
}

/** Drop the closing vertex that GeoJSON rings repeat. */
function openRing(ring: Position[]): Position[] {
  if (ring.length > 1) {
    const a = ring[0]
    const b = ring[ring.length - 1]
    if (a[0] === b[0] && a[1] === b[1]) return ring.slice(0, -1)
  }
  return ring
}

export function polygonHierarchies(geometry: Geometry): PolygonHierarchy[] {
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.type === 'MultiPolygon' ? geometry.coordinates : []
  return polygons.map(([outer, ...holes]) => new PolygonHierarchy(positions(openRing(outer)), holes.map((h) => new PolygonHierarchy(positions(openRing(h))))))
}

type HeightFn = (lon: number, lat: number) => number

/** Polygon rings as explicit 3D positions (terrain-draped by the caller's height function). */
export function polygonHierarchiesAt(geometry: Geometry, height: HeightFn): PolygonHierarchy[] {
  const at = (ring: Position[]) => Cartesian3.fromDegreesArrayHeights(openRing(ring).flatMap((p) => [p[0], p[1], height(p[0], p[1])]))
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.type === 'MultiPolygon' ? geometry.coordinates : []
  return polygons.map(([outer, ...holes]) => new PolygonHierarchy(at(outer), holes.map((h) => new PolygonHierarchy(at(h)))))
}

/** Line parts as explicit 3D positions (terrain-draped by the caller's height function). */
export function linePartsAt(geometry: Geometry, height: HeightFn): Cartesian3[][] {
  const at = (coords: Position[]) => Cartesian3.fromDegreesArrayHeights(coords.flatMap((p) => [p[0], p[1], height(p[0], p[1])]))
  if (geometry.type === 'LineString') return [at(geometry.coordinates)]
  if (geometry.type === 'MultiLineString') return geometry.coordinates.map(at)
  if (geometry.type === 'Polygon') return geometry.coordinates.map(at)
  if (geometry.type === 'MultiPolygon') return geometry.coordinates.flat().map(at)
  return []
}

export function lineParts(geometry: Geometry): Cartesian3[][] {
  if (geometry.type === 'LineString') return [positions(geometry.coordinates)]
  if (geometry.type === 'MultiLineString') return geometry.coordinates.map(positions)
  if (geometry.type === 'Polygon') return geometry.coordinates.map(positions)
  if (geometry.type === 'MultiPolygon') return geometry.coordinates.flat().map(positions)
  return []
}

export function bboxOf(features: { geometry: Geometry }[]): [number, number, number, number] | null {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  const visit = (value: unknown): void => {
    if (Array.isArray(value) && typeof value[0] === 'number') {
      const [x, y] = value as number[]
      minX = Math.min(minX, x)
      minY = Math.min(minY, y)
      maxX = Math.max(maxX, x)
      maxY = Math.max(maxY, y)
    } else if (Array.isArray(value)) {
      value.forEach(visit)
    }
  }
  features.forEach((f) => visit(f.geometry.coordinates))
  return Number.isFinite(minX) ? [minX, minY, maxX, maxY] : null
}

function ringContains(ring: Position[], lon: number, lat: number): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}

/**
 * Even-odd point-in-polygon test in lon/lat for (Multi)Polygon geometry, holes included.
 * Used only as an immediate UI hint when a location is picked; the backend decides in EPSG:32644.
 */
export function pointInGeometry(lon: number, lat: number, geometry: Geometry): boolean {
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.type === 'MultiPolygon' ? geometry.coordinates : []
  return polygons.some((rings) => rings.reduce((inside, ring) => (ringContains(ring, lon, lat) ? !inside : inside), false))
}
