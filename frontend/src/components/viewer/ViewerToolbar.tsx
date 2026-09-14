import { useViewerStore } from '../../state/viewerStore'
import { useDigitalTwin } from './controllerContext'

export function ViewerToolbar() {
  const controller = useDigitalTwin()
  const renderError = useViewerStore((s) => s.renderError)
  const restartViewer = useViewerStore((s) => s.restartViewer)
  return (
    <div className="viewer-toolbar" role="toolbar" aria-label="Camera controls">
      <button type="button" onClick={() => controller?.fitWard()} disabled={!controller}>
        Fit Ward 176
      </button>
      <button type="button" onClick={() => controller?.resetView()} disabled={!controller}>
        Reset view
      </button>
      {renderError && (
        <span className="render-error" role="alert" title={renderError}>
          3D rendering stopped{' '}
          <button type="button" onClick={() => controller?.restartRendering()}>
            Resume rendering
          </button>
          <button type="button" onClick={restartViewer} title="Recreates the 3D viewer and reloads map layers">
            Restart 3D viewer
          </button>
        </span>
      )}
    </div>
  )
}
