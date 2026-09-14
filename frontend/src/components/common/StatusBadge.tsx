import type { SimulationStatusValue } from '../../types/api'

const TONE: Record<SimulationStatusValue, string> = {
  CREATED: 'neutral',
  VALIDATING: 'active',
  PREPARING: 'active',
  RUNNING: 'active',
  PROCESSING: 'active',
  COMPLETED: 'success',
  FAILED: 'danger',
}

export function StatusBadge({ status }: { status: SimulationStatusValue }) {
  return <span className={`badge badge-${TONE[status]}`}>{status}</span>
}
