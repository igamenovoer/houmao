"""Tests for the Codex observer hooks generator."""

from __future__ import annotations

import json
import shlex
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

from houmao.hook_observation.codex_hooks_generator import (
    CODEX_EVENTS,
    DEFAULT_TIMEOUT_SECONDS,
    SESSION_END_TIMEOUT_SECONDS,
    build_emitter_command,
    build_observer_hooks_document,
    render_hooks_state_toml,
    render_observer_hooks_json,
)
from houmao.hook_observation.trust_hash import (
    EVENT_LABELS,
    hook_hash,
    hook_state_key,
    iter_handlers,
)

EMITTER = Path("/srv/houmao/hook_observation/emit_hook.py")
PYTHON = "/usr/bin/python3"
EMITTER_COMMAND = f"{PYTHON} {EMITTER}"
HOOKS_JSON_PATH = Path("/srv/houmao/sessions/abc/codex-home/hooks.json")

# Golden hashes for the generated handlers. They guard the exact normalized
# handler shape (timeout, async, and omitted optional fields) that Codex
# persists as ``trusted_hash``; the algorithm itself is pinned to upstream
# vectors in ``test_trust_hash.py``.
SESSION_START_GOLDEN_HASH = (
    "sha256:252bc1bc68c114de4c6c67c99495549c327e296501420104bc7027041e7e60a7"
)
SESSION_END_GOLDEN_HASH = "sha256:588005e2cbf45f6f8056be8adf02b8d43b0cc1cf9b0776b65d0d1a6e11ba623b"


def _build(**overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {"emitter_command": EMITTER_COMMAND}
    arguments.update(overrides)
    return build_observer_hooks_document(**arguments)


def test_document_subscribes_all_fourteen_events() -> None:
    document = _build()
    assert tuple(document["hooks"]) == CODEX_EVENTS
    assert len(CODEX_EVENTS) == 14
    assert len(document["hooks"]) == 14


def test_every_event_has_one_sync_handler_without_a_matcher() -> None:
    hooks = _build()["hooks"]
    for event_name in CODEX_EVENTS:
        groups = hooks[event_name]
        assert len(groups) == 1
        assert "matcher" not in groups[0]
        handlers = groups[0]["hooks"]
        assert len(handlers) == 1
        assert handlers[0]["type"] == "command"
        assert handlers[0]["command"] == EMITTER_COMMAND
        assert handlers[0]["async"] is False


def test_timeouts_are_five_seconds_except_session_end() -> None:
    hooks = _build()["hooks"]
    assert DEFAULT_TIMEOUT_SECONDS == 5
    assert SESSION_END_TIMEOUT_SECONDS == 2
    assert hooks["SessionEnd"][0]["hooks"][0]["timeout"] == 2
    for event_name in CODEX_EVENTS:
        if event_name != "SessionEnd":
            assert hooks[event_name][0]["hooks"][0]["timeout"] == 5


def test_timeout_overrides_are_applied_per_event() -> None:
    hooks = _build(timeout_seconds=9, session_end_timeout_seconds=3)["hooks"]
    assert hooks["SessionEnd"][0]["hooks"][0]["timeout"] == 3
    assert hooks["Stop"][0]["hooks"][0]["timeout"] == 9


def test_build_emitter_command_quotes_paths() -> None:
    command = build_emitter_command(
        emitter=Path("/srv/hook dir/emit hook.py"), python_executable=PYTHON
    )
    assert shlex.split(command) == [PYTHON, "/srv/hook dir/emit hook.py"]


def test_build_emitter_command_defaults_to_current_interpreter() -> None:
    command = build_emitter_command(emitter=EMITTER)
    assert shlex.split(command) == [sys.executable, str(EMITTER)]


@pytest.mark.parametrize(
    "overrides",
    [
        {"emitter_command": ""},
        {"emitter_command": "   "},
        {"session_end_timeout_seconds": 0},
        {"session_end_timeout_seconds": 4},
        {"timeout_seconds": 0},
    ],
)
def test_invalid_inputs_are_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        _build(**overrides)


def test_rendered_json_round_trips() -> None:
    document = _build()
    text = render_observer_hooks_json(document)
    assert text.endswith("\n")
    assert json.loads(text) == document


def test_state_block_pretrusts_every_generated_handler() -> None:
    document = _build()
    text = render_hooks_state_toml(document, HOOKS_JSON_PATH)
    state = tomllib.loads(text)["hooks"]["state"]

    expected: dict[str, str] = {}
    for event_name, group_index, handler_index, matcher, handler in iter_handlers(document):
        key = hook_state_key(HOOKS_JSON_PATH, event_name, group_index, handler_index)
        expected[key] = hook_hash(event_name, matcher, handler)

    assert state == {key: {"trusted_hash": digest} for key, digest in expected.items()}
    assert len(state) == 14
    assert set(state) == {
        f"{HOOKS_JSON_PATH}:{EVENT_LABELS[event_name]}:0:0" for event_name in CODEX_EVENTS
    }


def test_state_block_pins_generated_handler_hashes() -> None:
    state = tomllib.loads(render_hooks_state_toml(_build(), HOOKS_JSON_PATH))["hooks"]["state"]
    start_key = f"{HOOKS_JSON_PATH}:session_start:0:0"
    end_key = f"{HOOKS_JSON_PATH}:session_end:0:0"
    assert state[start_key]["trusted_hash"] == SESSION_START_GOLDEN_HASH
    assert state[end_key]["trusted_hash"] == SESSION_END_GOLDEN_HASH
    assert state[start_key]["trusted_hash"] != state[end_key]["trusted_hash"]


def test_state_block_covers_every_group_and_handler() -> None:
    document = {
        "hooks": {
            "PreToolUse": [
                {"hooks": [{"type": "command", "command": "echo one"}]},
                {
                    "matcher": "^Bash$",
                    "hooks": [
                        {"type": "command", "command": "echo two"},
                        {"type": "command", "command": "echo three"},
                    ],
                },
            ]
        }
    }
    state = tomllib.loads(render_hooks_state_toml(document, HOOKS_JSON_PATH))["hooks"]["state"]
    assert set(state) == {
        f"{HOOKS_JSON_PATH}:pre_tool_use:0:0",
        f"{HOOKS_JSON_PATH}:pre_tool_use:1:0",
        f"{HOOKS_JSON_PATH}:pre_tool_use:1:1",
    }


def test_state_block_escapes_toml_keys() -> None:
    hooks_path = Path('/srv/houmao/ho"ok\\dir/hooks.json')
    state = tomllib.loads(render_hooks_state_toml(_build(), hooks_path))["hooks"]["state"]
    assert f"{hooks_path}:session_start:0:0" in state


def test_empty_document_renders_empty_block() -> None:
    assert render_hooks_state_toml({"hooks": {}}, HOOKS_JSON_PATH) == ""


def test_state_block_ends_with_a_single_newline() -> None:
    text = render_hooks_state_toml(_build(), HOOKS_JSON_PATH)
    assert text.endswith("\n")
    assert not text.endswith("\n\n")
