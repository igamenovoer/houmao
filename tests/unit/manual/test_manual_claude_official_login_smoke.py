from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
from types import ModuleType

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
MANUAL_SCRIPT = REPO_ROOT / "tests" / "manual" / "manual_claude_official_login_smoke.py"


def _load_manual_smoke_module() -> ModuleType:
    """Load the manual smoke script as an importable module."""

    spec = importlib.util.spec_from_file_location(
        "manual_claude_official_login_smoke", MANUAL_SCRIPT
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_prompt_and_auth(tmp_path: Path) -> tuple[Path, Path]:
    """Create minimal prompt and auth inputs for command construction tests."""

    source_agent_def_dir = tmp_path / "plain-agent-def"
    role_dir = source_agent_def_dir / "roles" / "server-api-smoke"
    role_dir.mkdir(parents=True)
    (role_dir / "system-prompt.md").write_text("Smoke prompt\n", encoding="utf-8")

    auth_bundle_root = tmp_path / "auth-bundles" / "claude" / "official-login"
    files_dir = auth_bundle_root / "files"
    files_dir.mkdir(parents=True)
    (files_dir / ".credentials.json").write_text('{"token":"local"}\n', encoding="utf-8")
    (files_dir / ".claude.json").write_text("{}\n", encoding="utf-8")
    return source_agent_def_dir, auth_bundle_root


def test_official_login_smoke_launch_uses_project_backed_birth(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_manual_smoke_module()
    source_agent_def_dir, auth_bundle_root = _seed_prompt_and_auth(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    commands: list[list[str]] = []

    def _fake_run_command(*, args: list[str], cwd: Path, env: dict[str, str]):
        commands.append(args)
        assert cwd.is_relative_to(tmp_path / "tmp")
        assert env["HOUMAO_CLI_PRINT_STYLE"] == "json"
        assert env["HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE"] == "cwd_only"
        assert "HOUMAO_AGENT_DEF_DIR" not in env
        assert "HOUMAO_NATIVE_AGENT_ROOT" not in env
        stdout = ""
        if args[:5] == ["pixi", "run", "houmao-mgr", "project", "agents"]:
            stdout = (
                '{"status":"Managed agent launch complete",'
                '"agent_id":"agent-123","manifest_path":"'
                f"{manifest_path}"
                '"}\n'
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(module, "_run_command", _fake_run_command)

    workdir, payload = module._run_smoke_launch(
        repo_root=tmp_path,
        source_agent_def_dir=source_agent_def_dir,
        auth_bundle_root=auth_bundle_root,
        auth_name="official-login",
    )

    assert workdir.is_dir()
    assert payload["agent_id"] == "agent-123"
    assert commands[0] == ["pixi", "run", "houmao-mgr", "project", "init"]
    assert commands[1][:7] == [
        "pixi",
        "run",
        "houmao-mgr",
        "project",
        "credentials",
        "claude",
        "add",
    ]
    assert "--config-dir" in commands[1]
    assert commands[2][:5] == ["pixi", "run", "houmao-mgr", "project", "specialist"]
    assert "--system-prompt-file" in commands[2]
    assert commands[3] == [
        "pixi",
        "run",
        "houmao-mgr",
        "project",
        "agents",
        "launch",
        "--specialist",
        "server-api-smoke",
        "--name",
        "server-api-smoke",
        "--auth",
        "official-login",
        "--headless",
    ]
    assert ["pixi", "run", "houmao-mgr", "agents", "launch"] not in commands


def test_official_login_smoke_cleanup_uses_scoped_single_agent_commands(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_manual_smoke_module()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    commands: list[list[str]] = []

    def _fake_run_command(*, args: list[str], cwd: Path, env: dict[str, str]):
        commands.append(args)
        assert cwd == tmp_path
        assert env["HOUMAO_CLI_PRINT_STYLE"] == "json"
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module, "_run_command", _fake_run_command)

    module._stop_and_cleanup_session(
        workdir=tmp_path,
        agent_id="agent-123",
        manifest_path=manifest_path,
    )

    assert commands == [
        [
            "pixi",
            "run",
            "houmao-mgr",
            "agents",
            "single",
            "--agent-id",
            "agent-123",
            "stop",
        ],
        [
            "pixi",
            "run",
            "houmao-mgr",
            "agents",
            "single",
            "--agent-id",
            "agent-123",
            "cleanup",
            "session",
            "--manifest-path",
            str(manifest_path),
        ],
    ]
