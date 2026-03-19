"""Unit tests for the Houmao-server dual shadow-watch monitor."""

from __future__ import annotations

import json
from pathlib import Path

import houmao.demo.houmao_server_dual_shadow_watch.monitor as monitor_module
from houmao.demo.houmao_server_dual_shadow_watch.models import (
    AgentSessionState,
    HoumaoServerDualShadowWatchState,
    MonitorSessionState,
    ServerProcessState,
    save_demo_state,
)
from houmao.server.models import (
    HoumaoLifecycleTimingMetadata,
    HoumaoOperatorState,
    HoumaoParsedSurface,
    HoumaoProbeSnapshot,
    HoumaoRecentTransition,
    HoumaoStabilityMetadata,
    HoumaoTerminalStateResponse,
    HoumaoTrackedSessionIdentity,
)


def _terminal_state(terminal_id: str, *, tool: str, slot: str) -> HoumaoTerminalStateResponse:
    return HoumaoTerminalStateResponse(
        terminal_id=terminal_id,
        tracked_session=HoumaoTrackedSessionIdentity(
            tracked_session_id=f"cao-{slot}",
            session_name=f"cao-{slot}",
            tool=tool,
            tmux_session_name=f"cao-{slot}",
            terminal_aliases=[terminal_id],
        ),
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=HoumaoProbeSnapshot(
            observed_at_utc="2026-03-19T10:00:00+00:00",
            pane_id="%9",
            pane_pid=4321,
            captured_text_hash="abc123",
            captured_text_length=12,
            captured_text_excerpt="hello world",
            matched_process_names=[tool],
        ),
        probe_error=None,
        parse_error=None,
        parsed_surface=HoumaoParsedSurface(
            parser_family=f"{tool}_shadow",
            parser_preset_id=tool,
            parser_preset_version="1.0.0",
            availability="supported",
            business_state="idle",
            input_mode="freeform",
            ui_context="normal_prompt",
            normalized_projection_text="hello world",
            dialog_text="hello world",
            dialog_head="hello world",
            dialog_tail="hello world",
            anomaly_codes=["baseline_invalidated"],
            baseline_invalidated=True,
            operator_blocked_excerpt=None,
        ),
        operator_state=HoumaoOperatorState(
            status="ready",
            readiness_state="ready",
            completion_state="candidate_complete",
            detail="Supported TUI is ready for input.",
            projection_changed=True,
            updated_at_utc="2026-03-19T10:00:00+00:00",
        ),
        lifecycle_timing=HoumaoLifecycleTimingMetadata(
            readiness_unknown_elapsed_seconds=None,
            completion_unknown_elapsed_seconds=None,
            completion_candidate_elapsed_seconds=0.7,
            unknown_to_stalled_timeout_seconds=30.0,
            completion_stability_seconds=1.0,
        ),
        stability=HoumaoStabilityMetadata(
            signature="deadbeef",
            stable=False,
            stable_for_seconds=0.7,
            stable_since_utc="2026-03-19T09:59:59+00:00",
        ),
        recent_transitions=[
            HoumaoRecentTransition(
                recorded_at_utc="2026-03-19T10:00:00+00:00",
                summary=f"{slot} became candidate_complete",
                changed_fields=["completion_state"],
                transport_state="tmux_up",
                process_state="tui_up",
                parse_status="parsed",
                operator_status="ready",
            ),
        ],
    )


