import {
  BoundingSphere,
  Cartesian3,
  ColorMaterialProperty,
  CustomDataSource,
  EllipsoidTerrainProvider,
  Entity,
  HeadingPitchRange,
  HeightReference,
  ImageryLayer,
  Math as CesiumMath,
  OpenStreetMapImageryProvider,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  Viewer,
  defined,
  type Color,
  type MaterialProperty,
  type TerrainProvider,
} from 'cesium'
import type { FeatureCollection, FloodFeatureProperties, TerrainGrid } from '../types/gis'
import type { LayerKey, LayerLoadState, SelectedFeature } from '../state/viewerStore'
import { bboxOf, lineParts, polygonHierarchies } from './geometry'
import { BUILDING_VISUAL_EXTRUSION_M, LAYER_COLORS, floodColor } from './styles'
import { createDemTerrainProvider } from './terrain'

type StaticLayer = 'boundary' | 'buildings' | 'roads' | 'drains' | 'subcatchments'
type ApiLayerName = 'ward' | 'buildings' | 'roads' | 'drains' | 'subcatchments'

const API_LAYER: Record<StaticLayer, ApiLayerName> = {
  boundary: 'ward',
  buildings: 'buildings',
  roads: 'roads',
  drains: 'drains',
  subcatchments: 'subcatchments',
}

export interface ControllerLoaders {
  layer: (name: ApiLayerName, signal: AbortSignal) => Promise<FeatureCollection>
  terrain: (signal: AbortSignal) => Promise<TerrainGrid>
}

export interface ControllerCallbacks {
  onLayerState: (layer: LayerKey, value: { state: LayerLoadState; message?: string; featureCount?: number; loadMs?: number }) => void
  onSelect: (feature: SelectedFeature | null) => void
  /** Called when Cesium stops rendering because of an error (null when rendering resumes). */
  onRenderError: (message: string | null) => void
}

interface FeatureRef {
  feature: SelectedFeature
  entities: Entity[]
}

/**
 * Owns the single Cesium Viewer and everything drawn in it (docs/08 §7–§9).
 * React calls these methods; it never recreates the viewer on state changes.
 */
export class DigitalTwinController {
  readonly viewer: Viewer
  private readonly loaders: ControllerLoaders
  private readonly callbacks: ControllerCallbacks
  private readonly abort = new AbortController()
  private readonly handler: ScreenSpaceEventHandler
  private readonly layers = new Map<StaticLayer, CustomDataSource>()
  private readonly floodSource = new CustomDataSource('flood')
  private readonly featureByEntity = new Map<Entity, FeatureRef>()
  private readonly floodFeatureByEntity = new Map<Entity, FeatureRef>()
  /** Visibility requested before a layer finished loading. */
  private readonly pendingVisibility = new Map<StaticLayer, boolean>()
  private demTerrain: TerrainProvider | null = null
  private terrainEnabled = true
  private wardBbox: [number, number, number, number] | null = null
  private selected: { ref: FeatureRef; originals: (MaterialProperty | Color | undefined)[] } | null = null
  private floodOpacity = 0.55
  private floodFeatures: FeatureCollection<FloodFeatureProperties> | null = null
  private destroyed = false
  private buildingsTranslucent = false

