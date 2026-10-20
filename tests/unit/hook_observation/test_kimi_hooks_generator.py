"""Tests for the Kimi observer hooks generator."""

from __future__ import annotations

import shlex
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.launch_policy.provider_hooks import set_toml_key
from houmao.hook_observation.kimi_hooks_generator import (
    ALLOWED_HOOK_KEYS,
    DEFAULT_TIMEOUT_SECONDS,
    KIMI_EVENTS,
    OBSERVER_BLOCK_BEGIN_MARKER,
    OBSERVER_BLOCK_END_MARKER,
    KimiHookConfigError,
    build_collector_emitter_command,
    build_emitter_command,
    merge_observer_block,
    render_hook_entry,
    render_observer_block,
    strip_observer_block,
    validate_hooks_file,
)
from houmao.hook_observation.settings_generator import collector_url

EMITTER = Path("/srv/houmao/hook_observation/emitter.py")
PYTHON = "/usr/bin/python3"
EMITTER_COMMAND = f"{PYTHON} {EMITTER}"
CONFIG_PATH = Path("/srv/houmao/sessions/abc/kimi-home/config.toml")

ROOT_FIELDS = 'default_model = "managed:kimi-code/kimi-k2.5"\ndefault_permission_mode = "auto"\n'
PROVIDER_MODEL_TABLES = (
    "\n[providers.managed]\n"
    'type = "openai"\n'
    'base_url = "https://example.invalid/v1"\n'
    '\n[models."kimi-k2.5"]\n'
    'provider = "managed"\n'
    'model = "kimi-k2.5"\n'
)
OPERATOR_HOOK = '[[hooks]]\nevent = "Stop"\ncommand = "true"\ntimeout = 5\n'


def _render(**overrides: Any) -> str:
    arguments: dict[str, Any] = {"emitter_command": EMITTER_COMMAND, "generation": 1}
    arguments.update(overrides)
    return render_observer_block(**arguments)


def _entries(text: str) -> list[dict[str, Any]]:
    hooks = tomllib.loads(text)["hooks"]
    assert isinstance(hooks, list)
    return hooks


def _write_launch_policy_fields(config_path: Path) -> None:
    set_toml_key(
        path=config_path,
        key_path=("default_model",),
        value="managed:kimi-code/kimi-k2.5",
    )
    set_toml_key(
        path=config_path,
        key_path=("default_permission_mode",),
        value="auto",
    )
    set_toml_key(
        path=config_path,
        key_path=("providers", "managed", "type"),
        value="openai",
    )
    set_toml_key(
        path=config_path,
        key_path=("providers", "managed", "base_url"),
        value="https://example.invalid/v1",
    )
    set_toml_key(
        path=config_path,
        key_path=("models", "kimi-k2.5", "provider"),
        value="managed",
    )
    set_toml_key(
        path=config_path,
        key_path=("models", "kimi-k2.5", "model"),
        value="kimi-k2.5",
    )


