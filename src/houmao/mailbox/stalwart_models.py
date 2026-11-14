"""Bounded JMAP wire results shared by online attachment and observation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class JmapOperationMeter:
    """An operation-local deadline and method meter, including failed requests."""

    deadline: float
    remaining_methods: int | None
    attempted_methods: int = 0


@dataclass(frozen=True)
class JmapMetadataQuery:
    """An exact server-filtered mailbox view, with an exclusive timestamp boundary."""

    box: str = "inbox"
    read_state: str = "any"
    answered_state: str = "any"
    archived: bool | None = None
    since: str | None = None


@dataclass(frozen=True)
class ValidatedJmapBinding:
    """Secret-free validated account, submission identity, and connection limits."""

    account_id: str
    identity_id: str
    sender_address: str
    discovery_url: str
    api_url: str
    capabilities: dict[str, Any]
    mailbox_roles: dict[str, str]
    max_objects_in_get: int
    max_calls_in_request: int


@dataclass(frozen=True)
class JmapMetadataPage:
    """A finite metadata page whose counts never imply the account's total size."""

    messages: list[dict[str, Any]]
    query_state: str
    position: int
    has_more: bool
    complete: bool
    next_position: int | None
    total_count: int | None = None
    method_calls: int = 0


@dataclass(frozen=True)
class JmapMetadataBatch:
    """Metadata and authoritative missing IDs from one bounded Email/get."""

    messages: list[dict[str, Any]]
    not_found: list[str]
    state: str
    method_calls: int = 1


@dataclass(frozen=True)
class JmapEmailChanges:
    """An object-state delta, including a resumable intermediate checkpoint."""

    old_state: str
    new_state: str
    has_more_changes: bool
    created: list[str]
    updated: list[str]
    destroyed: list[str]
    method_calls: int = 1


@dataclass(frozen=True)
class JmapQueryChanges:
    """A query-specific delta; this protocol has no hasMoreChanges field."""

    old_query_state: str
    new_query_state: str
    removed: list[str]
    added: list[dict[str, Any]] = field(default_factory=list)
    total_count: int | None = None
    method_calls: int = 1
