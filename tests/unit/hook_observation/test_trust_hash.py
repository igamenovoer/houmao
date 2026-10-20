"""Tests for the Codex hook trust hash and state-key port.

The expected literals are copied from the upstream Codex test suite:

- ``extern/orphan/codex/codex-rs/config/src/fingerprint_tests.rs:6-26``
  pins the canonical serializer bytes;
- ``extern/orphan/codex/codex-rs/core/tests/suite/hooks.rs:4696-4699`` pins
  the two declaration-only plugin hashes, and ``hooks.rs:4748-4765`` carries
  the declarations those hashes cover.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest

from houmao.hook_observation.trust_hash import (
    ADDITIONAL_CONTEXT_EVENTS,
    DEFAULT_ADDITIONAL_CONTEXT_LIMIT,
    DEFAULT_TIMEOUT_SECONDS,
    EVENT_LABELS,
    MATCHER_EVENTS,
    HookHashError,
    build_identity,
    canonical_json,
    hook_hash,
    hook_state_key,
    iter_handlers,
    normalize_timeout,
    resolve_event_name,
    sha256_prefixed,
)

# extern/orphan/codex/codex-rs/config/src/fingerprint_tests.rs:9-23
FINGERPRINT_INPUTS: tuple[str, ...] = (
    'rows = [{ z = 2, a = 1 }, { z = 4, a = 3 }]\n[nested]\nz = "text"\na = true\n',
    'rows = [{ a = 1, z = 2 }, { a = 3, z = 4 }]\n[nested]\na = true\nz = "text"\n',
)
FINGERPRINT_HASH = "sha256:a5e4c8fbdbc75d185b0f2b5291bfb2de10e8c523d6c89248876fd78a97c83176"

# extern/orphan/codex/codex-rs/core/tests/suite/hooks.rs:4748-4765 declares the
# command and matcher; the expected hashes are at hooks.rs:4696-4699.
PLUGIN_COMMAND = "python3 -I -S ${PLUGIN_ROOT}/hooks/pre_tool_use_hook.py"
PLUGIN_MATCHER = "^Bash$"
PLUGIN_HANDLER: dict[str, Any] = {"type": "command", "command": PLUGIN_COMMAND}
PLUGIN_HASHES: tuple[tuple[str, str], ...] = (
    (
        "PreToolUse",
        "sha256:c9ee1aca1b5d8c72b99df6571c87d61350b09f7f4594ae30e7250a2027e9d76b",
    ),
    (
        "PostToolUse",
        "sha256:9eef43ad6f26b1f9b94f318a50445f8bb62c363da08152a2966b73d308bf42ba",
    ),
)
NON_MATCHER_EVENTS: tuple[str, ...] = (
    "PreModelRequest",
    "PostModelRequest",
    "UserPromptSubmit",
    "Stop",
    "Interrupt",
)
NON_CONTEXT_EVENTS: tuple[str, ...] = (
    "PermissionRequest",
    "PreCompact",
    "PostCompact",
    "SessionEnd",
    "SubagentStop",
    "Stop",
    "Interrupt",
    "PreModelRequest",
    "PostModelRequest",
)


@pytest.mark.parametrize("fingerprint_toml", FINGERPRINT_INPUTS)
def test_fingerprint_fixture_matches_upstream_hash(fingerprint_toml: str) -> None:
    assert sha256_prefixed(tomllib.loads(fingerprint_toml)) == FINGERPRINT_HASH


@pytest.mark.parametrize(("event_name", "expected"), PLUGIN_HASHES)
def test_plugin_declaration_hashes_match_upstream(event_name: str, expected: str) -> None:
    assert hook_hash(event_name, PLUGIN_MATCHER, PLUGIN_HANDLER) == expected


def test_event_names_resolve_in_both_directions() -> None:
    for event_name, label in EVENT_LABELS.items():
        assert resolve_event_name(event_name) == event_name
        assert resolve_event_name(label) == event_name
    with pytest.raises(HookHashError):
        resolve_event_name("NotAnEvent")


def test_timeout_normalization_uses_session_end_clamp_for_two_events() -> None:
    assert normalize_timeout("SessionEnd", None) == 1
    assert normalize_timeout("SessionEnd", 0) == 1
    assert normalize_timeout("SessionEnd", 2) == 2
    assert normalize_timeout("SessionEnd", 600) == 3
    assert normalize_timeout("Interrupt", None) == 1
    assert normalize_timeout("Interrupt", 5) == 3
    assert normalize_timeout("PreToolUse", None) == DEFAULT_TIMEOUT_SECONDS
    assert normalize_timeout("Stop", 0) == 1
    assert normalize_timeout("Stop", 900) == 900


def test_identity_applies_timeout_normalization() -> None:
    assert build_identity("SessionEnd", None, PLUGIN_HANDLER)["hooks"][0]["timeout"] == 1
    assert (
        build_identity("SessionEnd", None, {**PLUGIN_HANDLER, "timeout": 600})["hooks"][0][
            "timeout"
        ]
        == 3
    )
    assert (
        build_identity("Interrupt", None, {**PLUGIN_HANDLER, "timeout": 5})["hooks"][0]["timeout"]
        == 3
    )
    assert (
        build_identity("PreToolUse", None, PLUGIN_HANDLER)["hooks"][0]["timeout"]
        == DEFAULT_TIMEOUT_SECONDS
    )


@pytest.mark.parametrize("bad_timeout", [1.5, "5", True, False, -1])
def test_invalid_timeouts_are_rejected(bad_timeout: object) -> None:
    with pytest.raises(HookHashError):
        normalize_timeout("PreToolUse", bad_timeout)


def test_matcher_is_kept_for_matcher_capable_events() -> None:
    with_matcher = hook_hash("PreToolUse", PLUGIN_MATCHER, PLUGIN_HANDLER)
    without_matcher = hook_hash("PreToolUse", None, PLUGIN_HANDLER)
    assert with_matcher != without_matcher
    for event_name in MATCHER_EVENTS:
        identity = build_identity(event_name, PLUGIN_MATCHER, PLUGIN_HANDLER)
        assert identity["matcher"] == PLUGIN_MATCHER


@pytest.mark.parametrize("event_name", NON_MATCHER_EVENTS)
def test_matcher_is_dropped_for_non_matcher_events(event_name: str) -> None:
    assert hook_hash(event_name, PLUGIN_MATCHER, PLUGIN_HANDLER) == hook_hash(
        event_name, None, PLUGIN_HANDLER
    )
    assert "matcher" not in build_identity(event_name, PLUGIN_MATCHER, PLUGIN_HANDLER)


def test_explicit_empty_matcher_is_significant() -> None:
    assert hook_hash("PreToolUse", "", PLUGIN_HANDLER) != hook_hash(
        "PreToolUse", None, PLUGIN_HANDLER
    )


def test_invalid_matchers_are_rejected() -> None:
    with pytest.raises(HookHashError):
        hook_hash("PreToolUse", 42, PLUGIN_HANDLER)


def test_default_additional_context_limit_is_omitted() -> None:
    handler = {
        **PLUGIN_HANDLER,
        "additionalContextLimit": DEFAULT_ADDITIONAL_CONTEXT_LIMIT,
    }
    identity = build_identity("PreToolUse", None, handler)
    assert "additionalContextLimit" not in identity["hooks"][0]
    assert hook_hash("PreToolUse", None, handler) == hook_hash("PreToolUse", None, PLUGIN_HANDLER)


@pytest.mark.parametrize("limit", [0, 4096, 20000])
def test_custom_additional_context_limit_is_hashed(limit: int) -> None:
    handler = {**PLUGIN_HANDLER, "additionalContextLimit": limit}
    identity = build_identity("PreToolUse", None, handler)
    assert identity["hooks"][0]["additionalContextLimit"] == limit
    assert hook_hash("PreToolUse", None, handler) != hook_hash("PreToolUse", None, PLUGIN_HANDLER)


@pytest.mark.parametrize("event_name", sorted(ADDITIONAL_CONTEXT_EVENTS))
def test_additional_context_limit_is_kept_for_context_events(
    event_name: str,
) -> None:
    handler = {**PLUGIN_HANDLER, "additionalContextLimit": 4096}
    identity = build_identity(event_name, None, handler)
    assert identity["hooks"][0]["additionalContextLimit"] == 4096


@pytest.mark.parametrize("event_name", NON_CONTEXT_EVENTS)
def test_additional_context_limit_is_ignored_for_other_events(
    event_name: str,
) -> None:
    handler = {**PLUGIN_HANDLER, "additionalContextLimit": 4096}
    identity = build_identity(event_name, None, handler)
    assert "additionalContextLimit" not in identity["hooks"][0]
    assert hook_hash(event_name, None, handler) == hook_hash(event_name, None, PLUGIN_HANDLER)


@pytest.mark.parametrize("bad_limit", [-1, 2.5, True, "2500"])
def test_invalid_additional_context_limits_are_rejected(bad_limit: object) -> None:
    handler = {**PLUGIN_HANDLER, "additionalContextLimit": bad_limit}
    with pytest.raises(HookHashError):
        hook_hash("PreToolUse", None, handler)


def test_command_windows_is_cleared() -> None:
    handler = {
        **PLUGIN_HANDLER,
        "commandWindows": "powershell.exe -File hook.ps1",
    }
    assert "commandWindows" not in build_identity("PreToolUse", None, handler)["hooks"][0]
    assert hook_hash("PreToolUse", None, handler) == hook_hash("PreToolUse", None, PLUGIN_HANDLER)


def test_none_fields_are_omitted_from_the_identity() -> None:
    handler = {
        "type": "command",
        "command": PLUGIN_COMMAND,
        "timeout": None,
        "commandWindows": None,
        "statusMessage": None,
        "additionalContextLimit": None,
    }
    identity = build_identity("Stop", None, handler)
    normalized = identity["hooks"][0]
    assert set(normalized) == {"type", "command", "timeout", "async"}
    assert "null" not in canonical_json(identity)


def test_status_message_is_retained_when_present() -> None:
    handler = {**PLUGIN_HANDLER, "statusMessage": "observing turn"}
    identity = build_identity("Stop", None, handler)
    assert identity["hooks"][0]["statusMessage"] == "observing turn"


def test_async_flag_is_normalized_to_a_boolean() -> None:
    assert build_identity("Stop", None, PLUGIN_HANDLER)["hooks"][0]["async"] is False
    assert (
        build_identity("Stop", None, {**PLUGIN_HANDLER, "async": True})["hooks"][0]["async"] is True
    )
    with pytest.raises(HookHashError):
        hook_hash("Stop", None, {**PLUGIN_HANDLER, "async": "false"})


@pytest.mark.parametrize(
    "handler",
    [
        {"type": "http", "command": PLUGIN_COMMAND},
        {"command": PLUGIN_COMMAND},
        {"type": "command"},
        {"type": "command", "command": "   "},
        {"type": "command", "command": PLUGIN_COMMAND, "statusMessage": 42},
    ],
)
def test_invalid_handlers_are_rejected(handler: dict[str, Any]) -> None:
    with pytest.raises(HookHashError):
        hook_hash("PreToolUse", None, handler)


def test_canonical_json_sorts_keys_recursively_and_stays_compact() -> None:
    value = {"b": [{"z": 1, "a": 2}], "a": {"d": 4, "c": 3}}
    assert canonical_json(value) == '{"a":{"c":3,"d":4},"b":[{"a":2,"z":1}]}'
    assert canonical_json({"k": "é"}) == '{"k":"é"}'


def test_state_key_format(tmp_path: Path) -> None:
    hooks_path = tmp_path / "hooks.json"
    assert hook_state_key(hooks_path, "PreToolUse", 0, 0) == f"{hooks_path}:pre_tool_use:0:0"
    assert hook_state_key(hooks_path, "pre_tool_use", 1, 2) == f"{hooks_path}:pre_tool_use:1:2"


def test_state_key_makes_relative_paths_absolute(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    assert (
        hook_state_key(Path("hooks.json"), "Stop", 0, 0) == f"{Path.cwd() / 'hooks.json'}:stop:0:0"
    )


def test_iter_handlers_reports_group_and_handler_indices() -> None:
    document = {
        "hooks": {
            "PreToolUse": [
                {
                    "hooks": [
                        {"type": "command", "command": "echo one"},
                        {"type": "command", "command": "echo two"},
                    ]
                },
                {
                    "matcher": PLUGIN_MATCHER,
                    "hooks": [{"type": "command", "command": "echo three"}],
                },
            ]
        }
    }
    rows = [
        (event_name, group_index, handler_index, matcher)
        for event_name, group_index, handler_index, matcher, _ in iter_handlers(document)
    ]
    assert rows == [
        ("PreToolUse", 0, 0, None),
        ("PreToolUse", 0, 1, None),
        ("PreToolUse", 1, 0, PLUGIN_MATCHER),
    ]


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"hooks": []},
        {"hooks": {"NotAnEvent": []}},
        {"hooks": {"PreToolUse": {}}},
        {"hooks": {"PreToolUse": [42]}},
        {"hooks": {"PreToolUse": [{"hooks": {}}]}},
        {"hooks": {"PreToolUse": [{"hooks": [42]}]}},
    ],
)
def test_iter_handlers_rejects_malformed_documents(
    document: dict[str, Any],
) -> None:
    with pytest.raises(HookHashError):
        list(iter_handlers(document))
