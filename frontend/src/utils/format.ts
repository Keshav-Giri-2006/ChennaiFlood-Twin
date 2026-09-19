import type { Quantity } from '../types/api'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** "03 Dec 2023 22:00 UTC" — timestamps are displayed in UTC, the rainfall/SWMM time basis. */
export function formatTimestampUtc(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getUTCDate())} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`
}

const MONTHS_UPPER = MONTHS.map((m) => m.toUpperCase())

/** "03 DEC 2023" / "22:00 UTC" of a simulated reporting timestamp (never the viewer's wall-clock time). */
export function simulatedDateParts(iso: string | null | undefined): { date: string; time: string } | null {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  const pad = (n: number) => String(n).padStart(2, '0')
  return { date: `${pad(d.getUTCDate())} ${MONTHS_UPPER[d.getUTCMonth()]} ${d.getUTCFullYear()}`, time: `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC` }
}

export function formatNumber(value: number | null | undefined, maxFractionDigits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  return value.toLocaleString('en-IN', { maximumFractionDigits: maxFractionDigits })
}

/** Litres are shown in million litres for readability (1 ML = 10^6 L). */
export function formatLitres(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return `${formatNumber(value / 1_000_000, 3)} million L`
}

const UNIT_LABELS: Record<string, string> = { m2: 'm²', m3: 'm³', 'm3/s': 'm³/s', count: '', 'ISO 8601': '' }

export function formatQuantity(q: Quantity | undefined): string {
  if (!q || q.value === null || q.value === undefined) return 'Not available'
  if (typeof q.value === 'string') return q.unit === 'ISO 8601' ? formatTimestampUtc(q.value) : q.value
  if (q.unit === 'L') return formatLitres(q.value)
  const unit = UNIT_LABELS[q.unit] ?? q.unit
  return unit ? `${formatNumber(q.value, 3)} ${unit}` : formatNumber(q.value, 3)
}

export function sourceLabel(source: string | undefined): string {
  switch (source) {
    case 'source':
      return 'Source data'
    case 'model-derived':
      return 'Model-derived'
    case 'derived':
      return 'Derived'
    default:
      return source ?? ''
  }
}

export function humanizeKey(key: string): string {
  return key.replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/^./, (c) => c.toUpperCase())
}
