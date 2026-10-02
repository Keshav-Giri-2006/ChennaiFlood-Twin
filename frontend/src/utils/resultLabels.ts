import type { SimulationStatus } from '../types/api'

/** How the displayed result was produced — never presented as live or real-time data. */
export function resultSourceLabel(status: SimulationStatus | undefined, sessionRunIds: string[]): string {
  if (!status) return ''
  if (status.executionMode === 'precomputed-demo') return 'Precomputed demonstration result'
  if (sessionRunIds.includes(status.simulationId)) return 'Simulated now (this session)'
  return 'Stored simulation result'
}

export function multiplierLabel(status: SimulationStatus | undefined): string {
  const m = status?.parameters?.rainfallMultiplier ?? 1
  return m === 1 ? 'Baseline 1.00× historical rainfall' : `${m.toFixed(2)}× rainfall multiplier (what-if scenario)`
}

/** Backend lifecycle stages of a simulation (progress reflects these stages, not simulated time). */
export const STAGE_LABELS: Record<string, string> = {
  QUEUED: 'Queued',
  VALIDATION: 'Validating model and rainfall',
  WORKSPACE_PREPARATION: 'Preparing isolated workspace',
  SWMM_EXECUTION: 'Running EPA SWMM',
  RESULT_PROCESSING: 'Processing results, flood and decision-support products',
  COMPLETE: 'Complete',
}
