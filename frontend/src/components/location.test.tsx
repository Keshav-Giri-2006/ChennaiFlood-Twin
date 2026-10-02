import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { locationApi, simulationsApi } from '../api/endpoints'
import { queryKeys } from '../hooks/queries'
import { useFloodStore } from '../state/floodStore'
import { useLocationStore } from '../state/locationStore'
import { useSimulationStore } from '../state/simulationStore'
import { useViewerStore } from '../state/viewerStore'
import { SIM, seededClient, status, wrap } from '../test/fixtures'
import type { LocationCheck } from '../types/api'
import { LocationLayerSync } from './location/LocationLayerSync'
import { LocationPanel } from './location/LocationPanel'
import { DigitalTwinViewer } from './viewer/DigitalTwinViewer'

type Recorded = { callbacks: { onLocationPick?: (p: unknown) => void; onSelect: (f: unknown) => void }; setLocationMode: ReturnType<typeof vi.fn>; setLocationPin: ReturnType<typeof vi.fn>; destroy: ReturnType<typeof vi.fn> }
const created: Recorded[] = []

// WebGL-free double recording what React asks of the controller (the real controller is covered in cesium/locationPick.test.ts).
vi.mock('../cesium/DigitalTwinController', () => ({
  DigitalTwinController: vi.fn().mockImplementation(function (_container: unknown, _loaders: unknown, callbacks: Recorded['callbacks']) {
    const instance = {
      callbacks,
      setLayerVisible: vi.fn(),
      setVerticalExaggeration: vi.fn(),
      setFloodOpacity: vi.fn(),
      loadStaticScene: vi.fn(async () => {}),
      setLocationMode: vi.fn(),
      setLocationPin: vi.fn(),
      destroy: vi.fn(),
    }
    created.push(instance as unknown as Recorded)
    return instance
  }),
}))

const SCENARIO = { scenarioId: 'michaung-2023', name: 'Cyclone Michaung 2023', rainfall: {}, source: {} }

/** TEST FIXTURE — synthetic, API-shaped location-check response. */
function result(latitude: number, longitude: number): LocationCheck {
  const node = {
    nodeId: 'J006', nodeType: 'JUNCTION' as const, location: [80.218, 12.971] as [number, number], distanceM: 15.5, withinRadius: true, zoneOverlapM2: 19669.6, zoneOverlapShare: 0.1464, isNearest: true,
    response: {
      condition: 'OVERFLOW' as const, description: 'Overflow', overflowPeriods: 106, overflowHours: 53, surchargePeriods: 0, surchargeHours: 0, peakOverflowRateCms: 0.460317, peakOverflowTime: '2023-12-03T22:00:00Z',
      firstOverflowTime: '2023-12-03T10:00:00Z', lastOverflowTime: '2023-12-05T21:30:00Z', highestOverflowClass: 'HIGH' as const, approxCumulativeOverflowM3: 17437.1, maxNodeWaterDepthM: 1.07, maxFillRatio: 1,
    },
  }
  return {
    simulationId: SIM, scenarioId: 'michaung-2023', modelVersion: 'm', rainfallMultiplier: 1, locationCheckVersion: 'location-check-v1', floodProcessingVersion: 'flood-processing-v1', dataType: 'model-derived',
    terminology: 't', location: { latitude, longitude, withinStudyArea: true, crs: 'EPSG:4326', processingCrs: 'EPSG:32644', eastingM: 1, northingM: 1 }, radiusMeters: 250,
    response: { code: 'OVERFLOW_AT_NEAREST_NODE', description: 'The modelled drainage node nearest to the selected location overflowed.' },
    nearestNode: { ...node, zoneContainsLocation: true },
    surroundingArea: {
      circleAreaM2: 196329.8, areaWithinStudyAreaM2: 134309.7, shareWithinStudyArea: 0.6841, associatedNodeCount: 16, overflowingNodeCount: 1, surchargeOnlyNodeCount: 3, noReportedStressNodeCount: 12, outfallNodeCount: 0,
      areaAssociatedWithOverflowM2: 19669.6, shareAssociatedWithOverflow: 0.1464, firstOverflowTime: '2023-12-03T10:00:00Z', lastOverflowTime: '2023-12-05T21:30:00Z', overflowDurationHours: 53,
      peak: { time: '2023-12-03T22:00:00Z', index: 2, combinedOverflowRateCms: 0.460317, overflowingNodeCount: 1, overflowingNodeIds: ['J006'], areaAssociatedWithOverflowM2: 19669.6, shareAssociatedWithOverflow: 0.1464 },
    },
    nodes: [node], potentialBottlenecks: [{ linkId: 'C099', sourceObjectId: 5857, severity: 'LOW', confidence: 'LOW', fromNodeId: 'J007', toNodeId: 'J023', nearestEndNodeDistanceM: 119.8 }],
    intervalMinutes: 30, groundFloodDepthM: null, floodExtentAvailable: false, notDerived: { groundFloodDepth: 'SWMM ran with ALLOW_PONDING=NO.' }, timeConvention: 'UTC', method: {}, limitations: ['Model-derived result; not a property assessment.'],
  }
}

