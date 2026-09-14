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
