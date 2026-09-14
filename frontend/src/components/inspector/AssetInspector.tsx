import type { ReactNode } from 'react'
import { friendlyErrorMessage } from '../../api/client'
import { useBottleneck, useBottlenecks, useExposureAssets } from '../../hooks/queries'
import { useActiveTimeline } from '../../hooks/useTimeline'
import { useViewerStore, type SelectedFeature } from '../../state/viewerStore'
import type { BottleneckDetail } from '../../types/api'
import { formatNumber, formatTimestampUtc, humanizeKey } from '../../utils/format'
import { Panel } from '../common/Panel'
import { SeverityBadge } from '../decision/HydraulicsPanel'
import { useDigitalTwin } from '../viewer/controllerContext'

type Row = [label: string, value: unknown]

/** Identifiers must never be number-formatted (5902, not 5,902). */
const id = (value: unknown): string => (value === null || value === undefined ? '—' : String(value))

function display(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'number') return formatNumber(value, 3)
  if (Array.isArray(value)) return value.length ? value.join(', ') : '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}

function Section({ title, rows, note }: { title: string; rows: Row[]; note?: string }) {
  return (
    <div className="inspector-section">
      <h4>{title}</h4>
      <dl className="kv">
        {rows.map(([label, value]) => (
          <div key={label} className="kv-row">
            <dt>{label}</dt>
            <dd>{display(value)}</dd>
          </div>
        ))}
      </dl>
      {note && <p className="muted small">{note}</p>}
    </div>
  )
}

interface Explanation {
  what: ReactNode
  why: ReactNode
  evidence?: ReactNode
  source: ReactNode
  consider: ReactNode
}

/** The five explainability questions (Part 14), answered concisely from backend data. */
function Explain({ e }: { e: Explanation }) {
  return (
    <div className="explain" aria-label="Explanation">
      <h4>What is this?</h4>
      <div className="small">{e.what}</div>
      <h4>Why is it relevant?</h4>
      <div className="small">{e.why}</div>
      {e.evidence && (
        <>
          <h4>What model evidence supports it?</h4>
          <div className="small">{e.evidence}</div>
        </>
      )}
      <h4>What source data produced it?</h4>
      <div className="small">{e.source}</div>
      <h4>What should the planner consider?</h4>
      <div className="small">{e.consider}</div>
    </div>
  )
}

