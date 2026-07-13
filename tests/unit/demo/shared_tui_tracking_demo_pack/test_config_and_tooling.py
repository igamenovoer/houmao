from __future__ import annotations

import tomllib
from pathlib import Path
from types import SimpleNamespace

from houmao.demo.shared_tui_tracking_demo_pack import driver, sweep, tooling
from houmao.demo.shared_tui_tracking_demo_pack.config import resolve_demo_config
from houmao.demo.shared_tui_tracking_demo_pack.schema_validation import (
    load_schema,
    validate_demo_config_document,
)
from houmao.shared_tui_tracking.registry import DetectorProfileRegistry, app_id_from_tool


_WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
_DEMO_CONFIG_PATH = _WORKSPACE_ROOT / "scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml"


def test_default_demo_config_accepts_kimi_tool() -> None:
    payload = tomllib.loads(_DEMO_CONFIG_PATH.read_text(encoding="utf-8"))

    validated = validate_demo_config_document(payload=payload, config_path=_DEMO_CONFIG_PATH)
    resolved = resolve_demo_config(repo_root=_WORKSPACE_ROOT)

    assert validated.tools.kimi.recipe_path.endswith("interactive-watch-kimi-default.yaml")
    assert resolved.tool_config(tool="kimi").operator_prompt_mode == "unattended"
    assert "kimi" in load_schema()["$defs"]["DemoToolsConfigV1"]["required"]


def test_driver_accepts_kimi_tool_choices() -> None:
    parser = driver._build_parser()

    start_args = parser.parse_args(["start", "--tool", "kimi"])
    validate_args = parser.parse_args(
        ["recorded-validate", "--fixture-root", "fixture-root", "--tool", "kimi"]
    )

    assert start_args.tool == "kimi"
    assert validate_args.tool == "kimi"


def test_sweep_infers_kimi_from_fixture_path() -> None:
    assert sweep._infer_tool_from_path(Path("tests/fixtures/shared_tui_tracking/kimi/case")) == (
        "kimi"
    )


def test_kimi_tool_resolves_shared_tracking_profile() -> None:
    profile = DetectorProfileRegistry.default().resolve(
        app_id=app_id_from_tool(tool="kimi"),
        observed_version=None,
    )

    assert profile.app_id == "kimi_code"
    assert profile.profile.detector_name == "kimi_code"


def test_find_supported_process_pid_matches_kimi_executables(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tooling, "process_is_alive", lambda _pid: True)
    monkeypatch.setattr(
        tooling,
        "process_tree",
        lambda: {
            10: {"ppid": 1, "args": "bash launch.sh"},
            11: {"ppid": 10, "args": "/home/user/.kimi-code/bin/kimi"},
            12: {"ppid": 10, "args": "helper"},
        },
    )

    assert tooling.find_supported_process_pid(root_pid=10, tool="kimi") == 11


def test_detect_tool_version_tries_kimi_candidates(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        if command[0] == "kimi":
            raise FileNotFoundError
        return SimpleNamespace(stdout="kimi-code 0.1.0\n", stderr="")

    monkeypatch.setattr(tooling.subprocess, "run", fake_run)

    assert tooling.detect_tool_version(tool="kimi") == "kimi-code 0.1.0"
    assert calls == [["kimi", "--version"], ["kimi-code", "--version"]]


def test_launch_tmux_session_can_retain_restart_shell(tmp_path: Path, monkeypatch) -> None:
    """Long-horizon exit tests keep a shell beneath the provider process."""

    commands: list[list[str]] = []

    def fake_tmux(command: list[str]):
        commands.append(command)
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(tooling, "run_tmux", fake_tmux)
    launch_script = tmp_path / "launch helper.sh"

    tooling.launch_tmux_session(
        session_name="session",
        workdir=tmp_path,
        launch_script=launch_script,
        retain_shell_after_exit=True,
    )

    assert commands[0][-3:-1] == ["bash", "-lc"]
    assert commands[0][-1].endswith("; exec bash --noprofile --norc")
    assert "'" in commands[0][-1]
    assert commands[1] == ["set-option", "-t", "session", "remain-on-exit", "on"]
