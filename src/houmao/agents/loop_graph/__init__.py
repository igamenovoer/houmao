"""NetworkX-backed graph helpers for Houmao loop authoring tools."""

from __future__ import annotations

from houmao.agents.loop_graph.analysis import analyze_graph, slice_graph
from houmao.agents.loop_graph.io import (
    GraphInputError,
    graph_to_node_link_data,
    node_link_data_to_graph,
)
from houmao.agents.loop_graph.packets import (
    build_pairwise_v2_packet_expectations,
    validate_pairwise_v2_packets,
)

__all__ = [
    "GraphInputError",
    "analyze_graph",
    "build_pairwise_v2_packet_expectations",
    "graph_to_node_link_data",
    "node_link_data_to_graph",
    "slice_graph",
    "validate_pairwise_v2_packets",
]
