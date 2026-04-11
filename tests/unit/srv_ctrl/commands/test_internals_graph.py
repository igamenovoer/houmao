from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx  # type: ignore[import-untyped]
from click.testing import CliRunner

from houmao.agents.loop_graph.io import graph_to_node_link_data
from houmao.srv_ctrl.commands.main import cli


def _sample_graph_payload() -> dict[str, Any]:
    """Return one NetworkX node-link graph payload for CLI tests."""

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
    graph.add_edge(
        "master",
        "agent-a",
        key="m-a",
        id="edge-master-agent-a",
        kind="pairwise",
    )
    graph.add_edge(
        "agent-a",
        "agent-b",
        key="a-b",
        id="edge-agent-a-agent-b",
        kind="pairwise",
    )
    return graph_to_node_link_data(graph)


def _packet_payload() -> dict[str, object]:
    """Return packet JSON matching ``_sample_graph_payload``."""

    return {
        "root_packet": {
            "packet_id": "root-packet",
            "intended_recipient": "master",
            "plan_revision": "rev-1",
            "plan_digest": "digest-1",
            "child_dispatch_table": {"agent-a": {"packet_ref": "packet://edge-master-agent-a"}},
        },
        "child_packets": {
            "edge-master-agent-a": {
                "packet_id": "packet-a",
                "intended_recipient": "agent-a",
                "immediate_driver": "master",
                "plan_revision": "rev-1",
                "plan_digest": "digest-1",
                "child_dispatch_table": {"agent-b": {"packet_text": "Dispatch to agent-b."}},
            },
            "edge-agent-a-agent-b": {
                "packet_id": "packet-b",
                "intended_recipient": "agent-b",
                "immediate_driver": "agent-a",
                "plan_revision": "rev-1",
                "plan_digest": "digest-1",
            },
        },
    }


def _write_json(path: Path, payload: object) -> Path:
    """Write one JSON payload for a CLI fixture."""

    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _invoke_json(runner: CliRunner, args: list[str]) -> dict[str, Any]:
    """Run one ``houmao-mgr --print-json`` invocation and parse its payload."""

    result = runner.invoke(cli, ["--print-json", *args])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert isinstance(payload, dict)
    return payload


def test_internals_graph_help_includes_command_examples() -> None:
    runner = CliRunner()
    command_args = [
        ["internals", "graph", "high", "analyze"],
        ["internals", "graph", "high", "packet-expectations"],
        ["internals", "graph", "high", "validate-packets"],
        ["internals", "graph", "high", "slice"],
        ["internals", "graph", "high", "render-mermaid"],
        ["internals", "graph", "low", "create"],
        ["internals", "graph", "low", "mutate"],
        ["internals", "graph", "low", "relabel"],
        ["internals", "graph", "low", "compose"],
        ["internals", "graph", "low", "subgraph"],
        ["internals", "graph", "low", "reverse"],
        ["internals", "graph", "low", "ego"],
        ["internals", "graph", "low", "alg", "ancestors"],
        ["internals", "graph", "low", "alg", "descendants"],
        ["internals", "graph", "low", "alg", "descendants-at-distance"],
        ["internals", "graph", "low", "alg", "topological-sort"],
        ["internals", "graph", "low", "alg", "is-dag"],
        ["internals", "graph", "low", "alg", "cycles"],
        ["internals", "graph", "low", "alg", "weak-components"],
        ["internals", "graph", "low", "alg", "strong-components"],
        ["internals", "graph", "low", "alg", "condensation"],
        ["internals", "graph", "low", "alg", "transitive-reduction"],
        ["internals", "graph", "low", "alg", "dag-longest-path"],
        ["internals", "graph", "low", "alg", "shortest-path"],
        ["internals", "graph", "low", "alg", "all-simple-paths"],
    ]

    for args in command_args:
        result = runner.invoke(cli, [*args, "--help"])

        assert result.exit_code == 0, result.output
        assert "Examples:" in result.output
        assert "houmao-mgr" in result.output


def test_internals_graph_help_documents_non_graph_json_payloads() -> None:
    runner = CliRunner()

    validate_help = runner.invoke(cli, ["internals", "graph", "high", "validate-packets", "--help"])
    mutate_help = runner.invoke(cli, ["internals", "graph", "low", "mutate", "--help"])
    subgraph_help = runner.invoke(cli, ["internals", "graph", "low", "subgraph", "--help"])

    assert validate_help.exit_code == 0, validate_help.output
    assert mutate_help.exit_code == 0, mutate_help.output
    assert subgraph_help.exit_code == 0, subgraph_help.output
    assert "Packet JSON shape" in validate_help.output
    assert "root_packet" in validate_help.output
    assert '"ops"' in mutate_help.output
    assert '"nodes"' in subgraph_help.output


def test_internals_graph_high_analyze_outputs_structured_json(tmp_path: Path) -> None:
    runner = CliRunner()
    graph_path = _write_json(tmp_path / "graph.json", _sample_graph_payload())

    payload = _invoke_json(
        runner,
        ["internals", "graph", "high", "analyze", "--input", str(graph_path)],
    )

    assert payload["operation"] == "high.analyze"
    assert payload["root"] == "master"
    assert payload["mode"] == "pairwise-v2"
    assert payload["non_leaf_nodes"] == ["agent-a", "master"]
    assert payload["leaf_nodes"] == ["agent-b"]


def test_internals_graph_high_validate_packets_outputs_structured_json(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    graph_path = _write_json(tmp_path / "graph.json", _sample_graph_payload())
    packets_path = _write_json(tmp_path / "packets.json", _packet_payload())

    payload = _invoke_json(
        runner,
        [
            "internals",
            "graph",
            "high",
            "validate-packets",
            "--graph",
            str(graph_path),
            "--packets",
            str(packets_path),
        ],
    )

    assert payload["operation"] == "high.validate-packets"
    assert payload["valid"] is True
    assert payload["errors"] == []


def test_internals_graph_low_alg_descendants_outputs_structured_json(tmp_path: Path) -> None:
    runner = CliRunner()
    graph_path = _write_json(tmp_path / "graph.json", _sample_graph_payload())

    payload = _invoke_json(
        runner,
        [
            "internals",
            "graph",
            "low",
            "alg",
            "descendants",
            "--input",
            str(graph_path),
            "--node",
            "master",
        ],
    )

    assert payload["operation"] == "low.alg.descendants"
    assert payload["result"] == ["agent-a", "agent-b"]
    assert payload["warnings"] == [
        "Algorithm executed on a simple directed projection of the multigraph."
    ]


def test_internals_graph_low_mutate_rejects_unsupported_ops(tmp_path: Path) -> None:
    runner = CliRunner()
    graph_path = _write_json(tmp_path / "graph.json", _sample_graph_payload())
    ops_path = _write_json(tmp_path / "ops.json", {"ops": [{"op": "run_python"}]})

    result = runner.invoke(
        cli,
        [
            "--print-json",
            "internals",
            "graph",
            "low",
            "mutate",
            "--input",
            str(graph_path),
            "--ops",
            str(ops_path),
        ],
    )

    assert result.exit_code != 0
    assert "Unsupported graph mutation op `run_python`" in result.output
