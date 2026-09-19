import { rainVisual } from '../../cesium/rainfall'
import { useActiveTimeline } from '../../hooks/useTimeline'
import { useViewerStore } from '../../state/viewerStore'

/**
 * Rainfall visualisation: a screen-space overlay above the 3D scene whose density and fall speed follow
 * the simulated rainfall intensity (mm/hr) of the displayed run at the selected timeline timestamp.
 *
 * It is a presentation effect, not a raindrop or atmospheric model. Three GPU-composited CSS layers are
 * used (no element per drop and no per-frame JavaScript); nothing is rendered at 0 mm/hr or when the
 * "Rainfall visualisation" layer is switched off.
 */
export function RainOverlay() {
  const enabled = useViewerStore((s) => s.visibility.rain)
  const { entry } = useActiveTimeline()
  const visual = rainVisual(entry?.rainfallMmHr)
  if (!enabled || visual.intensity <= 0) return null

  // Presentation mapping: stronger rainfall = more opaque layers falling faster.
  const style = {
    '--rain-opacity': String(Math.round((0.18 + 0.38 * visual.intensity) * 100) / 100),
    '--rain-duration': `${Math.round((1.5 / visual.speed) * 100) / 100}s`,
  } as React.CSSProperties

  return (
    <div className="rain-overlay" style={style} aria-hidden data-intensity={visual.intensity}>
      <span className="rain-layer rain-back" />
      <span className="rain-layer rain-mid" />
      <span className="rain-layer rain-front" />
    </div>
  )
}
