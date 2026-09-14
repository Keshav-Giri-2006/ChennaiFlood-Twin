import { useScenario, useSimulationStatus } from '../../hooks/queries'
import { useResetDemo } from '../../hooks/useResetDemo'
import { useSimulationStore } from '../../state/simulationStore'
import { useViewerStore } from '../../state/viewerStore'
import { StatusBadge } from '../common/StatusBadge'
import { BackendStatus } from './BackendStatus'

export function Header() {
  const scenarioId = useSimulationStore((s) => s.scenarioId)
  const runningSimulationId = useSimulationStore((s) => s.runningSimulationId)
  const activeSimulationId = useSimulationStore((s) => s.activeSimulationId)
  const setMethodologyOpen = useViewerStore((s) => s.setMethodologyOpen)
  const scenario = useScenario(scenarioId)
  const status = useSimulationStatus(runningSimulationId ?? activeSimulationId)
  const resetDemo = useResetDemo()

  return (
    <header className="app-header">
      <div className="brand">
        <h1>ChennaiFlood-Twin</h1>
        <span className="subtitle">Urban Flood Digital Twin &amp; Decision Support · Ward 176 · Velachery, Chennai</span>
      </div>
      <div className="header-status">
        <BackendStatus />
        {scenario.data && <span className="scenario-chip">{scenario.data.name}</span>}
        {status.data && <StatusBadge status={status.data.status} />}
        <button type="button" onClick={resetDemo} title="Default camera, layers, timestep and baseline result; no data is deleted">
          Reset demo
        </button>
        <button type="button" onClick={() => setMethodologyOpen(true)}>
          Methodology &amp; Limitations
        </button>
      </div>
    </header>
  )
}
