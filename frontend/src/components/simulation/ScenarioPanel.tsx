import { useEffect } from 'react'
import { friendlyErrorMessage } from '../../api/client'
import { useScenario, useScenarios } from '../../hooks/queries'
import { useSimulationStore } from '../../state/simulationStore'
import type { WhatIfSpec } from '../../types/api'
import { formatNumber, formatTimestampUtc } from '../../utils/format'
import { Panel } from '../common/Panel'

export function ScenarioPanel() {
  const scenarios = useScenarios()
  const scenarioId = useSimulationStore((s) => s.scenarioId)
  const setScenario = useSimulationStore((s) => s.setScenario)
  const detail = useScenario(scenarioId)

  useEffect(() => {
    if (!scenarioId && scenarios.data?.length) setScenario(scenarios.data[0].scenarioId)
  }, [scenarioId, scenarios.data, setScenario])

  return (
    <Panel title="Rainfall scenario">
      {scenarios.isPending && <p className="muted">Loading scenarios…</p>}
      {scenarios.isError && <p className="error-text">{friendlyErrorMessage(scenarios.error)}</p>}
      {scenarios.data && (
        <label className="field">
          <span>Scenario</span>
          <select value={scenarioId ?? ''} onChange={(e) => setScenario(e.target.value)}>
            {scenarios.data.map((s) => (
              <option key={s.scenarioId} value={s.scenarioId}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
      )}
      {detail.data?.whatIf && <RainfallMultiplierField spec={detail.data.whatIf} />}
      {detail.data && (
        <dl className="kv">
          <dt>Event</dt>
          <dd>{detail.data.event} ({detail.data.rainfallType})</dd>
          <dt>Period</dt>
          <dd>
            {formatTimestampUtc(detail.data.rainfall.startTime)} → {formatTimestampUtc(detail.data.rainfall.endTime)}
          </dd>
          <dt>Total rainfall</dt>
          <dd>{formatNumber(detail.data.rainfall.totalMm, 3)} mm</dd>
          <dt>Peak intensity</dt>
          <dd>
            {formatNumber(detail.data.rainfall.peakMmHr, 2)} mm/hr <span className="muted">at {formatTimestampUtc(detail.data.rainfall.peakIntervalStart)}</span>
          </dd>
          <dt>Resolution</dt>
          <dd>{detail.data.rainfall.intervalMinutes} min, {detail.data.rainfall.records} records</dd>
          <dt>Source</dt>
          <dd>
            {detail.data.source.name} <span className="muted">({detail.data.source.variable})</span>
          </dd>
        </dl>
      )}
      {detail.data?.limitations.length ? <p className="note">{detail.data.limitations[0]}</p> : null}
    </Panel>
  )
}

/** What-if rainfall sensitivity selection (backend-registered presets and range). */
function RainfallMultiplierField({ spec }: { spec: WhatIfSpec }) {
  const value = useSimulationStore((s) => s.rainfallMultiplier)
  const setValue = useSimulationStore((s) => s.setRainfallMultiplier)
  return (
    <div className="what-if">
      <label className="field">
        <span>{spec.label}</span>
        <select value={value} onChange={(e) => setValue(Number(e.target.value))} aria-describedby="what-if-note">
          {spec.presets.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </label>
      <p id="what-if-note" className="note">
        {value === spec.baseline ? 'Historical rainfall as observed by IMERG.' : `What-if rainfall sensitivity scenario: every rainfall intensity × ${value.toFixed(2)}. Not a forecast, warning or climate projection.`}
      </p>
    </div>
  )
}
