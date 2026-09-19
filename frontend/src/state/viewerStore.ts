import { create } from 'zustand'

/** Viewer/UI state only: layer visibility, visual settings, selection, open panels. No server data. */
export type LayerKey =
  | 'terrain'
  | 'boundary'
  | 'buildings'
  | 'roads'
  | 'drains'
  | 'subcatchments'
  | 'nodes'
  | 'rain'
  | 'flood'
  | 'bottlenecks'
  | 'exposureBuildings'
  | 'exposureRoads'
  | 'comparison'
export type LayerLoadState = 'idle' | 'loading' | 'ready' | 'error'
export type DashboardTab = 'flood' | 'hydraulics' | 'exposure' | 'actions' | 'compare'
export type ExposureScopeChoice = 'timestamp' | 'event'

export interface SelectedFeature {
  layer: 'boundary' | 'buildings' | 'roads' | 'drains' | 'subcatchments' | 'flood' | 'bottlenecks'
  id: string
  properties: Record<string, unknown>
}

type LoadInfo = { state: LayerLoadState; message?: string; featureCount?: number; loadMs?: number }

interface ViewerState {
  visibility: Record<LayerKey, boolean>
  loadState: Partial<Record<LayerKey, LoadInfo>>
  floodOpacity: number
  verticalExaggeration: number
  selection: SelectedFeature | null
  renderError: string | null
  viewerEpoch: number
  dashboardTab: DashboardTab
  exposureScope: ExposureScopeChoice
  comparisonScope: ExposureScopeChoice
  methodologyOpen: boolean
  setVisible: (layer: LayerKey, visible: boolean) => void
  setLoadState: (layer: LayerKey, value: LoadInfo) => void
  setFloodOpacity: (opacity: number) => void
  setVerticalExaggeration: (value: number) => void
  select: (feature: SelectedFeature | null) => void
  setRenderError: (message: string | null) => void
  /** Recreate the Cesium viewer (explicit recovery action only). */
  restartViewer: () => void
  setDashboardTab: (tab: DashboardTab) => void
  setExposureScope: (scope: ExposureScopeChoice) => void
  setComparisonScope: (scope: ExposureScopeChoice) => void
  setMethodologyOpen: (open: boolean) => void
  /** Restore default layers, opacity, tabs and selection (demo reset). */
  reset: () => void
}

// docs/08 §102 default: city layers on, subcatchments off, flood on once a result exists.
// Decision-support overlays start off so the flood story reads first.
export const DEFAULT_VISIBILITY: Record<LayerKey, boolean> = {
  terrain: true,
  boundary: true,
  buildings: true,
  roads: true,
  drains: true,
  subcatchments: false,
  nodes: true,
  rain: true,
  flood: true,
  bottlenecks: false,
  exposureBuildings: false,
  exposureRoads: false,
  comparison: false,
}

export const useViewerStore = create<ViewerState>((set) => ({
  visibility: { ...DEFAULT_VISIBILITY },
  loadState: {},
  floodOpacity: 0.55,
  verticalExaggeration: 1,
  selection: null,
  renderError: null,
  viewerEpoch: 0,
  dashboardTab: 'flood',
  exposureScope: 'timestamp',
  comparisonScope: 'event',
  methodologyOpen: false,
  setVisible: (layer, visible) => set((s) => ({ visibility: { ...s.visibility, [layer]: visible } })),
  setLoadState: (layer, value) => set((s) => ({ loadState: { ...s.loadState, [layer]: value } })),
  setFloodOpacity: (floodOpacity) => set({ floodOpacity: Math.min(1, Math.max(0.05, floodOpacity)) }),
  setVerticalExaggeration: (verticalExaggeration) => set({ verticalExaggeration }),
  select: (selection) => set({ selection }),
  setRenderError: (renderError) => set({ renderError }),
  restartViewer: () => set((s) => ({ viewerEpoch: s.viewerEpoch + 1, renderError: null, selection: null })),
  setDashboardTab: (dashboardTab) => set({ dashboardTab }),
  setExposureScope: (exposureScope) => set({ exposureScope }),
  setComparisonScope: (comparisonScope) => set({ comparisonScope }),
  setMethodologyOpen: (methodologyOpen) => set({ methodologyOpen }),
  reset: () =>
    set({
      visibility: { ...DEFAULT_VISIBILITY },
      floodOpacity: 0.55,
      verticalExaggeration: 1,
      selection: null,
      dashboardTab: 'flood',
      exposureScope: 'timestamp',
      comparisonScope: 'event',
      methodologyOpen: false,
    }),
}))
