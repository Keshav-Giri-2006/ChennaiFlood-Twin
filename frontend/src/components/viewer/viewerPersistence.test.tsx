import { act, cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useFloodStore } from '../../state/floodStore'
import { useSimulationStore } from '../../state/simulationStore'
import { DEFAULT_VISIBILITY, useViewerStore } from '../../state/viewerStore'
import { DigitalTwinViewer } from './DigitalTwinViewer'

const created: { setLayerVisible: ReturnType<typeof vi.fn>; destroy: ReturnType<typeof vi.fn> }[] = []

// The Cesium controller needs WebGL; replace it with a recording double to test lifecycle only.
vi.mock('../../cesium/DigitalTwinController', () => ({
  DigitalTwinController: vi.fn().mockImplementation(function (this: Record<string, unknown>) {
    const instance = {
      setLayerVisible: vi.fn(),
      setVerticalExaggeration: vi.fn(),
      setFloodOpacity: vi.fn(),
      loadStaticScene: vi.fn(async () => {}),
      destroy: vi.fn(),
    }
    created.push(instance)
    return instance
  }),
}))

afterEach(cleanup)

describe('DigitalTwinViewer', () => {
  it('creates the Cesium controller once and keeps it through layer, timeline and panel state changes', () => {
    useViewerStore.setState({ visibility: { ...DEFAULT_VISIBILITY } })
    const { rerender, unmount } = render(<DigitalTwinViewer />)
    const count = created.length
    expect(count).toBeGreaterThanOrEqual(1)
    const controller = created[created.length - 1]

    act(() => {
      useViewerStore.getState().setVisible('bottlenecks', true)
      useViewerStore.getState().setVisible('exposureBuildings', true)
      useViewerStore.getState().setDashboardTab('exposure')
      useViewerStore.getState().setFloodOpacity(0.8)
      useFloodStore.setState({ simulationId: 's', selectedIndex: 5, isPlaying: true })
      useViewerStore.getState().setVisible('comparison', true)
      useSimulationStore.getState().setRainfallMultiplier(1.25)
      useSimulationStore.getState().setActiveSimulation('what-if-run')
      useSimulationStore.getState().setComparison('baseline', 'what-if-run')
    })
    rerender(<DigitalTwinViewer />)

    expect(created.length).toBe(count)
    expect(controller.destroy).not.toHaveBeenCalled()
    expect(controller.setLayerVisible).toHaveBeenCalledWith('bottlenecks', true)
    expect(controller.setLayerVisible).toHaveBeenCalledWith('exposureBuildings', true)
    // Only the explicit recovery action recreates the viewer.
    act(() => useViewerStore.getState().restartViewer())
    expect(created.length).toBe(count + 1)
    expect(controller.destroy).toHaveBeenCalledTimes(1)
    unmount()
  })
})