function client() {
  const c = seededClient()
  c.setQueryData(queryKeys.scenario('michaung-2023'), SCENARIO)
  c.setQueryData(queryKeys.simulation(SIM), status(SIM))
  return c
}

beforeEach(() => {
  useLocationStore.getState().reset()
  useViewerStore.getState().reset()
  useSimulationStore.setState({ scenarioId: 'michaung-2023', rainfallMultiplier: 1, runningSimulationId: null, activeSimulationId: null, sessionRunIds: [] })
  created.length = 0
})
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('Location pin via the Cesium viewer', () => {
  it('map clicks create one pin and move it; the viewer is created once and location mode follows the tab', () => {
    const c = client()
    render(wrap(<DigitalTwinViewer><LocationLayerSync /></DigitalTwinViewer>, c))
    expect(created).toHaveLength(1)
    const controller = created[0]
    expect(controller.setLocationMode).toHaveBeenLastCalledWith(false)

    act(() => useViewerStore.getState().setDashboardTab('location'))
    expect(controller.setLocationMode).toHaveBeenLastCalledWith(true)

    act(() => controller.callbacks.onLocationPick?.({ latitude: 12.9715, longitude: 80.2185, insideStudyArea: true }))
    expect(useLocationStore.getState().location).toEqual({ latitude: 12.9715, longitude: 80.2185, insideStudyArea: true })
    expect(controller.setLocationPin).toHaveBeenLastCalledWith({ latitude: 12.9715, longitude: 80.2185, insideStudyArea: true, radiusMeters: 250 })

    act(() => controller.callbacks.onLocationPick?.({ latitude: 12.975, longitude: 80.222, insideStudyArea: true }))
    expect(useLocationStore.getState().location?.latitude).toBe(12.975)
    // Every call carries exactly one pin; the second replaces the first.
    expect(controller.setLocationPin.mock.calls.every((args) => args.length === 1)).toBe(true)
    expect(controller.setLocationPin).toHaveBeenLastCalledWith({ latitude: 12.975, longitude: 80.222, insideStudyArea: true, radiusMeters: 250 })

    act(() => useViewerStore.getState().setDashboardTab('hydraulics'))
    expect(controller.setLocationMode).toHaveBeenLastCalledWith(false)
    // Feature selection callback is untouched.
    act(() => controller.callbacks.onSelect({ layer: 'drains', id: '5857', properties: {} }))
    expect(useViewerStore.getState().selection?.id).toBe('5857')
    expect(created).toHaveLength(1)
    expect(controller.destroy).not.toHaveBeenCalled()
  })
})