def test_monitor_consumes_server_state_and_writes_samples_and_transitions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Monitor output should mirror the server payloads it consumes."""

    state_path = tmp_path / "control" / "demo_state.json"
    monitor_dir = tmp_path / "monitor"
    demo_state = HoumaoServerDualShadowWatchState(
        schema_version=1,
        active=True,
        created_at_utc="2026-03-19T12:00:00+00:00",
        stopped_at_utc=None,
        repo_root="/repo",
        run_root=str(tmp_path),
        agent_def_dir="/repo/tests/fixtures/agents",
        project_fixture="/repo/tests/fixtures/dummy-projects/projection-demo-python",
        profile_path="/repo/scripts/demo/houmao-server-dual-shadow-watch/profiles/projection-demo.md",
        poll_interval_seconds=0.01,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
        server_start_timeout_seconds=20.0,
        launch_timeout_seconds=45.0,
        stop_timeout_seconds=20.0,
        server=ServerProcessState(
            api_base_url="http://127.0.0.1:19989",
            port=19989,
            runtime_root=str(tmp_path / "server" / "runtime"),
            home_dir=str(tmp_path / "server" / "home"),
            pid=4242,
            started_by_demo=True,
            stdout_log_path=str(tmp_path / "logs" / "houmao-server.stdout.log"),
            stderr_log_path=str(tmp_path / "logs" / "houmao-server.stderr.log"),
        ),
        agents={
            "claude": AgentSessionState(
                slot="claude",
                tool="claude",
                provider="claude_code",
                profile_name="projection-demo",
                session_name="cao-claude",
                terminal_id="abcd1234",
                tmux_session_name="cao-claude",
                workdir=str(tmp_path / "projects" / "claude"),
                agent_name="cao-claude",
                agent_id="AGENTSYS-cao-claude",
                blueprint_path="/repo/tests/fixtures/agents/blueprints/projection-demo-claude.yaml",
                brain_recipe_path="/repo/tests/fixtures/agents/brains/brain-recipes/claude/projection-demo-default.yaml",
                role_name="projection-demo",
                config_profile="default",
                credential_profile="personal-a-default",
                brain_home_path=str(tmp_path / "runtime" / "homes" / "projection-demo-claude"),
                brain_manifest_path=str(
                    tmp_path / "runtime" / "manifests" / "projection-demo-claude.yaml"
                ),
                launch_helper_path=str(
                    tmp_path / "runtime" / "homes" / "projection-demo-claude" / "launch.sh"
                ),
                session_manifest_path=str(
                    tmp_path
                    / "runtime"
                    / "sessions"
                    / "houmao_server_rest"
                    / "cao-claude"
                    / "manifest.json"
                ),
                session_root=str(
                    tmp_path / "runtime" / "sessions" / "houmao_server_rest" / "cao-claude"
                ),
                launch_stdout_path=str(tmp_path / "logs" / "launch-claude.stdout.log"),
                launch_stderr_path=str(tmp_path / "logs" / "launch-claude.stderr.log"),
            ),
            "codex": AgentSessionState(
                slot="codex",
                tool="codex",
                provider="codex",
                profile_name="projection-demo",
                session_name="cao-codex",
                terminal_id="dcba4321",
                tmux_session_name="cao-codex",
                workdir=str(tmp_path / "projects" / "codex"),
                agent_name="cao-codex",
                agent_id="AGENTSYS-cao-codex",
                blueprint_path="/repo/tests/fixtures/agents/blueprints/projection-demo-codex.yaml",
                brain_recipe_path="/repo/tests/fixtures/agents/brains/brain-recipes/codex/projection-demo-default.yaml",
                role_name="projection-demo",
                config_profile="default",
                credential_profile="personal-a-default",
                brain_home_path=str(tmp_path / "runtime" / "homes" / "projection-demo-codex"),
                brain_manifest_path=str(
                    tmp_path / "runtime" / "manifests" / "projection-demo-codex.yaml"
                ),
                launch_helper_path=str(
                    tmp_path / "runtime" / "homes" / "projection-demo-codex" / "launch.sh"
                ),
                session_manifest_path=str(
                    tmp_path
                    / "runtime"
                    / "sessions"
                    / "houmao_server_rest"
                    / "cao-codex"
                    / "manifest.json"
                ),
                session_root=str(
                    tmp_path / "runtime" / "sessions" / "houmao_server_rest" / "cao-codex"
                ),
                launch_stdout_path=str(tmp_path / "logs" / "launch-codex.stdout.log"),
                launch_stderr_path=str(tmp_path / "logs" / "launch-codex.stderr.log"),
            ),
        },
        monitor=MonitorSessionState(
            tmux_session_name="houmao-shadow-watch-monitor-demo",
            command=("python", "watch_dashboard.py"),
            samples_path=str(monitor_dir / "samples.ndjson"),
            transitions_path=str(monitor_dir / "transitions.ndjson"),
            dashboard_log_path=str(tmp_path / "logs" / "monitor-dashboard.log"),
        ),
    )
    save_demo_state(state_path, demo_state)

    class _ClientDouble:
        def __init__(self, base_url: str, timeout_seconds: float = 2.0) -> None:
            del base_url, timeout_seconds

        def terminal_state(self, terminal_id: str) -> HoumaoTerminalStateResponse:
            if terminal_id == "abcd1234":
                return _terminal_state(terminal_id, tool="claude", slot="claude")
            return _terminal_state(terminal_id, tool="codex", slot="codex")

    monkeypatch.setattr(monitor_module, "HoumaoServerClient", _ClientDouble)

    monitor = monitor_module.ShadowWatchMonitor(state_file=state_path)
    result = monitor.run(max_iterations=1)

    assert result == 0
    samples = [
        json.loads(line)
        for line in (monitor_dir / "samples.ndjson").read_text(encoding="utf-8").splitlines()
    ]
    transitions = [
        json.loads(line)
        for line in (monitor_dir / "transitions.ndjson").read_text(encoding="utf-8").splitlines()
    ]

    assert len(samples) == 2
    assert (
        samples[0]["terminal_state"]["operator_state"]["completion_state"] == "candidate_complete"
    )
    assert len(transitions) == 2
    assert transitions[0]["summary"].endswith("became candidate_complete")
