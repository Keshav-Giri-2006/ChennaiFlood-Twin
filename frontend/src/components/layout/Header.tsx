import { useScenario, useSimulationStatus } from '../../hooks/queries'
import { useSimulationStore } from '../../state/simulationStore'
import { StatusBadge } from '../common/StatusBadge'

export function Header() {
  const scenarioId = useSimulationStore((s) => s.scenarioId)
  const runningSimulationId = useSimulationStore((s) => s.runningSimulationId)
  const activeSimulationId = useSimulationStore((s) => s.activeSimulationId)
  const scenario = useScenario(scenarioId)
  const status = useSimulationStatus(runningSimulationId ?? activeSimulationId)

  return (
    <header className="app-header">
      <div className="brand">
        <h1>ChennaiFlood-Twin</h1>
        <span className="subtitle">Urban Flood Digital Twin · Ward 176 · Velachery, Chennai</span>
      </div>
      <div className="header-status">
        {scenario.data && <span className="scenario-chip">{scenario.data.name}</span>}
        {status.data && <StatusBadge status={status.data.status} />}
      </div>
    </header>
  )
}
