import { act, cleanup, fireEvent, render, renderHook, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryKeys } from '../hooks/queries'
import { useResetDemo } from '../hooks/useResetDemo'
import { useFloodStore } from '../state/floodStore'
import { useSimulationStore } from '../state/simulationStore'
import { DEFAULT_VISIBILITY, useViewerStore } from '../state/viewerStore'
import type { Comparison, WhatIfSpec } from '../types/api'
import { BASE, SIM, WHATIF, comparison, seededClient, status, timeline, wrap } from '../test/fixtures'
import { EventCharts } from './charts/EventCharts'
import { ScenarioOverviewChart } from './charts/ScenarioOverviewChart'
import { ScenarioPanel } from './simulation/ScenarioPanel'
import { MapLegend } from './viewer/MapLegend'

vi.mock('cesium', () => ({ Color: { fromCssColorString: () => ({ withAlpha: () => ({}) }) } }))

const WHAT_IF: WhatIfSpec = {
  parameter: 'rainfallMultiplier', label: 'Rainfall multiplier (what-if sensitivity)', description: 'd', minimum: 0.5, maximum: 2, decimals: 2, baseline: 1,
  presets: [{ value: 1, label: '1.00× Baseline' }, { value: 1.25, label: '1.25×' }, { value: 1.5, label: '1.50×' }], scenarioAnalysisVersion: 'scenario-analysis-v1', terminology: 't',
}

beforeEach(() => {
  useSimulationStore.setState({ scenarioId: 'michaung-2023', activeSimulationId: SIM, runningSimulationId: null, rainfallMultiplier: 1, sessionRunIds: [], comparisonBaselineId: null, comparisonScenarioId: null })
  useFloodStore.setState({ simulationId: SIM, selectedIndex: 2, isPlaying: true, speed: 1 })
  useViewerStore.setState({ visibility: { ...DEFAULT_VISIBILITY }, methodologyOpen: false })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('EventCharts', () => {
  it('plots the backend timeline, marks the selected timestamp and lets the chart select a timestamp', () => {
    render(<EventCharts simulationId={SIM} timeline={timeline} index={2} />)
    const chart = screen.getByRole('slider', { name: /Rainfall and system overflow chart/ })
    expect(chart.getAttribute('aria-valuenow')).toBe('2')
    // Peak marker and caption use the backend values of the selected timestamp (fixture: 9 nodes × 0.1 m³/s).
    expect(screen.getByText(/peak 0\.9/)).toBeTruthy()
    expect(screen.getByText(/0\.9 m³\/s overflow/)).toBeTruthy()
    expect(document.querySelectorAll('rect.chart-rain')).toHaveLength(timeline.entries.length)
    fireEvent.keyDown(chart, { key: 'ArrowRight' })
    expect(useFloodStore.getState()).toMatchObject({ selectedIndex: 3, isPlaying: false })
  })
})

describe('ScenarioOverviewChart', () => {
  it('shows baseline and stored what-if values taken from the backend comparisons', () => {
    const client = seededClient()
    const c150 = { ...comparison, metrics: [{ key: 'totalRainfall', label: 'Total rainfall', unit: 'mm', source: 's', baseline: 282.835, scenario: 424.252, absoluteChange: 141.4, percentChange: 50 }] } as unknown as Comparison
    const c125 = { ...comparison, metrics: [{ key: 'totalRainfall', label: 'Total rainfall', unit: 'mm', source: 's', baseline: 282.835, scenario: 353.544, absoluteChange: 70.7, percentChange: 25 }] } as unknown as Comparison
    client.setQueryData(['comparison', BASE, WHATIF], c125)
    client.setQueryData(['comparison', BASE, 'test-sim-1500'], c150)
    const runs = [status(WHATIF, { parameters: { rainfallMultiplier: 1.25 } }), status('test-sim-1500', { parameters: { rainfallMultiplier: 1.5 } })]
    render(wrap(<ScenarioOverviewChart baselineId={BASE} runs={runs} whatIf={WHAT_IF} />, client))
    expect(screen.getByText('282.8 mm')).toBeTruthy()
    expect(screen.getByText('353.5 mm')).toBeTruthy()
    expect(screen.getByText('424.3 mm')).toBeTruthy()
    expect(screen.getByText(/not forecasts/)).toBeTruthy()
    // Metrics not present in the comparison are shown as unavailable, never invented.
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })

  it('asks for the presets when no what-if run is stored', () => {
    render(wrap(<ScenarioOverviewChart baselineId={BASE} runs={[]} whatIf={WHAT_IF} />, seededClient()))
    expect(screen.getByText(/Run or load the what-if presets/)).toBeTruthy()
  })
})

describe('MapLegend', () => {
  it('explains influence zones without implying water depth and follows visible layers', () => {
    render(wrap(<MapLegend />, seededClient()))
    expect(screen.getByText(/Not water depth or observed extent/)).toBeTruthy()
    expect(screen.queryByText('Potential bottlenecks (diagnostic concern)')).toBeNull()
    act(() => useViewerStore.getState().setVisible('bottlenecks', true))
    expect(screen.getByText('Potential bottlenecks (diagnostic concern)')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'What are these?' }))
    expect(useViewerStore.getState().methodologyOpen).toBe(true)
  })
})

