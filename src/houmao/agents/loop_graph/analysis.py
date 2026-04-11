"""Structural analysis and transformation helpers for loop graphs."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import networkx as nx  # type: ignore[import-untyped]

from houmao.agents.loop_graph.models import AlgorithmResult, GraphAnalysisResult, GraphSummary

_DEFAULT_CYCLE_LIMIT = 20
_DEFAULT_PATH_LIMIT = 50


def summarize_graph(graph: nx.Graph) -> GraphSummary:
    """Build a compact summary for one graph."""

    return GraphSummary(
        node_count=graph.number_of_nodes(),
        edge_count=graph.number_of_edges(),
        directed=graph.is_directed(),
        multigraph=graph.is_multigraph(),
        metadata=dict(graph.graph),
    )


def analyze_graph(
    graph: nx.MultiDiGraph,
    *,
    root: str | None = None,
    mode: str | None = None,
    cycle_limit: int = _DEFAULT_CYCLE_LIMIT,
) -> GraphAnalysisResult:
    """Analyze one Houmao graph for loop-authoring structural facts."""

    resolved_root = root or _optional_graph_attr(graph, "root")
    resolved_mode = mode or _optional_graph_attr(graph, "mode")
    warnings: list[str] = []
    errors: list[str] = []

    if resolved_root is not None and resolved_root not in graph:
        errors.append(f"Root `{resolved_root}` is not present in the graph.")

    reachable_nodes: list[str] = []
    disconnected_nodes: list[str] = []
    if resolved_root is not None and resolved_root in graph:
        reachable = {resolved_root, *nx.descendants(graph, resolved_root)}
        reachable_nodes = _sorted_strings(reachable)
        disconnected_nodes = _sorted_strings(set(graph.nodes) - reachable)
        if disconnected_nodes:
            warnings.append("Some graph nodes are not reachable from the configured root.")

    immediate_children = {
        str(node): _sorted_strings(graph.successors(node)) for node in _sorted_nodes(graph.nodes)
    }
    leaf_nodes = _sorted_strings(node for node in graph.nodes if graph.out_degree(node) == 0)
    non_leaf_nodes = _sorted_strings(node for node in graph.nodes if graph.out_degree(node) > 0)
    branch_points = _sorted_strings(node for node in graph.nodes if graph.out_degree(node) > 1)
    collapsed = collapse_to_digraph(graph)
    is_dag = nx.is_directed_acyclic_graph(collapsed)
    topological_order: list[str] | None = None
    cycles: list[list[str]] = []
    if is_dag:
        topological_order = _sorted_topological(collapsed)
    else:
        warnings.append("Graph contains at least one directed cycle.")
        cycles = _limited_cycles(collapsed, limit=cycle_limit)

    dependency_edges = _dependency_edges(graph)
    component_dependency_order = _component_dependency_order(dependency_edges)
    if dependency_edges and component_dependency_order is None:
        warnings.append("Component dependency edges contain a cycle.")

    return GraphAnalysisResult(
        graph=summarize_graph(graph),
        root=resolved_root,
        mode=resolved_mode,
        reachable_nodes=reachable_nodes,
        disconnected_nodes=disconnected_nodes,
        leaf_nodes=leaf_nodes,
        non_leaf_nodes=non_leaf_nodes,
        immediate_children=immediate_children,
        branch_points=branch_points,
        is_dag=is_dag,
        topological_order=topological_order,
        cycles=cycles,
        weak_components=[
            _sorted_strings(component) for component in nx.weakly_connected_components(graph)
        ],
        strong_components=[
            _sorted_strings(component) for component in nx.strongly_connected_components(graph)
        ],
        dependency_edges=dependency_edges,
        component_dependency_order=component_dependency_order,
        warnings=warnings,
        errors=errors,
    )


def slice_graph(
    graph: nx.MultiDiGraph,
    *,
    root: str,
    direction: str,
    component_id: str | None = None,
) -> nx.MultiDiGraph:
    """Return a selected authoring-time graph slice."""

    if direction == "component":
        if component_id is None:
            raise ValueError("`component_id` is required for component slices.")
        return _component_slice(graph, component_id=component_id)
    if root not in graph:
        raise ValueError(f"Root `{root}` is not present in the graph.")
    if direction == "ancestors":
        nodes = {root, *nx.ancestors(graph, root)}
    elif direction == "descendants":
        nodes = {root, *nx.descendants(graph, root)}
    elif direction == "reachable":
        nodes = {root, *nx.descendants(graph, root)}
    else:
        raise ValueError(f"Unsupported slice direction `{direction}`.")
    sliced = graph.subgraph(nodes).copy()
    sliced.graph.update(graph.graph)
    sliced.graph["slice_direction"] = direction
    sliced.graph["slice_root"] = root
    return nx.MultiDiGraph(sliced)


def create_empty_graph(graph_type: str) -> nx.Graph:
    """Create one supported empty NetworkX graph."""

    normalized = graph_type.strip().lower()
    if normalized == "multidigraph":
        return nx.MultiDiGraph()
    if normalized == "digraph":
        return nx.DiGraph()
    if normalized == "multigraph":
        return nx.MultiGraph()
    if normalized == "graph":
        return nx.Graph()
    raise ValueError(f"Unsupported graph type `{graph_type}`.")


def apply_mutation_ops(graph: nx.MultiDiGraph, ops_payload: object) -> nx.MultiDiGraph:
    """Apply a constrained batch of graph mutation operations."""

    operations = _coerce_operations(ops_payload)
    mutated = graph.copy()
    for operation in operations:
        op = str(operation.get("op", "")).strip()
        attrs = _coerce_attrs(operation.get("attrs"))
        if op == "add_node":
            node = _required(operation, "node")
            mutated.add_node(node, **attrs)
        elif op == "add_edge":
            source = _required(operation, "source")
            target = _required(operation, "target")
            key = operation.get("key")
            if key is None:
                mutated.add_edge(source, target, **attrs)
            else:
                mutated.add_edge(source, target, key=key, **attrs)
        elif op == "remove_node":
            mutated.remove_node(_required(operation, "node"))
        elif op == "remove_edge":
            source = _required(operation, "source")
            target = _required(operation, "target")
            key = operation.get("key")
            if key is None:
                mutated.remove_edge(source, target)
            else:
                mutated.remove_edge(source, target, key=key)
        elif op == "set_graph_attr":
            if "attrs" in operation:
                mutated.graph.update(attrs)
            else:
                key = str(_required(operation, "key"))
                mutated.graph[key] = operation.get("value")
        else:
            raise ValueError(f"Unsupported graph mutation op `{op}`.")
    return nx.MultiDiGraph(mutated)


def relabel_graph(graph: nx.MultiDiGraph, mapping_payload: object) -> nx.MultiDiGraph:
    """Relabel nodes with a JSON mapping payload."""

    if not isinstance(mapping_payload, dict):
        raise ValueError("Relabel mapping must be a JSON object.")
    return nx.MultiDiGraph(nx.relabel_nodes(graph, mapping_payload, copy=True))


def compose_graphs(left: nx.MultiDiGraph, right: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Compose two graphs with NetworkX compose semantics."""

    return nx.MultiDiGraph(nx.compose(left, right))


