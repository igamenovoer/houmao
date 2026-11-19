"""Shared parsing state and accounting-only observation construction.

These helpers keep source-format parsing independent of collection I/O. Provider
adapters preserve absent fields and carry scope and identities into assembly.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import hashlib
import json
import math
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from houmao.agents.realm_controller.usage_models import (
    UsageCoverage,
    UsageNumber,
    UsageObservation,
    UsageScope,
    UsageSourceKind,
    UsageTokenSemantics,
    UsageTurnSnapshot,
    opaque_usage_reference,
)

TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)


class UsageAdapterState(BaseModel):
    """JSON-safe private state needed to resume one provider source stream."""

    model_config = ConfigDict(extra="forbid")
    provider: str
    provider_session_id: str | None = None
    provider_turn_id: str | None = None
    model: str | None = None
    previous_totals: dict[str, UsageNumber | None] = Field(default_factory=dict)
    previous_total_source_ids: dict[str, list[str]] = Field(default_factory=dict)
    latest_response_values: dict[str, UsageNumber | None] = Field(default_factory=dict)
    latest_response_id: str | None = None
    forked_from_id: str | None = None
    spawned_subagent: bool = False
    replay_active: bool = False
    compacted_ids: list[str] = Field(default_factory=list)
    pending_compactions: dict[str, dict[str, Any]] = Field(default_factory=dict)
    occurrences: dict[str, int] = Field(default_factory=dict)
    sequence: int = 0
    profile_id: str | None = None
    provider_version: str | None = None
    qualified_version: bool = True


class UsageParseContext(BaseModel):
    """Per-call source locator and optional Houmao turn association."""

    source_kind: UsageSourceKind = "native_session_log"
    source_ref: str
    turn_id: str | None = None
    binding_id: str | None = None


def mapping(value: Any) -> Mapping[str, Any]:
    """Return a mapping view, using an empty view for another JSON shape."""

    return value if isinstance(value, dict) else {}


def text_id(value: Any) -> str | None:
    """Read a nonempty identity, retaining numeric zero as a valid turn key."""

    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return None


def verify_service_turn_receipt(
    snapshot: UsageTurnSnapshot,
    receipt: Mapping[str, Any],
    process: Mapping[str, Any],
    outcome: str,
) -> tuple[str, str]:
    """Bind a private native receipt to the recorded process and managed request."""

    session_id = snapshot.provider_session_id
    native_turn_id = text_id(receipt.get("native_turn_id"))
    incarnation = snapshot.metadata.get("service_incarnation")
    pid = process.get("child_pid")
    birth = process.get("child_birth_token")
    if (
        type(receipt.get("version")) is not int
        or receipt["version"] != 1
        or receipt.get("agent_id") != snapshot.agent_id
        or receipt.get("runtime_session_id") != snapshot.runtime_session_id
        or receipt.get("request_id") != snapshot.turn_id
        or not snapshot.generation_id
        or receipt.get("generation_id") != snapshot.generation_id
        or not incarnation
        or receipt.get("service_incarnation") != incarnation
        or not session_id
        or receipt.get("native_session_id") != session_id
        or native_turn_id is None
        or receipt.get("terminal") != outcome
        or type(pid) is not int
        or pid <= 0
        or receipt.get("process_id") != pid
        or not isinstance(birth, str)
        or not birth
        or receipt.get("process_birth_token") != birth
    ):
        raise ValueError("Native accounting receipt does not match the managed request")
    return session_id, native_turn_id


def number(value: Any) -> UsageNumber | None:
    """Read a finite nonnegative numeric measurement without coercing absence."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if value >= 0 and math.isfinite(value) else None


def counters(
    usage: Mapping[str, Any], aliases: Mapping[str, tuple[str, ...]]
) -> dict[str, UsageNumber | None]:
    """Project known counter aliases while preserving explicitly missing values."""

    result: dict[str, UsageNumber | None] = {}
    for target, names in aliases.items():
        for name in names:
            if name in usage:
                value = number(usage[name])
                # Token counts are integral even when another metric permits floats.
                result[target] = value if isinstance(value, int) else None
                break
    return result


