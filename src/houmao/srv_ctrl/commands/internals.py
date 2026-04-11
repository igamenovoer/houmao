"""Internal utility commands for ``houmao-mgr``."""

from __future__ import annotations

from pathlib import Path

import click
import networkx as nx  # type: ignore[import-untyped]

from houmao.agents.loop_graph.analysis import (
    analyze_graph,
    apply_mutation_ops,
    compose_graphs,
    create_empty_graph,
    ego_graph,
    node_subgraph,
    relabel_graph,
    reverse_graph,
    run_low_algorithm,
    slice_graph,
)
from houmao.agents.loop_graph.io import (
    GraphInputError,
    graph_to_node_link_data,
    read_graph_document,
    read_json_document,
)
from houmao.agents.loop_graph.mermaid import render_mermaid
from houmao.agents.loop_graph.packets import (
    build_pairwise_v2_packet_expectations,
    validate_pairwise_v2_packets,
)

from .output import emit

_GRAPH_INPUT_HELP = "NetworkX node-link JSON graph file; use `-` to read stdin."
_GRAPH_OUTPUT_NOTE = "Input and output graphs use NetworkX node-link JSON with `nodes` and `edges`."
_PACKET_DOC_NOTE = (
    "Packet JSON shape: `root_packet` plus `child_packets`, where each packet includes "
    "`intended_recipient`, `immediate_driver`, freshness markers, and optional "
    "`child_dispatch_table` entries with `packet_text` or `packet_ref`."
)
_OPS_DOC_NOTE = (
    'Ops JSON shape: `{ "ops": [{ "op": "add_node", "node": "agent-a", '
    '"attrs": {"kind": "agent"} }] }`.'
)


def _help(summary: str, *examples: str) -> str:
    """Build help text with examples for agent-facing commands."""

    example_text = "\n".join(f"  {example}" for example in examples)
    return f"{summary}\n\n{_GRAPH_OUTPUT_NOTE}\n\n\\b\nExamples:\n{example_text}"


@click.group(name="internals")
def internals_group() -> None:
    """Internal Houmao utility commands for agents and maintainers."""


@internals_group.group(name="graph")
def graph_group() -> None:
    """NetworkX-backed graph helpers using node-link JSON."""


@graph_group.group(name="high")
def graph_high_group() -> None:
    """Houmao-aware loop graph helpers."""


@graph_group.group(name="low")
def graph_low_group() -> None:
    """Constrained NetworkX-style low-level graph primitives."""


@graph_low_group.group(name="alg")
def graph_low_alg_group() -> None:
    """Whitelisted low-level graph algorithm wrappers."""


@graph_high_group.command(
    name="analyze",
    help=_help(
        "Analyze Houmao loop graph structure.",
        "houmao-mgr --print-json internals graph high analyze --input graph.json",
        "houmao-mgr internals graph high analyze --input graph.json --root master --mode pairwise-v2",
    ),
)
@click.option(
    "--input", "input_path", required=True, type=click.Path(path_type=Path), help=_GRAPH_INPUT_HELP
)
@click.option("--root", default=None, help="Optional root override; defaults to graph.root.")
@click.option("--mode", default=None, help="Optional mode override; defaults to graph.mode.")
@click.option(
    "--cycle-limit",
    default=20,
    show_default=True,
    type=click.IntRange(min=1),
    help="Maximum cycle examples to include.",
)
def high_analyze_command(
    input_path: Path,
    root: str | None,
    mode: str | None,
    cycle_limit: int,
) -> None:
    """Analyze one Houmao graph."""

    graph = _read_graph_or_click(input_path)
    emit(analyze_graph(graph, root=root, mode=mode, cycle_limit=cycle_limit))


