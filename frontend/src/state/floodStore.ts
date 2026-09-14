import { create } from 'zustand'

export const PLAYBACK_SPEEDS = [0.5, 1, 2, 4] as const
export type PlaybackSpeed = (typeof PLAYBACK_SPEEDS)[number]

/** Wall-clock time per SWMM reporting step at 1× (one 30-minute reporting interval per second). */
export const BASE_STEP_MS = 1000

/**
 * Flood display state: which reporting timestamp of which simulation is selected, and timeline playback.
 * Timestamps themselves always come from the backend timeline; this store only holds an index.
 */
interface FloodState {
  simulationId: string | null
  selectedIndex: number | null
  isPlaying: boolean
  speed: PlaybackSpeed
  selectTimestamp: (simulationId: string, index: number) => void
  reset: (simulationId: string | null, index: number | null) => void
  play: () => void
  pause: () => void
  setSpeed: (speed: PlaybackSpeed) => void
}

export const useFloodStore = create<FloodState>((set, get) => ({
  simulationId: null,
  selectedIndex: null,
  isPlaying: false,
  speed: 1,
  selectTimestamp: (simulationId, index) => set({ simulationId, selectedIndex: index }),
  reset: (simulationId, index) => set({ simulationId, selectedIndex: index, isPlaying: false }),
  play: () => {
    if (get().selectedIndex !== null) set({ isPlaying: true })
  },
  pause: () => set({ isPlaying: false }),
  setSpeed: (speed) => set({ speed }),
}))

/** Clamp an index into the available timestamps; returns null when there are none. */
export function clampIndex(index: number, count: number): number | null {
  if (count <= 0) return null
  return Math.min(count - 1, Math.max(0, Math.round(index)))
}

export function stepIntervalMs(speed: PlaybackSpeed): number {
  return BASE_STEP_MS / speed
}
