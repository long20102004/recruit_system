import networkx as nx
import pytest

from app.graph import graph_distance, graph_match_score


def test_graph_distance_and_match_score():
    graph = nx.Graph()
    graph.add_edges_from([("react", "frontend"), ("vue", "frontend")])

    assert graph_distance(graph, "react", "react") == 0
    assert graph_distance(graph, "react", "vue") == 2
    assert graph_match_score(graph, "react", "vue") == pytest.approx(1 / 3)
    assert graph_distance(graph, "react", "unknown") is None