describe('LocationPanel', () => {
  it('asks for a location and cannot run without one', () => {
    render(wrap(<LocationPanel />, client()))
    expect(screen.getByText('Click the map to select a location.')).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Run Location Flood Check' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('shows coordinates, updates them when the pin moves, and clears the location', () => {
    render(wrap(<LocationPanel />, client()))
    act(() => useLocationStore.getState().setLocation({ latitude: 12.9715123, longitude: 80.2185456, insideStudyArea: true }))
    expect(screen.getByText('12.971512°')).toBeTruthy()
    expect(screen.getByText('80.218546°')).toBeTruthy()
    act(() => useLocationStore.getState().setLocation({ latitude: 12.975, longitude: 80.222, insideStudyArea: true }))
    expect(screen.getByText('12.975000°')).toBeTruthy()
    expect(screen.queryByText('12.971512°')).toBeNull()
    expect((screen.getByRole('button', { name: 'Run Location Flood Check' }) as HTMLButtonElement).disabled).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: 'Clear location' }))
    expect(useLocationStore.getState().location).toBeNull()
    expect(screen.getByText('Click the map to select a location.')).toBeTruthy()
  })

  it('rejects a point outside Ward 176 before any request', () => {
    const check = vi.spyOn(locationApi, 'check')
    render(wrap(<LocationPanel />, client()))
    act(() => useLocationStore.getState().setLocation({ latitude: 13.05, longitude: 80.25, insideStudyArea: false }))
    expect(screen.getByText(/outside Ward 176/)).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Run Location Flood Check' }) as HTMLButtonElement).disabled).toBe(true)
    expect(check).not.toHaveBeenCalled()
  })

  it('Run Location Flood Check starts the existing simulation workflow for the selected scenario', async () => {
    const create = vi.spyOn(simulationsApi, 'create').mockResolvedValue({ simulationId: 'run-1', status: 'CREATED' } as never)
    const check = vi.spyOn(locationApi, 'check')
    render(wrap(<LocationPanel />, client()))
    act(() => useLocationStore.getState().setLocation({ latitude: 12.97, longitude: 80.22, insideStudyArea: true }))
    fireEvent.click(screen.getByRole('button', { name: 'Run Location Flood Check' }))
    await waitFor(() => expect(useSimulationStore.getState().runningSimulationId).toBe('run-1'))
    expect(create).toHaveBeenCalledWith('michaung-2023', { rainfallMultiplier: undefined })
    expect(useLocationStore.getState()).toMatchObject({ checkRequested: true, runSimulationId: 'run-1' })
    expect(check).not.toHaveBeenCalled() // nothing is queried while the simulation is incomplete
  })

  it('shows the running state and does not query incomplete results', () => {
    const check = vi.spyOn(locationApi, 'check')
    const c = client()
    c.setQueryData(queryKeys.simulation('run-1'), status('run-1', { status: 'RUNNING', stage: 'SWMM_EXECUTION', progress: 30, completedAt: null }))
    useSimulationStore.setState({ runningSimulationId: 'run-1', activeSimulationId: SIM })
    useLocationStore.setState({ location: { latitude: 12.97, longitude: 80.22, insideStudyArea: true }, checkRequested: true, runSimulationId: 'run-1' })
    render(wrap(<LocationPanel />, c))
    expect(screen.getByText('Running EPA SWMM')).toBeTruthy()
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('30')
    expect(screen.getByText(/evaluated when the simulation has completed/)).toBeTruthy()
    expect(screen.queryByText('Historical Flood Response')).toBeNull()
    expect(check).not.toHaveBeenCalled()
  })

  it('shows the failure state of its simulation and does not evaluate the location', () => {
    const check = vi.spyOn(locationApi, 'check')
    const c = client()
    c.setQueryData(queryKeys.simulation('run-1'), status('run-1', { status: 'FAILED', stage: 'SWMM_EXECUTION', error: { code: 'SIMULATION_FAILED', message: 'Simulation failed during SWMM execution.' } }))
    useSimulationStore.setState({ runningSimulationId: null, activeSimulationId: SIM })
    useLocationStore.setState({ location: { latitude: 12.97, longitude: 80.22, insideStudyArea: true }, checkRequested: true, runSimulationId: 'run-1' })
    render(wrap(<LocationPanel />, c))
    expect(screen.getByText(/Simulation could not be completed/)).toBeTruthy()
    expect(screen.getByText(/The location was not evaluated/)).toBeTruthy()
    expect(check).not.toHaveBeenCalled()
  })

  it('renders the backend result after completion and re-queries the same simulation when the pin moves', async () => {
    const check = vi.spyOn(locationApi, 'check').mockImplementation(async (_sid, loc) => result(loc.latitude, loc.longitude))
    const create = vi.spyOn(simulationsApi, 'create')
    useSimulationStore.setState({ activeSimulationId: SIM })
    useLocationStore.setState({ location: { latitude: 12.9716, longitude: 80.2182, insideStudyArea: true }, checkRequested: true, runSimulationId: null })
    render(wrap(<LocationPanel />, client()))
    await screen.findByText('Historical Flood Response')
    expect(check).toHaveBeenCalledWith(SIM, { latitude: 12.9716, longitude: 80.2182, radiusMeters: 250 }, expect.anything())
    expect(screen.getByText(/Model-derived result for the selected historical rainfall scenario/)).toBeTruthy()
    expect(screen.getByText('Overflow modelled at the nearest drainage node')).toBeTruthy()
    expect(screen.getByText('J006')).toBeTruthy()
    // Peak overflow of the nearest node and the combined peak of the surrounding area (same single node here).
    expect(screen.getAllByText(/0\.46 m³\/s/)).toHaveLength(2)
    expect(screen.getByText('Not derived by this model')).toBeTruthy()
    expect(screen.getByText(/C099 \(low, 120 m\)/)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Show on timeline' }))
    expect(useFloodStore.getState()).toMatchObject({ simulationId: SIM, selectedIndex: 2, isPlaying: false })

    act(() => useLocationStore.getState().setLocation({ latitude: 12.975, longitude: 80.222, insideStudyArea: true }))
    await waitFor(() => expect(check).toHaveBeenLastCalledWith(SIM, { latitude: 12.975, longitude: 80.222, radiusMeters: 250 }, expect.anything()))
    expect(create).not.toHaveBeenCalled() // moving the pin never re-runs SWMM
  })

  it('checks the displayed completed result without re-running SWMM', async () => {
    const check = vi.spyOn(locationApi, 'check').mockImplementation(async (_sid, loc) => result(loc.latitude, loc.longitude))
    const create = vi.spyOn(simulationsApi, 'create')
    useSimulationStore.setState({ activeSimulationId: SIM })
    render(wrap(<LocationPanel />, client()))
    act(() => useLocationStore.getState().setLocation({ latitude: 12.97, longitude: 80.22, insideStudyArea: true }))
    fireEvent.click(screen.getByRole('button', { name: 'Check displayed result (no re-run)' }))
    await screen.findByText('Historical Flood Response')
    expect(check).toHaveBeenCalledTimes(1)
    expect(create).not.toHaveBeenCalled()
  })

  it('shows backend errors such as a location outside the study area', async () => {
    const { ApiError } = await import('../api/client')
    vi.spyOn(locationApi, 'check').mockRejectedValue(new ApiError(422, { code: 'LOCATION_OUTSIDE_STUDY_AREA', message: 'outside' }))
    useSimulationStore.setState({ activeSimulationId: SIM })
    useLocationStore.setState({ location: { latitude: 12.9, longitude: 80.2, insideStudyArea: null }, checkRequested: true, runSimulationId: null })
    render(wrap(<LocationPanel />, client()))
    await screen.findByText(/The hydraulic model covers Ward 176 only/)
  })

  it('demo reset clears the location', () => {
    useLocationStore.setState({ location: { latitude: 12.97, longitude: 80.22, insideStudyArea: true }, checkRequested: true, runSimulationId: 'x' })
    useLocationStore.getState().reset()
    expect(useLocationStore.getState()).toMatchObject({ location: null, checkRequested: false, runSimulationId: null })
  })
})
