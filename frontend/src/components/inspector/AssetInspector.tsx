import { useDigitalTwin } from '../viewer/controllerContext'
import { useViewerStore, type SelectedFeature } from '../../state/viewerStore'
import { formatNumber, humanizeKey } from '../../utils/format'
import { Panel } from '../common/Panel'

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

function DrainDetails({ p }: { p: Record<string, unknown> }) {
  const quality = (p.dataQuality as { flag: string; note: string }[] | undefined) ?? []
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
          ['Model link IDs', p.modelLinkIds],
          ['In hydraulic model', p.inHydraulicModel],
        ]}
        note="The source ObjectID and SWMM link IDs are different identifiers; one source drain can map to several model conduits."
      />
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
  return (
    <Section
      title={p.featureType === 'influenceZone' ? 'Flood influence zone (model-derived)' : 'SWMM node state (model-derived)'}
      rows={[
        ['Model node', p.nodeId],
        ['State', p.state],
        ['Overflow class', p.overflowClass],
        ['Overflow rate (m³/s)', p.floodingRateCms],
        ['Approx. cumulative overflow (m³)', p.approxCumulativeOverflowM3],
        ['Node water depth (m, in-network)', p.nodeWaterDepthM],
        ['Fill ratio', p.fillRatio],
        ...(p.zoneAreaM2 !== undefined ? ([['Zone area (m²)', p.zoneAreaM2]] as Row[]) : []),
      ]}
      note="Node depth is water depth in the drainage node, not ground flood depth. Influence zones associate surrounding area with the nearest model node; they are not flood extent."
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
  return <Section title={titles[feature.layer] ?? feature.layer} rows={rows} />
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
      {!selection && <p className="muted">Click a drain, building, road, subcatchment or flood feature in the 3D view to inspect it.</p>}
      {selection?.layer === 'drains' && <DrainDetails p={selection.properties} />}
      {selection?.layer === 'flood' && <FloodDetails p={selection.properties} />}
      {selection && selection.layer !== 'drains' && selection.layer !== 'flood' && <GenericDetails feature={selection} />}
    </Panel>
  )
}
