import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { NODE_MARKER } from '../cesium/styles'
import { RAIN_VISUAL_FULL_SCALE_MM_HR, rainVisual, rainfallClass } from '../cesium/rainfall'
import { queryKeys } from '../hooks/queries'
import { useFloodStore } from '../state/floodStore'
import { useSimulationStore } from '../state/simulationStore'
import { DEFAULT_VISIBILITY, useViewerStore } from '../state/viewerStore'
import type { FloodTimeline } from '../types/api'
import { SIM, seededClient, timeline, wrap } from '../test/fixtures'
import { RainOverlay } from './viewer/RainOverlay'
import { SimulationHud } from './viewer/SimulationHud'
import { simulatedDateParts } from '../utils/format'

vi.mock('cesium', () => ({ Color: { fromCssColorString: () => ({ withAlpha: () => ({}) }) } }))

const WHATIF_SIM = 'test-sim-1250'

/** Copy of the fixture timeline with a different simulation id and scaled rainfall (a what-if run). */
function scaledTimeline(factor: number): FloodTimeline {
  return {
    ...timeline,
    simulationId: WHATIF_SIM,
    entries: timeline.entries.map((e) => ({ ...e, rainfallMmHr: Math.round(e.rainfallMmHr * factor * 1000) / 1000 })),
  }
}

beforeEach(() => {
  useSimulationStore.setState({ scenarioId: 'michaung-2023', activeSimulationId: SIM, runningSimulationId: null, rainfallMultiplier: 1 })
  useFloodStore.setState({ simulationId: SIM, selectedIndex: 2, isPlaying: false, speed: 1 })
  useViewerStore.setState({ visibility: { ...DEFAULT_VISIBILITY } })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('rainfall display mapping', () => {
  it('classifies simulated intensities and never draws rain at zero', () => {
    expect(rainfallClass(0)).toBe('NONE')
    expect(rainfallClass(null)).toBe('NONE')
    expect(rainfallClass(1.2)).toBe('LIGHT')
    expect(rainfallClass(5)).toBe('MODERATE')
    expect(rainfallClass(12)).toBe('HEAVY')
    expect(rainfallClass(23.35)).toBe('VERY HEAVY')
    expect(rainVisual(0).intensity).toBe(0)
    expect(rainVisual(null).intensity).toBe(0)
  })

  it('increases visual density and speed with intensity and saturates at full scale', () => {
    const light = rainVisual(1)
    const heavy = rainVisual(12)
    const peak = rainVisual(23.35)
    expect(light.intensity).toBeLessThan(heavy.intensity)
    expect(heavy.intensity).toBeLessThan(peak.intensity)
    expect(light.speed).toBeLessThan(peak.speed)
    expect(rainVisual(RAIN_VISUAL_FULL_SCALE_MM_HR).intensity).toBe(1)
    // Beyond the full-scale value the overlay does not keep growing.
    expect(rainVisual(RAIN_VISUAL_FULL_SCALE_MM_HR * 3).intensity).toBe(1)
  })
})

describe('RainOverlay', () => {
  it('follows the simulated rainfall of the selected timestep and disappears when it is zero', () => {
    const client = seededClient()
    const { container } = render(wrap(<RainOverlay />, client))
    const overlay = container.querySelector('.rain-overlay') as HTMLElement
    expect(overlay).toBeTruthy()
    expect(overlay.querySelectorAll('.rain-layer')).toHaveLength(3)
    const strong = Number(overlay.dataset.intensity)

    // A timestep without rainfall draws nothing at all.
    const dry = { ...timeline, entries: timeline.entries.map((e) => ({ ...e, rainfallMmHr: 0 })) }
    client.setQueryData(queryKeys.floodTimeline(SIM), dry)
    cleanup()
    const { container: dryContainer } = render(wrap(<RainOverlay />, client))
    expect(dryContainer.querySelector('.rain-overlay')).toBeNull()
    expect(strong).toBeGreaterThan(0)
  })

  it('is removed when the rainfall visualisation layer is switched off', () => {
    const client = seededClient()
    const { container } = render(wrap(<RainOverlay />, client))
    expect(container.querySelector('.rain-overlay')).toBeTruthy()
    act(() => useViewerStore.getState().setVisible('rain', false))
    expect(container.querySelector('.rain-overlay')).toBeNull()
  })

  it('uses the rainfall of the displayed what-if run, not the historical baseline', () => {
    const client = seededClient()
    client.setQueryData(queryKeys.floodTimeline(WHATIF_SIM), scaledTimeline(8))
    const baseline = render(wrap(<RainOverlay />, client)).container.querySelector('.rain-overlay') as HTMLElement
    const baselineIntensity = Number(baseline.dataset.intensity)
    cleanup()
    useSimulationStore.setState({ activeSimulationId: WHATIF_SIM })
    useFloodStore.setState({ simulationId: WHATIF_SIM, selectedIndex: 2 })
    const scenario = render(wrap(<RainOverlay />, client)).container.querySelector('.rain-overlay') as HTMLElement
    expect(Number(scenario.dataset.intensity)).toBeGreaterThan(baselineIntensity)
  })
})

describe('SimulationHud', () => {
  it('shows the simulated timestamp and rainfall of the selected timestep, following the timeline', () => {
    const client = seededClient()
    render(wrap(<SimulationHud />, client))
    // Fixture timeline: entry 2 is 2023-12-03 21:00 UTC with 1 mm/hr rainfall.
    expect(screen.getByText('03 DEC 2023')).toBeTruthy()
    expect(screen.getByText('21:00 UTC')).toBeTruthy()
    expect(screen.getByText(/Peak simulated flooding/i)).toBeTruthy()
    expect(screen.getByText('LIGHT')).toBeTruthy()
    act(() => useFloodStore.getState().selectTimestamp(SIM, 0))
    expect(screen.getByText('20:00 UTC')).toBeTruthy()
  })

  it('formats simulated timestamps in UTC and never falls back to the current wall-clock time', () => {
    expect(simulatedDateParts('2023-12-03T22:00:00Z')).toEqual({ date: '03 DEC 2023', time: '22:00 UTC' })
    expect(simulatedDateParts(null)).toBeNull()
    expect(simulatedDateParts('not-a-date')).toBeNull()
  })
})

describe('node state emphasis', () => {
  it('draws stressed nodes larger than normal ones, scaled by the backend overflow class', () => {
    const { normal, surcharged, flooding } = NODE_MARKER
    expect(normal.pixelSize).toBeLessThan(surcharged.pixelSize)
    expect(surcharged.pixelSize).toBeLessThan(flooding.pixelSize.LOW)
    expect(flooding.pixelSize.LOW).toBeLessThan(flooding.pixelSize.MODERATE)
    expect(flooding.pixelSize.MODERATE).toBeLessThan(flooding.pixelSize.HIGH)
    // The pulse stays small enough that a flooding node never shrinks below a surcharged one.
    expect(flooding.pixelSize.LOW - flooding.pulseAmplitude).toBeGreaterThan(surcharged.pixelSize)
  })
})
