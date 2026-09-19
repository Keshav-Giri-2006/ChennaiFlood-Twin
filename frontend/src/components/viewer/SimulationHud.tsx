import { rainVisual } from '../../cesium/rainfall'
import { floodStateLabel, useActiveTimeline } from '../../hooks/useTimeline'
import { formatNumber, simulatedDateParts } from '../../utils/format'

/**
 * Heads-up display over the 3D scene: the simulated timestamp and the simulated rainfall intensity of the
 * displayed run at that timestamp. Both values come from the backend flood timeline of the active
 * simulation, so a what-if run shows its own scaled rainfall, not the historical series.
 */
export function SimulationHud() {
  const { entry, isPeak } = useActiveTimeline()
  if (!entry) return null
  const parts = simulatedDateParts(entry.time)
  const rain = rainVisual(entry.rainfallMmHr)

  return (
    <div className="sim-hud" aria-label="Simulated time and rainfall">
      <div className="hud-time">
        <span className="hud-date">{parts?.date ?? '—'}</span>
        <span className="hud-clock">{parts?.time ?? '—'}</span>
        <span className="hud-caption">Simulated time · {floodStateLabel(entry, isPeak)}</span>
      </div>
      <div className="hud-rain">
        <span className="hud-label">Rainfall (simulated)</span>
        <span className="hud-value">
          {formatNumber(entry.rainfallMmHr, 2)} <span className="hud-unit">mm/hr</span>
        </span>
        <span className={`hud-class rain-${rain.label.replace(' ', '-').toLowerCase()}`}>{rain.label === 'NONE' ? 'NO RAINFALL' : rain.label}</span>
        <span className="hud-bar" aria-hidden>
          <span style={{ width: `${Math.round(rain.intensity * 100)}%` }} />
        </span>
      </div>
    </div>
  )
}
