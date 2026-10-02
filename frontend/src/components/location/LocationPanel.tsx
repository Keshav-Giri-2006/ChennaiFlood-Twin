import { friendlyErrorMessage, messageForCode } from '../../api/client'
import { LOCATION_RADIUS_M, useCreateSimulation, useLocationCheck, useScenario, useSimulationStatus } from '../../hooks/queries'
import { useFloodStore } from '../../state/floodStore'
import { useLocationStore } from '../../state/locationStore'
import { useSimulationStore } from '../../state/simulationStore'
import type { LocationCheck, LocationNodeCondition, LocationResponseCode, SimulationStatus } from '../../types/api'
import { formatNumber, formatTimestampUtc } from '../../utils/format'
import { STAGE_LABELS, multiplierLabel } from '../../utils/resultLabels'
import { StatusBadge } from '../common/StatusBadge'

const RESPONSE_LABELS: Record<LocationResponseCode, string> = {
  OVERFLOW_AT_NEAREST_NODE: 'Overflow modelled at the nearest drainage node',
  OVERFLOW_IN_SURROUNDING_AREA: 'Overflow modelled in the surrounding area',
  SURCHARGE_ONLY: 'Surcharge only — no modelled overflow',
  NO_REPORTED_STRESS: 'No modelled overflow or surcharge',
}

const CONDITION_LABELS: Record<LocationNodeCondition, string> = {
  OVERFLOW: 'Overflow (SWMM node flooding)',
  SURCHARGE_ONLY: 'Surcharged, no overflow',
  NO_REPORTED_STRESS: 'No overflow or surcharge',
  OUTFALL: 'Model outfall (cannot overflow)',
}

const pct = (share: number) => `${formatNumber(share * 100, 1)}%`
const coord = (value: number) => `${value.toFixed(6)}°`
const range = (a: string | null, b: string | null) => (a && b ? (a === b ? formatTimestampUtc(a) : `${formatTimestampUtc(a)} – ${formatTimestampUtc(b)}`) : '—')

