# ChennaiFlood-Twin — Cesium Performance Notes

Measured 2026-09-14 on the development/demo laptop: Intel UHD Graphics (ANGLE Direct3D 11), 16 GB RAM, 1600 × 853 px canvas, real Ward 176 data (6,428 buildings → 6,565 polygon entities, 301 carriageways → 332 polygons, 135 drains → 137 polylines, 35 subcatchments, DEM terrain, OSM imagery, 42-entity peak flood slice).

## Method

- In-app frame profiler `DigitalTwinController.profileFrames(ms)` counts `scene.postRender` events of the normal render loop and reports fps and p50/p95 frame intervals.
- The embedded IDE preview pane throttles or stops `requestAnimationFrame` whenever it is hidden (it reported 0–7 fps and, in a synchronous render benchmark, meaningless sub-millisecond frames), so it is **not** used for numbers.
- Measurements ran in a **separate headless Microsoft Edge** instance (new headless mode, hardware ANGLE D3D11, temporary profile) driven over the DevTools protocol against the running dev app. Each configuration toggles layers, waits 2.5 s and records 5–6 s. Headless frame pacing limits this setup to ≈ 21–23 fps even with no globe, so values near 20 fps are the environment ceiling.

## Baseline (Prompt 3 rendering: ground-clamped roads, drains, subcatchments, ward outline)

| Configuration | fps | p50 frame (ms) | p95 frame (ms) |
|---|---|---|---|
| All layers | 4.3 – 5.2 | 169 – 235 | 286 – 290 |
| Buildings hidden | 4.3 | 231 | 291 |
| Roads hidden | 7.3 | 135 | 171 |
| Drains hidden | 5.2 | 197 | 229 |
| Roads + drains hidden | 10.0 (18.0 in a repeat) | 99 (56) | 143 |
| Flood hidden | 4.7 | 221 | 285 |
| Terrain + imagery only | 11.3 – 18.4 | 54 – 87 | 53 – 126 |
| All layers + timeline playback 1× | 6.5 | 150 | 291 |

Diagnostic experiments (terrain only): no globe 21.9 fps; no atmosphere/fog/FXAA 19.9; no depth test against terrain 19.4; `resolutionScale 0.75` 28.4; disabling CSS `backdrop-filter` or hiding all UI overlays +1–2 fps. Conclusion: buildings (≈ 6.5 k extruded polygons in a few batches) and the flood layer are cheap; the **ground-clamped carriageway polygons and drain polylines cost ≈ 95 ms per frame** (classification / ground-polyline passes over terrain). The earlier Prompt 3 observation was confirmed by measurement.

## Change

Roads, drains, subcatchments and the ward outline are now drawn as ordinary batched primitives at **DEM-sampled heights** instead of ground-clamped classification geometry:

- Each vertex height = the same bilinear DEM sample the terrain provider uses (`sampleDem`), × vertical exaggeration, + a small draping offset (subcatchments 0.3 m, roads 0.5 m, drains 1.0 m, ward outline 1.5 m); 0 m when terrain is switched off.
- The DEM grid now loads before these layers; positions are recomputed (not re-downloaded) when terrain or exaggeration changes.
- No feature, vertex or attribute was removed or simplified; buildings, flood zones, bottlenecks and comparison zones are unchanged.
- Visual trade-off: between vertices the terrain mesh can differ slightly from a flat polygon, which the offsets absorb at 1×; at 3–5× exaggeration a small parallax can appear (exaggeration is a labelled visual aid).

## After

| Configuration | fps | p50 frame (ms) | p95 frame (ms) |
|---|---|---|---|
| All layers | **19.0 – 20.0** | **51.5 – 52.8** | 56.4 – 56.7 |
| Buildings hidden | 19.5 | 51.6 | 57.2 |
| Roads hidden | 19.3 | 52.0 | 56.3 |
| Drains hidden | 19.6 | 51.1 | 55.8 |
| Roads + drains hidden | 19.5 | 51.4 | 56.2 |
| Flood hidden | 20.5 | 49.4 | 53.2 |
| Terrain + imagery only | 20.8 | 48.4 | 52.5 |
| All layers + timeline playback 1× | 19.5 | 50.1 | 58.1 |

