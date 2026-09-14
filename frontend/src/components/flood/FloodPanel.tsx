import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { friendlyErrorMessage } from '../../api/client'
import { FLOOD_CLASS_COLORS, SURCHARGED_COLOR } from '../../cesium/styles'
import { floodSliceQuery, useFloodSummary } from '../../hooks/queries'
import { floodStateLabel, useActiveTimeline } from '../../hooks/useTimeline'
import { useFloodStore } from '../../state/floodStore'
import { useViewerStore } from '../../state/viewerStore'
import type { FloodLegend } from '../../types/api'
import type { FloodFeatureProperties } from '../../types/gis'
import { formatNumber, formatTimestampUtc } from '../../utils/format'
import { EventCharts } from '../charts/EventCharts'
import { useDigitalTwin } from '../viewer/controllerContext'

export function FloodLegendView({ legend }: { legend: FloodLegend }) {
  return (
    <div className="legend" aria-label="Flood legend">
      <p className="legend-title">Simulated node overflow rate (m³/s) — display classes</p>
      <ul>
        <li>
          <span className="swatch swatch-empty" aria-hidden />
          No simulated flooding (no shading)
        </li>
        {legend.overflowClasses.map((c) => (
          <li key={c.class}>
            <span className="swatch" style={{ background: FLOOD_CLASS_COLORS[c.class] }} aria-hidden />
            <strong>{c.class[0] + c.class.slice(1).toLowerCase()}</strong> {formatNumber(c.minExclusiveCms, 3)} – {formatNumber(c.maxInclusiveCms, 3)}
          </li>
        ))}
        <li>
          <span className="swatch" style={{ background: SURCHARGED_COLOR }} aria-hidden />
          Surcharged node (no overflow)
        </li>
      </ul>
      <p className="muted small">{legend.classBasis}</p>
      <p className="muted small">Shaded areas are nearest-node influence zones of overflowing nodes — not flood extent, no depth, not hazard zoning.</p>
    </div>
  )
}

export function FloodPanel() {
  const client = useQueryClient()
  const controller = useDigitalTwin()
  const { simulationId, timeline, index, entry, isPeak } = useActiveTimeline()
  const summary = useFloodSummary(simulationId)
  const opacity = useViewerStore((s) => s.floodOpacity)
  const setOpacity = useViewerStore((s) => s.setFloodOpacity)
  const [peakMessage, setPeakMessage] = useState<string | null>(null)

  if (!simulationId) return <p className="muted">Flood results appear after a simulation has completed.</p>

  /** Explicit user action: select the backend peak timestamp and fly to its overflowing influence zones. */
  const goToPeak = async () => {
    if (!timeline) return
    const { pause, selectTimestamp } = useFloodStore.getState()
    pause()
    selectTimestamp(simulationId, timeline.peakIndex)
    setPeakMessage(null)
    try {
      const fc = await client.fetchQuery(floodSliceQuery(simulationId, timeline.entries[timeline.peakIndex]))
      const zones = fc.features.filter((f) => (f.properties as unknown as FloodFeatureProperties).featureType === 'influenceZone')
      const points = zones.flatMap((f) => (f.geometry.type === 'Polygon' ? f.geometry.coordinates.flat() : f.geometry.type === 'MultiPolygon' ? f.geometry.coordinates.flat(2) : [])).map((p) => [p[0], p[1]] as [number, number])
      if (!controller?.flyToLonLats(points)) setPeakMessage('No overflowing zones at the peak timestamp to frame.')
    } catch (error) {
      setPeakMessage(friendlyErrorMessage(error))
    }
  }

  return (
    <div className="tab-body">
      {(summary.isPending || !timeline) && !summary.isError && <p className="muted">Loading flood results…</p>}
      {summary.isError && <p className="error-text">Flood visualisation unavailable: {friendlyErrorMessage(summary.error)}</p>}
      {timeline && entry && index !== null && (
        <>
          <button type="button" className="primary" onClick={goToPeak}>
            Go to Peak Flood
          </button>
          <p className="muted small">
            Peak from backend: {formatTimestampUtc(timeline.entries[timeline.peakIndex].time)} (highest system overflow rate). Flies the camera to the overflowing influence zones.
          </p>
          {peakMessage && <p className="error-text">{peakMessage}</p>}
          <EventCharts simulationId={simulationId} timeline={timeline} index={index} />
          <dl className="kv">
            <dt>Selected time</dt>
            <dd>
              {formatTimestampUtc(entry.time)} {isPeak && <span className="badge badge-active">peak</span>}
            </dd>
            <dt>State</dt>
            <dd>{floodStateLabel(entry, isPeak)}</dd>
            <dt>Flooding / surcharged nodes</dt>
            <dd>
              {entry.floodingNodeCount} / {entry.surchargedNodeCount}
            </dd>
            <dt>Max node overflow rate</dt>
            <dd>{formatNumber(entry.maxNodeFloodingRateCms, 3)} m³/s</dd>
            <dt>Rainfall at this time</dt>
            <dd>{formatNumber(entry.rainfallMmHr, 2)} mm/hr</dd>
            <dt>Approx. cumulative overflow</dt>
            <dd>
              {formatNumber(entry.approxCumulativeSystemOverflowM3, 0)} m³ <span className="muted small">(model diagnostic)</span>
            </dd>
          </dl>
          <label className="field compact">
            <span>Flood layer opacity {Math.round(opacity * 100)}%</span>
            <input type="range" min={0.1} max={1} step={0.05} value={opacity} onChange={(e) => setOpacity(Number(e.target.value))} />
          </label>
          <FloodLegendView legend={timeline.legend} />
          <p className="muted small">
            Method {timeline.metadata.floodProcessingVersion}. Ground flood depth and extent are not derived: SWMM ran without surface ponding and model/DEM elevations are not vertically consistent.
          </p>
        </>
      )}
    </div>
  )
}