def node_subgraph(graph: nx.MultiDiGraph, nodes_payload: object) -> nx.MultiDiGraph:
    """Return a node-induced subgraph from a JSON node list payload."""

    nodes = _coerce_node_list(nodes_payload)
    sliced = graph.subgraph(nodes).copy()
    sliced.graph.update(graph.graph)
    return nx.MultiDiGraph(sliced)


def reverse_graph(graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Return a directed graph with all edges reversed."""

    return nx.MultiDiGraph(graph.reverse(copy=True))


def ego_graph(
    graph: nx.MultiDiGraph,
    *,
    node: str,
    radius: int,
    undirected: bool = False,
) -> nx.MultiDiGraph:
    """Return a NetworkX ego graph around one node."""

    if node not in graph:
        raise ValueError(f"Node `{node}` is not present in the graph.")
    return nx.MultiDiGraph(nx.ego_graph(graph, node, radius=radius, undirected=undirected))


def run_low_algorithm(
    graph: nx.MultiDiGraph,
    *,
    algorithm: str,
    node: str | None = None,
    source: str | None = None,
    target: str | None = None,
    distance: int | None = None,
    cutoff: int | None = None,
    length_bound: int | None = None,
    limit: int = _DEFAULT_PATH_LIMIT,
) -> AlgorithmResult:
    """Run one whitelisted low-level graph algorithm."""

    collapsed = collapse_to_digraph(graph)
    warnings: list[str] = []
    bound: int | None = None
    if graph.is_multigraph():
        warnings.append("Algorithm executed on a simple directed projection of the multigraph.")

    if algorithm == "ancestors":
        resolved_node = _require_node_arg(node=node, graph=collapsed)
        result: Any = _sorted_strings(nx.ancestors(collapsed, resolved_node))
    elif algorithm == "descendants":
        resolved_node = _require_node_arg(node=node, graph=collapsed)
        result = _sorted_strings(nx.descendants(collapsed, resolved_node))
    elif algorithm == "descendants-at-distance":
        resolved_node = _require_node_arg(node=node, graph=collapsed)
        if distance is None:
            raise ValueError("`distance` is required for descendants-at-distance.")
        result = _sorted_strings(nx.descendants_at_distance(collapsed, resolved_node, distance))
    elif algorithm == "topological-sort":
        result = _sorted_topological(collapsed)
    elif algorithm == "is-dag":
        result = nx.is_directed_acyclic_graph(collapsed)
    elif algorithm == "cycles":
        bound = length_bound if length_bound is not None else 8
        result = _limited_cycles(collapsed, limit=limit, length_bound=bound)
    elif algorithm == "weak-components":
        result = [
            _sorted_strings(component) for component in nx.weakly_connected_components(collapsed)
        ]
    elif algorithm == "strong-components":
        result = [
            _sorted_strings(component) for component in nx.strongly_connected_components(collapsed)
        ]
    elif algorithm == "condensation":
        condensed = nx.condensation(collapsed)
        result = {
            "graph": _graph_to_serializable_adjacency(condensed),
            "mapping": {str(k): v for k, v in condensed.graph.get("mapping", {}).items()},
        }
    elif algorithm == "transitive-reduction":
        if not nx.is_directed_acyclic_graph(collapsed):
            raise ValueError("transitive-reduction requires a directed acyclic graph.")
        result = _graph_to_serializable_adjacency(nx.transitive_reduction(collapsed))
    elif algorithm == "dag-longest-path":
        if not nx.is_directed_acyclic_graph(collapsed):
            raise ValueError("dag-longest-path requires a directed acyclic graph.")
        result = _string_list(nx.dag_longest_path(collapsed))
    elif algorithm == "shortest-path":
        if source is None or target is None:
            raise ValueError("`source` and `target` are required for shortest-path.")
        result = _string_list(nx.shortest_path(collapsed, source=source, target=target))
    elif algorithm == "all-simple-paths":
        if source is None or target is None:
            raise ValueError("`source` and `target` are required for all-simple-paths.")
        bound = cutoff if cutoff is not None else 8
        paths = nx.all_simple_paths(collapsed, source=source, target=target, cutoff=bound)
        result = [_string_list(path) for _, path in zip(range(limit), paths)]
    else:
        raise ValueError(f"Unsupported low-level algorithm `{algorithm}`.")

    return AlgorithmResult(
        operation=f"low.alg.{algorithm}",
        result=result,
        bound=bound,
        warnings=warnings,
    )


def collapse_to_digraph(graph: nx.Graph) -> nx.DiGraph:
    """Collapse any graph into one simple directed graph for algorithms."""

    collapsed = nx.DiGraph()
    collapsed.add_nodes_from(graph.nodes(data=True))
    if graph.is_multigraph():
        collapsed.add_edges_from((u, v) for u, v, _key in graph.edges(keys=True))
    else:
        collapsed.add_edges_from((u, v) for u, v in graph.edges())
    collapsed.graph.update(graph.graph)
    return collapsed


def _optional_graph_attr(graph: nx.Graph, key: str) -> str | None:
    """Return one optional graph attribute as a string."""

    value = graph.graph.get(key)
    return str(value) if value is not None else None


def _sorted_nodes(nodes: Iterable[object]) -> list[object]:
    """Return nodes in deterministic string order."""

    return sorted(nodes, key=str)


def _sorted_strings(values: Iterable[object]) -> list[str]:
    """Return values as sorted strings."""

    return [str(value) for value in sorted(values, key=str)]


def _string_list(values: Iterable[object]) -> list[str]:
    """Return values as strings while preserving iterable order."""

    return [str(value) for value in values]


def _sorted_topological(graph: nx.DiGraph) -> list[str]:
    """Return a deterministic topological order."""

    return [str(node) for node in nx.lexicographical_topological_sort(graph, key=str)]


def _limited_cycles(
    graph: nx.DiGraph,
    *,
    limit: int,
    length_bound: int | None = None,
) -> list[list[str]]:
    """Return a bounded list of simple cycles."""

    cycles = nx.simple_cycles(graph, length_bound=length_bound)
    return [_string_list(cycle) for _, cycle in zip(range(limit), cycles)]


def _dependency_edges(graph: nx.MultiDiGraph) -> list[dict[str, Any]]:
    """Extract component dependency edges from graph attributes."""

    edges: list[dict[str, Any]] = []
    for source, target, key, data in graph.edges(keys=True, data=True):
        kind = str(data.get("kind", data.get("edge_type", ""))).lower()
        if bool(data.get("dependency")) or "dependency" in kind:
            edge_id = data.get("id", data.get("edge_id", key))
            source_component = data.get("source_component", data.get("from_component", source))
            target_component = data.get("target_component", data.get("to_component", target))
            edges.append(
                {
                    "source": str(source),
                    "target": str(target),
                    "key": str(key),
                    "edge_id": str(edge_id),
                    "source_component": str(source_component),
                    "target_component": str(target_component),
                }
            )
    return edges


def _component_dependency_order(edges: list[dict[str, Any]]) -> list[str] | None:
    """Return component dependency order when dependency edges form a DAG."""

    if not edges:
        return None
    dependency_graph = nx.DiGraph()
    for edge in edges:
        dependency_graph.add_edge(edge["source_component"], edge["target_component"])
    if not nx.is_directed_acyclic_graph(dependency_graph):
        return None
    return _sorted_topological(dependency_graph)


def _component_slice(graph: nx.MultiDiGraph, *, component_id: str) -> nx.MultiDiGraph:
    """Return a slice containing edges for one component id."""

    sliced = nx.MultiDiGraph()
    sliced.graph.update(graph.graph)
    sliced.graph["slice_direction"] = "component"
    sliced.graph["component_id"] = component_id
    for source, target, key, data in graph.edges(keys=True, data=True):
        if str(data.get("component_id", "")) != component_id:
            continue
        sliced.add_node(source, **dict(graph.nodes[source]))
        sliced.add_node(target, **dict(graph.nodes[target]))
        sliced.add_edge(source, target, key=key, **dict(data))
    return sliced


def _coerce_operations(payload: object) -> list[dict[str, Any]]:
    """Normalize a mutation operation payload."""

    if isinstance(payload, dict):
        operations = payload.get("ops")
    else:
        operations = payload
    if not isinstance(operations, list):
        raise ValueError("Mutation operations must be a list or an object with an `ops` list.")
    normalized: list[dict[str, Any]] = []
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("Each mutation operation must be a JSON object.")
        normalized.append(operation)
    return normalized


def _coerce_attrs(payload: object) -> dict[str, Any]:
    """Normalize optional attribute payloads."""

    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError("Operation `attrs` must be a JSON object.")
    return dict(payload)


def _required(mapping: dict[str, Any], key: str) -> object:
    """Return one required mapping value."""

    if key not in mapping:
        raise ValueError(f"Operation is missing required `{key}`.")
    return mapping[key]


def _coerce_node_list(payload: object) -> list[object]:
    """Normalize a node list payload."""

    if isinstance(payload, dict):
        nodes = payload.get("nodes")
    else:
        nodes = payload
    if not isinstance(nodes, list):
        raise ValueError("Node selection must be a list or an object with a `nodes` list.")
    return list(nodes)


def _require_node_arg(*, node: str | None, graph: nx.DiGraph) -> str:
    """Validate and return one node argument."""

    if node is None:
        raise ValueError("`node` is required for this algorithm.")
    if node not in graph:
        raise ValueError(f"Node `{node}` is not present in the graph.")
    return node


def _graph_to_serializable_adjacency(graph: nx.DiGraph) -> dict[str, list[str]]:
    """Serialize a graph as sorted adjacency for algorithm result payloads."""

    return {
        str(node): _sorted_strings(graph.successors(node)) for node in _sorted_nodes(graph.nodes)
    }
