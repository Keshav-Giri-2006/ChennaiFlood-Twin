import { useEffect, useRef } from 'react'
import { useBottlenecks, useExposure, useFloodSummary, useRecommendations, useSimulationSummary } from '../../hooks/queries'
import { useSimulationStore } from '../../state/simulationStore'
import { useViewerStore } from '../../state/viewerStore'

/** Plain-language methodology and limitations (academic defensibility). */
export function MethodologyDialog() {
  const open = useViewerStore((s) => s.methodologyOpen)
  const setOpen = useViewerStore((s) => s.setMethodologyOpen)
  const simulationId = useSimulationStore((s) => s.activeSimulationId)
  const summary = useSimulationSummary(open ? simulationId : null)
  const flood = useFloodSummary(open ? simulationId : null)
  const bottlenecks = useBottlenecks(open ? simulationId : null)
  const exposure = useExposure(open ? simulationId : null)
  const recs = useRecommendations(open ? simulationId : null)
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, setOpen])

  if (!open) return null
  const versions = [
    ['Model', (summary.data?.metadata?.modelVersion as string | undefined) ?? 'ward176-hydraulic-reconstructed-v1'],
    ['Flood processing', flood.data?.metadata.floodProcessingVersion],
    ['Bottleneck analysis', bottlenecks.data?.bottleneckAnalysisVersion],
    ['Exposure analysis', exposure.data?.exposureAnalysisVersion],
    ['Decision support', recs.data?.decisionSupportVersion],
  ].filter(([, v]) => Boolean(v))

  return (
    <div className="dialog-backdrop" onClick={() => setOpen(false)}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="methodology-title" onClick={(e) => e.stopPropagation()}>
        <header className="panel-header">
          <h2 id="methodology-title">Methodology &amp; Limitations</h2>
          <button ref={closeRef} type="button" onClick={() => setOpen(false)} aria-label="Close methodology">
            Close
          </button>
        </header>
        <div className="dialog-body">
          <h3>How the results are produced</h3>
          <ul>
            <li>
              <strong>EPA SWMM 5.2.4 performs the hydraulic simulation</strong> of the Ward 176 drainage network (1D Dynamic Wave) for historical NASA GPM IMERG rainfall of Cyclone Michaung
              (Dec 2023).
            </li>
            <li>
              <strong>CesiumJS provides the 3D Digital Twin visualisation</strong> of GCC GIS buildings, carriageways and storm-water drains on Copernicus terrain. Buildings use a uniform visual
              height because no height data exist.
            </li>
            <li>
              <strong>Flood zones are model-derived spatial influence zones:</strong> the area whose nearest modelled drainage node is overflowing at the selected time. They are not a full 2D
              hydraulic flood surface, not an observed flood extent and carry no ground depth.
            </li>
            <li>
              <strong>Exposure means spatial intersection</strong> of buildings/carriageways with those model-derived zones. It is not flooding, damage or impact.
            </li>
            <li>
              <strong>Bottlenecks are model diagnostics, not confirmed drainage failures.</strong> A conduit is flagged only when SWMM reports hydraulic loading (capacity-limited, sustained
              full-bore surcharge or peak flow above full-flow capacity). Numerical solver sensitivities (e.g. C162) are listed separately.
            </li>
            <li>
              <strong>Recommendations are rule-based, evidence-traceable academic decision support</strong>, not municipal engineering orders. No AI model generates them.
            </li>
            <li>A formal risk score is not derived because hazard × exposure would not be defensible without ground flood depth or extent.</li>
          </ul>
          <h3>Presenter questions</h3>
          <dl className="faq">
            <dt>What exactly are the shaded flood polygons?</dt>
            <dd>
              For each 30-minute SWMM reporting timestamp, every drainage node that SWMM reports as overflowing gets its nearest-node (Voronoi) influence zone shaded, clipped to Ward 176. Colour
              classes rank the node overflow rate (m³/s) within the displayed run. They show <em>where overflowing nodes are</em>, not water on the ground: no depth, no observed extent.
            </dd>
            <dt>Is any of this observed data?</dt>
            <dd>Inputs are real (GCC GIS, NASA GPM IMERG rainfall, Copernicus DEM). Everything on the timeline is simulated by EPA SWMM or derived from it; nothing is a sensor reading or field observation.</dd>
            <dt>What do 1.25× and 1.50× mean?</dt>
            <dd>What-if sensitivity runs: every historical Michaung rainfall intensity is multiplied on an isolated copy of the model and SWMM is run again. They are not forecasts, warnings or climate projections.</dd>
            <dt>What is the “simulated flooding volume”?</dt>
            <dd>SWMM&apos;s flooding loss: water leaving overflowing nodes in this uncalibrated network (no surface ponding). It is a model diagnostic, not an observed flood volume.</dd>
            <dt>Why is C169 a potential bottleneck?</dt>
            <dd>Open the Hydraulics tab and select a bottleneck: the inspector lists which SWMM criteria were met (capacity-limited hours, full at both ends, peak flow above full-flow capacity, connected flooding) with the reported values.</dd>
          </dl>
          <h3>Key limitations</h3>
          <ul>
            <li>The drainage network is fragmented: many drainage components have no outfall in the model, so part of the simulated overflow reflects missing connectivity.</li>
            <li>Outfalls are provisional; roughness, infiltration and subcatchments are first-pass assumptions; the model is not calibrated or field-validated.</li>
            <li>Simulated flooding volume is a model diagnostic, not observed flood volume. Timeline values are 30-minute SWMM reporting samples.</li>
            {(summary.data?.limitations ?? []).map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
          <h3>Versions</h3>
          <dl className="kv">
            {versions.map(([k, v]) => (
              <div key={k} className="kv-row">
                <dt>{k}</dt>
                <dd>
                  <code>{v}</code>
                </dd>
              </div>
            ))}
          </dl>
          <p className="muted small">
            Full documentation: docs/FLOOD_PROCESSING_METHOD.md, docs/DECISION_SUPPORT_METHOD.md and docs/SCENARIO_ANALYSIS_METHOD.md. Data: GCC GIS · NASA GPM IMERG · Copernicus DEM GLO-30 · © OpenStreetMap contributors.
          </p>
        </div>
      </div>
    </div>
  )
}
