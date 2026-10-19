"""Tests for the observer settings generator."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import Any

import pytest

from houmao.hook_observation.settings_generator import (
    COMMAND_EVENTS,
    HTTP_EVENTS,
    OBSERVER_EVENTS,
    TOKEN_ENV_VAR,
    build_observer_hooks_block,
    build_observer_settings,
    collector_url,
    is_observer_hook_entry,
)

PORT = 54321
GENERATION = 4
STORE = Path("/srv/houmao/sessions/abc/hook-observation/claude")
PYTHON = "/usr/bin/python3"
HTTP_EVENTS_V1 = (
    "UserPromptSubmit",
    "Stop",
    "StopFailure",
    "PermissionRequest",
    "PreCompact",
    "PostCompact",
    "PostToolUse",
    "PostToolUseFailure",
)


def _expected_command() -> str:
    return (
        f"{PYTHON} -m houmao.hook_observation.emitter "
        f"--collector-url http://127.0.0.1:{PORT}/v1/hook "
        f"--store {STORE} "
        f"--generation {GENERATION}"
    )


def _expected_http_group() -> dict[str, Any]:
    return {
        "hooks": [
            {
                "type": "http",
                "url": f"http://127.0.0.1:{PORT}/v1/hook",
                "timeout": 2,
                "headers": {"Authorization": "Bearer $HOUMAO_HOOK_TOKEN"},
                "allowedEnvVars": ["HOUMAO_HOOK_TOKEN"],
            }
        ]
    }


def _expected_command_group() -> dict[str, Any]:
    return {
        "hooks": [
            {
                "type": "command",
                "command": _expected_command(),
                "timeout": 2,
            }
        ]
    }


def _expected_settings() -> dict[str, Any]:
    hooks: dict[str, Any] = {"SessionStart": [_expected_command_group()]}
    for name in HTTP_EVENTS_V1:
        hooks[name] = [_expected_http_group()]
    return {"hooks": hooks}


def _build(**overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "port": PORT,
        "store": STORE,
        "generation": GENERATION,
        "python_executable": PYTHON,
    }
    arguments.update(overrides)
    return build_observer_settings(**arguments)


def test_settings_snapshot_matches_pinned_shape() -> None:
    assert _build() == _expected_settings()


def test_hooks_block_matches_settings_hooks_key() -> None:
    block = build_observer_hooks_block(
        port=PORT,
        store=STORE,
        generation=GENERATION,
        python_executable=PYTHON,
    )
    assert block == _expected_settings()["hooks"]


def test_event_set_is_nine_events_with_http_command_split() -> None:
    settings = _build()
    assert set(settings["hooks"]) == set(OBSERVER_EVENTS)
    assert len(settings["hooks"]) == 9
    assert COMMAND_EVENTS == ("SessionStart",)
    assert len(HTTP_EVENTS) == 8
    assert set(HTTP_EVENTS) == set(HTTP_EVENTS_V1)


def test_http_handlers_reference_token_through_allowed_env_var() -> None:
    hooks = _build()["hooks"]
    for name in HTTP_EVENTS_V1:
        handler = hooks[name][0]["hooks"][0]
        assert handler["type"] == "http"
        assert handler["url"] == collector_url(PORT)
        assert handler["timeout"] == 2
        assert handler["headers"] == {"Authorization": f"Bearer ${TOKEN_ENV_VAR}"}
        assert handler["allowedEnvVars"] == [TOKEN_ENV_VAR]


def test_command_handler_uses_current_interpreter_and_baked_argv() -> None:
    settings = build_observer_settings(port=PORT, store=STORE, generation=GENERATION)
    argv = shlex.split(settings["hooks"]["SessionStart"][0]["hooks"][0]["command"])
    assert argv[0] == sys.executable
    assert argv[1:3] == ["-m", "houmao.hook_observation.emitter"]
    assert argv[argv.index("--collector-url") + 1] == collector_url(PORT)
    assert argv[argv.index("--store") + 1] == str(STORE)
    assert argv[argv.index("--generation") + 1] == str(GENERATION)


def test_generated_output_never_contains_the_token_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "sk-super-secret-token-value"
    monkeypatch.setenv(TOKEN_ENV_VAR, secret)
    dumped = json.dumps(_build())
    assert secret not in dumped
    assert "$HOUMAO_HOOK_TOKEN" in dumped
    assert TOKEN_ENV_VAR in dumped


def test_is_observer_hook_entry_accepts_generated_entries() -> None:
    hooks = _build()["hooks"]
    for name in OBSERVER_EVENTS:
        assert is_observer_hook_entry(hooks[name][0]) is True


def test_is_observer_hook_entry_accepts_bare_handlers() -> None:
    command_handler = _build()["hooks"]["SessionStart"][0]["hooks"][0]
    http_handler = _build()["hooks"]["Stop"][0]["hooks"][0]
    assert is_observer_hook_entry(command_handler) is True
    assert is_observer_hook_entry(http_handler) is True


def test_is_observer_hook_entry_rejects_operator_entries() -> None:
    operator_command = {
        "hooks": [{"type": "command", "command": "bash /opt/operator/hook.sh", "timeout": 5}]
    }
    operator_http = {
        "hooks": [
            {
                "type": "http",
                "url": "http://127.0.0.1:9999/operator",
                "timeout": 2,
                "headers": {},
                "allowedEnvVars": [],
            }
        ]
    }
    unrelated_matcher = {"matcher": "Bash", "hooks": [{"type": "command", "command": "true"}]}
    assert is_observer_hook_entry(operator_command) is False
    assert is_observer_hook_entry(operator_http) is False
    assert is_observer_hook_entry(unrelated_matcher) is False


def test_is_observer_hook_entry_tolerates_malformed_entries() -> None:
    assert is_observer_hook_entry(None) is False
    assert is_observer_hook_entry({}) is False
    assert is_observer_hook_entry([]) is False
    assert is_observer_hook_entry("Stop") is False
    assert is_observer_hook_entry({"hooks": "not-a-list"}) is False
    assert is_observer_hook_entry({"hooks": [None, 42, {}]}) is False


def test_is_observer_hook_entry_matches_mixed_groups() -> None:
    mixed = {
        "hooks": [
            {"type": "command", "command": "bash /opt/operator/hook.sh"},
            _build()["hooks"]["SessionStart"][0]["hooks"][0],
        ]
    }
    assert is_observer_hook_entry(mixed) is True


def test_timeout_override_applies_to_every_handler() -> None:
    hooks = _build(timeout_seconds=5)["hooks"]
    for name in OBSERVER_EVENTS:
        assert hooks[name][0]["hooks"][0]["timeout"] == 5
