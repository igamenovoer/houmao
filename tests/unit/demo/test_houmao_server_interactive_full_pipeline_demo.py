"""Unit tests for the interactive full-pipeline demo."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import houmao.demo.houmao_server_interactive_full_pipeline_demo.cli as demo_cli
import houmao.demo.houmao_server_interactive_full_pipeline_demo.commands as demo_commands
from houmao.demo.houmao_server_interactive_full_pipeline_demo.models import (
    DEFAULT_COMPAT_CODEX_WARMUP_SECONDS,
    DEFAULT_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS,
    DEFAULT_COMPAT_SHELL_READY_TIMEOUT_SECONDS,
    DemoEnvironment,
    DemoPaths,
    DemoRequestRecord,
    DemoState,
    ManagedAgentHistorySnapshot,
    ManagedAgentSnapshot,
    TerminalSnapshot,
)


def _demo_env(repo_root: Path) -> DemoEnvironment:
    """Return one representative demo environment for tests."""

    base_root = repo_root / "tmp" / "demo" / "houmao-server-interactive-full-pipeline-demo"
    return DemoEnvironment(
        repo_root=repo_root,
        demo_base_root=base_root,
        current_run_root_path=base_root / "current_run_root.txt",
        provision_worktree=False,
        request_settle_timeout_seconds=2.0,
        request_poll_interval_seconds=0.01,
        compat_shell_ready_timeout_seconds=DEFAULT_COMPAT_SHELL_READY_TIMEOUT_SECONDS,
        compat_provider_ready_timeout_seconds=DEFAULT_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS,
        compat_codex_warmup_seconds=DEFAULT_COMPAT_CODEX_WARMUP_SECONDS,
    )


def _fixture_agent_def_dir(repo_root: Path) -> Path:
    """Return the canonical fixture-backed agent-definition root for tests."""

    return repo_root / "tests" / "fixtures" / "agents"


def _demo_agent_def_symlink(repo_root: Path) -> Path:
    """Return the demo-local agent-definition entry for tests."""

    return (
        repo_root / "scripts" / "demo" / "houmao-server-interactive-full-pipeline-demo" / "agents"
    )


def _seed_demo_agent_def_symlink(repo_root: Path) -> Path:
    """Create one demo-local symlink that points at the fixture tree."""

    fixture_agent_def_dir = _fixture_agent_def_dir(repo_root)
    fixture_agent_def_dir.mkdir(parents=True, exist_ok=True)
    demo_agent_def_dir = _demo_agent_def_symlink(repo_root)
    demo_agent_def_dir.parent.mkdir(parents=True, exist_ok=True)
    demo_agent_def_dir.symlink_to(Path("..") / ".." / ".." / "tests" / "fixtures" / "agents")
    return demo_agent_def_dir


def _demo_state(paths: DemoPaths, *, active: bool = True) -> DemoState:
    """Return one representative persisted demo state."""

    return DemoState(
        active=active,
        provider="claude_code",
        tool="claude",
        agent_profile="gpu-kernel-coder",
        variant_id="claude-gpu-kernel-coder",
        agent_name="alice",
        agent_id="agent-id-alice",
        requested_session_name="alice",
        tmux_session_name="alice",
        tracked_agent_id="tracked-alice",
        session_manifest_path=str(
            paths.runtime_root / "sessions" / "local_interactive" / "session-1" / "manifest.json"
        ),
        session_root=str(paths.runtime_root / "sessions" / "local_interactive" / "session-1"),
        runtime_root=str(paths.runtime_root),
        registry_root=str(paths.registry_root),
        jobs_root=str(paths.jobs_root),
        workspace_dir=str(paths.workspace_root),
        workdir=str(paths.workdir),
        agent_def_dir="/repo/scripts/demo/houmao-server-interactive-full-pipeline-demo/agents",
        updated_at="2026-03-24T12:00:00+00:00",
        prompt_turn_count=0,
        interrupt_count=0,
    )


def _managed_snapshot(*, phase: str, result: str, turn_index: int | None) -> ManagedAgentSnapshot:
    """Build one managed-agent snapshot for request-artifact tests."""

    return ManagedAgentSnapshot(
        tracked_agent_id="tracked-alice",
        transport="tui",
        tool="claude",
        session_name="alice",
        terminal_id="term-1",
        manifest_path="/tmp/runtime/sessions/local_interactive/session-1/manifest.json",
        availability="available",
        turn_phase=phase,
        active_turn_id=None if phase == "ready" else "turn-1",
        last_turn_result=result,
        last_turn_id=None if turn_index is None else f"turn-{turn_index}",
        last_turn_index=turn_index,
        last_turn_updated_at_utc=None if turn_index is None else "2026-03-24T12:00:05+00:00",
        detail_transport="tui",
        terminal_state_route="/houmao/terminals/term-1/state",
        terminal_history_route="/houmao/terminals/term-1/history",
        parsed_surface_present=True,
        ready_posture="yes",
        stable=True,
        stable_for_seconds=1.5,
        can_accept_prompt_now=None,
        interruptible=None,
        diagnostic_count=0,
        gateway_queue_depth=None,
    )


def _history_snapshot(*, count: int) -> ManagedAgentHistorySnapshot:
    """Build one managed-agent history snapshot."""

    return ManagedAgentHistorySnapshot(
        entry_count=count,
        latest_recorded_at_utc="2026-03-24T12:00:05+00:00" if count else None,
        latest_summary="Turn completed." if count else None,
        latest_turn_phase="ready" if count else None,
        latest_last_turn_result="success" if count else None,
    )


def _terminal_snapshot(*, result: str) -> TerminalSnapshot:
    """Build one terminal snapshot."""

    return TerminalSnapshot(
        terminal_id="term-1",
        parser_family="shadow",
        availability="available",
        business_state="ready",
        input_mode="command",
        ui_context="conversation",
        parsed_surface_present=True,
        ready_posture="yes",
        turn_phase="ready",
        last_turn_result=result,
        stable=True,
        stable_for_seconds=1.5,
        recent_transition_count=2,
        probe_captured_text_length=120,
    )


def test_demo_pack_agents_entry_exists_as_demo_local_agent_root() -> None:
    """The tracked demo `agents` entry should exist as a usable demo-local root."""

    repo_root = Path(__file__).resolve().parents[3]
    demo_agent_def_dir = _demo_agent_def_symlink(repo_root)

    assert demo_agent_def_dir.is_symlink()
    assert demo_agent_def_dir.is_dir()
    assert demo_agent_def_dir.resolve() == _fixture_agent_def_dir(repo_root).resolve()


def test_demo_agent_def_dir_path_preserves_demo_local_symlink_path(tmp_path: Path) -> None:
    """Startup should keep the demo-local `agents` path instead of collapsing to the target."""

    repo_root = tmp_path / "repo"
    expected = _seed_demo_agent_def_symlink(repo_root)

    assert demo_commands._demo_agent_def_dir_path(repo_root) == expected
    assert (
        demo_commands._demo_agent_def_dir_path(repo_root).resolve()
        == _fixture_agent_def_dir(repo_root).resolve()
    )


def test_start_demo_persists_local_managed_agent_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Startup should persist the local managed-agent identity tuple and runtime roots."""

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    paths = DemoPaths.from_workspace_root(tmp_path / "workspace")
    env = _demo_env(repo_root)
    agent_def_dir = _seed_demo_agent_def_symlink(repo_root)
    captured: dict[str, object] = {}

    monkeypatch.setattr(demo_commands, "_cleanup_existing_state_for_startup", lambda **kwargs: None)
    monkeypatch.setattr(
        demo_commands,
        "resolve_native_launch_target",
        lambda **kwargs: SimpleNamespace(
            agent_def_dir=agent_def_dir,
            tool="claude",
            role_name="coder",
            recipe=SimpleNamespace(
                tool="claude",
                skills=["demo-skill"],
                config_profile="default",
                credential_profile="default",
                launch_overrides=None,
                operator_prompt_mode=None,
                mailbox=None,
            ),
            recipe_path=agent_def_dir / "brains" / "brain-recipes" / "claude" / "demo.yaml",
        ),
    )

    def _fake_build_brain_home(request: object) -> object:
        captured["build_request"] = request
        return SimpleNamespace(manifest_path=paths.runtime_root / "brains" / "demo-home" / "manifest.json")

    def _fake_start_runtime_session(**kwargs: object) -> object:
        captured["start_kwargs"] = kwargs
        return SimpleNamespace(
            agent_identity="alice",
            agent_id="agent-id-alice",
            tmux_session_name="alice",
            manifest_path=paths.runtime_root
            / "sessions"
            / "local_interactive"
            / "session-1"
            / "manifest.json",
            launch_plan=SimpleNamespace(tool="claude"),
        )

    monkeypatch.setattr(demo_commands, "build_brain_home", _fake_build_brain_home)
    monkeypatch.setattr(demo_commands, "start_runtime_session", _fake_start_runtime_session)
    monkeypatch.setattr(demo_commands, "_wait_for_controller_launch_readiness", lambda **kwargs: None)

    payload = demo_commands.start_demo(
        paths=paths,
        env=env,
        provider="claude_code",
        requested_session_name="alice",
    )

    loaded = demo_commands.load_demo_state(paths.state_path)
    assert loaded is not None
    build_request = captured["build_request"]
    start_kwargs = captured["start_kwargs"]

    assert payload.state.agent_name == "alice"
    assert payload.state.agent_id == "agent-id-alice"
    assert payload.state.tmux_session_name == "alice"
    assert payload.state.tracked_agent_id is None
    assert payload.state.session_manifest_path.endswith("manifest.json")
    assert payload.state.agent_def_dir == str(agent_def_dir)
    assert build_request.agent_name == "alice"
    assert start_kwargs["agent_name"] == "alice"
    assert start_kwargs["tmux_session_name"] == "alice"
    assert loaded.registry_root == str(paths.registry_root)
    assert loaded.jobs_root == str(paths.jobs_root)


