import { useQueries } from '@tanstack/react-query'
import { comparisonsApi } from '../../api/endpoints'
import type { Comparison, SimulationStatus, WhatIfSpec } from '../../types/api'
import { formatNumber } from '../../utils/format'

/** Metrics shown in the overview (keys of the backend comparison `metrics`). */
const METRICS: { key: string; label: string; format: (v: number) => string }[] = [
  { key: 'totalRainfall', label: 'Total rainfall', format: (v) => `${formatNumber(v, 1)} mm` },
  { key: 'peakSystemFloodingRate', label: 'Peak overflow rate', format: (v) => `${formatNumber(v, 2)} m³/s` },
  { key: 'simulatedFloodingVolume', label: 'Simulated flooding volume (diagnostic)', format: (v) => `${formatNumber(v / 1_000_000, 1)} ML` },
  { key: 'buildingsExposedPeak', label: 'Buildings in influence zones (peak)', format: (v) => formatNumber(v, 0) },
  { key: 'highPotentialBottlenecks', label: 'High-concern potential bottlenecks', format: (v) => formatNumber(v, 0) },
]

const COLORS = ['#94a3b8', '#38bdf8', '#f472b6', '#facc15', '#a3e635']

/**
 * Baseline vs every stored what-if preset run, using the backend comparison of each pair (the baseline
 * value comes from the same comparison documents). No value is computed here except bar length.
 */
export function ScenarioOverviewChart({ baselineId, runs, whatIf }: { baselineId: string; runs: SimulationStatus[]; whatIf: WhatIfSpec }) {
  const presets = whatIf.presets.filter((p) => p.value !== whatIf.baseline)
  const pairs = presets
    .map((p) => ({ preset: p, run: runs.find((r) => r.parameters?.rainfallMultiplier === p.value) }))
    .filter((p): p is { preset: (typeof presets)[number]; run: SimulationStatus } => Boolean(p.run))

  const results = useQueries({
    queries: pairs.map(({ run }) => ({
      queryKey: ['comparison', baselineId, run.simulationId],
      queryFn: ({ signal }: { signal: AbortSignal }) => comparisonsApi.get(baselineId, run.simulationId, signal),
      retry: false,
      staleTime: Infinity,
    })),
  })

  if (pairs.length === 0) return <p className="muted small">Run or load the what-if presets to see the scenario overview.</p>
  const loaded = results.map((r, i) => ({ pair: pairs[i], data: r.data as Comparison | undefined, isError: r.isError }))
  const ready = loaded.filter((l): l is typeof l & { data: Comparison } => Boolean(l.data))
  if (ready.length === 0) return <p className="muted small">{loaded.some((l) => l.isError) ? 'Scenario overview unavailable for these runs.' : 'Loading scenario overview…'}</p>

  const series = [
    { label: `${whatIf.baseline.toFixed(2)}× baseline`, get: (key: string) => ready[0].data.metrics.find((m) => m.key === key)?.baseline ?? null },
    ...ready.map((l) => ({ label: `${l.pair.preset.value.toFixed(2)}× what-if`, get: (key: string) => l.data.metrics.find((m) => m.key === key)?.scenario ?? null })),
  ]

  return (
    <figure className="scenario-overview" aria-label="Scenario overview chart">
      <div className="overview-legend small">
        {series.map((s, i) => (
          <span key={s.label}>
            <span className="swatch" style={{ background: COLORS[i] }} aria-hidden /> {s.label}
          </span>
        ))}
      </div>
      {METRICS.map((metric) => {
        const values = series.map((s) => s.get(metric.key))
        const max = Math.max(...values.map((v) => v ?? 0))
        return (
          <div key={metric.key} className="overview-metric">
            <p className="overview-label small">{metric.label}</p>
            {series.map((s, i) => {
              const v = values[i]
              return (
                <div key={s.label} className="overview-row" title={`${s.label}: ${v === null ? 'not available' : metric.format(v)}`}>
                  <span className="overview-track">
                    <span className="overview-bar" style={{ width: `${v !== null && max > 0 ? Math.max(1.5, (v / max) * 100) : 0}%`, background: COLORS[i] }} />
                  </span>
                  <span className="overview-value small">{v === null ? '—' : metric.format(v)}</span>
                </div>
              )
            })}
          </div>
        )
      })}
      <figcaption className="muted small">Stored SWMM runs of the same model with scaled historical rainfall; what-if sensitivity, not forecasts. Bars are scaled per metric.</figcaption>
    </figure>
  )
}
