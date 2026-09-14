import type { KeyboardEvent, MouseEvent } from 'react'
import { useFloodStore } from '../../state/floodStore'
import type { FloodTimeline } from '../../types/api'
import { formatNumber, formatTimestampUtc } from '../../utils/format'

const W = 300
const PAD_L = 36
const PAD_R = 8
const PANEL_H = 58
const TOP_Y = 16
const BOTTOM_Y = TOP_Y + PANEL_H + 24
const AXIS_Y = BOTTOM_Y + PANEL_H
const H = AXIS_Y + 18

/** "Nice" rounded axis maximum (display only). */
function niceMax(value: number): number {
  if (!(value > 0)) return 1
  const exp = 10 ** Math.floor(Math.log10(value))
  const f = value / exp
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * exp
}

/**
 * Rainfall hyetograph and system overflow rate over the actual SWMM reporting timestamps of the
 * displayed run. Values are plotted exactly as returned by the backend timeline; the vertical
 * cursor is the selected timestamp and clicking the chart selects the nearest reporting timestamp.
 */
export function EventCharts({ simulationId, timeline, index }: { simulationId: string; timeline: FloodTimeline; index: number }) {
  const entries = timeline.entries
  const n = entries.length
  const plotW = W - PAD_L - PAD_R
  const x = (i: number) => PAD_L + (n <= 1 ? 0 : (i / (n - 1)) * plotW)
  const barW = Math.max(0.6, plotW / n - 0.3)

  const rainMax = niceMax(Math.max(...entries.map((e) => e.rainfallMmHr)))
  const flowMax = niceMax(Math.max(...entries.map((e) => e.systemFloodingRateCms)))
  const rainPeakIndex = entries.reduce((best, e, i) => (e.rainfallMmHr > entries[best].rainfallMmHr ? i : best), 0)
  const peak = entries[timeline.peakIndex]

  const flowPath = entries.map((e, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${(BOTTOM_Y + PANEL_H - (e.systemFloodingRateCms / flowMax) * PANEL_H).toFixed(1)}`).join('')
  const flowArea = `${flowPath}L${x(n - 1).toFixed(1)},${BOTTOM_Y + PANEL_H}L${x(0).toFixed(1)},${BOTTOM_Y + PANEL_H}Z`

  // Day ticks at 00:00 UTC.
  const dayTicks = entries.map((e, i) => ({ i, d: new Date(e.time) })).filter(({ d }) => d.getUTCHours() === 0 && d.getUTCMinutes() === 0)

  const select = (i: number) => {
    const { pause, selectTimestamp } = useFloodStore.getState()
    pause()
    selectTimestamp(simulationId, Math.min(n - 1, Math.max(0, i)))
  }
  const onClick = (event: MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    const vx = ((event.clientX - rect.left) / rect.width) * W
    select(Math.round(((vx - PAD_L) / plotW) * (n - 1)))
  }
  const onKey = (event: KeyboardEvent<SVGSVGElement>) => {
    if (event.key === 'ArrowRight') select(index + 1)
    else if (event.key === 'ArrowLeft') select(index - 1)
    else return
    event.preventDefault()
  }

  const current = entries[index]
  return (
    <figure className="event-charts">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="slider"
        tabIndex={0}
        aria-label="Rainfall and system overflow chart; selects the timeline timestamp"
        aria-valuemin={0}
        aria-valuemax={n - 1}
        aria-valuenow={index}
        aria-valuetext={formatTimestampUtc(current?.time)}
        onClick={onClick}
        onKeyDown={onKey}
      >
        {/* Rainfall hyetograph */}
        <text x={PAD_L} y={TOP_Y - 4} className="chart-title">
          Rainfall applied in SWMM (mm/hr)
        </text>
        <line x1={PAD_L} x2={W - PAD_R} y1={TOP_Y + PANEL_H} y2={TOP_Y + PANEL_H} className="chart-axis" />
        <text x={PAD_L - 4} y={TOP_Y + 6} className="chart-tick" textAnchor="end">
          {formatNumber(rainMax, 1)}
        </text>
        <text x={PAD_L - 4} y={TOP_Y + PANEL_H} className="chart-tick" textAnchor="end">
          0
        </text>
        {entries.map((e, i) =>
          e.rainfallMmHr > 0 ? (
            <rect key={e.key} x={x(i) - barW / 2} width={barW} y={TOP_Y + PANEL_H - (e.rainfallMmHr / rainMax) * PANEL_H} height={(e.rainfallMmHr / rainMax) * PANEL_H} className={i === rainPeakIndex ? 'chart-rain chart-rain-peak' : 'chart-rain'} />
          ) : null,
        )}
        <text x={Math.min(x(rainPeakIndex) + 4, W - PAD_R - 78)} y={TOP_Y + 8} className="chart-note">
          max {formatNumber(entries[rainPeakIndex].rainfallMmHr, 2)}
        </text>

        {/* System overflow rate */}
        <text x={PAD_L} y={BOTTOM_Y - 4} className="chart-title">
          Simulated system overflow rate (m³/s)
        </text>
        <line x1={PAD_L} x2={W - PAD_R} y1={BOTTOM_Y + PANEL_H} y2={BOTTOM_Y + PANEL_H} className="chart-axis" />
        <text x={PAD_L - 4} y={BOTTOM_Y + 6} className="chart-tick" textAnchor="end">
          {formatNumber(flowMax, 1)}
        </text>
        <text x={PAD_L - 4} y={BOTTOM_Y + PANEL_H} className="chart-tick" textAnchor="end">
          0
        </text>
        <path d={flowArea} className="chart-flow-area" />
        <path d={flowPath} className="chart-flow" />
        <circle cx={x(timeline.peakIndex)} cy={BOTTOM_Y + PANEL_H - (peak.systemFloodingRateCms / flowMax) * PANEL_H} r={3} className="chart-peak" />
        <text x={Math.min(x(timeline.peakIndex) + 5, W - PAD_R - 74)} y={BOTTOM_Y + 8} className="chart-note">
          peak {formatNumber(peak.systemFloodingRateCms, 3)}
        </text>

        {/* Day ticks */}
        {dayTicks.map(({ i, d }) => (
          <g key={i}>
            <line x1={x(i)} x2={x(i)} y1={AXIS_Y} y2={AXIS_Y + 3} className="chart-axis" />
            <text x={x(i)} y={AXIS_Y + 13} className="chart-tick" textAnchor="middle">
              {String(d.getUTCDate()).padStart(2, '0')} {d.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' })}
            </text>
          </g>
        ))}

        {/* Selected timestamp */}
        <line x1={x(index)} x2={x(index)} y1={TOP_Y} y2={AXIS_Y} className="chart-cursor" />
      </svg>
      <figcaption className="muted small">
        {formatTimestampUtc(current?.time)}: {formatNumber(current?.rainfallMmHr, 2)} mm/hr rainfall · {formatNumber(current?.systemFloodingRateCms, 3)} m³/s overflow. Values at the 30-min SWMM reporting timestamps (UTC); click the chart to jump.
      </figcaption>
    </figure>
  )
}
