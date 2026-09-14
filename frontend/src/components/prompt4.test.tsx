import { QueryClient } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiRequest, friendlyErrorMessage } from '../api/client'
import { queryKeys } from '../hooks/queries'
import { useResetDemo } from '../hooks/useResetDemo'
import { useFloodStore } from '../state/floodStore'
import { useSimulationStore } from '../state/simulationStore'
import { DEFAULT_VISIBILITY, useViewerStore } from '../state/viewerStore'
import { BASE, SIM, WHATIF, bottleneckTimeline, comparison, fakeController, seededClient, status, wrap } from '../test/fixtures'
import { ComparisonPanel } from './decision/ComparisonPanel'
import { HydraulicsPanel } from './decision/HydraulicsPanel'
import { BackendStatus } from './layout/BackendStatus'
import { ScenarioPanel } from './simulation/ScenarioPanel'
import { SimulationControls } from './simulation/SimulationControls'

vi.mock('cesium', () => ({ Color: { fromCssColorString: () => ({ withAlpha: () => ({}) }) } }))

beforeEach(() => {
  useSimulationStore.setState({ scenarioId: 'michaung-2023', activeSimulationId: SIM, runningSimulationId: null, rainfallMultiplier: 1, sessionRunIds: [], comparisonBaselineId: null, comparisonScenarioId: null })
  useFloodStore.setState({ simulationId: SIM, selectedIndex: 2, isPlaying: false, speed: 1 })
  useViewerStore.setState({ visibility: { ...DEFAULT_VISIBILITY }, dashboardTab: 'flood', exposureScope: 'timestamp', comparisonScope: 'event', selection: null })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function jsonResponse(body: unknown, statusCode = 200) {
  return new Response(JSON.stringify(body), { status: statusCode })
}

describe('api client error handling', () => {
  it('turns a hung request into a friendly timeout instead of waiting forever', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init: RequestInit) => new Promise((_resolve, reject) => init.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError'))))),
    )
    const error = await apiRequest('/health', { timeoutMs: 20 }).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).code).toBe('NETWORK_TIMEOUT')
    expect(friendlyErrorMessage(error)).toMatch(/did not respond in time/)
  })

  it('never shows raw server text for unknown 5xx errors', () => {
    const error = new ApiError(500, { code: 'SOMETHING_ODD', message: 'Traceback (most recent call last): ...' })
    expect(friendlyErrorMessage(error)).not.toMatch(/Traceback/)
  })
})

describe('BackendStatus', () => {
  it('shows connected when /health answers', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ status: 'ok', service: 'api', version: '0.1.0' })))
    render(wrap(<BackendStatus />, new QueryClient({ defaultOptions: { queries: { retry: false } } })))
    expect(await screen.findByText(/Backend connected/)).toBeTruthy()
  })

  it('shows offline with a retry when the backend cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))))
    render(wrap(<BackendStatus />, new QueryClient({ defaultOptions: { queries: { retry: false } } })))
    expect(await screen.findByText(/Backend offline/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeTruthy()
  })
})

describe('Demo mode', () => {
  it('loads the verified demo result without starting a simulation and labels it clearly', async () => {
    useSimulationStore.setState({ activeSimulationId: null })
    const client = seededClient()
    client.setQueryData(queryKeys.latestCompleted('michaung-2023'), null)
    const calls: { url: string; method: string }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        calls.push({ url, method: init?.method ?? 'GET' })
        if (url.endsWith('/demo'))
          return jsonResponse({ demoResults: [{ demoId: 'michaung-2023-verified', label: 'Precomputed demonstration result', description: 'd', scenarioId: 'michaung-2023', modelVersion: 'm', rainfallMultiplier: 1, executionMode: 'precomputed-demo', available: true, verification: 'v', loadedSimulationId: BASE, loadingSimulationId: null }] })
        if (url.endsWith('/demo/michaung-2023-verified/load')) return jsonResponse({ demoId: 'michaung-2023-verified', simulationId: BASE, status: 'COMPLETED', reused: true })
        if (url.includes(`/simulations/${BASE}`)) return jsonResponse(status(BASE, { executionMode: 'precomputed-demo', demoId: 'michaung-2023-verified' }))
        return jsonResponse({ simulations: [], limit: 1, offset: 0 })
      }),
    )
    render(wrap(<SimulationControls />, client))
    fireEvent.click(await screen.findByRole('button', { name: 'Load verified demo result' }))
    await waitFor(() => expect(useSimulationStore.getState().activeSimulationId).toBe(BASE))
    expect(await screen.findByText('Precomputed demonstration result')).toBeTruthy()
    expect(calls.some((c) => c.method === 'POST' && c.url.endsWith('/simulations'))).toBe(false)
  })

  it('runs a what-if simulation with the selected rainfall multiplier', async () => {
    useSimulationStore.setState({ rainfallMultiplier: 1.25 })
    const client = seededClient()
    const bodies: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method === 'POST' && url.endsWith('/simulations')) {
          bodies.push(JSON.parse(String(init.body)))
          return jsonResponse({ simulationId: WHATIF, scenarioId: 'michaung-2023', modelVersion: 'm', status: 'CREATED', createdAt: 'x' }, 202)
        }
        if (url.endsWith('/demo')) return jsonResponse({ demoResults: [] })
        return jsonResponse(status(WHATIF, { status: 'RUNNING', stage: 'SWMM_EXECUTION', progress: 30, parameters: { rainfallMultiplier: 1.25 } }))
      }),
    )
    render(wrap(<SimulationControls />, client))
    fireEvent.click(screen.getByRole('button', { name: 'Run 1.25× what-if simulation' }))
    await waitFor(() => expect(bodies).toEqual([{ scenarioId: 'michaung-2023', parameters: { rainfallMultiplier: 1.25 } }]))
    expect(useSimulationStore.getState().sessionRunIds).toContain(WHATIF)
  })
})

