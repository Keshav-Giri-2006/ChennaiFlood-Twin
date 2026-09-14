import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiRequest, friendlyErrorMessage, requireFields, resolveUrl } from './client'
import { floodApi, simulationsApi } from './endpoints'

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn(async () => new Response(typeof body === 'string' ? body : JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

async function failure(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise
  } catch (error) {
    if (error instanceof ApiError) return error
    throw error
  }
  throw new Error('expected the request to fail')
}

describe('api client', () => {
  it('resolves relative paths against the API base and keeps opaque asset URLs', () => {
    expect(resolveUrl('/scenarios')).toBe('/api/v1/scenarios')
    expect(resolveUrl('/api/v1/simulations/x/flood/timeslices/20231203T220000Z')).toBe('/api/v1/simulations/x/flood/timeslices/20231203T220000Z')
  })

  it('maps structured backend errors to ApiError with the original code', async () => {
    mockFetch(404, { error: { code: 'TIMESTAMP_NOT_FOUND', message: 'not a reporting timestamp', requestId: 'req-1', details: null } })
    const error = await failure(apiRequest('/x'))
    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('TIMESTAMP_NOT_FOUND')
    expect(error.status).toBe(404)
    expect(error.requestId).toBe('req-1')
  })

  it('handles network failures and non-JSON bodies explicitly', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))))
    const network = await failure(apiRequest('/x'))
    expect(network.code).toBe('NETWORK_ERROR')
    expect(friendlyErrorMessage(network)).toContain('backend could not be reached')
    mockFetch(200, '<!doctype html>')
    const invalid = await failure(apiRequest('/x'))
    expect(invalid.code).toBe('INVALID_RESPONSE')
  })

  it('rejects responses missing required fields', () => {
    expect(() => requireFields({ a: 1 }, ['a', 'b' as never], 'Thing')).toThrow(/missing b/)
  })

  it('posts only scenarioId when creating a simulation', async () => {
    const fn = mockFetch(202, { simulationId: 'abc', status: 'CREATED' })
    await simulationsApi.create('michaung-2023')
    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/v1/simulations')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ scenarioId: 'michaung-2023' })
  })

  it('fetches time slices by the backend-provided asset URL', async () => {
    const fn = mockFetch(200, { type: 'FeatureCollection', features: [] })
    await floodApi.timesliceAsset('/api/v1/simulations/s1/flood/timeslices/20231203T220000Z')
    expect((fn.mock.calls[0] as unknown as [string])[0]).toBe('/api/v1/simulations/s1/flood/timeslices/20231203T220000Z')
  })
})
