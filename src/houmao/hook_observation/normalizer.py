"""Normalize raw Claude hook events into provider-neutral observations.

The normalizer is deliberately tolerant: unknown event names become
``unknown`` observations, malformed payloads become counted ``malformed``
observations, and unknown provider fields are ignored. Text-bearing fields
such as prompts, tool inputs, tool responses, and assistant messages are
never copied into the observation.
"""

from __future__ import annotations

import json
from typing import Any

from houmao.hook_observation.models import (
    HookBackgroundTask,
    HookEventEnvelope,
    HookObservation,
)


MAX_PROVIDER_EVENT_BYTES = 1 << 20
ERROR_CLASS_MAX_CHARS = 80


def normalize_envelope(envelope: HookEventEnvelope) -> HookObservation:
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
    return normalize_provider_event(
        envelope.provider_event,
        channel_generation=envelope.channel_generation,
        received_at_utc=envelope.received_at_utc,
        sequence=envelope.sequence,
    )


def normalize_provider_event(
    provider_event: object,
    *,
    channel_generation: int,
    received_at_utc: str,
    sequence: int | None,
) -> HookObservation:
    """Normalize one raw provider payload.

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
        Normalized observation. Unknown and malformed payloads are returned
        as ``unknown`` observations with counters-visible flags.
    """

    if not isinstance(provider_event, dict):
        return _malformed_observation(
            event_name="<malformed>",
            reason="not_object",
            channel_generation=channel_generation,
            received_at_utc=received_at_utc,
            sequence=sequence,
        )
    size_bytes = _payload_size_bytes(provider_event)
    if size_bytes is None:
        return _malformed_observation(
            event_name="<malformed>",
            reason="not_serializable",
            channel_generation=channel_generation,
            received_at_utc=received_at_utc,
            sequence=sequence,
        )
    if size_bytes > MAX_PROVIDER_EVENT_BYTES:
        return _malformed_observation(
            event_name="<oversized>",
            reason="oversized",
            channel_generation=channel_generation,
            received_at_utc=received_at_utc,
            sequence=sequence,
        )
    event_name = provider_event.get("hook_event_name")
    if not isinstance(event_name, str) or not event_name:
        return _malformed_observation(
            event_name="<malformed>",
            reason="missing_event_name",
            channel_generation=channel_generation,
            received_at_utc=received_at_utc,
            sequence=sequence,
        )

    session_id = _optional_str(provider_event, "session_id")
    prompt_id = _optional_str(provider_event, "prompt_id")
    tool_name = _optional_str(provider_event, "tool_name")
    tool_use_id = _optional_str(provider_event, "tool_use_id")
    common: dict[str, Any] = {
        "event_name": event_name,
        "channel_generation": channel_generation,
        "received_at_utc": received_at_utc,
        "sequence": sequence,
        "session_id": session_id,
        "prompt_id": prompt_id,
    }

    if event_name == "SessionStart":
        return HookObservation(
            kind="session_started",
            **common,
            source=_optional_str(provider_event, "source"),
        )
    if event_name == "UserPromptSubmit":
        return HookObservation(
            kind="prompt_submitted",
            **common,
            turn_state_hint="active",
            provider_initiated=_is_task_notification(provider_event.get("prompt")),
        )
    if event_name == "PermissionRequest":
        return HookObservation(
            kind="permission_requested",
            **common,
            tool_name=tool_name,
            turn_state_hint="blocked",
        )
    if event_name == "PostToolUse":
        return HookObservation(
            kind="activity",
            **common,
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            turn_state_hint="active",
        )
    if event_name == "PostToolUseFailure":
        return HookObservation(
            kind="activity",
            **common,
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            turn_state_hint="active",
            is_interrupt=_optional_bool(provider_event, "is_interrupt"),
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
    if event_name == "Stop":
        background_tasks, background_work_pending = _background_task_summary(
            provider_event.get("background_tasks")
        )
        return HookObservation(
            kind="turn_completed",
            **common,
            turn_state_hint="ended",
            terminal_hint="success",
            background_tasks=background_tasks,
            background_work_pending=background_work_pending,
            stop_hook_active=_optional_bool(provider_event, "stop_hook_active"),
            last_assistant_message_present=_message_present(provider_event),
        )
    if event_name == "StopFailure":
        return HookObservation(
            kind="turn_failed",
            **common,
            turn_state_hint="ended",
            terminal_hint="known_failure",
            stop_hook_active=_optional_bool(provider_event, "stop_hook_active"),
            last_assistant_message_present=_message_present(provider_event),
            error_class=_error_class(provider_event),
        )
    return HookObservation(
        kind="unknown",
        **common,
    )


def _malformed_observation(
    *,
    event_name: str,
    reason: str,
    channel_generation: int,
    received_at_utc: str,
    sequence: int | None,
) -> HookObservation:
    """Build one counted malformed observation."""

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


def _is_task_notification(prompt: object) -> bool:
    """Return whether a prompt is a provider-synthesized task notification."""

    if not isinstance(prompt, str):
        return False
    text = prompt.lstrip()
    return text.startswith("<task-notification") and "</task-notification>" in text


def _background_task_summary(
    value: object,
) -> tuple[tuple[HookBackgroundTask, ...], bool | None]:
    """Summarize the ``Stop.background_tasks`` payload array."""

    if not isinstance(value, list):
        return (), None
    tasks: list[HookBackgroundTask] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        tasks.append(
            HookBackgroundTask(
                task_id=_optional_str(item, "id"),
                status=_optional_str(item, "status"),
                task_type=_optional_str(item, "type"),
            )
        )
    return tuple(tasks), len(value) > 0


def _message_present(payload: dict[str, Any]) -> bool | None:
    """Return whether a final assistant message carries text, never the text."""

    value = payload.get("last_assistant_message")
    if not isinstance(value, str):
        return None
    return bool(value)


def _error_class(payload: dict[str, Any]) -> str | None:
    """Extract one bounded provider error class from a failure payload."""

    for key in ("error", "error_details"):
        class_name = _error_class_from_value(payload.get(key))
        if class_name is not None:
            return class_name
    return None


def _error_class_from_value(value: object) -> str | None:
    """Extract an error class from one string or structured error field."""

    if isinstance(value, str):
        return _bounded_error_class(value)
    if isinstance(value, dict):
        for key in ("type", "code", "error_type", "failure_class", "name"):
            candidate = value.get(key)
            if isinstance(candidate, str):
                return _bounded_error_class(candidate)
    return None


def _bounded_error_class(value: str) -> str | None:
    """Return a short error class label, discarding message-shaped values."""

    text = value.strip()
    if not text:
        return None
    if len(text) > ERROR_CLASS_MAX_CHARS:
        return "unclassified"
    return text
