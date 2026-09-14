import { create } from 'zustand'

/** Flood display state: which reporting timestamp of which simulation is selected. */
interface FloodState {
  simulationId: string | null
  selectedIndex: number | null
  selectTimestamp: (simulationId: string, index: number) => void
  reset: (simulationId: string | null, index: number | null) => void
}

export const useFloodStore = create<FloodState>((set) => ({
  simulationId: null,
  selectedIndex: null,
  selectTimestamp: (simulationId, index) => set({ simulationId, selectedIndex: index }),
  reset: (simulationId, index) => set({ simulationId, selectedIndex: index }),
}))

/** Clamp an index into the available timestamps; returns null when there are none. */
export function clampIndex(index: number, count: number): number | null {
  if (count <= 0) return null
  return Math.min(count - 1, Math.max(0, Math.round(index)))
}
