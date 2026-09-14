import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { friendlyErrorMessage, messageForCode } from '../../api/client'
import { queryKeys, useCompletedSimulations, useCreateSimulation, useDemoCatalogue, useLatestCompletedSimulation, useLoadDemo, useSimulationStatus } from '../../hooks/queries'
import { useFloodStore } from '../../state/floodStore'
import { useSimulationStore } from '../../state/simulationStore'
import type { SimulationStatus } from '../../types/api'
import { formatTimestampUtc } from '../../utils/format'
import { multiplierLabel, resultSourceLabel } from '../../utils/resultLabels'
import { Panel } from '../common/Panel'
import { StatusBadge } from '../common/StatusBadge'

const STAGE_LABELS: Record<string, string> = {
  QUEUED: 'Queued',
  VALIDATION: 'Validating model and rainfall',
  WORKSPACE_PREPARATION: 'Preparing isolated workspace',
  SWMM_EXECUTION: 'Running EPA SWMM',
  RESULT_PROCESSING: 'Processing results, flood and decision-support products',
  COMPLETE: 'Complete',
}

export function SimulationControls() {
  const client = useQueryClient()
  const { scenarioId, rainfallMultiplier, runningSimulationId, activeSimulationId, sessionRunIds, startTracking, finishTracking, setActiveSimulation } = useSimulationStore()
  const latest = useLatestCompletedSimulation(scenarioId)
  const running = useSimulationStatus(runningSimulationId)
  const active = useSimulationStatus(activeSimulationId)
  const demos = useDemoCatalogue()
  const create = useCreateSimulation()
  const loadDemo = useLoadDemo()
  const demo = demos.data?.find((d) => d.scenarioId === scenarioId) ?? null
  const completed = useCompletedSimulations(scenarioId)
  // Re-use a stored completed what-if run with the same multiplier instead of re-running SWMM (backend results are immutable per run).
  const storedWhatIf = rainfallMultiplier === 1 ? null : completed.data?.find((r) => r.parameters?.rainfallMultiplier === rainfallMultiplier && r.modelVersion) ?? null

  // Show the most recent completed result for the scenario until the user runs or loads one.
  useEffect(() => {
    if (!activeSimulationId && !runningSimulationId && latest.data) setActiveSimulation(latest.data.simulationId)
  }, [activeSimulationId, runningSimulationId, latest.data, setActiveSimulation])

  const status: SimulationStatus | undefined = running.data
  useEffect(() => {
    if (!status || !runningSimulationId || status.simulationId !== runningSimulationId) return
    if (status.status === 'COMPLETED' || status.status === 'FAILED') {
      finishTracking(status.simulationId, status.status === 'COMPLETED')
      void client.invalidateQueries({ queryKey: queryKeys.latestCompleted(status.scenarioId) })
      void client.invalidateQueries({ queryKey: ['simulations'] })
      void client.invalidateQueries({ queryKey: ['demo'] })
      if (status.status === 'COMPLETED') useFloodStore.getState().pause()
    }
  }, [status, runningSimulationId, finishTracking, client])

  const isActive = Boolean(runningSimulationId) || create.isPending || loadDemo.isPending
  const lastFailed = !runningSimulationId && status?.status === 'FAILED'

  const run = () => {
    if (!scenarioId || isActive) return
    create.mutate({ scenarioId, rainfallMultiplier: rainfallMultiplier === 1 ? undefined : rainfallMultiplier }, { onSuccess: (created) => startTracking(created.simulationId) })
  }

  const load = () => {
    if (!demo || isActive) return
    loadDemo.mutate(demo.demoId, {
      onSuccess: (loaded) => {
        if (loaded.status === 'COMPLETED') {
          setActiveSimulation(loaded.simulationId)
          void client.invalidateQueries({ queryKey: queryKeys.simulation(loaded.simulationId) })
        } else {
          startTracking(loaded.simulationId, { sessionRun: false })
        }
      },
    })
  }

  const runLabel = isActive && !loadDemo.isPending ? 'Running…' : lastFailed ? 'Retry simulation' : rainfallMultiplier === 1 ? 'Run simulation' : `Run ${rainfallMultiplier.toFixed(2)}× what-if simulation`

  return (
    <Panel title="Simulation">
      <div className="button-stack">
        <button type="button" className="primary" onClick={run} disabled={!scenarioId || isActive}>
          {runLabel}
        </button>
        {storedWhatIf && (
          <button type="button" onClick={() => setActiveSimulation(storedWhatIf.simulationId)} disabled={isActive || activeSimulationId === storedWhatIf.simulationId}>
            Load stored {rainfallMultiplier.toFixed(2)}× result
          </button>
        )}
        {demo && (
          <button type="button" onClick={load} disabled={isActive || !demo.available} title={demo.description}>
            {loadDemo.isPending ? 'Loading demo result…' : 'Load verified demo result'}
          </button>
        )}
      </div>
      {demo && !demo.available && <p className="error-text">The verified demo result files are not available on the backend.</p>}
      {create.isError && <p className="error-text">{friendlyErrorMessage(create.error)}</p>}
      {loadDemo.isError && (
        <p className="error-text">
          {friendlyErrorMessage(loadDemo.error)}{' '}
          <button type="button" className="link" onClick={load}>
            Retry
          </button>
        </p>
      )}

      {status && (runningSimulationId === status.simulationId || lastFailed) && (
        <div className="sim-status" aria-live="polite">
          <div className="row">
            <StatusBadge status={status.status} />
            <span>{status.executionMode === 'precomputed-demo' ? 'Loading verified result (SWMM not re-run)' : STAGE_LABELS[status.stage] ?? status.stage}</span>
          </div>
          <div className="progress" role="progressbar" aria-valuenow={status.progress} aria-valuemin={0} aria-valuemax={100}>
            <div style={{ width: `${status.progress}%` }} />
          </div>
          <p className="muted small">Progress reflects backend lifecycle stages, not simulated time.</p>
          {status.error && (
            <p className="error-text">
              {messageForCode(status.error.code, status.error.message)}{' '}
              <button type="button" className="link" onClick={run}>
                Retry
              </button>
            </p>
          )}
        </div>
      )}
      {running.isError && runningSimulationId && <p className="error-text">{friendlyErrorMessage(running.error)}</p>}

      <div className="displayed-result">
        <span className="muted small">Displayed result</span>
        {activeSimulationId ? (
          <>
            <p className="small">
              <strong className={active.data?.executionMode === 'precomputed-demo' ? 'source-demo' : 'source-live'}>{resultSourceLabel(active.data, sessionRunIds)}</strong>
            </p>
            <p className="small">
              {multiplierLabel(active.data)} · <code title={activeSimulationId}>{activeSimulationId.slice(0, 8)}</code>
              {active.data?.completedAt && <> · completed {formatTimestampUtc(active.data.completedAt)}</>}
            </p>
            {active.isError && (
              <p className="error-text">
                {friendlyErrorMessage(active.error)}{' '}
                <button type="button" className="link" onClick={() => void active.refetch()}>
                  Reload result
                </button>
              </p>
            )}
          </>
        ) : (
          <p className="small muted">{latest.isPending ? 'Checking for completed simulations…' : 'No completed simulation yet — load the demo result or run one.'}</p>
        )}
      </div>
    </Panel>
  )
}