describe('ScenarioPanel displayed what-if run', () => {
  it('shows the scaled rainfall recorded for the displayed what-if run next to the historical values', () => {
    useSimulationStore.setState({ activeSimulationId: WHATIF })
    const client = seededClient()
    client.setQueryData(queryKeys.scenarios, [{ scenarioId: 'michaung-2023', name: 'Michaung 2023' }])
    client.setQueryData(queryKeys.scenario('michaung-2023'), {
      scenarioId: 'michaung-2023', name: 'Michaung 2023', event: 'e', description: 'd', rainfallType: 'historical', dataType: 'source', source: { name: 'IMERG', variable: 'v' },
      rainfall: { type: 'i', unit: 'mm/hr', intervalMinutes: 30, records: 192, startTime: 'a', endTime: 'b', timeBasis: 'UTC', totalMm: 282.835, peakMmHr: 23.35, peakIntervalStart: 'c', dailyTotalsMm: {} },
      limitations: [], whatIf: WHAT_IF,
    })
    client.setQueryData(
      queryKeys.simulation(WHATIF),
      status(WHATIF, {
        parameters: { rainfallMultiplier: 1.25 },
        scenarioRun: { scenarioAnalysisVersion: 'scenario-analysis-v1', type: 'rainfall-multiplier', parentScenarioId: 'michaung-2023', rainfallMultiplier: 1.25, baselineModelSha256: 'a', transformedModelSha256: 'b', transformedModelIdenticalToBaseline: false, rainfall: { records: 192, baselineTotalMm: 282.835, scenarioTotalMm: 353.544, baselinePeakMmHr: 23.35, scenarioPeakMmHr: 29.188 }, createdAt: 'x' },
      }),
    )
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 200 })))
    render(wrap(<ScenarioPanel />, client))
    expect(screen.getByText('Historical total')).toBeTruthy()
    expect(screen.getByText('353.544 mm')).toBeTruthy()
    expect(screen.getByText('29.19 mm/hr')).toBeTruthy()
    expect(screen.getByText(/Displayed run: 1.25× what-if rainfall/)).toBeTruthy()
  })
})

describe('Reset demo with a loaded verified demo result', () => {
  it('returns the display to the precomputed demonstration result instead of another baseline run', () => {
    const client = seededClient()
    client.setQueryData(['demo'], [{ demoId: 'michaung-2023-verified', label: 'l', description: 'd', scenarioId: 'michaung-2023', modelVersion: 'm', rainfallMultiplier: 1, executionMode: 'precomputed-demo', available: true, verification: 'v', loadedSimulationId: 'demo-sim', loadingSimulationId: null }])
    useSimulationStore.setState({ activeSimulationId: WHATIF })
    const { result } = renderHook(() => useResetDemo(), { wrapper: ({ children }: { children: ReactNode }) => wrap(children, client, { resetDemo: vi.fn() }) })
    act(() => result.current())
    expect(useSimulationStore.getState().activeSimulationId).toBe('demo-sim')
  })
})
