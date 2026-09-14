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
  exposure?: Record<string, Quantity>
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

// ---- decision support (bottleneck-analysis-v1, exposure-analysis-v1, decision-support-v1) ----
export type BottleneckSeverity = 'HIGH' | 'MODERATE' | 'LOW'
export type Confidence = 'MEDIUM' | 'LOW'
export type Priority = 'HIGH' | 'MEDIUM' | 'LOW'

export interface BottleneckCriterion {
  id: 'L1' | 'L2' | 'L3' | 'S1'
  label: string
  met: boolean
  value: number | string[]
  unit: string
  threshold: string
  source: string
}

export interface ConnectedNodeEvidence {
  nodeId: string
  role: string
  nodeType: 'JUNCTION' | 'OUTFALL'
  flooding: { hoursFlooded: number; maximumRateCms: number; timeOfMaximum: string | null; totalFloodVolumeMillionLiters: number } | null
  surcharge: { hoursSurcharged: number; maxHeightAboveCrownM: number } | null
  swmmWarning02: boolean
  location: [number, number] | null
}

export interface ProjectInvestigation {
  sourceObjectId?: number
  nodes: string[]
  finding: string
  decision: string
  confidence: string
  source: string
}

export interface Bottleneck {
  rank: number
  linkId: string
  sourceObjectId: number
  identifierNote: string
  fromNodeId: string
  toNodeId: string
  severity: BottleneckSeverity
  uncappedSeverity: BottleneckSeverity
  severityCappedByNetworkContext: boolean
  score: number
  criteriaMet: number
  criteria: BottleneckCriterion[]
  confidence: Confidence
  confidenceReasons: string[]
  interpretation: string
  reason: string
  conduit: { modelLengthM: number | null; sourceWidthM: number | null; sourceDepthM: number | null; modelShape: string | null; modelFullDepthM: number | null; roughness: number | null }
  hydraulics: {
    maximumFlowCms: number
    timeOfMaximumFlow: string | null
    maximumVelocityMps: number | null
    maxOverFullFlow: number | null
    maxOverFullDepth: number | null
    derivedFullFlowCapacityCms: number | null
    hoursFullBothEnds: number
    hoursFullUpstream: number
    hoursFullDownstream: number
    hoursAboveFullNormalFlow: number
    hoursCapacityLimited: number
  }
  numericalDiagnostics: { timeStepCriticalPercent: number | null; flowInstabilityIndex: number | null }
  connectedNodes: ConnectedNodeEvidence[]
  networkContext: { modelComponentId: number; componentHasOutfall: boolean; componentOutfalls: string[]; componentNodeCount: number; outfallNote: string }
  sourceAttributes: { objectId: number; status: string | null; puccaKacha: string | null; drainDetail: string | null; invertScreeningDecision: string | null }
  projectInvestigation: ProjectInvestigation | null
  explanation: { whatIsThis: string; whyFlagged: string; interpretation: string; sourceData: string; plannerConsideration: string; disclaimer: string }
}

export interface NumericalDiagnostic {
  linkId: string
  sourceObjectId: number
  fromNodeId: string
  toNodeId: string
  timeStepCriticalPercent: number | null
  flowInstabilityIndex: number | null
  isPotentialBottleneck: boolean
  maxOverFullFlow: number | null
  hoursFullBothEnds: number
  modelComponentId: number
  componentHasOutfall: boolean
  interpretation: string
  projectInvestigation: ProjectInvestigation | null
}

export interface BottleneckList {
  simulationId: string
  bottleneckAnalysisVersion: string
  dataType: DataType
  terminology: string
  criteriaDefinition: Record<string, string>
  legend: { severity: BottleneckSeverity; label: string }[]
  summary: {
    conduitsScreened: number
    potentialBottlenecks: number
    bySeverity: Record<BottleneckSeverity, number>
    inComponentsWithoutOutfall: number
    modelComponents: number
    modelComponentsWithOutfall: number
  }
  bottlenecks: Bottleneck[]
  numericalDiagnostics: NumericalDiagnostic[]
  limitations: string[]
}

