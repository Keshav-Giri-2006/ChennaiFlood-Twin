import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DEFAULT_VISIBILITY, useViewerStore } from '../state/viewerStore'
import { seededClient, wrap } from '../test/fixtures'
import { AssetInspector } from './inspector/AssetInspector'
import { LayerControls } from './viewer/LayerControls'

// cesium is heavy and needs WebGL; components under test only use its constants/types.
vi.mock('cesium', () => ({ Color: { fromCssColorString: () => ({ withAlpha: () => ({}) }) } }))


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
    render(wrap(<AssetInspector />, seededClient()))
    expect(screen.getByText('Source attributes (GCC GIS)')).toBeTruthy()
    expect(screen.getByText('Model representation (SWMM)')).toBeTruthy()
    expect(screen.getByText('5902')).toBeTruthy()
    expect(screen.getByText('C162')).toBeTruthy()
  })
})
