"""Input and output helpers for NetworkX node-link graph payloads."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import networkx as nx  # type: ignore[import-untyped]
from networkx.readwrite import json_graph  # type: ignore[import-untyped]


class GraphInputError(ValueError):
    """Raised when a graph payload is not accepted by the graph helper layer."""


def read_json_document(path: Path | None) -> object:
    """Read one JSON document from a path or standard input.

    Parameters
    ----------
    path
        Optional JSON path. ``None`` or ``-`` reads from standard input.

    Returns
    -------
    object
        Parsed JSON payload.
    """

    try:
        if path is None or str(path) == "-":
            return json.loads(sys.stdin.read())
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GraphInputError(f"Invalid JSON input: {exc}") from exc
    except OSError as exc:
        raise GraphInputError(f"Failed to read JSON input: {exc}") from exc


def read_graph_document(path: Path | None) -> nx.MultiDiGraph:
    """Read one NetworkX node-link JSON graph from a path or standard input."""

    return node_link_data_to_graph(read_json_document(path))


def node_link_data_to_graph(data: object) -> nx.MultiDiGraph:
    """Convert NetworkX node-link JSON data to a ``MultiDiGraph``.

    Parameters
    ----------
    data
        Parsed node-link JSON object.

    Returns
    -------
    networkx.MultiDiGraph
        Normalized directed multigraph.
    """

    if not isinstance(data, dict):
        raise GraphInputError("Graph input must be a JSON object.")
    if not isinstance(data.get("nodes"), list):
        raise GraphInputError("Graph input must include a `nodes` list.")
    if not isinstance(data.get("edges"), list):
        raise GraphInputError("Graph input must include an `edges` list.")
    if not isinstance(data.get("graph"), dict):
        raise GraphInputError("Graph input must include a `graph` object.")

    directed = bool(data.get("directed", True))
    multigraph = bool(data.get("multigraph", True))
    try:
        loaded = json_graph.node_link_graph(
            data,
            directed=directed,
            multigraph=multigraph,
            nodes="nodes",
            edges="edges",
        )
    except Exception as exc:
        raise GraphInputError(f"Invalid NetworkX node-link graph: {exc}") from exc

    if isinstance(loaded, nx.MultiDiGraph):
        return loaded
    if isinstance(loaded, nx.MultiGraph):
        normalized = nx.MultiDiGraph()
        normalized.add_nodes_from(loaded.nodes(data=True))
        normalized.add_edges_from(
            (u, v, key, attrs) for u, v, key, attrs in loaded.edges(keys=True, data=True)
        )
        normalized.graph.update(loaded.graph)
        return normalized
    normalized = nx.MultiDiGraph(loaded)
    normalized.graph.update(getattr(loaded, "graph", {}))
    return normalized


def graph_to_node_link_data(graph: nx.Graph) -> dict[str, Any]:
    """Return NetworkX node-link JSON data using the ``edges`` key."""

    data = json_graph.node_link_data(graph, nodes="nodes", edges="edges")
    if isinstance(data, dict):
        return data
    raise GraphInputError("NetworkX returned a non-object node-link payload.")


def json_object_from_document(path: Path | None) -> dict[str, Any]:
    """Read and validate one JSON object document."""

    payload = read_json_document(path)
    if not isinstance(payload, dict):
        raise GraphInputError("Expected a JSON object document.")
    return payload
