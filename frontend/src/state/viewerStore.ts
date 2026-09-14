import { create } from 'zustand'

/** Viewer/UI state only: layer visibility, visual settings, selection, open panels. No server data. */
export type LayerKey =
  | 'terrain'
  | 'boundary'
  | 'buildings'
  | 'roads'
  | 'drains'
  | 'subcatchments'
  | 'flood'
  | 'bottlenecks'
  | 'exposureBuildings'
  | 'exposureRoads'
export type LayerLoadState = 'idle' | 'loading' | 'ready' | 'error'
export type DashboardTab = 'flood' | 'hydraulics' | 'exposure' | 'actions'
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
  dashboardTab: DashboardTab
  exposureScope: ExposureScopeChoice
  methodologyOpen: boolean
  setVisible: (layer: LayerKey, visible: boolean) => void
  setLoadState: (layer: LayerKey, value: LoadInfo) => void
  setFloodOpacity: (opacity: number) => void
  setVerticalExaggeration: (value: number) => void
  select: (feature: SelectedFeature | null) => void
  setRenderError: (message: string | null) => void
  setDashboardTab: (tab: DashboardTab) => void
  setExposureScope: (scope: ExposureScopeChoice) => void
  setMethodologyOpen: (open: boolean) => void
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
  flood: true,
  bottlenecks: false,
  exposureBuildings: false,
  exposureRoads: false,
}

export const useViewerStore = create<ViewerState>((set) => ({
  visibility: { ...DEFAULT_VISIBILITY },
  loadState: {},
  floodOpacity: 0.55,
  verticalExaggeration: 1,
  selection: null,
  renderError: null,
  dashboardTab: 'flood',
  exposureScope: 'timestamp',
  methodologyOpen: false,
  setVisible: (layer, visible) => set((s) => ({ visibility: { ...s.visibility, [layer]: visible } })),
  setLoadState: (layer, value) => set((s) => ({ loadState: { ...s.loadState, [layer]: value } })),
  setFloodOpacity: (floodOpacity) => set({ floodOpacity: Math.min(1, Math.max(0.05, floodOpacity)) }),
  setVerticalExaggeration: (verticalExaggeration) => set({ verticalExaggeration }),
  select: (selection) => set({ selection }),
  setRenderError: (renderError) => set({ renderError }),
  setDashboardTab: (dashboardTab) => set({ dashboardTab }),
  setExposureScope: (exposureScope) => set({ exposureScope }),
  setMethodologyOpen: (methodologyOpen) => set({ methodologyOpen }),
}))
