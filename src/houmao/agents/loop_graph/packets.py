"""Pairwise-v2 routing packet expectations and validation."""

from __future__ import annotations

from typing import Any

import networkx as nx  # type: ignore[import-untyped]
from pydantic import ValidationError

from houmao.agents.loop_graph.models import (
    ChildDispatchEntry,
    PacketDocument,
    PacketExpectation,
    PacketExpectationsResult,
    PacketValidationError,
    PacketValidationResult,
    RoutingPacket,
)


def build_pairwise_v2_packet_expectations(
    graph: nx.MultiDiGraph,
    *,
    root: str | None = None,
) -> PacketExpectationsResult:
    """Build expected routing-packet coverage from a pairwise-v2 topology."""

    resolved_root = root or _optional_graph_attr(graph, "root")
    plan_revision = _optional_graph_attr(graph, "plan_revision")
    plan_digest = _optional_graph_attr(graph, "plan_digest")
    warnings: list[str] = []
    errors: list[str] = []

    if resolved_root is None:
        errors.append("Pairwise-v2 packet expectations require a root.")
    elif resolved_root not in graph:
        errors.append(f"Root `{resolved_root}` is not present in the graph.")

    pairwise_edges = list(_pairwise_edges(graph))
    children_by_driver: dict[str, list[str]] = {}
    for edge in pairwise_edges:
        children_by_driver.setdefault(edge["source"], []).append(edge["target"])
    children_by_driver = {
        driver: sorted(set(children), key=str) for driver, children in children_by_driver.items()
    }
    non_leaf_nodes = sorted(children_by_driver, key=str)

    expectations: list[PacketExpectation] = []
    if resolved_root is not None:
        expectations.append(
            PacketExpectation(
                packet_kind="root",
                expected_recipient=resolved_root,
                expected_children=children_by_driver.get(resolved_root, []),
                child_dispatch_table_required=bool(children_by_driver.get(resolved_root)),
                plan_revision=plan_revision,
                plan_digest=plan_digest,
            )
        )

    for edge in pairwise_edges:
        target = edge["target"]
        expectations.append(
            PacketExpectation(
                packet_kind="child",
                expected_recipient=target,
                expected_driver=edge["source"],
                edge_id=edge["edge_id"],
                edge_key=edge["edge_key"],
                expected_children=children_by_driver.get(target, []),
                child_dispatch_table_required=bool(children_by_driver.get(target)),
                plan_revision=plan_revision,
                plan_digest=plan_digest,
            )
        )

    if not pairwise_edges:
        warnings.append("No pairwise edges were found in the graph.")

    return PacketExpectationsResult(
        root=resolved_root,
        mode=_optional_graph_attr(graph, "mode"),
        plan_revision=plan_revision,
        plan_digest=plan_digest,
        non_leaf_nodes=non_leaf_nodes,
        expectations=expectations,
        warnings=warnings,
        errors=errors,
    )


def validate_pairwise_v2_packets(
    graph: nx.MultiDiGraph,
    packet_payload: object,
    *,
    root: str | None = None,
) -> PacketValidationResult:
    """Validate one packet document against pairwise-v2 graph expectations."""

    expectations = build_pairwise_v2_packet_expectations(graph, root=root)
    packet_document = parse_packet_document(packet_payload)
    errors: list[PacketValidationError] = []

    for expectation in expectations.expectations:
        if expectation.packet_kind == "root":
            _validate_root_packet(
                packet_document.root_packet,
                expectation=expectation,
                errors=errors,
            )
        else:
            packet = _find_child_packet(packet_document, expectation=expectation)
            _validate_child_packet(packet, expectation=expectation, errors=errors)

    warnings = list(expectations.warnings)
    if expectations.errors:
        for message in expectations.errors:
            errors.append(PacketValidationError(code="graph_error", message=message))

    return PacketValidationResult(
        valid=not errors,
        root=expectations.root,
        expectations=expectations.expectations,
        errors=errors,
        warnings=warnings,
    )


def parse_packet_document(payload: object) -> PacketDocument:
    """Parse a flexible packet JSON document into a normalized model."""

    if not isinstance(payload, dict):
        raise ValueError("Packet document must be a JSON object.")

    root_packet = _optional_packet(payload.get("root_packet"))
    raw_child_packets = payload.get("child_packets", payload.get("packets", []))
    child_packets = _coerce_packet_list(raw_child_packets)
    try:
        return PacketDocument(root_packet=root_packet, child_packets=child_packets)
    except ValidationError as exc:
        raise ValueError(f"Invalid packet document: {exc}") from exc


