from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from gig_agents.agents.realm_controller.errors import SessionManifestError
from gig_agents.agents.realm_controller.launch_plan import (
    LaunchPlanRequest,
    build_launch_plan,
)
from gig_agents.agents.realm_controller.loaders import (
    load_brain_manifest,
    load_role_package,
)
from gig_agents.agents.realm_controller.models import BackendKind
from gig_agents.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
)
from gig_agents.agents.realm_controller.runtime import (
    resume_runtime_session,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_manifest(
    agent_def_dir: Path,
    tmp_path: Path,
    *,
    tool: str = "claude",
    cao_parsing_mode: str | None = None,
) -> Path:
    if tool == "claude":
        env_var = "ANTHROPIC_API_KEY"
        home_env_var = "CLAUDE_CONFIG_DIR"
    else:
        env_var = "OPENAI_API_KEY"
        home_env_var = "CODEX_HOME"

    env_file = tmp_path / "vars.env"
    env_file.write_text(f"{env_var}=secret\n", encoding="utf-8")

    manifest_path = tmp_path / "brain.yaml"
    runtime_lines = [
        "inputs:",
        f"  tool: {tool}",
        "runtime:",
        f"  launch_executable: {tool}",
        "  launch_args: []",
        "  launch_home_selector:",
        f"    env_var: {home_env_var}",
        f"    value: {tmp_path / 'home'}",
    ]
    if cao_parsing_mode is not None:
        runtime_lines.append(f"  cao_parsing_mode: {cao_parsing_mode}")
    runtime_lines.extend(
        [
            "credentials:",
            "  env_contract:",
            f"    source_file: {env_file}",
            "    allowlisted_env_vars:",
            f"      - {env_var}",
        ]
    )
    manifest_path.write_text("\n".join(runtime_lines) + "\n", encoding="utf-8")

    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt")
    return manifest_path


def _build_session_payload(
    agent_def_dir: Path,
    tmp_path: Path,
    *,
    tool: str,
    backend: BackendKind,
    backend_state: dict[str, Any],
    cao_parsing_mode: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    brain_manifest_path = _seed_manifest(
        agent_def_dir,
        tmp_path,
        tool=tool,
        cao_parsing_mode=cao_parsing_mode,
    )
    manifest = load_brain_manifest(brain_manifest_path)
    role = load_role_package(agent_def_dir, "r")
    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend=backend,
            working_directory=tmp_path,
        )
    )
    session_payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=brain_manifest_path,
            backend_state=backend_state,
        )
    )
    return brain_manifest_path, session_payload


def test_resume_headless_requires_session_id(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    brain_manifest_path = _seed_manifest(agent_def_dir, tmp_path)

    manifest = load_brain_manifest(brain_manifest_path)
    role = load_role_package(agent_def_dir, "r")
    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="claude_headless",
            working_directory=tmp_path,
        )
    )

    session_payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=brain_manifest_path,
            backend_state={
                "session_id": "sess-1",
                "turn_index": 0,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
            },
        )
    )
    session_payload["headless"]["session_id"] = ""
    session_payload["headless"]["turn_index"] = 1
    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    with pytest.raises(SessionManifestError, match="session_id"):
        resume_runtime_session(
            agent_def_dir=agent_def_dir,
            session_manifest_path=session_path,
        )


def test_resume_cao_uses_manifest_api_base_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _, session_payload = _build_session_payload(
        agent_def_dir,
        tmp_path,
        tool="codex",
        backend="cao_rest",
        backend_state={
            "api_base_url": "http://manifest-only.example:9444",
            "session_name": "cao-s1",
            "terminal_id": "term-123",
            "profile_name": "runtime-profile",
            "profile_path": str(tmp_path / "runtime-profile.md"),
            "parsing_mode": "shadow_only",
            "turn_index": 2,
        },
    )
    session_path = tmp_path / "session-cao.json"
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    captured: dict[str, Any] = {}

    class _FakeCaoRestSession:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)
            self.state = type(
                "State",
                (),
                {"parsing_mode": "cao_only", "session_name": "cao-s1"},
            )()

    monkeypatch.setattr(
        "gig_agents.agents.realm_controller.runtime.CaoRestSession",
        _FakeCaoRestSession,
    )

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=session_path,
    )

    assert captured["api_base_url"] == "http://manifest-only.example:9444"
    assert captured["existing_state"].api_base_url == "http://manifest-only.example:9444"
    assert captured["agent_def_dir"] == agent_def_dir.resolve()
    assert captured["session_manifest_path"] == session_path.resolve()
    assert controller.launch_plan.backend == "cao_rest"
    assert "api_base_url" not in inspect.signature(resume_runtime_session).parameters