def test_start_demo_derives_default_agent_name_from_variant_when_session_name_omitted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Startup should derive a stable default managed-agent name from the demo variant."""

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    paths = DemoPaths.from_workspace_root(tmp_path / "workspace")
    env = _demo_env(repo_root)
    agent_def_dir = _seed_demo_agent_def_symlink(repo_root)
    captured: dict[str, object] = {}

    monkeypatch.setattr(demo_commands, "_cleanup_existing_state_for_startup", lambda **kwargs: None)
    monkeypatch.setattr(
        demo_commands,
        "resolve_native_launch_target",
        lambda **kwargs: SimpleNamespace(
            agent_def_dir=agent_def_dir,
            tool="claude",
            role_name="coder",
            recipe=SimpleNamespace(
                tool="claude",
                skills=["demo-skill"],
                config_profile="default",
                credential_profile="default",
                launch_overrides=None,
                operator_prompt_mode=None,
                mailbox=None,
            ),
            recipe_path=agent_def_dir / "brains" / "brain-recipes" / "claude" / "demo.yaml",
        ),
    )

    def _fake_build_brain_home(request: object) -> object:
        captured["build_request"] = request
        return SimpleNamespace(manifest_path=paths.runtime_root / "brains" / "demo-home" / "manifest.json")

    def _fake_start_runtime_session(**kwargs: object) -> object:
        captured["start_kwargs"] = kwargs
        return SimpleNamespace(
            agent_identity="claude-gpu-kernel-coder",
            agent_id="agent-id-default",
            tmux_session_name="tmux-claude-gpu-kernel-coder",
            manifest_path=paths.runtime_root
            / "sessions"
            / "local_interactive"
            / "session-2"
            / "manifest.json",
            launch_plan=SimpleNamespace(tool="claude"),
        )

    monkeypatch.setattr(demo_commands, "build_brain_home", _fake_build_brain_home)
    monkeypatch.setattr(demo_commands, "start_runtime_session", _fake_start_runtime_session)
    monkeypatch.setattr(demo_commands, "_wait_for_controller_launch_readiness", lambda **kwargs: None)

    payload = demo_commands.start_demo(
        paths=paths,
        env=env,
        provider="claude_code",
        requested_session_name=None,
    )

    build_request = captured["build_request"]
    start_kwargs = captured["start_kwargs"]
    assert build_request.agent_name == "claude-gpu-kernel-coder"
    assert start_kwargs["agent_name"] == "claude-gpu-kernel-coder"
    assert start_kwargs["tmux_session_name"] is None
    assert payload.state.agent_name == "claude-gpu-kernel-coder"


def test_cli_help_describes_local_launch_surface() -> None:
    """CLI help should describe the local managed-agent startup contract."""

    help_text = demo_cli._build_parser().format_help().lower()

    assert "local interactive full-pipeline demo commands" in help_text
    assert "loopback port" not in help_text
    assert "native headless launch create timeout" not in help_text


def test_send_turn_records_local_artifact_and_updates_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Prompt submission should persist a local artifact and update tracked counts."""

    paths = DemoPaths.from_workspace_root(tmp_path / "workspace")
    env = _demo_env(tmp_path / "repo")
    state = _demo_state(paths)
    demo_commands.save_demo_state(paths.state_path, state)

    target = SimpleNamespace(identity=SimpleNamespace(tracked_agent_id="tracked-alice"))
    bundles = iter(
        [
            {"state": "before", "detail": "before", "history": "before", "terminal": "before"},
            {"state": "after", "detail": "after", "history": "after", "terminal": "after"},
        ]
    )

    monkeypatch.setattr(demo_commands, "_resolve_local_target", lambda state: target)
    monkeypatch.setattr(demo_commands, "_fetch_live_bundle_from_target", lambda **kwargs: next(bundles))
    monkeypatch.setattr(
        demo_commands,
        "_managed_agent_snapshot",
        lambda **kwargs: (
            _managed_snapshot(phase="ready", result="none", turn_index=None)
            if kwargs["state_response"] == "before"
            else _managed_snapshot(phase="ready", result="success", turn_index=1)
        ),
    )
    monkeypatch.setattr(
        demo_commands,
        "_history_snapshot",
        lambda payload: _history_snapshot(count=0 if payload == "before" else 1),
    )
    monkeypatch.setattr(
        demo_commands,
        "_terminal_snapshot",
        lambda payload: _terminal_snapshot(result="none" if payload == "before" else "success"),
    )
    monkeypatch.setattr(
        demo_commands,
        "_submit_request_record",
        lambda **kwargs: DemoRequestRecord(
            request_id="prompt-1",
            request_kind="submit_prompt",
            tracked_agent_id="tracked-alice",
            detail="accepted",
            success=True,
            disposition="accepted",
        ),
    )

    artifact = demo_commands.send_turn(paths=paths, env=env, prompt="Hello from the demo")
    updated_state = demo_commands.load_demo_state(paths.state_path)

    assert artifact.request.request_id == "prompt-1"
    assert artifact.agent_name == "alice"
    assert artifact.agent_id == "agent-id-alice"
    assert artifact.state_change_observed is True
    assert updated_state is not None
    assert updated_state.prompt_turn_count == 1
    assert updated_state.tracked_agent_id == "tracked-alice"


