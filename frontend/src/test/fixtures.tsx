/**
 * TEST FIXTURES ONLY — small, clearly synthetic API-shaped objects for component tests.
 * They are never imported by application code. Values mirror the shape of backend responses;
 * the real values are verified in backend tests and the end-to-end run.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { vi } from 'vitest'
import { queryKeys } from '../hooks/queries'
import type { BottleneckList, Exposure, FloodSummary, FloodTimeline, FloodTimelineEntry, KpiResponse, RecommendationList } from '../types/api'
import type { DigitalTwinController } from '../cesium/DigitalTwinController'
import { ControllerContext } from '../components/viewer/controllerContext'

export const SIM = 'test-sim-0000'

function entry(index: number, flooding: number, surcharged: number): FloodTimelineEntry {
  const time = new Date(Date.UTC(2023, 11, 3, 20, 0) + index * 30 * 60_000).toISOString().replace('.000', '')
  return {
    index,
    time,
    key: time.replace(/[-:]/g, ''),
    hasFlooding: flooding > 0,
    floodingNodeCount: flooding,
    surchargedNodeCount: surcharged,
    systemFloodingRateCms: flooding * 0.1,
    maxNodeFloodingRateCms: flooding * 0.01,
    rainfallMmHr: 1,
    floodingInfluenceZoneAreaM2: 100,
    approxCumulativeSystemOverflowM3: index * 10,
    asset: { type: 'geojson', url: `/api/v1/simulations/${SIM}/flood/timeslices/${index}` },
  }
}

export const timeline: FloodTimeline = {
  simulationId: SIM,
  intervalMinutes: 30,
  timeConvention: 'test',
  timestamps: [],
  peakIndex: 2,
  entries: [entry(0, 0, 1), entry(1, 5, 2), entry(2, 9, 4), entry(3, 3, 0)],
  legend: { states: { FLOODING: 'f', SURCHARGED: 's' }, overflowClasses: [{ class: 'LOW', minExclusiveCms: 0, maxInclusiveCms: 1 }], classBasis: 'test basis', quantity: 'q' },
  metadata: { floodProcessingVersion: 'flood-processing-v1', dataType: 'model-derived', method: 'm' },
}
timeline.timestamps = timeline.entries.map((e) => e.time)

export const sliceFor = (index: number) => ({ type: 'FeatureCollection' as const, metadata: { simulationId: SIM, index }, features: [] })

const qty = (value: number | string | null, unit: string) => ({ value, unit, source: 'model-derived' })

export const kpis: KpiResponse = {
  simulationId: SIM,
  rainfall: { total: qty(282.835, 'mm'), peakIntensity: qty(23.35, 'mm/hr') },
  flood: {},
  hydraulics: { simulatedFloodingVolume: qty(197876000, 'L') },
  drainage: {},
  modelDiagnostics: {},
  metadata: {},
}

export const floodSummary = {
  simulationId: SIM,
  peakTime: timeline.entries[2].time,
  peakIndex: 2,
  metrics: {
    peakConcurrentFloodingNodes: qty(9, 'count'),
    peakSystemFloodingRate: qty(5.435, 'm3/s'),
    floodingDuration: qty(90, 'hr'),
    maximumNodeWaterDepth: qty(1.36, 'm'),
  },
  legend: timeline.legend,
  metadata: { floodProcessingVersion: 'flood-processing-v1' },
} as unknown as FloodSummary

export const bottlenecks = {
  simulationId: SIM,
  bottleneckAnalysisVersion: 'bottleneck-analysis-v1',
  dataType: 'model-derived',
  terminology: 'Potential drainage bottleneck: a model-derived diagnostic. Not a confirmed failure.',
  criteriaDefinition: { L1: 'capacity limited' },
  legend: [{ severity: 'HIGH', label: 'High diagnostic concern' }],
  summary: { conduitsScreened: 3, potentialBottlenecks: 1, bySeverity: { HIGH: 1, MODERATE: 0, LOW: 0 }, inComponentsWithoutOutfall: 0, modelComponents: 2, modelComponentsWithOutfall: 1 },
  bottlenecks: [
    {
      rank: 1,
      linkId: 'C901',
      sourceObjectId: 9001,
      fromNodeId: 'J1',
      toNodeId: 'J2',
      severity: 'HIGH',
      criteriaMet: 4,
      confidence: 'MEDIUM',
      reason: 'test reason',
      criteria: [{ id: 'S1', label: 'Connected node flooding', met: true, value: ['J1'], unit: 'nodes', threshold: 't', source: 's' }],
      connectedNodes: [{ nodeId: 'J1', location: [80.2, 12.98], flooding: { hoursFlooded: 2 } }],
      networkContext: { componentHasOutfall: true },
    },
  ],
  numericalDiagnostics: [{ linkId: 'C902', sourceObjectId: 9002, timeStepCriticalPercent: 35.7, flowInstabilityIndex: null, interpretation: 'Numerical diagnostic, not capacity.', projectInvestigation: null }],
  limitations: [],
} as unknown as BottleneckList

export const exposure = {
  simulationId: SIM,
  exposureAnalysisVersion: 'exposure-analysis-v1',
  terminology: 'Model-derived exposure: not flooded or damaged assets.',
  definition: { a: 'definition' },
  totals: { buildings: { count: 100, footprintAreaM2: 1000 }, roads: { count: 10, areaM2: 500 } },
  event: { floodingNodeCount: 2, buildings: { intersectingCount: 20, percentOfBuildings: 20, footprintAreaWithinZonesM2: 200, percentOfFootprintArea: 20, intersectingZonesOfNodesWithoutOutfallCount: 5 }, roads: { intersectingCount: 2, percentOfRoadFeatures: 20, areaWithinZonesM2: 50, percentOfRoadArea: 10 } },
  peak: { index: 2, time: timeline.entries[2].time, floodingNodeCount: 2, buildings: { intersectingCount: 15, percentOfBuildings: 15, footprintAreaWithinZonesM2: 150, percentOfFootprintArea: 15, intersectingZonesOfNodesWithoutOutfallCount: 5 }, roads: { intersectingCount: 1, percentOfRoadFeatures: 10, areaWithinZonesM2: 30, percentOfRoadArea: 6 } },
  timeline: timeline.entries.map((e) => ({ index: e.index, time: e.time, floodingNodeCount: e.floodingNodeCount, buildingsIntersecting: e.floodingNodeCount * 3, buildingFootprintAreaM2: 1, roadsIntersecting: 1, roadAreaM2: 1 })),
  byNode: [{ nodeId: 'J1', buildingsIntersecting: 12, roadsIntersecting: 1, hoursFloodingSampled: 3, componentHasOutfall: false }],
  limitations: ['limitation'],
} as unknown as Exposure

export const recommendations = {
  simulationId: SIM,
  decisionSupportVersion: 'decision-support-v1',
  disclaimer: 'Decision-support suggestion; not an engineering order.',
  rules: { R1: 'rule one' },
  summary: { total: 2, byPriority: { HIGH: 1, MEDIUM: 0, LOW: 1 }, byRule: {} },
  recommendations: [
    {
      id: 'rec-r1-C901', rule: 'R1', category: 'DRAINAGE_CAPACITY', priority: 'HIGH', confidence: 'MEDIUM', title: 'Assess drainage capacity of segment C901',
      recommendation: 'Inspect corridor.', why: 'Because evidence.', evidence: { links: [{ linkId: 'C901', sourceObjectId: 9001 }], nodes: ['J1'], metrics: [{ label: 'Hours capacity limited', value: 9.47, unit: 'hr', source: 'SWMM' }] },
      drivers: [], confidenceReasons: [], relatedBottleneckLinkIds: ['C901'], focus: { linkIds: ['C901'], nodeIds: ['J1'] }, disclaimer: 'd',
    },
    {
      id: 'rec-r6-C902', rule: 'R6', category: 'MODEL_DATA_VERIFICATION', priority: 'LOW', confidence: 'LOW', title: 'Verify invert data at C902',
      recommendation: 'Survey.', why: 'Numerical.', evidence: { links: [], nodes: [], metrics: [{ label: 'Time-step critical', value: 35.7, unit: '%', source: 'SWMM' }] },
      drivers: [], confidenceReasons: [], relatedBottleneckLinkIds: [], focus: { linkIds: [], nodeIds: [] }, disclaimer: 'd',
    },
  ],
} as unknown as RecommendationList

/** QueryClient pre-seeded with fixture responses (no network). */
export function seededClient(): QueryClient {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } })
  client.setQueryData(queryKeys.floodTimeline(SIM), timeline)
  client.setQueryData(queryKeys.floodSummary(SIM), floodSummary)
  client.setQueryData(queryKeys.kpis(SIM), kpis)
  client.setQueryData(queryKeys.bottlenecks(SIM), bottlenecks)
  client.setQueryData(queryKeys.exposure(SIM), exposure)
  client.setQueryData(queryKeys.recommendations(SIM), recommendations)
  client.setQueryData(queryKeys.bottleneckGeojson(SIM), { type: 'FeatureCollection', metadata: { simulationId: SIM }, features: [{ type: 'Feature', id: 'C901', geometry: { type: 'LineString', coordinates: [[80.2, 12.98], [80.201, 12.981]] }, properties: {} }] })
  return client
}

export function fakeController() {
  return {
    selectBottleneck: vi.fn(() => true),
    fitBottlenecks: vi.fn(() => true),
    flyToGeometries: vi.fn(() => true),
    flyToLonLats: vi.fn(() => true),
    focusOn: vi.fn(() => true),
    clearSelection: vi.fn(),
  }
}

export function wrap(ui: ReactNode, client: QueryClient, controller: unknown = null) {
  return (
    <QueryClientProvider client={client}>
      <ControllerContext.Provider value={controller as DigitalTwinController | null}>{ui}</ControllerContext.Provider>
    </QueryClientProvider>
  )
}
