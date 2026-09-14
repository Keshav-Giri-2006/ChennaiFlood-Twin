import { useEffect, useMemo } from 'react'
import { useBottleneckGeojson, useBottlenecks, useExposureAssets } from '../../hooks/queries'
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
      <ExposureSync type="buildings" />
      <ExposureSync type="roads" />
    </>
  )
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
