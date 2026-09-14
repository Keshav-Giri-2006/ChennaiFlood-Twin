import { useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import { useDigitalTwin } from '../components/viewer/controllerContext'
import { useFloodStore } from '../state/floodStore'
import { useSimulationStore } from '../state/simulationStore'
import { useViewerStore } from '../state/viewerStore'
import type { SimulationStatus } from '../types/api'
import { queryKeys } from './queries'

/**
 * Returns the UI to a known demo state: default camera and layers, no selection or temporary
 * highlights, baseline scenario selection, normal opacity and the first timestamp.
 * Nothing on the backend (results, runs, data) is deleted.
 */
export function useResetDemo(): () => void {
  const controller = useDigitalTwin()
  const client = useQueryClient()
  return useCallback(() => {
    const flood = useFloodStore.getState()
    flood.pause()
    flood.setSpeed(1)
    if (flood.simulationId) flood.selectTimestamp(flood.simulationId, 0)
    useViewerStore.getState().reset()
    const sim = useSimulationStore.getState()
    sim.setRainfallMultiplier(1)
    sim.setComparison(null, null)
    if (sim.activeSimulationId && !sim.runningSimulationId) {
      const status = client.getQueryData<SimulationStatus>(queryKeys.simulation(sim.activeSimulationId))
      // Return to the baseline result; the latest completed 1.00x run is selected automatically.
      if ((status?.parameters?.rainfallMultiplier ?? 1) !== 1) sim.setActiveSimulation(null)
    }
    controller?.resetDemo()
  }, [controller, client])
}
