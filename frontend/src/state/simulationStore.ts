import { create } from 'zustand'

/**
 * Simulation selection state. Status/results themselves are server state (TanStack Query);
 * this store only records which scenario/simulation the user is looking at.
 */
interface SimulationState {
  scenarioId: string | null
  /** Simulation started from this browser session and still being tracked. */
  runningSimulationId: string | null
  /** Simulation whose results are displayed. */
  activeSimulationId: string | null
  setScenario: (scenarioId: string) => void
  startTracking: (simulationId: string) => void
  finishTracking: (simulationId: string, completed: boolean) => void
  setActiveSimulation: (simulationId: string | null) => void
}

export const useSimulationStore = create<SimulationState>((set, get) => ({
  scenarioId: null,
  runningSimulationId: null,
  activeSimulationId: null,
  setScenario: (scenarioId) =>
    set((s) => (s.scenarioId === scenarioId ? s : { scenarioId, activeSimulationId: null, runningSimulationId: null })),
  startTracking: (simulationId) => set({ runningSimulationId: simulationId }),
  finishTracking: (simulationId, completed) => {
    // Ignore late updates for a simulation that is no longer tracked (race protection).
    if (get().runningSimulationId !== simulationId) return
    set(completed ? { runningSimulationId: null, activeSimulationId: simulationId } : { runningSimulationId: null })
  },
  setActiveSimulation: (activeSimulationId) => set({ activeSimulationId }),
}))
