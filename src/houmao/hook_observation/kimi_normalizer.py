"""Normalize raw Kimi Code hook events into provider-neutral observations.

Kimi delivers 20 PascalCase event families over the same collector transport
as Claude and Codex, but its correlation contract differs in four ways this
normalizer owns:

- ``UserPromptSubmit`` arms a turn epoch and the following
  ``TurnStarted(origin_kind=user)`` binds the integer, session-scoped
  ``turn_id``; tool events, ``Stop``, and ``UserPromptSubmit`` carry no turn
  identifier and attribute to the armed epoch by arrival order.
- ``prompt`` on ``UserPromptSubmit`` and ``UserPromptQueued`` arrives as a
  ``ContentPart[]`` array; the observation carries the joined text and the
  part count, while the part types stay visible in
  :attr:`KimiEventNormalizer.summary`.
- ``tool_call_id`` pairs ``PreToolUse`` with ``PostToolUse``,
  ``PostToolUseFailure``, and the permission events directly, with no
  pair-back heuristic.
- ``UserPromptQueued`` is queue evidence only. Steered input never produces
  a second ``UserPromptSubmit``, so it cannot arm a second epoch.

Subagent activity (``SubagentStart``/``SubagentStop`` and the nested
``TurnStarted(origin_kind=system_trigger)``) is marked as scope evidence, and
``SessionHeartbeat`` is liveness evidence only. Tool input, tool output,
assistant responses, and subagent prompts are never copied into an
observation. Unknown event names are tolerated and counted; the families the
supported floor never dispatches are reported as unavailable in
:attr:`KimiEventNormalizer.summary`.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from houmao.hook_observation.kimi_hooks_generator import KIMI_EVENTS
from houmao.hook_observation.models import (
    HookEventEnvelope,
    HookObservation,
    NormalizedHookKind,
)
from houmao.hook_observation.normalizer import ERROR_CLASS_MAX_CHARS, MAX_PROVIDER_EVENT_BYTES


KIMI_SILENT_FLOOR_FAMILIES: tuple[str, ...] = (
    "StopFailure",
    "TaskStarted",
    "Notification",
)
KIMI_TOLERATED_FAMILIES: frozenset[str] = frozenset({"TaskStarted", "Notification"})
PERMISSION_DECISION_MAX_CHARS = 32
_LABEL_MAX_CHARS = 64
_DEFAULT_OPEN_TOOL_CAPACITY = 256

_KIMI_EVENT_KINDS: dict[str, NormalizedHookKind] = {
    "SessionStart": "session_started",
    "SessionEnd": "session_ended",
    "SessionHeartbeat": "session_heartbeat",
    "UserPromptSubmit": "prompt_submitted",
    "UserPromptQueued": "prompt_queued",
    "TurnStarted": "turn_started",
    "PreToolUse": "tool_started",
    "PostToolUse": "tool_completed",
    "PostToolUseFailure": "tool_failed",
    "PermissionRequest": "permission_requested",
    "PermissionResult": "permission_resolved",
    "Stop": "turn_completed",
    "StopFailure": "turn_failed",
    "Interrupt": "turn_interrupted",
    "PreCompact": "maintenance_started",
    "PostCompact": "maintenance_ended",
    "SubagentStart": "subagent_started",
    "SubagentStop": "subagent_stopped",
}


@dataclass(frozen=True)
class KimiNormalizerSummary:
    """Bounded normalization counters for one Kimi event stream."""

    events_seen: int = 0
    normalized_events: int = 0
    unknown_events: int = 0
    malformed_events: int = 0
    tolerated_family_events: int = 0
    prompt_submissions: int = 0
    content_parts_collapsed: int = 0
    prompt_part_types: tuple[str, ...] = ()
    steer_events: int = 0
    queued_prompts: int = 0
    turn_started_events: int = 0
    nested_turn_events: int = 0
    pre_tool_uses: int = 0
    post_tool_uses: int = 0
    tool_failures: int = 0
    tool_pairs: int = 0
    unpaired_post_tool_uses: int = 0
    permission_requests: int = 0
    permission_pairings: int = 0
    unpaired_permission_requests: int = 0
    permission_results: int = 0
    unexercised_permission_decisions: int = 0
    interrupts: int = 0
    heartbeats: int = 0
    compaction_events: int = 0
    subagent_starts: int = 0
    subagent_stops: int = 0
    unknown_event_names: tuple[str, ...] = ()
    unseen_families: tuple[str, ...] = ()
    unavailable_families: tuple[str, ...] = ()


class KimiEventNormalizer:
    """Stateful Kimi event normalizer for one channel stream.

    One instance consumes one stream in arrival order. It keeps only
    correlation identifiers and bounded counters; provider text is collapsed
    or inspected for equality checks as required by the Kimi contract.
    """

    def __init__(
        self,
        *,
        subscribed_events: Iterable[str] = KIMI_EVENTS,
        open_tool_capacity: int = _DEFAULT_OPEN_TOOL_CAPACITY,
    ) -> None:
        """Initialize an empty normalizer.

        Parameters
        ----------
        subscribed_events:
            Event families the observer subscribes for the supported provider
            floor. Families never seen in the stream are reported as unseen.
        open_tool_capacity:
            Maximum retained ``PreToolUse`` identifiers awaiting their
            completion pair.
        """

        if open_tool_capacity < 1:
            raise ValueError("open_tool_capacity must be positive")
        self.m_subscribed_events: tuple[str, ...] = tuple(subscribed_events)
        self.m_open_tool_capacity: int = open_tool_capacity
        self.m_open_tool_uses: dict[str, str | None] = {}
        self.m_seen_event_names: set[str] = set()
        self.m_unknown_event_counts: dict[str, int] = {}
        self.m_prompt_part_types: set[str] = set()
        self.m_events_seen: int = 0
        self.m_normalized_events: int = 0
        self.m_unknown_events: int = 0
        self.m_malformed_events: int = 0
        self.m_tolerated_family_events: int = 0
        self.m_prompt_submissions: int = 0
        self.m_content_parts_collapsed: int = 0
        self.m_steer_events: int = 0
        self.m_queued_prompts: int = 0
        self.m_turn_started_events: int = 0
        self.m_nested_turn_events: int = 0
        self.m_pre_tool_uses: int = 0
        self.m_post_tool_uses: int = 0
        self.m_tool_failures: int = 0
        self.m_tool_pairs: int = 0
        self.m_unpaired_post_tool_uses: int = 0
        self.m_permission_requests: int = 0
        self.m_permission_pairings: int = 0
        self.m_unpaired_permission_requests: int = 0
        self.m_permission_results: int = 0
        self.m_unexercised_permission_decisions: int = 0
        self.m_interrupts: int = 0
        self.m_heartbeats: int = 0
        self.m_compaction_events: int = 0
        self.m_subagent_starts: int = 0
        self.m_subagent_stops: int = 0

    @property
    def summary(self) -> KimiNormalizerSummary:
        """Return the current counters and family availability."""

        return KimiNormalizerSummary(
            events_seen=self.m_events_seen,
            normalized_events=self.m_normalized_events,
            unknown_events=self.m_unknown_events,
            malformed_events=self.m_malformed_events,
            tolerated_family_events=self.m_tolerated_family_events,
            prompt_submissions=self.m_prompt_submissions,
            content_parts_collapsed=self.m_content_parts_collapsed,
            prompt_part_types=tuple(sorted(self.m_prompt_part_types)),
            steer_events=self.m_steer_events,
            queued_prompts=self.m_queued_prompts,
            turn_started_events=self.m_turn_started_events,
            nested_turn_events=self.m_nested_turn_events,
            pre_tool_uses=self.m_pre_tool_uses,
            post_tool_uses=self.m_post_tool_uses,
            tool_failures=self.m_tool_failures,
            tool_pairs=self.m_tool_pairs,
            unpaired_post_tool_uses=self.m_unpaired_post_tool_uses,
            permission_requests=self.m_permission_requests,
            permission_pairings=self.m_permission_pairings,
            unpaired_permission_requests=self.m_unpaired_permission_requests,
            permission_results=self.m_permission_results,
            unexercised_permission_decisions=self.m_unexercised_permission_decisions,
            interrupts=self.m_interrupts,
            heartbeats=self.m_heartbeats,
            compaction_events=self.m_compaction_events,
            subagent_starts=self.m_subagent_starts,
            subagent_stops=self.m_subagent_stops,
            unknown_event_names=tuple(sorted(self.m_unknown_event_counts)),
            unseen_families=tuple(sorted(set(self.m_subscribed_events) - self.m_seen_event_names)),
            unavailable_families=tuple(
                family
                for family in KIMI_SILENT_FLOOR_FAMILIES
                if family not in self.m_seen_event_names
            ),
        )

    @property
    def unavailable_families(self) -> tuple[str, ...]:
        """Return floor-unavailable families that never appeared in the stream."""

        return self.summary.unavailable_families

    def normalize_envelope(self, envelope: HookEventEnvelope) -> HookObservation:
        """Normalize one store envelope into one posture observation.

        Parameters
        ----------
        envelope:
            Parsed store line. Generation boundary records produce a
            ``generation_started`` observation.

        Returns
        -------
        HookObservation
            Provider-neutral observation carrying the envelope stamps.
        """

        if envelope.is_generation_boundary:
            return HookObservation(
                kind="generation_started",
                event_name="generation_boundary",
                channel_generation=envelope.channel_generation,
                received_at_utc=envelope.received_at_utc,
                sequence=envelope.sequence,
            )
        return self.normalize_provider_event(
            envelope.provider_event,
            channel_generation=envelope.channel_generation,
            received_at_utc=envelope.received_at_utc,
            sequence=envelope.sequence,
        )

    def normalize_provider_event(
        self,
        provider_event: object,
        *,
        channel_generation: int,
        received_at_utc: str,
        sequence: int | None,
    ) -> HookObservation:
        """Normalize one raw Kimi payload.

        Parameters
        ----------
        provider_event:
            Raw provider event value decoded from the store envelope.
        channel_generation:
            Generation stamp from the envelope.
        received_at_utc:
            Receive-time stamp from the envelope.
        sequence:
            Receive-order stamp from the envelope, when present.

        Returns
        -------
        HookObservation
            Normalized observation. Unknown families and malformed payloads
            are returned as counted ``unknown`` observations.
        """

        self.m_events_seen += 1
        if not isinstance(provider_event, dict):
            return self._malformed(
                event_name="<malformed>",
                reason="not_object",
                channel_generation=channel_generation,
                received_at_utc=received_at_utc,
                sequence=sequence,
            )
        size_bytes = _payload_size_bytes(provider_event)
        if size_bytes is None:
            return self._malformed(
                event_name="<malformed>",
                reason="not_serializable",
                channel_generation=channel_generation,
                received_at_utc=received_at_utc,
                sequence=sequence,
            )
        if size_bytes > MAX_PROVIDER_EVENT_BYTES:
            return self._malformed(
                event_name="<oversized>",
                reason="oversized",
                channel_generation=channel_generation,
                received_at_utc=received_at_utc,
                sequence=sequence,
            )
        event_name = provider_event.get("hook_event_name")
        if not isinstance(event_name, str) or not event_name:
            return self._malformed(
                event_name="<malformed>",
                reason="missing_event_name",
                channel_generation=channel_generation,
                received_at_utc=received_at_utc,
                sequence=sequence,
            )

        self.m_seen_event_names.add(event_name)
        turn_id = _turn_id(provider_event.get("turn_id"))
        common: dict[str, Any] = {
            "event_name": event_name,
            "channel_generation": channel_generation,
            "received_at_utc": received_at_utc,
            "sequence": sequence,
            "session_id": _optional_str(provider_event, "session_id"),
            "turn_id": turn_id,
            "prompt_id": _optional_str(provider_event, "prompt_id"),
            "agent_id": _optional_str(provider_event, "agent_id"),
        }
        kind = _KIMI_EVENT_KINDS.get(event_name)
        if kind is None:
            self.m_unknown_events += 1
            self.m_unknown_event_counts[event_name] = (
                self.m_unknown_event_counts.get(event_name, 0) + 1
            )
            if event_name in KIMI_TOLERATED_FAMILIES:
                self.m_tolerated_family_events += 1
            return HookObservation(kind="unknown", **common)

        self.m_normalized_events += 1
        if event_name == "SessionStart":
            return HookObservation(
                kind="session_started",
                **common,
                source=_optional_label(provider_event, "source"),
            )
        if event_name == "SessionEnd":
            return HookObservation(
                kind="session_ended",
                **common,
                reason=_optional_label(provider_event, "reason"),
                turn_state_hint="ended",
            )
        if event_name == "SessionHeartbeat":
            self.m_heartbeats += 1
            return HookObservation(kind="session_heartbeat", **common)
        if event_name == "UserPromptSubmit":
            return self._normalize_prompt_submitted(provider_event, common)
        if event_name == "UserPromptQueued":
            return self._normalize_prompt_queued(provider_event, common)
        if event_name == "TurnStarted":
            return self._normalize_turn_started(provider_event, common)
        if event_name == "PreToolUse":
            return self._normalize_pre_tool_use(provider_event, common)
        if event_name == "PostToolUse":
            return self._normalize_post_tool_use(provider_event, common)
        if event_name == "PostToolUseFailure":
            return self._normalize_post_tool_use_failure(provider_event, common)
        if event_name == "PermissionRequest":
            return self._normalize_permission_request(provider_event, common)
        if event_name == "PermissionResult":
            return self._normalize_permission_result(provider_event, common)
        if event_name == "Stop":
            return HookObservation(
                kind="turn_completed",
                **common,
                turn_state_hint="ended",
                terminal_hint="success",
                stop_hook_active=_optional_bool(provider_event, "stop_hook_active"),
            )
        if event_name == "StopFailure":
            return HookObservation(
                kind="turn_failed",
                **common,
                turn_state_hint="ended",
                terminal_hint="known_failure",
                stop_hook_active=_optional_bool(provider_event, "stop_hook_active"),
                error_class=_error_class(provider_event),
            )
        if event_name == "Interrupt":
            self.m_interrupts += 1
            return HookObservation(
                kind="turn_interrupted",
                **common,
                turn_state_hint="ended",
                terminal_hint="interrupted",
                reason=_optional_label(provider_event, "reason"),
            )
        if event_name == "PreCompact":
            self.m_compaction_events += 1
            return HookObservation(
                kind="maintenance_started",
                **common,
                turn_state_hint="maintenance",
                maintenance_trigger=_optional_label(provider_event, "trigger"),
            )
        if event_name == "PostCompact":
            self.m_compaction_events += 1
            return HookObservation(
                kind="maintenance_ended",
                **common,
                maintenance_trigger=_optional_label(provider_event, "trigger"),
            )
        if event_name == "SubagentStart":
            self.m_subagent_starts += 1
            return HookObservation(
                kind="subagent_started",
                **common,
                agent_name=_optional_label(provider_event, "agent_name"),
            )
        self.m_subagent_stops += 1
        return HookObservation(
            kind="subagent_stopped",
            **common,
            agent_name=_optional_label(provider_event, "agent_name"),
        )

    def _normalize_prompt_submitted(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Collapse a ContentPart[] prompt to text and flag steered input."""

        prompt_text, part_count, part_types = _content_parts(provider_event.get("prompt"))
        if prompt_text is None:
            prompt_text = _optional_str(provider_event, "prompt")
        if part_count is not None:
            self.m_prompt_part_types.update(part_types)
            self.m_content_parts_collapsed += part_count
        self.m_prompt_submissions += 1
        steer = _optional_bool(provider_event, "is_steer") is True
        if steer:
            self.m_steer_events += 1
        return HookObservation(
            kind="prompt_submitted",
            **common,
            steer=steer,
            prompt_text=prompt_text,
            prompt_part_count=part_count,
            turn_state_hint="active",
        )

    def _normalize_prompt_queued(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Record queue evidence without arming a second turn epoch."""

        self.m_queued_prompts += 1
        return HookObservation(
            kind="prompt_queued",
            **common,
            queue_length=_optional_int(provider_event, "queue_length"),
        )

    def _normalize_turn_started(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Carry the integer turn identifier and the turn origin."""

        origin_kind = _optional_label(provider_event, "origin_kind")
        origin_name = _optional_label(provider_event, "origin_name")
        self.m_turn_started_events += 1
        if origin_kind == "system_trigger" or origin_name == "subagent":
            self.m_nested_turn_events += 1
        return HookObservation(
            kind="turn_started",
            **common,
            prompt_text=_optional_str(provider_event, "prompt"),
            origin_kind=origin_kind,
            origin_name=origin_name,
            turn_state_hint="active",
        )

    def _normalize_pre_tool_use(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Record one open tool call keyed by ``tool_call_id``."""

        self.m_pre_tool_uses += 1
        tool_use_id = _optional_str(provider_event, "tool_call_id")
        self._note_open_tool_use(tool_use_id)
        return HookObservation(
            kind="tool_started",
            **common,
            tool_name=_optional_str(provider_event, "tool_name"),
            tool_use_id=tool_use_id,
            turn_state_hint="active",
        )

    def _normalize_post_tool_use(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Close the ``PreToolUse`` pair for one completed tool call."""

        self.m_post_tool_uses += 1
        tool_use_id = _optional_str(provider_event, "tool_call_id")
        self._consume_tool_call(tool_use_id)
        return HookObservation(
            kind="tool_completed",
            **common,
            tool_name=_optional_str(provider_event, "tool_name"),
            tool_use_id=tool_use_id,
            turn_state_hint="active",
        )

    def _normalize_post_tool_use_failure(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Record a failed tool call as non-terminal turn evidence."""

        self.m_tool_failures += 1
        tool_use_id = _optional_str(provider_event, "tool_call_id")
        self._consume_tool_call(tool_use_id)
        return HookObservation(
            kind="tool_failed",
            **common,
            tool_name=_optional_str(provider_event, "tool_name"),
            tool_use_id=tool_use_id,
            error_class=_error_class(provider_event),
            turn_state_hint="active",
        )

    def _normalize_permission_request(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Pair one permission wait with its open tool call by identifier."""

        self.m_permission_requests += 1
        tool_use_id = _optional_str(provider_event, "tool_call_id")
        if tool_use_id is not None and tool_use_id in self.m_open_tool_uses:
            self.m_permission_pairings += 1
        else:
            self.m_unpaired_permission_requests += 1
        return HookObservation(
            kind="permission_requested",
            **common,
            tool_name=_optional_str(provider_event, "tool_name"),
            tool_use_id=tool_use_id,
            turn_state_hint="blocked",
        )

    def _normalize_permission_result(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Carry the permission decision that settles the blocked window."""

        self.m_permission_results += 1
        decision = _bounded_label(provider_event.get("decision"), PERMISSION_DECISION_MAX_CHARS)
        if decision not in ("approved", "rejected"):
            self.m_unexercised_permission_decisions += 1
        return HookObservation(
            kind="permission_resolved",
            **common,
            tool_name=_optional_str(provider_event, "tool_name"),
            tool_use_id=_optional_str(provider_event, "tool_call_id"),
            permission_decision=decision,
            turn_state_hint="active",
        )

    def _note_open_tool_use(self, tool_use_id: str | None) -> None:
        """Remember one open tool call within the bounded pairing window."""

        if tool_use_id is None:
            return
        if tool_use_id in self.m_open_tool_uses:
            del self.m_open_tool_uses[tool_use_id]
        if len(self.m_open_tool_uses) >= self.m_open_tool_capacity:
            oldest = next(iter(self.m_open_tool_uses))
            del self.m_open_tool_uses[oldest]
        self.m_open_tool_uses[tool_use_id] = None

    def _consume_tool_call(self, tool_use_id: str | None) -> None:
        """Pair a completion or failure with its pending ``PreToolUse``."""

        if tool_use_id is not None and tool_use_id in self.m_open_tool_uses:
            self.m_tool_pairs += 1
            del self.m_open_tool_uses[tool_use_id]
            return
        self.m_unpaired_post_tool_uses += 1

    def _malformed(
        self,
        *,
        event_name: str,
        reason: str,
        channel_generation: int,
        received_at_utc: str,
        sequence: int | None,
    ) -> HookObservation:
        """Build and count one malformed observation."""

        self.m_malformed_events += 1
        return HookObservation(
            kind="unknown",
            event_name=event_name,
            channel_generation=channel_generation,
            received_at_utc=received_at_utc,
            sequence=sequence,
            malformed=True,
            malformed_reason=reason,
        )


def _payload_size_bytes(provider_event: dict[str, Any]) -> int | None:
    """Return the compact JSON size of one provider payload."""

    try:
        encoded = json.dumps(
            provider_event,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return len(encoded)


def _optional_str(payload: dict[str, Any], key: str) -> str | None:
    """Return one non-empty string field or ``None``."""

    value = payload.get(key)
    if not isinstance(value, str) or not value:
        return None
    return value


def _optional_bool(payload: dict[str, Any], key: str) -> bool | None:
    """Return one boolean field or ``None`` when absent or mistyped."""

    value = payload.get(key)
    return value if isinstance(value, bool) else None


def _optional_int(payload: dict[str, Any], key: str) -> int | None:
    """Return one integer field, accepting a numeric string defensively."""

    value = payload.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _turn_id(value: object) -> str | None:
    """Return Kimi's integer ``turn_id`` as a canonical decimal string."""

    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        try:
            return str(int(value))
        except ValueError:
            return None
    return None


def _optional_label(payload: dict[str, Any], key: str) -> str | None:
    """Return one bounded enum-shaped label field."""

    return _bounded_label(payload.get(key), _LABEL_MAX_CHARS)


def _bounded_label(value: object, max_chars: int) -> str | None:
    """Return a short label value, replacing message-shaped values."""

    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) > max_chars:
        return "unclassified"
    return text


def _content_parts(value: object) -> tuple[str | None, int | None, tuple[str, ...]]:
    """Collapse one ContentPart[] prompt to joined text and shape evidence."""

    if isinstance(value, str):
        return (value or None), None, ()
    if not isinstance(value, list):
        return None, None, ()
    pieces: list[str] = []
    part_types: list[str] = []
    for part in value:
        if not isinstance(part, dict):
            part_types.append("unknown")
            continue
        part_type = part.get("type")
        part_types.append(part_type if isinstance(part_type, str) and part_type else "unknown")
        text = part.get("text")
        if isinstance(text, str):
            pieces.append(text)
    joined = "".join(pieces)
    return (joined or None), len(value), tuple(part_types)


def _error_class(payload: dict[str, Any]) -> str | None:
    """Extract one bounded error class from a failure payload."""

    for key in ("error", "error_type", "error_details"):
        class_name = _error_class_from_value(payload.get(key))
        if class_name is not None:
            return class_name
    return None


def _error_class_from_value(value: object) -> str | None:
    """Extract an error class from one string or structured error field."""

    if isinstance(value, str):
        return _bounded_label(value, ERROR_CLASS_MAX_CHARS)
    if isinstance(value, dict):
        for key in ("code", "type", "error_type", "name", "failure_class"):
            candidate = value.get(key)
            if isinstance(candidate, str):
                return _bounded_label(candidate, ERROR_CLASS_MAX_CHARS)
    return None
