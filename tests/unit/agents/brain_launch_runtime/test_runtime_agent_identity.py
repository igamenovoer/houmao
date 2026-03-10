"""Unit tests for tmux-backed runtime agent-identity resolution."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from gig_agents.agents.brain_launch_runtime.errors import SessionManifestError
from gig_agents.agents.brain_launch_runtime.launch_plan import (
    LaunchPlanRequest,
    build_launch_plan,
)
from gig_agents.agents.brain_launch_runtime.loaders import (
    load_brain_manifest,
    load_role_package,
)
from gig_agents.agents.brain_launch_runtime.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
)
from gig_agents.agents.brain_launch_runtime.runtime import (
    resolve_agent_identity,
)


def _write(path: Path, text: str) -> None:
    """Write text content to a file path, creating parents as needed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_brain_manifest(agent_def_dir: Path, tmp_path: Path) -> Path:
    """Create a minimal brain manifest and role for runtime tests."""

    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=secret\n", encoding="utf-8")

    manifest_path = tmp_path / "brain.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "inputs:",
                "  tool: codex",
                "runtime:",
                "  launch_executable: codex",
                "  launch_args: []",
                "  launch_home_selector:",
                "    env_var: CODEX_HOME",
                f"    value: {tmp_path / 'home'}",
                "credentials:",
                "  env_contract:",
                f"    source_file: {env_file}",
                "    allowlisted_env_vars:",
                "      - OPENAI_API_KEY",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt")
    return manifest_path


def _build_cao_manifest(
    agent_def_dir: Path,
    tmp_path: Path,
    *,
    session_name: str,
    path: Path,
    parsing_mode: str = "cao_only",
) -> Path:
    """Build and persist a schema-valid CAO session manifest."""

    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)
    manifest = load_brain_manifest(brain_manifest_path)
    role = load_role_package(agent_def_dir, "r")
    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="cao_rest",
            working_directory=tmp_path,
        )
    )

    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=brain_manifest_path,
            backend_state={
                "api_base_url": "http://localhost:9889",
                "session_name": session_name,
                "terminal_id": "term-1",
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": parsing_mode,
                "turn_index": 1,
            },
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _build_headless_manifest(
    agent_def_dir: Path,
    tmp_path: Path,
    *,
    backend: str,
    session_name: str,
    path: Path,
) -> Path:
    """Build and persist a schema-valid tmux-backed headless manifest."""

    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)
    manifest = load_brain_manifest(brain_manifest_path)
    role = load_role_package(agent_def_dir, "r")
    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend=backend,  # type: ignore[arg-type]
            working_directory=tmp_path,
        )
    )

    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=brain_manifest_path,
            backend_state={
                "session_id": "sess-or-thread-1",
                "turn_index": 1,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": session_name,
            },
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _completed(
    args: list[str], *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    """Build a `CompletedProcess` helper for tmux command mocks."""

    return subprocess.CompletedProcess(
        args=args,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_resolve_agent_identity_path_like_missing_fails_fast(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _fail_if_called(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise AssertionError("tmux must not be called for path-like identity")

    monkeypatch.setattr("subprocess.run", _fail_if_called)
    with pytest.raises(SessionManifestError, match="Session manifest not found"):
        resolve_agent_identity(
            agent_identity=str(tmp_path / "missing.json"),
            base=tmp_path,
        )


@pytest.mark.parametrize("parsing_mode", ["cao_only", "shadow_only"])
def test_resolve_agent_identity_name_reads_tmux_manifest_pointer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    parsing_mode: str,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / "cao.json",
        parsing_mode=parsing_mode,
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "tmux"
        if cmd[1:3] == ["has-session", "-t"]:
            assert cmd[3] == "AGENTSYS-gpu"
            return _completed(cmd)
        if cmd[1:3] == ["show-environment", "-t"]:
            assert cmd[3] == "AGENTSYS-gpu"
            return _completed(
                cmd,
                stdout=f"AGENTSYS_MANIFEST_PATH={manifest_path}\n",
            )
        raise AssertionError(f"Unexpected tmux command: {cmd}")

    monkeypatch.setattr("subprocess.run", _fake_run)

    resolved = resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)
    assert resolved.canonical_agent_identity == "AGENTSYS-gpu"
    assert resolved.session_manifest_path == manifest_path.resolve()


def test_resolve_agent_identity_name_fails_when_tmux_session_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "tmux"
        return _completed(
            cmd,
            returncode=1,
            stderr="can't find session: AGENTSYS-gpu",
        )

    monkeypatch.setattr("subprocess.run", _fake_run)
    with pytest.raises(SessionManifestError, match="Agent not found"):
        resolve_agent_identity(agent_identity="gpu", base=tmp_path)


def test_resolve_agent_identity_name_fails_when_manifest_pointer_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    call_index = {"count": 0}

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        call_index["count"] += 1
        if call_index["count"] == 1:
            return _completed(cmd)
        return _completed(cmd, returncode=1, stderr="unknown variable: AGENTSYS_MANIFEST_PATH")

    monkeypatch.setattr("subprocess.run", _fake_run)
    with pytest.raises(SessionManifestError, match="Manifest pointer missing"):
        resolve_agent_identity(agent_identity="gpu", base=tmp_path)


def test_resolve_agent_identity_name_fails_when_manifest_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _build_cao_manifest(
        agent_def_dir,
        tmp_path,
        session_name="AGENTSYS-other",
        path=tmp_path / "sessions" / "cao.json",
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if cmd[1] == "has-session":
            return _completed(cmd)
        return _completed(cmd, stdout=f"AGENTSYS_MANIFEST_PATH={manifest_path}\n")

    monkeypatch.setattr("subprocess.run", _fake_run)

    with pytest.raises(SessionManifestError, match="does not match addressed tmux session"):
        resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)


@pytest.mark.parametrize("backend", ["codex_headless", "claude_headless", "gemini_headless"])
def test_resolve_agent_identity_accepts_tmux_backed_headless_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    backend: str,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _build_headless_manifest(
        agent_def_dir,
        tmp_path,
        backend=backend,
        session_name="AGENTSYS-gpu",
        path=tmp_path / "sessions" / f"{backend}.json",
    )

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "tmux"
        if cmd[1:3] == ["has-session", "-t"]:
            return _completed(cmd)
        if cmd[1:3] == ["show-environment", "-t"]:
            return _completed(cmd, stdout=f"AGENTSYS_MANIFEST_PATH={manifest_path}\n")
        raise AssertionError(f"Unexpected tmux command: {cmd}")

    monkeypatch.setattr("subprocess.run", _fake_run)
    resolved = resolve_agent_identity(agent_identity="gpu", base=agent_def_dir)
    assert resolved.session_manifest_path == manifest_path.resolve()
