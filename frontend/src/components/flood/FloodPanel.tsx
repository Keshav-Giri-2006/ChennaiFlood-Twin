import { friendlyErrorMessage } from '../../api/client'
import { FLOOD_CLASS_COLORS, SURCHARGED_COLOR } from '../../cesium/styles'
import { useFloodSummary, useFloodTimeline, useFloodTimeslice } from '../../hooks/queries'
import { clampIndex, useFloodStore } from '../../state/floodStore'
import { useSimulationStore } from '../../state/simulationStore'
import { useViewerStore } from '../../state/viewerStore'
import type { FloodLegend } from '../../types/api'
import { formatNumber, formatTimestampUtc } from '../../utils/format'
import { Panel } from '../common/Panel'

export function FloodLegendView({ legend }: { legend: FloodLegend }) {
  return (
    <div className="legend" aria-label="Flood legend">
      <p className="legend-title">Simulated node overflow rate (m³/s)</p>
      <ul>
        {legend.overflowClasses.map((c) => (
          <li key={c.class}>
            <span className="swatch" style={{ background: FLOOD_CLASS_COLORS[c.class] }} aria-hidden />
            <strong>{c.class}</strong> {formatNumber(c.minExclusiveCms, 3)} – {formatNumber(c.maxInclusiveCms, 3)}
          </li>
        ))}
        <li>
          <span className="swatch" style={{ background: SURCHARGED_COLOR }} aria-hidden />
          <strong>SURCHARGED</strong> node (no overflow)
        </li>
      </ul>
      <p className="muted small">{legend.classBasis}</p>
      <p className="muted small">Shaded areas are nearest-node influence zones of overflowing nodes — not flood extent, no depth.</p>
    </div>
  )
}

export function FloodPanel() {
  const activeSimulationId = useSimulationStore((s) => s.activeSimulationId)
  const summary = useFloodSummary(activeSimulationId)
  const timeline = useFloodTimeline(activeSimulationId)
  const { simulationId, selectedIndex, selectTimestamp } = useFloodStore()
  const opacity = useViewerStore((s) => s.floodOpacity)
  const setOpacity = useViewerStore((s) => s.setFloodOpacity)

  const entries = timeline.data?.entries ?? []
  const index = simulationId === activeSimulationId ? selectedIndex : null
  const entry = index !== null ? entries[index] ?? null : null
  const slice = useFloodTimeslice(activeSimulationId, entry)

  const step = (delta: number) => {
    if (!activeSimulationId || index === null) return
    const next = clampIndex(index + delta, entries.length)
    if (next !== null) selectTimestamp(activeSimulationId, next)
  }

  if (!activeSimulationId) {
    return (
      <Panel title="Simulated flood">
        <p className="muted">Flood results appear after a simulation has completed.</p>
      </Panel>
    )
  }

  return (
    <Panel title="Simulated flood (model-derived)">
      {(summary.isPending || timeline.isPending) && <p className="muted">Loading flood results…</p>}
      {(summary.isError || timeline.isError) && <p className="error-text">Flood visualisation unavailable: {friendlyErrorMessage(summary.error ?? timeline.error)}</p>}
      {timeline.data && entry && (
        <>
          <div className="time-selector">
            <button type="button" onClick={() => step(-1)} disabled={index === 0} aria-label="Previous timestamp">
              ◀
            </button>
            <input
              type="range"
              min={0}
              max={entries.length - 1}
              value={index ?? 0}
              onChange={(e) => selectTimestamp(activeSimulationId, Number(e.target.value))}
              aria-label="Simulation timestamp"
            />
            <button type="button" onClick={() => step(1)} disabled={index === entries.length - 1} aria-label="Next timestamp">
              ▶
            </button>
          </div>
          <p className="timestamp">
            {formatTimestampUtc(entry.time)}
            {index === timeline.data.peakIndex && <span className="badge badge-active">peak</span>}
            <span className="muted small"> · step {(index ?? 0) + 1}/{entries.length}</span>
          </p>
          <button type="button" className="link" onClick={() => selectTimestamp(activeSimulationId, timeline.data.peakIndex)}>
            Jump to peak system flooding
          </button>
          <dl className="kv">
            <dt>Overflowing nodes</dt>
            <dd>{entry.floodingNodeCount}</dd>
            <dt>Surcharged nodes</dt>
            <dd>{entry.surchargedNodeCount}</dd>
            <dt>System overflow rate</dt>
            <dd>{formatNumber(entry.systemFloodingRateCms, 3)} m³/s</dd>
            <dt>Rainfall at this time</dt>
            <dd>{formatNumber(entry.rainfallMmHr, 2)} mm/hr</dd>
          </dl>
          {slice.isFetching && <p className="muted small">Loading time slice…</p>}
          {slice.isError && <p className="error-text">{friendlyErrorMessage(slice.error)}</p>}
          <label className="field compact">
            <span>Flood opacity {Math.round(opacity * 100)}%</span>
            <input type="range" min={0.1} max={1} step={0.05} value={opacity} onChange={(e) => setOpacity(Number(e.target.value))} />
          </label>
          <FloodLegendView legend={timeline.data.legend} />
          <p className="muted small">
            Method {timeline.data.metadata.floodProcessingVersion}. Ground flood depth and extent are not derived: SWMM ran without surface ponding and model/DEM elevations are not vertically consistent.
          </p>
        </>
      )}
    </Panel>
  )
}
