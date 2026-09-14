import { friendlyErrorMessage } from '../../api/client'
import { useBottlenecks, useExposure, useFloodSummary, useKpis } from '../../hooks/queries'
import { useActiveTimeline } from '../../hooks/useTimeline'
import type { Quantity } from '../../types/api'
import { formatNumber, formatQuantity, formatTimestampUtc } from '../../utils/format'
import { Panel } from '../common/Panel'

interface CardProps {
  label: string
  value: string
  hint?: string
  live?: boolean
  unavailable?: boolean
}

function Card({ label, value, hint, live, unavailable }: CardProps) {
  return (
    <div className={`kpi-card${live ? ' kpi-live' : ''}${unavailable ? ' kpi-unavailable' : ''}`} title={hint}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
    </div>
  )
}

const q = (quantity: Quantity | undefined, digits = 3): string => {
  if (!quantity || quantity.value === null) return 'Not available'
  if (typeof quantity.value === 'number' && quantity.unit !== 'L') {
    const unit = { 'm3/s': 'm³/s', count: '', hr: 'h' }[quantity.unit] ?? quantity.unit
    return `${formatNumber(quantity.value, digits)}${unit ? ` ${unit}` : ''}`
  }
  return formatQuantity(quantity)
}

/**
 * Live KPIs: "now" cards follow the selected timeline timestamp; event cards are backend event
 * metrics. Every value comes from the API; only formatting happens here.
 */
export function KpiPanel() {
  const { simulationId, entry, index } = useActiveTimeline()
  const kpis = useKpis(simulationId)
  const flood = useFloodSummary(simulationId)
  const exposure = useExposure(simulationId)
  const bottlenecks = useBottlenecks(simulationId)

  if (!simulationId) {
    return (
      <Panel title="Key indicators">
        <p className="muted">KPIs appear after a simulation has completed.</p>
      </Panel>
    )
  }
  if (kpis.isPending || flood.isPending) {
    return (
      <Panel title="Key indicators">
        <p className="muted">Loading KPIs…</p>
      </Panel>
    )
  }
  if (kpis.isError || flood.isError) {
    return (
      <Panel title="Key indicators">
        <p className="error-text">{friendlyErrorMessage(kpis.error ?? flood.error)}</p>
      </Panel>
    )
  }
  const m = flood.data.metrics
  const exposureNow = index !== null ? exposure.data?.timeline[index] : undefined

  return (
    <Panel title="Key indicators">
      <p className="kpi-group-title">
        At {entry ? formatTimestampUtc(entry.time) : '—'} <span className="muted small">(follows timeline)</span>
      </p>
      <div className="kpi-grid" aria-label="Indicators at the selected timestamp">
        <Card live label="Flooding nodes" value={entry ? formatNumber(entry.floodingNodeCount, 0) : '—'} hint="SWMM nodes with overflow rate > 0 at this reporting timestamp." />
        <Card live label="Surcharged nodes" value={entry ? formatNumber(entry.surchargedNodeCount, 0) : '—'} hint="Nodes above the crown of their highest conduit, without overflow." />
        <Card live label="System overflow" value={entry ? `${formatNumber(entry.systemFloodingRateCms, 3)} m³/s` : '—'} hint="Total simulated node overflow rate (model diagnostic)." />
        <Card
          live
          label="Buildings in influence zones"
          value={exposureNow ? formatNumber(exposureNow.buildingsIntersecting, 0) : exposure.isError ? 'Unavailable' : '—'}
          hint="Model-derived exposure: buildings intersecting flood influence zones of overflowing nodes. Not flooded or damaged buildings."
        />
      </div>
      <p className="kpi-group-title">Simulated event</p>
      <div className="kpi-grid" aria-label="Event indicators">
        <Card label="Total rainfall" value={q(kpis.data.rainfall.total)} hint={kpis.data.rainfall.total?.description ?? undefined} />
        <Card label="Peak rainfall intensity" value={q(kpis.data.rainfall.peakIntensity, 2)} hint={`At ${formatTimestampUtc(kpis.data.rainfall.peakIntensity?.time)}`} />
        <Card label="Peak flooding nodes" value={q(m.peakConcurrentFloodingNodes, 0)} hint={`At ${formatTimestampUtc(m.peakConcurrentFloodingNodes?.time)}`} />
        <Card label="Peak overflow rate" value={q(m.peakSystemFloodingRate, 3)} hint={m.peakSystemFloodingRate?.description ?? undefined} />
        <Card label="Peak flooding time" value={formatTimestampUtc(flood.data.peakTime)} hint="Timestamp of peak system overflow rate (backend-derived)." />
        <Card label="Flooding duration" value={q(m.floodingDuration, 1)} hint={m.floodingDuration?.description ?? undefined} />
        <Card label="Max node water depth" value={q(m.maximumNodeWaterDepth, 2)} hint="In-network SWMM node depth — not a ground flood depth." />
        <Card
          label="Potential bottlenecks"
          value={bottlenecks.data ? `${bottlenecks.data.summary.potentialBottlenecks} (${bottlenecks.data.summary.bySeverity.HIGH} high)` : '—'}
          hint="Model-diagnostic potential bottlenecks (bottleneck-analysis-v1), not confirmed failures."
        />
      </div>
      <p className="muted small">Ground flood depth and flood extent are not derived by this model (see Methodology &amp; Limitations).</p>
    </Panel>
  )
}