describe('ScenarioPanel what-if selection', () => {
  it('uses backend presets and labels non-baseline values as a what-if sensitivity, not a forecast', () => {
    const client = seededClient()
    client.setQueryData(queryKeys.scenarios, [{ scenarioId: 'michaung-2023', name: 'Michaung 2023' }])
    client.setQueryData(queryKeys.scenario('michaung-2023'), {
      scenarioId: 'michaung-2023', name: 'Michaung 2023', event: 'e', description: 'd', rainfallType: 'historical', dataType: 'source', source: { name: 'IMERG', variable: 'v' },
      rainfall: { type: 'i', unit: 'mm/hr', intervalMinutes: 30, records: 192, startTime: 'a', endTime: 'b', timeBasis: 'UTC', totalMm: 282.835, peakMmHr: 23.35, peakIntervalStart: 'c', dailyTotalsMm: {} },
      limitations: [],
      whatIf: { parameter: 'rainfallMultiplier', label: 'Rainfall multiplier (what-if sensitivity)', description: 'd', minimum: 0.5, maximum: 2, decimals: 2, baseline: 1, presets: [{ value: 1, label: '1.00× Baseline' }, { value: 1.25, label: '1.25× Increased rainfall' }], scenarioAnalysisVersion: 'scenario-analysis-v1', terminology: 't' },
    })
    render(wrap(<ScenarioPanel />, client))
    fireEvent.change(screen.getByLabelText('Rainfall multiplier (what-if sensitivity)'), { target: { value: '1.25' } })
    expect(useSimulationStore.getState().rainfallMultiplier).toBe(1.25)
    expect(screen.getByText(/Not a forecast, warning or climate projection/)).toBeTruthy()
  })
})

describe('Hydraulics time-aware view', () => {
  it('lists potential bottlenecks active at the selected timestamp and updates with the timeline', () => {
    const client = seededClient()
    client.setQueryData(['decision', SIM, 'bottleneck-timeline'], bottleneckTimeline)
    const controller = fakeController()
    render(wrap(<HydraulicsPanel />, client, controller))
    const box = screen.getByLabelText('Hydraulic state at the selected timestamp')
    expect(box.textContent).toContain('C901')
    expect(box.textContent).toContain('220% of full-flow capacity')
    fireEvent.click(screen.getByRole('button', { name: 'View on map' }))
    expect(controller.selectBottleneck).toHaveBeenCalledWith('C901')
    act(() => useFloodStore.getState().selectTimestamp(SIM, 1))
    expect(screen.getByLabelText('Hydraulic state at the selected timestamp').textContent).toContain('No potential bottleneck is full')
  })
})

describe('ComparisonPanel', () => {
  it('shows backend comparison metrics, changes and a categorical comparison layer toggle', () => {
    useSimulationStore.setState({ comparisonBaselineId: BASE, comparisonScenarioId: WHATIF })
    const client = seededClient()
    client.setQueryData(['simulations', 'completed', 'michaung-2023'], [status(BASE, { executionMode: 'precomputed-demo' }), status(WHATIF, { parameters: { rainfallMultiplier: 1.25 } })])
    client.setQueryData(['comparison', BASE, WHATIF], comparison)
    render(wrap(<ComparisonPanel />, client))
    expect(screen.getByText('Peak flooding nodes')).toBeTruthy()
    expect(screen.getByText('+2 (+10.5%)')).toBeTruthy()
    expect(screen.getAllByText(/C903/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('New').length).toBeGreaterThan(0)
    expect(screen.getByText(/NOT a shared scale/)).toBeTruthy()
    expect(screen.getByText(/Not a forecast/)).toBeTruthy()
    fireEvent.click(screen.getByLabelText(/Show comparison layer/))
    expect(useViewerStore.getState().visibility.comparison).toBe(true)
  })
})

describe('Reset demo', () => {
  it('restores default layers, timestep, multiplier and camera without deleting results', () => {
    const controller = fakeController()
    useViewerStore.setState({ visibility: { ...DEFAULT_VISIBILITY, bottlenecks: true, roads: false }, floodOpacity: 0.9, dashboardTab: 'compare' })
    useSimulationStore.setState({ rainfallMultiplier: 1.5, comparisonBaselineId: BASE, comparisonScenarioId: WHATIF })
    useFloodStore.setState({ selectedIndex: 3, isPlaying: true, speed: 4 })
    const client = seededClient()
    const { result } = renderHook(() => useResetDemo(), { wrapper: ({ children }: { children: ReactNode }) => wrap(children, client, controller) })
    act(() => result.current())
    expect(useViewerStore.getState()).toMatchObject({ visibility: DEFAULT_VISIBILITY, floodOpacity: 0.55, dashboardTab: 'flood' })
    expect(useFloodStore.getState()).toMatchObject({ selectedIndex: 0, isPlaying: false, speed: 1 })
    expect(useSimulationStore.getState()).toMatchObject({ rainfallMultiplier: 1, comparisonBaselineId: null, activeSimulationId: SIM })
    expect(controller.resetDemo).toHaveBeenCalledTimes(1)
  })
})
