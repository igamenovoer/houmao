"""Unit tests for provider-aware hook observation installation."""

from __future__ import annotations

import json
import stat
import tomllib
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.launch_policy.provider_hooks import set_toml_key
from houmao.hook_observation.codex_hooks_generator import (
    CODEX_EVENTS,
    build_observer_hooks_document,
    render_hooks_state_toml,
)
from houmao.hook_observation.install import (
    CODEX_CONFIG_FILENAME,
    CODEX_HOOKS_FILENAME,
    CODEX_PRETRUST_BEGIN_MARKER,
    CODEX_PRETRUST_END_MARKER,
    HOOK_OBSERVATION_CLAUDE_ENV_FLAG,
    HOOK_OBSERVATION_CODEX_ENV_FLAG,
    HOOK_OBSERVATION_KIMI_ENV_FLAG,
    KIMI_CONFIG_FILENAME,
    ObserverSettingsError,
    allocate_next_generation,
    claude_hook_artifact_dir,
    codex_hook_artifact_dir,
    hook_artifact_dir,
    hook_observation_applies,
    hook_observation_enabled,
    install_codex_observer_configuration,
    install_kimi_observer_configuration,
    kimi_hook_artifact_dir,
    merge_codex_pretrust_block,
    read_channel_generation,
    remove_codex_observer_configuration,
    remove_kimi_observer_configuration,
    render_codex_pretrust_block,
    strip_codex_pretrust_block,
    write_channel_install_status,
    write_launch_wrapper,
)
from houmao.hook_observation.kimi_hooks_generator import (
    KIMI_EVENTS,
    KimiHookConfigError,
    validate_hooks_file,
)
from houmao.hook_observation.trust_hash import hook_hash, hook_state_key, iter_handlers

EMITTER = Path("/srv/houmao/hook_observation/emitter.py")
STALE_EMITTER = Path("/opt/stale/emitter.py")
PYTHON = "/usr/bin/python3"
EMITTER_COMMAND = f"{PYTHON} {EMITTER}"
USER_STATE_KEY = "/opt/operator/hooks.json:stop:0:0"
USER_CONFIG = f'model = "gpt-5"\n\n[hooks.state."{USER_STATE_KEY}"]\ntrusted_hash = "sha256:user"\n'
KIMI_USER_CONFIG = (
    'default_model = "managed:kimi-code/kimi-k2.5"\n'
    'default_permission_mode = "auto"\n'
    '\n[models."kimi-k2.5"]\n'
    'provider = "managed"\n'
    'model = "kimi-k2.5"\n'
)
KIMI_USER_HOOK = '\n[[hooks]]\nevent = "Notification"\ncommand = "notify-send kimi"\ntimeout = 10\n'


def _document(emitter_command: str = EMITTER_COMMAND) -> dict[str, Any]:
    return build_observer_hooks_document(emitter_command=emitter_command)


def _block(
    home_path: Path,
    *,
    generation: int = 1,
    emitter_command: str = EMITTER_COMMAND,
) -> str:
    return render_codex_pretrust_block(
        _document(emitter_command),
        home_path / CODEX_HOOKS_FILENAME,
        generation=generation,
    )


def _state(config_text: str) -> dict[str, Any]:
    return tomllib.loads(config_text)["hooks"]["state"]


def _home(tmp_path: Path) -> Path:
    home = tmp_path / "codex-home"
    home.mkdir()
    return home


def _markerless_config(home_path: Path) -> str:
    state = render_hooks_state_toml(_document(), home_path / CODEX_HOOKS_FILENAME)
    return (
        "[hooks]\n"
        "[hooks.state]\n"
        f"{state}"
        f'[hooks.state."{USER_STATE_KEY}"]\n'
        'trusted_hash = "sha256:user"\n'
    )


