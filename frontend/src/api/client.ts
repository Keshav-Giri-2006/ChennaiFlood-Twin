import type { ApiErrorBody } from '../types/api'

export const API_BASE_URL: string = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api/v1'

/** Error raised for any non-2xx API response or network failure. Keeps the backend code for debugging. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string | null
  readonly details: unknown

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.name = 'ApiError'
    this.status = status
    this.code = body.code
    this.requestId = body.requestId ?? null
    this.details = body.details
  }
}

function isErrorBody(value: unknown): value is { error: ApiErrorBody } {
  if (typeof value !== 'object' || value === null || !('error' in value)) return false
  const err = (value as { error: unknown }).error
  return typeof err === 'object' && err !== null && typeof (err as ApiErrorBody).code === 'string'
}

/** Resolve an API path ("/scenarios") or an opaque absolute API URL returned by the backend. */
export function resolveUrl(pathOrUrl: string): string {
  if (/^https?:\/\//.test(pathOrUrl) || pathOrUrl.startsWith(API_BASE_URL)) return pathOrUrl
  return `${API_BASE_URL}${pathOrUrl}`
}

export interface RequestOptions {
  method?: 'GET' | 'POST'
  body?: unknown
  signal?: AbortSignal
  /** Abort the request after this many milliseconds (default 30 s). */
  timeoutMs?: number
}

export const DEFAULT_TIMEOUT_MS = 30_000

export async function apiRequest<T>(pathOrUrl: string, options: RequestOptions = {}): Promise<T> {
  let response: Response
  const timeout = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    timeout.abort()
  }, options.timeoutMs ?? DEFAULT_TIMEOUT_MS)
  const onCallerAbort = () => timeout.abort()
  options.signal?.addEventListener('abort', onCallerAbort)
  try {
    response = await fetch(resolveUrl(pathOrUrl), {
      method: options.method ?? 'GET',
      headers: options.body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: timeout.signal,
    })
  } catch (error) {
    if (timedOut) throw new ApiError(0, { code: 'NETWORK_TIMEOUT', message: 'The API did not respond in time.' })
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, { code: 'NETWORK_ERROR', message: 'The ChennaiFlood-Twin API could not be reached.' })
  } finally {
    clearTimeout(timer)
    options.signal?.removeEventListener('abort', onCallerAbort)
  }

  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      throw new ApiError(response.status, { code: 'INVALID_RESPONSE', message: 'The API returned a response that is not valid JSON.' })
    }
  }
  if (!response.ok) {
    if (isErrorBody(payload)) throw new ApiError(response.status, payload.error)
    throw new ApiError(response.status, { code: 'HTTP_ERROR', message: `The API request failed with status ${response.status}.` })
  }
  return payload as T
}

/** Defensive runtime check for required top-level fields of an API response. */
export function requireFields<T extends object>(value: unknown, fields: (keyof T)[], label: string): T {
  if (typeof value !== 'object' || value === null) {
    throw new ApiError(200, { code: 'INVALID_RESPONSE', message: `${label}: response is not an object.` })
  }
  const missing = fields.filter((f) => !(f in value))
  if (missing.length) {
    throw new ApiError(200, { code: 'INVALID_RESPONSE', message: `${label}: response is missing ${missing.join(', ')}.` })
  }
  return value as T
}

const FRIENDLY_MESSAGES: Record<string, string> = {
  NETWORK_ERROR: 'The backend could not be reached. Check that the API server is running and try again.',
  NETWORK_TIMEOUT: 'The backend did not respond in time. Check the backend and try again.',
  INVALID_RESPONSE: 'The backend returned an unexpected response. Reload the result or try again.',
  INTERNAL_ERROR: 'The backend hit an internal error. Try again; if it persists, check the backend log.',
  SIMULATION_FAILED: 'Simulation could not be completed. Check the backend and try again.',
  PROCESSING_FAILED: 'The simulation results could not be processed. Check the backend and try again.',
  SCENARIO_NOT_FOUND: 'The selected scenario is not available on the backend.',
  SIMULATION_NOT_FOUND: 'This result is no longer available on the backend. Load the demo result or run a new simulation.',
  RESULT_NOT_FOUND: 'The stored result files are missing. Load the demo result or run a new simulation.',
  FLOOD_PRODUCT_NOT_AVAILABLE: 'This flood product is not derived by the current method.',
  GEOSPATIAL_ERROR: 'This map layer is currently unavailable.',
  INVALID_TIMESTAMP: 'The selected time is not valid for this result.',
  TIMESTAMP_NOT_FOUND: 'The selected time is not a reporting timestamp of this result.',
  INVALID_PARAMETER: 'The scenario parameter is outside the allowed range.',
  COMPARISON_NOT_COMPATIBLE: 'These two results cannot be compared.',
  SIMULATION_TIMEOUT: 'The flood simulation took too long to complete. Please try again.',
  SWMM_UNAVAILABLE: 'The SWMM simulation engine is not available on the server.',
  SIMULATION_NOT_COMPLETED: 'Results are available once the simulation has completed.',
  SIMULATION_INTERRUPTED: 'The simulation was interrupted because the backend restarted.',
}

/** Concise user-facing message; never exposes stack traces or raw technical details. */
export function friendlyErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return FRIENDLY_MESSAGES[error.code] ?? (error.status >= 500 ? FRIENDLY_MESSAGES.INTERNAL_ERROR : error.message)
  if (error instanceof DOMException && error.name === 'AbortError') return 'The request was cancelled.'
  return 'An unexpected error occurred. Try again.'
}

/** Friendly message for a backend error code (e.g. a FAILED simulation's error), falling back to the backend's safe message. */
export function messageForCode(code: string, fallback: string): string {
  return FRIENDLY_MESSAGES[code] ?? fallback
}

export function isOfflineError(error: unknown): boolean {
  return error instanceof ApiError && (error.code === 'NETWORK_ERROR' || error.code === 'NETWORK_TIMEOUT')
}
