import { describe, expect, it } from 'vitest'
import { formatLitres, formatQuantity, formatTimestampUtc, humanizeKey, sourceLabel } from './format'

describe('formatting', () => {
  it('formats timestamps in UTC regardless of browser timezone', () => {
    expect(formatTimestampUtc('2023-12-03T22:00:00Z')).toBe('03 Dec 2023 22:00 UTC')
    expect(formatTimestampUtc(null)).toBe('—')
    expect(formatTimestampUtc('not a date')).toBe('—')
  })

  it('formats litres as million litres', () => {
    expect(formatLitres(197_876_000)).toBe('197.876 million L')
  })

  it('never turns unavailable quantities into zero', () => {
    expect(formatQuantity({ value: null, unit: 'm', source: 'model-derived' })).toBe('Not available')
    expect(formatQuantity(undefined)).toBe('Not available')
    expect(formatQuantity({ value: 0, unit: 'count', source: 'model-derived' })).toBe('0')
  })

  it('formats units and ISO values', () => {
    expect(formatQuantity({ value: 5.435016, unit: 'm3/s', source: 'model-derived' })).toBe('5.435 m³/s')
    expect(formatQuantity({ value: '2023-12-02T03:30:00Z', unit: 'ISO 8601', source: 'model-derived' })).toBe('02 Dec 2023 03:30 UTC')
  })

  it('labels provenance', () => {
    expect(sourceLabel('model-derived')).toBe('Model-derived')
    expect(sourceLabel('source')).toBe('Source data')
    expect(humanizeKey('sourceFootprintAreaM2')).toBe('Source Footprint Area M2')
  })
})
