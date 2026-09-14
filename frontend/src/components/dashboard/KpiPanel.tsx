import { friendlyErrorMessage } from '../../api/client'
import { useKpis } from '../../hooks/queries'
import { useSimulationStore } from '../../state/simulationStore'
import type { KpiResponse, Quantity } from '../../types/api'
import { formatQuantity, sourceLabel } from '../../utils/format'

const CARDS: { group: keyof Pick<KpiResponse, 'rainfall' | 'flood' | 'hydraulics' | 'drainage'>; key: string; label: string }[] = [
  { group: 'rainfall', key: 'total', label: 'Total rainfall' },
  { group: 'rainfall', key: 'peakIntensity', label: 'Peak intensity' },
  { group: 'flood', key: 'peakConcurrentFloodingNodes', label: 'Peak overflowing nodes' },
  { group: 'drainage', key: 'floodedNodes', label: 'Nodes with overflow (event)' },
  { group: 'hydraulics', key: 'simulatedFloodingVolume', label: 'Simulated flooding volume' },
  { group: 'flood', key: 'maximumDepth', label: 'Max ground flood depth' },
]

function Card({ label, quantity }: { label: string; quantity: Quantity | undefined }) {
  const unavailable = !quantity || quantity.value === null
  return (
    <div className={`kpi-card${unavailable ? ' kpi-unavailable' : ''}`} title={quantity?.reason ?? quantity?.description ?? undefined}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{formatQuantity(quantity)}</span>
      <span className="kpi-source">{unavailable ? 'Not derived' : sourceLabel(quantity?.source)}</span>
    </div>
  )
}

export function KpiPanel() {
  const activeSimulationId = useSimulationStore((s) => s.activeSimulationId)
  const kpis = useKpis(activeSimulationId)
  if (!activeSimulationId) return <div className="kpi-strip muted">KPIs appear after a simulation has completed.</div>
  if (kpis.isPending) return <div className="kpi-strip muted">Loading KPIs…</div>
  if (kpis.isError) return <div className="kpi-strip error-text">{friendlyErrorMessage(kpis.error)}</div>
  return (
    <div className="kpi-strip" aria-label="Key performance indicators">
      {CARDS.map((c) => (
        <Card key={`${c.group}.${c.key}`} label={c.label} quantity={kpis.data[c.group][c.key]} />
      ))}
    </div>
  )
}
