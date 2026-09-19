/**
 * Presentation mapping from the simulated rainfall intensity (mm/hr, from the backend flood timeline of
 * the displayed run) to display classes and visual rain parameters.
 *
 * This is a VISUAL mapping only: it does not model raindrops, drop-size distribution or any physics.
 * The classes follow the common hourly-intensity wording (light / moderate / heavy / very heavy) and are
 * used for labelling and for how dense and fast the rain overlay looks — nothing else in the system.
 */
export type RainfallClass = 'NONE' | 'LIGHT' | 'MODERATE' | 'HEAVY' | 'VERY HEAVY'

/** Upper bounds (mm/hr, inclusive) of the display classes. */
export const RAINFALL_CLASS_BOUNDS: { max: number; label: RainfallClass }[] = [
  { max: 0, label: 'NONE' },
  { max: 2.5, label: 'LIGHT' },
  { max: 7.6, label: 'MODERATE' },
  { max: 15, label: 'HEAVY' },
  { max: Number.POSITIVE_INFINITY, label: 'VERY HEAVY' },
]

/** Intensity (mm/hr) at which the rain overlay reaches its maximum density (display only). */
export const RAIN_VISUAL_FULL_SCALE_MM_HR = 30

export interface RainVisual {
  /** Display class of the intensity. */
  label: RainfallClass
  /** 0–1 visual strength used by the overlay and the indicator bar (0 = no rain drawn). */
  intensity: number
  /** Relative fall speed of the overlay (display only). */
  speed: number
}

export function rainfallClass(mmPerHour: number | null | undefined): RainfallClass {
  if (mmPerHour === null || mmPerHour === undefined || !Number.isFinite(mmPerHour) || mmPerHour <= 0) return 'NONE'
  return RAINFALL_CLASS_BOUNDS.find((c) => mmPerHour <= c.max)?.label ?? 'VERY HEAVY'
}

/**
 * Visual parameters for an intensity. The curve is square-root-shaped so light rain is still visible
 * while heavy rain does not saturate the screen; above the full-scale value the overlay stops growing.
 */
export function rainVisual(mmPerHour: number | null | undefined): RainVisual {
  const label = rainfallClass(mmPerHour)
  if (label === 'NONE') return { label, intensity: 0, speed: 0 }
  const value = Math.min(mmPerHour as number, RAIN_VISUAL_FULL_SCALE_MM_HR)
  const normalised = Math.sqrt(value / RAIN_VISUAL_FULL_SCALE_MM_HR)
  return {
    label,
    intensity: Math.min(1, Math.max(0.12, Math.round(normalised * 1000) / 1000)),
    speed: Math.round((0.55 + 0.65 * normalised) * 1000) / 1000,
  }
}