def _validate_root_packet(
    packet: RoutingPacket | None,
    *,
    expectation: PacketExpectation,
    errors: list[PacketValidationError],
) -> None:
    """Validate the root routing packet."""

    if packet is None:
        errors.append(
            PacketValidationError(
                code="missing_root_packet",
                message="The root routing packet is missing.",
                recipient=expectation.expected_recipient,
            )
        )
        return
    _validate_recipient(packet, expectation=expectation, errors=errors)
    _validate_freshness(packet, expectation=expectation, errors=errors)
    _validate_dispatch_table(packet, expectation=expectation, errors=errors)


def _validate_child_packet(
    packet: RoutingPacket | None,
    *,
    expectation: PacketExpectation,
    errors: list[PacketValidationError],
) -> None:
    """Validate one expected child routing packet."""

    if packet is None:
        errors.append(
            PacketValidationError(
                code="missing_child_packet",
                message="The expected child routing packet is missing.",
                edge_id=expectation.edge_id,
                driver=expectation.expected_driver,
                recipient=expectation.expected_recipient,
            )
        )
        return
    _validate_recipient(packet, expectation=expectation, errors=errors)
    _validate_driver(packet, expectation=expectation, errors=errors)
    _validate_freshness(packet, expectation=expectation, errors=errors)
    _validate_dispatch_table(packet, expectation=expectation, errors=errors)


def _validate_recipient(
    packet: RoutingPacket,
    *,
    expectation: PacketExpectation,
    errors: list[PacketValidationError],
) -> None:
    """Validate a routing packet recipient."""

    if packet.intended_recipient != expectation.expected_recipient:
        errors.append(
            PacketValidationError(
                code="intended_recipient_mismatch",
                message=(
                    "Packet intended recipient does not match the graph-derived expected recipient."
                ),
                edge_id=expectation.edge_id,
                driver=expectation.expected_driver,
                recipient=expectation.expected_recipient,
                packet_id=packet.packet_id,
            )
        )


def _validate_driver(
    packet: RoutingPacket,
    *,
    expectation: PacketExpectation,
    errors: list[PacketValidationError],
) -> None:
    """Validate a routing packet immediate driver."""

    if packet.immediate_driver != expectation.expected_driver:
        errors.append(
            PacketValidationError(
                code="immediate_driver_mismatch",
                message="Packet immediate driver does not match the expected graph edge driver.",
                edge_id=expectation.edge_id,
                driver=expectation.expected_driver,
                recipient=expectation.expected_recipient,
                packet_id=packet.packet_id,
            )
        )


def _validate_freshness(
    packet: RoutingPacket,
    *,
    expectation: PacketExpectation,
    errors: list[PacketValidationError],
) -> None:
    """Validate routing packet freshness markers."""

    if expectation.plan_revision is not None and packet.plan_revision != expectation.plan_revision:
        errors.append(
            PacketValidationError(
                code="stale_packet",
                message="Packet plan revision does not match the active graph plan revision.",
                edge_id=expectation.edge_id,
                driver=expectation.expected_driver,
                recipient=expectation.expected_recipient,
                packet_id=packet.packet_id,
            )
        )
    if expectation.plan_digest is not None and packet.plan_digest != expectation.plan_digest:
        errors.append(
            PacketValidationError(
                code="stale_packet",
                message="Packet plan digest does not match the active graph plan digest.",
                edge_id=expectation.edge_id,
                driver=expectation.expected_driver,
                recipient=expectation.expected_recipient,
                packet_id=packet.packet_id,
            )
        )


def _validate_dispatch_table(
    packet: RoutingPacket,
    *,
    expectation: PacketExpectation,
    errors: list[PacketValidationError],
) -> None:
    """Validate required child dispatch-table coverage."""

    if not expectation.child_dispatch_table_required:
        return
    if not packet.child_dispatch_table:
        errors.append(
            PacketValidationError(
                code="missing_child_dispatch_table",
                message="Expected a child dispatch table for a non-leaf routing packet.",
                edge_id=expectation.edge_id,
                driver=expectation.expected_driver,
                recipient=expectation.expected_recipient,
                packet_id=packet.packet_id,
            )
        )
        return
    by_child = {entry.child: entry for entry in packet.child_dispatch_table}
    for child in expectation.expected_children:
        entry = by_child.get(child)
        if entry is None or (entry.packet_text is None and entry.packet_ref is None):
            errors.append(
                PacketValidationError(
                    code="missing_child_packet_reference",
                    message=(
                        "Dispatch-table child is missing exact child packet text or an "
                        "exact child packet reference."
                    ),
                    edge_id=expectation.edge_id,
                    driver=expectation.expected_recipient,
                    recipient=child,
                    packet_id=packet.packet_id,
                )
            )


