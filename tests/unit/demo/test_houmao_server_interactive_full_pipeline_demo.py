"""Unit tests for the Houmao-server interactive full-pipeline demo."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import houmao.demo.houmao_server_interactive_full_pipeline_demo.cli as demo_cli
import houmao.demo.houmao_server_interactive_full_pipeline_demo.commands as demo_commands
from houmao.agents.realm_controller.boundary_models import HoumaoServerSectionV1
from houmao.cao.rest_client import CaoApiError
from houmao.demo.houmao_server_interactive_full_pipeline_demo.models import (
    DemoEnvironment,
    DemoPaths,
    DemoState,
    ManagedAgentHistorySnapshot,
    ManagedAgentSnapshot,
    TerminalSnapshot,
)
from houmao.owned_paths import (
    AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR,
    AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR,
    AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR,
)
from houmao.server.models import (
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
    )


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
        agent_ref="cao-alice",
        requested_session_name="alice",
        session_manifest_path=str(
            paths.runtime_root / "sessions" / "houmao_server_rest" / "cao-alice" / "manifest.json"
        ),
        session_root=str(paths.runtime_root / "sessions" / "houmao_server_rest" / "cao-alice"),
        session_name="cao-alice",
        terminal_id="term-1",
        tracked_agent_id="tracked-cao-alice",
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
        install_profile_source="/repo/scripts/demo/houmao-server-interactive-full-pipeline-demo/profiles/gpu-kernel-coder.md",
        install_stdout_log_path=str(paths.logs_dir / "install.stdout.log"),
        install_stderr_log_path=str(paths.logs_dir / "install.stderr.log"),
        houmao_server=HoumaoServerSectionV1(
            api_base_url="http://127.0.0.1:19989",
            session_name="cao-alice",
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
        tracked_agent_id="tracked-cao-alice",
        transport="tui",
        tool="claude",
        session_name="cao-alice",
        terminal_id="term-1",
        manifest_path="/tmp/runtime/sessions/houmao_server_rest/cao-alice/manifest.json",
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


def test_install_pair_profile_targets_public_pair_port(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Pair-profile installs should target the public demo-owned pair port."""

    captured: dict[str, object] = {}
    profile_path = tmp_path / "gpu-kernel-coder.md"
    profile_path.write_text(
        "---\nname: gpu-kernel-coder\ndescription: demo\n---\nbody\n", encoding="utf-8"
    )
    stdout_path = tmp_path / "install.stdout.log"
    stderr_path = tmp_path / "install.stderr.log"

    def _fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        captured["args"] = args[0]
        captured["cwd"] = kwargs["cwd"]
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"ok\n", stderr=b"")

    monkeypatch.setattr(demo_commands.subprocess, "run", _fake_run)

    demo_commands._install_pair_profile(
        api_base_url="http://127.0.0.1:19989",
        profile_source=profile_path,
        provider="codex",
        env={"HOME": "/demo/server/home"},
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )

    assert captured["args"] == [
        demo_commands.sys.executable,
        "-m",
        "houmao.srv_ctrl",
        "install",
        str(profile_path),
        "--provider",
        "codex",
        "--port",
        "19989",
    ]
    assert captured["cwd"] == str(profile_path.parent)
    assert captured["env"] == {"HOME": "/demo/server/home"}
    assert stdout_path.read_text(encoding="utf-8") == "ok\n"


