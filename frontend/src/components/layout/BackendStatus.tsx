import { useBackendHealth } from '../../hooks/queries'

/** Small liveness indicator (GET /health every 20 s). Already-loaded data stays usable when offline. */
export function BackendStatus() {
  const health = useBackendHealth()
  const state = health.isSuccess && !health.isRefetchError ? 'connected' : health.isError ? 'offline' : 'connecting'
  const label = { connected: 'Backend connected', connecting: 'Connecting to backend…', offline: 'Backend offline' }[state]
  return (
    <span className={`backend-status backend-${state}`} role="status" aria-live="polite" title={state === 'offline' ? 'Loaded map layers and results remain visible; new requests will fail until the backend is back.' : undefined}>
      <span className="dot" aria-hidden /> {label}
      {state === 'offline' && (
        <button type="button" className="link" onClick={() => void health.refetch()}>
          Retry
        </button>
      )}
    </span>
  )
}
