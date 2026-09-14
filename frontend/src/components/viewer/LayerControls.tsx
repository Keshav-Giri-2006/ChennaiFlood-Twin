import { useViewerStore, type LayerKey } from '../../state/viewerStore'
import { BUILDING_VISUAL_EXTRUSION_M } from '../../cesium/styles'
import { formatNumber } from '../../utils/format'

const LAYERS: { key: LayerKey; label: string; hint?: string }[] = [
  { key: 'terrain', label: 'Terrain (Copernicus DEM)', hint: 'DSM-derived, ~30 m' },
  { key: 'boundary', label: 'Ward 176 boundary' },
  { key: 'buildings', label: 'Buildings', hint: `uniform ${BUILDING_VISUAL_EXTRUSION_M} m visual extrusion — no height data` },
  { key: 'roads', label: 'Roads (carriageways)' },
  { key: 'drains', label: 'Storm-water drains', hint: 'cyan = in SWMM model, grey = not modelled' },
  { key: 'subcatchments', label: 'Model subcatchments', hint: 'first-pass model constructs' },
  { key: 'flood', label: 'Simulated node flooding', hint: 'model-derived' },
]

export function LayerControls() {
  const visibility = useViewerStore((s) => s.visibility)
  const loadState = useViewerStore((s) => s.loadState)
  const setVisible = useViewerStore((s) => s.setVisible)
  const exaggeration = useViewerStore((s) => s.verticalExaggeration)
  const setExaggeration = useViewerStore((s) => s.setVerticalExaggeration)

  return (
    <div className="layer-controls" role="group" aria-label="Layer controls">
      <h3>Layers</h3>
      <ul>
        {LAYERS.map(({ key, label, hint }) => {
          const ls = loadState[key]
          return (
            <li key={key}>
              <label title={hint}>
                <input type="checkbox" checked={visibility[key]} onChange={(e) => setVisible(key, e.target.checked)} />
                <span>{label}</span>
              </label>
              <span className={`layer-state layer-state-${ls?.state ?? 'idle'}`} title={ls?.message ?? (ls?.loadMs ? `${ls.loadMs} ms` : undefined)}>
                {ls?.state === 'loading' && 'loading…'}
                {ls?.state === 'ready' && (ls.featureCount !== undefined ? formatNumber(ls.featureCount, 0) : '✓')}
                {ls?.state === 'error' && 'unavailable'}
              </span>
            </li>
          )
        })}
      </ul>
      <label className="field compact">
        <span>Terrain exaggeration (visual aid only)</span>
        <select value={exaggeration} onChange={(e) => setExaggeration(Number(e.target.value))}>
          {[1, 2, 3, 5].map((v) => (
            <option key={v} value={v}>
              {v}×
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}
