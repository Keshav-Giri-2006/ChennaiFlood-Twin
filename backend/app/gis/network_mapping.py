"""Traceability between SWMM model elements and GCC source drainage features.

Model link IDs and source ObjectIDs are different identifier spaces: one source
drain can become several model conduits, and some source drains are not in the
model at all. They are therefore always exposed as separate fields.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from app.simulation.inp_reader import InpModel

_NODE_NUMBER = re.compile(r"^(?:J|OUT)(\d+)$")


class NetworkMappingError(ValueError):
    pass


def node_number(model_node_id: str) -> int:
    m = _NODE_NUMBER.match(model_node_id)
    if not m:
        raise NetworkMappingError(f"Unrecognised model node ID format: {model_node_id}")
    return int(m.group(1))


@dataclass(frozen=True)
class NodeLocation:
    reconstructed_node: int
    easting_m: float
    northing_m: float
    component_id: int | None


@dataclass
class NetworkMapping:
    link_to_object_id: dict[str, int]
    object_id_to_links: dict[int, list[str]]
    link_component: dict[str, int | None]
    node_locations: dict[str, NodeLocation]
    crs: str = "EPSG:32644"


def load_network_mapping(inp: InpModel, conduits_csv: Path, nodes_csv: Path) -> NetworkMapping:
    with conduits_csv.open("r", encoding="utf-8", newline="") as handle:
        conduit_rows = {row["recon_conduit_id"]: row for row in csv.DictReader(handle)}
    with nodes_csv.open("r", encoding="utf-8", newline="") as handle:
        node_rows = {int(row["node_id"]): row for row in csv.DictReader(handle)}

    link_to_object: dict[str, int] = {}
    object_to_links: dict[int, list[str]] = {}
    link_component: dict[str, int | None] = {}
    problems: list[str] = []
    for link_id, conduit in inp.conduits.items():
        row = conduit_rows.get(link_id)
        if row is None:
            problems.append(f"{link_id}: not in reconstructed conduit table")
            continue
        expected = (int(row["from_node"]), int(row["to_node"]))
        actual = (node_number(str(conduit["fromNode"])), node_number(str(conduit["toNode"])))
        if expected != actual:
            problems.append(f"{link_id}: endpoints {actual} differ from reconstruction {expected}")
            continue
        object_id = int(row["objectid"])
        link_to_object[link_id] = object_id
        object_to_links.setdefault(object_id, []).append(link_id)
        comp = row.get("component_id_after") or row.get("component_id")
        link_component[link_id] = int(comp) if comp not in (None, "") else None

    locations: dict[str, NodeLocation] = {}
    for node_id in inp.node_ids:
        row = node_rows.get(node_number(node_id))
        if row is None:
            problems.append(f"{node_id}: no reconstructed node coordinates")
            continue
        comp = row.get("component_id")
        locations[node_id] = NodeLocation(
            reconstructed_node=int(row["node_id"]),
            easting_m=float(row["easting_m"]),
            northing_m=float(row["northing_m"]),
            component_id=int(comp) if comp not in (None, "") else None,
        )

    if problems:
        raise NetworkMappingError("Model/network mapping is inconsistent: " + "; ".join(problems[:10]))
    return NetworkMapping(link_to_object, object_to_links, link_component, locations)
