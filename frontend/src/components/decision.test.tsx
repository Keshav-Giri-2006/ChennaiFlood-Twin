import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { floodSliceQuery } from '../hooks/queries'
import { usePlayback } from '../hooks/useTimeline'
import { BASE_STEP_MS, useFloodStore } from '../state/floodStore'
import { useSimulationStore } from '../state/simulationStore'
import { DEFAULT_VISIBILITY, useViewerStore } from '../state/viewerStore'
import { SIM, fakeController, seededClient, sliceFor, timeline, wrap } from '../test/fixtures'
import { KpiPanel } from './dashboard/KpiPanel'
import { AssetInspector } from './inspector/AssetInspector'
import { queryKeys } from '../hooks/queries'
import { ExposurePanel } from './decision/ExposurePanel'
import { HydraulicsPanel } from './decision/HydraulicsPanel'
import { RecommendationsPanel } from './decision/RecommendationsPanel'
import { MethodologyDialog } from './methodology/MethodologyDialog'
import { TimelineBar } from './timeline/TimelineBar'
import { LayerControls } from './viewer/LayerControls'

vi.mock('cesium', () => ({ Color: { fromCssColorString: () => ({ withAlpha: () => ({}) }) } }))

beforeEach(() => {
  useSimulationStore.setState({ scenarioId: 'michaung-2023', activeSimulationId: SIM, runningSimulationId: null })
  useFloodStore.setState({ simulationId: SIM, selectedIndex: 2, isPlaying: false, speed: 1 })
  useViewerStore.setState({ visibility: { ...DEFAULT_VISIBILITY }, dashboardTab: 'flood', exposureScope: 'timestamp', methodologyOpen: false, selection: null })
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('TimelineBar', () => {
  it('shows the backend timestamp, state and counts, and steps through actual timestamps', () => {
    render(wrap(<TimelineBar />, seededClient()))
    expect(screen.getByText('Peak simulated flooding')).toBeTruthy()
    expect(screen.getByText('9')).toBeTruthy()
    fireEvent.click(screen.getByLabelText('Next timestamp'))
    expect(useFloodStore.getState().selectedIndex).toBe(3)
    expect(screen.getByLabelText('Next timestamp')).toHaveProperty('disabled', true)
    fireEvent.click(screen.getByLabelText('First timestamp'))
    expect(useFloodStore.getState().selectedIndex).toBe(0)
    expect(screen.getByText('Surcharge only')).toBeTruthy()
    fireEvent.click(screen.getByLabelText('Go to peak timestamp'))
    expect(useFloodStore.getState().selectedIndex).toBe(timeline.peakIndex)
    fireEvent.click(screen.getByLabelText('Previous timestamp'))
    expect(useFloodStore.getState().selectedIndex).toBe(1)
  })

  it('play/pause and speed control update playback state; seeking pauses', () => {
    render(wrap(<TimelineBar />, seededClient()))
    fireEvent.click(screen.getByLabelText('Play'))
    expect(useFloodStore.getState().isPlaying).toBe(true)
    fireEvent.change(screen.getByLabelText('Playback speed'), { target: { value: '4' } })
    expect(useFloodStore.getState().speed).toBe(4)
    fireEvent.click(screen.getByLabelText('Pause'))
    expect(useFloodStore.getState().isPlaying).toBe(false)
    fireEvent.click(screen.getByLabelText('Play'))
    fireEvent.change(screen.getByLabelText('Simulation timestamp'), { target: { value: '0' } })
    expect(useFloodStore.getState()).toMatchObject({ isPlaying: false, selectedIndex: 0 })
  })
})

function PlaybackHost() {
  usePlayback()
  return null
}

describe('usePlayback', () => {
  it('advances one actual timestamp per step interval at the chosen speed and stops at the end', async () => {
    vi.useFakeTimers()
    const client = seededClient()
    timeline.entries.forEach((e) => client.setQueryData(floodSliceQuery(SIM, e).queryKey, sliceFor(e.index)))
    useFloodStore.setState({ selectedIndex: 1, speed: 2, isPlaying: true })
    render(wrap(<PlaybackHost />, client))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(BASE_STEP_MS / 2 - 10)
    })
    expect(useFloodStore.getState().selectedIndex).toBe(1)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(20)
    })
    expect(useFloodStore.getState().selectedIndex).toBe(2)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(BASE_STEP_MS * 3)
    })
    expect(useFloodStore.getState()).toMatchObject({ selectedIndex: 3, isPlaying: false })
  })

  it('does not skip a timestamp whose slice is not loaded yet', async () => {
    vi.useFakeTimers()
    const client = seededClient()
    let resolve: (v: unknown) => void = () => {}
    const pending = new Promise((r) => (resolve = r))
    vi.stubGlobal('fetch', vi.fn(async () => {
      await pending
      return new Response(JSON.stringify(sliceFor(1)), { status: 200 })
    }))
    useFloodStore.setState({ selectedIndex: 0, isPlaying: true, speed: 4 })
    render(wrap(<PlaybackHost />, client))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(BASE_STEP_MS * 3)
    })
    expect(useFloodStore.getState().selectedIndex).toBe(0)
    await act(async () => {
      resolve(null)
      await vi.advanceTimersByTimeAsync(10)
    })
    expect(useFloodStore.getState().selectedIndex).toBe(1)
    vi.unstubAllGlobals()
  })
})

