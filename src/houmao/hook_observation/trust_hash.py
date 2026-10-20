"""Codex hook trust hashes and persisted hook-state keys.

Codex trusts a hook handler only when the persisted
``[hooks.state."<key>".trusted_hash]`` equals the handler's current hash
(``codex-rs/hooks/src/engine/discovery.rs``, ``fn hook_hash`` and
``hook_trust_status``). The current hash is built from a normalized identity:

1. ``event_name`` is Codex's snake_case event label.
2. The matcher group keeps its matcher only for events that support matchers
   (``codex-rs/hooks/src/events/common.rs``, ``matcher_pattern_for_event``).
3. The handler list is replaced by the one normalized command handler:
   timeout defaulted and normalized, ``commandWindows`` cleared,
   ``additionalContextLimit`` kept only for context-capable events and only
   when it differs from the 2500-token default.
4. The identity is serialized to TOML and then JSON, all object keys are
   sorted recursively, and the compact JSON bytes are SHA-256 hashed and
   prefixed with ``sha256:`` (``codex-rs/config/src/fingerprint.rs``,
   ``version_for_toml``).

The persisted state key is
``<absolute hooks.json path>:<event_label>:<group_index>:<handler_index>``
(``codex-rs/hooks/src/lib.rs``, ``hook_key``).

The algorithm is pinned to the upstream fixtures in
``codex-rs/config/src/fingerprint_tests.rs`` and
``codex-rs/core/tests/suite/hooks.rs``. Linux and macOS command selection is
assumed: ``command`` wins over ``commandWindows``.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, Final

EVENT_LABELS: Final[dict[str, str]] = {
    "PreModelRequest": "pre_model_request",
    "PostModelRequest": "post_model_request",
    "PreToolUse": "pre_tool_use",
    "PermissionRequest": "permission_request",
    "PostToolUse": "post_tool_use",
    "PreCompact": "pre_compact",
    "PostCompact": "post_compact",
    "SessionStart": "session_start",
    "SessionEnd": "session_end",
    "UserPromptSubmit": "user_prompt_submit",
    "SubagentStart": "subagent_start",
    "SubagentStop": "subagent_stop",
    "Stop": "stop",
    "Interrupt": "interrupt",
}
EVENT_BY_LABEL: Final[dict[str, str]] = {label: event for event, label in EVENT_LABELS.items()}
MATCHER_EVENTS: Final[frozenset[str]] = frozenset(
    {
        "PreToolUse",
        "PermissionRequest",
        "PostToolUse",
        "SessionStart",
        "SessionEnd",
        "SubagentStart",
        "SubagentStop",
        "PreCompact",
        "PostCompact",
    }
)
SESSION_END_LIKE_EVENTS: Final[frozenset[str]] = frozenset({"SessionEnd", "Interrupt"})
ADDITIONAL_CONTEXT_EVENTS: Final[frozenset[str]] = frozenset(
    {
        "PreToolUse",
        "PostToolUse",
        "SessionStart",
        "UserPromptSubmit",
        "SubagentStart",
    }
)
DEFAULT_TIMEOUT_SECONDS: Final[int] = 600
SESSION_END_MAX_TIMEOUT_SECONDS: Final[int] = 3
DEFAULT_ADDITIONAL_CONTEXT_LIMIT: Final[int] = 2500


class HookHashError(ValueError):
    """Raised when a hooks document cannot be normalized like Codex would."""


def canonical_json(value: object) -> str:
    """Serialize a JSON value compactly with all object keys sorted recursively.

    Parameters
    ----------
    value:
        JSON-compatible value to serialize.

    Returns
    -------
    str
        Compact JSON text without insignificant whitespace and with object
        keys sorted at every nesting level.
    """

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_prefixed(value: object) -> str:
    """Return ``sha256:<hex>`` over the canonical JSON encoding of ``value``.

    Parameters
    ----------
    value:
        JSON-compatible value to hash.

    Returns
    -------
    str
        Lowercase hex SHA-256 digest prefixed with ``sha256:``.
    """

    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def resolve_event_name(value: str) -> str:
    """Return the PascalCase event name for either PascalCase or snake_case input.

    Parameters
    ----------
    value:
        Codex event name in PascalCase or its snake_case state label.

    Returns
    -------
    str
        The canonical PascalCase event name.

    Raises
    ------
    HookHashError
        If the event name is unknown.
    """

    if value in EVENT_LABELS:
        return value
    if value in EVENT_BY_LABEL:
        return EVENT_BY_LABEL[value]
    known = ", ".join(EVENT_LABELS)
    raise HookHashError(f"unknown event {value!r}; expected one of: {known}")


def normalize_timeout(event_name: str, timeout: object) -> int:
    """Normalize a handler timeout exactly like ``normalize_command_hook``.

    ``SessionEnd`` and ``Interrupt`` default to 1 s and clamp to 1-3 s; every
    other event defaults to 600 s and floors at 1 s with no upper clamp.

    Parameters
    ----------
    event_name:
        Canonical PascalCase event name.
    timeout:
        Raw ``timeout`` value from the handler declaration; ``None`` when the
        field is absent.

    Returns
    -------
    int
        The normalized timeout in seconds.

    Raises
    ------
    HookHashError
        If ``timeout`` is not a non-negative integer.
    """

    if timeout is None:
        timeout_value = 1 if event_name in SESSION_END_LIKE_EVENTS else DEFAULT_TIMEOUT_SECONDS
    else:
        if isinstance(timeout, bool) or not isinstance(timeout, int):
            raise HookHashError(f"timeout must be an integer, got {timeout!r}")
        if timeout < 0:
            raise HookHashError(f"timeout must be non-negative, got {timeout!r}")
        timeout_value = timeout
    if event_name in SESSION_END_LIKE_EVENTS:
        return min(max(timeout_value, 1), SESSION_END_MAX_TIMEOUT_SECONDS)
    return max(timeout_value, 1)


def normalize_command_handler(event_name: str, handler: Mapping[str, Any]) -> dict[str, Any]:
    """Return Codex's normalized ``HookHandlerConfig::Command`` mapping.

    ``None``-valued optional fields are omitted, matching TOML serialization
    (TOML has no null). ``commandWindows`` is always cleared after Codex
    selects the platform command; on Linux and macOS ``command`` wins.

    Parameters
    ----------
    event_name:
        Canonical PascalCase event name.
    handler:
        Raw command handler declaration.

    Returns
    -------
    dict
        The normalized handler with ``type``, ``command``, ``timeout``,
        ``async``, and any retained optional fields.

    Raises
    ------
    HookHashError
        If the handler is not a supported command handler or carries invalid
        field values.
    """

    handler_type = handler.get("type")
    if handler_type != "command":
        raise HookHashError(
            f"unsupported handler type {handler_type!r}; only command handlers are supported"
        )
    command = handler.get("command")
    if not isinstance(command, str):
        raise HookHashError(f"command must be a string, got {command!r}")
    if not command.strip():
        raise HookHashError("empty hook commands are skipped by Codex and cannot be hashed")

    async_value = handler.get("async", False)
    if not isinstance(async_value, bool):
        raise HookHashError(f"async must be a boolean, got {async_value!r}")

    normalized: dict[str, Any] = {
        "type": "command",
        "command": command,
        "timeout": normalize_timeout(event_name, handler.get("timeout")),
        "async": async_value,
    }

    status_message = handler.get("statusMessage")
    if status_message is not None:
        if not isinstance(status_message, str):
            raise HookHashError(f"statusMessage must be a string, got {status_message!r}")
        normalized["statusMessage"] = status_message

    limit = handler.get("additionalContextLimit")
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise HookHashError(
                f"additionalContextLimit must be a non-negative integer, got {limit!r}"
            )
        if event_name in ADDITIONAL_CONTEXT_EVENTS and limit != DEFAULT_ADDITIONAL_CONTEXT_LIMIT:
            normalized["additionalContextLimit"] = limit

    return normalized


def normalize_matcher(event_name: str, matcher: object) -> str | None:
    """Return the matcher Codex keeps in the identity for one event.

    Parameters
    ----------
    event_name:
        Canonical PascalCase event name.
    matcher:
        Raw matcher value from the declaration; ``None`` when absent.

    Returns
    -------
    str or None
        The matcher for matcher-capable events, otherwise ``None``. An
        explicit empty matcher is significant and is preserved.

    Raises
    ------
    HookHashError
        If ``matcher`` is neither a string nor ``None``.
    """

    if matcher is not None and not isinstance(matcher, str):
        raise HookHashError(f"matcher must be a string or null, got {matcher!r}")
    if event_name not in MATCHER_EVENTS:
        return None
    return matcher


def build_identity(event_name: str, matcher: object, handler: Mapping[str, Any]) -> dict[str, Any]:
    """Build the normalized identity Codex hashes for one handler.

    Parameters
    ----------
    event_name:
        Event name in PascalCase or snake_case.
    matcher:
        Matcher value from the handler's group.
    handler:
        Raw command handler declaration.

    Returns
    -------
    dict
        ``{"event_name": <snake_case label>, "hooks": [<handler>]}`` plus
        ``matcher`` only when the event keeps matchers and one is present.
    """

    resolved_event = resolve_event_name(event_name)
    identity: dict[str, Any] = {
        "event_name": EVENT_LABELS[resolved_event],
        "hooks": [normalize_command_handler(resolved_event, handler)],
    }
    normalized_matcher = normalize_matcher(resolved_event, matcher)
    if normalized_matcher is not None:
        identity["matcher"] = normalized_matcher
    return identity


def hook_hash(event_name: str, matcher: object, handler: Mapping[str, Any]) -> str:
    """Return the ``sha256:`` trust hash for one normalized handler.

    Parameters
    ----------
    event_name:
        Event name in PascalCase or snake_case.
    matcher:
        Matcher value from the handler's group.
    handler:
        Raw command handler declaration.

    Returns
    -------
    str
        Trust hash in Codex's persisted format.
    """

    return sha256_prefixed(build_identity(event_name, matcher, handler))


def hook_state_key(
    hooks_json_path: Path | str,
    event_name: str,
    group_index: int,
    handler_index: int,
) -> str:
    """Return Codex's persisted hook-state key for one handler.

    Parameters
    ----------
    hooks_json_path:
        Path of the ``hooks.json`` document that owns the handler. Relative
        paths are made absolute without resolving symlinks, matching Codex's
        key source.
    event_name:
        Event name in PascalCase or snake_case.
    group_index:
        Zero-based matcher-group index within the event.
    handler_index:
        Zero-based handler index within the matcher group.

    Returns
    -------
    str
        ``<absolute hooks.json path>:<event_label>:<group>:<handler>``.
    """

    resolved_event = resolve_event_name(event_name)
    return (
        f"{os.path.abspath(os.fspath(hooks_json_path))}:"
        f"{EVENT_LABELS[resolved_event]}:{group_index}:{handler_index}"
    )


def iter_handlers(
    document: Mapping[str, Any],
) -> Iterator[tuple[str, int, int, object, Mapping[str, Any]]]:
    """Yield ``(event, group_index, handler_index, matcher, handler)`` in file order.

    Parameters
    ----------
    document:
        Parsed ``hooks.json`` document carrying a ``hooks`` mapping.

    Yields
    ------
    tuple
        One tuple per handler, with the canonical PascalCase event name and
        the raw group matcher.

    Raises
    ------
    HookHashError
        If the document or any matcher group has an invalid shape or an
        unknown event name.
    """

    hooks = document.get("hooks")
    if not isinstance(hooks, Mapping):
        raise HookHashError("hooks JSON must contain an object under 'hooks'")
    for raw_event, groups_value in hooks.items():
        event_name = resolve_event_name(str(raw_event))
        if not isinstance(groups_value, list):
            raise HookHashError(f"{event_name}: matcher groups must be a list")
        for group_index, group_value in enumerate(groups_value):
            if not isinstance(group_value, Mapping):
                raise HookHashError(f"{event_name}[{group_index}]: group must be an object")
            handlers_value = group_value.get("hooks")
            if not isinstance(handlers_value, list):
                raise HookHashError(f"{event_name}[{group_index}]: 'hooks' must be a list")
            matcher = group_value.get("matcher")
            for handler_index, handler_value in enumerate(handlers_value):
                if not isinstance(handler_value, Mapping):
                    raise HookHashError(
                        f"{event_name}[{group_index}].hooks[{handler_index}]: "
                        "handler must be an object"
                    )
                yield (
                    event_name,
                    group_index,
                    handler_index,
                    matcher,
                    handler_value,
                )
