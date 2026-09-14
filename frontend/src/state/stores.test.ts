import { beforeEach, describe, expect, it } from 'vitest'
import { clampIndex } from './floodStore'
import { useSimulationStore } from './simulationStore'
import { DEFAULT_VISIBILITY, useViewerStore } from './viewerStore'

describe('simulation store', () => {
  beforeEach(() => useSimulationStore.setState({ scenarioId: 'michaung-2023', runningSimulationId: null, activeSimulationId: null }))

  it('activates a simulation only when the tracked run completes', () => {
    const s = useSimulationStore.getState()
    s.startTracking('sim-b')
    s.finishTracking('sim-b', true)
    expect(useSimulationStore.getState().activeSimulationId).toBe('sim-b')
    expect(useSimulationStore.getState().runningSimulationId).toBeNull()
  })

  it('ignores a late completion from a simulation that is no longer tracked (race protection)', () => {
    const s = useSimulationStore.getState()
    s.startTracking('sim-a')
    s.startTracking('sim-b')
    s.finishTracking('sim-a', true)
    expect(useSimulationStore.getState().activeSimulationId).toBeNull()
    expect(useSimulationStore.getState().runningSimulationId).toBe('sim-b')
  })

  it('does not activate failed simulations', () => {
    const s = useSimulationStore.getState()
    s.startTracking('sim-f')
    s.finishTracking('sim-f', false)
    expect(useSimulationStore.getState().activeSimulationId).toBeNull()
  })
})

describe('viewer store', () => {
  beforeEach(() => useViewerStore.setState({ visibility: { ...DEFAULT_VISIBILITY }, floodOpacity: 0.55 }))

  it('toggles layers independently', () => {
    useViewerStore.getState().setVisible('drains', false)
    const v = useViewerStore.getState().visibility
    expect(v.drains).toBe(false)
    expect(v.buildings).toBe(true)
    expect(v.roads).toBe(true)
  })

  it('bounds flood opacity', () => {
    useViewerStore.getState().setFloodOpacity(4)
    expect(useViewerStore.getState().floodOpacity).toBe(1)
    useViewerStore.getState().setFloodOpacity(-1)
    expect(useViewerStore.getState().floodOpacity).toBe(0.05)
  })
})

describe('clampIndex', () => {
  it('keeps indices within the backend timestamp list', () => {
    expect(clampIndex(-3, 190)).toBe(0)
    expect(clampIndex(500, 190)).toBe(189)
    expect(clampIndex(91, 190)).toBe(91)
    expect(clampIndex(0, 0)).toBeNull()
  })
})