describe('KpiPanel', () => {
  it('updates "now" KPIs with the selected timestamp and shows backend event KPIs', () => {
    render(wrap(<KpiPanel />, seededClient()))
    const now = screen.getByLabelText('Indicators at the selected timestamp')
    expect(now.textContent).toContain('Flooding nodes9')
    expect(now.textContent).toContain('Buildings in influence zones27')
    expect(screen.getByText('5.435 m³/s')).toBeTruthy()
    expect(screen.getByText('282.835 mm')).toBeTruthy()
    act(() => useFloodStore.getState().selectTimestamp(SIM, 1))
    expect(screen.getByLabelText('Indicators at the selected timestamp').textContent).toContain('Flooding nodes5')
  })
})

describe('HydraulicsPanel', () => {
  it('lists potential bottlenecks with separate GCC ObjectID and SWMM link, and selects one in the viewer', () => {
    const controller = fakeController()
    render(wrap(<HydraulicsPanel />, seededClient(), controller))
    expect(screen.getByText('C901')).toBeTruthy()
    expect(screen.getByText('GCC ObjectID 9001')).toBeTruthy()
    fireEvent.click(screen.getByText('C901'))
    expect(controller.selectBottleneck).toHaveBeenCalledWith('C901')
    expect(controller.flyToGeometries).toHaveBeenCalled()
    expect(useViewerStore.getState().visibility.bottlenecks).toBe(true)
    fireEvent.click(screen.getByText('View Hotspots'))
    expect(controller.fitBottlenecks).toHaveBeenCalled()
    expect(screen.getByText(/Numerical diagnostics \(not bottlenecks\)/)).toBeTruthy()
  })
})

describe('ExposurePanel', () => {
  it('shows exposure at the selected timestamp with non-damage terminology and toggles highlights', () => {
    render(wrap(<ExposurePanel />, seededClient()))
    expect(screen.getByText(/not flooded or damaged/i)).toBeTruthy()
    expect(screen.getByText('27 of 100')).toBeTruthy()
    fireEvent.click(screen.getByLabelText(/Model-derived building exposure/))
    expect(useViewerStore.getState().visibility.exposureBuildings).toBe(true)
    expect(useViewerStore.getState().visibility.buildings).toBe(true)
  })
})

describe('RecommendationsPanel', () => {
  it('renders traceable recommendations and filters by priority', () => {
    render(wrap(<RecommendationsPanel />, seededClient(), fakeController()))
    expect(screen.getByText(/not an engineering order/)).toBeTruthy()
    expect(screen.getByText('Assess drainage capacity of segment C901')).toBeTruthy()
    expect(screen.getByText('C901 → 9001')).toBeTruthy()
    expect(screen.getByText('9.47 h')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /^Low 1/ }))
    expect(screen.queryByText('Assess drainage capacity of segment C901')).toBeNull()
    expect(screen.getByText('Verify invert data at C902')).toBeTruthy()
  })
})

