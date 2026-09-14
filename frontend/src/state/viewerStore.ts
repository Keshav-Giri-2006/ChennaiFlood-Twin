import { create } from 'zustand'

/** Viewer/UI state only: layer visibility, visual settings, selection. No server data. */
export type LayerKey = 'terrain' | 'boundary' | 'buildings' | 'roads' | 'drains' | 'subcatchments' | 'flood'
export type LayerLoadState = 'idle' | 'loading' | 'ready' | 'error'

export interface SelectedFeature {
  layer: 'boundary' | 'buildings' | 'roads' | 'drains' | 'subcatchments' | 'flood'
  id: string
  properties: Record<string, unknown>
}

interface ViewerState {
  visibility: Record<LayerKey, boolean>
  loadState: Partial<Record<LayerKey, { state: LayerLoadState; message?: string; featureCount?: number; loadMs?: number }>>
  floodOpacity: number
  verticalExaggeration: number
  selection: SelectedFeature | null
  renderError: string | null
  setVisible: (layer: LayerKey, visible: boolean) => void
  setLoadState: (layer: LayerKey, value: { state: LayerLoadState; message?: string; featureCount?: number; loadMs?: number }) => void
  setFloodOpacity: (opacity: number) => void
  setVerticalExaggeration: (value: number) => void
  select: (feature: SelectedFeature | null) => void
  setRenderError: (message: string | null) => void
}

// docs/08 §102 default: city layers on, subcatchments off, flood on once a result exists.
export const DEFAULT_VISIBILITY: Record<LayerKey, boolean> = {
  terrain: true,
  boundary: true,
  buildings: true,
  roads: true,
  drains: true,
  subcatchments: false,
  flood: true,
}

export const useViewerStore = create<ViewerState>((set) => ({
  visibility: { ...DEFAULT_VISIBILITY },
  loadState: {},
  floodOpacity: 0.55,
  verticalExaggeration: 1,
  selection: null,
  renderError: null,
  setVisible: (layer, visible) => set((s) => ({ visibility: { ...s.visibility, [layer]: visible } })),
  setLoadState: (layer, value) => set((s) => ({ loadState: { ...s.loadState, [layer]: value } })),
  setFloodOpacity: (floodOpacity) => set({ floodOpacity: Math.min(1, Math.max(0.05, floodOpacity)) }),
  setVerticalExaggeration: (verticalExaggeration) => set({ verticalExaggeration }),
  select: (selection) => set({ selection }),
  setRenderError: (renderError) => set({ renderError }),
}))
