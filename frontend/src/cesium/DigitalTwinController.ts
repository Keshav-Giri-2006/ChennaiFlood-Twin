import {
  BoundingSphere,
  CallbackProperty,
  Cartesian2,
  Cartesian3,
  Color,
  ArcType,
  ColorMaterialProperty,
  ConstantProperty,
  CustomDataSource,
  DistanceDisplayCondition,
  EllipsoidTerrainProvider,
  Entity,
  HeadingPitchRange,
  HeightReference,
  ImageryLayer,
  LabelStyle,
  Math as CesiumMath,
  OpenStreetMapImageryProvider,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  VerticalOrigin,
  Viewer,
  defined,
  type MaterialProperty,
  type TerrainProvider,
} from 'cesium'
import type { BottleneckFeatureProperties, BottleneckSeverity, ExposureAssetType, NodeSplit } from '../types/api'
import type { FeatureCollection, FloodFeatureProperties, Geometry, TerrainGrid } from '../types/gis'
import type { LayerKey, LayerLoadState, SelectedFeature } from '../state/viewerStore'
import { bboxOf, lineParts, linePartsAt, polygonHierarchies, polygonHierarchiesAt } from './geometry'
import { BOTTLENECK_COLORS, BOTTLENECK_INACTIVE_COLOR, BOTTLENECK_WIDTH, BUILDING_VISUAL_EXTRUSION_M, COMPARISON_COLORS, EXPOSURE_COLORS, LAYER_COLORS, NODE_MARKER, floodColor, floodCss } from './styles'
import { createDemTerrainProvider, sampleDem } from './terrain'

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

/** A flooding node connected to a potential bottleneck (location from the backend evidence record). */
export interface BottleneckNodeMarker {
  nodeId: string
  lon: number
  lat: number
}

interface FeatureRef {
  feature: SelectedFeature
  entities: Entity[]
}

type Material = MaterialProperty | undefined

/** Draping offsets (m) above the DEM surface; drains sit above carriageways, the ward outline above both. */
const DRAPE_OFFSET = { subcatchments: 0.3, roads: 0.5, drains: 1.0, boundary: 1.5 }

/** Fade-in of a newly shown flood time slice (ms). Visual transition only; no value is interpolated. */
const FLOOD_FADE_MS = 320

/** Pulse period (ms) and width (px) of the selected potential bottleneck glow. */
const EMPHASIS_PULSE_MS = 2200
const EMPHASIS_WIDTH = 22

const MATERIALS = {
  building: new ColorMaterialProperty(LAYER_COLORS.building),
  buildingTranslucent: new ColorMaterialProperty(LAYER_COLORS.buildingUnderFlood),
  buildingExposed: new ColorMaterialProperty(Color.fromCssColorString(EXPOSURE_COLORS.building).withAlpha(0.95)),
  buildingExposedTranslucent: new ColorMaterialProperty(Color.fromCssColorString(EXPOSURE_COLORS.building).withAlpha(0.7)),
  road: new ColorMaterialProperty(LAYER_COLORS.road),
  roadExposed: new ColorMaterialProperty(Color.fromCssColorString(EXPOSURE_COLORS.road).withAlpha(0.9)),
}

/**
 * Owns the single Cesium Viewer and everything drawn in it (docs/08 §7–§9).
 * React calls these methods; it never recreates the viewer on state changes.
 * Static layers are loaded once; flood, bottleneck, exposure and focus overlays only update
 * their own entities (or entity materials) when timeline/decision state changes.
 */