@graph_high_group.command(
    name="packet-expectations",
    help=_help(
        "Derive pairwise-v2 routing-packet expectations from graph topology.",
        "houmao-mgr --print-json internals graph high packet-expectations --input graph.json",
        "houmao-mgr internals graph high packet-expectations --input graph.json --root master",
    ),
)
@click.option(
    "--input", "input_path", required=True, type=click.Path(path_type=Path), help=_GRAPH_INPUT_HELP
)
@click.option("--root", default=None, help="Optional root override; defaults to graph.root.")
def high_packet_expectations_command(input_path: Path, root: str | None) -> None:
    """Derive pairwise-v2 routing-packet expectations."""

    graph = _read_graph_or_click(input_path)
    emit(build_pairwise_v2_packet_expectations(graph, root=root))


@graph_high_group.command(
    name="validate-packets",
    help=_help(
        f"Validate pairwise-v2 routing packets against graph-derived expectations. {_PACKET_DOC_NOTE}",
        (
            "houmao-mgr --print-json internals graph high validate-packets "
            "--graph graph.json --packets packets.json"
        ),
        (
            "houmao-mgr internals graph high validate-packets "
            "--graph graph.json --packets packets.json --root master"
        ),
    ),
)
@click.option(
    "--graph", "graph_path", required=True, type=click.Path(path_type=Path), help=_GRAPH_INPUT_HELP
)
@click.option(
    "--packets",
    "packets_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Pairwise-v2 routing packet JSON document.",
)
@click.option("--root", default=None, help="Optional root override; defaults to graph.root.")
def high_validate_packets_command(
    graph_path: Path,
    packets_path: Path,
    root: str | None,
) -> None:
    """Validate pairwise-v2 routing-packet metadata."""

    graph = _read_graph_or_click(graph_path)
    packet_payload = _read_json_or_click(packets_path)
    try:
        emit(validate_pairwise_v2_packets(graph, packet_payload, root=root))
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@graph_high_group.command(
    name="slice",
    help=_help(
        "Extract an authoring-time graph slice.",
        (
            "houmao-mgr --print-json internals graph high slice --input graph.json "
            "--root agent-a --direction descendants"
        ),
        (
            "houmao-mgr --print-json internals graph high slice --input graph.json "
            "--direction component --component-id c1 --root master"
        ),
    ),
)
@click.option(
    "--input", "input_path", required=True, type=click.Path(path_type=Path), help=_GRAPH_INPUT_HELP
)
@click.option(
    "--root", required=True, help="Root node for ancestor, descendant, or reachable slices."
)
@click.option(
    "--direction",
    required=True,
    type=click.Choice(["ancestors", "descendants", "reachable", "component"]),
    help="Slice direction.",
)
@click.option("--component-id", default=None, help="Component id required for component slices.")
def high_slice_command(
    input_path: Path,
    root: str,
    direction: str,
    component_id: str | None,
) -> None:
    """Extract one high-level graph slice."""

    graph = _read_graph_or_click(input_path)
    try:
        emit(
            graph_to_node_link_data(
                slice_graph(graph, root=root, direction=direction, component_id=component_id)
            )
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@graph_high_group.command(
    name="render-mermaid",
    help=_help(
        "Render deterministic Mermaid scaffolding from graph structure.",
        "houmao-mgr internals graph high render-mermaid --input graph.json",
        "houmao-mgr --print-json internals graph high render-mermaid --input graph.json --mode generic",
    ),
)
@click.option(
    "--input", "input_path", required=True, type=click.Path(path_type=Path), help=_GRAPH_INPUT_HELP
)
@click.option("--root", default=None, help="Optional root override; defaults to graph.root.")
@click.option("--mode", default=None, help="Optional mode override; defaults to graph.mode.")
def high_render_mermaid_command(input_path: Path, root: str | None, mode: str | None) -> None:
    """Render Mermaid scaffolding for one graph."""

    graph = _read_graph_or_click(input_path)
    payload = {
        "operation": "high.render-mermaid",
        "mermaid": render_mermaid(graph, root=root, mode=mode),
        "note": "Scaffold only; review loop semantics in the owning Houmao skill.",
    }
    emit(payload, plain_renderer=_render_mermaid_plain)


@graph_low_group.command(
    name="create",
    help=_help(
        "Create an empty supported NetworkX graph.",
        "houmao-mgr --print-json internals graph low create --type multidigraph",
        "houmao-mgr --print-json internals graph low create --type digraph",
    ),
)
@click.option(
    "--type",
    "graph_type",
    default="multidigraph",
    show_default=True,
    type=click.Choice(["multidigraph", "digraph", "multigraph", "graph"]),
    help="NetworkX graph type to create.",
)
def low_create_command(graph_type: str) -> None:
    """Create one empty graph."""

    try:
        emit(graph_to_node_link_data(create_empty_graph(graph_type)))
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@graph_low_group.command(
    name="mutate",
    help=_help(
        f"Apply constrained graph mutation operations. {_OPS_DOC_NOTE}",
        "houmao-mgr --print-json internals graph low mutate --input graph.json --ops ops.json",
        'printf \'%s\' \'{"ops":[{"op":"add_node","node":"agent-a"}]}\' > ops.json',
    ),
)
@click.option(
    "--input", "input_path", required=True, type=click.Path(path_type=Path), help=_GRAPH_INPUT_HELP
)
@click.option(
    "--ops", "ops_path", required=True, type=click.Path(path_type=Path), help="Mutation ops JSON."
)
def low_mutate_command(input_path: Path, ops_path: Path) -> None:
    """Apply low-level graph mutation operations."""

    graph = _read_graph_or_click(input_path)
    ops_payload = _read_json_or_click(ops_path)
    try:
        emit(graph_to_node_link_data(apply_mutation_ops(graph, ops_payload)))
    except (ValueError, nx.NetworkXException) as exc:
        raise click.ClickException(str(exc)) from exc


@graph_low_group.command(
    name="relabel",
    help=_help(
        "Relabel graph nodes with a JSON object mapping.",
        "houmao-mgr --print-json internals graph low relabel --input graph.json --mapping mapping.json",
        "printf '%s' '{\"old-agent\":\"new-agent\"}' > mapping.json",
    ),
)
@click.option(
    "--input", "input_path", required=True, type=click.Path(path_type=Path), help=_GRAPH_INPUT_HELP
)
@click.option(
    "--mapping",
    "mapping_path",
    required=True,
    type=click.Path(path_type=Path),
    help="JSON object mapping old node ids to new node ids.",
)
def low_relabel_command(input_path: Path, mapping_path: Path) -> None:
    """Relabel graph nodes."""

    graph = _read_graph_or_click(input_path)
    mapping = _read_json_or_click(mapping_path)
    try:
        emit(graph_to_node_link_data(relabel_graph(graph, mapping)))
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@graph_low_group.command(
    name="compose",
    help=_help(
        "Compose two node-link graphs.",
        "houmao-mgr --print-json internals graph low compose --left a.json --right b.json",
        "houmao-mgr internals graph low compose --left base.json --right overlay.json",
    ),
)
@click.option(
    "--left", "left_path", required=True, type=click.Path(path_type=Path), help="Left graph JSON."
)
@click.option(
    "--right",
    "right_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Right graph JSON.",
)
def low_compose_command(left_path: Path, right_path: Path) -> None:
    """Compose two graphs."""

    emit(
        graph_to_node_link_data(
            compose_graphs(_read_graph_or_click(left_path), _read_graph_or_click(right_path))
        )
    )


@graph_low_group.command(
    name="subgraph",
    help=_help(
        "Extract a node-induced subgraph.",
        "houmao-mgr --print-json internals graph low subgraph --input graph.json --nodes nodes.json",
        'printf \'%s\' \'{"nodes":["master","agent-a"]}\' > nodes.json',
    ),
)
@click.option(
    "--input", "input_path", required=True, type=click.Path(path_type=Path), help=_GRAPH_INPUT_HELP
)
@click.option(
    "--nodes", "nodes_path", required=True, type=click.Path(path_type=Path), help="JSON node list."
)
def low_subgraph_command(input_path: Path, nodes_path: Path) -> None:
    """Extract a node-induced subgraph."""

    graph = _read_graph_or_click(input_path)
    nodes_payload = _read_json_or_click(nodes_path)
    try:
        emit(graph_to_node_link_data(node_subgraph(graph, nodes_payload)))
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@graph_low_group.command(
    name="reverse",
    help=_help(
        "Reverse directed graph edges.",
        "houmao-mgr --print-json internals graph low reverse --input graph.json",
        "houmao-mgr internals graph low reverse --input graph.json",
    ),
)
@click.option(
    "--input", "input_path", required=True, type=click.Path(path_type=Path), help=_GRAPH_INPUT_HELP
)
def low_reverse_command(input_path: Path) -> None:
    """Reverse graph edges."""

    emit(graph_to_node_link_data(reverse_graph(_read_graph_or_click(input_path))))


@graph_low_group.command(
    name="ego",
    help=_help(
        "Compute an ego graph around one node.",
        "houmao-mgr --print-json internals graph low ego --input graph.json --node agent-a --radius 2",
        "houmao-mgr internals graph low ego --input graph.json --node agent-a --undirected",
    ),
)
@click.option(
    "--input", "input_path", required=True, type=click.Path(path_type=Path), help=_GRAPH_INPUT_HELP
)
@click.option("--node", required=True, help="Center node.")
@click.option(
    "--radius", default=1, show_default=True, type=click.IntRange(min=0), help="Ego radius."
)
@click.option("--undirected", is_flag=True, help="Treat graph as undirected for ego expansion.")
def low_ego_command(input_path: Path, node: str, radius: int, undirected: bool) -> None:
    """Compute an ego graph around one node."""

    graph = _read_graph_or_click(input_path)
    try:
        emit(
            graph_to_node_link_data(
                ego_graph(graph, node=node, radius=radius, undirected=undirected)
            )
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _algorithm_command(name: str, help_summary: str, *examples: str) -> click.Command:
    """Create one low-level algorithm Click command."""

    @click.command(name=name, help=_help(help_summary, *examples))
    @click.option(
        "--input",
        "input_path",
        required=True,
        type=click.Path(path_type=Path),
        help=_GRAPH_INPUT_HELP,
    )
    @click.option("--node", default=None, help="Node argument for node-centered algorithms.")
    @click.option("--source", default=None, help="Source node for path algorithms.")
    @click.option("--target", default=None, help="Target node for path algorithms.")
    @click.option("--distance", default=None, type=click.IntRange(min=0), help="Distance value.")
    @click.option("--cutoff", default=None, type=click.IntRange(min=0), help="Path cutoff.")
    @click.option(
        "--length-bound", default=None, type=click.IntRange(min=1), help="Cycle length bound."
    )
    @click.option(
        "--limit",
        default=50,
        show_default=True,
        type=click.IntRange(min=1),
        help="Maximum result count for expansive algorithms.",
    )
    def command(
        input_path: Path,
        node: str | None,
        source: str | None,
        target: str | None,
        distance: int | None,
        cutoff: int | None,
        length_bound: int | None,
        limit: int,
    ) -> None:
        """Run one whitelisted low-level graph algorithm."""

        graph = _read_graph_or_click(input_path)
        try:
            emit(
                run_low_algorithm(
                    graph,
                    algorithm=name,
                    node=node,
                    source=source,
                    target=target,
                    distance=distance,
                    cutoff=cutoff,
                    length_bound=length_bound,
                    limit=limit,
                )
            )
        except (ValueError, nx.NetworkXException) as exc:
            raise click.ClickException(str(exc)) from exc

    return command


graph_low_alg_group.add_command(
    _algorithm_command(
        "ancestors",
        "Return NetworkX ancestors for one node.",
        "houmao-mgr --print-json internals graph low alg ancestors --input graph.json --node agent-b",
    )
)
graph_low_alg_group.add_command(
    _algorithm_command(
        "descendants",
        "Return NetworkX descendants for one node.",
        "houmao-mgr --print-json internals graph low alg descendants --input graph.json --node agent-a",
    )
)
graph_low_alg_group.add_command(
    _algorithm_command(
        "descendants-at-distance",
        "Return NetworkX descendants at an exact distance.",
        (
            "houmao-mgr --print-json internals graph low alg descendants-at-distance "
            "--input graph.json --node master --distance 2"
        ),
    )
)
graph_low_alg_group.add_command(
    _algorithm_command(
        "topological-sort",
        "Return a deterministic topological ordering.",
        "houmao-mgr --print-json internals graph low alg topological-sort --input graph.json",
    )
)
graph_low_alg_group.add_command(
    _algorithm_command(
        "is-dag",
        "Report whether the directed graph is acyclic.",
        "houmao-mgr --print-json internals graph low alg is-dag --input graph.json",
    )
)
graph_low_alg_group.add_command(
    _algorithm_command(
        "cycles",
        "Return bounded simple cycle examples.",
        (
            "houmao-mgr --print-json internals graph low alg cycles --input graph.json "
            "--length-bound 6 --limit 10"
        ),
    )
)
graph_low_alg_group.add_command(
    _algorithm_command(
        "weak-components",
        "Return weakly connected component sets.",
        "houmao-mgr --print-json internals graph low alg weak-components --input graph.json",
    )
)
graph_low_alg_group.add_command(
    _algorithm_command(
        "strong-components",
        "Return strongly connected component sets.",
        "houmao-mgr --print-json internals graph low alg strong-components --input graph.json",
    )
)
graph_low_alg_group.add_command(
    _algorithm_command(
        "condensation",
        "Return NetworkX condensation graph summary.",
        "houmao-mgr --print-json internals graph low alg condensation --input graph.json",
    )
)
graph_low_alg_group.add_command(
    _algorithm_command(
        "transitive-reduction",
        "Return a transitive-reduction adjacency summary for a DAG.",
        "houmao-mgr --print-json internals graph low alg transitive-reduction --input graph.json",
    )
)
graph_low_alg_group.add_command(
    _algorithm_command(
        "dag-longest-path",
        "Return a DAG longest path.",
        "houmao-mgr --print-json internals graph low alg dag-longest-path --input graph.json",
    )
)
graph_low_alg_group.add_command(
    _algorithm_command(
        "shortest-path",
        "Return one shortest path between source and target.",
        (
            "houmao-mgr --print-json internals graph low alg shortest-path "
            "--input graph.json --source master --target agent-b"
        ),
    )
)
graph_low_alg_group.add_command(
    _algorithm_command(
        "all-simple-paths",
        "Return bounded simple paths between source and target.",
        (
            "houmao-mgr --print-json internals graph low alg all-simple-paths "
            "--input graph.json --source master --target agent-b --cutoff 5 --limit 20"
        ),
    )
)


def _read_graph_or_click(path: Path | None) -> nx.MultiDiGraph:
    """Read one graph and normalize input errors to Click exceptions."""

    try:
        return read_graph_document(path)
    except GraphInputError as exc:
        raise click.ClickException(str(exc)) from exc


def _read_json_or_click(path: Path | None) -> object:
    """Read one JSON document and normalize input errors to Click exceptions."""

    try:
        return read_json_document(path)
    except GraphInputError as exc:
        raise click.ClickException(str(exc)) from exc


def _render_mermaid_plain(payload: object) -> None:
    """Render Mermaid payloads as plain Mermaid text."""

    if isinstance(payload, dict) and isinstance(payload.get("mermaid"), str):
        click.echo(payload["mermaid"], nl=False)
    else:
        click.echo(str(payload))
