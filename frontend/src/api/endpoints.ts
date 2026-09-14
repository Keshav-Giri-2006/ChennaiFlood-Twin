import type {
  BottleneckDetail,
  BottleneckFeatureProperties,
  BottleneckList,
  Exposure,
  ExposureAssets,
  ExposureAssetType,
  FloodSummary,
  FloodTimeline,
  KpiResponse,
  ScenarioDetail,
  ScenarioListItem,
  SimulationCreated,
  SimulationList,
  SimulationStatus,
  SimulationStatusValue,
  SimulationSummary,
  RecommendationList,
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
  async summary(simulationId: string, signal?: AbortSignal): Promise<SimulationSummary> {
    return requireFields<SimulationSummary>(await apiRequest(`/simulations/${enc(simulationId)}/summary`, { signal }), ['simulationId', 'limitations'], 'Simulation summary')
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

/** Backend-derived decision support. The frontend displays these results; it never recomputes them. */
export const decisionApi = {
  async bottlenecks(simulationId: string, signal?: AbortSignal): Promise<BottleneckList> {
    return requireFields<BottleneckList>(await apiRequest(`/simulations/${enc(simulationId)}/bottlenecks`, { signal }), ['bottlenecks', 'summary', 'numericalDiagnostics'], 'Potential bottlenecks')
  },
  async bottleneck(simulationId: string, linkId: string, signal?: AbortSignal): Promise<BottleneckDetail> {
    return requireFields<BottleneckDetail>(await apiRequest(`/simulations/${enc(simulationId)}/bottlenecks/${enc(linkId)}`, { signal }), ['linkId', 'sourceObjectId', 'criteria', 'explanation'], 'Bottleneck evidence')
  },
  async bottlenecksGeojson(simulationId: string, signal?: AbortSignal): Promise<FeatureCollection<BottleneckFeatureProperties>> {
    return requireFields<FeatureCollection<BottleneckFeatureProperties>>(await apiRequest(`/simulations/${enc(simulationId)}/bottlenecks/geojson`, { signal }), ['type', 'features'], 'Bottleneck geometry')
  },
  async exposure(simulationId: string, signal?: AbortSignal): Promise<Exposure> {
    return requireFields<Exposure>(await apiRequest(`/simulations/${enc(simulationId)}/exposure`, { signal }), ['event', 'timeline', 'byNode', 'totals'], 'Exposure')
  },
  async exposureAssets(simulationId: string, assetType: ExposureAssetType, time: string | null, signal?: AbortSignal): Promise<ExposureAssets> {
    const query = time ? `?time=${enc(time)}` : ''
    return requireFields<ExposureAssets>(await apiRequest(`/simulations/${enc(simulationId)}/exposure/${assetType}${query}`, { signal }), ['objectIds', 'count', 'scope'], 'Exposed assets')
  },
  async recommendations(simulationId: string, signal?: AbortSignal): Promise<RecommendationList> {
    return requireFields<RecommendationList>(await apiRequest(`/simulations/${enc(simulationId)}/recommendations`, { signal }), ['recommendations', 'summary', 'rules'], 'Recommendations')
  },
}

export type StaticLayerName = 'ward' | 'buildings' | 'roads' | 'drains' | 'subcatchments'

export const gisApi = {
  async layer(name: StaticLayerName, signal?: AbortSignal): Promise<FeatureCollection> {
    const body = requireFields<FeatureCollection>(await apiRequest(`/gis/${name}`, { signal }), ['type', 'features'], `GIS layer ${name}`)
    if (body.type !== 'FeatureCollection') throw new Error(`GIS layer ${name} is not a FeatureCollection`)
    return body
  },
  /** SWMM model representation layers (conduits/nodes), used to locate recommendation evidence. */
  async model(kind: 'conduits' | 'nodes', signal?: AbortSignal): Promise<FeatureCollection> {
    return requireFields<FeatureCollection>(await apiRequest(`/gis/model/${kind}`, { signal }), ['type', 'features'], `Model ${kind}`)
  },
  async terrain(signal?: AbortSignal): Promise<TerrainGrid> {
    return requireFields<TerrainGrid>(await apiRequest('/gis/terrain', { signal }), ['width', 'height', 'heights', 'firstCellCenter', 'cellSizeDeg'], 'Terrain grid')
  },
}