def test_inspect_omits_dialog_tail_unless_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Inspect should keep parser-derived dialog tail behind the explicit opt-in flag."""

    paths = DemoPaths.from_workspace_root(tmp_path / "workspace")
    demo_commands.save_demo_state(paths.state_path, _demo_state(paths))
    bundle = {"state": "live", "detail": "live", "history": "live", "terminal": "live"}

    monkeypatch.setattr(demo_commands, "_fetch_live_bundle", lambda **kwargs: bundle)
    monkeypatch.setattr(
        demo_commands,
        "_managed_agent_snapshot",
        lambda **kwargs: _managed_snapshot(phase="ready", result="success", turn_index=1),
    )
    monkeypatch.setattr(
        demo_commands,
        "_history_snapshot",
        lambda payload: _history_snapshot(count=1),
    )
    monkeypatch.setattr(
        demo_commands,
        "_terminal_snapshot",
        lambda payload: _terminal_snapshot(result="success"),
    )
    monkeypatch.setattr(
        demo_commands,
        "_dialog_tail_from_terminal_state",
        lambda **kwargs: "tail excerpt",
    )

    default_payload = demo_commands.inspect_demo(paths=paths, dialog_tail_chars=None)
    explicit_payload = demo_commands.inspect_demo(paths=paths, dialog_tail_chars=80)

    assert default_payload.dialog_tail is None
    assert explicit_payload.dialog_tail == "tail excerpt"
    assert explicit_payload.dialog_tail_chars_requested == 80
    assert explicit_payload.tracked_agent_id == "tracked-alice"


def test_stop_demo_tolerates_stale_local_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Stale local stop outcomes should still deactivate demo state safely."""

    paths = DemoPaths.from_workspace_root(tmp_path / "workspace")
    env = _demo_env(tmp_path / "repo")
    demo_commands.save_demo_state(paths.state_path, _demo_state(paths))
    killed_sessions: list[str] = []

    monkeypatch.setattr(
        demo_commands,
        "_resume_local_controller",
        lambda state: (_ for _ in ()).throw(FileNotFoundError("manifest missing")),
    )
    monkeypatch.setattr(
        demo_commands,
        "_best_effort_kill_tmux_session",
        lambda session_name: killed_sessions.append(session_name),
    )
    monkeypatch.setattr(demo_commands, "_best_effort_cleanup_session_root", lambda session_root: None)

    payload = demo_commands.stop_demo(paths=paths, env=env)
    updated_state = demo_commands.load_demo_state(paths.state_path)

    assert payload.stop_status == "stale_missing"
    assert payload.stale_session_tolerated is True
    assert killed_sessions == ["alice"]
    assert updated_state is not None
    assert updated_state.active is False


def test_cli_resolves_workspace_root_from_current_run_pointer(tmp_path: Path) -> None:
    """Follow-up CLI commands should reuse the current-run workspace pointer."""

    repo_root = tmp_path / "repo"
    workspace_root = (
        repo_root / "tmp" / "demo" / "houmao-server-interactive-full-pipeline-demo" / "run-1"
    )
    workspace_root.mkdir(parents=True, exist_ok=True)
    current_run_root_path = (
        repo_root
        / "tmp"
        / "demo"
        / "houmao-server-interactive-full-pipeline-demo"
        / "current_run_root.txt"
    )
    current_run_root_path.parent.mkdir(parents=True, exist_ok=True)
    current_run_root_path.write_text(f"{workspace_root}\n", encoding="utf-8")

    invocation = demo_cli._resolve_demo_invocation(
        demo_cli._build_parser().parse_args(["--repo-root", str(repo_root), "inspect"])
    )

    assert invocation.paths.workspace_root == workspace_root.resolve()