def _find_child_packet(
    packet_document: PacketDocument,
    *,
    expectation: PacketExpectation,
) -> RoutingPacket | None:
    """Return the child packet matching one expectation."""

    for packet in packet_document.child_packets:
        if expectation.edge_id is not None and packet.edge_id == expectation.edge_id:
            return packet
    for packet in packet_document.child_packets:
        if (
            packet.immediate_driver == expectation.expected_driver
            and packet.intended_recipient == expectation.expected_recipient
        ):
            return packet
    return None


def _optional_graph_attr(graph: nx.Graph, key: str) -> str | None:
    """Return one optional graph attribute as a string."""

    value = graph.graph.get(key)
    return str(value) if value is not None else None


def _pairwise_edges(graph: nx.MultiDiGraph) -> list[dict[str, str]]:
    """Return graph edges treated as pairwise-v2 parent-to-child edges."""

    edges: list[dict[str, str]] = []
    for source, target, key, data in graph.edges(keys=True, data=True):
        kind = str(data.get("kind", data.get("component_type", "pairwise"))).lower()
        if bool(data.get("dependency")) or "dependency" in kind or kind == "relay":
            continue
        edge_id = data.get("id", data.get("edge_id", key))
        edges.append(
            {
                "source": str(source),
                "target": str(target),
                "edge_id": str(edge_id),
                "edge_key": str(key),
            }
        )
    return edges


def _optional_packet(payload: object) -> RoutingPacket | None:
    """Normalize an optional routing packet payload."""

    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ValueError("Routing packet payloads must be JSON objects.")
    return _packet_from_mapping(payload)


def _coerce_packet_list(payload: object) -> list[RoutingPacket]:
    """Normalize child packet collections."""

    packets: list[RoutingPacket] = []
    if payload is None:
        return packets
    if isinstance(payload, dict):
        for key, value in payload.items():
            if not isinstance(value, dict):
                raise ValueError("Child packet mapping values must be JSON objects.")
            packet_data = dict(value)
            packet_data.setdefault("edge_id", str(key))
            packets.append(_packet_from_mapping(packet_data))
        return packets
    if not isinstance(payload, list):
        raise ValueError("Child packets must be a list or object mapping.")
    for value in payload:
        if not isinstance(value, dict):
            raise ValueError("Child packet list entries must be JSON objects.")
        packets.append(_packet_from_mapping(value))
    return packets


def _packet_from_mapping(payload: dict[str, Any]) -> RoutingPacket:
    """Build one packet model from a raw JSON mapping."""

    packet_data = dict(payload)
    packet_data["child_dispatch_table"] = _coerce_dispatch_table(
        packet_data.get("child_dispatch_table", packet_data.get("dispatch_table"))
    )
    try:
        return RoutingPacket.model_validate(packet_data)
    except ValidationError as exc:
        raise ValueError(f"Invalid routing packet: {exc}") from exc


def _coerce_dispatch_table(payload: object) -> list[ChildDispatchEntry]:
    """Normalize child dispatch-table forms."""

    if payload is None:
        return []
    entries: list[ChildDispatchEntry] = []
    if isinstance(payload, dict):
        for child, raw in payload.items():
            if isinstance(raw, dict):
                entry_data = dict(raw)
                entry_data.setdefault("child", str(child))
            else:
                entry_data = {"child": str(child), "packet_ref": str(raw)}
            entries.append(ChildDispatchEntry.model_validate(entry_data))
        return entries
    if not isinstance(payload, list):
        raise ValueError("Child dispatch table must be a list or object mapping.")
    for raw in payload:
        if isinstance(raw, str):
            entries.append(ChildDispatchEntry(child=raw))
            continue
        if not isinstance(raw, dict):
            raise ValueError("Child dispatch entries must be strings or JSON objects.")
        entries.append(ChildDispatchEntry.model_validate(raw))
    return entries