export class DigitalTwinController {
  readonly viewer: Viewer
  private readonly loaders: ControllerLoaders
  private readonly callbacks: ControllerCallbacks
  private readonly abort = new AbortController()
  private readonly handler: ScreenSpaceEventHandler
  private readonly layers = new Map<StaticLayer, CustomDataSource>()
  private readonly floodSource = new CustomDataSource('flood')
  private readonly bottleneckSource = new CustomDataSource('bottlenecks')
  private readonly focusSource = new CustomDataSource('focus')
  private readonly comparisonSource = new CustomDataSource('comparison')
  /** All SWMM model nodes as small muted markers, so state changes read against a "normal" baseline. */
  private readonly nodeSource = new CustomDataSource('nodes')
  /** Emphasis overlay for the potential bottleneck currently being explained (visual only). */
  private readonly emphasisSource = new CustomDataSource('emphasis')
  private emphasisedLinkId: string | null = null
  private modelNodesLoaded = false
  /** Start of the current flood slice fade-in (performance clock, ms); visual transition only. */
  private floodFadeStart = 0
  /** Per potential bottleneck: severity-coloured line entities and label, for time-aware restyling. */
  private readonly bottleneckStyle = new Map<string, { severity: BottleneckSeverity; lines: Entity[]; label: Entity | null }>()
  private bottleneckStateKey = ''
  private bottleneckTimeState: Record<string, BottleneckSeverity> | null = null
  private readonly comparisonZones = new Map<string, Entity[]>()
  private comparisonZonesSource: FeatureCollection | null = null
  private comparisonKey = ''
  private readonly featureByEntity = new Map<Entity, FeatureRef>()
  private readonly floodFeatureByEntity = new Map<Entity, FeatureRef>()
  private readonly bottleneckFeatureByEntity = new Map<Entity, FeatureRef>()
  private readonly assetEntities: Record<ExposureAssetType, Map<number, Entity[]>> = { buildings: new Map(), roads: new Map() }
  private readonly exposed: Record<ExposureAssetType, Set<number>> = { buildings: new Set(), roads: new Set() }
  /** Visibility requested before a layer finished loading. */
  private readonly pendingVisibility = new Map<StaticLayer, boolean>()
  private demTerrain: TerrainProvider | null = null
  private terrainGrid: TerrainGrid | null = null
  private exaggeration = 1
  /**
   * Performance (docs/PERFORMANCE_NOTES.md): roads, drains, subcatchments and the ward outline are drawn
   * as ordinary primitives at DEM-sampled heights instead of ground-clamped classification geometry,
   * which cost ~95 ms per frame on the demo iGPU. Their lon/lat geometry is kept here so heights can be
   * recomputed when terrain or exaggeration changes; the data itself is never altered or reduced.
   */
  private readonly draped = new Map<Entity, { kind: 'polygon' | 'polyline'; geometry: FeatureCollection['features'][number]['geometry']; part: number; offset: number }>()
  readonly staticRenderingMode = 'terrain-sampled-primitives'
  private terrainEnabled = true
  private wardBbox: [number, number, number, number] | null = null
  private selected: { ref: FeatureRef; originals: Material[] } | null = null
  private floodOpacity = 0.55
  private floodFeatures: FeatureCollection<FloodFeatureProperties> | null = null
  private bottleneckFeatures: FeatureCollection<BottleneckFeatureProperties> | null = null
  private destroyed = false
  private buildingsTranslucent = false
  /** Diagnostic counters (exposed for performance inspection). */
  readonly stats = { floodSliceUpdates: 0, lastFloodSliceMs: 0, exposureUpdates: 0, lastExposureChanged: 0, staticLayerLoads: 0, bottleneckStateUpdates: 0, comparisonUpdates: 0 }

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
      // OpenStreetMap context imagery; avoids Cesium Ion services and tokens. OSM serves zoom <= 19
      // (requests beyond that fail without CORS headers).
      baseLayer: new ImageryLayer(new OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/', maximumLevel: 19 })),
      terrainProvider: new EllipsoidTerrainProvider(),
      // Continuous rendering: requestRenderMode stalled imagery/terrain tile and async geometry loading.
      // Cesium's own error overlay would cover the whole UI; errors are reported non-blockingly instead.
      showRenderLoopErrors: false,
    })
    this.viewer.scene.globe.depthTestAgainstTerrain = true
    this.viewer.scene.renderError.addEventListener((_scene: unknown, error: unknown) => {
      this.callbacks.onRenderError(error instanceof Error ? error.message : String(error))
    })
    this.viewer.dataSources.add(this.nodeSource)
    this.viewer.dataSources.add(this.floodSource)
    this.viewer.dataSources.add(this.bottleneckSource)
    this.viewer.dataSources.add(this.focusSource)
    this.viewer.dataSources.add(this.emphasisSource)
    this.viewer.dataSources.add(this.comparisonSource)
    this.comparisonSource.show = false
    this.bottleneckSource.show = false
    this.handler = new ScreenSpaceEventHandler(this.viewer.scene.canvas)
    this.handler.setInputAction((movement: ScreenSpaceEventHandler.PositionedEvent) => this.pick(movement.position), ScreenSpaceEventType.LEFT_CLICK)
  }

  // ---- static scene --------------------------------------------------------------------
  async loadStaticScene(): Promise<void> {
    // Ward first so the camera frames Ward 176 immediately (docs/08 §87).
    await this.loadLayer('boundary')
    this.fitWard(0)
    // Terrain heights are needed to drape roads/drains, so the DEM grid loads first (it is small, ~2 kB of heights).
    await this.loadTerrain()
    this.redrapeStaticLayers()
    await Promise.allSettled([this.loadLayer('roads'), this.loadLayer('subcatchments'), this.loadLayer('drains')])
    await this.loadLayer('buildings')
  }

  private async loadTerrain(): Promise<void> {
    const started = performance.now()
    this.callbacks.onLayerState('terrain', { state: 'loading' })
    try {
      const grid = await this.loaders.terrain(this.abort.signal)
      if (this.destroyed) return
      this.terrainGrid = grid
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
      this.stats.staticLayerLoads += 1
      if (key === 'buildings' || key === 'roads') this.refreshAssetMaterials(key)
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
      if (key === 'buildings' || key === 'roads') {
        const objectId = Number(props.objectId)
        const list = this.assetEntities[key].get(objectId) ?? []
        list.push(entity)
        this.assetEntities[key].set(objectId, list)
      }
    }
    switch (key) {
      case 'buildings':
        for (const hierarchy of polygonHierarchies(feature.geometry)) {
          add({
            polygon: {
              hierarchy,
              material: MATERIALS.building,
              height: 0,
              heightReference: HeightReference.CLAMP_TO_GROUND,
              extrudedHeight: BUILDING_VISUAL_EXTRUSION_M,
              extrudedHeightReference: HeightReference.RELATIVE_TO_GROUND,
            },
          })
        }
        break
      case 'roads':
      case 'subcatchments': {
        const offset = key === 'roads' ? DRAPE_OFFSET.roads : DRAPE_OFFSET.subcatchments
        const material = key === 'roads' ? MATERIALS.road : LAYER_COLORS.subcatchment
        polygonHierarchiesAt(feature.geometry, this.heightFn(offset)).forEach((hierarchy, part) => {
          add({ polygon: { hierarchy, perPositionHeight: true, material } })
          this.draped.set(ref.entities[ref.entities.length - 1], { kind: 'polygon', geometry: feature.geometry, part, offset })
        })
        break
      }
      case 'boundary':
      case 'drains': {
        const offset = key === 'drains' ? DRAPE_OFFSET.drains : DRAPE_OFFSET.boundary
        const color = key === 'boundary' ? LAYER_COLORS.boundary : props.inHydraulicModel ? LAYER_COLORS.drainModelled : LAYER_COLORS.drainNotModelled
        linePartsAt(feature.geometry, this.heightFn(offset)).forEach((positions, part) => {
          add({ polyline: { positions, width: key === 'drains' ? 3.5 : 3, arcType: ArcType.NONE, material: color } })
          this.draped.set(ref.entities[ref.entities.length - 1], { kind: 'polyline', geometry: feature.geometry, part, offset })
        })
        break
      }
    }
  }

  // ---- visibility / settings ---------------------------------------------------------------

  setLayerVisible(key: LayerKey, visible: boolean): void {
    if (key === 'terrain') {
      this.terrainEnabled = visible
      this.viewer.terrainProvider = visible && this.demTerrain ? this.demTerrain : new EllipsoidTerrainProvider()
      this.redrapeStaticLayers()
    } else if (key === 'flood') {
      this.floodSource.show = visible
      this.updateBuildingContrast()
    } else if (key === 'rain') {
      // The rainfall visualisation is a screen-space overlay outside the Cesium scene (see RainOverlay).
    } else if (key === 'nodes') {
      this.nodeSource.show = visible
    } else if (key === 'comparison') {
      this.comparisonSource.show = visible
    } else if (key === 'bottlenecks') {
      this.bottleneckSource.show = visible
      if (!visible && this.selected?.ref.feature.layer === 'bottlenecks') this.clearSelection()
    } else if (key === 'exposureBuildings' || key === 'exposureRoads') {
      // Exposure is a highlight of existing building/road entities; data arrives via setExposedAssets.
      if (!visible) this.setExposedAssets(key === 'exposureBuildings' ? 'buildings' : 'roads', null)
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
    if (value !== this.exaggeration) {
      this.exaggeration = value
      this.redrapeStaticLayers()
    }
    this.render()
  }

  /** Height (m) of a draped vertex: the same DEM sampling the terrain provider uses, exaggerated, plus a small offset. */
  private heightFn(offset: number): (lon: number, lat: number) => number {
    const grid = this.terrainEnabled ? this.terrainGrid : null
    const factor = this.exaggeration
    return (lon, lat) => (grid ? (sampleDem(grid, lon, lat) ?? 0) * factor : 0) + offset
  }

  /** Recompute draped positions after a terrain or exaggeration change (static data is not reloaded). */
  private redrapeStaticLayers(): void {
    for (const [entity, d] of this.draped) {
      const height = this.heightFn(d.offset)
      if (d.kind === 'polygon' && entity.polygon) {
        entity.polygon.hierarchy = new ConstantProperty(polygonHierarchiesAt(d.geometry, height)[d.part]) as never
      } else if (d.kind === 'polyline' && entity.polyline) {
        entity.polyline.positions = new ConstantProperty(linePartsAt(d.geometry, height)[d.part]) as never
      }
    }
    this.render()
  }

  // ---- model nodes (context for node states) -------------------------------------------------------
  /** All SWMM model nodes drawn small and muted; flood slices draw the stressed ones on top. */
  setModelNodes(fc: FeatureCollection | null): void {
    if (this.modelNodesLoaded || !fc) return
    const entities = this.nodeSource.entities
    entities.suspendEvents()
    entities.removeAll()
    const color = Color.fromCssColorString(NODE_MARKER.normal.color).withAlpha(NODE_MARKER.normal.alpha)
    for (const feature of fc.features) {
      if (feature.geometry.type !== 'Point') continue
      const [lon, lat] = feature.geometry.coordinates as [number, number]
      entities.add({
        position: Cartesian3.fromDegrees(lon, lat),
        point: { pixelSize: NODE_MARKER.normal.pixelSize, color, heightReference: HeightReference.CLAMP_TO_GROUND, disableDepthTestDistance: Number.POSITIVE_INFINITY },
      })
    }
    entities.resumeEvents()
    this.modelNodesLoaded = true
    this.callbacks.onLayerState('nodes', { state: 'ready', featureCount: entities.values.length })
    this.render()
  }

  // ---- flood (dynamic) --------------------------------------------------------------------------
  /** Replace the flood layer content with one backend time slice (null clears it). Static layers are untouched. */
  setFloodSlice(fc: FeatureCollection<FloodFeatureProperties> | null): void {
    if (fc === this.floodFeatures) return
    const started = performance.now()
    this.floodFadeStart = started
    const reselect = this.selected?.ref.feature.layer === 'flood' ? this.selected.ref.feature.id : null
    if (reselect) this.restoreSelection()
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
        const ref: FeatureRef = { feature: { layer: 'flood', id: `${p.featureType}:${p.nodeId}`, properties: { ...p, time: fc.metadata?.time } as unknown as Record<string, unknown> }, entities: [] }
        if (p.featureType === 'influenceZone') {
          for (const hierarchy of polygonHierarchies(feature.geometry)) {
            const e = entities.add({ polygon: { hierarchy, material: this.zoneMaterial(p) } })
            ref.entities.push(e)
            this.floodFeatureByEntity.set(e, ref)
          }
        } else if (feature.geometry.type === 'Point') {
          const [lon, lat] = feature.geometry.coordinates
          const e = entities.add({
            position: Cartesian3.fromDegrees(lon, lat),
            point: {
              pixelSize: this.nodePixelSize(p),
              color: floodColor(p.state, p.overflowClass, 1),
              outlineColor: p.state === 'FLOODING' ? Color.WHITE.withAlpha(0.95) : LAYER_COLORS.boundary.withAlpha(0.9),
              outlineWidth: p.state === 'FLOODING' ? NODE_MARKER.flooding.outlineWidth : NODE_MARKER.surcharged.outlineWidth,
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
    // Keep an inspected flood feature selected across timesteps when it still exists; otherwise clear it.
    if (reselect) {
      const ref = [...new Set(this.floodFeatureByEntity.values())].find((r) => r.feature.id === reselect)
      if (ref) {
        this.highlight(ref)
        this.callbacks.onSelect(ref.feature)
      } else {
        this.callbacks.onSelect(null)
      }
    }
    this.updateBuildingContrast()
    this.stats.floodSliceUpdates += 1
    this.stats.lastFloodSliceMs = Math.round((performance.now() - started) * 10) / 10
    this.render()
  }

  /**
   * Visual aid: flood influence zones are draped on the ground and would be hidden by extruded
   * buildings, so buildings are drawn semi-transparent while a flood slice is shown.
   */
  private updateBuildingContrast(): void {
    const wanted = this.floodSource.show && this.currentFloodFeatureCount > 0
    if (wanted === this.buildingsTranslucent) return
    this.buildingsTranslucent = wanted
    this.refreshAssetMaterials('buildings')
  }

  setFloodOpacity(opacity: number): void {
    this.floodOpacity = opacity
    for (const [entity, ref] of this.floodFeatureByEntity) {
      if (this.selected?.ref === ref) continue
      const p = ref.feature.properties as unknown as FloodFeatureProperties
      if (entity.polygon) entity.polygon.material = this.zoneMaterial(p)
    }
    this.render()
  }

  /**
   * Influence-zone material with a short fade-in when a new time slice is shown. The fade is a visual
   * transition between the discrete SWMM reporting timesteps only: nothing is interpolated, and the
   * geometry and display classes are exactly those of the backend slice.
   */
  private zoneMaterial(p: FloodFeatureProperties): ColorMaterialProperty {
    const base = Color.fromCssColorString(floodCss(p.state, p.overflowClass))
    const target = this.floodOpacity * 0.7
    const fadeStart = this.floodFadeStart
    const scratch = new Color()
    return new ColorMaterialProperty(
      new CallbackProperty(() => {
        const progress = Math.min(1, (performance.now() - fadeStart) / FLOOD_FADE_MS)
        return Color.fromAlpha(base, target * progress, scratch)
      }, false),
    )
  }

  /**
   * Marker size per node state. Overflowing nodes are larger (scaled by the backend overflow display
   * class) and pulse slightly so stress is visible during playback; the classification is unchanged.
   */
  private nodePixelSize(p: FloodFeatureProperties): number | CallbackProperty {
    if (p.state !== 'FLOODING') return NODE_MARKER.surcharged.pixelSize
    const base = NODE_MARKER.flooding.pixelSize[p.overflowClass ?? 'LOW'] ?? NODE_MARKER.flooding.pixelSize.LOW
    const { pulseAmplitude, pulsePeriodMs } = NODE_MARKER.flooding
    return new CallbackProperty(() => base + pulseAmplitude * Math.sin((performance.now() / pulsePeriodMs) * Math.PI * 2), false)
  }

  get currentFloodFeatureCount(): number {
    return this.floodFeatures?.features.length ?? 0
  }

  // ---- model-derived exposure (highlight of existing entities) -----------------------------------
  private assetMaterial(type: ExposureAssetType, objectId: number): MaterialProperty {
    const exposed = this.exposed[type].has(objectId)
    if (type === 'roads') return exposed ? MATERIALS.roadExposed : MATERIALS.road
    if (this.buildingsTranslucent) return exposed ? MATERIALS.buildingExposedTranslucent : MATERIALS.buildingTranslucent
    return exposed ? MATERIALS.buildingExposed : MATERIALS.building
  }

  private applyMaterial(entity: Entity, material: MaterialProperty): void {
    const index = this.selected?.ref.entities.indexOf(entity) ?? -1
    if (this.selected && index >= 0) {
      this.selected.originals[index] = material // restored when the selection is cleared
    } else if (entity.polygon) {
      entity.polygon.material = material
    }
  }

  private refreshAssetMaterials(type: ExposureAssetType): void {
    const source = this.layers.get(type)
    if (!source) return
    source.entities.suspendEvents()
    for (const [objectId, list] of this.assetEntities[type]) {
      const material = this.assetMaterial(type, objectId)
      for (const e of list) this.applyMaterial(e, material)
    }
    source.entities.resumeEvents()
    this.render()
  }

  /**
   * Highlight the backend-reported exposed assets (null clears). Only entities whose exposure
   * status changed are updated, so timeline playback does not touch all 6,428 buildings.
   */
  setExposedAssets(type: ExposureAssetType, objectIds: number[] | null): number {
    const next = new Set(objectIds ?? [])
    const previous = this.exposed[type]
    const changed: number[] = []
    for (const id of previous) if (!next.has(id)) changed.push(id)
    for (const id of next) if (!previous.has(id)) changed.push(id)
    this.exposed[type] = next
    const source = this.layers.get(type)
    if (source && changed.length) {
      source.entities.suspendEvents()
      for (const id of changed) {
        const material = this.assetMaterial(type, id)
        for (const e of this.assetEntities[type].get(id) ?? []) this.applyMaterial(e, material)
      }
      source.entities.resumeEvents()
    }
    this.stats.exposureUpdates += 1
    this.stats.lastExposureChanged = changed.length
    this.render()
    return changed.length
  }

  exposedCount(type: ExposureAssetType): number {
    return this.exposed[type].size
  }

  // ---- potential bottlenecks (dynamic, per simulation) ------------------------------------------------
  setBottlenecks(fc: FeatureCollection<BottleneckFeatureProperties> | null, nodes: BottleneckNodeMarker[] = []): void {
    if (this.selected?.ref.feature.layer === 'bottlenecks') this.clearSelection()
    this.emphasiseBottleneck(null)
    this.bottleneckFeatures = fc
    const entities = this.bottleneckSource.entities
    entities.suspendEvents()
    entities.removeAll()
    this.bottleneckFeatureByEntity.clear()
    this.bottleneckStyle.clear()
    this.bottleneckStateKey = ''
    for (const feature of fc?.features ?? []) {
      const p = feature.properties
      const ref: FeatureRef = { feature: { layer: 'bottlenecks', id: p.linkId, properties: p as unknown as Record<string, unknown> }, entities: [] }
      const color = Color.fromCssColorString(BOTTLENECK_COLORS[p.severity] ?? BOTTLENECK_COLORS.LOW)
      const width = BOTTLENECK_WIDTH[p.severity] ?? 5
      const style = { severity: p.severity, lines: [] as Entity[], label: null as Entity | null }
      this.bottleneckStyle.set(p.linkId, style)
      for (const part of lineParts(feature.geometry)) {
        const casing = entities.add({ polyline: { positions: part, width: width + 4, clampToGround: true, zIndex: 10, material: Color.BLACK.withAlpha(0.75) } })
        const line = entities.add({ polyline: { positions: part, width, clampToGround: true, zIndex: 11, material: color } })
        style.lines.push(line)
        for (const e of [casing, line]) {
          ref.entities.push(e)
          this.bottleneckFeatureByEntity.set(e, ref)
        }
      }
      const mid = midpoint(feature.geometry)
      if (mid) {
        const label = entities.add({
          position: Cartesian3.fromDegrees(mid[0], mid[1]),
          label: {
            text: `${p.linkId}`,
            font: p.severity === 'LOW' ? '12px sans-serif' : 'bold 14px sans-serif',
            fillColor: color,
            outlineColor: Color.BLACK,
            outlineWidth: 3,
            style: LabelStyle.FILL_AND_OUTLINE,
            verticalOrigin: VerticalOrigin.BOTTOM,
            pixelOffset: new Cartesian2(0, -10),
            heightReference: HeightReference.CLAMP_TO_GROUND,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
            distanceDisplayCondition: p.severity === 'LOW' ? new DistanceDisplayCondition(0, 2500) : undefined,
          },
        })
        ref.entities.push(label)
        this.bottleneckFeatureByEntity.set(label, ref)
        style.label = label
      }
    }
    // Re-apply the latest time-aware state to the new entities.
    if (this.bottleneckTimeState) {
      const pending = this.bottleneckTimeState
      queueMicrotask(() => this.setBottleneckTimeState(pending))
    }
    // Connected overflowing nodes, so the user can follow bottleneck → node → flooding.
    for (const node of nodes) {
      entities.add({
        position: Cartesian3.fromDegrees(node.lon, node.lat),
        point: { pixelSize: 18, color: Color.TRANSPARENT, outlineColor: Color.WHITE, outlineWidth: 2.5, heightReference: HeightReference.CLAMP_TO_GROUND, disableDepthTestDistance: Number.POSITIVE_INFINITY },
        label: {
          text: node.nodeId,
          font: '12px sans-serif',
          fillColor: Color.WHITE,
          outlineColor: Color.BLACK,
          outlineWidth: 3,
          style: LabelStyle.FILL_AND_OUTLINE,
          pixelOffset: new Cartesian2(0, 18),
          heightReference: HeightReference.CLAMP_TO_GROUND,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          distanceDisplayCondition: new DistanceDisplayCondition(0, 2500),
        },
      })
    }
    entities.resumeEvents()
    this.render()
  }

  /**
   * Time-aware bottleneck styling (bottleneck-timeline-v1). ``active`` maps link IDs active at the
   * selected timestamp to their backend time severity; other potential bottlenecks are dimmed.
   * ``null`` restores the event-level colours. Only changed styles are applied.
   */
  setBottleneckTimeState(active: Record<string, BottleneckSeverity> | null): void {
    this.bottleneckTimeState = active
    const key = active === null ? 'event' : Object.entries(active).sort().map(([k, v]) => `${k}:${v}`).join('|')
    if (key === this.bottleneckStateKey) return
    this.bottleneckStateKey = key
    for (const [linkId, style] of this.bottleneckStyle) {
      const severity = active === null ? style.severity : active[linkId]
      const color = severity ? Color.fromCssColorString(BOTTLENECK_COLORS[severity]) : Color.fromCssColorString(BOTTLENECK_INACTIVE_COLOR).withAlpha(0.55)
      const material = new ColorMaterialProperty(color)
      for (const line of style.lines) {
        const index = this.selected?.ref.entities.indexOf(line) ?? -1
        if (this.selected && index >= 0) this.selected.originals[index] = material
        else if (line.polyline) line.polyline.material = material
      }
      if (style.label?.label) style.label.label.fillColor = new ConstantProperty(color) as never
    }
    this.stats.bottleneckStateUpdates += 1
    this.render()
  }

  get bottleneckCount(): number {
    return this.bottleneckFeatures?.features.length ?? 0
  }

  /** "View Hotspots": fit the camera to the actual potential bottleneck geometry. */
  fitBottlenecks(duration = 1.2): boolean {
    const points = (this.bottleneckFeatures?.features ?? []).flatMap((f) => coordinates(f.geometry))
    return this.flyToLonLats(points, duration)
  }

  selectBottleneck(linkId: string): boolean {
    const ref = [...new Set(this.bottleneckFeatureByEntity.values())].find((r) => r.feature.id === linkId)
    if (!ref) return false
    this.highlight(ref)
    this.emphasiseBottleneck(linkId)
    this.callbacks.onSelect(ref.feature)
    return true
  }

  get emphasisedBottleneck(): string | null {
    return this.emphasisedLinkId
  }

  /**
   * Visual emphasis of the conduit a bottleneck explanation is about (e.g. C169, J161 -> J177):
   * a pulsing glow along the backend conduit geometry plus rings and labels at its two model junctions.
   * Purely presentational: it adds no analysis and does not change severity, confidence or classification.
   * ``null`` clears it.
   */
  emphasiseBottleneck(linkId: string | null): boolean {
    if (linkId === this.emphasisedLinkId) return linkId !== null
    this.emphasisedLinkId = linkId
    const entities = this.emphasisSource.entities
    entities.suspendEvents()
    entities.removeAll()
    const feature = linkId ? this.bottleneckFeatures?.features.find((f) => f.properties.linkId === linkId) : undefined
    if (!feature) {
      entities.resumeEvents()
      this.emphasisedLinkId = feature ? linkId : null
      this.render()
      return false
    }
    const p = feature.properties
    const color = Color.fromCssColorString(BOTTLENECK_COLORS[p.severity] ?? BOTTLENECK_COLORS.LOW)
    const glow = new ColorMaterialProperty(
      new CallbackProperty((_time, result) => {
        const pulse = 0.35 + 0.25 * (0.5 + 0.5 * Math.sin((performance.now() / EMPHASIS_PULSE_MS) * Math.PI * 2))
        return Color.fromAlpha(color, pulse, result as Color | undefined)
      }, false),
    )
    const parts = lineParts(feature.geometry)
    for (const part of parts) {
      entities.add({ polyline: { positions: part, width: EMPHASIS_WIDTH, clampToGround: true, zIndex: 5, material: glow } })
    }
    const ends = coordinates(feature.geometry)
    const junctions: [string | undefined, [number, number] | undefined][] = [
      [p.fromNodeId, ends[0]],
      [p.toNodeId, ends[ends.length - 1]],
    ]
    for (const [nodeId, position] of junctions) {
      if (!nodeId || !position) continue
      entities.add({
        position: Cartesian3.fromDegrees(position[0], position[1]),
        point: { pixelSize: 20, color: Color.TRANSPARENT, outlineColor: color, outlineWidth: 3, heightReference: HeightReference.CLAMP_TO_GROUND, disableDepthTestDistance: Number.POSITIVE_INFINITY },
        label: {
          text: nodeId,
          font: 'bold 12px sans-serif',
          fillColor: Color.WHITE,
          outlineColor: Color.BLACK,
          outlineWidth: 3,
          style: LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: VerticalOrigin.TOP,
          pixelOffset: new Cartesian2(0, 14),
          heightReference: HeightReference.CLAMP_TO_GROUND,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      })
    }
    entities.resumeEvents()
    this.render()
    return true
  }

  // ---- scenario comparison (categorical influence per node) -----------------------------------------
  /**
   * Shows influence zones of nodes overflowing in both runs, only in the scenario ("additional
   * model-derived flood influence") or only in the baseline. Zone polygons are created once per
   * zones collection and only re-styled when the backend node split changes.
   */
  setComparison(zones: FeatureCollection | null, split: NodeSplit | null): void {
    if (zones !== this.comparisonZonesSource) {
      this.comparisonZonesSource = zones
      this.comparisonKey = ''
      const entities = this.comparisonSource.entities
      entities.suspendEvents()
      entities.removeAll()
      this.comparisonZones.clear()
      for (const feature of zones?.features ?? []) {
        const nodeId = String(feature.properties.nodeId)
        const list: Entity[] = []
        for (const hierarchy of polygonHierarchies(feature.geometry)) list.push(entities.add({ show: false, polygon: { hierarchy, material: Color.TRANSPARENT } }))
        this.comparisonZones.set(nodeId, list)
      }
      entities.resumeEvents()
    }
    const key = split ? `${split.both.join()}|${split.scenarioOnly.join()}|${split.baselineOnly.join()}` : 'none'
    if (key === this.comparisonKey) return
    this.comparisonKey = key
    const category = new Map<string, keyof typeof COMPARISON_COLORS>()
    for (const n of split?.both ?? []) category.set(n, 'both')
    for (const n of split?.scenarioOnly ?? []) category.set(n, 'scenarioOnly')
    for (const n of split?.baselineOnly ?? []) category.set(n, 'baselineOnly')
    this.comparisonSource.entities.suspendEvents()
    for (const [nodeId, list] of this.comparisonZones) {
      const c = category.get(nodeId)
      for (const e of list) {
        e.show = Boolean(c)
        if (c && e.polygon) e.polygon.material = new ColorMaterialProperty(Color.fromCssColorString(COMPARISON_COLORS[c]).withAlpha(0.55))
      }
    }
    this.comparisonSource.entities.resumeEvents()
    this.stats.comparisonUpdates += 1
    this.render()
  }

  // ---- performance profiling ----------------------------------------------------------------------
  /** Frame statistics over ``ms`` of the normal render loop (requires a visible browser tab). */
  async profileFrames(ms = 5000): Promise<{ frames: number; seconds: number; fps: number; p50FrameMs: number | null; p95FrameMs: number | null; visibility: DocumentVisibilityState }> {
    const stamps: number[] = []
    const listener = () => stamps.push(performance.now())
    this.viewer.scene.postRender.addEventListener(listener)
    const started = performance.now()
    await new Promise((resolve) => setTimeout(resolve, ms))
    this.viewer.scene.postRender.removeEventListener(listener)
    const seconds = (performance.now() - started) / 1000
    const deltas = stamps.slice(1).map((t, i) => t - stamps[i]).sort((a, b) => a - b)
    const pick = (q: number) => (deltas.length ? Math.round(deltas[Math.min(deltas.length - 1, Math.floor(q * deltas.length))] * 10) / 10 : null)
    return { frames: stamps.length, seconds: Math.round(seconds * 10) / 10, fps: Math.round((stamps.length / seconds) * 10) / 10, p50FrameMs: pick(0.5), p95FrameMs: pick(0.95), visibility: document.visibilityState }
  }

  /** Entity counts per data source (static layers are loaded once; dynamic ones change). */
  entityCounts(): Record<string, number> {
    const counts: Record<string, number> = {}
    for (let i = 0; i < this.viewer.dataSources.length; i += 1) {
      const ds = this.viewer.dataSources.get(i)
      counts[ds.name] = ds.entities.values.length
    }
    return counts
  }

  // ---- focus (recommendation evidence) -------------------------------------------------------------
  /** Draw evidence geometry (links as lines, nodes as rings) and fly to it. Returns false if nothing to show. */
  focusOn(lines: Geometry[], points: [number, number][], duration = 1.2): boolean {
    const entities = this.focusSource.entities
    entities.suspendEvents()
    entities.removeAll()
    for (const geometry of lines) {
      for (const part of lineParts(geometry)) entities.add({ polyline: { positions: part, width: 12, clampToGround: true, zIndex: 20, material: LAYER_COLORS.focus.withAlpha(0.6) } })
    }
    for (const [lon, lat] of points) {
      entities.add({
        position: Cartesian3.fromDegrees(lon, lat),
        point: { pixelSize: 24, color: Color.TRANSPARENT, outlineColor: LAYER_COLORS.focus, outlineWidth: 3, heightReference: HeightReference.CLAMP_TO_GROUND, disableDepthTestDistance: Number.POSITIVE_INFINITY },
      })
    }
    entities.resumeEvents()
    return this.flyToLonLats([...lines.flatMap(coordinates), ...points], duration)
  }

  clearFocus(): void {
    this.focusSource.entities.removeAll()
    this.render()
  }

  // ---- camera ----------------------------------------------------------------------------------
  fitWard(duration = 1.2): void {
    if (!this.wardBbox) return
    const [w, s, e, n] = this.wardBbox
    this.flyToLonLats([[w, s], [e, s], [e, n], [w, n]], duration, 2.6)
  }

  /** Fly to lon/lat points (explicit user action only; timeline changes never move the camera). */
  flyToLonLats(points: [number, number][], duration = 1.2, rangeFactor = 3): boolean {
    if (!points.length) return false
    const sphere = BoundingSphere.fromPoints(points.map(([lon, lat]) => Cartesian3.fromDegrees(lon, lat)))
    const range = Math.max(sphere.radius * rangeFactor, 250)
    this.viewer.camera.flyToBoundingSphere(sphere, { duration, offset: new HeadingPitchRange(0, CesiumMath.toRadians(-50), range) })
    this.render()
    return true
  }

  flyToGeometries(geometries: Geometry[], points: [number, number][] = [], duration = 1.2): boolean {
    return this.flyToLonLats([...geometries.flatMap(coordinates), ...points], duration)
  }

  resetView(): void {
    this.clearSelection()
    this.clearFocus()
    this.fitWard(0.8)
  }

  /** Demo reset: default camera, no selection, no temporary highlights (static layers are kept). */
  resetDemo(): void {
    this.clearSelection()
    this.clearFocus()
    this.setExposedAssets('buildings', null)
    this.setExposedAssets('roads', null)
    this.setComparison(this.comparisonZonesSource, null)
    this.setBottleneckTimeState(null)
    this.fitWard(0.8)
  }

  // ---- selection -------------------------------------------------------------------------------
  private pick(position: { x: number; y: number }): void {
    // Ground-draped polygons (roads, zones) are picked above ground polylines, so drill through the
    // stack and prefer the more specific feature: bottleneck > drain > flood node > everything else.
    const refs = this.viewer.scene
      .drillPick(position as never, 8)
      .map((picked) => (defined(picked) && picked.id instanceof Entity ? picked.id : null))
      .filter((e): e is Entity => e !== null)
      .map((e) => this.bottleneckFeatureByEntity.get(e) ?? this.featureByEntity.get(e) ?? this.floodFeatureByEntity.get(e))
      .filter((r): r is FeatureRef => r !== undefined)
    const rank = (r: FeatureRef) =>
      r.feature.layer === 'bottlenecks' ? 0 : r.feature.layer === 'drains' ? 1 : r.feature.layer === 'flood' && r.feature.id.startsWith('node:') ? 2 : 3
    const ref = refs.sort((a, b) => rank(a) - rank(b))[0]
    if (!ref) {
      this.clearSelection()
      return
    }
    this.highlight(ref)
    this.emphasiseBottleneck(ref.feature.layer === 'bottlenecks' ? ref.feature.id : null)
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
    const { ref, originals } = this.selected
    this.selected = null
    ref.entities.forEach((e, i) => {
      const original = originals[i]
      if (e.polygon && original) e.polygon.material = original
      if (e.polyline && original) e.polyline.material = original
    })
  }

  clearSelection(): void {
    const had = this.selected !== null
    this.emphasiseBottleneck(null)
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
    this.draped.clear()
    this.floodFeatureByEntity.clear()
    this.bottleneckFeatureByEntity.clear()
    this.bottleneckStyle.clear()
    this.comparisonZones.clear()
    this.assetEntities.buildings.clear()
    this.assetEntities.roads.clear()
    if (!this.viewer.isDestroyed()) this.viewer.destroy()
  }
}

function coordinates(geometry: Geometry): [number, number][] {
  const out: [number, number][] = []
  const visit = (value: unknown): void => {
    if (Array.isArray(value) && typeof value[0] === 'number') out.push([value[0] as number, value[1] as number])
    else if (Array.isArray(value)) value.forEach(visit)
  }
  visit(geometry.coordinates)
  return out
}

/** Vertex closest to half the line's vertex sequence (label anchor only). */
function midpoint(geometry: Geometry): [number, number] | null {
  const pts = coordinates(geometry)
  return pts.length ? pts[Math.floor(pts.length / 2)] : null
}
