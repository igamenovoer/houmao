"""Unit tests for the Houmao-server dual shadow-watch monitor."""

from __future__ import annotations

import json
from pathlib import Path

import houmao.demo.houmao_server_dual_shadow_watch.monitor as monitor_module
from rich.console import Console

from houmao.demo.houmao_server_dual_shadow_watch.models import (
    AgentSessionState,
    HoumaoServerDualShadowWatchState,
    MonitorSessionState,
    ServerProcessState,
    save_demo_state,
)
from houmao.server.models import (
    HoumaoLifecycleAuthorityMetadata,
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
        lifecycle_authority=HoumaoLifecycleAuthorityMetadata(
            completion_authority="turn_anchored",
            turn_anchor_state="active",
            completion_monitoring_armed=True,
            detail="Server-owned turn anchor is active for completion monitoring.",
            anchor_armed_at_utc="2026-03-19T09:59:58+00:00",
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


def _render_demo_state(tmp_path: Path) -> HoumaoServerDualShadowWatchState:
    """Return a minimal persisted demo state for render-only tests."""

    return HoumaoServerDualShadowWatchState(
        schema_version=1,
        active=True,
        created_at_utc="2026-03-19T12:00:00+00:00",
        stopped_at_utc=None,
        repo_root="/repo",
        run_root=str(tmp_path),
        agent_def_dir="/repo/tests/fixtures/agents",
        project_fixture="/repo/tests/fixtures/dummy-projects/projection-demo-python",
        profile_path="/repo/scripts/demo/houmao-server-dual-shadow-watch/profiles/projection-demo.md",
        poll_interval_seconds=0.5,
        stability_threshold_seconds=1.0,
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
        agents={},
        monitor=MonitorSessionState(
            tmux_session_name="houmao-shadow-watch-monitor-demo",
            command=("python", "watch_dashboard.py"),
            samples_path=str(tmp_path / "monitor" / "samples.ndjson"),
            transitions_path=str(tmp_path / "monitor" / "transitions.ndjson"),
            dashboard_log_path=str(tmp_path / "logs" / "monitor-dashboard.log"),
        ),
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
        stability_threshold_seconds=1.0,
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


def test_render_agent_panel_uses_server_owned_status_fields() -> None:
    """The agent panel should show the server-consumer display contract."""

    display_state = monitor_module._display_state_from_terminal(
        slot="codex",
        state=_terminal_state("dcba4321", tool="codex", slot="codex"),
    )

    console = Console(record=True, width=120)
    console.print(monitor_module._render_agent_panel(display_state))
    output = console.export_text()

    assert "current: ready" in output
    assert "ready/complete: ready / candidate_complete" in output
    assert "authority: turn_anchored / active" in output
    assert "health: tmux_up / tui_up / parsed" in output
    assert "surface: supported / idle / freeform / normal_prompt" in output
    assert "projection: changed" in output
    assert "visible stability: changing for 0.7s" in output
    assert "timing: candidate_for=0.7s" in output
    assert "last transition:" in output
    assert "transport/process/parse:" not in output
    assert "tmux:" not in output


def test_render_header_and_transition_panels_separate_monitor_and_server_posture(
    tmp_path: Path,
) -> None:
    """Header and transition panels should separate monitor cadence from server posture."""

    demo_state = _render_demo_state(tmp_path)
    display_state = monitor_module._display_state_from_terminal(
        slot="codex",
        state=_terminal_state("dcba4321", tool="codex", slot="codex"),
    )
    transition = monitor_module.ServerTransitionEvent(
        ts_utc="2026-03-19T10:00:00+00:00",
        slot="codex",
        tool="codex",
        terminal_id="dcba4321",
        summary="codex became candidate_complete",
        changed_fields=("completion_state",),
    )

    header_console = Console(record=True, width=140)
    header_console.print(
        monitor_module._render_header_panel(demo_state=demo_state, display_states=[display_state])
    )
    header_output = header_console.export_text()

    assert "Houmao Server State Watch" in header_output
    assert "monitor: poll=0.5s" in header_output
    assert "server posture: completion_debounce=1.0s  unknown->stalled=30.0s" in header_output
    assert "current: codex: ready (ready/candidate_complete)" in header_output

    transition_console = Console(record=True, width=140)
    transition_console.print(
        monitor_module._render_transition_panel(demo_state=demo_state, transitions=[transition])
    )
    transition_output = transition_console.export_text()

    assert "Recent Server Transitions" in transition_output
    assert "monitor: poll=0.5s" in transition_output
    assert "server posture: completion_debounce=1.0s  unknown->stalled=30.0s" in transition_output
    assert "10:00:00 codex: codex became candidate_complete" in transition_output


def test_compact_dialog_excerpt_keeps_only_meaningful_tail_lines() -> None:
    """The tail excerpt should drop empty lines and box-drawing noise."""

    excerpt = monitor_module._compact_dialog_excerpt(
        """
        │ header │

        › Say READY in one short sentence and stop.

        • READY.
        """
    )

    assert excerpt == "› Say READY in one short sentence and stop. | • READY."
