"""Local reimplementation of Codex's hook trust hash (throwaway harness).

Codex trusts a hook handler only when the persisted
``[hooks.state."<key>".trusted_hash]`` equals the handler's current hash
(``codex-rs/hooks/src/engine/discovery.rs``, ``fn hook_hash`` and
``hook_trust_status``). The current hash is built from a normalized identity:

1. ``event_name`` is Codex's snake_case event label.
2. The matcher group keeps its matcher only for events that support matchers
   (``codex-rs/hooks/src/events/common.rs``, ``matcher_pattern_for_event``).
3. The handler list is replaced by the one normalized command handler:
   timeout defaulted/normalized, ``commandWindows`` cleared,
   ``additionalContextLimit`` kept only for context-capable events and only
   when it differs from the 2500-token default.
4. The identity is serialized to TOML and then JSON, all object keys are
   sorted recursively, and the **compact** JSON bytes are SHA-256 hashed and
   prefixed ``sha256:`` (``codex-rs/config/src/fingerprint.rs``,
   ``version_for_toml``).

The persisted state key is
``<absolute hooks.json path>:<event_label>:<group_index>:<handler_index>``
(``hooks/src/lib.rs``, ``hook_key``).

Validation status: the canonicalization matches the two declaration hashes
hard-coded in ``core/tests/suite/hooks.rs`` (plugin PreToolUse/PostToolUse
fixtures) and the ``fingerprint_tests.rs`` fixture, so the serializer and
normalization are verified against Codex's own test vectors. Live
``currentHash`` validation against the installed 0.163.0 binary is still
pending (campaign arm T1/S2). Linux/macOS command selection only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any, Iterator

EVENT_LABELS: dict[str, str] = {
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
EVENT_BY_LABEL: dict[str, str] = {label: event for event, label in EVENT_LABELS.items()}
MATCHER_EVENTS: frozenset[str] = frozenset(
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
SESSION_END_LIKE_EVENTS: frozenset[str] = frozenset({"SessionEnd", "Interrupt"})
ADDITIONAL_CONTEXT_EVENTS: frozenset[str] = frozenset(
    {
        "PreToolUse",
        "PostToolUse",
        "SessionStart",
        "UserPromptSubmit",
        "SubagentStart",
    }
)
DEFAULT_TIMEOUT_SECONDS = 600
SESSION_END_MAX_TIMEOUT_SECONDS = 3
DEFAULT_ADDITIONAL_CONTEXT_LIMIT = 2500

# Codex test vectors. Sources:
#   extern/orphan/codex/codex-rs/core/tests/suite/hooks.rs (legacy plugin
#     declaration-only approvals) for the two hook hashes;
#   extern/orphan/codex/codex-rs/config/src/fingerprint_tests.rs for the
#     canonical-serializer hash.
FIXTURE_PLUGIN_HASHES: dict[str, str] = {
    "PreToolUse": "sha256:c9ee1aca1b5d8c72b99df6571c87d61350b09f7f4594ae30e7250a2027e9d76b",
    "PostToolUse": "sha256:9eef43ad6f26b1f9b94f318a50445f8bb62c363da08152a2966b73d308bf42ba",
}
FIXTURE_PLUGIN_COMMAND = "python3 -I -S ${PLUGIN_ROOT}/hooks/pre_tool_use_hook.py"
FIXTURE_PLUGIN_MATCHER = "^Bash$"
FIXTURE_FINGERPRINT_TOML = """rows = [{ z = 2, a = 1 }, { z = 4, a = 3 }]
[nested]
z = "text"
a = true
"""
FIXTURE_FINGERPRINT_HASH = "sha256:a5e4c8fbdbc75d185b0f2b5291bfb2de10e8c523d6c89248876fd78a97c83176"


class HookHashError(ValueError):
    """Raised when a hooks document cannot be normalized like Codex would."""


def canonical_json(value: Any) -> str:
    """Serialize a JSON value compactly with all object keys sorted recursively."""

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_prefixed(value: Any) -> str:
    """Return ``sha256:<hex>`` over the canonical JSON encoding of ``value``."""

    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def resolve_event_name(value: str) -> str:
    """Return the PascalCase event name for either PascalCase or snake_case input."""

    if value in EVENT_LABELS:
        return value
    if value in EVENT_BY_LABEL:
        return EVENT_BY_LABEL[value]
    known = ", ".join(EVENT_LABELS)
    raise HookHashError(f"unknown event {value!r}; expected one of: {known}")


def normalize_timeout(event_name: str, timeout: Any) -> int:
    """Normalize a handler timeout exactly like ``normalize_command_hook``.

    ``SessionEnd`` and ``Interrupt`` default to 1 s and clamp to 1-3 s; every
    other event defaults to 600 s and floors at 1 s with no upper clamp.
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


