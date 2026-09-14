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
