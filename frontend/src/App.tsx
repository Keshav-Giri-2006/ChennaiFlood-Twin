import { ErrorBoundary } from './components/common/ErrorBoundary'
import { DashboardTabs } from './components/dashboard/DashboardTabs'
import { KpiPanel } from './components/dashboard/KpiPanel'
import { DecisionLayerSync } from './components/decision/DecisionLayerSync'
import { FloodLayerSync } from './components/flood/FloodLayerSync'
import { AssetInspector } from './components/inspector/AssetInspector'
import { Header } from './components/layout/Header'
import { MethodologyDialog } from './components/methodology/MethodologyDialog'
import { ScenarioPanel } from './components/simulation/ScenarioPanel'
import { SimulationControls } from './components/simulation/SimulationControls'
import { TimelineBar } from './components/timeline/TimelineBar'
import { DigitalTwinViewer } from './components/viewer/DigitalTwinViewer'
import { LayerControls } from './components/viewer/LayerControls'
import { ViewerToolbar } from './components/viewer/ViewerToolbar'

export default function App() {
  return (
    <div className="app-shell">
      <Header />
      <DigitalTwinViewer>
        <aside className="sidebar sidebar-left">
          <ErrorBoundary label="Scenario panel">
            <ScenarioPanel />
          </ErrorBoundary>
          <ErrorBoundary label="Simulation controls">
            <SimulationControls />
          </ErrorBoundary>
          <ErrorBoundary label="KPI panel">
            <KpiPanel />
          </ErrorBoundary>
          <ErrorBoundary label="Decision support">
            <DashboardTabs />
          </ErrorBoundary>
        </aside>
        <div className="viewer-overlay-top">
          <ViewerToolbar />
        </div>
        <aside className="sidebar sidebar-right">
          <LayerControls />
          <ErrorBoundary label="Inspector">
            <AssetInspector />
          </ErrorBoundary>
        </aside>
        <div className="bottom-bar">
          <ErrorBoundary label="Timeline">
            <TimelineBar />
          </ErrorBoundary>
        </div>
        <ErrorBoundary label="Flood layer">
          <FloodLayerSync />
        </ErrorBoundary>
        <ErrorBoundary label="Decision layers">
          <DecisionLayerSync />
        </ErrorBoundary>
      </DigitalTwinViewer>
      <MethodologyDialog />
      <footer className="model-note">
        Model note: results are simulation-derived (EPA SWMM 5.2.4, candidate model ward176-hydraulic-reconstructed-v1) on an incomplete drainage network with provisional outfalls. Flood zones,
        exposure, bottlenecks and recommendations are model-derived decision support, not observations. Data: GCC GIS · NASA GPM IMERG · Copernicus DEM GLO-30 · © OpenStreetMap contributors.
      </footer>
    </div>
  )
}
