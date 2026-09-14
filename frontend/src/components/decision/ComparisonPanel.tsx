import { useEffect, useMemo } from 'react'
import { friendlyErrorMessage } from '../../api/client'
import { COMPARISON_COLORS } from '../../cesium/styles'
import { useComparison, useCompletedSimulations, useCreateSimulation, useScenario } from '../../hooks/queries'
import { useSimulationStore } from '../../state/simulationStore'
import { useViewerStore } from '../../state/viewerStore'
import type { ComparisonMetric, SimulationStatus } from '../../types/api'
import { formatNumber, formatTimestampUtc } from '../../utils/format'
import { ScenarioOverviewChart } from '../charts/ScenarioOverviewChart'
import { SeverityBadge } from './HydraulicsPanel'

const UNIT: Record<string, string> = { 'm3/s': 'm³/s', m2: 'm²', count: '', hr: 'h' }

function runLabel(s: SimulationStatus): string {
  const m = s.parameters?.rainfallMultiplier ?? 1
  const kind = s.executionMode === 'precomputed-demo' ? 'demo result' : m === 1 ? 'baseline' : 'what-if'
  return `${m.toFixed(2)}× ${kind} · ${s.simulationId.slice(0, 8)} · ${formatTimestampUtc(s.completedAt)}`
}

function value(m: ComparisonMetric, v: number): string {
  if (m.unit === 'L') return `${formatNumber(v / 1_000_000, 3)} ML`
  const unit = UNIT[m.unit] ?? m.unit
  return `${formatNumber(v, 3)}${unit ? ` ${unit}` : ''}`
}

function change(m: ComparisonMetric): string {
  if (m.absoluteChange === null) return '—'
  const abs = m.unit === 'L' ? `${formatNumber(m.absoluteChange / 1_000_000, 3)} ML` : formatNumber(m.absoluteChange, 3)
  const sign = m.absoluteChange > 0 ? '+' : ''
  return `${sign}${abs}${m.percentChange !== null ? ` (${m.percentChange > 0 ? '+' : ''}${formatNumber(m.percentChange, 1)}%)` : ''}`
}

