"""Structured models for Houmao loop graph analysis and validation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


JsonObject = dict[str, Any]
"""JSON-compatible object mapping used by graph helper payloads."""


class GraphSummary(BaseModel):
    """Compact summary of one loaded graph."""

    node_count: int
    edge_count: int
    directed: bool
    multigraph: bool
    metadata: JsonObject = Field(default_factory=dict)


class GraphAnalysisResult(BaseModel):
    """High-level structural facts for one Houmao graph."""

    operation: str = "high.analyze"
    graph: GraphSummary
    root: str | None = None
    mode: str | None = None
    reachable_nodes: list[str] = Field(default_factory=list)
    disconnected_nodes: list[str] = Field(default_factory=list)
    leaf_nodes: list[str] = Field(default_factory=list)
    non_leaf_nodes: list[str] = Field(default_factory=list)
    immediate_children: dict[str, list[str]] = Field(default_factory=dict)
    branch_points: list[str] = Field(default_factory=list)
    is_dag: bool
    topological_order: list[str] | None = None
    cycles: list[list[str]] = Field(default_factory=list)
    weak_components: list[list[str]] = Field(default_factory=list)
    strong_components: list[list[str]] = Field(default_factory=list)
    dependency_edges: list[JsonObject] = Field(default_factory=list)
    component_dependency_order: list[str] | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PacketExpectation(BaseModel):
    """Expected routing packet derived from a pairwise-v2 topology."""

    packet_kind: Literal["root", "child"]
    expected_recipient: str
    expected_driver: str | None = None
    edge_id: str | None = None
    edge_key: str | None = None
    expected_children: list[str] = Field(default_factory=list)
    child_dispatch_table_required: bool = False
    plan_revision: str | None = None
    plan_digest: str | None = None


class PacketExpectationsResult(BaseModel):
    """Routing-packet expectation payload for one pairwise-v2 graph."""

    operation: str = "high.packet-expectations"
    root: str | None = None
    mode: str | None = None
    plan_revision: str | None = None
    plan_digest: str | None = None
    non_leaf_nodes: list[str] = Field(default_factory=list)
    expectations: list[PacketExpectation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ChildDispatchEntry(BaseModel):
    """One child dispatch-table entry from a routing packet document."""

    child: str
    packet_id: str | None = None
    packet_text: str | None = None
    packet_ref: str | None = None


class RoutingPacket(BaseModel):
    """Machine-readable routing packet metadata for validation."""

    packet_id: str | None = None
    edge_id: str | None = None
    intended_recipient: str | None = None
    immediate_driver: str | None = None
    plan_revision: str | None = None
    plan_digest: str | None = None
    packet_text: str | None = None
    packet_ref: str | None = None
    child_dispatch_table: list[ChildDispatchEntry] = Field(default_factory=list)


class PacketDocument(BaseModel):
    """Machine-readable packet collection consumed by packet validation."""

    root_packet: RoutingPacket | None = None
    child_packets: list[RoutingPacket] = Field(default_factory=list)


class PacketValidationError(BaseModel):
    """One fail-closed routing-packet validation error."""

    code: str
    message: str
    edge_id: str | None = None
    driver: str | None = None
    recipient: str | None = None
    packet_id: str | None = None


class PacketValidationResult(BaseModel):
    """Structured result for pairwise-v2 packet validation."""

    operation: str = "high.validate-packets"
    valid: bool
    root: str | None = None
    expectations: list[PacketExpectation] = Field(default_factory=list)
    errors: list[PacketValidationError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AlgorithmResult(BaseModel):
    """Structured result for one low-level graph algorithm."""

    operation: str
    result: Any
    bound: int | None = None
    warnings: list[str] = Field(default_factory=list)
