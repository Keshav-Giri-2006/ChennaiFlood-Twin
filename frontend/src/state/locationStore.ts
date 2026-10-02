import { create } from 'zustand'

/** A map position picked by the user (WGS 84). `insideStudyArea` is a UI pre-check; the backend decides. */
export interface SelectedLocation {
  latitude: number
  longitude: number
  /** null when the ward boundary was not loaded yet, so the pre-check could not run. */
  insideStudyArea: boolean | null
}

/**
 * Location Flood Check UI state: one selected location (never more than one pin), whether the user asked
 * for the check, and the simulation this panel started. Results are server state (TanStack Query).
 */
interface LocationState {
  location: SelectedLocation | null
  /** The user asked for a check; it is evaluated against the displayed completed simulation. */
  checkRequested: boolean
  /** Simulation started by "Run Location Flood Check" (for its running/failed state). */
  runSimulationId: string | null
  /** Place the pin, or move the existing one. */
  setLocation: (location: SelectedLocation) => void
  clearLocation: () => void
  requestCheck: (runSimulationId?: string | null) => void
  reset: () => void
}

const INITIAL = { location: null, checkRequested: false, runSimulationId: null }

export const useLocationStore = create<LocationState>((set) => ({
  ...INITIAL,
  setLocation: (location) => set({ location }),
  clearLocation: () => set({ ...INITIAL }),
  requestCheck: (runSimulationId) => set((s) => ({ checkRequested: true, runSimulationId: runSimulationId === undefined ? s.runSimulationId : runSimulationId })),
  reset: () => set({ ...INITIAL }),
}))
