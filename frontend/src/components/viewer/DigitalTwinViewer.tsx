import { useEffect, useRef, useState, type ReactNode } from 'react'
import { gisApi } from '../../api/endpoints'
import { DigitalTwinController } from '../../cesium/DigitalTwinController'
import { useViewerStore, type LayerKey } from '../../state/viewerStore'
import { ControllerContext } from './controllerContext'

/**
 * Creates the Cesium viewer exactly once per mount and exposes its controller.
 * Store changes are pushed to the controller through effects; the viewer itself is never recreated.
 */
export function DigitalTwinViewer({ children }: { children?: ReactNode }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [controller, setController] = useState<DigitalTwinController | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const { setLoadState, select, setRenderError } = useViewerStore.getState()
    const instance = new DigitalTwinController(
      container,
      { layer: (name, signal) => gisApi.layer(name, signal), terrain: (signal) => gisApi.terrain(signal) },
      { onLayerState: setLoadState, onSelect: select, onRenderError: setRenderError },
    )
    // Apply visibility chosen before creation.
    const { visibility, verticalExaggeration } = useViewerStore.getState()
    ;(Object.keys(visibility) as LayerKey[]).forEach((key) => instance.setLayerVisible(key, visibility[key]))
    instance.setVerticalExaggeration(verticalExaggeration)
    setController(instance)
    void instance.loadStaticScene()
    if (import.meta.env.DEV) {
      // Development-only debugging handle; not present in production builds.
      ;(window as unknown as { __digitalTwin?: DigitalTwinController }).__digitalTwin = instance
      console.info('[digital-twin] viewer created')
    }
    return () => {
      instance.destroy()
      setController(null)
      if (import.meta.env.DEV) console.info('[digital-twin] viewer destroyed')
    }
  }, [])

  // Sync viewer/UI state into the scene.
  useEffect(() => {
    if (!controller) return
    let previous = useViewerStore.getState().visibility
    return useViewerStore.subscribe((state) => {
      if (state.visibility !== previous) {
        ;(Object.keys(state.visibility) as LayerKey[]).forEach((key) => {
          if (state.visibility[key] !== previous[key]) controller.setLayerVisible(key, state.visibility[key])
        })
        previous = state.visibility
      }
    })
  }, [controller])

  const floodOpacity = useViewerStore((s) => s.floodOpacity)
  const exaggeration = useViewerStore((s) => s.verticalExaggeration)
  useEffect(() => controller?.setFloodOpacity(floodOpacity), [controller, floodOpacity])
  useEffect(() => controller?.setVerticalExaggeration(exaggeration), [controller, exaggeration])

  return (
    <ControllerContext.Provider value={controller}>
      <div className="viewer-root">
        <div ref={containerRef} className="cesium-container" aria-label="Ward 176 3D Digital Twin viewer" />
        {children}
      </div>
    </ControllerContext.Provider>
  )
}
