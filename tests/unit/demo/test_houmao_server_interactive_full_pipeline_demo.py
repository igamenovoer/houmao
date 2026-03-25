"""Unit tests for the Houmao-server interactive full-pipeline demo."""

from __future__ import annotations

from pathlib import Path

import pytest

import houmao.demo.houmao_server_interactive_full_pipeline_demo.cli as demo_cli
import houmao.demo.houmao_server_interactive_full_pipeline_demo.commands as demo_commands
from houmao.agents.realm_controller.boundary_models import HoumaoServerSectionV1
from houmao.cao.rest_client import CaoApiError
from houmao.demo.houmao_server_interactive_full_pipeline_demo.models import (
    DEFAULT_COMPAT_CODEX_WARMUP_SECONDS,
    DEFAULT_COMPAT_CREATE_TIMEOUT_SECONDS,
    DEFAULT_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS,
    DEFAULT_COMPAT_SHELL_READY_TIMEOUT_SECONDS,
    DemoEnvironment,
    DemoPaths,
    DemoState,
    ManagedAgentHistorySnapshot,
    ManagedAgentSnapshot,
    TerminalSnapshot,
)
from houmao.server.models import (
    HoumaoHeadlessLaunchResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentRequestAcceptedResponse,
)


def _demo_env(repo_root: Path) -> DemoEnvironment:
    """Return one representative demo environment for tests."""

    base_root = repo_root / "tmp" / "demo" / "houmao-server-interactive-full-pipeline-demo"
    return DemoEnvironment(
        repo_root=repo_root,
        demo_base_root=base_root,
        current_run_root_path=base_root / "current_run_root.txt",
        provision_worktree=False,
        server_start_timeout_seconds=5.0,
        request_settle_timeout_seconds=2.0,
        request_poll_interval_seconds=0.01,
        server_stop_timeout_seconds=2.0,
        compat_shell_ready_timeout_seconds=DEFAULT_COMPAT_SHELL_READY_TIMEOUT_SECONDS,
        compat_provider_ready_timeout_seconds=DEFAULT_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS,
        compat_codex_warmup_seconds=DEFAULT_COMPAT_CODEX_WARMUP_SECONDS,
        compat_create_timeout_seconds=DEFAULT_COMPAT_CREATE_TIMEOUT_SECONDS,
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
        api_base_url="http://127.0.0.1:19989",
        agent_identity="alice",
        agent_ref="alice",
        requested_session_name="alice",
        session_manifest_path=str(
            paths.runtime_root / "sessions" / "houmao_server_rest" / "alice" / "manifest.json"
        ),
        session_root=str(paths.runtime_root / "sessions" / "houmao_server_rest" / "alice"),
        session_name="alice",
        terminal_id="term-1",
        tracked_agent_id="tracked-alice",
        runtime_root=str(paths.runtime_root),
        registry_root=str(paths.registry_root),
        jobs_root=str(paths.jobs_root),
        workspace_dir=str(paths.workspace_root),
        workdir=str(paths.workdir),
        server_home_dir=str(paths.server_home_dir),
        server_runtime_root=str(paths.server_runtime_root),
        server_pid=4242,
        server_stdout_log_path=str(paths.logs_dir / "houmao-server.stdout.log"),
        server_stderr_log_path=str(paths.logs_dir / "houmao-server.stderr.log"),
        agent_def_dir="/repo/scripts/demo/houmao-server-interactive-full-pipeline-demo/agents",
        houmao_server=HoumaoServerSectionV1(
            api_base_url="http://127.0.0.1:19989",
            session_name="alice",
            terminal_id="term-1",
            parsing_mode="shadow_only",
            tmux_window_name="gpu-kernel-coder",
            turn_index=0,
        ),
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
        manifest_path="/tmp/runtime/sessions/houmao_server_rest/alice/manifest.json",
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


def test_start_server_process_passes_demo_owned_compatibility_startup_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Demo-owned server startup should forward explicit compatibility timing overrides."""

    captured: dict[str, object] = {}
    paths = DemoPaths.from_workspace_root(tmp_path / "workspace")
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.workspace_root.mkdir(parents=True, exist_ok=True)

    class _FakeProcess:
        pid = 4242

    def _fake_popen(*args: object, **kwargs: object) -> _FakeProcess:
        captured["args"] = args[0]
        captured["cwd"] = kwargs["cwd"]
        captured["env"] = kwargs["env"]
        captured["start_new_session"] = kwargs["start_new_session"]
        return _FakeProcess()

    monkeypatch.setattr(demo_commands.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(demo_commands, "_wait_for_server_health", lambda **kwargs: None)

    process = demo_commands._start_server_process(
        api_base_url="http://127.0.0.1:19989",
        paths=paths,
        timeout_seconds=5.0,
        env={"HOME": "/demo/server/home"},
        compat_shell_ready_timeout_seconds=20.0,
        compat_provider_ready_timeout_seconds=120.0,
        compat_codex_warmup_seconds=10.0,
    )

    assert process.pid == 4242
    assert captured["args"] == [
        demo_commands.sys.executable,
        "-m",
        "houmao.server",
        "serve",
        "--api-base-url",
        "http://127.0.0.1:19989",
        "--runtime-root",
        str(paths.server_runtime_root),
        "--compat-shell-ready-timeout-seconds",
        "20.0",
        "--compat-provider-ready-timeout-seconds",
        "120.0",
        "--compat-codex-warmup-seconds",
        "10.0",
    ]
    assert captured["cwd"] == str(paths.workspace_root)
    assert captured["env"] == {"HOME": "/demo/server/home"}
    assert captured["start_new_session"] is True


def test_start_demo_persists_manifest_bridge_without_second_registration_post(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Startup should persist the delegated manifest bridge and rely on auto-registration."""

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    paths = DemoPaths.from_workspace_root(tmp_path / "workspace")
    env = _demo_env(repo_root)
    agent_def_dir = _seed_demo_agent_def_symlink(repo_root)
    captured: dict[str, object] = {}

    # Mock _launch_native_session to return a synchronous headless launch response
    def _fake_launch_native_session(
        *,
        client: object,
        provider: str,
        requested_session_name: str | None,
        workdir: Path,
        runtime_root: Path,
    ) -> HoumaoHeadlessLaunchResponse:
        # Use requested session name directly (native launch doesn't add cao- prefix)
        captured["create_timeout_seconds"] = getattr(client, "create_timeout_seconds", None)
        session_name = requested_session_name or "alice"
        return HoumaoHeadlessLaunchResponse(
            success=True,
            detail="Native headless launch successful",
            tracked_agent_id="tracked-alice",
            identity=HoumaoManagedAgentIdentity(
                tracked_agent_id="tracked-alice",
                transport="tui",
                tool="claude",
                session_name=session_name,
                terminal_id="term-1",
                runtime_session_id=None,
                tmux_session_name=session_name,
                tmux_window_name="gpu-kernel-coder",
                manifest_path=str(
                    paths.runtime_root
                    / "sessions"
                    / "houmao_server_rest"
                    / session_name
                    / "manifest.json"
                ),
                session_root=str(
                    paths.runtime_root / "sessions" / "houmao_server_rest" / session_name
                ),
                agent_name=session_name,
                agent_id=f"AGENTSYS-{session_name}",
            ),
            manifest_path=str(
                paths.runtime_root
                / "sessions"
                / "houmao_server_rest"
                / session_name
                / "manifest.json"
            ),
            session_root=str(paths.runtime_root / "sessions" / "houmao_server_rest" / session_name),
        )

    monkeypatch.setattr(demo_commands, "_cleanup_existing_state_for_startup", lambda **kwargs: None)
    monkeypatch.setattr(
        demo_commands, "_start_server_process", lambda **kwargs: type("Proc", (), {"pid": 4242})()
    )
    monkeypatch.setattr(demo_commands, "_launch_native_session", _fake_launch_native_session)
    monkeypatch.setattr(
        demo_commands,
        "_load_manifest_bridge",
        lambda path: HoumaoServerSectionV1(
            api_base_url="http://127.0.0.1:19989",
            session_name="alice",
            terminal_id="term-1",
            parsing_mode="shadow_only",
            tmux_window_name="gpu-kernel-coder",
            turn_index=0,
        ),
    )

    payload = demo_commands.start_demo(
        paths=paths,
        env=env,
        provider="claude_code",
        requested_session_name="alice",
        requested_port=19989,
    )

    loaded = demo_commands.load_demo_state(paths.state_path)
    assert loaded is not None
    # Native launch uses session name directly (no cao- prefix)
    assert payload.state.session_name == "alice"
    assert payload.state.agent_ref == "alice"
    assert payload.state.agent_identity == "AGENTSYS-alice"
    assert payload.state.tracked_agent_id == "tracked-alice"
    assert payload.state.houmao_server.session_name == "alice"
    assert captured["create_timeout_seconds"] == env.compat_create_timeout_seconds
    assert loaded.session_manifest_path.endswith("manifest.json")
    assert loaded.runtime_root == str(paths.runtime_root)
    assert loaded.registry_root == str(paths.registry_root)
    assert loaded.jobs_root == str(paths.jobs_root)
    assert loaded.agent_def_dir == str(agent_def_dir)


def test_cli_help_describes_native_headless_launch_timeout() -> None:
    """The CLI help should describe the current native headless launch budget."""

    help_text = demo_cli._build_parser().format_help().lower()

    assert "native headless launch create timeout" in help_text
    assert "houmao-mgr cao launch" not in help_text


def test_send_turn_targets_session_name_backed_agent_ref(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Prompt submission should target the persisted `agent_ref = session_name` contract."""

    paths = DemoPaths.from_workspace_root(tmp_path / "workspace")
    env = _demo_env(tmp_path / "repo")
    state = _demo_state(paths)
    demo_commands.save_demo_state(paths.state_path, state)

    bundles = iter(
        [
            {"state": "before", "detail": "before", "history": "before", "terminal": "before"},
            {"state": "after", "detail": "after", "history": "after", "terminal": "after"},
        ]
    )

    monkeypatch.setattr(demo_commands, "_fetch_live_bundle", lambda **kwargs: next(bundles))
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

    captured: dict[str, object] = {}

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
            captured["base_url"] = base_url
            captured["timeout_seconds"] = timeout_seconds

        def submit_managed_agent_request(
            self, agent_ref: str, request_model: object
        ) -> HoumaoManagedAgentRequestAcceptedResponse:
            captured["agent_ref"] = agent_ref
            captured["request_model"] = request_model
            return HoumaoManagedAgentRequestAcceptedResponse(
                success=True,
                tracked_agent_id="tracked-alice",
                request_id="mreq-1",
                request_kind="submit_prompt",
                disposition="accepted",
                detail="accepted",
                headless_turn_id=None,
                headless_turn_index=None,
            )

    monkeypatch.setattr(demo_commands, "HoumaoServerClient", _FakeClient)

    artifact = demo_commands.send_turn(paths=paths, env=env, prompt="Hello from the demo")
    updated_state = demo_commands.load_demo_state(paths.state_path)

    assert captured["agent_ref"] == "alice"
    assert artifact.request_kind == "submit_prompt"
    assert artifact.state_change_observed is True
    assert updated_state is not None
    assert updated_state.prompt_turn_count == 1


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


def test_stop_demo_uses_managed_agent_stop_route_and_tolerates_stale_remote_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Managed-agent stale stop outcomes should still deactivate local demo state safely."""

    paths = DemoPaths.from_workspace_root(tmp_path / "workspace")
    env = _demo_env(tmp_path / "repo")
    demo_commands.save_demo_state(paths.state_path, _demo_state(paths))
    killed_sessions: list[str] = []
    captured: dict[str, object] = {}

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 3.0) -> None:
            del base_url, timeout_seconds

        def stop_managed_agent(self, agent_ref: str) -> object:
            captured["agent_ref"] = agent_ref
            raise CaoApiError(
                method="POST",
                url=f"http://127.0.0.1:19989/houmao/agents/{agent_ref}/stop",
                detail="managed agent not found",
                status_code=404,
            )

    monkeypatch.setattr(demo_commands, "HoumaoServerClient", _FakeClient)
    monkeypatch.setattr(
        demo_commands,
        "_best_effort_kill_tmux_session",
        lambda session_name: killed_sessions.append(session_name),
    )
    monkeypatch.setattr(
        demo_commands,
        "_stop_server_process",
        lambda **kwargs: {"status": "stopped", "pid": 4242},
    )

    payload = demo_commands.stop_demo(paths=paths, env=env)
    updated_state = demo_commands.load_demo_state(paths.state_path)

    assert payload.session_delete_status == "stale_missing"
    assert payload.stale_session_tolerated is True
    assert payload.server_stop_status == "stopped"
    assert captured["agent_ref"] == "alice"
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