def test_launch_pair_session_uses_public_detached_compat_command_and_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Detached startup should invoke the public compatibility launch surface."""

    captured: dict[str, object] = {}
    workdir = tmp_path / "wktree"
    launch_env = {
        "HOME": "/demo/server/home",
        AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR: "/demo/runtime",
        AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR: "/demo/registry",
        AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR: "/demo/jobs",
    }

    def _fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        captured["args"] = args[0]
        captured["cwd"] = kwargs["cwd"]
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(demo_commands.subprocess, "run", _fake_run)

    demo_commands._launch_pair_session(
        api_base_url="http://127.0.0.1:19989",
        provider="codex",
        requested_session_name="alice",
        workdir=workdir,
        env=launch_env,
    )

    assert captured["args"] == [
        demo_commands.sys.executable,
        "-m",
        "houmao.srv_ctrl",
        "cao",
        "launch",
        "--headless",
        "--yolo",
        "--agents",
        "gpu-kernel-coder",
        "--provider",
        "codex",
        "--port",
        "19989",
        "--session-name",
        "alice",
    ]
    assert captured["cwd"] == str(workdir.resolve())
    assert captured["env"] == launch_env


def test_start_demo_persists_manifest_bridge_without_second_registration_post(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Startup should persist the delegated manifest bridge and rely on auto-registration."""

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    paths = DemoPaths.from_workspace_root(tmp_path / "workspace")
    env = _demo_env(repo_root)
    profile_path = (
        repo_root
        / "scripts"
        / "demo"
        / "houmao-server-interactive-full-pipeline-demo"
        / "profiles"
        / "gpu-kernel-coder.md"
    )
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        "---\nname: gpu-kernel-coder\ndescription: demo\n---\nbody\n", encoding="utf-8"
    )

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
            del base_url, timeout_seconds

        def list_sessions(self) -> list[object]:
            return [type("Session", (), {"id": "cao-alice"})()]

    captured_launch_kwargs: dict[str, object] = {}

    monkeypatch.setattr(demo_commands, "_cleanup_existing_state_for_startup", lambda **kwargs: None)
    monkeypatch.setattr(
        demo_commands, "_start_server_process", lambda **kwargs: type("Proc", (), {"pid": 4242})()
    )
    monkeypatch.setattr(demo_commands, "_install_pair_profile", lambda **kwargs: None)
    monkeypatch.setattr(
        demo_commands,
        "_launch_pair_session",
        lambda **kwargs: captured_launch_kwargs.update(kwargs),
    )
    monkeypatch.setattr(
        demo_commands, "_wait_for_launched_session_name", lambda **kwargs: "cao-alice"
    )
    monkeypatch.setattr(demo_commands, "_wait_for_session_detail", lambda **kwargs: object())
    monkeypatch.setattr(
        demo_commands, "_terminal_id_from_session_detail", lambda **kwargs: "term-1"
    )
    monkeypatch.setattr(
        demo_commands,
        "_wait_for_session_manifest",
        lambda **kwargs: (
            paths.runtime_root / "sessions" / "houmao_server_rest" / "cao-alice" / "manifest.json"
        ),
    )
    monkeypatch.setattr(
        demo_commands,
        "_load_manifest_bridge",
        lambda path: HoumaoServerSectionV1(
            api_base_url="http://127.0.0.1:19989",
            session_name="cao-alice",
            terminal_id="term-1",
            parsing_mode="shadow_only",
            tmux_window_name="gpu-kernel-coder",
            turn_index=0,
        ),
    )
    monkeypatch.setattr(
        demo_commands,
        "_wait_for_managed_agent_identity",
        lambda **kwargs: HoumaoManagedAgentIdentity(
            tracked_agent_id="tracked-cao-alice",
            transport="tui",
            tool="claude",
            session_name="cao-alice",
            terminal_id="term-1",
            runtime_session_id=None,
            tmux_session_name="cao-alice",
            tmux_window_name="gpu-kernel-coder",
            manifest_path="/tmp/runtime/sessions/houmao_server_rest/cao-alice/manifest.json",
            session_root="/tmp/runtime/sessions/houmao_server_rest/cao-alice",
            agent_name="cao-alice",
            agent_id="AGENTSYS-cao-alice",
        ),
    )
    monkeypatch.setattr(demo_commands, "HoumaoServerClient", _FakeClient)

    payload = demo_commands.start_demo(
        paths=paths,
        env=env,
        provider="claude_code",
        requested_session_name="alice",
        requested_port=19989,
    )

    loaded = demo_commands.load_demo_state(paths.state_path)
    assert loaded is not None
    assert payload.state.session_name == "cao-alice"
    assert payload.state.agent_ref == "cao-alice"
    assert payload.state.agent_identity == "AGENTSYS-alice"
    assert payload.state.tracked_agent_id == "tracked-cao-alice"
    assert payload.state.houmao_server.session_name == "cao-alice"
    assert loaded.session_manifest_path.endswith("manifest.json")
    assert captured_launch_kwargs["workdir"] == paths.workdir
    launch_env = captured_launch_kwargs["env"]
    assert isinstance(launch_env, dict)
    assert launch_env["HOME"] == str(paths.server_home_dir)
    assert launch_env[AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR] == str(paths.runtime_root)
    assert launch_env[AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR] == str(paths.registry_root)
    assert launch_env[AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR] == str(paths.jobs_root)


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
                tracked_agent_id="tracked-cao-alice",
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

    assert captured["agent_ref"] == "cao-alice"
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
    assert captured["agent_ref"] == "cao-alice"
    assert killed_sessions == ["cao-alice"]
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
