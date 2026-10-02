"""flood-processing-v1: node-based simulated flooding states + nearest-node flood influence zones.

Method summary (full documentation: docs/FLOOD_PROCESSING_METHOD.md)

1. Node states per SWMM reporting timestamp (from the binary output):
   * FLOODING   - SWMM node flooding (overflow) rate > 0 m3/s
   * SURCHARGED - not flooding, and node water depth > crown of the highest
                  connected conduit (+1 mm tolerance)
   Outfalls are excluded (free outfalls cannot flood).
2. Flood influence zone of a node = its nearest-model-node (Voronoi) cell,
   computed in EPSG:32644 from the reconstructed node coordinates and clipped
   to the Ward 176 boundary. Zones are a spatial association of the
   surrounding area with the closest modelled drainage node. They are NOT a
   flood extent and carry NO depth.
3. Overflow-rate classes (LOW / MODERATE / HIGH) are visualisation classes
   relative to this simulation: breaks at the 50th and 90th percentiles of all
   non-zero node flooding-rate samples. They are not hazard thresholds.
4. Approximate cumulative overflow volume per node: trapezoidal integration of
   reporting-period flooding rates (zero at simulation start). Cross-checked
   against the SWMM report flooding loss.

Not derived (deliberately): ground flood depth and flood extent. With
ALLOW_PONDING=NO, SWMM removes overflow from the system and caps node depth at
the rim, so no surface water depth exists in the output; model rim elevations
and the Copernicus DSM are also not vertically consistent (see method doc).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
from shapely import MultiPoint, Point, union_all, voronoi_polygons
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

from app.gis.network_mapping import NetworkMapping
from app.gis.transform import UTM44N, bbox_of, geometry_to_web, transform_xy, within_envelope
from app.simulation.inp_reader import InpModel
from app.simulation.output_reader import SwmmOutput
from app.simulation.report_parser import SwmmReport
from app.utils.timeutil import to_iso_z

SURCHARGE_TOLERANCE_M = 0.001
CUMULATIVE_VOLUME_TOLERANCE = 0.05  # 5 % vs report flooding loss
STATE_FLOODING = "FLOODING"
STATE_SURCHARGED = "SURCHARGED"
CLASS_ORDER = ("LOW", "MODERATE", "HIGH")


class FloodProcessingError(Exception):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.details = details


def timestamp_key(value: datetime) -> str:
    """Filesystem/URL-safe key for a timestamp, e.g. 20231203T220000Z."""
    return value.strftime("%Y%m%dT%H%M%SZ")


@dataclass
class FloodProducts:
    manifest: dict[str, Any]
    timeline: dict[str, Any]
    zones: dict[str, Any]
    timeslices: dict[str, dict[str, Any]]
    diagnostics: dict[str, Any]


def node_crown_heights(inp: InpModel) -> dict[str, float]:
    """Height above node invert of the top of the highest connected conduit (LINK_OFFSETS=DEPTH)."""
    if inp.options.get("LINK_OFFSETS", "DEPTH").upper() != "DEPTH":
        raise FloodProcessingError("Only LINK_OFFSETS=DEPTH models are supported by flood-processing-v1")
    crowns: dict[str, float] = {}
    for link_id, conduit in inp.conduits.items():
        xs = inp.xsections.get(link_id)
        if xs is None:
            raise FloodProcessingError(f"Conduit {link_id} has no cross-section")
        full = float(xs["fullDepthM"])
        for node, offset in ((conduit["fromNode"], conduit["inOffsetM"]), (conduit["toNode"], conduit["outOffsetM"])):
            crowns[str(node)] = max(crowns.get(str(node), 0.0), float(offset) + full)
    return crowns


def _web_geometry(geom: BaseGeometry) -> dict[str, Any]:
    return geometry_to_web(mapping(geom), UTM44N)


def _influence_zones(node_ids: list[str], mapping_: NetworkMapping, ward: BaseGeometry) -> dict[str, BaseGeometry]:
    points = [Point(mapping_.node_locations[n].easting_m, mapping_.node_locations[n].northing_m) for n in node_ids]
    cells = list(voronoi_polygons(MultiPoint(points), extend_to=ward.envelope.buffer(1000)).geoms)
    if len(cells) != len(points):
        raise FloodProcessingError("Voronoi cell count does not match node count (duplicate node coordinates?)")
    zones: dict[str, BaseGeometry] = {}
    for node_id, point in zip(node_ids, points, strict=True):
        owners = [c for c in cells if c.contains(point)]
        if len(owners) != 1:
            raise FloodProcessingError(f"Could not assign a unique Voronoi cell to node {node_id}")
        zones[node_id] = owners[0].intersection(ward)
    return zones


influence_zones = _influence_zones  # public name used by exposure-analysis-v1 (same zones as the flood products)


@dataclass
class NodeStates:
    """Junction states at every SWMM reporting timestamp, as defined by flood-processing-v1.

    Arrays are (reporting periods x junctions). Shared by the flood products and
    location-check-v1 so both use exactly the same state definitions.
    """

    times: list[datetime]
    junction_ids: list[str]
    depth: np.ndarray
    head: np.ndarray
    flooding: np.ndarray
    is_flooding: np.ndarray
    is_surcharged: np.ndarray
    cumulative: np.ndarray
    effective_full: np.ndarray
    p50: float
    p90: float
    event_max_rate: float

    def overflow_class(self, rate: float) -> str:
        if rate <= self.p50:
            return "LOW"
        return "MODERATE" if rate <= self.p90 else "HIGH"


def compute_node_states(output: SwmmOutput, inp: InpModel) -> NodeStates:
    node_ids = output.node_ids
    if node_ids != inp.node_ids:
        raise FloodProcessingError("Output node IDs differ from the model input")
    junction_ids = [n for n in node_ids if n in inp.junctions]
    j_index = [node_ids.index(n) for n in junction_ids]

    depth = np.asarray(output.node_series("depth"), dtype=np.float64)[:, j_index]
    head = np.asarray(output.node_series("head"), dtype=np.float64)[:, j_index]
    flooding = np.asarray(output.node_series("flooding"), dtype=np.float64)[:, j_index]
    times = output.times

    crowns = node_crown_heights(inp)
    crown = np.array([crowns.get(n, 0.0) for n in junction_ids])
    max_depth = np.array([inp.junctions[n]["maxDepthM"] for n in junction_ids])
    effective_full = np.maximum(max_depth, crown)  # SWMM Warning 02 raises max depth to the crown

    is_flooding = flooding > 0.0
    is_surcharged = (~is_flooding) & (depth > crown + SURCHARGE_TOLERANCE_M)

    # Visualisation classes from the empirical distribution of non-zero overflow rates.
    nonzero = flooding[is_flooding]
    if nonzero.size:
        p50, p90 = (float(np.percentile(nonzero, q)) for q in (50, 90))
        event_max_rate = float(nonzero.max())
    else:
        p50 = p90 = event_max_rate = 0.0

    # Trapezoidal cumulative overflow volume (m3); flooding is zero at simulation start.
    sim_start = inp.simulation_start()
    dt = np.array([(times[0] - sim_start).total_seconds()] + [(b - a).total_seconds() for a, b in zip(times, times[1:])])
    previous = np.vstack([np.zeros(len(junction_ids)), flooding[:-1]])
    cumulative = np.cumsum((previous + flooding) / 2.0 * dt[:, None], axis=0)

    return NodeStates(
        times=list(times),
        junction_ids=junction_ids,
        depth=depth,
        head=head,
        flooding=flooding,
        is_flooding=is_flooding,
        is_surcharged=is_surcharged,
        cumulative=cumulative,
        effective_full=effective_full,
        p50=p50,
        p90=p90,
        event_max_rate=event_max_rate,
    )


def generate_flood_products(
    *,
    simulation_id: str,
    scenario_id: str,
    model_version: str,
    flood_processing_version: str,
    output: SwmmOutput,
    report: SwmmReport,
    inp: InpModel,
    network: NetworkMapping,
    ward_utm: BaseGeometry,
    generated_at: datetime,
) -> FloodProducts:
    node_ids = output.node_ids
    states = compute_node_states(output, inp)
    junction_ids = states.junction_ids
    depth, head, flooding = states.depth, states.head, states.flooding
    is_flooding, is_surcharged, cumulative = states.is_flooding, states.is_surcharged, states.cumulative
    effective_full = states.effective_full
    p50, p90, event_max_rate = states.p50, states.p90, states.event_max_rate
    overflow_class = states.overflow_class
    nonzero = flooding[is_flooding]
    rainfall = output.system_series("rainfall")
    system_flooding = output.system_series("flooding")
    times = output.times
    n_periods = len(times)

    # Spatial association.
    zones_utm = _influence_zones(node_ids, network, ward_utm)
    zone_area = {n: g.area for n, g in zones_utm.items()}
    lons, lats = transform_xy(UTM44N, [network.node_locations[n].easting_m for n in node_ids], [network.node_locations[n].northing_m for n in node_ids])
    node_lonlat = {n: [round(x, 7), round(y, 7)] for n, x, y in zip(node_ids, lons, lats, strict=True)}
    ward_area = ward_utm.area

    # ---- validation ----------------------------------------------------------------
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, message: str, details: Any = None, hard: bool = True) -> None:
        checks.append({"check": name, "passed": bool(passed), "hard": hard, "details": details})
        if hard and not passed:
            raise FloodProcessingError(message, details)

    non_empty = {n: g for n, g in zones_utm.items() if not g.is_empty}
    check("zones.valid", all(g.is_valid for g in non_empty.values()), "Invalid influence zone geometry.")
    outside = sum(g.difference(ward_utm).area for g in non_empty.values())
    check("zones.withinWard", outside < 1e-3, "Influence zones extend outside Ward 176.", {"areaOutsideM2": outside})
    union_area = union_all(list(non_empty.values())).area
    total_area = sum(g.area for g in non_empty.values())
    check("zones.nonOverlapping", abs(total_area - union_area) < 1.0, "Influence zones overlap.", {"sumAreaM2": total_area, "unionAreaM2": union_area})
    check("zones.coverWard", abs(union_area - ward_area) / ward_area < 1e-6, "Influence zones do not partition the ward.", {"unionAreaM2": union_area, "wardAreaM2": ward_area})
    check("output.timestampsIncreasing", all(b > a for a, b in zip(times, times[1:])), "Output timestamps are not increasing.")

    report_flooding_ids = {r["id"] for r in report.node_flooding}
    sampled_flooding_ids = {junction_ids[j] for j in np.where(is_flooding.any(axis=0))[0]}
    check("crosscheck.floodingNodesSubsetOfReport", sampled_flooding_ids <= report_flooding_ids, "Output flooding nodes not listed in the SWMM report.", sorted(sampled_flooding_ids - report_flooding_ids))
    missed = sorted(report_flooding_ids - sampled_flooding_ids)
    check(
        "crosscheck.reportFloodingNodesSeenInSamples",
        not missed,
        "Some nodes flood only between reporting timestamps.",
        {"nodesFloodingOnlyBetweenReportTimes": missed},
        hard=False,
    )
    report_loss_m3 = report.routing_continuity["Flooding Loss"]["volumeMillionLiters"] * 1000.0
    approx_total_m3 = float(cumulative[-1].sum())
    rel_diff = (approx_total_m3 - report_loss_m3) / report_loss_m3 if report_loss_m3 else 0.0
    check(
        "crosscheck.cumulativeOverflowVsReport",
        abs(rel_diff) <= CUMULATIVE_VOLUME_TOLERANCE,
        "Approximate cumulative overflow differs from SWMM flooding loss beyond tolerance.",
        {"approxTotalM3": round(approx_total_m3, 1), "reportFloodingLossM3": round(report_loss_m3, 1), "relativeDifference": round(rel_diff, 4)},
    )
    report_surcharge_ids = {r["id"] for r in report.node_surcharge}
    sampled_surcharge_or_flood = {junction_ids[j] for j in np.where((is_flooding | is_surcharged).any(axis=0))[0]}
    check(
        "crosscheck.surchargeNodesVsReport",
        sampled_surcharge_or_flood <= report_surcharge_ids | report_flooding_ids,
        "Sampled surcharge detection disagrees with the SWMM Node Surcharge Summary.",
        {
            "sampledOnly": sorted(sampled_surcharge_or_flood - report_surcharge_ids - report_flooding_ids),
            "reportOnly": sorted((report_surcharge_ids | report_flooding_ids) - sampled_surcharge_or_flood),
        },
        hard=False,
    )

    # ---- products ----------------------------------------------------------------------
    legend = {
        "states": {
            STATE_FLOODING: "SWMM node flooding (overflow) rate > 0 m3/s at this timestamp.",
            STATE_SURCHARGED: "Node water depth above the crown of its highest connected conduit, without overflow.",
        },
        "overflowClasses": [
            {"class": "LOW", "minExclusiveCms": 0.0, "maxInclusiveCms": round(p50, 6)},
            {"class": "MODERATE", "minExclusiveCms": round(p50, 6), "maxInclusiveCms": round(p90, 6)},
            {"class": "HIGH", "minExclusiveCms": round(p90, 6), "maxInclusiveCms": round(event_max_rate, 6)},
        ],
        "classBasis": "50th/90th percentiles of all non-zero node flooding-rate samples in this simulation (visualisation classes, not hazard thresholds).",
        "quantity": "Simulated node overflow rate (m3/s)",
    }

    zone_features = []
    for n in node_ids:
        g = zones_utm[n]
        if g.is_empty:
            continue
        zone_features.append(
            {
                "type": "Feature",
                "id": f"zone:{n}",
                "geometry": _web_geometry(g),
                "properties": {"featureType": "influenceZone", "nodeId": n, "zoneAreaM2": round(zone_area[n], 1)},
            }
        )

    metadata = {
        "simulationId": simulation_id,
        "scenarioId": scenario_id,
        "modelVersion": model_version,
        "floodProcessingVersion": flood_processing_version,
        "dataType": "model-derived",
        "crs": "OGC:CRS84 (RFC 7946 longitude, latitude)",
        "processingCrs": UTM44N,
        "method": "docs/FLOOD_PROCESSING_METHOD.md",
        "representation": "Simulated node flooding/surcharge states with nearest-node flood influence zones (not flood extent, no ground depth).",
    }

    timeline_entries = []
    timeslices: dict[str, dict[str, Any]] = {}
    for p, t in enumerate(times):
        key = timestamp_key(t)
        features = []
        flooding_zone_area = 0.0
        node_summaries = []
        for j, n in enumerate(junction_ids):
            if not (is_flooding[p, j] or is_surcharged[p, j]):
                continue
            state = STATE_FLOODING if is_flooding[p, j] else STATE_SURCHARGED
            props = {
                "featureType": "node",
                "nodeId": n,
                "state": state,
                "overflowClass": overflow_class(flooding[p, j]) if state == STATE_FLOODING else None,
                "floodingRateCms": round(float(flooding[p, j]), 6),
                "approxCumulativeOverflowM3": round(float(cumulative[p, j]), 1),
                "nodeWaterDepthM": round(float(depth[p, j]), 4),
                "nodeHeadM": round(float(head[p, j]), 4),
                "fillRatio": round(float(depth[p, j] / effective_full[j]), 4) if effective_full[j] > 0 else None,
            }
            node_summaries.append(props)
            features.append({"type": "Feature", "id": f"node:{n}", "geometry": {"type": "Point", "coordinates": node_lonlat[n]}, "properties": props})
            if state == STATE_FLOODING and not zones_utm[n].is_empty:
                flooding_zone_area += zone_area[n]
                features.append(
                    {
                        "type": "Feature",
                        "id": f"zone:{n}",
                        "geometry": _web_geometry(zones_utm[n]),
                        "properties": {**props, "featureType": "influenceZone", "zoneAreaM2": round(zone_area[n], 1)},
                    }
                )
        n_flood = int(is_flooding[p].sum())
        n_sur = int(is_surcharged[p].sum())
        entry = {
            "index": p,
            "time": to_iso_z(t),
            "key": key,
            "hasFlooding": n_flood > 0,
            "floodingNodeCount": n_flood,
            "surchargedNodeCount": n_sur,
            "systemFloodingRateCms": round(float(system_flooding[p]), 6),
            "maxNodeFloodingRateCms": round(float(flooding[p].max()), 6) if n_flood else 0.0,
            "rainfallMmHr": round(float(rainfall[p]), 4),
            "floodingInfluenceZoneAreaM2": round(flooding_zone_area, 1),
            "approxCumulativeSystemOverflowM3": round(float(cumulative[p].sum()), 1),
        }
        timeline_entries.append(entry)
        timeslices[key] = {
            "type": "FeatureCollection",
            "metadata": {**metadata, "time": entry["time"], "index": p, "summary": {k: v for k, v in entry.items() if k not in ("index", "time", "key")}},
            "features": features,
        }

    all_features = [f for fc in timeslices.values() for f in fc["features"]] + zone_features
    if all_features:
        bbox = bbox_of(all_features)
        check("web.bboxWithinChennai", within_envelope(bbox), "Flood product coordinates outside the Chennai envelope (CRS error).", {"bbox": bbox})

    peak_index = int(np.argmax(system_flooding))
    concurrent = is_flooding.sum(axis=1)
    flooding_periods = np.where(concurrent > 0)[0]
    step_hours = output.report_step_seconds / 3600.0
    ever_flooded = sorted(sampled_flooding_ids)
    max_depth_j = int(np.argmax(depth.max(axis=0)))

    summary = {
        "available": True,
        "reportingPeriods": n_periods,
        "intervalMinutes": output.report_step_seconds // 60,
        "firstTime": to_iso_z(times[0]),
        "lastTime": to_iso_z(times[-1]),
        "peakTime": to_iso_z(times[peak_index]),
        "peakIndex": peak_index,
        "metrics": {
            "peakSystemFloodingRate": {"value": round(float(system_flooding[peak_index]), 6), "unit": "m3/s", "source": "model-derived", "time": to_iso_z(times[peak_index]), "description": "Peak total node overflow rate at a reporting timestamp."},
            "floodedNodesEvent": {"value": len(report_flooding_ids), "unit": "count", "source": "model-derived", "description": "Nodes listed in the SWMM Node Flooding Summary (routing-step resolution)."},
            "floodedNodesInReportingSamples": {"value": len(ever_flooded), "unit": "count", "source": "model-derived", "description": "Nodes with overflow at one or more 30-minute reporting timestamps."},
            "peakConcurrentFloodingNodes": {"value": int(concurrent.max()), "unit": "count", "source": "model-derived", "time": to_iso_z(times[int(np.argmax(concurrent))]), "description": "Largest number of nodes overflowing at one reporting timestamp."},
            "surchargedNodesEvent": {"value": len(report_surcharge_ids), "unit": "count", "source": "model-derived", "description": "Nodes listed in the SWMM Node Surcharge Summary."},
            "firstFloodingTime": {"value": to_iso_z(times[int(flooding_periods[0])]) if flooding_periods.size else None, "unit": "ISO 8601", "source": "model-derived", "description": "First reporting timestamp with any node overflow."},
            "floodingDuration": {"value": round(float(flooding_periods.size * step_hours), 2), "unit": "hr", "source": "model-derived", "description": "Reporting periods with at least one overflowing node × reporting step."},
            "maximumNodeWaterDepth": {"value": round(float(depth.max()), 3), "unit": "m", "source": "model-derived", "nodeId": junction_ids[max_depth_j], "description": "Maximum in-network node water depth (SWMM node depth). Not a ground flood depth."},
            "simulatedFloodingVolume": {"value": round(report_loss_m3 * 1000.0, 1), "unit": "L", "source": "model-derived", "description": "SWMM flooding loss under the current incomplete network representation; not observed flood volume."},
            "peakFloodingInfluenceZoneArea": {"value": timeline_entries[peak_index]["floodingInfluenceZoneAreaM2"], "unit": "m2", "source": "derived", "time": to_iso_z(times[peak_index]), "description": "Area of influence zones of nodes overflowing at the peak timestamp. Not a flooded area."},
        },
        "extentAvailable": False,
        "depthAvailable": False,
        "influenceZonesAvailable": True,
        "notDerived": {
            "groundFloodDepth": "SWMM ran with ALLOW_PONDING=NO, so overflow leaves the model and node depth is capped at the rim; no surface water depth exists in the output. Model rim elevations and the Copernicus DSM are not vertically consistent.",
            "floodExtent": "A 1D drainage model with sparse nodes does not define where surface water spreads; influence zones are associations, not extents.",
        },
    }

    diagnostics = {
        **metadata,
        "generatedAt": to_iso_z(generated_at),
        "checks": checks,
        "zoneStatistics": {
            "zones": len(non_empty),
            "emptyZones": sorted(n for n, g in zones_utm.items() if g.is_empty),
            "wardAreaM2": round(ward_area, 1),
            "zoneAreaM2": {
                "min": round(min(zone_area[n] for n in non_empty), 1),
                "median": round(float(np.median([zone_area[n] for n in non_empty])), 1),
                "max": round(max(zone_area[n] for n in non_empty), 1),
            },
        },
        "overflowRateDistribution": {"nonZeroSamples": int(nonzero.size), "p50Cms": round(p50, 6), "p90Cms": round(p90, 6), "maxCms": round(event_max_rate, 6)},
        "everFloodingNodesInSamples": ever_flooded,
    }

    manifest = {
        **metadata,
        "generatedAt": to_iso_z(generated_at),
        "reportingPeriods": n_periods,
        "legend": legend,
        "summary": summary,
        "products": {"timeline": "timeline.json", "zones": "zones.geojson", "timeslices": "timeslices/<key>.geojson", "diagnostics": "diagnostics.json"},
    }
    timeline = {
        **metadata,
        "intervalMinutes": output.report_step_seconds // 60,
        "timeConvention": "SWMM reporting timestamps (UTC). The first report time is one reporting step after the simulation start.",
        "peakIndex": peak_index,
        "legend": legend,
        "entries": timeline_entries,
    }
    zones_fc = {"type": "FeatureCollection", "metadata": {**metadata, "description": "Nearest-model-node (Voronoi) cells clipped to Ward 176; spatial association only."}, "features": zone_features}
    if not math.isfinite(approx_total_m3):
        raise FloodProcessingError("Non-finite cumulative overflow volume")
    return FloodProducts(manifest=manifest, timeline=timeline, zones=zones_fc, timeslices=timeslices, diagnostics=diagnostics)


def parse_time_query(value: str) -> datetime:
    """Parse an ISO 8601 timestamp; naive values are rejected (timestamps must be explicit)."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a UTC offset or Z")
    return parsed


__all__ = ["generate_flood_products", "compute_node_states", "NodeStates", "timestamp_key", "parse_time_query", "FloodProcessingError", "FloodProducts", "node_crown_heights"]
