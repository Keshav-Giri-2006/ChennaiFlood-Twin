import { useEffect } from 'react'
import { LOCATION_RADIUS_M } from '../../hooks/queries'
import { useLocationStore } from '../../state/locationStore'
import { useViewerStore } from '../../state/viewerStore'
import { useDigitalTwin } from '../viewer/controllerContext'

/**
 * Pushes Location Flood Check state into the scene: map clicks pick a location while the Location tab is
 * open (other tabs keep normal feature selection), and the single pin follows the selected location.
 * No Cesium event handlers are registered here; the controller owns its one click handler.
 */
export function LocationLayerSync() {
  const controller = useDigitalTwin()
  const locationTab = useViewerStore((s) => s.dashboardTab === 'location')
  const location = useLocationStore((s) => s.location)

  useEffect(() => {
    if (!controller) return
    controller.setLocationMode(locationTab)
    return () => controller.setLocationMode(false)
  }, [controller, locationTab])

  useEffect(() => {
    controller?.setLocationPin(location ? { ...location, radiusMeters: LOCATION_RADIUS_M } : null)
  }, [controller, location])

  return null
}
