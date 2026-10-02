import { BOTTLENECK_COLORS, BOTTLENECK_INACTIVE_COLOR, COMPARISON_COLORS, EXPOSURE_COLORS, FLOOD_CLASS_COLORS, LOCATION_COLORS, NODE_MARKER, SURCHARGED_COLOR } from '../../cesium/styles'
import { LOCATION_RADIUS_M } from '../../hooks/queries'
import { useActiveTimeline } from '../../hooks/useTimeline'
import { useLocationStore } from '../../state/locationStore'
import { useViewerStore } from '../../state/viewerStore'

function Item({ color, label, line, dashed }: { color: string; label: string; line?: boolean; dashed?: boolean }) {
  return (
    <li>
      <span className={`swatch${line ? ' swatch-line' : ''}${dashed ? ' swatch-empty' : ''}`} style={dashed ? undefined : { background: color }} aria-hidden />
      {label}
    </li>
  )
}

/** Compact legend for the layers currently visible on the map. Colours only map backend classes/states. */
export function MapLegend() {
  const visibility = useViewerStore((s) => s.visibility)
  const setMethodologyOpen = useViewerStore((s) => s.setMethodologyOpen)
  const { timeline } = useActiveTimeline()
  const hasLocation = useLocationStore((s) => s.location !== null)

  return (
    <details className="layer-controls map-legend" open>
      <summary>Map legend</summary>
      <ul className="legend-list">
        {visibility.boundary && <Item color="#f5c542" line label="Ward 176 boundary" />}
        {visibility.drains && <Item color="#22d3ee" line label="Drain in SWMM model" />}
        {visibility.drains && <Item color="#94a3b8" line label="Drain not modelled" />}
        {visibility.nodes && <Item color={NODE_MARKER.normal.color} label="Drainage node, no reported stress" />}
        {hasLocation && <Item color={LOCATION_COLORS.pin} label={`Selected location · ${LOCATION_RADIUS_M} m surrounding area`} />}
      </ul>
      {visibility.flood && timeline && (
        <>
          <p className="legend-title">Simulated node flooding · influence zones</p>
          <ul className="legend-list">
            {timeline.legend.overflowClasses.map((c) => (
              <Item key={c.class} color={FLOOD_CLASS_COLORS[c.class]} label={`${c.class[0]}${c.class.slice(1).toLowerCase()} overflow rate (this run)`} />
            ))}
            <Item color={SURCHARGED_COLOR} label="Surcharged node, no overflow" />
          </ul>
          <p className="legend-note">
            Not water depth or observed extent.{' '}
            <button type="button" className="link" onClick={() => setMethodologyOpen(true)}>
              What are these?
            </button>
          </p>
        </>
      )}
      {visibility.bottlenecks && (
        <>
          <p className="legend-title">Potential bottlenecks (diagnostic concern)</p>
          <ul className="legend-list">
            <Item color={BOTTLENECK_COLORS.HIGH} line label="High" />
            <Item color={BOTTLENECK_COLORS.MODERATE} line label="Moderate" />
            <Item color={BOTTLENECK_COLORS.LOW} line label="Low" />
            <Item color={BOTTLENECK_INACTIVE_COLOR} line label="Not active at this timestamp" />
          </ul>
        </>
      )}
      {(visibility.exposureBuildings || visibility.exposureRoads) && (
        <>
          <p className="legend-title">Model-derived exposure</p>
          <ul className="legend-list">
            {visibility.exposureBuildings && <Item color={EXPOSURE_COLORS.building} label="Building in an influence zone" />}
            {visibility.exposureRoads && <Item color={EXPOSURE_COLORS.road} label="Carriageway in an influence zone" />}
          </ul>
        </>
      )}
      {visibility.comparison && (
        <>
          <p className="legend-title">Scenario comparison</p>
          <ul className="legend-list">
            <Item color={COMPARISON_COLORS.scenarioOnly} label="Additional influence (what-if only)" />
            <Item color={COMPARISON_COLORS.both} label="Influence in both runs" />
            <Item color={COMPARISON_COLORS.baselineOnly} label="Baseline only" />
          </ul>
        </>
      )}
    </details>
  )
}
