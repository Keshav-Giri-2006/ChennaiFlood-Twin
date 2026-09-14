import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { decisionApi } from '../api/endpoints'
import { stepIntervalMs, useFloodStore } from '../state/floodStore'
import { useSimulationStore } from '../state/simulationStore'
import { useViewerStore } from '../state/viewerStore'
import type { FloodTimeline, FloodTimelineEntry } from '../types/api'
import { floodSliceQuery, queryKeys, useFloodTimeline } from './queries'

/** Number of upcoming time slices preloaded ahead of the playhead. */
export const PRELOAD_AHEAD = 3

export interface ActiveTimeline {
  simulationId: string | null
  timeline: FloodTimeline | undefined
  index: number | null
  entry: FloodTimelineEntry | null
  isPeak: boolean
}

/** The backend timeline of the active simulation and the selected reporting timestamp. */
export function useActiveTimeline(): ActiveTimeline {
  const simulationId = useSimulationStore((s) => s.activeSimulationId)
  const timeline = useFloodTimeline(simulationId)
  const floodSimulationId = useFloodStore((s) => s.simulationId)
  const selectedIndex = useFloodStore((s) => s.selectedIndex)
  const index = timeline.data && floodSimulationId === simulationId ? selectedIndex : null
  const entry = index !== null ? timeline.data?.entries[index] ?? null : null
  return { simulationId, timeline: timeline.data, index, entry, isPeak: index !== null && index === timeline.data?.peakIndex }
}

/** Plain-language state of the selected timestamp, derived only from backend counts (no thresholds). */
export function floodStateLabel(entry: FloodTimelineEntry | null, isPeak: boolean): string {
  if (!entry) return '—'
  if (isPeak) return 'Peak simulated flooding'
  if (entry.floodingNodeCount > 0) return 'Simulated node flooding'
  if (entry.surchargedNodeCount > 0) return 'Surcharge only'
  return 'No simulated flooding'
}

/**
 * Timeline playback driver. Steps through the actual SWMM reporting timestamps only; it never
 * interpolates states. The playhead advances when the next slice is available (preloaded ahead),
 * so slow networks slow playback down instead of skipping hydraulic states.
 */
export function usePlayback(): void {
  const client = useQueryClient()
  const { simulationId, timeline, index } = useActiveTimeline()
  const isPlaying = useFloodStore((s) => s.isPlaying)
  const speed = useFloodStore((s) => s.speed)
  const exposureTimestamps = useViewerStore((s) => (s.visibility.exposureBuildings || s.visibility.exposureRoads) && s.exposureScope === 'timestamp')
  const exposureBuildings = useViewerStore((s) => s.visibility.exposureBuildings)
  const exposureRoads = useViewerStore((s) => s.visibility.exposureRoads)

  // Preload neighbouring slices (and exposure highlights when shown) around the playhead.
  useEffect(() => {
    if (!simulationId || !timeline || index === null) return
    const ahead = isPlaying ? PRELOAD_AHEAD : 1
    for (let k = -1; k <= ahead; k += 1) {
      const e = timeline.entries[index + k]
      if (!e || k === 0) continue
      void client.prefetchQuery(floodSliceQuery(simulationId, e))
      if (exposureTimestamps) {
        const types = [...(exposureBuildings ? (['buildings'] as const) : []), ...(exposureRoads ? (['roads'] as const) : [])]
        for (const type of types) {
          void client.prefetchQuery({
            queryKey: queryKeys.exposureAssets(simulationId, type, e.time),
            queryFn: ({ signal }) => decisionApi.exposureAssets(simulationId, type, e.time, signal),
            staleTime: Infinity,
          })
        }
      }
    }
  }, [client, simulationId, timeline, index, isPlaying, exposureTimestamps, exposureBuildings, exposureRoads])

  useEffect(() => {
    if (!isPlaying || !simulationId || !timeline || index === null) return
    const { pause, selectTimestamp } = useFloodStore.getState()
    if (index >= timeline.entries.length - 1) {
      pause()
      return
    }
    let cancelled = false
    const timer = setTimeout(async () => {
      const next = timeline.entries[index + 1]
      try {
        await client.ensureQueryData(floodSliceQuery(simulationId, next))
      } catch {
        if (!cancelled) pause()
        return
      }
      const state = useFloodStore.getState()
      // Only advance if nothing changed meanwhile (user seek, pause or simulation switch).
      if (!cancelled && state.isPlaying && state.simulationId === simulationId && state.selectedIndex === index) {
        selectTimestamp(simulationId, index + 1)
      }
    }, stepIntervalMs(speed))
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [client, isPlaying, simulationId, timeline, index, speed])
}
