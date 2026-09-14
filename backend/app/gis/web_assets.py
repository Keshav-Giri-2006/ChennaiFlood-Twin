"""Build and cache web-ready (RFC 7946, lon/lat) GeoJSON layers from project data.

Source files are only read. Built layers are written to ``WEB_ASSETS_DIR`` and
rebuilt automatically when a source file checksum or the GIS processing
version changes, so there is no manual pre-processing step.

Processing applied (``web-gis-v1``):
  * explicit CRS transformation to lon/lat (EPSG:32644 -> EPSG:4326, or CRS84 passthrough)
  * Z/M coordinates dropped, coordinates rounded to 7 decimals (~1 cm)
  * selected source attributes renamed to camelCase; source IDs preserved
  * geometry validity checked on the source geometry and reported (never "fixed")
  * no simplification, no feature removal, no geometry shifting
"""

from __future__ import annotations

import csv
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shapely.geometry import shape

from app.core.config import Settings
from app.gis.network_mapping import NetworkMapping, node_number
from app.gis.transform import CRS84, UTM44N, bbox_of, declared_crs, geometry_to_web, transform_xy, within_envelope
from app.simulation.inp_reader import InpModel
from app.utils.files import read_json, sha256_file, write_json_atomic
from app.utils.timeutil import to_iso_z, utcnow


class GisBuildError(RuntimeError):
    pass


def _num(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True)
class LayerSpec:
    name: str
    title: str
    data_type: str  # "source" | "model-representation" | "model-construct"
    source_files: tuple[str, ...]  # keys resolved by the builder
    description: str


LAYERS: dict[str, LayerSpec] = {
    "ward": LayerSpec("ward", "Ward 176 boundary", "source", ("processed:gis/ward176_boundary.geojson",), "GCC administrative ward boundary (processed extract)."),
    "buildings": LayerSpec("buildings", "Ward 176 buildings", "source", ("processed:gis/ward176_buildings.geojson",), "GCC building footprints clipped to Ward 176. No measured building heights are included."),
    "roads": LayerSpec("roads", "Ward 176 carriageways", "source", ("processed:gis/ward176_carriageways.geojson",), "GCC carriageway polygons clipped to Ward 176."),
    "drains": LayerSpec(
        "drains",
        "Ward 176 storm-water drains",
        "source",
        ("processed:gis/ward176_storm_water_drains.geojson", "mapping:conduitsCsv", "mapping:invertDecisionsCsv", "model:inp"),
        "GCC storm-water drain source features (135) with references to the SWMM model links that represent them and data-quality flags.",
    ),
    "subcatchments": LayerSpec(
        "subcatchments",
        "Ward 176 model subcatchments",
        "model-construct",
        ("processed:gis/ward176_subcatchments.geojson", "model:inp"),
        "First-pass GIS-derived SWMM subcatchments. Model constructs, not official hydrological catchments.",
    ),
    "model-conduits": LayerSpec(
        "model-conduits",
        "SWMM model conduits",
        "model-representation",
        ("gis:mapping:conduitGeometry", "mapping:conduitsCsv", "model:inp"),
        "Geometry of the 182 conduits in the current SWMM candidate model (reconstructed from GCC source drains).",
    ),
    "model-nodes": LayerSpec(
        "model-nodes",
        "SWMM model nodes",
        "model-representation",
        ("mapping:nodesCsv", "mapping:conduitsCsv", "model:inp"),
        "Reconstructed junction/outfall locations of the 228 nodes in the current SWMM candidate model. Outfalls are provisional boundary terminals.",
    ),
}


