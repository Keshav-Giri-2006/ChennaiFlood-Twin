import { floodStateLabel, useActiveTimeline } from '../../hooks/useTimeline'
import { PLAYBACK_SPEEDS, clampIndex, useFloodStore, type PlaybackSpeed } from '../../state/floodStore'
import { formatNumber, formatTimestampUtc } from '../../utils/format'

/** Timeline controller over the actual SWMM reporting timestamps (no interpolated states). */
export function TimelineBar() {
  const { simulationId, timeline, index, entry, isPeak } = useActiveTimeline()
  const isPlaying = useFloodStore((s) => s.isPlaying)
  const speed = useFloodStore((s) => s.speed)
  const { play, pause, setSpeed, selectTimestamp } = useFloodStore.getState()

  if (!simulationId || !timeline || index === null || !entry) {
    return (
      <div className="timeline-bar timeline-empty" aria-label="Flood timeline">
        <span className="muted">The flood timeline appears when a completed simulation is displayed.</span>
      </div>
    )
  }

  const last = timeline.entries.length - 1
  const go = (target: number) => {
    const next = clampIndex(target, timeline.entries.length)
    if (next !== null) selectTimestamp(simulationId, next)
  }
  const seek = (target: number) => {
    pause()
    go(target)
  }
  const first = timeline.entries[0]
  const final = timeline.entries[last]
  const spanHours = (Date.parse(final.time) - Date.parse(first.time)) / 3_600_000
  const stateClass = isPeak ? 'state-peak' : entry.floodingNodeCount > 0 ? 'state-flooding' : entry.surchargedNodeCount > 0 ? 'state-surcharge' : 'state-dry'

  return (
    <div className="timeline-bar" role="region" aria-label="Flood timeline">
      <div className="timeline-buttons" role="group" aria-label="Playback controls">
        <button type="button" onClick={() => seek(0)} disabled={index === 0} aria-label="First timestamp" title="First timestamp">
          ⏮
        </button>
        <button type="button" onClick={() => seek(index - 1)} disabled={index === 0} aria-label="Previous timestamp" title="Previous timestamp">
          ◀
        </button>
        {isPlaying ? (
          <button type="button" className="play" onClick={pause} aria-label="Pause" title="Pause">
            ⏸
          </button>
        ) : (
          <button
            type="button"
            className="play"
            onClick={() => {
              if (index >= last) go(0)
              play()
            }}
            aria-label="Play"
            title="Play"
          >
            ▶
          </button>
        )}
        <button type="button" onClick={() => seek(index + 1)} disabled={index === last} aria-label="Next timestamp" title="Next timestamp">
          ▶|
        </button>
        <button type="button" onClick={() => seek(timeline.peakIndex)} disabled={isPeak} aria-label="Go to peak timestamp" title="Peak simulated flooding (from backend)">
          ⏭ Peak
        </button>
      </div>

      <div className="timeline-track">
        <input
          type="range"
          min={0}
          max={last}
          value={index}
          onChange={(e) => seek(Number(e.target.value))}
          aria-label="Simulation timestamp"
          aria-valuetext={formatTimestampUtc(entry.time)}
        />
        <div className="timeline-scale muted small">
          <span>{formatTimestampUtc(first.time)}</span>
          <span title={`${timeline.intervalMinutes}-min SWMM reporting timestamps · ${formatNumber(spanHours, 1)} h simulated`}>
            step {index + 1}/{timeline.entries.length} · {timeline.intervalMinutes}-min SWMM steps
          </span>
          <span>{formatTimestampUtc(final.time)}</span>
        </div>
      </div>

      <label className="timeline-speed">
        <span className="muted small">Speed</span>
        <select value={speed} onChange={(e) => setSpeed(Number(e.target.value) as PlaybackSpeed)} aria-label="Playback speed">
          {PLAYBACK_SPEEDS.map((s) => (
            <option key={s} value={s}>
              {s}×
            </option>
          ))}
        </select>
      </label>

      <div className="timeline-status" aria-live="polite">
        <strong className="timeline-time">{formatTimestampUtc(entry.time)}</strong>
        <span className={`timeline-state ${stateClass}`}>{floodStateLabel(entry, isPeak)}</span>
        <span className="small">
          <strong>{entry.floodingNodeCount}</strong> flooding nodes · <strong>{entry.surchargedNodeCount}</strong> surcharged nodes
        </span>
      </div>
    </div>
  )
}
