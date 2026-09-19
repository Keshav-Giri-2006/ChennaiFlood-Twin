import { useEffect } from 'react'
import { useModelLayer } from '../../hooks/queries'
import { useViewerStore } from '../../state/viewerStore'
import { useDigitalTwin } from './controllerContext'

/**
 * Loads the SWMM model nodes that give node states a "normal" baseline on the map. The stressed nodes
 * themselves come from the backend flood time slices (FloodLayerSync), so nothing here is derived.
 */
export function SceneSync() {
  const controller = useDigitalTwin()
  const visible = useViewerStore((s) => s.visibility.nodes)
  const nodes = useModelLayer('nodes', visible)

  useEffect(() => {
    if (controller && nodes.data) controller.setModelNodes(nodes.data)
  }, [controller, nodes.data])

  return null
}
