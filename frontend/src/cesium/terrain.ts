import { CustomHeightmapTerrainProvider, GeographicTilingScheme, Math as CesiumMath, Rectangle } from 'cesium'
import type { TerrainGrid } from '../types/gis'

export const TERRAIN_TILE_SIZE = 32

/**
 * Sample the backend DEM grid (Copernicus GLO-30, point-registered cell centres) at lon/lat.
 *
 * Bilinear interpolation over the valid neighbouring samples (weights renormalised).
 * Returns null where every neighbour is masked or the point is outside the grid —
 * masked cells are never given an elevation.
 */
export function sampleDem(grid: TerrainGrid, lon: number, lat: number): number | null {
  const col = (lon - grid.firstCellCenter.lon) / grid.cellSizeDeg.lon
  const row = (grid.firstCellCenter.lat - lat) / grid.cellSizeDeg.lat // rows run north to south
  if (col < -0.5 || row < -0.5 || col > grid.width - 0.5 || row > grid.height - 0.5) return null
  const c0 = Math.floor(col)
  const r0 = Math.floor(row)
  const fc = col - c0
  const fr = row - r0
  let sum = 0
  let weight = 0
  for (const [dr, dc, w] of [
    [0, 0, (1 - fr) * (1 - fc)],
    [0, 1, (1 - fr) * fc],
    [1, 0, fr * (1 - fc)],
    [1, 1, fr * fc],
  ] as const) {
    const r = r0 + dr
    const c = c0 + dc
    if (r < 0 || c < 0 || r >= grid.height || c >= grid.width || w === 0) continue
    const h = grid.heights[r * grid.width + c]
    if (h === null || h === undefined) continue
    sum += h * w
    weight += w
  }
  return weight > 0 ? sum / weight : null
}

/**
 * Terrain provider backed by the project DEM. Outside the Ward 176 DEM mask the
 * surface stays at height 0 (Cesium's default ellipsoid surface = "no elevation data"),
 * so an edge step appears at the mask boundary. Heights are the DEM values as delivered
 * (EGM2008 orthometric), used consistently for every layer; no geoid conversion.
 */
export function createDemTerrainProvider(grid: TerrainGrid): CustomHeightmapTerrainProvider {
  const tilingScheme = new GeographicTilingScheme()
  const extent = Rectangle.fromDegrees(grid.bounds.west, grid.bounds.south, grid.bounds.east, grid.bounds.north)
  const size = TERRAIN_TILE_SIZE
  return new CustomHeightmapTerrainProvider({
    width: size,
    height: size,
    tilingScheme,
    credit: 'Terrain: Copernicus DEM GLO-30 (DSM) — Ward 176 clip',
    callback: (x, y, level) => {
      const heights = new Float32Array(size * size)
      const rect = tilingScheme.tileXYToRectangle(x, y, level)
      if (!Rectangle.intersection(rect, extent)) return heights
      const west = CesiumMath.toDegrees(rect.west)
      const east = CesiumMath.toDegrees(rect.east)
      const north = CesiumMath.toDegrees(rect.north)
      const south = CesiumMath.toDegrees(rect.south)
      for (let j = 0; j < size; j++) {
        const lat = north - ((north - south) * j) / (size - 1)
        for (let i = 0; i < size; i++) {
          const lon = west + ((east - west) * i) / (size - 1)
          heights[j * size + i] = sampleDem(grid, lon, lat) ?? 0
        }
      }
      return heights
    },
  })
}