def timestamp(payload: Mapping[str, Any]) -> str | None:
    """Normalize provider timestamps only when they are explicitly reported."""

    value = payload.get("timestamp")
    if isinstance(value, str):
        return value
    time_value = payload.get("time")
    value = time_value if time_value is not None else value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            seconds = value / 1000 if time_value is not None else value
            return datetime.fromtimestamp(seconds, UTC).isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    return None


def stable_key(*parts: Any) -> str:
    """Hash structured identities into a stable non-content-bearing key."""

    encoded = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()[:32]


def observation(
    state: UsageAdapterState,
    context: UsageParseContext,
    payload: Mapping[str, Any],
    *,
    event_type: str,
    kind: str = "request",
    scope: UsageScope = "request",
    values: dict[str, UsageNumber | None] | None = None,
    request_id: str | None = None,
    accounting: dict[str, Any] | None = None,
    semantics: UsageTokenSemantics | None = None,
    coverage: UsageCoverage = "complete",
    lifecycle: str | None = None,
    accounting_kind: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> UsageObservation:
    """Build one scoped observation without retaining conversation content."""

    source_ref = (
        context.source_ref
        if re.fullmatch(r"source-[0-9a-f]{24}:[0-9]+", context.source_ref)
        else opaque_usage_reference(context.source_ref)
    )
    values = values or {}
    profile = state.profile_id or (
        f"{state.provider}-{state.provider_version}-v1"
        if state.provider_version and state.qualified_version
        else f"{state.provider}-structured-v1"
        if state.qualified_version
        else f"{state.provider}-unqualified-version-v1"
    )
    if not state.qualified_version and kind != "lifecycle":
        scope = "unknown"
        coverage = "unknown"
        semantics = UsageTokenSemantics()
        metadata = {**(metadata or {}), "qualification": "unsupported_client_version"}
    identifier = "observation-" + stable_key(
        state.provider,
        state.provider_session_id,
        state.provider_turn_id,
        context.source_kind,
        source_ref,
        event_type,
        request_id,
        values,
        timestamp(payload),
        lifecycle,
    )
    return UsageObservation(
        observation_id=identifier,
        provider=state.provider,
        provider_session_id=state.provider_session_id,
        provider_turn_id=state.provider_turn_id,
        request_id=request_id,
        turn_id=context.turn_id,
        binding_id=context.binding_id,
        source_kind=context.source_kind,
        source_ref=source_ref,
        profile_id=profile,
        provider_event_type=event_type,
        provider_version=state.provider_version,
        kind=kind,  # type: ignore[arg-type]
        accounting_kind=accounting_kind,
        measurement_scope=scope,
        values=values,
        token_semantics=semantics or UsageTokenSemantics(),
        accounting=accounting or {},
        lifecycle=lifecycle,  # type: ignore[arg-type]
        timestamp_utc=timestamp(payload),
        model=state.model,
        is_sidechain=bool(payload.get("isSidechain", False)),
        coverage=coverage,
        metadata=metadata or {},
    )


def lifecycle_observation(
    state: UsageAdapterState,
    context: UsageParseContext,
    payload: Mapping[str, Any],
    event_type: str,
    lifecycle: str,
) -> UsageObservation:
    """Build a structured start or terminal marker with no invented counters."""

    return observation(
        state,
        context,
        payload,
        event_type=event_type,
        kind="lifecycle",
        scope="turn",
        lifecycle=lifecycle,
        accounting_kind="turn_" + lifecycle,
        metadata={
            "baseline": dict(state.previous_totals),
            "baseline_source_ids": dict(state.previous_total_source_ids),
        }
        if lifecycle == "started"
        else {},
    )
