import { useEffect } from 'react'
import { useFloodTimeline, useFloodTimeslice } from '../../hooks/queries'
import { clampIndex, useFloodStore } from '../../state/floodStore'
import { useSimulationStore } from '../../state/simulationStore'
import type { FeatureCollection, FloodFeatureProperties } from '../../types/gis'
import { useDigitalTwin } from '../viewer/controllerContext'

/** Pushes the backend flood time slice for the active simulation + selected timestamp into Cesium. */
export function FloodLayerSync() {
  const controller = useDigitalTwin()
  const activeSimulationId = useSimulationStore((s) => s.activeSimulationId)
  const timeline = useFloodTimeline(activeSimulationId)
  const { simulationId: floodSimulationId, selectedIndex, reset } = useFloodStore()

  // Default to the backend-reported peak timestamp when a new simulation becomes active.
  useEffect(() => {
    if (!activeSimulationId) {
      reset(null, null)
      return
    }
    if (timeline.data && floodSimulationId !== activeSimulationId) {
      reset(activeSimulationId, clampIndex(timeline.data.peakIndex, timeline.data.entries.length))
    }
  }, [activeSimulationId, timeline.data, floodSimulationId, reset])

  const entry =
    timeline.data && floodSimulationId === activeSimulationId && selectedIndex !== null ? timeline.data.entries[selectedIndex] ?? null : null
  const slice = useFloodTimeslice(activeSimulationId, entry)

  useEffect(() => {
    if (!controller) return
    const fc = slice.data as FeatureCollection<FloodFeatureProperties> | undefined
    // Only draw a slice that belongs to the currently active simulation (race protection).
    if (!activeSimulationId || !fc || fc.metadata?.simulationId !== activeSimulationId) {
      if (!activeSimulationId) controller.setFloodSlice(null)
      return
    }
    controller.setFloodSlice(fc)
  }, [controller, activeSimulationId, slice.data])

  return null
}
