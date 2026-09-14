import { describe, expect, it } from 'vitest'
import type { TerrainGrid } from '../types/gis'
import { sampleDem } from './terrain'

function grid(heights: (number | null)[], width: number, height: number): TerrainGrid {
  return {
    source: 'test',
    crs: 'EPSG:4326',
    width,
    height,
    rowOrder: 'north-to-south',
    firstCellCenter: { lon: 80.0, lat: 13.0 },
    cellSizeDeg: { lon: 0.001, lat: 0.001 },
    bounds: { west: 79.9995, east: 80.0005 + (width - 1) * 0.001, north: 13.0005, south: 12.9995 - (height - 1) * 0.001 },
    verticalReference: 'test',
    maskNote: 'test',
    statistics: { validCells: 0, maskedCells: 0, min: 0, max: 0, mean: 0 },
    heights,
  }
}

describe('sampleDem', () => {
  const g = grid([1, 2, 3, 4], 2, 2) // row 0 (north): 1 2 ; row 1 (south): 3 4

  it('returns exact values at cell centres (north-to-south rows)', () => {
    expect(sampleDem(g, 80.0, 13.0)).toBeCloseTo(1)
    expect(sampleDem(g, 80.001, 13.0)).toBeCloseTo(2)
    expect(sampleDem(g, 80.0, 12.999)).toBeCloseTo(3)
  })

  it('interpolates bilinearly between centres', () => {
    expect(sampleDem(g, 80.0005, 12.9995)).toBeCloseTo(2.5)
  })

  it('never invents elevations for masked cells or outside the grid', () => {
    const masked = grid([null, null, null, null], 2, 2)
    expect(sampleDem(masked, 80.0005, 12.9995)).toBeNull()
    expect(sampleDem(g, 81, 13)).toBeNull()
    const partial = grid([10, null, null, null], 2, 2)
    expect(sampleDem(partial, 80.0005, 12.9995)).toBeCloseTo(10) // renormalised over valid neighbours only
  })
})

describe('terrain-sampled static geometry', () => {
  it('drapes line and polygon vertices at the DEM height plus offset (no clamping primitives)', async () => {
    const { Cartographic } = await import('cesium')
    const { linePartsAt, polygonHierarchiesAt } = await import('./geometry')
    const g = grid([10, 10, 10, 10], 2, 2)
    const height = (lon: number, lat: number) => (sampleDem(g, lon, lat) ?? 0) + 0.5
    const [line] = linePartsAt({ type: 'LineString', coordinates: [[80.0, 13.0], [80.001, 12.999]] }, height)
    expect(line.map((p) => Math.round(Cartographic.fromCartesian(p).height * 100) / 100)).toEqual([10.5, 10.5])
    const [poly] = polygonHierarchiesAt({ type: 'Polygon', coordinates: [[[80.0, 13.0], [80.001, 13.0], [80.001, 12.999], [80.0, 13.0]]] }, () => 2)
    expect(poly.positions).toHaveLength(3)
    expect(Cartographic.fromCartesian(poly.positions[0]).height).toBeCloseTo(2, 3)
  })
})
