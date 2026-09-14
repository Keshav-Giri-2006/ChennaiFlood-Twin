import { useEffect } from 'react'
import { useFloodTimeline, useFloodTimeslice } from '../../hooks/queries'
import { useActiveTimeline, usePlayback } from '../../hooks/useTimeline'
import { clampIndex, useFloodStore } from '../../state/floodStore'
import { useSimulationStore } from '../../state/simulationStore'
import type { FeatureCollection, FloodFeatureProperties } from '../../types/gis'
import { useDigitalTwin } from '../viewer/controllerContext'

/**
 * Pushes the backend flood time slice for the active simulation + selected timestamp into Cesium
 * and drives timeline playback. Only the flood layer is updated; static layers are never reloaded.
 */
export function FloodLayerSync() {
  const controller = useDigitalTwin()
  const activeSimulationId = useSimulationStore((s) => s.activeSimulationId)
  const timeline = useFloodTimeline(activeSimulationId)
  const floodSimulationId = useFloodStore((s) => s.simulationId)
  const reset = useFloodStore((s) => s.reset)
  const { entry } = useActiveTimeline()
  usePlayback()

  // Default to the backend-reported peak timestamp when a new simulation becomes active.
  useEffect(() => {
    if (!activeSimulationId) {
      reset(null, null)
      return
    }
    if (timeline.data && timeline.data.simulationId === activeSimulationId && floodSimulationId !== activeSimulationId) {
      reset(activeSimulationId, clampIndex(timeline.data.peakIndex, timeline.data.entries.length))
    }
  }, [activeSimulationId, timeline.data, floodSimulationId, reset])

  const slice = useFloodTimeslice(activeSimulationId, entry)

  useEffect(() => {
    if (!controller) return
    const fc = slice.data as FeatureCollection<FloodFeatureProperties> | undefined
    if (!activeSimulationId) {
      controller.setFloodSlice(null)
      return
    }
    // Only draw a slice that belongs to the currently active simulation (race protection).
    if (!fc || fc.metadata?.simulationId !== activeSimulationId) return
    controller.setFloodSlice(fc)
  }, [controller, activeSimulationId, slice.data])

  return null
}