function BottleneckDetails({ linkId }: { linkId: string }) {
  const { simulationId } = useActiveTimeline()
  const detail = useBottleneck(simulationId, linkId)
  if (detail.isPending) return <p className="muted">Loading evidence for {linkId}…</p>
  if (detail.isError) return <p className="error-text">{friendlyErrorMessage(detail.error)}</p>
  const b: BottleneckDetail = detail.data
  return (
    <>
      <p className="item-head">
        <SeverityBadge severity={b.severity} /> <strong>Potential bottleneck {b.linkId}</strong> <span className="muted small">confidence {b.confidence.toLowerCase()}</span>
      </p>
      <Explain
        e={{
          what: b.explanation.whatIsThis,
          why: (
            <>
              <strong>Why flagged? </strong>
              {b.explanation.whyFlagged} {b.explanation.interpretation}
            </>
          ),
          evidence: (
            <table className="mini-table">
              <thead>
                <tr>
                  <th scope="col">Criterion</th>
                  <th scope="col">Value</th>
                  <th scope="col">Rule</th>
                </tr>
              </thead>
              <tbody>
                {b.criteria.map((c) => (
                  <tr key={c.id} className={c.met ? 'met' : 'not-met'}>
                    <td>
                      {c.met ? '✓' : '✗'} {c.id} {c.label}
                    </td>
                    <td>{Array.isArray(c.value) ? c.value.join(', ') || '—' : `${formatNumber(c.value, 2)} ${c.unit === 'ratio' ? '×' : c.unit}`}</td>
                    <td className="muted">{c.threshold}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ),
          source: (
            <ol className="trace">
              <li>GCC storm-water drain ObjectID {id(b.sourceObjectId)}</li>
              <li>Reconstructed conduit ({formatNumber(b.conduit.modelLengthM, 2)} m, {formatNumber(b.conduit.sourceWidthM, 2)} × {formatNumber(b.conduit.sourceDepthM, 2)} m)</li>
              <li>
                SWMM link {b.linkId}: {b.fromNodeId} → {b.toNodeId}
              </li>
              <li>SWMM 5.2.4 report of this simulation</li>
              <li>{b.metadata.bottleneckAnalysisVersion} diagnostic</li>
            </ol>
          ),
          consider: b.explanation.plannerConsideration,
        }}
      />
      <Section
        title="Hydraulic statistics (SWMM)"
        rows={[
          ['Max flow (m³/s)', b.hydraulics.maximumFlowCms],
          ['Time of max flow', formatTimestampUtc(b.hydraulics.timeOfMaximumFlow)],
          ['Max velocity (m/s)', b.hydraulics.maximumVelocityMps],
          ['Max / full flow', b.hydraulics.maxOverFullFlow],
          ['Max / full depth', b.hydraulics.maxOverFullDepth],
          ['Derived full-flow capacity (m³/s)', b.hydraulics.derivedFullFlowCapacityCms],
          ['Hours capacity limited', b.hydraulics.hoursCapacityLimited],
          ['Hours full both ends', b.hydraulics.hoursFullBothEnds],
          ['Hours full downstream', b.hydraulics.hoursFullDownstream],
        ]}
      />
      <Section
        title="Connected nodes"
        rows={b.connectedNodes.map((n) => [
          `${n.nodeId} (${n.role.split(' ')[0]})`,
          n.flooding ? `floods ${formatNumber(n.flooding.hoursFlooded, 1)} h, max ${formatNumber(n.flooding.maximumRateCms, 3)} m³/s` : n.surcharge ? `surcharged ${formatNumber(n.surcharge.hoursSurcharged, 1)} h` : 'no overflow',
        ])}
        note={`Network component ${b.networkContext.modelComponentId}: ${b.networkContext.componentHasOutfall ? `drains to provisional outfall(s) ${b.networkContext.componentOutfalls.join(', ')}` : 'no model outfall'}.`}
      />
      {b.confidenceReasons.length > 0 && (
        <div className="inspector-section">
          <h4>Confidence caveats</h4>
          <ul className="plain-list small">
            {b.confidenceReasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
      {b.relatedRecommendationIds.length > 0 && <p className="small">Related recommendations: {b.relatedRecommendationIds.join(', ')} (Actions tab)</p>}
      <p className="note small">{b.explanation.disclaimer}</p>
    </>
  )
}

function DrainDetails({ p }: { p: Record<string, unknown> }) {
  const { simulationId } = useActiveTimeline()
  const bottlenecks = useBottlenecks(simulationId)
  const controller = useDigitalTwin()
  const setVisible = useViewerStore((s) => s.setVisible)
  const quality = (p.dataQuality as { flag: string; note: string }[] | undefined) ?? []
  const links = (p.modelLinkIds as string[] | undefined) ?? []
  const flagged = bottlenecks.data?.bottlenecks.filter((b) => links.includes(b.linkId)) ?? []
  return (
    <>
      <Section
        title="Source attributes (GCC GIS)"
        rows={[
          ['Source ObjectID', id(p.objectId)],
          ['Zone', p.zone],
          ['Ward', p.ward],
          ['Location', p.location],
          ['Drain type', p.drainType],
          ['Length (m, attribute)', p.lengthM],
          ['Width (m)', p.widthM],
          ['Depth (m)', p.depthM],
          ['Status', p.status],
          ['Material', p.material],
          ['Detail', p.drainDetail],
          ['Invert start / end (m)', `${display(p.sourceInvertStartM)} / ${display(p.sourceInvertEndM)}`],
        ]}
      />
      <Section
        title="Model representation (SWMM)"
        rows={[
          ['Model link IDs', links],
          ['In hydraulic model', p.inHydraulicModel],
        ]}
        note="The source ObjectID and SWMM link IDs are different identifiers; one source drain can map to several model conduits."
      />
      {simulationId && bottlenecks.data && (
        <div className="inspector-section">
          <h4>Decision support</h4>
          {flagged.length ? (
            flagged.map((b) => (
              <p key={b.linkId} className="small">
                <SeverityBadge severity={b.severity} /> {b.linkId} is a potential bottleneck.{' '}
                <button
                  type="button"
                  className="link"
                  onClick={() => {
                    setVisible('bottlenecks', true)
                    controller?.selectBottleneck(b.linkId)
                  }}
                >
                  Show evidence
                </button>
              </p>
            ))
          ) : (
            <p className="muted small">{links.length ? 'None of its model links meets the potential-bottleneck criteria in this simulation.' : 'Not represented in the hydraulic model.'}</p>
          )}
        </div>
      )}
      {quality.length > 0 && (
        <div className="inspector-section">
          <h4>Data quality flags</h4>
          <ul className="flags">
            {quality.map((q) => (
              <li key={q.flag}>
                <strong>{q.flag}</strong>: {q.note}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}

function FloodDetails({ p }: { p: Record<string, unknown> }) {
  const zone = p.featureType === 'influenceZone'
  const flooding = p.state === 'FLOODING'
  return (
    <>
      <Explain
        e={{
          what: zone
            ? `Flood influence zone of SWMM node ${String(p.nodeId)} at ${formatTimestampUtc(p.time as string)}: the area whose nearest modelled drainage node is overflowing.`
            : `SWMM model node ${String(p.nodeId)} at ${formatTimestampUtc(p.time as string)}, state ${String(p.state).toLowerCase()}.`,
          why: flooding
            ? `The node overflows at ${formatNumber(p.floodingRateCms as number, 3)} m³/s (${String(p.overflowClass).toLowerCase()} display class) at this timestamp.`
            : 'The node is surcharged (water above the conduit crown) without overflow at this timestamp.',
          source: 'EPA SWMM 5.2.4 binary output of this simulation → flood-processing-v1 (node states, nearest-node Voronoi zones in EPSG:32644).',
          consider: 'Treat this as a model-derived indication around the drainage node, not an observed flood extent. Check the Hydraulics and Actions tabs for related evidence.',
        }}
      />
      <Section
        title={zone ? 'Flood influence zone (model-derived)' : 'SWMM node state (model-derived)'}
        rows={[
          ['Timestamp', formatTimestampUtc(p.time as string)],
          ['Model node', p.nodeId],
          ['State', p.state],
          ['Overflow class', p.overflowClass],
          ['Overflow rate (m³/s)', p.floodingRateCms],
          ['Approx. cumulative overflow (m³)', p.approxCumulativeOverflowM3],
          ['Node water depth (m, in-network)', p.nodeWaterDepthM],
          ['Fill ratio', p.fillRatio],
          ...(p.zoneAreaM2 !== undefined ? ([['Zone area (m²)', p.zoneAreaM2]] as Row[]) : []),
        ]}
        note="Node depth is water depth in the drainage node, not ground flood depth. Influence zones are not flood extent."
      />
    </>
  )
}

function AssetExposure({ feature }: { feature: SelectedFeature }) {
  const { simulationId, entry } = useActiveTimeline()
  const type = feature.layer === 'buildings' ? 'buildings' : 'roads'
  const assets = useExposureAssets(simulationId, type, entry?.time ?? null, Boolean(simulationId && entry))
  const objectId = Number(feature.properties.objectId)
  const match = assets.data?.assets.find((a) => a.objectId === objectId)
  const noun = type === 'buildings' ? 'building' : 'carriageway'
  if (!simulationId || !entry) return null
  return (
    <Explain
      e={{
        what: `GCC ${noun} footprint, source ObjectID ${id(feature.properties.objectId)}.`,
        why: assets.isPending
          ? 'Checking model-derived exposure…'
          : match
            ? `At ${formatTimestampUtc(entry.time)} it intersects the flood influence zone of overflowing node(s) ${match.nodeIds.join(', ')} (${formatNumber(match.areaWithinZonesM2, 1)} m² within zones): model-derived exposure.`
            : `At ${formatTimestampUtc(entry.time)} it does not intersect any influence zone of an overflowing node.`,
        source: `GCC GIS ${noun} polygon (EPSG:32644) intersected with flood-processing-v1 influence zones → exposure-analysis-v1.`,
        consider: match
          ? 'Exposure is spatial association with a simulated overflowing drainage node, not observed flooding or damage. Consider it for preparedness and access planning only together with local knowledge.'
          : 'No model-derived exposure at this timestamp; this does not mean the location is safe from real flooding.',
      }}
    />
  )
}

function GenericDetails({ feature }: { feature: SelectedFeature }) {
  const rows = Object.entries(feature.properties).map(([k, v]) => [humanizeKey(k), /id$/i.test(k) ? id(v) : v] as Row)
  const titles: Record<string, string> = {
    buildings: 'Building (GCC source)',
    roads: 'Carriageway (GCC source)',
    boundary: 'Ward boundary (GCC source)',
    subcatchments: 'Model subcatchment (first-pass model construct)',
  }
  return (
    <>
      {(feature.layer === 'buildings' || feature.layer === 'roads') && <AssetExposure feature={feature} />}
      <Section title={titles[feature.layer] ?? feature.layer} rows={rows} />
    </>
  )
}

export function AssetInspector() {
  const selection = useViewerStore((s) => s.selection)
  const controller = useDigitalTwin()
  return (
    <Panel
      title="Inspector"
      actions={
        selection ? (
          <button type="button" className="link" onClick={() => controller?.clearSelection()}>
            Clear
          </button>
        ) : undefined
      }
    >
      {!selection && <p className="muted">Click a potential bottleneck, flood zone, drain, building, road or subcatchment in the 3D view to inspect it.</p>}
      {selection?.layer === 'bottlenecks' && <BottleneckDetails linkId={selection.id} />}
      {selection?.layer === 'drains' && <DrainDetails p={selection.properties} />}
      {selection?.layer === 'flood' && <FloodDetails p={selection.properties} />}
      {selection && !['drains', 'flood', 'bottlenecks'].includes(selection.layer) && <GenericDetails feature={selection} />}
    </Panel>
  )
}
