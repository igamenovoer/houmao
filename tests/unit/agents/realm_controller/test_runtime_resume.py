from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.realm_controller.backends.headless_base import HeadlessInteractiveSession
from houmao.agents.realm_controller.agent_identity import (
    derive_agent_id_from_name,
    normalize_agent_identity_name,
)
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.launch_plan import (
    LaunchPlanRequest,
    build_launch_plan,
)
from houmao.agents.realm_controller.loaders import (
    load_brain_manifest,
    load_role_package,
)
from houmao.agents.realm_controller.models import BackendKind
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
)
from houmao.agents.realm_controller.runtime import (
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
    operator_prompt_mode: str | None = "as_is",
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
        "schema_version: 3",
        "inputs:",
        f"  tool: {tool}",
        "  skills: []",
        "  setup: default",
        "  auth: default",
        "  adapter_path: /tmp/tool-adapter.yaml",
        "  preset_path: null",
        "runtime:",
        f"  runtime_root: {tmp_path}",
        "  home_id: test-home",
        f"  home_path: {tmp_path / 'home'}",
        f"  launch_helper: {tmp_path / 'home' / 'launch.sh'}",
        f"  launch_executable: {tool}",
        "  launch_home_selector:",
        f"    env_var: {home_env_var}",
        f"    value: {tmp_path / 'home'}",
        "  launch_contract:",
        "    adapter_defaults:",
        "      args: []",
        "      tool_params: {}",
        "    requested_overrides:",
        "      preset: null",
        "      direct: null",
        "    tool_metadata:",
        "      tool_params: {}",
        "    construction_provenance:",
        "      adapter_path: /tmp/tool-adapter.yaml",
        "      preset_path: null",
        "      preset_overrides_present: false",
        "      direct_overrides_present: false",
    ]
    if cao_parsing_mode is not None:
        runtime_lines.append(f"  cao_parsing_mode: {cao_parsing_mode}")
    runtime_lines.extend(
        [
            "credentials:",
            f"  auth_path: {tmp_path / 'auth'}",
            "  projected_files: []",
            "  env_contract:",
            f"    source_file: {env_file}",
            "    allowlisted_env_vars:",
            f"      - {env_var}",
        ]
    )
    if operator_prompt_mode is not None:
        runtime_lines.extend(
            [
                "launch_policy:",
                f"  operator_prompt_mode: {operator_prompt_mode}",
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
    operator_prompt_mode: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    brain_manifest_path = _seed_manifest(
        agent_def_dir,
        tmp_path,
        tool=tool,
        cao_parsing_mode=cao_parsing_mode,
        operator_prompt_mode=operator_prompt_mode,
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
    resolved_tmux_session_name = str(
        backend_state.get("tmux_session_name") or backend_state.get("session_name") or ""
    ).strip()
    resolved_agent_name = normalize_agent_identity_name(resolved_tmux_session_name).canonical_name
    session_payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=brain_manifest_path,
            agent_name=resolved_agent_name,
            agent_id=derive_agent_id_from_name(resolved_agent_name),
            tmux_session_name=resolved_tmux_session_name,
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
            agent_name="AGENTSYS-r",
            agent_id=derive_agent_id_from_name("AGENTSYS-r"),
            tmux_session_name="AGENTSYS-r",
            backend_state={
                "session_id": "sess-1",
                "turn_index": 0,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": "AGENTSYS-r",
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


def test_resume_local_interactive_uses_persisted_tmux_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _, session_payload = _build_session_payload(
        agent_def_dir,
        tmp_path,
        tool="claude",
        backend="local_interactive",
        backend_state={
            "turn_index": 2,
            "role_bootstrap_applied": True,
            "working_directory": str(tmp_path),
            "tmux_session_name": "AGENTSYS-r",
            "tmux_window_name": "manual",
        },
    )
    session_path = tmp_path / "session-local-interactive.json"
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    captured: dict[str, Any] = {}

    class _FakeLocalInteractiveSession:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)
            self.state = type("State", (), {"tmux_session_name": "AGENTSYS-r"})()

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.LocalInteractiveSession",
        _FakeLocalInteractiveSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.RuntimeSessionController.ensure_gateway_capability",
        lambda self: None,
    )

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=session_path,
    )

    assert captured["state"].turn_index == 2
    assert captured["state"].tmux_session_name == "AGENTSYS-r"
    assert captured["state"].tmux_window_name == "manual"
    assert controller.launch_plan.backend == "local_interactive"


def test_resume_local_interactive_restores_join_launch_window_name_when_manifest_fields_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _, session_payload = _build_session_payload(
        agent_def_dir,
        tmp_path,
        tool="claude",
        backend="local_interactive",
        backend_state={
            "turn_index": 2,
            "role_bootstrap_applied": True,
            "working_directory": str(tmp_path),
            "tmux_session_name": "AGENTSYS-r",
        },
    )
    session_payload["launch_plan"]["metadata"]["session_origin"] = "joined_tmux"
    session_payload["launch_plan"]["metadata"]["tmux_window_name"] = "manual"
    session_payload["agent_launch_authority"] = {
        "backend": "local_interactive",
        "tool": "claude",
        "tmux_session_name": "AGENTSYS-r",
        "primary_window_index": "0",
        "working_directory": str(tmp_path),
        "posture_kind": "unavailable",
        "session_origin": "joined_tmux",
    }
    if session_payload.get("tmux") is not None:
        session_payload["tmux"]["primary_window_name"] = None
    if session_payload.get("interactive") is not None:
        session_payload["interactive"]["tmux_window_name"] = None
    session_payload["backend_state"].pop("tmux_window_name", None)
    session_path = tmp_path / "session-local-interactive-joined.json"
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    captured: dict[str, Any] = {}

    class _FakeLocalInteractiveSession(HeadlessInteractiveSession):
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)
            self.backend = "local_interactive"
            self._state = kwargs["state"]

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.LocalInteractiveSession",
        _FakeLocalInteractiveSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.RuntimeSessionController.ensure_gateway_capability",
        lambda self: None,
    )

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=session_path,
    )

    assert captured["state"].tmux_window_name == "manual"
    assert controller.launch_plan.metadata["tmux_window_name"] == "manual"