  constructor(container: HTMLElement, loaders: ControllerLoaders, callbacks: ControllerCallbacks) {
    this.loaders = loaders
    this.callbacks = callbacks
    this.viewer = new Viewer(container, {
      animation: false,
      timeline: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      infoBox: false,
      selectionIndicator: false,
      // OpenStreetMap context imagery; avoids Cesium Ion services and tokens.
      baseLayer: new ImageryLayer(new OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })),
      terrainProvider: new EllipsoidTerrainProvider(),
      // Continuous rendering: requestRenderMode stalled imagery/terrain tile and async geometry loading.
      // Cesium's own error overlay would cover the whole UI; errors are reported non-blockingly instead.
      showRenderLoopErrors: false,
    })
    this.viewer.scene.globe.depthTestAgainstTerrain = true
    this.viewer.scene.renderError.addEventListener((_scene: unknown, error: unknown) => {
      this.callbacks.onRenderError(error instanceof Error ? error.message : String(error))
    })
    this.viewer.dataSources.add(this.floodSource)
    this.handler = new ScreenSpaceEventHandler(this.viewer.scene.canvas)
    this.handler.setInputAction((movement: ScreenSpaceEventHandler.PositionedEvent) => this.pick(movement.position), ScreenSpaceEventType.LEFT_CLICK)
  }

  // ---- static scene --------------------------------------------------------------------
  async loadStaticScene(): Promise<void> {
    // Ward first so the camera frames Ward 176 immediately (docs/08 §87).
    await this.loadLayer('boundary')
    this.fitWard(0)
    await Promise.allSettled([this.loadTerrain(), this.loadLayer('roads'), this.loadLayer('subcatchments'), this.loadLayer('drains')])
    await this.loadLayer('buildings')
  }

  private async loadTerrain(): Promise<void> {
    const started = performance.now()
    this.callbacks.onLayerState('terrain', { state: 'loading' })
    try {
      const grid = await this.loaders.terrain(this.abort.signal)
      if (this.destroyed) return
      this.demTerrain = createDemTerrainProvider(grid)
      if (this.terrainEnabled) this.viewer.terrainProvider = this.demTerrain
      this.callbacks.onLayerState('terrain', { state: 'ready', featureCount: grid.statistics.validCells, loadMs: Math.round(performance.now() - started) })
      this.render()
    } catch (error) {
      if (!this.destroyed) this.callbacks.onLayerState('terrain', { state: 'error', message: (error as Error).message })
    }
  }

  private async loadLayer(key: StaticLayer): Promise<void> {
    const started = performance.now()
    this.callbacks.onLayerState(key, { state: 'loading' })
    try {
      const fc = await this.loaders.layer(API_LAYER[key], this.abort.signal)
      if (this.destroyed) return
      const source = new CustomDataSource(key)
      source.entities.suspendEvents()
      for (const feature of fc.features) this.addStaticFeature(key, source, feature)
      source.entities.resumeEvents()
      await this.viewer.dataSources.add(source)
      source.show = this.pendingVisibility.get(key) ?? true
      this.layers.set(key, source)
      if (key === 'buildings') this.updateBuildingContrast()
      if (key === 'boundary') this.wardBbox = (fc.metadata?.bbox as [number, number, number, number] | undefined) ?? bboxOf(fc.features)
      this.callbacks.onLayerState(key, { state: 'ready', featureCount: fc.features.length, loadMs: Math.round(performance.now() - started) })
      this.render()
    } catch (error) {
      if (!this.destroyed && !(error instanceof DOMException && error.name === 'AbortError')) {
        this.callbacks.onLayerState(key, { state: 'error', message: (error as Error).message })
      }
    }
  }

  private addStaticFeature(key: StaticLayer, source: CustomDataSource, feature: FeatureCollection['features'][number]): void {
    const props = feature.properties
    const idValue = key === 'subcatchments' ? props.subcatchmentId : props.objectId
    const ref: FeatureRef = { feature: { layer: key, id: String(idValue ?? feature.id), properties: props }, entities: [] }
    const add = (options: Entity.ConstructorOptions) => {
      const entity = source.entities.add(options)
      ref.entities.push(entity)
      this.featureByEntity.set(entity, ref)
    }
    switch (key) {
      case 'buildings':
        for (const hierarchy of polygonHierarchies(feature.geometry)) {
          add({
            polygon: {
              hierarchy,
              material: LAYER_COLORS.building,
              height: 0,
              heightReference: HeightReference.CLAMP_TO_GROUND,
              extrudedHeight: BUILDING_VISUAL_EXTRUSION_M,
              extrudedHeightReference: HeightReference.RELATIVE_TO_GROUND,
            },
          })
        }
        break
      case 'roads':
      case 'subcatchments':
        for (const hierarchy of polygonHierarchies(feature.geometry)) {
          add({ polygon: { hierarchy, material: key === 'roads' ? LAYER_COLORS.road : LAYER_COLORS.subcatchment } })
        }
        break
      case 'boundary':
        for (const part of lineParts(feature.geometry)) add({ polyline: { positions: part, width: 3, clampToGround: true, material: LAYER_COLORS.boundary } })
        break
      case 'drains': {
        const color = props.inHydraulicModel ? LAYER_COLORS.drainModelled : LAYER_COLORS.drainNotModelled
        for (const part of lineParts(feature.geometry)) add({ polyline: { positions: part, width: 3.5, clampToGround: true, material: color } })
        break
      }
    }
  }

  // ---- visibility / settings ---------------------------------------------------------------

  setLayerVisible(key: LayerKey, visible: boolean): void {
    if (key === 'terrain') {
      this.terrainEnabled = visible
      this.viewer.terrainProvider = visible && this.demTerrain ? this.demTerrain : new EllipsoidTerrainProvider()
    } else if (key === 'flood') {
      this.floodSource.show = visible
      this.updateBuildingContrast()
    } else {
      this.pendingVisibility.set(key, visible)
      const source = this.layers.get(key)
      if (source) source.show = visible
      if (!visible && this.selected?.ref.feature.layer === key) this.clearSelection()
    }
    this.render()
  }

  setVerticalExaggeration(value: number): void {
    this.viewer.scene.verticalExaggeration = value
    this.render()
  }

  // ---- flood (dynamic) --------------------------------------------------------------------------
  /** Replace the flood layer content with one backend time slice (null clears it). */
  setFloodSlice(fc: FeatureCollection<FloodFeatureProperties> | null): void {
    if (this.selected?.ref.feature.layer === 'flood') this.clearSelection()
    this.floodFeatures = fc
    const entities = this.floodSource.entities
    entities.suspendEvents()
    entities.removeAll()
    this.floodFeatureByEntity.clear()
    if (fc) {
      // Zones first, then node markers on top.
      const ordered = [...fc.features].sort((a, b) => (a.properties.featureType === 'node' ? 1 : 0) - (b.properties.featureType === 'node' ? 1 : 0))
      for (const feature of ordered) {
        const p = feature.properties
        const ref: FeatureRef = { feature: { layer: 'flood', id: `${p.featureType}:${p.nodeId}`, properties: p as unknown as Record<string, unknown> }, entities: [] }
        if (p.featureType === 'influenceZone') {
          for (const hierarchy of polygonHierarchies(feature.geometry)) {
            const e = entities.add({ polygon: { hierarchy, material: floodColor(p.state, p.overflowClass, this.floodOpacity * 0.7) } })
            ref.entities.push(e)
            this.floodFeatureByEntity.set(e, ref)
          }
        } else if (feature.geometry.type === 'Point') {
          const [lon, lat] = feature.geometry.coordinates
          const e = entities.add({
            position: Cartesian3.fromDegrees(lon, lat),
            point: {
              pixelSize: p.state === 'FLOODING' ? 12 : 9,
              color: floodColor(p.state, p.overflowClass, 1),
              outlineColor: LAYER_COLORS.boundary.withAlpha(0.9),
              outlineWidth: 1.5,
              heightReference: HeightReference.CLAMP_TO_GROUND,
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
            },
          })
          ref.entities.push(e)
          this.floodFeatureByEntity.set(e, ref)
        }
      }
    }
    entities.resumeEvents()
    this.updateBuildingContrast()
    this.render()
  }

  /**
   * Visual aid: flood influence zones are draped on the ground and would be hidden by extruded
   * buildings, so buildings are drawn semi-transparent while a flood slice is shown.
   */
  private updateBuildingContrast(): void {
    const wanted = this.floodSource.show && this.currentFloodFeatureCount > 0
    const buildings = this.layers.get('buildings')
    if (!buildings || wanted === this.buildingsTranslucent) return
    this.buildingsTranslucent = wanted
    const color = wanted ? LAYER_COLORS.buildingUnderFlood : LAYER_COLORS.building
    const material = new ColorMaterialProperty(color)
    buildings.entities.suspendEvents()
    for (const e of buildings.entities.values) if (e.polygon && this.selected?.ref.entities.includes(e) !== true) e.polygon.material = material
    buildings.entities.resumeEvents()
  }

  setFloodOpacity(opacity: number): void {
    this.floodOpacity = opacity
    for (const [entity, ref] of this.floodFeatureByEntity) {
      const p = ref.feature.properties as unknown as FloodFeatureProperties
      if (entity.polygon) entity.polygon.material = new ColorMaterialProperty(floodColor(p.state, p.overflowClass, opacity * 0.7))
    }
    this.render()
  }

  get currentFloodFeatureCount(): number {
    return this.floodFeatures?.features.length ?? 0
  }

  // ---- camera ----------------------------------------------------------------------------------
  fitWard(duration = 1.2): void {
    if (!this.wardBbox) return
    const [w, s, e, n] = this.wardBbox
    const sphere = BoundingSphere.fromPoints([Cartesian3.fromDegrees(w, s), Cartesian3.fromDegrees(e, s), Cartesian3.fromDegrees(e, n), Cartesian3.fromDegrees(w, n)])
    this.viewer.camera.flyToBoundingSphere(sphere, { duration, offset: new HeadingPitchRange(0, CesiumMath.toRadians(-50), sphere.radius * 2.6) })
    this.render()
  }

  resetView(): void {
    this.clearSelection()
    this.fitWard(0.8)
  }

  // ---- selection -------------------------------------------------------------------------------
  private pick(position: { x: number; y: number }): void {
    const picked = this.viewer.scene.pick(position as never)
    const entity = defined(picked) && picked.id instanceof Entity ? picked.id : null
    const ref = entity ? this.featureByEntity.get(entity) ?? this.floodFeatureByEntity.get(entity) : undefined
    if (!ref) {
      this.clearSelection()
      return
    }
    this.highlight(ref)
    this.callbacks.onSelect(ref.feature)
  }

  private highlight(ref: FeatureRef): void {
    this.restoreSelection()
    const originals = ref.entities.map((e) => {
      if (e.polygon) {
        const original = e.polygon.material
        e.polygon.material = new ColorMaterialProperty(LAYER_COLORS.highlight.withAlpha(0.85))
        return original
      }
      if (e.polyline) {
        const original = e.polyline.material
        e.polyline.material = new ColorMaterialProperty(LAYER_COLORS.highlight)
        return original
      }
      return undefined
    })
    this.selected = { ref, originals }
    this.render()
  }

  private restoreSelection(): void {
    if (!this.selected) return
    this.selected.ref.entities.forEach((e, i) => {
      const original = this.selected?.originals[i] as MaterialProperty | undefined
      if (e.polygon && original) e.polygon.material = original
      if (e.polyline && original) e.polyline.material = original
    })
    this.selected = null
  }

  clearSelection(): void {
    const had = this.selected !== null
    this.restoreSelection()
    if (had) this.callbacks.onSelect(null)
    this.render()
  }

  // ---- lifecycle -------------------------------------------------------------------------------
  /** Resume Cesium's render loop after a render error (Cesium stops it on error). */
  restartRendering(): void {
    if (this.destroyed) return
    this.callbacks.onRenderError(null)
    this.viewer.useDefaultRenderLoop = true
  }

  private render(): void {
    if (!this.destroyed) this.viewer.scene.requestRender()
  }

  destroy(): void {
    this.destroyed = true
    this.abort.abort()
    this.handler.destroy()
    this.featureByEntity.clear()
    this.floodFeatureByEntity.clear()
    if (!this.viewer.isDestroyed()) this.viewer.destroy()
  }
}
