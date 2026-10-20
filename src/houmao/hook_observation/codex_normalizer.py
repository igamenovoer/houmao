"""Normalize raw Codex hook events into provider-neutral observations.

Codex delivers PascalCase event names with the same envelope conventions as
Claude and adds a per-turn ``turn_id``. This normalizer is stateful because two
Codex correlations are only decidable in arrival order:

- a second ``UserPromptSubmit`` carrying the running turn's identifier is
  steered input, not a new turn epoch;
- ``PermissionRequest`` has no ``tool_use_id`` and pairs back to the
  immediately preceding ``PreToolUse`` in the same turn with an equal tool
  name, verified by ``tool_input.command`` equality.

The normalizer never copies prompt text, tool input, tool output, or assistant
message text into an observation. Unknown event names are tolerated and
counted, and the families the supported floor never dispatches are reported as
unavailable (minus any that did fire) in
:meth:`CodexEventNormalizer.summary`.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from houmao.hook_observation.codex_hooks_generator import CODEX_EVENTS
from houmao.hook_observation.models import (
    HookEventEnvelope,
    HookObservation,
    NormalizedHookKind,
)
from houmao.hook_observation.normalizer import MAX_PROVIDER_EVENT_BYTES


_CODEX_EVENT_KINDS: dict[str, NormalizedHookKind] = {
    "SessionStart": "session_started",
    "UserPromptSubmit": "prompt_submitted",
    "PreToolUse": "tool_started",
    "PostToolUse": "tool_completed",
    "PermissionRequest": "permission_requested",
    "Stop": "turn_completed",
    "Interrupt": "turn_interrupted",
    "PreCompact": "maintenance_started",
    "PostCompact": "maintenance_ended",
    "SessionEnd": "session_ended",
}
CODEX_UNAVAILABLE_FLOOR_FAMILIES: tuple[str, ...] = (
    "PostModelRequest",
    "PreModelRequest",
    "SubagentStart",
    "SubagentStop",
)
_DEFAULT_OPEN_TOOL_CAPACITY = 256


@dataclass(frozen=True)
class CodexNormalizerSummary:
    """Bounded normalization counters for one Codex event stream."""

    events_seen: int = 0
    normalized_events: int = 0
    unknown_events: int = 0
    malformed_events: int = 0
    steer_events: int = 0
    permission_requests: int = 0
    permission_pairings: int = 0
    unpaired_permission_requests: int = 0
    unpaired_post_tool_uses: int = 0
    unknown_event_names: tuple[str, ...] = ()
    unseen_families: tuple[str, ...] = ()
    unavailable_families: tuple[str, ...] = ()


@dataclass(frozen=True)
class _PendingToolUse:
    """The immediately preceding PreToolUse, used to pair PermissionRequest."""

    turn_id: str | None
    tool_name: str | None
    tool_use_id: str | None
    command: str | None


class CodexEventNormalizer:
    """Stateful Codex event normalizer for one channel stream.

    One instance consumes one stream in arrival order. It keeps only
    correlation identifiers and bounded counters; provider text is inspected
    for equality checks and discarded immediately.
    """

    def __init__(
        self,
        *,
        subscribed_events: Iterable[str] = CODEX_EVENTS,
        open_tool_capacity: int = _DEFAULT_OPEN_TOOL_CAPACITY,
    ) -> None:
        """Initialize an empty normalizer.

        Parameters
        ----------
        subscribed_events:
            Event families the observer subscribes for the supported provider
            floor. Families never seen in the stream are reported as
            unavailable.
        open_tool_capacity:
            Maximum retained ``PreToolUse`` identifiers awaiting their
            ``PostToolUse`` pair.
        """

        if open_tool_capacity < 1:
            raise ValueError("open_tool_capacity must be positive")
        self.m_subscribed_events: tuple[str, ...] = tuple(subscribed_events)
        self.m_open_tool_capacity: int = open_tool_capacity
        self.m_turn_id: str | None = None
        self.m_last_pre_tool_use: _PendingToolUse | None = None
        self.m_open_tool_uses: dict[str, str | None] = {}
        self.m_seen_event_names: set[str] = set()
        self.m_unknown_event_counts: dict[str, int] = {}
        self.m_events_seen: int = 0
        self.m_normalized_events: int = 0
        self.m_unknown_events: int = 0
        self.m_malformed_events: int = 0
        self.m_steer_events: int = 0
        self.m_permission_requests: int = 0
        self.m_permission_pairings: int = 0
        self.m_unpaired_permission_requests: int = 0
        self.m_unpaired_post_tool_uses: int = 0

    @property
    def summary(self) -> CodexNormalizerSummary:
        """Return the current counters and family availability."""

        return CodexNormalizerSummary(
            events_seen=self.m_events_seen,
            normalized_events=self.m_normalized_events,
            unknown_events=self.m_unknown_events,
            malformed_events=self.m_malformed_events,
            steer_events=self.m_steer_events,
            permission_requests=self.m_permission_requests,
            permission_pairings=self.m_permission_pairings,
            unpaired_permission_requests=self.m_unpaired_permission_requests,
            unpaired_post_tool_uses=self.m_unpaired_post_tool_uses,
            unknown_event_names=tuple(sorted(self.m_unknown_event_counts)),
            unseen_families=tuple(sorted(set(self.m_subscribed_events) - self.m_seen_event_names)),
            unavailable_families=tuple(
                family
                for family in CODEX_UNAVAILABLE_FLOOR_FAMILIES
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
        """Normalize one raw Codex payload.

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
        turn_id = _optional_str(provider_event, "turn_id")
        common: dict[str, Any] = {
            "event_name": event_name,
            "channel_generation": channel_generation,
            "received_at_utc": received_at_utc,
            "sequence": sequence,
            "session_id": _optional_str(provider_event, "session_id"),
            "turn_id": turn_id,
            "prompt_id": turn_id,
            "agent_id": _optional_str(provider_event, "agent_id"),
        }
        kind = _CODEX_EVENT_KINDS.get(event_name)
        if kind is None:
            self.m_unknown_events += 1
            self.m_unknown_event_counts[event_name] = (
                self.m_unknown_event_counts.get(event_name, 0) + 1
            )
            return HookObservation(kind="unknown", **common)

        self.m_normalized_events += 1
        if event_name == "SessionStart":
            return self._normalize_session_start(provider_event, common)
        if event_name == "UserPromptSubmit":
            return self._normalize_prompt_submitted(provider_event, common)
        if event_name == "PreToolUse":
            return self._normalize_pre_tool_use(provider_event, common)
        if event_name == "PostToolUse":
            return self._normalize_post_tool_use(provider_event, common)
        if event_name == "PermissionRequest":
            return self._normalize_permission_request(provider_event, common)
        if event_name == "Stop":
            return self._normalize_stop(provider_event, common)
        if event_name == "Interrupt":
            self._clear_turn_correlation()
            return HookObservation(
                kind="turn_interrupted",
                **common,
                turn_state_hint="ended",
                terminal_hint="interrupted",
            )
        if event_name == "PreCompact":
            return HookObservation(
                kind="maintenance_started",
                **common,
                turn_state_hint="maintenance",
                maintenance_trigger=_optional_str(provider_event, "trigger"),
            )
        if event_name == "PostCompact":
            return HookObservation(
                kind="maintenance_ended",
                **common,
                maintenance_trigger=_optional_str(provider_event, "trigger"),
            )
        self._clear_turn_correlation()
        return HookObservation(
            kind="session_ended",
            **common,
            turn_state_hint="ended",
        )

    def _normalize_session_start(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Map SessionStart and reset turn correlation for the new context."""

        self._clear_turn_correlation()
        return HookObservation(
            kind="session_started",
            **common,
            source=_optional_str(provider_event, "source"),
        )

    def _normalize_prompt_submitted(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Map UserPromptSubmit and classify a same-turn repeat as a steer."""

        del provider_event
        turn_id: str | None = common["turn_id"]
        steer = turn_id is not None and turn_id == self.m_turn_id
        if steer:
            self.m_steer_events += 1
        else:
            self.m_turn_id = turn_id
            self._clear_tool_correlation()
        return HookObservation(
            kind="prompt_submitted",
            **common,
            steer=steer,
            turn_state_hint="active",
        )

    def _normalize_pre_tool_use(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Record the tool call a following PermissionRequest pairs with."""

        tool_use_id = _optional_str(provider_event, "tool_use_id")
        self.m_last_pre_tool_use = _PendingToolUse(
            turn_id=common["turn_id"],
            tool_name=_optional_str(provider_event, "tool_name"),
            tool_use_id=tool_use_id,
            command=_tool_command(provider_event),
        )
        self._note_open_tool_use(tool_use_id, common["turn_id"])
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
        """Close the PreToolUse pair for one completed tool call."""

        tool_use_id = _optional_str(provider_event, "tool_use_id")
        if tool_use_id is None or tool_use_id not in self.m_open_tool_uses:
            self.m_unpaired_post_tool_uses += 1
        else:
            del self.m_open_tool_uses[tool_use_id]
        return HookObservation(
            kind="tool_completed",
            **common,
            tool_name=_optional_str(provider_event, "tool_name"),
            tool_use_id=tool_use_id,
            turn_state_hint="active",
        )

    def _normalize_permission_request(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Pair a request, which carries no tool-use id, to its PreToolUse."""

        self.m_permission_requests += 1
        tool_name = _optional_str(provider_event, "tool_name")
        paired = self.m_last_pre_tool_use
        paired_tool_use_id: str | None = None
        if (
            paired is not None
            and paired.turn_id == common["turn_id"]
            and paired.tool_name == tool_name
            and paired.command == _tool_command(provider_event)
        ):
            self.m_permission_pairings += 1
            paired_tool_use_id = paired.tool_use_id
        else:
            self.m_unpaired_permission_requests += 1
        return HookObservation(
            kind="permission_requested",
            **common,
            tool_name=tool_name,
            tool_use_id=paired_tool_use_id,
            turn_state_hint="blocked",
        )

    def _normalize_stop(
        self,
        provider_event: dict[str, Any],
        common: dict[str, Any],
    ) -> HookObservation:
        """Map Stop, keeping correlation when a hook continued the turn."""

        stop_hook_active = _optional_bool(provider_event, "stop_hook_active")
        if stop_hook_active is not True:
            self._clear_turn_correlation()
        return HookObservation(
            kind="turn_completed",
            **common,
            turn_state_hint="ended",
            terminal_hint="success",
            stop_hook_active=stop_hook_active,
            last_assistant_message_present=_message_present(provider_event),
        )

    def _note_open_tool_use(self, tool_use_id: str | None, turn_id: str | None) -> None:
        """Remember one open tool call within the bounded pairing window."""

        if tool_use_id is None:
            return
        if tool_use_id in self.m_open_tool_uses:
            del self.m_open_tool_uses[tool_use_id]
        if len(self.m_open_tool_uses) >= self.m_open_tool_capacity:
            oldest = next(iter(self.m_open_tool_uses))
            del self.m_open_tool_uses[oldest]
        self.m_open_tool_uses[tool_use_id] = turn_id

    def _clear_tool_correlation(self) -> None:
        """Drop pending PreToolUse pairing state for the previous turn."""

        self.m_last_pre_tool_use = None
        self.m_open_tool_uses.clear()

    def _clear_turn_correlation(self) -> None:
        """Drop the running turn and its tool pairing state."""

        self.m_turn_id = None
        self._clear_tool_correlation()

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
    if not isinstance(value, bool):
        return None
    return value


def _tool_command(payload: dict[str, Any]) -> str | None:
    """Return the shell command from a tool payload, when present."""

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    return _optional_str(tool_input, "command")


def _message_present(payload: dict[str, Any]) -> bool | None:
    """Return whether a final assistant message carries text, never the text."""

    value = payload.get("last_assistant_message")
    if not isinstance(value, str):
        return None
    return bool(value)
