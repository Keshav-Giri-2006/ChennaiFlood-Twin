import { friendlyErrorMessage } from '../../api/client'
import { BOTTLENECK_COLORS } from '../../cesium/styles'
import { useBottleneckGeojson, useBottleneckTimeline, useBottlenecks, useKpis } from '../../hooks/queries'
import { useActiveTimeline } from '../../hooks/useTimeline'
import { useSimulationStore } from '../../state/simulationStore'
import { useViewerStore } from '../../state/viewerStore'
import type { Bottleneck } from '../../types/api'
import { formatLitres, formatNumber, formatTimestampUtc } from '../../utils/format'
import { useDigitalTwin } from '../viewer/controllerContext'

const CONCERN: Record<string, string> = { HIGH: 'High diagnostic concern', MODERATE: 'Moderate diagnostic concern', LOW: 'Low diagnostic concern' }

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className="badge sev" style={{ background: BOTTLENECK_COLORS[severity], color: severity === 'LOW' ? '#1f2937' : '#fff' }}>
      {severity}
    </span>
  )
}

export function HydraulicsPanel() {
  const controller = useDigitalTwin()
  const simulationId = useSimulationStore((s) => s.activeSimulationId)
  const list = useBottlenecks(simulationId)
  const geojson = useBottleneckGeojson(simulationId)
  const kpis = useKpis(simulationId)
  const visible = useViewerStore((s) => s.visibility.bottlenecks)
  const setVisible = useViewerStore((s) => s.setVisible)

  if (!simulationId) return <p className="muted">Hydraulic diagnostics appear after a simulation has completed.</p>
  if (list.isPending) return <p className="muted">Loading potential bottlenecks…</p>
  if (list.isError) return <p className="error-text">Bottleneck analysis unavailable: {friendlyErrorMessage(list.error)}</p>

  const doc = list.data
  const viewHotspots = () => {
    setVisible('bottlenecks', true)
    controller?.fitBottlenecks()
  }
  const open = (b: Bottleneck) => {
    setVisible('bottlenecks', true)
    const feature = geojson.data?.features.find((f) => f.id === b.linkId)
    if (feature && controller) {
      controller.flyToGeometries([feature.geometry])
      controller.selectBottleneck(b.linkId)
    }
  }
  const volume = kpis.data?.hydraulics.simulatedFloodingVolume

  return (
    <div className="tab-body">
      <p className="note-box">{doc.terminology}</p>
      <div className="row-actions">
        <label className="inline-toggle">
          <input type="checkbox" checked={visible} onChange={(e) => setVisible('bottlenecks', e.target.checked)} /> Show potential bottlenecks
        </label>
        <button type="button" onClick={viewHotspots} disabled={!geojson.data?.features.length}>
          View Hotspots
        </button>
      </div>
      <BottleneckNow onView={open} bottlenecks={doc.bottlenecks} />
      <p className="kpi-group-title">Whole simulated event</p>
      <dl className="kv">
        <dt>Conduits screened</dt>
        <dd>{doc.summary.conduitsScreened}</dd>
        <dt>Potential bottlenecks</dt>
        <dd>
          {doc.summary.potentialBottlenecks} ({doc.summary.bySeverity.HIGH} high · {doc.summary.bySeverity.MODERATE} moderate · {doc.summary.bySeverity.LOW} low)
        </dd>
        <dt>In components without outfall</dt>
        <dd>
          {doc.summary.inComponentsWithoutOutfall} <span className="muted small">(capped at low concern)</span>
        </dd>
        <dt>Network components</dt>
        <dd>
          {doc.summary.modelComponents} in the model graph, {doc.summary.modelComponentsWithOutfall} reach a provisional outfall
        </dd>
      </dl>

      <div className="legend" aria-label="Bottleneck legend">
        <ul>
          {doc.legend.map((l) => (
            <li key={l.severity}>
              <span className="swatch" style={{ background: BOTTLENECK_COLORS[l.severity] }} aria-hidden />
              {l.label}
            </li>
          ))}
        </ul>
      </div>

      <ul className="item-list" aria-label="Potential bottlenecks">
        {doc.bottlenecks.map((b) => (
          <li key={b.linkId}>
            <button type="button" className="item" onClick={() => open(b)} title={CONCERN[b.severity]}>
              <span className="item-head">
                <SeverityBadge severity={b.severity} />
                <strong>{b.linkId}</strong>
                <span className="muted small">GCC ObjectID {String(b.sourceObjectId)}</span>
                <span className="muted small">conf. {b.confidence.toLowerCase()}</span>
              </span>
              <span className="small">{b.reason}</span>
              <span className="muted small">
                criteria {b.criteriaMet}/4 · {b.fromNodeId} → {b.toNodeId}
                {!b.networkContext.componentHasOutfall && ' · component without outfall'}
              </span>
            </button>
          </li>
        ))}
      </ul>

      <details>
        <summary>Numerical diagnostics (not bottlenecks) — {doc.numericalDiagnostics.length}</summary>
        <ul className="plain-list">
          {doc.numericalDiagnostics.map((n) => (
            <li key={n.linkId}>
              <strong>{n.linkId}</strong> <span className="muted small">GCC ObjectID {String(n.sourceObjectId)}</span>
              {n.timeStepCriticalPercent !== null && <> · time-step critical {formatNumber(n.timeStepCriticalPercent, 1)}%</>}
              {n.flowInstabilityIndex !== null && <> · instability index {n.flowInstabilityIndex}</>}
              <br />
              <span className="small">{n.interpretation}</span>
              {n.projectInvestigation && (
                <span className="small muted">
                  <br />
                  Investigation: {n.projectInvestigation.decision} ({n.projectInvestigation.source})
                </span>
              )}
            </li>
          ))}
        </ul>
      </details>

      {volume && volume.value !== null && (
        <p className="small">
          Simulated flooding volume: <strong>{formatLitres(volume.value as number)}</strong>{' '}
          <span className="muted">— a SWMM flooding-loss diagnostic under an incomplete network with provisional outfalls, not an observed flood volume.</span>
        </p>
      )}
      <details>
        <summary>Screening criteria ({doc.bottleneckAnalysisVersion})</summary>
        <dl className="kv">
          {Object.entries(doc.criteriaDefinition).map(([k, v]) => (
            <div key={k} className="kv-row">
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      </details>
    </div>
  )
}

/** Time-aware view: potential bottlenecks hydraulically loaded at the selected SWMM timestamp. */
function BottleneckNow({ bottlenecks, onView }: { bottlenecks: Bottleneck[]; onView: (b: Bottleneck) => void }) {
  const { simulationId, index, entry } = useActiveTimeline()
  const timeline = useBottleneckTimeline(simulationId)
  if (!simulationId || index === null || !entry) return null
  if (timeline.isPending) return <p className="muted small">Loading time-varying hydraulic state…</p>
  if (timeline.isError) {
    return (
      <p className="error-text">
        Time-varying bottleneck state unavailable: {friendlyErrorMessage(timeline.error)}{' '}
        <button type="button" className="link" onClick={() => void timeline.refetch()}>
          Retry
        </button>
      </p>
    )
  }
  const now = timeline.data.entries[index]
  if (!now) return null
  const byId = new Map(bottlenecks.map((b) => [b.linkId, b]))
  return (
    <section className="now-box" aria-label="Hydraulic state at the selected timestamp">
      <p className="kpi-group-title">
        At {formatTimestampUtc(now.time)} <span className="muted small">(follows timeline; SWMM 30-min sample)</span>
      </p>
      <dl className="kv">
        <dt>Active potential bottlenecks</dt>
        <dd>{now.activeCount}</dd>
        <dt>Highest severity</dt>
        <dd>{now.highestSeverity ? <SeverityBadge severity={now.highestSeverity} /> : 'none'}</dd>
        <dt>Most loaded conduit</dt>
        <dd>
          {now.mostLoaded ? (
            <>
              {now.mostLoaded.linkId} · {formatNumber(now.mostLoaded.utilization * 100, 0)}% of full-flow capacity
              {!now.mostLoaded.isPotentialBottleneck && <span className="muted small"> (not a potential bottleneck)</span>}
            </>
          ) : (
            '—'
          )}
        </dd>
      </dl>
      {now.active.length > 0 ? (
        <ul className="item-list" aria-label="Active potential bottlenecks">
          {now.active.map((a) => (
            <li key={a.linkId} className="active-bn">
              <span className="item-head">
                <SeverityBadge severity={a.severity} />
                <strong>{a.linkId}</strong>
                <span className="muted small">GCC ObjectID {String(a.sourceObjectId)}</span>
              </span>
              <span className="small">
                {a.criteria.full ? 'full' : 'not full'}
                {a.utilization !== null && ` · flow ${formatNumber(a.utilization * 100, 0)}% of capacity`}
                {a.floodingNodeIds.length > 0 && ` · ${a.floodingNodeIds.join(', ')} overflowing`}
              </span>
              {byId.has(a.linkId) && (
                <button type="button" className="link" onClick={() => onView(byId.get(a.linkId) as Bottleneck)}>
                  View on map
                </button>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted small">No potential bottleneck is full or above its full-flow capacity at this timestamp.</p>
      )}
    </section>
  )
}
