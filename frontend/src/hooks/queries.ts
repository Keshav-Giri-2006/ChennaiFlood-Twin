import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { comparisonsApi, decisionApi, demoApi, floodApi, gisApi, healthApi, locationApi, scenariosApi, simulationsApi } from '../api/endpoints'
import type { ExposureAssetType, FloodTimelineEntry, SimulationStatusValue } from '../types/api'

const TERMINAL: SimulationStatusValue[] = ['COMPLETED', 'FAILED']
export const STATUS_POLL_MS = 1500

export const queryKeys = {
  scenarios: ['scenarios'] as const,
  scenario: (id: string) => ['scenario', id] as const,
  latestCompleted: (scenarioId: string) => ['simulations', 'latest-completed', scenarioId] as const,
  simulation: (id: string) => ['simulation', id] as const,
  kpis: (id: string) => ['kpis', id] as const,
  floodSummary: (id: string) => ['flood', id, 'summary'] as const,
  floodTimeline: (id: string) => ['flood', id, 'timeline'] as const,
  floodSlice: (id: string, key: string) => ['flood', id, 'timeslice', key] as const,
  summary: (id: string) => ['summary', id] as const,
  bottlenecks: (id: string) => ['decision', id, 'bottlenecks'] as const,
  bottleneck: (id: string, linkId: string) => ['decision', id, 'bottleneck', linkId] as const,
  bottleneckGeojson: (id: string) => ['decision', id, 'bottlenecks-geojson'] as const,
  exposure: (id: string) => ['decision', id, 'exposure'] as const,
  exposureAssets: (id: string, type: ExposureAssetType, time: string | null) => ['decision', id, 'exposure-assets', type, time ?? 'event'] as const,
  recommendations: (id: string) => ['decision', id, 'recommendations'] as const,
  modelLayer: (kind: 'conduits' | 'nodes') => ['gis', 'model', kind] as const,
  locationCheck: (id: string, lat: number, lon: number, radius: number) => ['location', id, lat.toFixed(7), lon.toFixed(7), radius] as const,
}

/** Completed-simulation products are immutable: cache them for the session. */
const IMMUTABLE = { staleTime: Infinity } as const

export function useScenarios() {
  return useQuery({ queryKey: queryKeys.scenarios, queryFn: ({ signal }) => scenariosApi.list(signal), staleTime: Infinity })
}

export function useScenario(scenarioId: string | null) {
  return useQuery({
    queryKey: queryKeys.scenario(scenarioId ?? ''),
    queryFn: ({ signal }) => scenariosApi.get(scenarioId as string, signal),
    enabled: Boolean(scenarioId),
    staleTime: Infinity,
  })
}

/** Most recent COMPLETED simulation for a scenario (e.g. a precomputed demo result). */
export function useLatestCompletedSimulation(scenarioId: string | null) {
  return useQuery({
    queryKey: queryKeys.latestCompleted(scenarioId ?? ''),
    // Baseline (1.00x) runs only: what-if runs are opened explicitly from the comparison panel.
    queryFn: async ({ signal }) => (await simulationsApi.list({ scenarioId: scenarioId as string, status: 'COMPLETED', limit: 1, rainfallMultiplier: 1 }, signal)).simulations[0] ?? null,
    enabled: Boolean(scenarioId),
    staleTime: 60_000,
  })
}

/** Backend-authoritative status. Polls only while the simulation is active. */
export function useSimulationStatus(simulationId: string | null) {
  return useQuery({
    queryKey: queryKeys.simulation(simulationId ?? ''),
    queryFn: ({ signal }) => simulationsApi.get(simulationId as string, signal),
    enabled: Boolean(simulationId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && TERMINAL.includes(status) ? false : STATUS_POLL_MS
    },
  })
}

export function useCreateSimulation() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ scenarioId, rainfallMultiplier }: { scenarioId: string; rainfallMultiplier?: number }) => simulationsApi.create(scenarioId, { rainfallMultiplier }),
    onSuccess: (created) => {
      client.invalidateQueries({ queryKey: ['simulations'] })
      return created
    },
  })
}