All layers now render at the environment ceiling (≈ 4× faster; p50 frame time 235 → 52 ms). Layer toggles no longer change frame time measurably.

## Dynamic updates (unchanged design, verified)

- Flood time-slice replacement: 0.1 – 1.1 ms per timestep (≈ 20–42 entities); static layers are never reloaded (`stats.staticLayerLoads` stays 5 through playback, scenario switches and comparison).
- Exposure highlighting: only changed entity materials are updated (25–68 per step at the peak).
- Bottleneck time state: restyles ≤ 12 links only when the active set changes; comparison zones are created once and re-styled.
- Playback preloads the next 3 slices; at 1× it advanced exactly 10 timestamps in 10.0 s; at 4× 36 of 40 in 10 s on the slower pre-optimisation build.

## 3D Tiles decision

Not introduced. Measurements show buildings are not the bottleneck (hiding them changed nothing measurable before or after), and the scene now renders at the headless ceiling with all data. Revisit only if the presentation machine is slower than this laptop or the building dataset grows substantially.

## Reproducing on the presentation machine

In a visible browser with the dev build, open the developer console and run `await window.__digitalTwin.profileFrames(6000)` (dev builds only). Compare with the table above; if fps is low, first check that hardware acceleration is enabled in the browser.

## Prompt 5 re-check (2026-09-14)

The same headless-Edge profiler was run against the dev app, now with the new SVG charts, map legend and header chip. The static rendering mode `terrain-sampled-primitives` is unchanged.

The machine was also running the Docker Desktop VM, so the environment ceiling was lower and noisier than in Prompt 4.

| Run | All layers | All layers + playback 1× | Terrain + imagery only |
|---|---|---|---|
| 1 | — | 20.6 fps (p50 41 ms) | — |
| 2 | 21.0 fps (p50 47 ms); repeat 13.5 fps | 14.4 fps | 18.2 fps |

- **Layers are not the limit:** layer toggles stay within the environment noise. For example, only terrain gave 18.2 fps while all layers gave 21.0 fps in the same run.
- **Static layers load once:** `staticLayerLoads` stays 5 through playback, scenario switches, comparison and reset.
- **Flood updates stay cheap:** slice updates take ≈ 0.4 ms.
- **Chart cost is small:** the charts re-render once per timeline step (≤ 190 SVG rects).
- **3D Tiles are still not needed.**
- **Production bundle:** 4.52 MB JS (1.23 MB gzip), nginx-served with gzip and immutable asset caching in Docker.
- **Presentation machine:** measure there with `await window.__digitalTwin.profileFrames(6000)` in the dev build (see *Reproducing* above). Close Docker Desktop if Option A is used, since its VM competes for CPU/GPU.

## Prompt 6 re-check (2026-09-19) — visual enhancement pass

Same headless-Edge profiler, dev app, peak flood timestamp, all layers on. The machine was also running the
backend, the Vite dev server and previous browser instances, so absolute values are lower and noisier than
the Prompt 4 figures; the comparison within the session is what matters.

| Configuration | fps | p50 frame (ms) | p95 frame (ms) |
|---|---|---|---|
| All layers + rainfall overlay | 15.5 | 64.1 | 111.6 |
| All layers, rainfall overlay off | 16.2 | 60.6 | 110.4 |
| All layers + rainfall overlay (repeat) | 15.3 | 64.3 | 73.0 |
| Rainfall on, drainage-node layer off | 15.8 | 62.8 | 70.0 |
| Timeline playback 1x + rainfall + nodes | 15.5 | 63.3 | 78.1 |

- **Rainfall overlay cost:** ≈ 0.5–0.9 fps, within the run-to-run noise of this machine. It is three CSS layers
  animated by the compositor (transform only), not Cesium geometry, and it is removed from the DOM at 0 mm/hr.
- **Drainage-node layer (228 point entities):** no measurable cost.
- **Node pulse and flood fade** use Cesium `CallbackProperty` on at most ~40 flood entities and reuse a scratch
  `Color`, so they add no per-frame allocations of note.
- **A GPU post-process shader was tried first and abandoned:** it was harder to verify (it rendered, but the
  streaks were barely visible against the bright basemap and the debugging cost was high), and the CSS overlay
  gives the same screen-space result with simpler disposal. Not a performance decision.