class WebAssetBuilder:
    def __init__(
        self,
        settings: Settings,
        *,
        model_inp_path: Path,
        model_version: str,
        network_mapping_files: dict[str, str],
        inp_loader: Callable[[], InpModel],
        mapping_loader: Callable[[], NetworkMapping],
    ) -> None:
        self.settings = settings
        self.root = settings.web_assets_root
        self.model_inp_path = model_inp_path
        self.model_version = model_version
        self.mapping_files = network_mapping_files
        self._inp_loader = inp_loader
        self._mapping_loader = mapping_loader
        self._locks: dict[str, threading.Lock] = {name: threading.Lock() for name in LAYERS}
        self._verified: dict[str, dict[str, Any]] = {}

    # -- source resolution --------------------------------------------------
    def resolve_source(self, key: str) -> Path:
        if key == "model:inp":
            return self.model_inp_path
        if key.startswith("processed:"):
            return self.settings.processed_dir / key.removeprefix("processed:")
        if key.startswith("gis:mapping:"):
            return self.settings.gis_source_dir / self.mapping_files[key.removeprefix("gis:mapping:")]
        if key.startswith("mapping:"):
            return self.settings.processed_dir / self.mapping_files[key.removeprefix("mapping:")]
        raise GisBuildError(f"Unknown source key {key}")

    def source_paths(self, layer: str) -> list[Path]:
        return [self.resolve_source(k) for k in LAYERS[layer].source_files]

    # -- public API -----------------------------------------------------------
    def get(self, layer: str) -> tuple[Path, dict[str, Any]]:
        """Return the built asset path and its manifest entry, building if needed."""
        if layer not in LAYERS:
            raise KeyError(layer)
        with self._locks[layer]:
            if layer in self._verified:
                return self.root / f"{layer}.geojson", self._verified[layer]
            asset = self.root / f"{layer}.geojson"
            manifest_path = self.root / f"{layer}.manifest.json"
            sources = self.source_paths(layer)
            missing = [p.name for p in sources if not p.is_file()]
            if missing:
                raise GisBuildError(f"Source data for layer '{layer}' is missing: {missing}")
            checksums = {p.name: sha256_file(p) for p in sources}
            if asset.is_file() and manifest_path.is_file():
                manifest = read_json(manifest_path)
                if manifest.get("sourceChecksums") == checksums and manifest.get("processingVersion") == self.settings.gis_processing_version:
                    self._verified[layer] = manifest
                    return asset, manifest
            manifest = self._build(layer, asset, checksums)
            write_json_atomic(manifest_path, manifest)
            self._verified[layer] = manifest
            return asset, manifest

    # -- builders -------------------------------------------------------------
    def _build(self, layer: str, asset: Path, checksums: dict[str, str]) -> dict[str, Any]:
        builder = getattr(self, f"_build_{layer.replace('-', '_')}")
        features, extra_meta, source_crs, invalid = builder()
        if not features:
            raise GisBuildError(f"Layer '{layer}' produced no features")
        bbox = bbox_of(features)
        if not within_envelope(bbox):
            raise GisBuildError(f"Layer '{layer}' coordinates fall outside the Chennai envelope; CRS handling is wrong")
        spec = LAYERS[layer]
        metadata = {
            "layer": layer,
            "title": spec.title,
            "description": spec.description,
            "dataType": spec.data_type,
            "studyArea": "Ward 176, Velachery, Chennai",
            "crs": "OGC:CRS84 (RFC 7946 longitude, latitude)",
            "sourceCrs": source_crs,
            "processingVersion": self.settings.gis_processing_version,
            "processing": "CRS transformation to lon/lat, Z dropped, coordinates rounded to 7 decimals; no simplification.",
            "featureCount": len(features),
            "invalidSourceGeometryCount": invalid,
            "bbox": [round(v, 7) for v in bbox],
            "builtAt": to_iso_z(utcnow()),
            **extra_meta,
        }
        write_json_atomic(asset, {"type": "FeatureCollection", "metadata": metadata, "features": features})
        return {
            "layer": layer,
            "processingVersion": self.settings.gis_processing_version,
            "sourceChecksums": checksums,
            "assetSha256": sha256_file(asset),
            "metadata": metadata,
        }

    def _load_source(self, relative_key: str) -> tuple[dict[str, Any], str]:
        collection = read_json(self.resolve_source(relative_key))
        return collection, declared_crs(collection)

    @staticmethod
    def _invalid_count(features: list[dict[str, Any]]) -> int:
        return sum(1 for f in features if f.get("geometry") is None or not shape(f["geometry"]).is_valid)

    def _simple_layer(self, key: str, props: Callable[[dict[str, Any]], dict[str, Any]], id_field: str) -> tuple[list[dict[str, Any]], dict[str, Any], str, int]:
        collection, crs = self._load_source(key)
        source_features = collection["features"]
        invalid = self._invalid_count(source_features)
        features = []
        for f in source_features:
            if f.get("geometry") is None:
                raise GisBuildError(f"Null geometry in {key}")
            p = f["properties"]
            features.append({"type": "Feature", "id": p[id_field], "geometry": geometry_to_web(f["geometry"], crs), "properties": props(p)})
        return features, {"sourceFeatureCount": len(source_features)}, crs, invalid

    def _build_ward(self):  # type: ignore[no-untyped-def]
        return self._simple_layer(
            "processed:gis/ward176_boundary.geojson",
            lambda p: {"objectId": p["objectid"], "ward": _text(p.get("ward")), "sourceAreaM2": _num(p.get("st_area(shape)"))},
            "objectid",
        )

    def _build_buildings(self):  # type: ignore[no-untyped-def]
        return self._simple_layer(
            "processed:gis/ward176_buildings.geojson",
            lambda p: {
                "objectId": p["objectid"],
                "gccGisId": _text(p.get("gcc_gis_id")),
                "roadId": _text(p.get("road_id")),
                "locality": _text(p.get("locality")),
                "areaName": _text(p.get("area_name")),
                "sourceFootprintAreaM2": _num(p.get("st_area(shape)")),
            },
            "objectid",
        )

    def _build_roads(self):  # type: ignore[no-untyped-def]
        return self._simple_layer(
            "processed:gis/ward176_carriageways.geojson",
            lambda p: {
                "objectId": p["objectid"],
                "roadId": _text(p.get("road_id")),
                "roadName": _text(p.get("road_name")),
                "roadCategory": _text(p.get("interior_brr")),
                "locality": _text(p.get("locality")),
                "areaName": _text(p.get("area_name")),
                "sourceAreaM2": _num(p.get("st_area(shape)")),
            },
            "objectid",
        )

    def _build_drains(self):  # type: ignore[no-untyped-def]
        mapping = self._mapping_loader()
        decisions: dict[int, dict[str, str]] = {}
        with self.resolve_source("mapping:invertDecisionsCsv").open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                decisions[int(row["objectid"])] = row

        def props(p: dict[str, Any]) -> dict[str, Any]:
            oid = int(p["objectid"])
            decision = decisions.get(oid)
            quality = []
            if decision and decision["validation_status"] != "VALID":
                quality.append({"flag": decision["validation_status"], "decision": decision["decision"], "note": decision["decision_note"]})
            links = sorted(mapping.object_id_to_links.get(oid, []))
            return {
                "objectId": oid,
                "zone": _text(p.get("zone")),
                "ward": _text(p.get("ward")),
                "location": _text(p.get("location")),
                "drainType": _text(p.get("drain_type")),
                "lengthM": _num(p.get("drain_len")),
                "widthM": _num(p.get("drain_wid")),
                "depthM": _num(p.get("drain_dep")),
                "sizeLabel": _text(p.get("drain_size")),
                "status": _text(p.get("status")),
                "material": _text(p.get("swd_mat")),
                "cover": _text(p.get("cover")),
                "drainDetail": _text(p.get("drain_detl")),
                "waterFlow": _text(p.get("water_flow")),
                "puccaKacha": _text(p.get("puca_kacha")),
                "sourceInvertStartM": _num(p.get("invert_sp")),
                "sourceInvertEndM": _num(p.get("invert_ep")),
                "obstacles": _text(p.get("obstacles")),
                "modelLinkIds": links,
                "inHydraulicModel": bool(links),
                "dataQuality": quality,
            }

        features, meta, crs, invalid = self._simple_layer("processed:gis/ward176_storm_water_drains.geojson", props, "objectid")
        meta.update(
            {
                "modelVersion": self.model_version,
                "identifierNote": "objectId is the GCC source feature ID. modelLinkIds are SWMM conduit IDs; one source drain may map to several model links.",
                "sourceInvertNote": "Invert values are GCC source attributes as supplied; flagged records are not corrected.",
            }
        )
        return features, meta, crs, invalid

    def _build_subcatchments(self):  # type: ignore[no-untyped-def]
        inp = self._inp_loader()

        def props(p: dict[str, Any]) -> dict[str, Any]:
            sc_id = p["subcatchment_id"]
            model_sc = inp.subcatchments.get(sc_id)
            return {
                "subcatchmentId": sc_id,
                "areaM2": _num(p.get("area_m2")),
                "imperviousPercent": _num(p.get("impervious_percent")),
                "slopePercentProxy": _num(p.get("slope_percent_proxy")),
                "widthM": _num(p.get("width_m")),
                "demMeanM": _num(p.get("dem_mean_m")),
                "buildingAreaM2": _num(p.get("building_area_m2")),
                "roadAreaM2": _num(p.get("road_area_m2")),
                "modelOutletNodeId": model_sc["outlet"] if model_sc else None,
                "inHydraulicModel": model_sc is not None,
                "outletAssignment": _text(p.get("outlet_assignment_method")),
                "parameterSource": _text(p.get("parameter_source")),
                "geometryQuality": _text(p.get("geometry_quality")),
            }

        features, meta, crs, invalid = self._simple_layer("processed:gis/ward176_subcatchments.geojson", props, "subcatchment_id")
        missing = sorted(set(inp.subcatchments) - {f["id"] for f in features})
        if missing:
            raise GisBuildError(f"Model subcatchments without geometry: {missing}")
        meta.update({"modelVersion": self.model_version, "note": "Imperviousness estimated from building and road overlays; parameters are modelling assumptions."})
        return features, meta, crs, invalid

    def _build_model_conduits(self):  # type: ignore[no-untyped-def]
        inp = self._inp_loader()
        mapping = self._mapping_loader()
        collection, crs = self._load_source("gis:mapping:conduitGeometry")
        by_id = {f["properties"]["recon_conduit_id"]: f for f in collection["features"]}
        missing = [lid for lid in inp.link_ids if lid not in by_id]
        if missing:
            raise GisBuildError(f"Model conduits without geometry: {missing}")
        source = [by_id[lid] for lid in inp.link_ids]
        invalid = self._invalid_count(source)
        features = []
        for lid in inp.link_ids:
            f = by_id[lid]
            p = f["properties"]
            if int(p["objectid"]) != mapping.link_to_object_id[lid]:
                raise GisBuildError(f"Conduit {lid} geometry ObjectID disagrees with the network mapping")
            c = inp.conduits[lid]
            features.append(
                {
                    "type": "Feature",
                    "id": lid,
                    "geometry": geometry_to_web(f["geometry"], crs),
                    "properties": {
                        "modelLinkId": lid,
                        "sourceObjectId": mapping.link_to_object_id[lid],
                        "fromNodeId": c["fromNode"],
                        "toNodeId": c["toNode"],
                        "modelLengthM": c["lengthM"],
                        "widthM": _num(p.get("width_m")),
                        "depthM": _num(p.get("depth_m")),
                        "networkComponentId": mapping.link_component.get(lid),
                    },
                }
            )
        return features, {"modelVersion": self.model_version, "sourceFeatureCount": len(collection["features"])}, crs, invalid

    def _build_model_nodes(self):  # type: ignore[no-untyped-def]
        inp = self._inp_loader()
        mapping = self._mapping_loader()
        ids = inp.node_ids
        xs = [mapping.node_locations[n].easting_m for n in ids]
        ys = [mapping.node_locations[n].northing_m for n in ids]
        lons, lats = transform_xy(UTM44N, xs, ys)
        features = []
        for node_id, lon, lat in zip(ids, lons, lats, strict=True):
            is_outfall = node_id in inp.outfalls
            elements = inp.outfalls[node_id] if is_outfall else inp.junctions[node_id]
            loc = mapping.node_locations[node_id]
            features.append(
                {
                    "type": "Feature",
                    "id": node_id,
                    "geometry": {"type": "Point", "coordinates": [round(lon, 7), round(lat, 7)]},
                    "properties": {
                        "modelNodeId": node_id,
                        "nodeType": "OUTFALL" if is_outfall else "JUNCTION",
                        "provisionalOutfall": is_outfall,
                        "invertElevationM": elements["invertElevM"],
                        "maxDepthM": None if is_outfall else elements["maxDepthM"],
                        "reconstructedNodeId": loc.reconstructed_node,
                        "networkComponentId": loc.component_id,
                    },
                }
            )
            assert node_number(node_id) == loc.reconstructed_node
        meta = {
            "modelVersion": self.model_version,
            "note": "Outfall nodes are provisional downstream boundary terminals, not confirmed physical outfalls. Elevations are model values.",
        }
        return features, meta, UTM44N, 0


__all__ = ["LAYERS", "WebAssetBuilder", "GisBuildError", "CRS84"]
