import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { friendlyErrorMessage } from '../../api/client'
import { queryKeys, useCreateSimulation, useLatestCompletedSimulation, useSimulationStatus } from '../../hooks/queries'
import { useSimulationStore } from '../../state/simulationStore'
import type { SimulationStatus } from '../../types/api'
import { formatTimestampUtc } from '../../utils/format'
import { Panel } from '../common/Panel'
import { StatusBadge } from '../common/StatusBadge'

const STAGE_LABELS: Record<string, string> = {
  QUEUED: 'Queued',
  VALIDATION: 'Validating model and rainfall',
  WORKSPACE_PREPARATION: 'Preparing isolated workspace',
  SWMM_EXECUTION: 'Running EPA SWMM',
  RESULT_PROCESSING: 'Processing results and flood products',
  COMPLETE: 'Complete',
}

export function SimulationControls() {
  const client = useQueryClient()
  const { scenarioId, runningSimulationId, activeSimulationId, startTracking, finishTracking, setActiveSimulation } = useSimulationStore()
  const latest = useLatestCompletedSimulation(scenarioId)
  const running = useSimulationStatus(runningSimulationId)
  const create = useCreateSimulation()

  // Show the most recent completed result for the scenario until the user runs a new one.
  useEffect(() => {
    if (!activeSimulationId && !runningSimulationId && latest.data) setActiveSimulation(latest.data.simulationId)
  }, [activeSimulationId, runningSimulationId, latest.data, setActiveSimulation])

  const status: SimulationStatus | undefined = running.data
  useEffect(() => {
    if (!status || !runningSimulationId || status.simulationId !== runningSimulationId) return
    if (status.status === 'COMPLETED' || status.status === 'FAILED') {
      finishTracking(status.simulationId, status.status === 'COMPLETED')
      void client.invalidateQueries({ queryKey: queryKeys.latestCompleted(status.scenarioId) })
    }
  }, [status, runningSimulationId, finishTracking, client])

  const isActive = Boolean(runningSimulationId) || create.isPending
  const lastFailed = !runningSimulationId && status?.status === 'FAILED'

  const run = () => {
    if (!scenarioId || isActive) return
    create.mutate({ scenarioId }, { onSuccess: (created) => startTracking(created.simulationId) })
  }

  const buttonLabel = isActive ? 'Running…' : lastFailed ? 'Retry simulation' : 'Run simulation'

  return (
    <Panel title="Simulation">
      <button type="button" className="primary" onClick={run} disabled={!scenarioId || isActive}>
        {buttonLabel}
      </button>
      {create.isError && <p className="error-text">{friendlyErrorMessage(create.error)}</p>}

      {status && (runningSimulationId === status.simulationId || lastFailed) && (
        <div className="sim-status" aria-live="polite">
          <div className="row">
            <StatusBadge status={status.status} />
            <span>{STAGE_LABELS[status.stage] ?? status.stage}</span>
          </div>
          <div className="progress" role="progressbar" aria-valuenow={status.progress} aria-valuemin={0} aria-valuemax={100}>
            <div style={{ width: `${status.progress}%` }} />
          </div>
          <p className="muted small">Progress reflects backend lifecycle stages, not simulated time.</p>
          {status.error && (
            <p className="error-text">
              {status.error.message} <code>{status.error.code}</code>
            </p>
          )}
        </div>
      )}

      <div className="displayed-result">
        <span className="muted small">Displayed result</span>
        {activeSimulationId ? (
          <p className="small">
            Simulation <code title={activeSimulationId}>{activeSimulationId.slice(0, 8)}</code>
            {latest.data?.simulationId === activeSimulationId && <> · completed {formatTimestampUtc(latest.data.completedAt)}</>}
          </p>
        ) : (
          <p className="small muted">{latest.isPending ? 'Checking for completed simulations…' : 'No completed simulation yet — run one.'}</p>
        )}
      </div>
    </Panel>
  )
}