export interface BottleneckDetail extends Bottleneck {
  relatedRecommendationIds: string[]
  metadata: Record<string, string>
  terminology: string
}

export interface BottleneckFeatureProperties {
  featureType: 'potentialBottleneck'
  linkId: string
  sourceObjectId: number
  fromNodeId: string
  toNodeId: string
  severity: BottleneckSeverity
  score: number
  confidence: Confidence
  rank: number
  componentHasOutfall: boolean
  floodingNodeIds: string[]
}

export interface ExposureScope {
  floodingNodeCount: number
  buildings: { intersectingCount: number; percentOfBuildings: number | null; footprintAreaWithinZonesM2: number; percentOfFootprintArea: number | null; intersectingZonesOfNodesWithoutOutfallCount: number }
  roads: { intersectingCount: number; percentOfRoadFeatures: number | null; areaWithinZonesM2: number; percentOfRoadArea: number | null }
}

export interface ExposureTimelineEntry {
  index: number
  time: string
  floodingNodeCount: number
  buildingsIntersecting: number
  buildingFootprintAreaM2: number
  roadsIntersecting: number
  roadAreaM2: number
}

export interface ExposureNode {
  nodeId: string
  zoneAreaM2: number | null
  reportingPeriodsFlooding: number
  hoursFloodingSampled: number
  buildingsIntersecting: number
  buildingFootprintAreaM2: number
  roadsIntersecting: number
  roadAreaM2: number
  roadNames: string[]
  modelComponentId: number
  componentHasOutfall: boolean
}

export interface Exposure {
  simulationId: string
  exposureAnalysisVersion: string
  floodProcessingVersion: string
  dataType: DataType
  terminology: string
  definition: Record<string, string>
  totals: { buildings: { count: number; footprintAreaM2: number }; roads: { count: number; areaM2: number } }
  event: ExposureScope
  peak: ExposureScope & { index: number; time: string }
  maxConcurrent: { buildingsIntersecting: { value: number; time: string; index: number }; roadAreaM2: { value: number; time: string; index: number } }
  timeline: ExposureTimelineEntry[]
  byNode: ExposureNode[]
  limitations: string[]
}

export type ExposureAssetType = 'buildings' | 'roads'

export interface ExposureAssets {
  simulationId: string
  assetType: ExposureAssetType
  scope: 'event' | 'timestamp'
  time: string | null
  index: number | null
  floodingNodeIds: string[]
  count: number
  objectIds: number[]
  assets: { objectId: number; areaWithinZonesM2: number; nodeIds: string[] }[]
  terminology: string
}

export interface RecommendationMetric {
  label: string
  value: number | string | null
  unit: string
  source: string
}

export interface Recommendation {
  id: string
  rule: 'R1' | 'R2' | 'R3' | 'R4' | 'R5' | 'R6'
  category: string
  priority: Priority
  confidence: Confidence
  title: string
  recommendation: string
  why: string
  evidence: { links: { linkId: string; sourceObjectId: number }[]; nodes: string[]; metrics: RecommendationMetric[] }
  drivers: string[]
  confidenceReasons: string[]
  relatedBottleneckLinkIds: string[]
  focus: { linkIds: string[]; nodeIds: string[] }
  disclaimer: string
}

export interface RecommendationList {
  simulationId: string
  decisionSupportVersion: string
  bottleneckAnalysisVersion: string
  exposureAnalysisVersion: string
  dataType: DataType
  disclaimer: string
  rules: Record<string, string>
  summary: { total: number; byPriority: Record<Priority, number>; byRule: Record<string, number> }
  recommendations: Recommendation[]
}

export interface SimulationSummary {
  simulationId: string
  limitations: string[]
  metadata: Record<string, unknown>
  [key: string]: unknown
}
