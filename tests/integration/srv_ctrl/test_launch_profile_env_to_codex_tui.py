from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import CliRunner

from houmao.srv_ctrl.commands.main import cli


HTTP_PROXY_VALUE = "http://127.0.0.1:7990"
HTTPS_PROXY_VALUE = "http://127.0.0.1:7990"
FEATURE_FLAG_VALUE = "profile-env"


def _load_first_json_object(output: str) -> dict[str, Any]:
    """Decode the first JSON object from CLI output that may include handoff text."""

    payload, _ = json.JSONDecoder().raw_decode(output.lstrip())
    assert isinstance(payload, dict)
    return payload


def _run_tmux(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run one tmux command for the live integration harness."""

    return subprocess.run(
        ["tmux", *args],
        check=check,
        capture_output=True,
        text=True,
    )


def _wait_for_file(path: Path, *, timeout_seconds: float = 10.0) -> str:
    """Wait until one file exists and return its UTF-8 content."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if path.is_file():
            return path.read_text(encoding="utf-8")
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {path}")


def _write_fake_codex(fake_bin: Path, *, capture_path: Path, ready_path: Path) -> Path:
    """Create a fake Codex TUI executable that records inherited proxy env vars."""

    fake_codex = fake_bin / "codex"
    fake_bin.mkdir(parents=True, exist_ok=True)
    quoted_capture_path = shlex.quote(str(capture_path))
    quoted_ready_path = shlex.quote(str(ready_path))
    fake_codex.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -eu",
                'if [[ "${1:-}" == "--version" ]]; then',
                '  printf "codex-cli 0.116.0\\n"',
                "  exit 0",
                "fi",
                (
                    "{ env | grep -E '^(http_proxy|https_proxy|FEATURE_FLAG_X)=' || true; } "
                    f"| sort > {quoted_capture_path}"
                ),
                f"touch {quoted_ready_path}",
                'exec -a codex sleep "${CODEX_FAKE_SLEEP_SECONDS:-60}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)
    return fake_codex


def _set_project_codex_executable(repo_root: Path, executable: Path) -> None:
    """Point the temporary project Codex adapter at the fake executable."""

    adapter_path = repo_root / ".houmao" / "agents" / "tools" / "codex" / "adapter.yaml"
    adapter_payload = yaml.safe_load(adapter_path.read_text(encoding="utf-8"))
    adapter_payload["launch"]["executable"] = str(executable)
    adapter_path.write_text(yaml.safe_dump(adapter_payload, sort_keys=False), encoding="utf-8")


@pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux is required")
def test_easy_profile_env_reaches_codex_tui_tmux_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Launch a Codex TUI from an easy profile and verify profile proxy env propagation."""

    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    workdir = (tmp_path / "workdir").resolve()
    fake_bin = (tmp_path / "fake-bin").resolve()
    capture_path = (tmp_path / "codex-env.txt").resolve()
    ready_path = (tmp_path / "codex-ready").resolve()
    tmux_env_path = (tmp_path / "tmux-env.txt").resolve()
    run_id = uuid.uuid4().hex[:8]
    agent_name = f"proxy-agent-{run_id}"
    session_name = f"hm-env-proxy-{run_id}"
    auth_json_path = (tmp_path / "auth.json").resolve()

    repo_root.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(parents=True, exist_ok=True)
    auth_json_path.write_text('{"logged_in": true}\n', encoding="utf-8")
    fake_codex = _write_fake_codex(fake_bin, capture_path=capture_path, ready_path=ready_path)

    monkeypatch.chdir(repo_root)
    monkeypatch.setenv("PATH", f"{fake_bin}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("CODEX_FAKE_SLEEP_SECONDS", "3")

    tmux_available = _run_tmux(["-V"], check=False)
    if tmux_available.returncode != 0:
        pytest.skip(f"tmux is not usable: {tmux_available.stderr or tmux_available.stdout}")

    try:
        init_result = runner.invoke(cli, ["project", "init"])
        assert init_result.exit_code == 0, init_result.output

        create_specialist = runner.invoke(
            cli,
            [
                "--print-json",
                "project",
                "easy",
                "specialist",
                "create",
                "--name",
                "researcher",
                "--system-prompt",
                "You are a precise repo researcher.",
                "--tool",
                "codex",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
            ],
        )
        assert create_specialist.exit_code == 0, create_specialist.output
        _set_project_codex_executable(repo_root, fake_codex)

        create_profile = runner.invoke(
            cli,
            [
                "--print-json",
                "project",
                "easy",
                "profile",
                "create",
                "--name",
                "proxy-profile",
                "--specialist",
                "researcher",
                "--agent-name",
                agent_name,
                "--workdir",
                str(workdir),
                "--no-gateway",
                "--env-set",
                f"http_proxy={HTTP_PROXY_VALUE}",
                "--env-set",
                f"https_proxy={HTTPS_PROXY_VALUE}",
                "--env-set",
                f"FEATURE_FLAG_X={FEATURE_FLAG_VALUE}",
            ],
        )
        assert create_profile.exit_code == 0, create_profile.output
        profile_payload = _load_first_json_object(create_profile.output)
        assert profile_payload["defaults"]["env"] == {
            "FEATURE_FLAG_X": FEATURE_FLAG_VALUE,
            "http_proxy": HTTP_PROXY_VALUE,
            "https_proxy": HTTPS_PROXY_VALUE,
        }

        launch_result = runner.invoke(
            cli,
            [
                "--print-json",
                "project",
                "easy",
                "instance",
                "launch",
                "--profile",
                "proxy-profile",
                "--session-name",
                session_name,
                "--no-gateway",
            ],
        )
        assert launch_result.exit_code == 0, launch_result.output
        launch_payload = _load_first_json_object(launch_result.output)
        assert launch_payload["tmux_session_name"] == session_name

        codex_env = _wait_for_file(capture_path)
        assert f"FEATURE_FLAG_X={FEATURE_FLAG_VALUE}" in codex_env
        assert f"http_proxy={HTTP_PROXY_VALUE}" in codex_env
        assert f"https_proxy={HTTPS_PROXY_VALUE}" in codex_env

        pane = _run_tmux(
            ["list-panes", "-t", f"{session_name}:agent", "-F", "#{pane_id}"]
        ).stdout.splitlines()[0]

        grep_command = f"env | grep proxy | sort > {shlex.quote(str(tmux_env_path))}"
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and not tmux_env_path.is_file():
            _run_tmux(["send-keys", "-t", pane, grep_command, "C-m"], check=False)
            time.sleep(0.2)

        tmux_env = _wait_for_file(tmux_env_path)
        assert f"http_proxy={HTTP_PROXY_VALUE}" in tmux_env
        assert f"https_proxy={HTTPS_PROXY_VALUE}" in tmux_env
    finally:
        _run_tmux(["kill-session", "-t", session_name], check=False)
