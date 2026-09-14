// Types mirroring docs/06_API_CONTRACT.md (incl. §81 addendum) and backend/app/schemas/api.py.

export type DataType = 'source' | 'model-derived' | 'derived' | 'estimated' | 'model-construct' | 'model-representation'

export interface ApiErrorBody {
  code: string
  message: string
  requestId?: string | null
  details?: unknown
  simulationId?: string
}

export interface Quantity {
  value: number | string | null
  unit: string
  source: string
  description?: string | null
  methodVersion?: string | null
  time?: string
  available?: boolean
  reason?: string
}

// ---- scenarios ---------------------------------------------------------------
export interface ScenarioListItem {
  scenarioId: string
  name: string
  description: string
  source: string
  rainfallType: string
  startTime: string
  endTime: string
  intervalMinutes: number
  totalRainfallMm: number
  peakIntensityMmHr: number
}

export interface ScenarioDetail {
  scenarioId: string
  name: string
  event: string
  description: string
  rainfallType: string
  dataType: DataType
  source: { name: string; variable: string; retrieval?: string | null; title?: string | null }
  rainfall: {
    type: string
    unit: string
    intervalMinutes: number
    records: number
    startTime: string
    endTime: string
    timeBasis: string
    totalMm: number
    peakMmHr: number
    peakIntervalStart: string
    dailyTotalsMm: Record<string, number>
  }
  limitations: string[]
}

// ---- simulations ---------------------------------------------------------------
export const SIMULATION_STATUSES = ['CREATED', 'VALIDATING', 'PREPARING', 'RUNNING', 'PROCESSING', 'COMPLETED', 'FAILED'] as const
export type SimulationStatusValue = (typeof SIMULATION_STATUSES)[number]

export type SimulationStage = 'QUEUED' | 'VALIDATION' | 'WORKSPACE_PREPARATION' | 'SWMM_EXECUTION' | 'RESULT_PROCESSING' | 'COMPLETE'

export interface SimulationStatus {
  simulationId: string
  scenarioId: string
  modelVersion: string
  processingVersion: string
  applicationVersion: string
  status: SimulationStatusValue
  stage: SimulationStage
  progress: number
  progressBasis: 'stage'
  createdAt: string
  startedAt: string | null
  completedAt: string | null
  error: { code: string; message: string; details?: unknown } | null
}

export interface SimulationCreated {
  simulationId: string
  scenarioId: string
  modelVersion: string
  status: SimulationStatusValue
  createdAt: string
}

export interface SimulationList {
  simulations: SimulationStatus[]
  limit: number
  offset: number
}

export interface KpiResponse {
  simulationId: string
  rainfall: Record<string, Quantity>
  flood: Record<string, Quantity>
  hydraulics: Record<string, Quantity>
  drainage: Record<string, Quantity>
  modelDiagnostics: Record<string, Quantity>
  metadata: Record<string, unknown>
}

// ---- flood (flood-processing-v1) -------------------------------------------------
export type FloodNodeState = 'FLOODING' | 'SURCHARGED'
export type OverflowClass = 'LOW' | 'MODERATE' | 'HIGH'

export interface FloodLegend {
  states: Record<FloodNodeState, string>
  overflowClasses: { class: OverflowClass; minExclusiveCms: number; maxInclusiveCms: number }[]
  classBasis: string
  quantity: string
}

export interface FloodSummary {
  simulationId: string
  available: boolean
  maximumDepthM: null
  peakTime: string
  peakIndex: number
  extentAvailable: boolean
  depthAvailable: boolean
  influenceZonesAvailable: boolean
  representation: string
  metrics: Record<string, Quantity>
  notDerived: Record<string, string>
  legend: FloodLegend
  metadata: { floodProcessingVersion: string; dataType: DataType; method: string; generatedAt: string; scenarioId: string; modelVersion: string }
}

export interface FloodTimelineEntry {
  index: number
  time: string
  key: string
  hasFlooding: boolean
  floodingNodeCount: number
  surchargedNodeCount: number
  systemFloodingRateCms: number
  maxNodeFloodingRateCms: number
  rainfallMmHr: number
  floodingInfluenceZoneAreaM2: number
  approxCumulativeSystemOverflowM3: number
  asset: { type: 'geojson'; url: string }
}

export interface FloodTimeline {
  simulationId: string
  intervalMinutes: number
  timeConvention: string
  timestamps: string[]
  peakIndex: number
  entries: FloodTimelineEntry[]
  legend: FloodLegend
  metadata: { floodProcessingVersion: string; dataType: DataType; method: string }
}
