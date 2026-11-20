"""Exercise project headless display settings through a real tmux bridge."""

from collections.abc import Iterator
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from click.testing import CliRunner
import pytest

from houmao.agents.realm_controller.runtime import resume_runtime_session
from houmao.execution.tmux import tmux_server_scope
from houmao.srv_ctrl.commands.main import cli


@pytest.fixture
def display_tmux_socket(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """Route launch, probes, and cleanup to a private tmux socket."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is required to exercise the live headless pane")
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SHELL", "/bin/sh")
    with tempfile.TemporaryDirectory(prefix="houmao-display-") as directory:
        socket = Path(directory) / "tmux.sock"
        try:
            with tmux_server_scope(socket):
                yield socket
        finally:
            _tmux(socket, "kill-server", check=False)


def _tmux(socket: Path, *args: str, check: bool = True) -> str:
    """Run a command on the fixture-owned tmux server."""

    return subprocess.run(
        ["tmux", "-S", str(socket), *args],
        capture_output=True,
        text=True,
        check=check,
        timeout=10,
    ).stdout


def _invoke(*args: str) -> dict[str, Any]:
    """Invoke a manager command and decode its leading JSON object."""

    result = CliRunner().invoke(cli, ["--print-json", *args])
    assert result.exit_code == 0, result.output
    payload, _ = json.JSONDecoder().raw_decode(result.output.lstrip())
    assert isinstance(payload, dict)
    return payload


def _install_fixture_codex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Emit deterministic Codex events without starting a model request."""

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    codex = fake_bin / "codex"
    codex.write_text(
        """#!/bin/sh
if [ "${1:-}" = --version ]; then
    echo 'codex-cli 0.169.0'
    exit 0
fi
cat <<'EVENTS'
{"type":"thread.started","thread_id":"headless-display-fixture"}
{"type":"item.completed","item":{"id":"reason","type":"reasoning","text":"Fixture reasoning"}}
{"type":"item.completed","item":{"id":"answer","type":"agent_message","text":"Fixture answer"}}
{"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":0,"output_tokens":2}}
EVENTS
""",
        encoding="utf-8",
    )
    codex.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")


def _manifest(path: Path) -> dict[str, Any]:
    """Read the manifest that the managed session owns."""

    return json.loads(path.read_text(encoding="utf-8"))


def _omit_display_detail(path: Path) -> None:
    """Simulate a supported manifest created before display detail was saved."""

    manifest = _manifest(path)
    manifest["launch_plan"]["metadata"].pop("headless_display_detail", None)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def _assert_live_display(
    socket: Path,
    session_name: str,
    agent_def_dir: Path,
    manifest_path: Path,
    *,
    style: str,
    detail: str,
) -> None:
    """Resume the saved controller and inspect the bridge command and pane output."""

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=manifest_path,
    )
    pane = f"{session_name}:agent"
    _tmux(socket, "resize-window", "-t", pane, "-x", "160", "-y", "40")
    controller.send_prompt("Emit the fixture events.")

    started = _tmux(socket, "display-message", "-p", "-t", pane, "#{pane_start_command}")
    assert f" --style {style} --detail {detail} " in started
    output = _tmux(socket, "capture-pane", "-p", "-J", "-t", pane)
    assert "Fixture answer" in output
    if style == "json":
        events = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
        reasoning = next(event for event in reversed(events) if event["kind"] == "reasoning")
        assert reasoning["message"] == "Fixture reasoning"
        if detail == "detail":
            assert reasoning["payload"]["provider_event_type"] == "item.completed.reasoning"
            assert reasoning["payload"]["raw"]["item"]["id"] == "reason"
        else:
            assert "provider_event_type" not in reasoning["payload"]
            assert "raw" not in reasoning["payload"]
    else:
        assert ("[reasoning] Fixture reasoning" in output) == (detail == "detail")


@pytest.mark.parametrize("style", ["plain", "json"])
def test_headless_launch_display_survives_profile_edit(
    display_tmux_socket: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    style: str,
) -> None:
    """Launch from a profile, then resume and relaunch with the manifest's settings."""

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.chdir(repo_root)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.setenv("HOUMAO_GLOBAL_RUNTIME_DIR", str(tmp_path / "runtime"))
    _install_fixture_codex(tmp_path, monkeypatch)

    init = CliRunner().invoke(cli, ["project", "init"])
    assert init.exit_code == 0, init.output
    auth = tmp_path / "auth.json"
    auth.write_text('{"logged_in": true}\n', encoding="utf-8")
    _invoke(
        "project",
        "specialist",
        "create",
        "--name",
        "display-fixture",
        "--system-prompt",
        "Produce fixture events.",
        "--tool",
        "codex",
        "--api-key",
        "sk-fixture-only",
        "--codex-auth-json",
        str(auth),
    )
    _invoke(
        "project",
        "profile",
        "create",
        "--name",
        "display-profile",
        "--specialist",
        "display-fixture",
        "--agent-name",
        "display-agent",
        "--mode",
        "headless",
        "--no-gateway",
        "--headless-display-style",
        "json" if style == "plain" else "plain",
        "--headless-display-detail",
        "detail",
    )
    launch = _invoke(
        "project",
        "agents",
        "launch",
        "--profile",
        "display-profile",
        "--headless-display-style",
        style,
    )
    manifest_path = Path(launch["manifest_path"])
    agent_def_dir = repo_root / ".houmao" / "agents"
    agent_selector = ["agents", "single", "--agent-name", "display-agent"]
    display = {"style": style, "detail": "detail"}
    metadata = _manifest(manifest_path)["launch_plan"]["metadata"]
    assert metadata["headless_display_style"] == style
    assert metadata["headless_display_detail"] == "detail"

    _invoke(
        "project",
        "profile",
        "set",
        "--name",
        "display-profile",
        "--headless-display-style",
        "fancy",
        "--headless-display-detail",
        "concise",
    )
    session_name = launch["tmux_session_name"]
    _assert_live_display(display_tmux_socket, session_name, agent_def_dir, manifest_path, **display)

    _invoke(*agent_selector, "relaunch")
    metadata = _manifest(manifest_path)["launch_plan"]["metadata"]
    assert metadata["headless_display_style"] == style
    assert metadata["headless_display_detail"] == "detail"
    _assert_live_display(display_tmux_socket, session_name, agent_def_dir, manifest_path, **display)

    if style == "json":
        _invoke(
            "project",
            "profile",
            "set",
            "--name",
            "display-profile",
            "--headless-display-detail",
            "detail",
        )
        fallback = {"style": "json", "detail": "concise"}
        _omit_display_detail(manifest_path)
        _assert_live_display(
            display_tmux_socket, session_name, agent_def_dir, manifest_path, **fallback
        )
        _omit_display_detail(manifest_path)
        _invoke(*agent_selector, "relaunch")
        metadata = _manifest(manifest_path)["launch_plan"]["metadata"]
        assert metadata["headless_display_style"] == "json"
        assert metadata["headless_display_detail"] == "concise"
        _assert_live_display(
            display_tmux_socket, session_name, agent_def_dir, manifest_path, **fallback
        )
