import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { friendlyErrorMessage } from '../../api/client'
import { gisApi } from '../../api/endpoints'
import { queryKeys, useRecommendations } from '../../hooks/queries'
import { useSimulationStore } from '../../state/simulationStore'
import { useViewerStore } from '../../state/viewerStore'
import type { Priority, Recommendation } from '../../types/api'
import type { Geometry } from '../../types/gis'
import { formatNumber } from '../../utils/format'
import { useDigitalTwin } from '../viewer/controllerContext'

const PRIORITIES: Priority[] = ['HIGH', 'MEDIUM', 'LOW']

function metricValue(value: number | string | null, unit: string): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  if (unit === 'L') return `${formatNumber(value / 1_000_000, 3)} million L`
  const label = { 'm3/s': 'm³/s', m2: 'm²', count: '', ratio: '×', attribute: '', hr: 'h' }[unit] ?? unit
  return `${formatNumber(value, 3)}${label ? ` ${label}` : ''}`
}

function RecommendationCard({ rec }: { rec: Recommendation }) {
  const client = useQueryClient()
  const controller = useDigitalTwin()
  const setVisible = useViewerStore((s) => s.setVisible)
  const [message, setMessage] = useState<string | null>(null)

  const showOnMap = async () => {
    if (!controller) return
    setMessage(null)
    try {
      const [conduits, nodes] = await Promise.all([
        client.fetchQuery({ queryKey: queryKeys.modelLayer('conduits'), queryFn: ({ signal }) => gisApi.model('conduits', signal), staleTime: Infinity }),
        client.fetchQuery({ queryKey: queryKeys.modelLayer('nodes'), queryFn: ({ signal }) => gisApi.model('nodes', signal), staleTime: Infinity }),
      ])
      const lines = rec.focus.linkIds.map((id) => conduits.features.find((f) => f.id === id)?.geometry).filter((g): g is Geometry => Boolean(g))
      const points = rec.focus.nodeIds
        .map((id) => nodes.features.find((f) => f.id === id)?.geometry)
        .filter((g): g is Extract<Geometry, { type: 'Point' }> => g?.type === 'Point')
        .map((g) => [g.coordinates[0], g.coordinates[1]] as [number, number])
      if (!controller.focusOn(lines, points)) setMessage('No model geometry is associated with this recommendation.')
      if (rec.relatedBottleneckLinkIds.length) {
        setVisible('bottlenecks', true)
        controller.selectBottleneck(rec.relatedBottleneckLinkIds[0])
      }
    } catch (error) {
      setMessage(friendlyErrorMessage(error))
    }
  }

  return (
    <li className={`rec-card rec-${rec.priority.toLowerCase()}`}>
      <div className="item-head">
        <span className={`badge prio prio-${rec.priority.toLowerCase()}`}>Priority {rec.priority}</span>
        <span className="muted small">Confidence {rec.confidence.toLowerCase()}</span>
        <span className="muted small">
          {rec.rule} · {rec.category.replaceAll('_', ' ').toLowerCase()}
        </span>
      </div>
      <strong className="rec-title">{rec.title}</strong>
      <p className="small">{rec.recommendation}</p>
      <details>
        <summary>Why, evidence and confidence</summary>
        <h4>Why</h4>
        <p className="small">{rec.why}</p>
        <h4>Evidence</h4>
        <dl className="kv">
          {rec.evidence.metrics.map((m, i) => (
            <div key={`${m.label}-${i}`} className="kv-row" title={m.source}>
              <dt>{m.label}</dt>
              <dd>{metricValue(m.value, m.unit)}</dd>
            </div>
          ))}
        </dl>
        {rec.evidence.links.length > 0 && (
          <p className="small">
            <span className="muted">SWMM link → GCC ObjectID: </span>
            {rec.evidence.links.map((l) => `${l.linkId} → ${String(l.sourceObjectId)}`).join(' · ')}
          </p>
        )}
        {rec.evidence.nodes.length > 0 && (
          <p className="small">
            <span className="muted">Model nodes: </span>
            {rec.evidence.nodes.join(', ')}
          </p>
        )}
        <h4>Confidence: {rec.confidence.toLowerCase()}</h4>
        <ul className="plain-list small">
          {(rec.confidenceReasons.length ? rec.confidenceReasons : ['No additional caveat beyond the general model limitations.']).map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </details>
      <div className="row-actions">
        <button type="button" onClick={showOnMap} disabled={!controller}>
          Show on map
        </button>
      </div>
      {message && <p className="error-text">{message}</p>}
    </li>
  )
}

export function RecommendationsPanel() {
  const simulationId = useSimulationStore((s) => s.activeSimulationId)
  const recs = useRecommendations(simulationId)
  const [filter, setFilter] = useState<Priority | 'ALL'>('ALL')

  if (!simulationId) return <p className="muted">Recommendations appear after a simulation has completed.</p>
  if (recs.isPending) return <p className="muted">Loading recommendations…</p>
  if (recs.isError) return <p className="error-text">Recommendations unavailable: {friendlyErrorMessage(recs.error)}</p>

  const doc = recs.data
  const shown = doc.recommendations.filter((r) => filter === 'ALL' || r.priority === filter)

  return (
    <div className="tab-body">
      <p className="note-box">{doc.disclaimer}</p>
      <div className="chips" role="group" aria-label="Filter by priority">
        <button type="button" className={filter === 'ALL' ? 'chip active' : 'chip'} aria-pressed={filter === 'ALL'} onClick={() => setFilter('ALL')}>
          All {doc.summary.total}
        </button>
        {PRIORITIES.map((p) => (
          <button key={p} type="button" className={filter === p ? 'chip active' : 'chip'} aria-pressed={filter === p} onClick={() => setFilter(p)}>
            {p[0] + p.slice(1).toLowerCase()} {doc.summary.byPriority[p]}
          </button>
        ))}
      </div>
      <ul className="rec-list" aria-label="Recommendations">
        {shown.map((r) => (
          <RecommendationCard key={r.id} rec={r} />
        ))}
      </ul>
      <details>
        <summary>Rules ({doc.decisionSupportVersion})</summary>
        <dl className="kv">
          {Object.entries(doc.rules).map(([k, v]) => (
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