def test_enablement_flags_are_per_tool() -> None:
    assert hook_observation_enabled({HOOK_OBSERVATION_CLAUDE_ENV_FLAG: "1"}) is True
    assert hook_observation_enabled({HOOK_OBSERVATION_CLAUDE_ENV_FLAG: "1"}, tool="codex") is False
    assert hook_observation_enabled({HOOK_OBSERVATION_CODEX_ENV_FLAG: "1"}, tool="codex") is True
    assert hook_observation_enabled({HOOK_OBSERVATION_CODEX_ENV_FLAG: "1"}) is False
    assert hook_observation_enabled({}, tool="codex") is False
    assert (
        hook_observation_enabled({HOOK_OBSERVATION_CODEX_ENV_FLAG: "true"}, tool="codex") is False
    )
    assert hook_observation_enabled({HOOK_OBSERVATION_CODEX_ENV_FLAG: "1"}, tool="kimi") is False
    assert hook_observation_enabled({HOOK_OBSERVATION_KIMI_ENV_FLAG: "1"}, tool="kimi") is True
    assert hook_observation_enabled({HOOK_OBSERVATION_KIMI_ENV_FLAG: "1"}) is False
    assert hook_observation_enabled({HOOK_OBSERVATION_KIMI_ENV_FLAG: "1"}, tool="codex") is False
    assert hook_observation_enabled({HOOK_OBSERVATION_CLAUDE_ENV_FLAG: "1"}, tool="kimi") is False
    assert hook_observation_enabled({HOOK_OBSERVATION_KIMI_ENV_FLAG: "true"}, tool="kimi") is False


@pytest.mark.parametrize(
    ("tool", "backend", "expected"),
    [
        ("claude", "local_interactive", True),
        ("codex", "local_interactive", True),
        ("kimi", "local_interactive", True),
        ("claude", "claude_headless", False),
        ("codex", "codex_headless", False),
        ("kimi", "kimi_headless", False),
    ],
)
def test_applicability_covers_supported_tool_backend_pairs(
    tool: str,
    backend: str,
    expected: bool,
) -> None:
    assert hook_observation_applies(tool=tool, backend=backend) is expected


def test_artifact_dirs_are_per_adapter(tmp_path: Path) -> None:
    assert claude_hook_artifact_dir(tmp_path) == tmp_path / "hook-observation" / "claude"
    assert codex_hook_artifact_dir(tmp_path) == tmp_path / "hook-observation" / "codex"
    assert kimi_hook_artifact_dir(tmp_path) == tmp_path / "hook-observation" / "kimi"
    assert hook_artifact_dir(tmp_path, tool="codex") == codex_hook_artifact_dir(tmp_path)
    assert hook_artifact_dir(tmp_path, tool="kimi") == kimi_hook_artifact_dir(tmp_path)
    with pytest.raises(ValueError):
        hook_artifact_dir(tmp_path, tool="gemini")


def test_generation_counters_are_per_adapter(tmp_path: Path) -> None:
    assert allocate_next_generation(tmp_path, tool="codex") == 1
    assert allocate_next_generation(tmp_path, tool="codex") == 2
    assert allocate_next_generation(tmp_path) == 1
    assert allocate_next_generation(tmp_path) == 2

    assert read_channel_generation(tmp_path, tool="codex") == 2
    assert read_channel_generation(tmp_path) == 2
    codex_counter = codex_hook_artifact_dir(tmp_path) / "generation.json"
    claude_counter = claude_hook_artifact_dir(tmp_path) / "generation.json"
    assert json.loads(codex_counter.read_text(encoding="utf-8"))["generation"] == 2
    assert json.loads(claude_counter.read_text(encoding="utf-8"))["generation"] == 2
    assert stat.S_IMODE(codex_counter.stat().st_mode) == 0o600


def test_launch_wrapper_and_channel_status_are_adapter_scoped(tmp_path: Path) -> None:
    wrapper = write_launch_wrapper(
        session_root=tmp_path,
        script="export HOUMAO_HOOK_TOKEN=secret\n",
        tool="codex",
    )
    assert wrapper == codex_hook_artifact_dir(tmp_path) / "launch-wrapper.sh"
    assert stat.S_IMODE(wrapper.stat().st_mode) == 0o600

    write_channel_install_status(
        session_root=tmp_path,
        generation=1,
        install_path="managed_home",
        channel_state="installing",
        detail="codex install",
        tool="codex",
    )

    channel = json.loads(
        (codex_hook_artifact_dir(tmp_path) / "channel.json").read_text(encoding="utf-8")
    )
    assert channel["channel_state"] == "installing"
    assert channel["install"]["path"] == "managed_home"
    assert not (claude_hook_artifact_dir(tmp_path) / "channel.json").exists()


