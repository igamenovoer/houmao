from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from houmao.agents.realm_controller.backends.cao_rest import (
    CaoRestSession,
    CaoSessionState,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.cao.models import CaoTerminal
from houmao.terminal_record.models import (
    DEFAULT_SAMPLE_INTERVAL_SECONDS,
    TERMINAL_RECORD_SCHEMA_VERSION,
    TerminalRecordLiveState,
    TerminalRecordManifest,
    TerminalRecordPaths,
    TerminalRecordTarget,
    now_utc_iso,
    save_live_state,
    save_manifest,
)


def _sample_launch_plan(tmp_path: Path) -> LaunchPlan:
    env_file = tmp_path / "codex-vars.env"
    env_file.write_text("OPENAI_API_KEY=from-profile\n", encoding="utf-8")
    return LaunchPlan(
        backend="cao_rest",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={"OPENAI_API_KEY": "secret"},
        env_var_names=["OPENAI_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="gpu-kernel-coder",
            prompt="Be precise",
        ),
        metadata={"env_source_file": str(env_file)},
    )


def _resume_state(tmp_path: Path, *, tmux_window_name: str | None) -> CaoSessionState:
    return CaoSessionState(
        api_base_url="http://localhost:9889",
        session_name="AGENTSYS-gpu",
        terminal_id="term-123",
        profile_name="runtime-profile",
        profile_path=str(tmp_path / "runtime-profile.md"),
        parsing_mode="shadow_only",
        tmux_window_name=tmux_window_name,
        turn_index=2,
    )


def test_cao_control_input_uses_persisted_tmux_window_without_live_lookup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError("persisted tmux_window_name should avoid CAO fallback")

    def _fake_run_tmux(
        args: list[str],
        *,
        timeout_seconds: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds
        commands.append(args)
        return subprocess.CompletedProcess(
            args=["tmux", *args],
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_windows",
        lambda *, session_name: [
            SimpleNamespace(
                window_id="@2",
                window_index="1",
                window_name="developer-1",
            )
        ],
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime.run_tmux",
        _fake_run_tmux,
    )
    monkeypatch.setattr(
        "houmao.terminal_record.runtime_bridge.read_tmux_session_environment_value",
        lambda *, session_name, variable_name: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        existing_state=_resume_state(tmp_path, tmux_window_name="developer-1"),
    )

    result = session.send_input_ex("/model<[Enter]><[Down]>")

    assert result.status == "ok"
    assert result.action == "control_input"
    assert commands == [
        ["send-keys", "-t", "@2", "-l", "/model"],
        ["send-keys", "-t", "@2", "Enter"],
        ["send-keys", "-t", "@2", "Down"],
    ]
    assert session.state.tmux_window_name == "developer-1"


def test_cao_control_input_falls_back_to_live_terminal_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []
    list_windows_call_count = {"count": 0}
    terminal_lookup_count = {"count": 0}

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            terminal_lookup_count["count"] += 1
            return CaoTerminal(
                id=terminal_id,
                name="developer-7",
                provider="codex",
                session_name="AGENTSYS-gpu",
                agent_profile="runtime-profile",
                status="idle",
            )

    def _fake_list_tmux_windows(*, session_name: str) -> list[object]:
        assert session_name == "AGENTSYS-gpu"
        list_windows_call_count["count"] += 1
        if list_windows_call_count["count"] == 1:
            return [
                SimpleNamespace(
                    window_id="@1",
                    window_index="0",
                    window_name="bootstrap",
                )
            ]
        return [
            SimpleNamespace(
                window_id="@7",
                window_index="1",
                window_name="developer-7",
            )
        ]

    def _fake_run_tmux(
        args: list[str],
        *,
        timeout_seconds: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds
        commands.append(args)
        return subprocess.CompletedProcess(
            args=["tmux", *args],
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_windows",
        _fake_list_tmux_windows,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime.run_tmux",
        _fake_run_tmux,
    )
    monkeypatch.setattr(
        "houmao.terminal_record.runtime_bridge.read_tmux_session_environment_value",
        lambda *, session_name, variable_name: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        existing_state=_resume_state(tmp_path, tmux_window_name="stale-window"),
    )

    result = session.send_input_ex("<[Escape]>")

    assert result.status == "ok"
    assert commands == [["send-keys", "-t", "@7", "Escape"]]
    assert terminal_lookup_count["count"] == 1
    assert session.state.tmux_window_name == "developer-7"


def test_cao_control_input_returns_explicit_error_when_target_is_unresolved(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            return CaoTerminal(
                id=terminal_id,
                name="developer-9",
                provider="codex",
                session_name="AGENTSYS-gpu",
                agent_profile="runtime-profile",
                status="idle",
            )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_windows",
        lambda *, session_name: [
            SimpleNamespace(
                window_id="@1",
                window_index="0",
                window_name="bootstrap",
            )
        ],
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        existing_state=_resume_state(tmp_path, tmux_window_name=None),
    )

    result = session.send_input_ex("<[Escape]>")

    assert result.status == "error"
    assert result.action == "control_input"
    assert "Unable to resolve live tmux target" in result.detail


def test_cao_control_input_appends_managed_event_for_active_terminal_recorder(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []
    run_root = tmp_path / "terminal-record-run"
    paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    save_manifest(
        paths.manifest_path,
        TerminalRecordManifest(
            schema_version=TERMINAL_RECORD_SCHEMA_VERSION,
            run_id=run_root.name,
            mode="active",
            repo_root=str(tmp_path),
            run_root=str(run_root),
            target=TerminalRecordTarget(
                session_name="AGENTSYS-gpu",
                pane_id="%1",
                window_id="@2",
                window_name="developer-1",
            ),
            tool="codex",
            sample_interval_seconds=DEFAULT_SAMPLE_INTERVAL_SECONDS,
            visual_recording_kind="interactive_client",
            input_capture_level="authoritative_managed",
            run_tainted=False,
            taint_reasons=(),
            recorder_session_name=f"HMREC-{run_root.name}",
            attach_command=f"env -u TMUX tmux attach-session -t HMREC-{run_root.name}",
            started_at_utc=now_utc_iso(),
            stopped_at_utc=None,
            stop_reason=None,
        ),
    )
    save_live_state(
        paths.live_state_path,
        TerminalRecordLiveState(
            schema_version=TERMINAL_RECORD_SCHEMA_VERSION,
            run_id=run_root.name,
            mode="active",
            status="running",
            repo_root=str(tmp_path),
            run_root=str(run_root),
            manifest_path=str(paths.manifest_path),
            controller_pid=4321,
            target_session_name="AGENTSYS-gpu",
            target_pane_id="%1",
            stop_requested_at_utc=None,
            last_error=None,
            updated_at_utc=now_utc_iso(),
        ),
    )

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError("persisted tmux_window_name should avoid CAO fallback")

    def _fake_run_tmux(
        args: list[str],
        *,
        timeout_seconds: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds
        commands.append(args)
        return subprocess.CompletedProcess(
            args=["tmux", *args],
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_windows",
        lambda *, session_name: [
            SimpleNamespace(
                window_id="@2",
                window_index="1",
                window_name="developer-1",
            )
        ],
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime.run_tmux",
        _fake_run_tmux,
    )
    monkeypatch.setattr(
        "houmao.terminal_record.runtime_bridge.read_tmux_session_environment_value",
        lambda *, session_name, variable_name: str(paths.live_state_path),
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        existing_state=_resume_state(tmp_path, tmux_window_name="developer-1"),
    )

    result = session.send_input_ex("/model<[Enter]>")
    payload = [json.loads(line) for line in paths.input_events_path.read_text(encoding="utf-8").splitlines()]

    assert result.status == "ok"
    assert commands == [
        ["send-keys", "-t", "@2", "-l", "/model"],
        ["send-keys", "-t", "@2", "Enter"],
    ]
    assert len(payload) == 1
    assert payload[0]["event_id"] == "i000001"
    assert payload[0]["source"] == "managed_send_keys"
    assert payload[0]["sequence"] == "/model<[Enter]>"
    assert payload[0]["escape_special_keys"] is False
    assert payload[0]["tmux_target"] == "@2"
    assert isinstance(payload[0]["elapsed_seconds"], float)
    assert isinstance(payload[0]["ts_utc"], str)