export function useKpis(simulationId: string | null) {
  return useQuery({ queryKey: queryKeys.kpis(simulationId ?? ''), queryFn: ({ signal }) => simulationsApi.kpis(simulationId as string, signal), enabled: Boolean(simulationId), staleTime: Infinity })
}

export function useFloodSummary(simulationId: string | null) {
  return useQuery({ queryKey: queryKeys.floodSummary(simulationId ?? ''), queryFn: ({ signal }) => floodApi.summary(simulationId as string, signal), enabled: Boolean(simulationId), staleTime: Infinity })
}

export function useFloodTimeline(simulationId: string | null) {
  return useQuery({ queryKey: queryKeys.floodTimeline(simulationId ?? ''), queryFn: ({ signal }) => floodApi.timeline(simulationId as string, signal), enabled: Boolean(simulationId), staleTime: Infinity })
}

/** Time slices of completed simulations are immutable; keyed by simulation + timestamp key. */
export function useFloodTimeslice(simulationId: string | null, entry: FloodTimelineEntry | null) {
  return useQuery({
    queryKey: queryKeys.floodSlice(simulationId ?? '', entry?.key ?? ''),
    queryFn: ({ signal }) => floodApi.timesliceAsset((entry as FloodTimelineEntry).asset.url, signal),
    enabled: Boolean(simulationId && entry),
    staleTime: Infinity,
    gcTime: 5 * 60_000,
  })
}

/** Query options for a time slice; shared by the flood layer and playback preloading (same cache entry). */
export function floodSliceQuery(simulationId: string, entry: FloodTimelineEntry) {
  return {
    queryKey: queryKeys.floodSlice(simulationId, entry.key),
    queryFn: ({ signal }: { signal?: AbortSignal }) => floodApi.timesliceAsset(entry.asset.url, signal),
    staleTime: Infinity,
    gcTime: 5 * 60_000,
  }
}

export function useSimulationSummary(simulationId: string | null) {
  return useQuery({ queryKey: queryKeys.summary(simulationId ?? ''), queryFn: ({ signal }) => simulationsApi.summary(simulationId as string, signal), enabled: Boolean(simulationId), ...IMMUTABLE })
}

export function useBottlenecks(simulationId: string | null) {
  return useQuery({ queryKey: queryKeys.bottlenecks(simulationId ?? ''), queryFn: ({ signal }) => decisionApi.bottlenecks(simulationId as string, signal), enabled: Boolean(simulationId), ...IMMUTABLE })
}

export function useBottleneck(simulationId: string | null, linkId: string | null) {
  return useQuery({
    queryKey: queryKeys.bottleneck(simulationId ?? '', linkId ?? ''),
    queryFn: ({ signal }) => decisionApi.bottleneck(simulationId as string, linkId as string, signal),
    enabled: Boolean(simulationId && linkId),
    retry: false,
    ...IMMUTABLE,
  })
}

export function useBottleneckGeojson(simulationId: string | null, enabled = true) {
  return useQuery({
    queryKey: queryKeys.bottleneckGeojson(simulationId ?? ''),
    queryFn: ({ signal }) => decisionApi.bottlenecksGeojson(simulationId as string, signal),
    enabled: Boolean(simulationId) && enabled,
    ...IMMUTABLE,
  })
}

export function useExposure(simulationId: string | null) {
  return useQuery({ queryKey: queryKeys.exposure(simulationId ?? ''), queryFn: ({ signal }) => decisionApi.exposure(simulationId as string, signal), enabled: Boolean(simulationId), ...IMMUTABLE })
}

/** Exposed asset ObjectIDs for one reporting timestamp (or the whole event when time is null). */
export function useExposureAssets(simulationId: string | null, assetType: ExposureAssetType, time: string | null, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.exposureAssets(simulationId ?? '', assetType, time),
    queryFn: ({ signal }) => decisionApi.exposureAssets(simulationId as string, assetType, time, signal),
    enabled: Boolean(simulationId) && enabled,
    // Keep the previous highlight of the same simulation while the next timestamp loads (no flicker).
    placeholderData: (previous) => (previous?.simulationId === simulationId ? previous : undefined),
    ...IMMUTABLE,
    gcTime: 5 * 60_000,
  })
}