def test_pretrust_block_covers_every_generated_handler(tmp_path: Path) -> None:
    document = _document()
    hooks_path = tmp_path / CODEX_HOOKS_FILENAME
    block = render_codex_pretrust_block(document, hooks_path, generation=7)

    assert block.startswith(f"{CODEX_PRETRUST_BEGIN_MARKER} (managed; do not edit; generation 7)")
    assert block.endswith(f"{CODEX_PRETRUST_END_MARKER}\n")

    expected: dict[str, Any] = {}
    for event_name, group_index, handler_index, matcher, handler in iter_handlers(document):
        key = hook_state_key(hooks_path, event_name, group_index, handler_index)
        expected[key] = {"trusted_hash": hook_hash(event_name, matcher, handler)}
    state = _state(block)
    assert state == expected
    assert len(state) == len(CODEX_EVENTS) == 14


def test_merge_preserves_operator_config_and_state(tmp_path: Path) -> None:
    merged = merge_codex_pretrust_block(USER_CONFIG, _block(tmp_path))

    assert merged.startswith(USER_CONFIG)
    state = _state(merged)
    assert state[USER_STATE_KEY] == {"trusted_hash": "sha256:user"}
    managed = {
        key: value for key, value in state.items() if str(tmp_path / CODEX_HOOKS_FILENAME) in key
    }
    assert len(managed) == len(CODEX_EVENTS)


def test_merge_is_idempotent(tmp_path: Path) -> None:
    block = _block(tmp_path)

    once = merge_codex_pretrust_block(USER_CONFIG, block)
    twice = merge_codex_pretrust_block(once, block)

    assert twice == once
    assert once.count(CODEX_PRETRUST_BEGIN_MARKER) == 1


def test_new_generation_replaces_the_stale_block(tmp_path: Path) -> None:
    stale = merge_codex_pretrust_block(
        "",
        _block(tmp_path, generation=1, emitter_command=f"{PYTHON} {STALE_EMITTER}"),
    )
    stale_state = _state(stale)

    refreshed = merge_codex_pretrust_block(
        stale,
        _block(tmp_path, generation=2),
    )
    refreshed_state = _state(refreshed)

    assert refreshed.count(CODEX_PRETRUST_BEGIN_MARKER) == 1
    assert "generation 2" in refreshed
    assert refreshed_state != stale_state
    assert len(refreshed_state) == len(CODEX_EVENTS)


def test_strip_removes_only_the_managed_block(tmp_path: Path) -> None:
    merged = merge_codex_pretrust_block(USER_CONFIG, _block(tmp_path))

    stripped = strip_codex_pretrust_block(merged)

    assert CODEX_PRETRUST_BEGIN_MARKER not in stripped
    assert CODEX_PRETRUST_END_MARKER not in stripped
    assert stripped.startswith(USER_CONFIG)
    assert _state(stripped) == {USER_STATE_KEY: {"trusted_hash": "sha256:user"}}
    assert strip_codex_pretrust_block(USER_CONFIG) == USER_CONFIG


def test_merge_repairs_markerless_tables_after_toml_rerender(tmp_path: Path) -> None:
    home = _home(tmp_path)
    markerless = _markerless_config(home)
    assert len(markerless.splitlines()) > len(CODEX_EVENTS)

    merged = merge_codex_pretrust_block(
        markerless,
        _block(home),
        hooks_json_path=home / CODEX_HOOKS_FILENAME,
    )

    assert merged.count(CODEX_PRETRUST_BEGIN_MARKER) == 1
    state = _state(merged)
    assert state[USER_STATE_KEY] == {"trusted_hash": "sha256:user"}
    assert len(state) == len(CODEX_EVENTS) + 1


def test_strip_removes_markerless_tables(tmp_path: Path) -> None:
    home = _home(tmp_path)

    stripped = strip_codex_pretrust_block(
        _markerless_config(home),
        hooks_json_path=home / CODEX_HOOKS_FILENAME,
    )

    assert _state(stripped) == {USER_STATE_KEY: {"trusted_hash": "sha256:user"}}


