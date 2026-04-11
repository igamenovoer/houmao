from __future__ import annotations

from copy import deepcopy

import networkx as nx  # type: ignore[import-untyped]
import pytest

from houmao.agents.loop_graph.analysis import (
    analyze_graph,
    apply_mutation_ops,
    node_subgraph,
    run_low_algorithm,
    slice_graph,
)
from houmao.agents.loop_graph.io import (
    GraphInputError,
    graph_to_node_link_data,
    node_link_data_to_graph,
)
from houmao.agents.loop_graph.packets import (
    build_pairwise_v2_packet_expectations,
    validate_pairwise_v2_packets,
)


def _sample_graph() -> nx.MultiDiGraph:
    """Build one pairwise-v2 graph fixture."""

    graph = nx.MultiDiGraph()
    graph.graph.update(
        {
            "root": "master",
            "mode": "pairwise-v2",
            "plan_revision": "rev-1",
            "plan_digest": "digest-1",
        }
    )
    graph.add_node("master", kind="master")
    graph.add_node("agent-a", kind="worker")
    graph.add_node("agent-b", kind="worker")
    graph.add_node("orphan", kind="worker")
    graph.add_edge(
        "master",
        "agent-a",
        key="m-a",
        id="edge-master-agent-a",
        kind="pairwise",
        component_id="component-a",
    )
    graph.add_edge(
        "agent-a",
        "agent-b",
        key="a-b",
        id="edge-agent-a-agent-b",
        kind="pairwise",
        component_id="component-a",
    )
    return graph


def _valid_packet_payload() -> dict[str, object]:
    """Build a packet document matching ``_sample_graph``."""

    return {
        "root_packet": {
            "packet_id": "root-packet",
            "intended_recipient": "master",
            "plan_revision": "rev-1",
            "plan_digest": "digest-1",
            "child_dispatch_table": [
                {"child": "agent-a", "packet_ref": "packet://edge-master-agent-a"}
            ],
        },
        "child_packets": [
            {
                "packet_id": "packet-a",
                "edge_id": "edge-master-agent-a",
                "intended_recipient": "agent-a",
                "immediate_driver": "master",
                "plan_revision": "rev-1",
                "plan_digest": "digest-1",
                "child_dispatch_table": [
                    {"child": "agent-b", "packet_text": "Dispatch to agent-b."}
                ],
            },
            {
                "packet_id": "packet-b",
                "edge_id": "edge-agent-a-agent-b",
                "intended_recipient": "agent-b",
                "immediate_driver": "agent-a",
                "plan_revision": "rev-1",
                "plan_digest": "digest-1",
            },
        ],
    }


def test_node_link_loading_normalizes_to_multidigraph() -> None:
    graph = nx.DiGraph()
    graph.graph["root"] = "master"
    graph.add_edge("master", "agent-a", id="edge-master-agent-a")

    loaded = node_link_data_to_graph(graph_to_node_link_data(graph))

    assert isinstance(loaded, nx.MultiDiGraph)
    assert loaded.graph["root"] == "master"
    assert list(loaded.successors("master")) == ["agent-a"]


def test_node_link_loading_rejects_non_node_link_payloads() -> None:
    with pytest.raises(GraphInputError, match="nodes"):
        node_link_data_to_graph({"graph": {}, "edges": []})

    with pytest.raises(GraphInputError, match="JSON object"):
        node_link_data_to_graph("nodes:\n  - master")


def test_analyze_graph_reports_houmao_shape_facts() -> None:
    result = analyze_graph(_sample_graph())

    assert result.root == "master"
    assert result.mode == "pairwise-v2"
    assert result.reachable_nodes == ["agent-a", "agent-b", "master"]
    assert result.disconnected_nodes == ["orphan"]
    assert result.leaf_nodes == ["agent-b", "orphan"]
    assert result.non_leaf_nodes == ["agent-a", "master"]
    assert result.immediate_children["master"] == ["agent-a"]
    assert result.immediate_children["agent-a"] == ["agent-b"]
    assert result.is_dag is True
    assert set(result.topological_order or []) == {"master", "agent-a", "agent-b", "orphan"}
    assert "Some graph nodes are not reachable from the configured root." in result.warnings


