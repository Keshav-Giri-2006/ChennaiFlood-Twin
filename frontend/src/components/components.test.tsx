import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useSimulationStore } from '../state/simulationStore'
import { DEFAULT_VISIBILITY, useViewerStore } from '../state/viewerStore'
import { KpiPanel } from './dashboard/KpiPanel'
import { AssetInspector } from './inspector/AssetInspector'
import { LayerControls } from './viewer/LayerControls'

// cesium is heavy and needs WebGL; components under test only use its constants/types.
vi.mock('cesium', () => ({ Color: { fromCssColorString: () => ({ withAlpha: () => ({}) }) } }))

function withQuery(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('LayerControls', () => {
  beforeEach(() => useViewerStore.setState({ visibility: { ...DEFAULT_VISIBILITY }, loadState: { buildings: { state: 'ready', featureCount: 6428 } } }))

  it('toggles one layer without affecting others and shows load state', () => {
    render(<LayerControls />)
    expect(screen.getByText('6,428')).toBeTruthy()
    fireEvent.click(screen.getByLabelText('Storm-water drains'))
    const v = useViewerStore.getState().visibility
    expect(v.drains).toBe(false)
    expect(v.buildings).toBe(true)
  })
})

describe('AssetInspector', () => {
  it('separates source ObjectID from model link IDs and does not number-format identifiers', () => {
    useViewerStore.setState({
      selection: {
        layer: 'drains',
        id: '5902',
        properties: { objectId: 5902, modelLinkIds: ['C162'], inHydraulicModel: true, zone: 'N13', ward: '176', widthM: 1.13, dataQuality: [] },
      },
    })
    render(<AssetInspector />)
    expect(screen.getByText('Source attributes (GCC GIS)')).toBeTruthy()
    expect(screen.getByText('Model representation (SWMM)')).toBeTruthy()
    expect(screen.getByText('5902')).toBeTruthy()
    expect(screen.getByText('C162')).toBeTruthy()
  })
})

describe('KpiPanel', () => {
  it('renders backend KPIs and marks underived flood depth as not available (never 0)', async () => {
    useSimulationStore.setState({ activeSimulationId: 'sim-1' })
    const kpis = {
      simulationId: 'sim-1',
      rainfall: { total: { value: 282.835, unit: 'mm', source: 'source' }, peakIntensity: { value: 23.35, unit: 'mm/hr', source: 'source' } },
      flood: { maximumDepth: { value: null, unit: 'm', source: 'model-derived', available: false, reason: 'not derived' }, peakConcurrentFloodingNodes: { value: 19, unit: 'count', source: 'model-derived' } },
      hydraulics: { simulatedFloodingVolume: { value: 197876000, unit: 'L', source: 'model-derived' } },
      drainage: { floodedNodes: { value: 22, unit: 'count', source: 'model-derived' } },
      modelDiagnostics: {},
      metadata: {},
    }
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(kpis), { status: 200 })))
    render(withQuery(<KpiPanel />))
    expect(await screen.findByText('282.835 mm')).toBeTruthy()
    expect(screen.getByText('197.876 million L')).toBeTruthy()
    expect(screen.getByText('Not available')).toBeTruthy()
    expect(screen.queryByText('0 m')).toBeNull()
  })
})