def test_unbalanced_marker_block_is_rejected() -> None:
    text = f"{CODEX_PRETRUST_BEGIN_MARKER} (generation 1)\n[hooks.state]\n"

    with pytest.raises(ObserverSettingsError):
        strip_codex_pretrust_block(text)
    with pytest.raises(ObserverSettingsError):
        merge_codex_pretrust_block(text, "")


def test_merge_rejects_malformed_config(tmp_path: Path) -> None:
    with pytest.raises(ObserverSettingsError):
        merge_codex_pretrust_block("model = [\n", _block(tmp_path))


def test_install_defaults_to_the_packaged_emitter(tmp_path: Path) -> None:
    home = _home(tmp_path)

    result = install_codex_observer_configuration(
        home_path=home,
        generation=1,
        python_executable=PYTHON,
    )

    assert result.install_path == "managed_home"
    hooks = json.loads((home / CODEX_HOOKS_FILENAME).read_text(encoding="utf-8"))
    command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert command.startswith(f"{PYTHON} ")
    assert command.endswith("/emitter.py")


def test_install_writes_hooks_and_pretrust_block(tmp_path: Path) -> None:
    home = _home(tmp_path)

    result = install_codex_observer_configuration(
        home_path=home,
        generation=3,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "managed_home"
    assert result.generation == 3
    assert result.hooks_path == home / CODEX_HOOKS_FILENAME
    assert result.config_path == home / CODEX_CONFIG_FILENAME
    assert result.detail is None

    hooks_path = home / CODEX_HOOKS_FILENAME
    config_path = home / CODEX_CONFIG_FILENAME
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    assert tuple(hooks["hooks"]) == CODEX_EVENTS
    for event_name in CODEX_EVENTS:
        handler = hooks["hooks"][event_name][0]["hooks"][0]
        assert handler["command"] == EMITTER_COMMAND

    config_text = config_path.read_text(encoding="utf-8")
    assert "generation 3" in config_text
    assert _state(config_text) == _state(render_hooks_state_toml(hooks, hooks_path))
    assert stat.S_IMODE(hooks_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600


def test_install_accepts_a_fully_rendered_emitter_command(tmp_path: Path) -> None:
    home = _home(tmp_path)
    command = (
        f"{PYTHON} {EMITTER} --collector-url http://127.0.0.1:4321/v1/hook "
        f"--store {tmp_path / 'store'} --generation 3"
    )

    result = install_codex_observer_configuration(
        home_path=home,
        generation=3,
        emitter_command=command,
    )

    assert result.install_path == "managed_home"
    hooks_path = home / CODEX_HOOKS_FILENAME
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    for event_name in CODEX_EVENTS:
        handler = hooks["hooks"][event_name][0]["hooks"][0]
        assert handler["command"] == command
    config_text = (home / CODEX_CONFIG_FILENAME).read_text(encoding="utf-8")
    assert _state(config_text) == _state(render_hooks_state_toml(hooks, hooks_path))


def test_install_degrades_when_emitter_inputs_conflict(tmp_path: Path) -> None:
    home = _home(tmp_path)

    result = install_codex_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        emitter_command=f"{PYTHON} {EMITTER}",
        python_executable=PYTHON,
    )

    assert result.install_path == "unavailable"
    assert "either" in (result.detail or "")
    assert not (home / CODEX_HOOKS_FILENAME).exists()


def test_install_preserves_operator_config_lines(tmp_path: Path) -> None:
    home = _home(tmp_path)
    config_path = home / CODEX_CONFIG_FILENAME
    config_path.write_text(USER_CONFIG, encoding="utf-8")

    result = install_codex_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "managed_home"
    config_text = config_path.read_text(encoding="utf-8")
    assert config_text.startswith(USER_CONFIG)
    state = _state(config_text)
    assert state[USER_STATE_KEY] == {"trusted_hash": "sha256:user"}
    assert len(state) == len(CODEX_EVENTS) + 1


def test_install_repairs_markerless_tables_after_external_rewrite(tmp_path: Path) -> None:
    home = _home(tmp_path)
    config_path = home / CODEX_CONFIG_FILENAME
    config_path.write_text(_markerless_config(home), encoding="utf-8")

    result = install_codex_observer_configuration(
        home_path=home,
        generation=2,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "managed_home"
    config_text = config_path.read_text(encoding="utf-8")
    assert config_text.count(CODEX_PRETRUST_BEGIN_MARKER) == 1
    state = _state(config_text)
    assert state[USER_STATE_KEY] == {"trusted_hash": "sha256:user"}
    assert len(state) == len(CODEX_EVENTS) + 1


def test_install_repairs_after_the_launch_policy_toml_rerender(tmp_path: Path) -> None:
    home = _home(tmp_path)
    config_path = home / CODEX_CONFIG_FILENAME
    first = install_codex_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )
    assert first.install_path == "managed_home"

    set_toml_key(
        path=config_path,
        key_path=("projects", str(home), "trust_level"),
        value="trusted",
    )
    rerendered = config_path.read_text(encoding="utf-8")
    assert CODEX_PRETRUST_BEGIN_MARKER not in rerendered
    assert len(_state(rerendered)) == len(CODEX_EVENTS)

    second = install_codex_observer_configuration(
        home_path=home,
        generation=2,
        emitter=EMITTER,
        python_executable=PYTHON,
    )
    assert second.install_path == "managed_home"
    repaired = config_path.read_text(encoding="utf-8")
    assert repaired.count(CODEX_PRETRUST_BEGIN_MARKER) == 1
    payload = tomllib.loads(repaired)
    assert len(payload["hooks"]["state"]) == len(CODEX_EVENTS)
    assert payload["projects"][str(home)]["trust_level"] == "trusted"


def test_install_rewrites_the_block_per_generation_and_is_idempotent(tmp_path: Path) -> None:
    home = _home(tmp_path)

    first = install_codex_observer_configuration(
        home_path=home,
        generation=1,
        emitter=STALE_EMITTER,
        python_executable=PYTHON,
    )
    assert first.install_path == "managed_home"
    config_path = home / CODEX_CONFIG_FILENAME
    hooks_path = home / CODEX_HOOKS_FILENAME
    first_text = config_path.read_text(encoding="utf-8")
    assert str(STALE_EMITTER) in hooks_path.read_text(encoding="utf-8")

    second = install_codex_observer_configuration(
        home_path=home,
        generation=2,
        emitter=EMITTER,
        python_executable=PYTHON,
    )
    assert second.install_path == "managed_home"
    second_text = config_path.read_text(encoding="utf-8")
    assert second_text != first_text
    assert second_text.count(CODEX_PRETRUST_BEGIN_MARKER) == 1
    assert "generation 2" in second_text
    assert str(STALE_EMITTER) not in hooks_path.read_text(encoding="utf-8")
    assert len(_state(second_text)) == len(CODEX_EVENTS)

    repeated = install_codex_observer_configuration(
        home_path=home,
        generation=2,
        emitter=EMITTER,
        python_executable=PYTHON,
    )
    assert repeated.install_path == "managed_home"
    assert config_path.read_text(encoding="utf-8") == second_text


def test_install_degrades_on_malformed_config(tmp_path: Path) -> None:
    home = _home(tmp_path)
    config_path = home / CODEX_CONFIG_FILENAME
    config_path.write_text("model = [\n", encoding="utf-8")

    result = install_codex_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "unavailable"
    assert result.hooks_path is None
    assert result.config_path is None
    assert "TOML" in (result.detail or "")
    assert not (home / CODEX_HOOKS_FILENAME).exists()
    assert config_path.read_text(encoding="utf-8") == "model = [\n"


def test_install_replaces_a_stale_unmarked_state_key(tmp_path: Path) -> None:
    home = _home(tmp_path)
    hooks_path = home / CODEX_HOOKS_FILENAME
    stale_key = hook_state_key(hooks_path, "Stop", 0, 0)
    config_path = home / CODEX_CONFIG_FILENAME
    config_path.write_text(
        f'[hooks.state."{stale_key}"]\ntrusted_hash = "sha256:stale"\n',
        encoding="utf-8",
    )

    result = install_codex_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "managed_home"
    state = _state(config_path.read_text(encoding="utf-8"))
    assert state[stale_key]["trusted_hash"] != "sha256:stale"
    assert len(state) == len(CODEX_EVENTS)


def test_install_degrades_on_symlinked_hooks_file(tmp_path: Path) -> None:
    home = _home(tmp_path)
    target = tmp_path / "operator-hooks.json"
    target.write_text("{}\n", encoding="utf-8")
    (home / CODEX_HOOKS_FILENAME).symlink_to(target)

    result = install_codex_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "unavailable"
    assert "symlink" in (result.detail or "")
    assert target.read_text(encoding="utf-8") == "{}\n"
    assert not (home / CODEX_CONFIG_FILENAME).exists()


def test_install_degrades_on_symlinked_config(tmp_path: Path) -> None:
    home = _home(tmp_path)
    target = tmp_path / "operator-config.toml"
    target.write_text('model = "gpt-5"\n', encoding="utf-8")
    (home / CODEX_CONFIG_FILENAME).symlink_to(target)

    result = install_codex_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "unavailable"
    assert "symlink" in (result.detail or "")
    assert target.read_text(encoding="utf-8") == 'model = "gpt-5"\n'
    assert not (home / CODEX_HOOKS_FILENAME).exists()


def test_install_degrades_when_the_runtime_home_is_missing(tmp_path: Path) -> None:
    result = install_codex_observer_configuration(
        home_path=tmp_path / "missing-home",
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "unavailable"
    assert "missing" in (result.detail or "")


def test_remove_cleans_managed_artifacts_and_preserves_operator_state(tmp_path: Path) -> None:
    home = _home(tmp_path)
    config_path = home / CODEX_CONFIG_FILENAME
    config_path.write_text(USER_CONFIG, encoding="utf-8")
    installed = install_codex_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )
    assert installed.install_path == "managed_home"

    remove_codex_observer_configuration(home_path=home)

    assert not (home / CODEX_HOOKS_FILENAME).exists()
    config_text = config_path.read_text(encoding="utf-8")
    assert CODEX_PRETRUST_BEGIN_MARKER not in config_text
    assert CODEX_PRETRUST_END_MARKER not in config_text
    assert config_text.startswith(USER_CONFIG)
    assert _state(config_text) == {USER_STATE_KEY: {"trusted_hash": "sha256:user"}}


def test_remove_strips_markerless_tables_after_external_rewrite(tmp_path: Path) -> None:
    home = _home(tmp_path)
    config_path = home / CODEX_CONFIG_FILENAME
    config_path.write_text(_markerless_config(home), encoding="utf-8")

    remove_codex_observer_configuration(home_path=home)

    assert _state(config_path.read_text(encoding="utf-8")) == {
        USER_STATE_KEY: {"trusted_hash": "sha256:user"}
    }


def test_remove_tolerates_missing_home_and_malformed_config(tmp_path: Path) -> None:
    remove_codex_observer_configuration(home_path=tmp_path / "missing-home")

    home = _home(tmp_path)
    config_path = home / CODEX_CONFIG_FILENAME
    config_path.write_text("model = [\n", encoding="utf-8")
    remove_codex_observer_configuration(home_path=home)
    assert config_path.read_text(encoding="utf-8") == "model = [\n"


def _kimi_home(tmp_path: Path) -> Path:
    home = tmp_path / "kimi-home"
    home.mkdir()
    return home


def _kimi_observer_entries(
    config_text: str,
    emitter_command: str = EMITTER_COMMAND,
) -> list[dict[str, Any]]:
    hooks = tomllib.loads(config_text)["hooks"]
    return [entry for entry in hooks if entry["command"] == emitter_command]


def test_kimi_install_writes_a_validated_block_alongside_operator_config(
    tmp_path: Path,
) -> None:
    home = _kimi_home(tmp_path)
    config_path = home / KIMI_CONFIG_FILENAME
    config_path.write_text(KIMI_USER_CONFIG + KIMI_USER_HOOK, encoding="utf-8")
    original_mode = stat.S_IMODE(config_path.stat().st_mode)

    result = install_kimi_observer_configuration(
        home_path=home,
        generation=3,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "managed_home"
    assert result.generation == 3
    assert result.config_path == config_path
    assert result.detail is None

    config_text = config_path.read_text(encoding="utf-8")
    assert config_text.startswith(KIMI_USER_CONFIG + KIMI_USER_HOOK)
    assert config_text.count("[[hooks]]") == len(KIMI_EVENTS) + 1
    assert "generation 3" in config_text
    document = tomllib.loads(config_text)
    assert document["default_model"] == "managed:kimi-code/kimi-k2.5"
    assert document["models"]["kimi-k2.5"]["provider"] == "managed"

    observer = _kimi_observer_entries(config_text)
    assert [entry["event"] for entry in observer] == list(KIMI_EVENTS)
    for entry in observer:
        assert set(entry) == {"event", "command", "timeout"}
        assert entry["timeout"] == 5
    operator = [entry for entry in document["hooks"] if entry["command"] == "notify-send kimi"]
    assert operator == [{"event": "Notification", "command": "notify-send kimi", "timeout": 10}]

    report = validate_hooks_file(config_path)
    assert report.entry_count == len(KIMI_EVENTS) + 1
    assert stat.S_IMODE(config_path.stat().st_mode) == original_mode


def test_kimi_install_accepts_a_fully_rendered_emitter_command(tmp_path: Path) -> None:
    home = _kimi_home(tmp_path)
    command = (
        f"{PYTHON} {EMITTER} --collector-url http://127.0.0.1:4321/v1/hook "
        f"--store {tmp_path / 'store'} --generation 3"
    )

    result = install_kimi_observer_configuration(
        home_path=home,
        generation=3,
        emitter_command=command,
    )

    assert result.install_path == "managed_home"
    config_text = (home / KIMI_CONFIG_FILENAME).read_text(encoding="utf-8")
    assert len(_kimi_observer_entries(config_text, emitter_command=command)) == len(KIMI_EVENTS)


def test_kimi_install_degrades_on_an_unvalidatable_operator_hook(tmp_path: Path) -> None:
    home = _kimi_home(tmp_path)
    config_path = home / KIMI_CONFIG_FILENAME
    original = (
        KIMI_USER_CONFIG
        + '\n[[hooks]]\nevent = "Stop"\ncommand = "operator-hook"\ntimeout = 5\n'
        + 'unsupported = "key"\n'
    )
    config_path.write_text(original, encoding="utf-8")

    result = install_kimi_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "unavailable"
    assert result.config_path is None
    assert "unsupported key" in (result.detail or "")
    assert config_path.read_text(encoding="utf-8") == original


def test_kimi_install_degrades_on_malformed_config(tmp_path: Path) -> None:
    home = _kimi_home(tmp_path)
    config_path = home / KIMI_CONFIG_FILENAME
    config_path.write_text("default_model = [\n", encoding="utf-8")

    result = install_kimi_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "unavailable"
    assert result.config_path is None
    assert "TOML" in (result.detail or "")
    assert config_path.read_text(encoding="utf-8") == "default_model = [\n"


def test_kimi_install_degrades_on_symlinked_config(tmp_path: Path) -> None:
    home = _kimi_home(tmp_path)
    target = tmp_path / "operator-config.toml"
    target.write_text(KIMI_USER_CONFIG, encoding="utf-8")
    (home / KIMI_CONFIG_FILENAME).symlink_to(target)

    result = install_kimi_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "unavailable"
    assert "symlink" in (result.detail or "")
    assert target.read_text(encoding="utf-8") == KIMI_USER_CONFIG


def test_kimi_install_degrades_when_the_runtime_home_is_missing(tmp_path: Path) -> None:
    result = install_kimi_observer_configuration(
        home_path=tmp_path / "missing-home",
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "unavailable"
    assert "missing" in (result.detail or "")


def test_kimi_install_restores_config_after_a_failed_read_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = _kimi_home(tmp_path)
    config_path = home / KIMI_CONFIG_FILENAME
    config_path.write_text(KIMI_USER_CONFIG, encoding="utf-8")

    def _fail_read_back(path: Path, **kwargs: object) -> None:
        del path, kwargs
        raise KimiHookConfigError("simulated read-back failure")

    monkeypatch.setattr(
        "houmao.hook_observation.kimi_hooks_generator.validate_hooks_file",
        _fail_read_back,
    )

    result = install_kimi_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "unavailable"
    assert "simulated read-back failure" in (result.detail or "")
    assert config_path.read_text(encoding="utf-8") == KIMI_USER_CONFIG


def test_kimi_install_degrades_on_a_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = _kimi_home(tmp_path)
    config_path = home / KIMI_CONFIG_FILENAME
    config_path.write_text(KIMI_USER_CONFIG, encoding="utf-8")

    def _fail_write(path: Path, text: str, *, mode: int) -> None:
        del path, text, mode
        raise OSError("simulated write failure")

    monkeypatch.setattr(
        "houmao.hook_observation.install._write_text_atomic",
        _fail_write,
    )

    result = install_kimi_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )

    assert result.install_path == "unavailable"
    assert "simulated write failure" in (result.detail or "")
    assert config_path.read_text(encoding="utf-8") == KIMI_USER_CONFIG


def test_kimi_install_rewrites_the_block_per_generation_and_is_idempotent(
    tmp_path: Path,
) -> None:
    home = _kimi_home(tmp_path)
    config_path = home / KIMI_CONFIG_FILENAME
    config_path.write_text(KIMI_USER_CONFIG, encoding="utf-8")

    first = install_kimi_observer_configuration(
        home_path=home,
        generation=1,
        emitter=STALE_EMITTER,
        python_executable=PYTHON,
    )
    assert first.install_path == "managed_home"
    first_text = config_path.read_text(encoding="utf-8")
    assert str(STALE_EMITTER) in first_text
    assert "generation 1" in first_text

    second = install_kimi_observer_configuration(
        home_path=home,
        generation=2,
        emitter=EMITTER,
        python_executable=PYTHON,
    )
    assert second.install_path == "managed_home"
    second_text = config_path.read_text(encoding="utf-8")
    assert second_text != first_text
    assert second_text.count("# >>> houmao kimi hook observation") == 1
    assert "generation 2" in second_text
    assert str(STALE_EMITTER) not in second_text
    assert second_text.startswith(KIMI_USER_CONFIG)
    assert [entry["event"] for entry in _kimi_observer_entries(second_text)] == list(KIMI_EVENTS)

    repeated = install_kimi_observer_configuration(
        home_path=home,
        generation=2,
        emitter=EMITTER,
        python_executable=PYTHON,
    )
    assert repeated.install_path == "managed_home"
    assert config_path.read_text(encoding="utf-8") == second_text


def test_kimi_remove_restores_operator_config_bytes(tmp_path: Path) -> None:
    home = _kimi_home(tmp_path)
    config_path = home / KIMI_CONFIG_FILENAME
    original = KIMI_USER_CONFIG + KIMI_USER_HOOK
    config_path.write_text(original, encoding="utf-8")
    installed = install_kimi_observer_configuration(
        home_path=home,
        generation=1,
        emitter=EMITTER,
        python_executable=PYTHON,
    )
    assert installed.install_path == "managed_home"
    assert "# >>> houmao kimi hook observation" in config_path.read_text(encoding="utf-8")

    remove_kimi_observer_configuration(home_path=home)

    assert config_path.read_text(encoding="utf-8") == original
    hooks = tomllib.loads(original)["hooks"]
    assert hooks == [{"event": "Notification", "command": "notify-send kimi", "timeout": 10}]


def test_kimi_remove_tolerates_missing_home_and_malformed_config(tmp_path: Path) -> None:
    remove_kimi_observer_configuration(home_path=tmp_path / "missing-home")

    home = _kimi_home(tmp_path)
    config_path = home / KIMI_CONFIG_FILENAME
    config_path.write_text("default_model = [\n", encoding="utf-8")
    remove_kimi_observer_configuration(home_path=home)
    assert config_path.read_text(encoding="utf-8") == "default_model = [\n"