/** Model-derived flood response around the selected location, exactly as returned by the backend (location-check-v1). */
function LocationResult({ result, scenarioName, status }: { result: LocationCheck; scenarioName: string; status: SimulationStatus | undefined }) {
  const nearest = result.nearestNode
  const r = nearest.response
  const area = result.surroundingArea
  const showPeak = () => {
    if (!area.peak) return
    const flood = useFloodStore.getState()
    flood.pause()
    flood.selectTimestamp(result.simulationId, area.peak.index)
  }
  if (!result.nodes.length) return <p className="muted">No model-derived flood result available for this location or its surrounding area.</p>

  return (
    <section className="location-result" aria-label="Historical flood response">
      <h3 className="location-heading">
        Historical Flood Response <span className="badge">model-derived</span>
      </h3>
      <p className="muted small">
        Model-derived result for the selected historical rainfall scenario: {scenarioName} · {multiplierLabel(status)} · <code title={result.simulationId}>{result.simulationId.slice(0, 8)}</code>
      </p>
      <div className={`location-headline location-${result.response.code.toLowerCase()}`}>
        <strong>{RESPONSE_LABELS[result.response.code]}</strong>
        <p className="small">{result.response.description}</p>
      </div>

      <p className="legend-title">Nearest modelled drainage node</p>
      <dl className="kv">
        <dt>Node</dt>
        <dd>
          <code>{nearest.nodeId}</code> · {formatNumber(nearest.distanceM, 0)} m away <span className="muted small">({nearest.nodeType.toLowerCase()})</span>
        </dd>
        <dt>Condition</dt>
        <dd>{CONDITION_LABELS[r.condition]}</dd>
        {r.condition !== 'OUTFALL' && (
          <>
            <dt>Overflow at reporting times</dt>
            <dd>
              {r.overflowPeriods} × {result.intervalMinutes} min ({formatNumber(r.overflowHours, 1)} h)
            </dd>
            {r.peakOverflowRateCms != null && (
              <>
                <dt>Peak overflow rate</dt>
                <dd>
                  {formatNumber(r.peakOverflowRateCms, 3)} m³/s <span className="muted">at {formatTimestampUtc(r.peakOverflowTime)}</span>
                </dd>
                <dt>Overflow period</dt>
                <dd>{range(r.firstOverflowTime ?? null, r.lastOverflowTime ?? null)}</dd>
                <dt>Highest overflow class</dt>
                <dd>
                  {r.highestOverflowClass} <span className="muted small">(relative to this run)</span>
                </dd>
                <dt>Approx. cumulative overflow</dt>
                <dd>
                  {formatNumber(r.approxCumulativeOverflowM3, 0)} m³ <span className="muted small">(model diagnostic)</span>
                </dd>
              </>
            )}
            {!!r.surchargePeriods && (
              <>
                <dt>Surcharged at reporting times</dt>
                <dd>
                  {r.surchargePeriods} ({formatNumber(r.surchargeHours, 1)} h)
                </dd>
              </>
            )}
            <dt>Max node water depth</dt>
            <dd>
              {formatNumber(r.maxNodeWaterDepthM, 2)} m {r.maxFillRatio != null && <>· fill {pct(r.maxFillRatio)}</>} <span className="muted small">(in the drainage node, not ground flood depth)</span>
            </dd>
          </>
        )}
      </dl>

      <p className="legend-title">Surrounding area · {formatNumber(result.radiusMeters, 0)} m radius</p>
      <dl className="kv">
        <dt>Area analysed</dt>
        <dd>
          {formatNumber(area.areaWithinStudyAreaM2 / 10_000, 2)} ha {area.shareWithinStudyArea < 0.999 && <span className="muted small">({pct(area.shareWithinStudyArea)} of the circle lies in Ward 176)</span>}
        </dd>
        <dt>Associated drainage nodes</dt>
        <dd>
          {area.associatedNodeCount} <span className="muted small">({area.overflowingNodeCount} overflow · {area.surchargeOnlyNodeCount} surcharge only · {area.noReportedStressNodeCount} no reported stress)</span>
        </dd>
        <dt>Associated with overflow</dt>
        <dd>
          {pct(area.shareAssociatedWithOverflow)} of the area <span className="muted small">(influence-zone association, not a flooded area)</span>
        </dd>
        {area.peak ? (
          <>
            <dt>Peak response</dt>
            <dd>
              {formatTimestampUtc(area.peak.time)} <span className="muted small">— combined overflow {formatNumber(area.peak.combinedOverflowRateCms, 3)} m³/s from {area.peak.overflowingNodeCount} node{area.peak.overflowingNodeCount === 1 ? '' : 's'}</span>{' '}
              <button type="button" className="link" onClick={showPeak}>
                Show on timeline
              </button>
            </dd>
            <dt>Overflow period</dt>
            <dd>
              {range(area.firstOverflowTime, area.lastOverflowTime)} <span className="muted small">({formatNumber(area.overflowDurationHours, 1)} h with overflow)</span>
            </dd>
          </>
        ) : (
          <>
            <dt>Peak response</dt>
            <dd>No modelled overflow at associated nodes</dd>
          </>
        )}
        <dt>Potential bottlenecks</dt>
        <dd>
          {result.potentialBottlenecks === null
            ? 'Not available for this result'
            : result.potentialBottlenecks.length
              ? result.potentialBottlenecks.map((b) => `${b.linkId} (${b.severity?.toLowerCase() ?? 'n/a'}, ${formatNumber(b.nearestEndNodeDistanceM, 0)} m)`).join(', ')
              : `None flagged within ${formatNumber(result.radiusMeters, 0)} m`}
        </dd>
        <dt>Ground flood depth</dt>
        <dd>
          Not derived by this model <span className="muted small">— {result.notDerived.groundFloodDepth ?? 'SWMM ran without surface ponding.'}</span>
        </dd>
      </dl>

      <details className="location-limitations">
        <summary>Method and limitations</summary>
        <ul className="plain-list small">
          {result.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
        <p className="muted small">
          {result.locationCheckVersion} on {result.floodProcessingVersion}; distances and areas computed in {result.location.processingCrs}.
        </p>
      </details>
    </section>
  )
}

/**
 * Location Flood Check: pick a point in Ward 176, run (or reuse) the existing SWMM simulation for the selected
 * historical scenario, then show the backend's model-derived flood response around that point.
 */
export function LocationPanel() {
  const { location, checkRequested, runSimulationId, clearLocation, requestCheck } = useLocationStore()
  const { scenarioId, rainfallMultiplier, runningSimulationId, activeSimulationId, startTracking } = useSimulationStore()
  const scenario = useScenario(scenarioId)
  const active = useSimulationStatus(activeSimulationId)
  const tracked = useSimulationStatus(runningSimulationId ?? runSimulationId)
  const create = useCreateSimulation()

  const valid = location !== null && location.insideStudyArea !== false
  const running = Boolean(runningSimulationId) || create.isPending
  const activeCompleted = Boolean(activeSimulationId) && active.data?.simulationId === activeSimulationId && active.data?.status === 'COMPLETED'
  const runFailed = !runningSimulationId && Boolean(runSimulationId) && tracked.data?.simulationId === runSimulationId && tracked.data?.status === 'FAILED'
  const check = useLocationCheck(activeSimulationId, valid ? location : null, checkRequested && !running && activeCompleted && !runFailed)
  const scenarioName = scenario.data?.name ?? scenarioId ?? 'selected scenario'

  const runCheck = () => {
    if (!valid || !scenarioId || running) return
    create.mutate(
      { scenarioId, rainfallMultiplier: rainfallMultiplier === 1 ? undefined : rainfallMultiplier },
      {
        onSuccess: (created) => {
          startTracking(created.simulationId)
          requestCheck(created.simulationId)
        },
      },
    )
  }

  return (
    <div className="tab-body location-panel">
      <h3 className="location-heading">Location Flood Check</h3>
      <p className="muted small">Location-specific historical flood analysis using the model-derived response around a user-selected point.</p>

      <div className="location-selected" aria-live="polite">
        <span className="legend-title">Selected Location</span>
        {location ? (
          <>
            <dl className="kv">
              <dt>Latitude</dt>
              <dd>{coord(location.latitude)}</dd>
              <dt>Longitude</dt>
              <dd>{coord(location.longitude)}</dd>
            </dl>
            {location.insideStudyArea === false && (
              <p className="error-text">This point is outside Ward 176. The hydraulic model covers Ward 176 only — click inside the yellow ward boundary.</p>
            )}
            <button type="button" className="link" onClick={clearLocation}>
              Clear location
            </button>
          </>
        ) : (
          <p className="location-prompt">Click the map to select a location.</p>
        )}
        <p className="muted small">While this tab is open, map clicks place the pin. Open another tab to select map features again.</p>
      </div>

      <dl className="kv">
        <dt>Historical Scenario</dt>
        <dd>{scenarioName}</dd>
        <dt>Rainfall</dt>
        <dd>{rainfallMultiplier === 1 ? 'Historical (1.00×)' : `${rainfallMultiplier.toFixed(2)}× what-if multiplier`}</dd>
      </dl>

      <div className="button-stack">
        <button type="button" className="primary" onClick={runCheck} disabled={!valid || !scenarioId || running}>
          {running ? 'Simulation running…' : 'Run Location Flood Check'}
        </button>
        {activeCompleted && (
          <button type="button" onClick={() => requestCheck(null)} disabled={!valid || running}>
            Check displayed result (no re-run)
          </button>
        )}
      </div>
      {!location && <p className="muted small">Select a location first; the check needs a point to evaluate.</p>}
      <p className="muted small">Runs the existing EPA SWMM simulation of the Ward 176 model for the selected scenario, then evaluates the flood response within {LOCATION_RADIUS_M} m of the pin.</p>
      {create.isError && <p className="error-text">{friendlyErrorMessage(create.error)}</p>}

      {running && tracked.data && (
        <div className="sim-status" aria-live="polite">
          <div className="row">
            <StatusBadge status={tracked.data.status} />
            <span>{STAGE_LABELS[tracked.data.stage] ?? tracked.data.stage}</span>
          </div>
          <div className="progress" role="progressbar" aria-valuenow={tracked.data.progress} aria-valuemin={0} aria-valuemax={100}>
            <div style={{ width: `${tracked.data.progress}%` }} />
          </div>
          <p className="muted small">The selected location is evaluated when the simulation has completed.</p>
        </div>
      )}
      {runFailed && tracked.data?.error && (
        <p className="error-text">
          {messageForCode(tracked.data.error.code, tracked.data.error.message)} The location was not evaluated.{' '}
          <button type="button" className="link" onClick={runCheck}>
            Retry
          </button>
        </p>
      )}

      {checkRequested && valid && !running && !runFailed && !activeCompleted && !active.isPending && (
        <p className="muted">No completed simulation is displayed. Run Location Flood Check to simulate {scenarioName}.</p>
      )}
      {check.isFetching && !check.data && <p className="muted">Evaluating the selected location…</p>}
      {check.isError && <p className="error-text">{friendlyErrorMessage(check.error)}</p>}
      {check.data && !running && !runFailed && <LocationResult result={check.data} scenarioName={scenarioName} status={active.data} />}

      <p className="note-box">
        Model-derived decision support for an academic Digital Twin. Not a property assessment, flood certification or prediction for any plot: the model has no surface flow, no ground flood depth and an incomplete drainage network.
      </p>
    </div>
  )
}
