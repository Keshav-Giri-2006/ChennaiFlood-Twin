import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { floodApi, scenariosApi, simulationsApi } from '../api/endpoints'
import type { FloodTimelineEntry, SimulationStatusValue } from '../types/api'

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
}

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
    queryFn: async ({ signal }) => (await simulationsApi.list({ scenarioId: scenarioId as string, status: 'COMPLETED', limit: 1 }, signal)).simulations[0] ?? null,
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
    mutationFn: ({ scenarioId }: { scenarioId: string }) => simulationsApi.create(scenarioId),
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
