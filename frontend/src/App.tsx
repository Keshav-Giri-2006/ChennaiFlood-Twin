import { ErrorBoundary } from './components/common/ErrorBoundary'
import { KpiPanel } from './components/dashboard/KpiPanel'
import { FloodLayerSync } from './components/flood/FloodLayerSync'
import { FloodPanel } from './components/flood/FloodPanel'
import { AssetInspector } from './components/inspector/AssetInspector'
import { Header } from './components/layout/Header'
import { ScenarioPanel } from './components/simulation/ScenarioPanel'
import { SimulationControls } from './components/simulation/SimulationControls'
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
          <ErrorBoundary label="Flood panel">
            <FloodPanel />
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
          <ErrorBoundary label="KPI panel">
            <KpiPanel />
          </ErrorBoundary>
          <div className="timeline-placeholder" aria-label="Timeline playback">
            Timeline playback (play / pause / speed) is planned next; step through actual SWMM timestamps in the flood panel.
          </div>
        </div>
        <ErrorBoundary label="Flood layer">
          <FloodLayerSync />
        </ErrorBoundary>
      </DigitalTwinViewer>
      <footer className="model-note">
        Model note: flood outputs are simulation-derived (EPA SWMM 5.2.4, candidate model ward176-hydraulic-reconstructed-v1) and depend on an incomplete drainage network with provisional outfalls, NASA GPM IMERG rainfall, Copernicus DSM terrain and modelling assumptions. Data: GCC GIS · NASA GPM IMERG · Copernicus DEM GLO-30 · © OpenStreetMap contributors.
      </footer>
    </div>
  )
}
