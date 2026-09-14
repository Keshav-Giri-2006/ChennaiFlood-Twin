import { useEffect, useMemo } from 'react'
import { useBottleneckGeojson, useBottleneckTimeline, useBottlenecks, useComparison, useExposureAssets, useFloodZones } from '../../hooks/queries'
import { useActiveTimeline } from '../../hooks/useTimeline'
import { useSimulationStore } from '../../state/simulationStore'
import { useViewerStore } from '../../state/viewerStore'
import type { BottleneckNodeMarker } from '../../cesium/DigitalTwinController'
import type { ExposureAssetType } from '../../types/api'
import { useDigitalTwin } from '../viewer/controllerContext'

/** Pushes backend potential bottlenecks and model-derived exposure highlights into Cesium. */
export function DecisionLayerSync() {
  const controller = useDigitalTwin()
  const simulationId = useSimulationStore((s) => s.activeSimulationId)
  const geojson = useBottleneckGeojson(simulationId)
  const list = useBottlenecks(simulationId)

  const nodes = useMemo<BottleneckNodeMarker[]>(() => {
    const seen = new Map<string, BottleneckNodeMarker>()
    for (const b of list.data?.bottlenecks ?? []) {
      const flooding = new Set(b.criteria.find((c) => c.id === 'S1')?.value as string[] | undefined)
      for (const n of b.connectedNodes) {
        if (flooding.has(n.nodeId) && n.location) seen.set(n.nodeId, { nodeId: n.nodeId, lon: n.location[0], lat: n.location[1] })
      }
    }
    return [...seen.values()]
  }, [list.data])

  useEffect(() => {
    if (!controller) return
    if (!simulationId) {
      controller.setBottlenecks(null)
      return
    }
    if (geojson.data?.metadata?.simulationId !== simulationId || list.data?.simulationId !== simulationId) return
    controller.setBottlenecks(geojson.data, nodes)
  }, [controller, simulationId, geojson.data, list.data, nodes])

  return (
    <>
      <BottleneckTimeSync />
      <ExposureSync type="buildings" />
      <ExposureSync type="roads" />
      <ComparisonSync />
    </>
  )
}

/** Restyles potential bottlenecks with the backend state at the selected timestamp (bottleneck-timeline-v1). */
function BottleneckTimeSync() {
  const controller = useDigitalTwin()
  const { simulationId, index } = useActiveTimeline()
  const visible = useViewerStore((s) => s.visibility.bottlenecks)
  const timeline = useBottleneckTimeline(visible ? simulationId : null)

  useEffect(() => {
    if (!controller) return
    const doc = timeline.data
    if (!visible || !doc || doc.simulationId !== simulationId || index === null) {
      controller.setBottleneckTimeState(null)
      return
    }
    const entry = doc.entries[index]
    controller.setBottleneckTimeState(Object.fromEntries((entry?.active ?? []).map((a) => [a.linkId, a.severity])))
  }, [controller, visible, timeline.data, simulationId, index])

  return null
}

/** Categorical comparison layer (both / additional in scenario / baseline only) following the timeline or the whole event. */
function ComparisonSync() {
  const controller = useDigitalTwin()
  const baselineId = useSimulationStore((s) => s.comparisonBaselineId)
  const scenarioId = useSimulationStore((s) => s.comparisonScenarioId)
  const visible = useViewerStore((s) => s.visibility.comparison)
  const scope = useViewerStore((s) => s.comparisonScope)
  const { index } = useActiveTimeline()
  const comparison = useComparison(baselineId, scenarioId)
  const zones = useFloodZones(baselineId, visible && Boolean(comparison.data))

  useEffect(() => {
    if (!controller) return
    const data = comparison.data
    if (!visible || !data || !zones.data) {
      controller.setComparison(zones.data ?? null, null)
      return
    }
    const split = scope === 'timestamp' && index !== null ? data.floodInfluence.timeline[index] : data.floodInfluence.event
    controller.setComparison(zones.data, split ?? data.floodInfluence.event)
  }, [controller, visible, comparison.data, zones.data, scope, index])

  return null
}

function ExposureSync({ type }: { type: ExposureAssetType }) {
  const controller = useDigitalTwin()
  const { simulationId, entry } = useActiveTimeline()
  const visible = useViewerStore((s) => (type === 'buildings' ? s.visibility.exposureBuildings : s.visibility.exposureRoads))
  const scope = useViewerStore((s) => s.exposureScope)
  const time = scope === 'timestamp' ? entry?.time ?? null : null
  const assets = useExposureAssets(simulationId, type, time, visible && (scope === 'event' || entry !== null))

  useEffect(() => {
    if (!controller) return
    const data = assets.data
    const valid = visible && data && data.simulationId === simulationId
    controller.setExposedAssets(type, valid ? data.objectIds : null)
  }, [controller, type, visible, simulationId, assets.data])

  return null
}