def test_resume_cao_rejects_api_base_url_mismatch(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _, session_payload = _build_session_payload(
        agent_def_dir,
        tmp_path,
        tool="codex",
        backend="cao_rest",
        backend_state={
            "api_base_url": "http://manifest-only.example:9444",
            "session_name": "cao-s1",
            "terminal_id": "term-123",
            "profile_name": "runtime-profile",
            "profile_path": str(tmp_path / "runtime-profile.md"),
            "parsing_mode": "cao_only",
            "turn_index": 2,
        },
    )
    session_payload["backend_state"]["api_base_url"] = "http://different.example:9889"
    session_path = tmp_path / "session-cao-mismatch.json"
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    with pytest.raises(SessionManifestError, match="api_base_url"):
        resume_runtime_session(
            agent_def_dir=agent_def_dir,
            session_manifest_path=session_path,
        )


def test_resume_cao_rejects_blank_terminal_id(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _, session_payload = _build_session_payload(
        agent_def_dir,
        tmp_path,
        tool="codex",
        backend="cao_rest",
        backend_state={
            "api_base_url": "http://manifest-only.example:9444",
            "session_name": "cao-s1",
            "terminal_id": "term-123",
            "profile_name": "runtime-profile",
            "profile_path": str(tmp_path / "runtime-profile.md"),
            "parsing_mode": "cao_only",
            "turn_index": 2,
        },
    )
    session_payload["cao"]["terminal_id"] = "   "
    session_path = tmp_path / "session-cao-terminal-blank.json"
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    with pytest.raises(SessionManifestError, match="terminal_id"):
        resume_runtime_session(
            agent_def_dir=agent_def_dir,
            session_manifest_path=session_path,
        )


def test_resume_cao_accepts_older_manifest_without_tmux_window_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _, session_payload = _build_session_payload(
        agent_def_dir,
        tmp_path,
        tool="codex",
        backend="cao_rest",
        backend_state={
            "api_base_url": "http://manifest-only.example:9444",
            "session_name": "cao-s1",
            "terminal_id": "term-123",
            "profile_name": "runtime-profile",
            "profile_path": str(tmp_path / "runtime-profile.md"),
            "parsing_mode": "shadow_only",
            "turn_index": 2,
        },
    )
    session_payload["cao"].pop("tmux_window_name", None)
    session_payload["backend_state"].pop("tmux_window_name", None)
    session_path = tmp_path / "session-cao-no-window.json"
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    captured: dict[str, Any] = {}

    class _FakeCaoRestSession:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)
            self.state = type(
                "State",
                (),
                {"parsing_mode": "shadow_only", "session_name": "cao-s1"},
            )()

    monkeypatch.setattr(
        "gig_agents.agents.realm_controller.runtime.CaoRestSession",
        _FakeCaoRestSession,
    )

    resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=session_path,
    )

    assert captured["existing_state"].tmux_window_name is None


def test_cao_manifest_payload_persists_parsing_mode(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _, session_payload = _build_session_payload(
        agent_def_dir,
        tmp_path,
        tool="codex",
        backend="cao_rest",
        backend_state={
            "api_base_url": "http://manifest-only.example:9444",
            "session_name": "cao-s1",
            "terminal_id": "term-123",
            "profile_name": "runtime-profile",
            "profile_path": str(tmp_path / "runtime-profile.md"),
            "parsing_mode": "shadow_only",
            "turn_index": 2,
        },
    )

    assert session_payload["cao"]["parsing_mode"] == "shadow_only"
    assert session_payload["backend_state"]["parsing_mode"] == "shadow_only"


def test_resume_cao_rejects_backend_state_parsing_mode_mismatch(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _, session_payload = _build_session_payload(
        agent_def_dir,
        tmp_path,
        tool="codex",
        backend="cao_rest",
        backend_state={
            "api_base_url": "http://manifest-only.example:9444",
            "session_name": "cao-s1",
            "terminal_id": "term-123",
            "profile_name": "runtime-profile",
            "profile_path": str(tmp_path / "runtime-profile.md"),
            "parsing_mode": "cao_only",
            "turn_index": 2,
        },
    )
    session_payload["backend_state"]["parsing_mode"] = "shadow_only"
    session_path = tmp_path / "session-cao-mode-mismatch.json"
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    with pytest.raises(SessionManifestError, match="parsing_mode mismatch"):
        resume_runtime_session(
            agent_def_dir=agent_def_dir,
            session_manifest_path=session_path,
        )


def test_resume_cao_rejects_config_resolved_parsing_mode_mismatch(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _, session_payload = _build_session_payload(
        agent_def_dir,
        tmp_path,
        tool="codex",
        backend="cao_rest",
        cao_parsing_mode="shadow_only",
        backend_state={
            "api_base_url": "http://manifest-only.example:9444",
            "session_name": "cao-s1",
            "terminal_id": "term-123",
            "profile_name": "runtime-profile",
            "profile_path": str(tmp_path / "runtime-profile.md"),
            "parsing_mode": "cao_only",
            "turn_index": 2,
        },
    )
    session_path = tmp_path / "session-cao-config-mode-mismatch.json"
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    with pytest.raises(SessionManifestError, match="parsing mode mismatch on resume"):
        resume_runtime_session(
            agent_def_dir=agent_def_dir,
            session_manifest_path=session_path,
        )
