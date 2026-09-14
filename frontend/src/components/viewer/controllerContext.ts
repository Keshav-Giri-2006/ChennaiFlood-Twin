import { createContext, useContext } from 'react'
import type { DigitalTwinController } from '../../cesium/DigitalTwinController'

export const ControllerContext = createContext<DigitalTwinController | null>(null)

/** The single Cesium controller created by DigitalTwinViewer (null until mounted). */
export function useDigitalTwin(): DigitalTwinController | null {
  return useContext(ControllerContext)
}
