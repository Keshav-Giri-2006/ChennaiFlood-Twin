import { Color } from 'cesium'

/**
 * Visual styling only. Flood, bottleneck and exposure colours map backend-provided states/classes
 * to colours; no thresholds or scientific rules are defined here.
 */
export const LAYER_COLORS = {
  boundary: Color.fromCssColorString('#f5c542'),
  building: Color.fromCssColorString('#d9d4c7').withAlpha(0.92),
  buildingUnderFlood: Color.fromCssColorString('#d9d4c7').withAlpha(0.35),
  road: Color.fromCssColorString('#6b7280').withAlpha(0.75),
  subcatchment: Color.fromCssColorString('#8b5cf6').withAlpha(0.18),
  drainModelled: Color.fromCssColorString('#22d3ee'),
  drainNotModelled: Color.fromCssColorString('#94a3b8'),
  highlight: Color.fromCssColorString('#10f5a0'),
  focus: Color.fromCssColorString('#ff3d7f'),
}

/** Uniform extrusion used purely for 3D context: the project has no building height data. */
export const BUILDING_VISUAL_EXTRUSION_M = 6

export const FLOOD_CLASS_COLORS: Record<string, string> = {
  LOW: '#7dd3fc',
  MODERATE: '#3b82f6',
  HIGH: '#1e3a8a',
}
export const SURCHARGED_COLOR = '#f59e0b'

export function floodCss(state: string, overflowClass: string | null): string {
  return state === 'FLOODING' ? FLOOD_CLASS_COLORS[overflowClass ?? 'LOW'] ?? FLOOD_CLASS_COLORS.LOW : SURCHARGED_COLOR
}

export function floodColor(state: string, overflowClass: string | null, alpha: number): Color {
  return Color.fromCssColorString(floodCss(state, overflowClass)).withAlpha(alpha)
}

/**
 * Node marker emphasis (display only; the SWMM state classification is unchanged).
 * Normal nodes are small and muted, surcharged nodes clearly brighter, overflowing nodes the strongest
 * and scaled by the backend overflow display class.
 */
export const NODE_MARKER = {
  normal: { pixelSize: 5, outlineWidth: 0, color: '#94a3b8', alpha: 0.55 },
  surcharged: { pixelSize: 12, outlineWidth: 2 },
  flooding: { pixelSize: { LOW: 15, MODERATE: 18, HIGH: 21 } as Record<string, number>, outlineWidth: 2.5, pulseAmplitude: 2, pulsePeriodMs: 1800 },
}

/** Potential bottleneck diagnostic concern classes (backend severity). */
export const BOTTLENECK_COLORS: Record<string, string> = {
  HIGH: '#ef4444',
  MODERATE: '#a855f7',
  LOW: '#facc15',
}
/** Potential bottleneck not loaded at the selected timestamp (time-aware view). */
export const BOTTLENECK_INACTIVE_COLOR = '#94a3b8'

/** Scenario comparison categories (categorical: no cross-run severity scale). */
export const COMPARISON_COLORS = {
  both: '#60a5fa',
  scenarioOnly: '#f43f5e',
  baselineOnly: '#a3e635',
}
export const BOTTLENECK_WIDTH: Record<string, number> = { HIGH: 9, MODERATE: 7, LOW: 5 }

/** Model-derived exposure highlight (assets intersecting influence zones of overflowing nodes). */
export const EXPOSURE_COLORS = {
  building: '#fb923c',
  road: '#fdba74',
}