def _malformed_config_path(tmp_path: Path, entry_text: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(_render() + "\n" + entry_text, encoding="utf-8")
    return path


def test_block_subscribes_all_twenty_events() -> None:
    entries = _entries(_render())
    assert len(KIMI_EVENTS) == 20
    assert len(entries) == 20
    assert tuple(entry["event"] for entry in entries) == KIMI_EVENTS


def test_every_entry_carries_only_the_provider_fields() -> None:
    for entry in _entries(_render()):
        assert set(entry) == {"event", "command", "timeout"}
        assert set(entry) <= ALLOWED_HOOK_KEYS
        assert entry["command"] == EMITTER_COMMAND
        assert entry["timeout"] == DEFAULT_TIMEOUT_SECONDS


def test_block_is_marker_delimited_with_a_generation_header() -> None:
    text = _render(generation=3)
    header = f"{OBSERVER_BLOCK_BEGIN_MARKER} (managed; do not edit; generation 3)\n"
    assert text.startswith(header)
    assert text.endswith(f"{OBSERVER_BLOCK_END_MARKER}\n")
    assert text.count(OBSERVER_BLOCK_BEGIN_MARKER) == 1
    assert text.count(OBSERVER_BLOCK_END_MARKER) == 1
    assert text.count("[[hooks]]") == 20


def test_single_entry_golden_shape() -> None:
    assert render_hook_entry(event="SessionStart", command=EMITTER_COMMAND) == (
        f'[[hooks]]\nevent = "SessionStart"\ncommand = "{EMITTER_COMMAND}"\ntimeout = 5\n'
    )


def test_custom_timeout_is_applied_to_every_entry() -> None:
    assert {entry["timeout"] for entry in _entries(_render(timeout=9))} == {9}


def test_render_rejects_unknown_events() -> None:
    with pytest.raises(KimiHookConfigError, match="unknown Kimi hook event"):
        render_observer_block(
            emitter_command=EMITTER_COMMAND,
            generation=1,
            events=("Stop", "Stopped"),
        )


def test_render_rejects_an_empty_command() -> None:
    with pytest.raises(KimiHookConfigError, match="must not be empty"):
        _render(emitter_command="   ")


@pytest.mark.parametrize("timeout", [0, 601, -1])
def test_render_rejects_out_of_range_timeouts(timeout: int) -> None:
    with pytest.raises(KimiHookConfigError, match="timeout"):
        _render(timeout=timeout)


def test_build_emitter_command_quotes_paths() -> None:
    command = build_emitter_command(
        emitter=Path("/srv/hook dir/emitter.py"),
        python_executable=PYTHON,
    )
    assert shlex.split(command) == [PYTHON, "/srv/hook dir/emitter.py"]


def test_build_emitter_command_defaults_to_the_current_interpreter() -> None:
    command = build_emitter_command(emitter=EMITTER)
    assert shlex.split(command) == [sys.executable, str(EMITTER)]


def test_build_collector_emitter_command_bakes_collector_coordinates() -> None:
    store = Path("/srv/houmao/sessions/abc/hook-observation/kimi")
    command = build_collector_emitter_command(
        port=43123,
        store=store,
        generation=4,
        emitter=EMITTER,
        python_executable=PYTHON,
    )
    assert shlex.split(command) == [
        PYTHON,
        str(EMITTER),
        "--collector-url",
        collector_url(43123),
        "--store",
        str(store),
        "--generation",
        "4",
    ]
    assert collector_url(43123) == "http://127.0.0.1:43123/v1/hook"


def test_quoted_command_round_trips_through_toml() -> None:
    command = build_emitter_command(
        emitter=Path("/srv/hook dir/emitter.py"),
        python_executable=PYTHON,
    )
    entries = _entries(render_observer_block(emitter_command=command, generation=1))
    assert {entry["command"] for entry in entries} == {command}
    assert shlex.split(entries[0]["command"]) == [PYTHON, "/srv/hook dir/emitter.py"]


def test_merge_appends_the_block_and_validates_it() -> None:
    original = 'default_model = "managed:kimi-code/kimi-k2.5"\n'
    merged = merge_observer_block(original, _render(), path=CONFIG_PATH)
    assert merged.startswith(original)
    document = tomllib.loads(merged)
    assert document["default_model"] == "managed:kimi-code/kimi-k2.5"
    assert tuple(entry["event"] for entry in document["hooks"]) == KIMI_EVENTS


def test_launch_policy_fields_written_first_survive_the_merge(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    _write_launch_policy_fields(config_path)
    original = config_path.read_text(encoding="utf-8")

    merged = merge_observer_block(original, _render(), path=config_path)
    assert merged.startswith(original)

    document = tomllib.loads(merged)
    assert document["default_model"] == "managed:kimi-code/kimi-k2.5"
    assert document["default_permission_mode"] == "auto"
    assert document["providers"]["managed"]["type"] == "openai"
    assert document["providers"]["managed"]["base_url"] == "https://example.invalid/v1"
    assert document["models"]["kimi-k2.5"]["provider"] == "managed"
    assert document["models"]["kimi-k2.5"]["model"] == "kimi-k2.5"
    assert tuple(entry["event"] for entry in document["hooks"]) == KIMI_EVENTS
    assert strip_observer_block(merged) == original


def test_launch_policy_fields_written_after_the_block_keep_it_valid(
    tmp_path: Path,
) -> None:
    # The launch-policy TOML writer re-renders scalars ahead of table blocks and
    # cannot serialize an existing `[[hooks]]` array, so production installs run
    # after synthesis. This pins the shape that keeps the reverse order valid.
    block_text = _render()
    text = f"{ROOT_FIELDS}\n{block_text}{PROVIDER_MODEL_TABLES}"
    config_path = tmp_path / "config.toml"
    config_path.write_text(text, encoding="utf-8")

    report = validate_hooks_file(config_path)
    assert report.entry_count == 20
    document = tomllib.loads(text)
    assert document["default_model"] == "managed:kimi-code/kimi-k2.5"
    assert document["default_permission_mode"] == "auto"
    assert document["providers"]["managed"]["type"] == "openai"
    assert document["models"]["kimi-k2.5"]["model"] == "kimi-k2.5"
    assert strip_observer_block(text) == f"{ROOT_FIELDS}{PROVIDER_MODEL_TABLES}"

    rewritten = merge_observer_block(text, _render(generation=2), path=config_path)
    assert rewritten.count(OBSERVER_BLOCK_BEGIN_MARKER) == 1
    assert "generation 1" not in rewritten
    assert "generation 2" in rewritten
    document = tomllib.loads(rewritten)
    assert document["default_permission_mode"] == "auto"
    assert document["providers"]["managed"]["base_url"] == "https://example.invalid/v1"
    assert len(document["hooks"]) == 20


def test_merge_is_idempotent_for_the_same_generation() -> None:
    once = merge_observer_block(ROOT_FIELDS, _render())
    twice = merge_observer_block(once, _render())
    assert twice == once


def test_merge_rewrites_the_block_for_a_new_generation() -> None:
    first = merge_observer_block("", _render(generation=1))
    second = merge_observer_block(first, _render(generation=2))
    assert "generation 1" not in second
    assert "generation 2" in second
    assert second.count(OBSERVER_BLOCK_BEGIN_MARKER) == 1
    assert len(_entries(second)) == 20


@pytest.mark.parametrize(
    "original",
    ["", 'default_model = "x"', 'default_model = "x"\n', 'default_model = "x"\n\n'],
)
def test_strip_restores_the_original_bytes(original: str) -> None:
    merged = merge_observer_block(original, _render())
    assert merged.startswith(original)
    assert strip_observer_block(merged) == original


def test_strip_without_a_block_is_a_noop() -> None:
    text = 'default_model = "x"\n'
    assert strip_observer_block(text) == text


def test_strip_rejects_unbalanced_markers() -> None:
    text = f"{OBSERVER_BLOCK_BEGIN_MARKER} (managed; do not edit; generation 1)\n"
    with pytest.raises(KimiHookConfigError, match="unbalanced"):
        strip_observer_block(text)


def test_operator_hooks_outside_the_block_are_preserved() -> None:
    original = f'default_model = "x"\n\n{OPERATOR_HOOK}'
    merged = merge_observer_block(original, _render())
    assert merged.startswith(original)
    entries = _entries(merged)
    assert len(entries) == 21
    assert entries[0] == {"event": "Stop", "command": "true", "timeout": 5}
    assert strip_observer_block(merged) == original


def test_validation_report_lists_entries_in_declaration_order(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(merge_observer_block("", _render(timeout=7)), encoding="utf-8")
    report = validate_hooks_file(config_path)
    assert report.path == config_path
    assert report.entry_count == 20
    assert report.events == KIMI_EVENTS
    assert report.timeouts == (7,) * 20


def test_validation_refuses_an_extra_key(tmp_path: Path) -> None:
    path = _malformed_config_path(
        tmp_path,
        '[[hooks]]\nevent = "Stop"\ncommand = "true"\ntimeout = 5\ncwd = "/tmp"\n',
    )
    with pytest.raises(KimiHookConfigError, match="unsupported key"):
        validate_hooks_file(path)


def test_validation_refuses_an_unknown_event(tmp_path: Path) -> None:
    path = _malformed_config_path(
        tmp_path,
        '[[hooks]]\nevent = "StopEverything"\ncommand = "true"\ntimeout = 5\n',
    )
    with pytest.raises(KimiHookConfigError, match="unknown event"):
        validate_hooks_file(path)


@pytest.mark.parametrize("timeout", ["5.0", '"5"', "true"])
def test_validation_refuses_non_integer_timeouts(tmp_path: Path, timeout: str) -> None:
    path = _malformed_config_path(
        tmp_path,
        f'[[hooks]]\nevent = "Stop"\ncommand = "true"\ntimeout = {timeout}\n',
    )
    with pytest.raises(KimiHookConfigError, match="timeout must be an integer"):
        validate_hooks_file(path)


@pytest.mark.parametrize("timeout", ["0", "601", "-1"])
def test_validation_refuses_out_of_range_timeouts(tmp_path: Path, timeout: str) -> None:
    path = _malformed_config_path(
        tmp_path,
        f'[[hooks]]\nevent = "Stop"\ncommand = "true"\ntimeout = {timeout}\n',
    )
    with pytest.raises(KimiHookConfigError, match="outside 1..600"):
        validate_hooks_file(path)


def test_validation_refuses_a_missing_timeout(tmp_path: Path) -> None:
    path = _malformed_config_path(
        tmp_path,
        '[[hooks]]\nevent = "Stop"\ncommand = "true"\n',
    )
    with pytest.raises(KimiHookConfigError, match="missing an explicit timeout"):
        validate_hooks_file(path)


def test_validation_refuses_a_missing_hooks_section(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('default_model = "x"\n', encoding="utf-8")
    with pytest.raises(KimiHookConfigError, match="missing events"):
        validate_hooks_file(path)


def test_merge_refuses_a_pre_existing_malformed_entry() -> None:
    bad = '[[hooks]]\nevent = "Stop"\ncommand = "true"\ntimeout = 5\ncwd = "/tmp"\n'
    with pytest.raises(KimiHookConfigError, match="unsupported key"):
        merge_observer_block(bad, _render())


def test_merge_refuses_invalid_toml_input() -> None:
    with pytest.raises(KimiHookConfigError, match="cannot parse TOML"):
        merge_observer_block("this is not toml =", _render())


def test_merge_refuses_a_block_without_markers() -> None:
    with pytest.raises(KimiHookConfigError, match="exactly one marker pair"):
        merge_observer_block(
            "",
            '[[hooks]]\nevent = "Stop"\ncommand = "true"\ntimeout = 5\n',
        )