def test_slice_graph_extracts_descendant_subgraph() -> None:
    sliced = slice_graph(_sample_graph(), root="agent-a", direction="descendants")

    assert sorted(sliced.nodes) == ["agent-a", "agent-b"]
    assert sliced.graph["slice_direction"] == "descendants"
    assert sliced.graph["slice_root"] == "agent-a"


def test_pairwise_v2_packet_expectations_include_root_child_and_dispatch_tables() -> None:
    result = build_pairwise_v2_packet_expectations(_sample_graph())

    root = result.expectations[0]
    child_a = next(
        expectation
        for expectation in result.expectations
        if expectation.edge_id == "edge-master-agent-a"
    )
    child_b = next(
        expectation
        for expectation in result.expectations
        if expectation.edge_id == "edge-agent-a-agent-b"
    )

    assert result.root == "master"
    assert result.plan_revision == "rev-1"
    assert result.plan_digest == "digest-1"
    assert result.non_leaf_nodes == ["agent-a", "master"]
    assert root.packet_kind == "root"
    assert root.expected_recipient == "master"
    assert root.expected_children == ["agent-a"]
    assert root.child_dispatch_table_required is True
    assert child_a.expected_driver == "master"
    assert child_a.expected_recipient == "agent-a"
    assert child_a.expected_children == ["agent-b"]
    assert child_a.child_dispatch_table_required is True
    assert child_b.expected_driver == "agent-a"
    assert child_b.expected_recipient == "agent-b"
    assert child_b.child_dispatch_table_required is False


def test_pairwise_v2_packet_validation_accepts_matching_document() -> None:
    result = validate_pairwise_v2_packets(_sample_graph(), _valid_packet_payload())

    assert result.valid is True
    assert result.errors == []


def test_pairwise_v2_packet_validation_reports_stale_and_mismatched_packets() -> None:
    payload = deepcopy(_valid_packet_payload())
    child_packets = payload["child_packets"]
    assert isinstance(child_packets, list)
    child_a = child_packets[0]
    assert isinstance(child_a, dict)
    child_a["plan_revision"] = "rev-old"
    child_a["intended_recipient"] = "agent-z"

    result = validate_pairwise_v2_packets(_sample_graph(), payload)
    codes = {error.code for error in result.errors}

    assert result.valid is False
    assert "stale_packet" in codes
    assert "intended_recipient_mismatch" in codes


def test_low_level_mutation_subgraph_and_algorithm_helpers() -> None:
    graph = _sample_graph()
    mutated = apply_mutation_ops(
        graph,
        {
            "ops": [
                {"op": "add_node", "node": "agent-c", "attrs": {"kind": "worker"}},
                {
                    "op": "add_edge",
                    "source": "agent-b",
                    "target": "agent-c",
                    "attrs": {"id": "edge-agent-b-agent-c"},
                },
                {"op": "set_graph_attr", "key": "plan_revision", "value": "rev-2"},
            ]
        },
    )

    descendants = run_low_algorithm(mutated, algorithm="descendants", node="master")
    subgraph = node_subgraph(mutated, {"nodes": ["master", "agent-a"]})

    assert mutated.graph["plan_revision"] == "rev-2"
    assert mutated.has_edge("agent-b", "agent-c")
    assert descendants.operation == "low.alg.descendants"
    assert descendants.result == ["agent-a", "agent-b", "agent-c"]
    assert descendants.warnings == [
        "Algorithm executed on a simple directed projection of the multigraph."
    ]
    assert sorted(subgraph.nodes) == ["agent-a", "master"]


def test_expansive_low_level_algorithms_report_effective_bounds() -> None:
    graph = _sample_graph()
    graph.add_edge("master", "agent-b", key="m-b", id="edge-master-agent-b", kind="pairwise")

    result = run_low_algorithm(
        graph,
        algorithm="all-simple-paths",
        source="master",
        target="agent-b",
        cutoff=3,
        limit=1,
    )

    assert result.bound == 3
    assert result.result == [["master", "agent-a", "agent-b"]]