/** Baseline vs what-if rainfall scenario comparison (scenario-analysis-v1). All values come from the backend. */
export function ComparisonPanel() {
  const { scenarioId, activeSimulationId, runningSimulationId, comparisonBaselineId, comparisonScenarioId, setComparison, startTracking, setActiveSimulation } = useSimulationStore()
  const scenario = useScenario(scenarioId)
  const runs = useCompletedSimulations(scenarioId)
  const create = useCreateSimulation()
  const comparison = useComparison(comparisonBaselineId, comparisonScenarioId)
  const mapVisible = useViewerStore((s) => s.visibility.comparison)
  const setVisible = useViewerStore((s) => s.setVisible)
  const scope = useViewerStore((s) => s.comparisonScope)
  const setScope = useViewerStore((s) => s.setComparisonScope)

  const list = useMemo(() => runs.data ?? [], [runs.data])
  const baselines = list.filter((r) => (r.parameters?.rainfallMultiplier ?? 1) === 1)
  const whatIfs = list.filter((r) => (r.parameters?.rainfallMultiplier ?? 1) !== 1)

  // Sensible defaults: displayed/demo baseline vs the most recent what-if run.
  useEffect(() => {
    if (!list.length) return
    const baseline = comparisonBaselineId ?? (baselines.find((r) => r.simulationId === activeSimulationId) ?? baselines.find((r) => r.executionMode === 'precomputed-demo') ?? baselines[0])?.simulationId ?? null
    const firstPreset = scenario.data?.whatIf?.presets.find((p) => p.value !== scenario.data?.whatIf?.baseline)?.value
    const what = comparisonScenarioId ?? (whatIfs.find((r) => r.parameters?.rainfallMultiplier === firstPreset) ?? whatIfs[0])?.simulationId ?? null
    if (baseline !== comparisonBaselineId || what !== comparisonScenarioId) setComparison(baseline, what)
  }, [list, baselines, whatIfs, activeSimulationId, comparisonBaselineId, comparisonScenarioId, setComparison, scenario.data])

  const presets = scenario.data?.whatIf?.presets.filter((p) => p.value !== scenario.data?.whatIf?.baseline) ?? []
  const missing = presets.filter((p) => !whatIfs.some((r) => r.parameters?.rainfallMultiplier === p.value))

  if (!scenarioId) return <p className="muted">Select a scenario first.</p>

  return (
    <div className="tab-body">
      <p className="note-box">What-if rainfall sensitivity comparison of model runs. Not a forecast, official warning or climate projection.</p>
      {runs.isError && <p className="error-text">{friendlyErrorMessage(runs.error)}</p>}
      <label className="field compact">
        <span>Baseline</span>
        <select value={comparisonBaselineId ?? ''} onChange={(e) => setComparison(e.target.value || null, comparisonScenarioId)}>
          <option value="">Select a completed baseline run</option>
          {baselines.map((r) => (
            <option key={r.simulationId} value={r.simulationId}>
              {runLabel(r)}
            </option>
          ))}
        </select>
      </label>
      <label className="field compact">
        <span>Scenario B (rainfall multiplier)</span>
        <select value={comparisonScenarioId ?? ''} onChange={(e) => setComparison(comparisonBaselineId, e.target.value || null)}>
          <option value="">Select a completed what-if run</option>
          {whatIfs.map((r) => (
            <option key={r.simulationId} value={r.simulationId}>
              {runLabel(r)}
            </option>
          ))}
        </select>
      </label>
      {missing.length > 0 && (
        <div className="row-actions">
          {missing.map((p) => (
            <button
              key={p.value}
              type="button"
              disabled={Boolean(runningSimulationId) || create.isPending}
              onClick={() => create.mutate({ scenarioId, rainfallMultiplier: p.value }, { onSuccess: (created) => startTracking(created.simulationId) })}
              title="Runs SWMM on an isolated copy of the model with scaled rainfall"
            >
              Run {p.value.toFixed(2)}× what-if simulation
            </button>
          ))}
        </div>
      )}
      {runningSimulationId && <p className="muted small">A simulation is running; it appears here when completed.</p>}
      {create.isError && <p className="error-text">{friendlyErrorMessage(create.error)}</p>}

      {comparisonBaselineId && scenario.data?.whatIf && (
        <>
          <h4 className="kpi-group-title">Scenario overview</h4>
          <ScenarioOverviewChart baselineId={comparisonBaselineId} runs={whatIfs} whatIf={scenario.data.whatIf} />
          <h4 className="kpi-group-title">Detailed comparison</h4>
        </>
      )}

      {comparison.isPending && comparisonBaselineId && comparisonScenarioId && <p className="muted">Comparing results…</p>}
      {comparison.isError && (
        <p className="error-text">
          {friendlyErrorMessage(comparison.error)}{' '}
          <button type="button" className="link" onClick={() => void comparison.refetch()}>
            Retry
          </button>
        </p>
      )}
      {comparison.data && (
        <>
          <div className="row-actions">
            <button type="button" onClick={() => setActiveSimulation(comparison.data.baseline.simulationId)} disabled={activeSimulationId === comparison.data.baseline.simulationId}>
              Show baseline result
            </button>
            <button type="button" onClick={() => setActiveSimulation(comparison.data.scenario.simulationId)} disabled={activeSimulationId === comparison.data.scenario.simulationId}>
              Show scenario result
            </button>
          </div>
          {comparison.data.statements.length > 0 && (
            <ul className="plain-list small statements">
              {comparison.data.statements.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          )}
          <div className="table-scroll">
            <table className="mini-table compare-table">
              <thead>
                <tr>
                  <th scope="col">Metric</th>
                  <th scope="col">Baseline</th>
                  <th scope="col">Scenario</th>
                  <th scope="col">Change</th>
                </tr>
              </thead>
              <tbody>
                {comparison.data.metrics.map((m) => (
                  <tr key={m.key}>
                    <td>{m.label}</td>
                    <td>{value(m, m.baseline)}</td>
                    <td>{value(m, m.scenario)}</td>
                    <td className={m.absoluteChange ? (m.absoluteChange > 0 ? 'up' : 'down') : undefined}>{change(m)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h4 className="kpi-group-title">Flood influence on the map</h4>
          <label className="inline-toggle">
            <input type="checkbox" checked={mapVisible} onChange={(e) => setVisible('comparison', e.target.checked)} /> Show comparison layer
          </label>
          <label className="field compact">
            <span>Comparison scope</span>
            <select value={scope} onChange={(e) => setScope(e.target.value as 'event' | 'timestamp')}>
              <option value="event">Any timestamp of the event</option>
              <option value="timestamp">Selected timestamp (follows timeline)</option>
            </select>
          </label>
          <div className="legend" aria-label="Comparison legend">
            <ul>
              <li>
                <span className="swatch" style={{ background: COMPARISON_COLORS.scenarioOnly }} aria-hidden /> Additional model-derived flood influence (scenario only):{' '}
                {comparison.data.floodInfluence.event.scenarioOnly.join(', ') || 'none'}
              </li>
              <li>
                <span className="swatch" style={{ background: COMPARISON_COLORS.both }} aria-hidden /> Influence in both runs ({comparison.data.floodInfluence.event.both.length} nodes)
              </li>
              <li>
                <span className="swatch" style={{ background: COMPARISON_COLORS.baselineOnly }} aria-hidden /> Baseline only: {comparison.data.floodInfluence.event.baselineOnly.join(', ') || 'none'}
              </li>
            </ul>
            <p className="muted small">{comparison.data.floodInfluence.sharedScale.note}</p>
          </div>

          <h4 className="kpi-group-title">Potential bottlenecks</h4>
          <ul className="plain-list small">
            {comparison.data.bottlenecks.new.map((b) => (
              <li key={`n-${b.linkId}`}>
                <span className="badge badge-danger">New</span> {b.linkId} (GCC {String(b.sourceObjectId)}) <SeverityBadge severity={b.scenarioSeverity} />
              </li>
            ))}
            {comparison.data.bottlenecks.persisting
              .filter((b) => b.change !== 'unchanged' || b.scenarioSeverity === 'HIGH')
              .map((b) => (
                <li key={`p-${b.linkId}`}>
                  <span className="badge badge-neutral">Persisting</span> {b.linkId} <SeverityBadge severity={b.baselineSeverity} /> → <SeverityBadge severity={b.scenarioSeverity} /> {b.change !== 'unchanged' && <em>({b.change})</em>}
                </li>
              ))}
            {comparison.data.bottlenecks.notFlaggedInScenario.map((b) => (
              <li key={`r-${b.linkId}`}>
                <span className="badge badge-success">Reduced</span> {b.linkId} not flagged in the scenario (baseline {b.baselineSeverity.toLowerCase()})
              </li>
            ))}
            <li className="muted">
              {comparison.data.bottlenecks.persisting.filter((b) => b.change === 'unchanged' && b.scenarioSeverity !== 'HIGH').length} other persisting potential bottlenecks unchanged
            </li>
          </ul>

          <h4 className="kpi-group-title">Model-derived exposure</h4>
          <dl className="kv">
            <dt>Buildings (any timestamp)</dt>
            <dd>
              {comparison.data.exposure.buildingsEvent.baseline} → {comparison.data.exposure.buildingsEvent.scenario} (+{comparison.data.exposure.buildingsEvent.additionalInScenario} additional)
            </dd>
            <dt>Buildings (peak timestamp)</dt>
            <dd>
              {comparison.data.exposure.buildingsPeak.baseline} → {comparison.data.exposure.buildingsPeak.scenario}
            </dd>
            <dt>Carriageway area</dt>
            <dd>
              {formatNumber(comparison.data.exposure.roadAreaEventM2.baseline, 0)} → {formatNumber(comparison.data.exposure.roadAreaEventM2.scenario, 0)} m²
            </dd>
          </dl>
          <p className="muted small">{comparison.data.exposure.terminology}</p>

          <h4 className="kpi-group-title">Recommendations</h4>
          <ul className="plain-list small">
            {comparison.data.recommendations.new.map((r) => (
              <li key={r.id}>
                <span className="badge badge-danger">New</span> <span className={`badge prio prio-${r.scenarioPriority.toLowerCase()}`}>{r.scenarioPriority}</span> {r.title}
              </li>
            ))}
            {comparison.data.recommendations.persisting
              .filter((r) => r.change !== 'unchanged')
              .map((r) => (
                <li key={r.id}>
                  <span className="badge badge-neutral">Changed</span> {r.title}: {r.baselinePriority} → {r.scenarioPriority}
                </li>
              ))}
            {comparison.data.recommendations.notTriggeredInScenario.map((r) => (
              <li key={r.id}>
                <span className="badge badge-success">Not triggered</span> {r.title}
              </li>
            ))}
            <li className="muted">{comparison.data.recommendations.persisting.filter((r) => r.change === 'unchanged').length} recommendations persist unchanged</li>
          </ul>
          <p className="muted small">{comparison.data.recommendations.note}</p>
          <details>
            <summary>Limitations ({comparison.data.scenarioAnalysisVersion})</summary>
            <ul className="plain-list small">
              {comparison.data.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </div>
  )
}