def test_resume_unattended_local_interactive_uses_resume_control_intent_without_mutating_owned_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)

    def _fake_version(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> object:
        del check, capture_output, text
        return type(
            "_Completed",
            (),
            {"stdout": "2.1.83 (Claude Code)", "stderr": "", "args": command},
        )()

    monkeypatch.setattr(
        "houmao.agents.launch_policy.engine.subprocess.run",
        _fake_version,
    )

    _, session_payload = _build_session_payload(
        agent_def_dir,
        tmp_path,
        tool="claude",
        backend="local_interactive",
        backend_state={
            "turn_index": 2,
            "role_bootstrap_applied": True,
            "working_directory": str(tmp_path),
            "tmux_session_name": "AGENTSYS-r",
        },
        operator_prompt_mode="unattended",
    )
    home = tmp_path / "home"
    settings_path = home / "settings.json"
    state_path = home / ".claude.json"
    settings_path.write_text("", encoding="utf-8")
    state_path.write_text("", encoding="utf-8")
    session_path = tmp_path / "session-local-interactive-unattended.json"
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    captured: dict[str, Any] = {}
    intents: list[str] = []
    real_build_launch_plan = build_launch_plan

    class _FakeLocalInteractiveSession:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)
            self.state = type("State", (), {"tmux_session_name": "AGENTSYS-r"})()

    def _capture_build_launch_plan(request: LaunchPlanRequest):
        intents.append(request.intent)
        return real_build_launch_plan(request)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.build_launch_plan",
        _capture_build_launch_plan,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.LocalInteractiveSession",
        _FakeLocalInteractiveSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.RuntimeSessionController.ensure_gateway_capability",
        lambda self: None,
    )

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=session_path,
    )

    assert intents == ["resume_control"]
    assert captured["state"].turn_index == 2
    assert controller.launch_plan.backend == "local_interactive"
    assert controller.launch_plan.args[-1] == "--dangerously-skip-permissions"
    assert settings_path.read_text(encoding="utf-8") == ""
    assert state_path.read_text(encoding="utf-8") == ""


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
        "houmao.agents.realm_controller.runtime.CaoRestSession",
        _FakeCaoRestSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.RuntimeSessionController.ensure_gateway_capability",
        lambda self: None,
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
        "houmao.agents.realm_controller.runtime.CaoRestSession",
        _FakeCaoRestSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.RuntimeSessionController.ensure_gateway_capability",
        lambda self: None,
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

    with pytest.raises(SessionManifestError, match="parsing mode mismatch"):
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
