import type { KeyboardEvent } from 'react'
import { useViewerStore, type DashboardTab } from '../../state/viewerStore'
import { ErrorBoundary } from '../common/ErrorBoundary'
import { ComparisonPanel } from '../decision/ComparisonPanel'
import { ExposurePanel } from '../decision/ExposurePanel'
import { HydraulicsPanel } from '../decision/HydraulicsPanel'
import { RecommendationsPanel } from '../decision/RecommendationsPanel'
import { FloodPanel } from '../flood/FloodPanel'
import { LocationPanel } from '../location/LocationPanel'

const TABS: { id: DashboardTab; label: string }[] = [
  { id: 'flood', label: 'Flood' },
  { id: 'hydraulics', label: 'Hydraulics' },
  { id: 'exposure', label: 'Exposure' },
  { id: 'actions', label: 'Actions' },
  { id: 'compare', label: 'Compare' },
  { id: 'location', label: 'Location' },
]

/** Decision-support panels. Switching tabs only changes React panels; the Cesium viewer is untouched. */
export function DashboardTabs() {
  const tab = useViewerStore((s) => s.dashboardTab)
  const setTab = useViewerStore((s) => s.setDashboardTab)

  const onKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return
    const i = TABS.findIndex((t) => t.id === tab)
    const next = TABS[(i + (event.key === 'ArrowRight' ? 1 : TABS.length - 1)) % TABS.length]
    setTab(next.id)
    document.getElementById(`tab-${next.id}`)?.focus()
  }

  return (
    <section className="panel dashboard" aria-label="Decision support">
      <div className="tabs" role="tablist" aria-label="Decision support panels" onKeyDown={onKey}>
        {TABS.map((t) => (
          <button
            key={t.id}
            id={`tab-${t.id}`}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            aria-controls={`tabpanel-${t.id}`}
            tabIndex={tab === t.id ? 0 : -1}
            className={tab === t.id ? 'tab active' : 'tab'}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`tabpanel-${tab}`} aria-labelledby={`tab-${tab}`}>
        <ErrorBoundary label={`${TABS.find((t) => t.id === tab)?.label} panel`}>
          {tab === 'flood' && <FloodPanel />}
          {tab === 'hydraulics' && <HydraulicsPanel />}
          {tab === 'exposure' && <ExposurePanel />}
          {tab === 'actions' && <RecommendationsPanel />}
          {tab === 'compare' && <ComparisonPanel />}
          {tab === 'location' && <LocationPanel />}
        </ErrorBoundary>
      </div>
    </section>
  )
}