def normalize_command_handler(event_name: str, handler: dict[str, Any]) -> dict[str, Any]:
    """Return Codex's normalized ``HookHandlerConfig::Command`` mapping.

    None-valued optional fields are omitted, matching TOML serialization (TOML
    has no null). ``commandWindows`` is always cleared after Codex selects the
    platform command; this harness runs on Linux, where ``command`` wins.
    """

    handler_type = handler.get("type")
    if handler_type != "command":
        raise HookHashError(
            f"unsupported handler type {handler_type!r}; hash_hook.py implements "
            "command handlers only (the campaign's observer hooks are commands)"
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


def normalize_matcher(event_name: str, matcher: Any) -> str | None:
    """Return the matcher Codex keeps in the identity for this event."""

    if matcher is not None and not isinstance(matcher, str):
        raise HookHashError(f"matcher must be a string or null, got {matcher!r}")
    if event_name not in MATCHER_EVENTS:
        return None
    return matcher


def build_identity(event_name: str, matcher: Any, handler: dict[str, Any]) -> dict[str, Any]:
    """Build the normalized identity Codex hashes for one handler."""

    identity: dict[str, Any] = {
        "event_name": EVENT_LABELS[event_name],
        "hooks": [normalize_command_handler(event_name, handler)],
    }
    normalized_matcher = normalize_matcher(event_name, matcher)
    if normalized_matcher is not None:
        identity["matcher"] = normalized_matcher
    return identity


def hook_hash(event_name: str, matcher: Any, handler: dict[str, Any]) -> str:
    """Return the ``sha256:`` trust hash for one normalized handler."""

    return sha256_prefixed(build_identity(event_name, matcher, handler))


def hook_state_key(
    hooks_json_path: Path, event_name: str, group_index: int, handler_index: int
) -> str:
    """Return Codex's persisted hook-state key for one handler."""

    return (
        f"{os.path.abspath(os.fspath(hooks_json_path))}:"
        f"{EVENT_LABELS[event_name]}:{group_index}:{handler_index}"
    )


def _load_document(path: Path) -> dict[str, Any]:
    """Load and minimally validate a hooks.json document."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HookHashError(f"cannot read hooks JSON {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise HookHashError("hooks JSON must be an object")
    hooks = document.get("hooks")
    if not isinstance(hooks, dict):
        raise HookHashError("hooks JSON must contain an object under 'hooks'")
    return document


def iter_handlers(
    document: dict[str, Any],
) -> Iterator[tuple[str, int, int, str | None, dict[str, Any]]]:
    """Yield ``(event, group_index, handler_index, matcher, handler)`` in file order."""

    hooks = document["hooks"]
    assert isinstance(hooks, dict)
    for raw_event, groups in hooks.items():
        event_name = resolve_event_name(str(raw_event))
        if not isinstance(groups, list):
            raise HookHashError(f"{event_name}: matcher groups must be a list")
        for group_index, group in enumerate(groups):
            if not isinstance(group, dict):
                raise HookHashError(f"{event_name}[{group_index}]: group must be an object")
            handlers = group.get("hooks")
            if not isinstance(handlers, list):
                raise HookHashError(f"{event_name}[{group_index}]: 'hooks' must be a list")
            matcher = group.get("matcher")
            for handler_index, handler in enumerate(handlers):
                if not isinstance(handler, dict):
                    raise HookHashError(
                        f"{event_name}[{group_index}].hooks[{handler_index}]: "
                        "handler must be an object"
                    )
                yield event_name, group_index, handler_index, matcher, handler


def _select_handler(
    document: dict[str, Any], event_query: str, group_index: int, handler_index: int
) -> tuple[str, int, int, str | None, dict[str, Any]]:
    """Return exactly one handler, validating indices and event presence."""

    event_name = resolve_event_name(event_query)
    matches = [
        item
        for item in iter_handlers(document)
        if item[0] == event_name and item[1] == group_index and item[2] == handler_index
    ]
    if not matches:
        raise HookHashError(
            f"no handler at {event_name} group={group_index} handler={handler_index}"
        )
    return matches[0]


def state_blocks(document: dict[str, Any], hooks_json_path: Path) -> list[str]:
    """Return one ``[hooks.state."<key>"]`` TOML block per handler."""

    blocks: list[str] = []
    for event_name, group_index, handler_index, matcher, handler in iter_handlers(document):
        key = hook_state_key(hooks_json_path, event_name, group_index, handler_index)
        digest = hook_hash(event_name, matcher, handler)
        blocks.append(f'[hooks.state."{_toml_key_escape(key)}"]\ntrusted_hash = "{digest}"')
    return blocks


def _toml_key_escape(value: str) -> str:
    """Escape one value for a TOML basic quoted key."""

    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _self_test() -> int:
    """Run serializer and normalization checks against Codex test vectors."""

    checks: list[tuple[str, bool, str]] = []

    fingerprint_value = tomllib.loads(FIXTURE_FINGERPRINT_TOML)
    got = sha256_prefixed(fingerprint_value)
    checks.append(
        (
            "fingerprint-fixture",
            got == FIXTURE_FINGERPRINT_HASH,
            f"got {got}",
        )
    )

    plugin_handler: dict[str, Any] = {
        "type": "command",
        "command": FIXTURE_PLUGIN_COMMAND,
    }
    for event_name, expected in FIXTURE_PLUGIN_HASHES.items():
        got = hook_hash(event_name, FIXTURE_PLUGIN_MATCHER, plugin_handler)
        checks.append(
            (
                f"codex-fixture-{EVENT_LABELS[event_name]}",
                got == expected,
                f"got {got}",
            )
        )

    baseline = hook_hash("PreToolUse", None, plugin_handler)
    again = hook_hash("PreToolUse", None, plugin_handler)
    changed = hook_hash(
        "PreToolUse", None, {"type": "command", "command": FIXTURE_PLUGIN_COMMAND + " --x"}
    )
    checks.append(("stable-across-runs", baseline == again, baseline))
    checks.append(("changes-with-command", baseline != changed, f"{baseline} != {changed}"))

    with_matcher = hook_hash("PreToolUse", "^Bash$", plugin_handler)
    without_matcher = hook_hash("PreToolUse", None, plugin_handler)
    dropped = hook_hash("UserPromptSubmit", "^Bash$", plugin_handler)
    dropped_none = hook_hash("UserPromptSubmit", None, plugin_handler)
    checks.append(("matcher-kept-where-supported", with_matcher != without_matcher, ""))
    checks.append(("matcher-dropped-where-unsupported", dropped == dropped_none, ""))
    checks.append(
        (
            "matcher-empty-is-significant",
            hook_hash("PreToolUse", "", plugin_handler) != without_matcher,
            "explicit empty matcher hashes differently from an absent matcher",
        )
    )

    explicit_default = hook_hash(
        "PreToolUse", None, {**plugin_handler, "additionalContextLimit": 2500}
    )
    custom_limit = hook_hash(
        "PreToolUse", None, {**plugin_handler, "additionalContextLimit": 20000}
    )
    unlimited = hook_hash("PreToolUse", None, {**plugin_handler, "additionalContextLimit": 0})
    unsupported_limit = hook_hash("Stop", None, {**plugin_handler, "additionalContextLimit": 4096})
    unsupported_none = hook_hash("Stop", None, plugin_handler)
    checks.append(("additional-context-default-omitted", baseline == explicit_default, ""))
    checks.append(("additional-context-custom-hashed", baseline != custom_limit, ""))
    checks.append(("additional-context-zero-hashed", baseline != unlimited, ""))
    checks.append(
        (
            "additional-context-ignored-on-unsupported-event",
            unsupported_limit == unsupported_none,
            "",
        )
    )

    session_end_default = build_identity("SessionEnd", None, plugin_handler)
    session_end_clamped = build_identity("SessionEnd", None, {**plugin_handler, "timeout": 600})
    interrupt_clamped = build_identity("Interrupt", None, {**plugin_handler, "timeout": 5})
    regular_default = build_identity("PreToolUse", None, plugin_handler)
    checks.append(
        (
            "timeout-normalization",
            session_end_default["hooks"][0]["timeout"] == 1
            and session_end_clamped["hooks"][0]["timeout"] == 3
            and interrupt_clamped["hooks"][0]["timeout"] == 3
            and regular_default["hooks"][0]["timeout"] == 600,
            "",
        )
    )

    key = hook_state_key(Path("/tmp/hooks.json"), "PreToolUse", 0, 0)
    checks.append(("state-key-format", key == "/tmp/hooks.json:pre_tool_use:0:0", key))

    with tempfile.TemporaryDirectory(prefix="hash-hook-selftest-") as tmp:
        hooks_path = Path(tmp) / "hooks.json"
        document = {
            "hooks": {
                "PreToolUse": [
                    {"hooks": [{"type": "command", "command": "echo one"}]},
                    {"matcher": "^Bash$", "hooks": [{"type": "command", "command": "echo two"}]},
                ]
            }
        }
        hooks_path.write_text(json.dumps(document), encoding="utf-8")
        blocks = state_blocks(_load_document(hooks_path), hooks_path)
        parsed = tomllib.loads("\n\n".join(blocks))
        expected_keys = {
            f"{hooks_path}:pre_tool_use:0:0",
            f"{hooks_path}:pre_tool_use:1:0",
        }
        checks.append(
            (
                "emit-state-toml-roundtrip",
                set(parsed.get("hooks", {}).get("state", {})) == expected_keys,
                f"{len(blocks)} blocks",
            )
        )

    failed = 0
    for name, ok, note in checks:
        suffix = f" ({note})" if note else ""
        print(f"{'PASS' if ok else 'FAIL'} {name}{suffix}")
        if not ok:
            failed += 1
    print(f"HASH SELF-TEST {'PASSED' if failed == 0 else f'{failed} CHECK(S) FAILED'}")
    return 0 if failed == 0 else 1


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: print one key/hash pair or a full state TOML block set."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hooks-json", type=Path, default=None, help="hooks.json path")
    parser.add_argument("--event", default=None, help="event name (PascalCase or snake_case)")
    parser.add_argument("--group", type=int, default=None, help="matcher-group index")
    parser.add_argument("--handler", type=int, default=None, help="handler index in the group")
    parser.add_argument(
        "--emit-state",
        action="store_true",
        help="emit the full [hooks.state...] TOML block for every handler",
    )
    parser.add_argument(
        "--identity",
        action="store_true",
        help="also print the canonical normalized identity JSON",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="verify against Codex's own hash fixtures and normalization rules",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()
    if args.hooks_json is None:
        parser.error("--hooks-json is required unless --self-test is given")
    try:
        document = _load_document(args.hooks_json)
        if args.emit_state:
            blocks = state_blocks(document, args.hooks_json)
            print("\n\n".join(blocks))
            return 0
        if args.event is None or args.group is None or args.handler is None:
            parser.error("--event, --group, and --handler are required without --emit-state")
        event_name, group_index, handler_index, matcher, handler = _select_handler(
            document, args.event, args.group, args.handler
        )
        key = hook_state_key(args.hooks_json, event_name, group_index, handler_index)
        digest = hook_hash(event_name, matcher, handler)
        print(f"key: {key}")
        print(f"hash: {digest}")
        if args.identity:
            print(f"identity: {canonical_json(build_identity(event_name, matcher, handler))}")
            print(f"key_source: {os.path.abspath(os.fspath(args.hooks_json))}")
        return 0
    except HookHashError as exc:
        print(f"hash_hook: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
