"""Mermaid graph scaffolding for Houmao loop graph authoring."""

from __future__ import annotations

import re

import networkx as nx  # type: ignore[import-untyped]


def render_mermaid(
    graph: nx.MultiDiGraph, *, root: str | None = None, mode: str | None = None
) -> str:
    """Render deterministic Mermaid scaffolding for one graph."""

    resolved_root = root or _optional_graph_attr(graph, "root")
    resolved_mode = mode or _optional_graph_attr(graph, "mode")
    lines = ["flowchart TD"]
    node_refs = {node: f"N{index}" for index, node in enumerate(sorted(graph.nodes, key=str))}
    for node in sorted(graph.nodes, key=str):
        attrs = graph.nodes[node]
        label = str(node)
        kind = attrs.get("kind")
        if kind is not None:
            label = f"{label}<br/>{kind}"
        if str(node) == resolved_root:
            label = f"{label}<br/>root"
        lines.append(f"    {node_refs[node]}[{_escape_label(label)}]")

    for source, target, key, attrs in graph.edges(keys=True, data=True):
        edge_id = attrs.get("id", attrs.get("edge_id", key))
        kind = attrs.get("kind", attrs.get("component_type", "edge"))
        label = _escape_label(f"{kind} {edge_id}")
        lines.append(f"    {node_refs[source]} -->|{label}| {node_refs[target]}")

    if resolved_mode is not None:
        lines.append(f"    %% mode: {_comment_text(resolved_mode)}")
    lines.append("    %% scaffold only: review loop semantics in the owning Houmao skill")
    return "\n".join(lines) + "\n"


def _optional_graph_attr(graph: nx.Graph, key: str) -> str | None:
    """Return one optional graph attribute as a string."""

    value = graph.graph.get(key)
    return str(value) if value is not None else None


def _escape_label(value: str) -> str:
    """Escape Mermaid label text while preserving simple line breaks."""

    return value.replace('"', "'").replace("|", "/")


def _comment_text(value: str) -> str:
    """Normalize Mermaid comment text."""

    return re.sub(r"[\r\n]+", " ", value)
