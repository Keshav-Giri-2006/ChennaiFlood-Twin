/**
 * Location picking in the real DigitalTwinController. Only the WebGL-bound pieces (Viewer, input handler,
 * imagery) are replaced; Cesium math, entities and data sources are the real library.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

const cesium = vi.hoisted(() => ({
  handlers: [] as { actions: Map<unknown, (e: { position: { x: number; y: number } }) => void>; setCalls: number; destroyed: boolean }[],
  groundPick: null as unknown,
  drillPick: null as unknown as ReturnType<typeof vi.fn>,
}))

vi.mock('cesium', async (importOriginal) => {
  const actual = await importOriginal<typeof import('cesium')>()
  class FakeHandler {
    actions = new Map()
    setCalls = 0
    destroyed = false
    constructor() {
      cesium.handlers.push(this)
    }
    setInputAction(fn: unknown, type: unknown) {
      this.setCalls += 1
      this.actions.set(type, fn)
    }
    destroy() {
      this.destroyed = true
    }
  }
  class FakeViewer {
    private readonly sources: { name: string; entities: { values: unknown[] }; show: boolean }[] = []
    terrainProvider: unknown = null
    useDefaultRenderLoop = true
    scene = {
      canvas: document.createElement('canvas'),
      renderError: { addEventListener: () => undefined },
      globe: { depthTestAgainstTerrain: false, pick: () => cesium.groundPick },
      drillPick: (cesium.drillPick = vi.fn(() => [])),
      requestRender: () => undefined,
      verticalExaggeration: 1,
    }
    camera = { getPickRay: () => ({}), pickEllipsoid: () => undefined, flyToBoundingSphere: () => undefined }
    dataSources = {
      add: (ds: never) => {
        this.sources.push(ds)
        return Promise.resolve(ds)
      },
      get: (i: number) => this.sources[i],
      get length() {
        return 0
      },
    }
    constructor() {
      const sources = this.sources
      Object.defineProperty(this.dataSources, 'length', { get: () => sources.length })
    }
    isDestroyed() {
      return false
    }
    destroy() {}
  }
  return { ...actual, Viewer: FakeViewer, ScreenSpaceEventHandler: FakeHandler, ImageryLayer: class {}, OpenStreetMapImageryProvider: class {} }
})

import { Cartesian3, ScreenSpaceEventType } from 'cesium'
import type { FeatureCollection } from '../types/gis'
import { DigitalTwinController, type ControllerCallbacks } from './DigitalTwinController'
import { pointInGeometry } from './geometry'

// Synthetic square "ward" around the click position (test geometry, not project data).
const WARD: FeatureCollection = {
  type: 'FeatureCollection',
  features: [{ type: 'Feature', properties: {}, geometry: { type: 'MultiPolygon', coordinates: [[[[80.21, 12.96], [80.23, 12.96], [80.23, 12.98], [80.21, 12.98], [80.21, 12.96]]]] } }],
}
const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] }

function make() {
  const callbacks = { onLayerState: vi.fn(), onSelect: vi.fn(), onRenderError: vi.fn(), onLocationPick: vi.fn() } satisfies ControllerCallbacks
  const loaders = {
    layer: vi.fn(async (name: string) => (name === 'ward' ? WARD : EMPTY)),
    terrain: vi.fn(async () => {
      throw new Error('no terrain in unit test')
    }),
  }
  const controller = new DigitalTwinController(document.createElement('div'), loaders as never, callbacks)
  const handler = cesium.handlers[cesium.handlers.length - 1]
  const click = (x = 10, y = 20) => handler.actions.get(ScreenSpaceEventType.LEFT_CLICK)!({ position: { x, y } })
  return { controller, callbacks, handler, click }
}

afterEach(() => {
  cesium.handlers.length = 0
  cesium.groundPick = null
})

describe('DigitalTwinController location picking', () => {
  it('uses one click handler; toggling location mode never registers another', () => {
    const { controller, handler } = make()
    expect(cesium.handlers).toHaveLength(1)
    expect(handler.setCalls).toBe(1)
    for (let i = 0; i < 5; i += 1) {
      controller.setLocationMode(true)
      controller.setLocationMode(false)
    }
    controller.setLocationMode(true)
    expect(cesium.handlers).toHaveLength(1)
    expect(handler.setCalls).toBe(1)
    expect(controller.isLocationMode).toBe(true)
    controller.destroy()
    expect(handler.destroyed).toBe(true)
  })

  it('in location mode a click reports the ground position and does not select features', () => {
    const { controller, callbacks, click } = make()
    cesium.groundPick = Cartesian3.fromDegrees(80.2203, 12.9728)
    controller.setLocationMode(true)
    click()
    expect(callbacks.onLocationPick).toHaveBeenCalledTimes(1)
    const pick = callbacks.onLocationPick.mock.calls[0][0]
    expect(pick.longitude).toBeCloseTo(80.2203, 6)
    expect(pick.latitude).toBeCloseTo(12.9728, 6)
    expect(pick.insideStudyArea).toBeNull() // ward boundary not loaded yet
    expect(cesium.drillPick).not.toHaveBeenCalled()
    expect(callbacks.onSelect).not.toHaveBeenCalled()
  })

  it('clicking the sky in location mode reports nothing', () => {
    const { controller, callbacks, click } = make()
    controller.setLocationMode(true)
    click()
    expect(callbacks.onLocationPick).not.toHaveBeenCalled()
  })

  it('outside location mode clicks keep the existing feature selection path', () => {
    const { callbacks, click } = make()
    cesium.groundPick = Cartesian3.fromDegrees(80.2203, 12.9728)
    click()
    expect(cesium.drillPick).toHaveBeenCalledTimes(1)
    expect(callbacks.onLocationPick).not.toHaveBeenCalled()
  })

  it('flags picks outside the loaded ward boundary', async () => {
    const { controller, callbacks, click } = make()
    await controller.loadStaticScene()
    controller.setLocationMode(true)
    cesium.groundPick = Cartesian3.fromDegrees(80.22, 12.97)
    click()
    cesium.groundPick = Cartesian3.fromDegrees(80.30, 13.05)
    click()
    expect(callbacks.onLocationPick.mock.calls.map((c) => c[0].insideStudyArea)).toEqual([true, false])
  })

  it('shows at most one pin; moving replaces it and null removes it', () => {
    const { controller } = make()
    const count = () => controller.entityCounts().location
    const source = () => (controller as unknown as { locationSource: { entities: { values: { id: string; point?: unknown; position?: { getValue: (t: unknown) => Cartesian3 } }[] } } }).locationSource.entities.values
    controller.setLocationPin({ longitude: 80.22, latitude: 12.97, insideStudyArea: true, radiusMeters: 250 })
    expect(count()).toBe(2) // pin + surrounding-area disc
    const firstIds = source().map((e) => e.id)
    controller.setLocationPin({ longitude: 80.221, latitude: 12.971, insideStudyArea: true, radiusMeters: 250 })
    expect(count()).toBe(2)
    // New entity ids, so Cesium reports remove + add (not "changed") and the visualizers draw the moved pin.
    expect(source().some((e) => firstIds.includes(e.id))).toBe(false)
    const pinPosition = source().find((e) => e.point)!.position!.getValue(undefined)
    expect(Cartesian3.equalsEpsilon(pinPosition, Cartesian3.fromDegrees(80.221, 12.971), 0, 1e-6)).toBe(true)
    controller.setLocationPin({ longitude: 80.3, latitude: 13.05, insideStudyArea: false, radiusMeters: 250 })
    expect(count()).toBe(1) // outside the study area: pin only, no analysed area
    controller.setLocationPin(null)
    expect(count()).toBe(0)
  })
})

describe('pointInGeometry', () => {
  it('handles polygons with holes and multipolygons', () => {
    const withHole = { type: 'Polygon' as const, coordinates: [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]] as [number, number][][] }
    expect(pointInGeometry(2, 2, withHole)).toBe(true)
    expect(pointInGeometry(5, 5, withHole)).toBe(false)
    expect(pointInGeometry(11, 5, withHole)).toBe(false)
    const multi = { type: 'MultiPolygon' as const, coordinates: [withHole.coordinates, [[[20, 20], [30, 20], [30, 30], [20, 20]]]] as [number, number][][][] }
    expect(pointInGeometry(28, 22, multi)).toBe(true)
    expect(pointInGeometry(1, 1, { type: 'LineString', coordinates: [[0, 0], [2, 2]] })).toBe(false)
  })
})
