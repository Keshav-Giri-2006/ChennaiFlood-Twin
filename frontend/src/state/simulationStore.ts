import { create } from 'zustand'

/**
 * Simulation selection state. Status/results themselves are server state (TanStack Query);
 * this store only records which scenario/simulation the user is looking at.
 */
interface SimulationState {
  scenarioId: string | null
  /** Rainfall multiplier for the next what-if run (1 = historical baseline). */
  rainfallMultiplier: number
  /** Simulation started from this browser session and still being tracked. */
  runningSimulationId: string | null
  /** Simulation whose results are displayed. */
  activeSimulationId: string | null
  /** Simulations started (not loaded) in this browser session, used to label "Simulated now". */
  sessionRunIds: string[]
  comparisonBaselineId: string | null
  comparisonScenarioId: string | null
  setScenario: (scenarioId: string) => void
  setRainfallMultiplier: (value: number) => void
  startTracking: (simulationId: string, options?: { sessionRun?: boolean }) => void
  finishTracking: (simulationId: string, completed: boolean) => void
  setActiveSimulation: (simulationId: string | null) => void
  setComparison: (baselineId: string | null, scenarioId: string | null) => void
  reset: () => void
}

const INITIAL = {
  rainfallMultiplier: 1,
  runningSimulationId: null,
  activeSimulationId: null,
  comparisonBaselineId: null,
  comparisonScenarioId: null,
}

export const useSimulationStore = create<SimulationState>((set, get) => ({
  scenarioId: null,
  sessionRunIds: [],
  ...INITIAL,
  setScenario: (scenarioId) =>
    set((s) => (s.scenarioId === scenarioId ? s : { scenarioId, activeSimulationId: null, runningSimulationId: null, comparisonBaselineId: null, comparisonScenarioId: null })),
  setRainfallMultiplier: (rainfallMultiplier) => set({ rainfallMultiplier }),
  startTracking: (simulationId, options) =>
    set((s) => ({ runningSimulationId: simulationId, sessionRunIds: options?.sessionRun === false ? s.sessionRunIds : [...s.sessionRunIds, simulationId] })),
  finishTracking: (simulationId, completed) => {
    // Ignore late updates for a simulation that is no longer tracked (race protection).
    if (get().runningSimulationId !== simulationId) return
    set(completed ? { runningSimulationId: null, activeSimulationId: simulationId } : { runningSimulationId: null })
  },
  setActiveSimulation: (activeSimulationId) => set({ activeSimulationId }),
  setComparison: (comparisonBaselineId, comparisonScenarioId) => set({ comparisonBaselineId, comparisonScenarioId }),
  /** Demo reset: keep the scenario catalogue selection, clear run/comparison selection. */
  reset: () => set({ ...INITIAL }),
}))
