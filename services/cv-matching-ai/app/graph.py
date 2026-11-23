"""Knowledge graph helpers for skill matching."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import networkx as nx

from .normalize import _text

ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = ROOT / "data" / "skills_graph.json"
KB_GRAPH_PATH = ROOT / "data" / "kb_skill_graph.json"
_RELATION_RANK = {"REQUIRES": 4, "PART_OF": 3, "IS_A": 2, "RELATED_TO": 1, "related_to": 1, "is_a": 2}
_BROAD_TYPES = {
    "frontend framework",
    "backend framework",
    "web framework",
    "api",
    "database",
    "cloud computing",
    "data science",
    "shell scripting",
}


def graph_key(text: str) -> str:
    """Same key as the interview skill graph and the extraction exporter."""
    value = unicodedata.normalize("NFD", text or "")
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d").replace("Đ", "d").lower()
    return re.sub(r"[^a-z0-9]", "", value)


def load_skill_graph(path: Path | str = GRAPH_PATH) -> nx.Graph:
    with Path(path).open(encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("nodes") and "name" in data["nodes"][0]:
        return _load_kb_graph(data)
    graph = nx.Graph()
    for node in data.get("nodes", []):
        graph.add_node(node["id"], label=node.get("label", node["id"]))
    for edge in data.get("edges", []):
        graph.add_edge(edge["from"], edge["to"], relation=edge.get("relation", "related_to"))
    return graph


def _load_kb_graph(data: dict) -> nx.Graph:
    graph = nx.Graph()
    aliases = data.get("aliases") or {}
    if isinstance(aliases, dict):
        graph.graph["aliases"] = {graph_key(key): value for key, value in aliases.items()}
    else:
        graph.graph["aliases"] = {item["from"]: item["to"] for item in aliases if item.get("from") and item.get("to")}
    graph.graph["job_skills"] = data.get("job_skills") or {}
    for node in data.get("nodes", []):
        graph.add_node(node["id"], label=node.get("name") or node["id"], category=node.get("category", ""))
    for edge in data.get("edges", []):
        left, right = edge.get("from"), edge.get("to")
        if left not in graph or right not in graph or left == right:
            continue
        relation = edge.get("rel") or edge.get("relation") or "RELATED_TO"
        if graph.has_edge(left, right) and _RELATION_RANK.get(graph.edges[left, right]["relation"], 0) >= _RELATION_RANK.get(relation, 0):
            continue
        graph.add_edge(left, right, relation=relation)
    return graph


@lru_cache(maxsize=1)
def default_skill_graph() -> nx.Graph:
    if KB_GRAPH_PATH.exists():
        return load_skill_graph(KB_GRAPH_PATH)
    return load_skill_graph()


@lru_cache(maxsize=1)
def skill_node_lookup() -> dict[str, str]:
    graph = default_skill_graph()
    lookup = dict(graph.graph.get("aliases") or {})
    for node_id, attributes in graph.nodes(data=True):
        lookup[graph_key(node_id)] = node_id
        lookup[graph_key(attributes.get("label", node_id))] = node_id
    return lookup


def skill_to_node_id(skill: str) -> str | None:
    return skill_node_lookup().get(graph_key(skill))


def direct_relation(graph: nx.Graph, left: str, right: str) -> str | None:
    if graph.has_edge(left, right):
        return graph.edges[left, right].get("relation")
    return None


def skills_for_title(title: str) -> list[str]:
    """Skills named by a job title. Family nodes such as API are not added."""
    graph = default_skill_graph()
    folded = _text(title)
    exact = (graph.graph.get("job_skills") or {}).get(folded)
    if exact:
        return [name for name in exact if _text(name) not in _BROAD_TYPES]
    found: list[str] = []
    seen: set[str] = set()
    for _node_id, attributes in graph.nodes(data=True):
        name = str(attributes.get("label") or "")
        needle = _text(name)
        if not name or needle in _BROAD_TYPES or attributes.get("category") == "Soft Skill" or len(needle) < 3:
            continue
        if needle not in seen and re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", folded):
            seen.add(needle)
            found.append(name)
    return found


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
