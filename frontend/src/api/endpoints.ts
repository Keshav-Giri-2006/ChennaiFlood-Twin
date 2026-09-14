import type {
  FloodSummary,
  FloodTimeline,
  KpiResponse,
  ScenarioDetail,
  ScenarioListItem,
  SimulationCreated,
  SimulationList,
  SimulationStatus,
  SimulationStatusValue,
} from '../types/api'
import type { FeatureCollection, TerrainGrid } from '../types/gis'
import { apiRequest, requireFields } from './client'

const enc = encodeURIComponent

export const scenariosApi = {
  async list(signal?: AbortSignal): Promise<ScenarioListItem[]> {
    const body = requireFields<{ scenarios: ScenarioListItem[] }>(await apiRequest('/scenarios', { signal }), ['scenarios'], 'Scenario list')
    return body.scenarios
  },
  async get(scenarioId: string, signal?: AbortSignal): Promise<ScenarioDetail> {
    return requireFields<ScenarioDetail>(await apiRequest(`/scenarios/${enc(scenarioId)}`, { signal }), ['scenarioId', 'rainfall', 'source'], 'Scenario')
  },
}

export const simulationsApi = {
  async create(scenarioId: string, modelVersion?: string): Promise<SimulationCreated> {
    const body = modelVersion ? { scenarioId, modelVersion } : { scenarioId }
    return requireFields<SimulationCreated>(await apiRequest('/simulations', { method: 'POST', body }), ['simulationId', 'status'], 'Created simulation')
  },
  async get(simulationId: string, signal?: AbortSignal): Promise<SimulationStatus> {
    return requireFields<SimulationStatus>(await apiRequest(`/simulations/${enc(simulationId)}`, { signal }), ['simulationId', 'status', 'stage', 'progress'], 'Simulation')
  },
  async list(params: { scenarioId?: string; status?: SimulationStatusValue; limit?: number }, signal?: AbortSignal): Promise<SimulationList> {
    const query = new URLSearchParams()
    if (params.scenarioId) query.set('scenarioId', params.scenarioId)
    if (params.status) query.set('status', params.status)
    if (params.limit) query.set('limit', String(params.limit))
    return requireFields<SimulationList>(await apiRequest(`/simulations?${query.toString()}`, { signal }), ['simulations'], 'Simulation list')
  },
  async kpis(simulationId: string, signal?: AbortSignal): Promise<KpiResponse> {
    return requireFields<KpiResponse>(await apiRequest(`/simulations/${enc(simulationId)}/kpis`, { signal }), ['rainfall', 'hydraulics', 'drainage'], 'KPIs')
  },
}

export const floodApi = {
  async summary(simulationId: string, signal?: AbortSignal): Promise<FloodSummary> {
    return requireFields<FloodSummary>(await apiRequest(`/simulations/${enc(simulationId)}/flood`, { signal }), ['available', 'metrics', 'legend'], 'Flood summary')
  },
  async timeline(simulationId: string, signal?: AbortSignal): Promise<FloodTimeline> {
    return requireFields<FloodTimeline>(await apiRequest(`/simulations/${enc(simulationId)}/flood/timeline`, { signal }), ['timestamps', 'entries', 'legend'], 'Flood timeline')
  },
  /** Fetch a time-slice GeoJSON asset. The URL is opaque and comes from the timeline response. */
  async timesliceAsset(assetUrl: string, signal?: AbortSignal): Promise<FeatureCollection> {
    return requireFields<FeatureCollection>(await apiRequest(assetUrl, { signal }), ['type', 'features'], 'Flood time slice')
  },
}

export type StaticLayerName = 'ward' | 'buildings' | 'roads' | 'drains' | 'subcatchments'

export const gisApi = {
  async layer(name: StaticLayerName, signal?: AbortSignal): Promise<FeatureCollection> {
    const body = requireFields<FeatureCollection>(await apiRequest(`/gis/${name}`, { signal }), ['type', 'features'], `GIS layer ${name}`)
    if (body.type !== 'FeatureCollection') throw new Error(`GIS layer ${name} is not a FeatureCollection`)
    return body
  },
  async terrain(signal?: AbortSignal): Promise<TerrainGrid> {
    return requireFields<TerrainGrid>(await apiRequest('/gis/terrain', { signal }), ['width', 'height', 'heights', 'firstCellCenter', 'cellSizeDeg'], 'Terrain grid')
  },
}
