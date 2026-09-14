import { friendlyErrorMessage } from '../../api/client'
import { EXPOSURE_COLORS } from '../../cesium/styles'
import { useExposure } from '../../hooks/queries'
import { useActiveTimeline } from '../../hooks/useTimeline'
import { useViewerStore } from '../../state/viewerStore'
import { formatNumber, formatTimestampUtc } from '../../utils/format'

const pct = (v: number | null) => (v === null ? '' : ` (${formatNumber(v, 1)}%)`)

export function ExposurePanel() {
  const { simulationId, index, entry } = useActiveTimeline()
  const exposure = useExposure(simulationId)
  const visibility = useViewerStore((s) => s.visibility)
  const setVisible = useViewerStore((s) => s.setVisible)
  const scope = useViewerStore((s) => s.exposureScope)
  const setScope = useViewerStore((s) => s.setExposureScope)

  if (!simulationId) return <p className="muted">Model-derived exposure appears after a simulation has completed.</p>
  if (exposure.isPending) return <p className="muted">Loading model-derived exposure…</p>
  if (exposure.isError) return <p className="error-text">Exposure analysis unavailable: {friendlyErrorMessage(exposure.error)}</p>

  const e = exposure.data
  const now = index !== null ? e.timeline[index] : undefined
  const topNodes = e.byNode.slice(0, 6)

  return (
    <div className="tab-body">
      <p className="note-box">{e.terminology}</p>
      <div className="toggles" role="group" aria-label="Exposure layers">
        <label className="inline-toggle">
          <input type="checkbox" checked={visibility.exposureBuildings} onChange={(ev) => setVisible('exposureBuildings', ev.target.checked)} />
          <span className="swatch" style={{ background: EXPOSURE_COLORS.building }} aria-hidden /> Model-derived building exposure
        </label>
        <label className="inline-toggle">
          <input type="checkbox" checked={visibility.exposureRoads} onChange={(ev) => setVisible('exposureRoads', ev.target.checked)} />
          <span className="swatch" style={{ background: EXPOSURE_COLORS.road }} aria-hidden /> Model-derived road exposure
        </label>
        <label className="field compact">
          <span>Highlight scope</span>
          <select value={scope} onChange={(ev) => setScope(ev.target.value as 'timestamp' | 'event')}>
            <option value="timestamp">Selected timestamp (follows timeline)</option>
            <option value="event">Any timestamp of the event</option>
          </select>
        </label>
      </div>

      {now && entry && (
        <>
          <p className="kpi-group-title">At {formatTimestampUtc(entry.time)}</p>
          <dl className="kv">
            <dt>Buildings intersecting zones</dt>
            <dd>
              {formatNumber(now.buildingsIntersecting, 0)} of {formatNumber(e.totals.buildings.count, 0)}
            </dd>
            <dt>Footprint within zones</dt>
            <dd>{formatNumber(now.buildingFootprintAreaM2, 0)} m²</dd>
            <dt>Carriageways intersecting</dt>
            <dd>
              {now.roadsIntersecting} of {e.totals.roads.count} ({formatNumber(now.roadAreaM2, 0)} m²)
            </dd>
          </dl>
        </>
      )}

      <p className="kpi-group-title">Peak ({formatTimestampUtc(e.peak.time)}) and whole event</p>
      <dl className="kv">
        <dt>Buildings — peak</dt>
        <dd>
          {formatNumber(e.peak.buildings.intersectingCount, 0)}
          {pct(e.peak.buildings.percentOfBuildings)}
        </dd>
        <dt>Buildings — any timestamp</dt>
        <dd>
          {formatNumber(e.event.buildings.intersectingCount, 0)}
          {pct(e.event.buildings.percentOfBuildings)}
        </dd>
        <dt>Carriageway area — any timestamp</dt>
        <dd>
          {formatNumber(e.event.roads.areaWithinZonesM2, 0)} m²{pct(e.event.roads.percentOfRoadArea)}
        </dd>
        <dt>Linked to components without outfall</dt>
        <dd>
          {formatNumber(e.event.buildings.intersectingZonesOfNodesWithoutOutfallCount, 0)} of the {formatNumber(e.event.buildings.intersectingCount, 0)} buildings
        </dd>
      </dl>

      <table className="mini-table">
        <caption className="muted small">Overflowing nodes with the most intersecting buildings</caption>
        <thead>
          <tr>
            <th scope="col">Node</th>
            <th scope="col">Buildings</th>
            <th scope="col">Roads</th>
            <th scope="col">Hours</th>
          </tr>
        </thead>
        <tbody>
          {topNodes.map((n) => (
            <tr key={n.nodeId}>
              <td>
                {n.nodeId}
                {!n.componentHasOutfall && (
                  <span className="badge badge-neutral" title="Node's drainage component has no model outfall">
                    no outfall
                  </span>
                )}
              </td>
              <td>{n.buildingsIntersecting}</td>
              <td>{n.roadsIntersecting}</td>
              <td>{formatNumber(n.hoursFloodingSampled, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <details>
        <summary>Definition and limitations ({e.exposureAnalysisVersion})</summary>
        <ul className="plain-list small">
          {Object.values(e.definition).map((d) => (
            <li key={d}>{d}</li>
          ))}
          {e.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </details>
      <p className="muted small">Formal risk scoring is not derived: without ground flood depth or extent, hazard × exposure would not be defensible.</p>
    </div>
  )
}
