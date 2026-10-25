"""Knowledge graph helpers for skill matching."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import networkx as nx

from .normalize import _text

ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = ROOT / "data" / "skills_graph.json"


def load_skill_graph(path: Path | str = GRAPH_PATH) -> nx.Graph:
    with Path(path).open(encoding="utf-8") as handle:
        data = json.load(handle)

    graph = nx.Graph()
    for node in data.get("nodes", []):
        graph.add_node(node["id"], label=node.get("label", node["id"]))
    for edge in data.get("edges", []):
        graph.add_edge(edge["from"], edge["to"], relation=edge.get("relation", "related_to"))
    return graph


@lru_cache(maxsize=1)
def default_skill_graph() -> nx.Graph:
    return load_skill_graph()


@lru_cache(maxsize=1)
def skill_node_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for node_id, attributes in default_skill_graph().nodes(data=True):
        lookup[_text(node_id)] = node_id
        lookup[_text(attributes.get("label", node_id))] = node_id
    return lookup


def skill_to_node_id(skill: str) -> str | None:
    return skill_node_lookup().get(_text(skill))


def graph_distance(g: nx.Graph, skill_a_id: str, skill_b_id: str) -> int | None:
    if skill_a_id == skill_b_id:
        return 0
    try:
        return nx.shortest_path_length(g, skill_a_id, skill_b_id)
    except (nx.NodeNotFound, nx.NetworkXNoPath):
        return None


def graph_match_score(
    g: nx.Graph, skill_a_id: str, skill_b_id: str, max_distance: int = 3
) -> float:
    if max_distance <= 0:
        raise ValueError("max_distance must be positive")
    distance = graph_distance(g, skill_a_id, skill_b_id)
    if distance is None or distance >= max_distance:
        return 0.0
    return 1.0 - (distance / max_distance)