export function useRecommendations(simulationId: string | null) {
  return useQuery({ queryKey: queryKeys.recommendations(simulationId ?? ''), queryFn: ({ signal }) => decisionApi.recommendations(simulationId as string, signal), enabled: Boolean(simulationId), ...IMMUTABLE })
}

export function useModelLayer(kind: 'conduits' | 'nodes', enabled = true) {
  return useQuery({ queryKey: queryKeys.modelLayer(kind), queryFn: ({ signal }) => gisApi.model(kind, signal), enabled, ...IMMUTABLE })
}

export const HEALTH_POLL_MS = 20_000

/** Backend liveness, polled gently (20 s; 5 s timeout). */
export function useBackendHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => healthApi.health(signal),
    refetchInterval: HEALTH_POLL_MS,
    refetchIntervalInBackground: false,
    retry: 0,
    staleTime: 0,
  })
}

export function useDemoCatalogue() {
  return useQuery({ queryKey: ['demo'], queryFn: ({ signal }) => demoApi.catalogue(signal), staleTime: 30_000 })
}

export function useLoadDemo() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (demoId: string) => demoApi.load(demoId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['demo'] })
      void client.invalidateQueries({ queryKey: ['simulations'] })
    },
  })
}

export function useBottleneckTimeline(simulationId: string | null) {
  return useQuery({ queryKey: ['decision', simulationId ?? '', 'bottleneck-timeline'], queryFn: ({ signal }) => decisionApi.bottleneckTimeline(simulationId as string, signal), enabled: Boolean(simulationId), ...IMMUTABLE })
}

/** Completed simulations of a scenario (baseline, what-if and demo runs) for comparison selection. */
export function useCompletedSimulations(scenarioId: string | null) {
  return useQuery({
    queryKey: ['simulations', 'completed', scenarioId ?? ''],
    queryFn: async ({ signal }) => (await simulationsApi.list({ scenarioId: scenarioId as string, status: 'COMPLETED', limit: 50 }, signal)).simulations,
    enabled: Boolean(scenarioId),
    staleTime: 30_000,
  })
}

export function useComparison(baselineId: string | null, scenarioId: string | null) {
  return useQuery({
    queryKey: ['comparison', baselineId ?? '', scenarioId ?? ''],
    queryFn: ({ signal }) => comparisonsApi.get(baselineId as string, scenarioId as string, signal),
    enabled: Boolean(baselineId && scenarioId && baselineId !== scenarioId),
    retry: false,
    ...IMMUTABLE,
  })
}

export function useFloodZones(simulationId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['flood', simulationId ?? '', 'zones'],
    queryFn: ({ signal }) => floodApi.zones(simulationId as string, signal),
    enabled: Boolean(simulationId) && enabled,
    ...IMMUTABLE,
  })
}

/** Radius of the surrounding area evaluated by the Location Flood Check (metres; backend default). */
export const LOCATION_RADIUS_M = 250

/**
 * Model-derived flood response around a location for one completed simulation. Results of a completed
 * simulation are immutable, so each (simulation, location) pair is cached; moving the pin issues a new query
 * against the same simulation without re-running SWMM.
 */
export function useLocationCheck(simulationId: string | null, location: { latitude: number; longitude: number } | null, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.locationCheck(simulationId ?? '', location?.latitude ?? 0, location?.longitude ?? 0, LOCATION_RADIUS_M),
    queryFn: ({ signal }) => locationApi.check(simulationId as string, { latitude: (location as { latitude: number }).latitude, longitude: (location as { longitude: number }).longitude, radiusMeters: LOCATION_RADIUS_M }, signal),
    enabled: Boolean(simulationId && location) && enabled,
    retry: false,
    ...IMMUTABLE,
  })
}