describe('LayerControls (decision layers)', () => {
  it('toggles bottleneck and exposure layers independently', () => {
    render(wrap(<LayerControls />, seededClient()))
    fireEvent.click(screen.getByLabelText('Potential bottlenecks'))
    fireEvent.click(screen.getByLabelText('Model-derived road exposure'))
    const v = useViewerStore.getState().visibility
    expect(v).toMatchObject({ bottlenecks: true, exposureRoads: true, exposureBuildings: false, flood: true, drains: true })
  })
})

describe('MethodologyDialog', () => {
  it('opens as an accessible dialog and closes with Escape', () => {
    const client = seededClient()
    client.setQueryData(['summary', SIM], { simulationId: SIM, limitations: ['Model limitation from backend.'], metadata: { modelVersion: 'ward176-hydraulic-reconstructed-v1' } })
    render(wrap(<MethodologyDialog />, client))
    expect(screen.queryByRole('dialog')).toBeNull()
    act(() => useViewerStore.getState().setMethodologyOpen(true))
    const dialog = screen.getByRole('dialog', { name: 'Methodology & Limitations' })
    expect(dialog.textContent).toContain('not a full 2D')
    expect(dialog.textContent).toContain('Bottlenecks are model diagnostics, not confirmed drainage failures.')
    expect(dialog.textContent).toContain('Model limitation from backend.')
    expect(dialog.textContent).toContain('bottleneck-analysis-v1')
    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    })
    expect(screen.queryByRole('dialog')).toBeNull()
  })
})

describe('AssetInspector explainability', () => {
  it('explains a selected potential bottleneck with evidence and source-to-diagnostic traceability', () => {
    const client = seededClient()
    client.setQueryData(queryKeys.bottleneck(SIM, 'C901'), {
      linkId: 'C901', sourceObjectId: 9001, fromNodeId: 'J1', toNodeId: 'J2', severity: 'HIGH', confidence: 'MEDIUM', confidenceReasons: [],
      criteria: [{ id: 'L1', label: 'Capacity limited (SWMM)', met: true, value: 9.47, unit: 'hr', threshold: '> 0.01 h', source: 's' }],
      conduit: { modelLengthM: 123.8, sourceWidthM: 0.78, sourceDepthM: 0.78 },
      hydraulics: { maximumFlowCms: 0.5, timeOfMaximumFlow: null, hoursCapacityLimited: 9.47, hoursFullBothEnds: 9.47, hoursFullDownstream: 70 },
      connectedNodes: [{ nodeId: 'J1', role: 'upstream (model direction)', flooding: { hoursFlooded: 74.3, maximumRateCms: 0.59 }, surcharge: null }],
      networkContext: { modelComponentId: 1, componentHasOutfall: true, componentOutfalls: ['OUT1'] },
      explanation: { whatIsThis: 'SWMM conduit C901, representing GCC ObjectID 9001.', whyFlagged: 'C901 meets 4 of 4 criteria.', interpretation: 'Capacity limited.', sourceData: 's', plannerConsideration: 'Assess capacity in the field.', disclaimer: 'Model-derived diagnostic; not a confirmed real-world drainage failure.' },
      relatedRecommendationIds: ['rec-r1-C901'], metadata: { bottleneckAnalysisVersion: 'bottleneck-analysis-v1' },
    })
    useViewerStore.setState({ selection: { layer: 'bottlenecks', id: 'C901', properties: {} } })
    render(wrap(<AssetInspector />, client))
    for (const heading of ['What is this?', 'Why is it relevant?', 'What model evidence supports it?', 'What source data produced it?', 'What should the planner consider?']) {
      expect(screen.getByText(heading)).toBeTruthy()
    }
    expect(screen.getByText('GCC storm-water drain ObjectID 9001')).toBeTruthy()
    expect(screen.getByText('SWMM link C901: J1 → J2')).toBeTruthy()
    expect(screen.getByText(/not a confirmed real-world drainage failure/)).toBeTruthy()
  })
})
