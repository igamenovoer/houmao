"""Codex hook-posture merge tests for the live session tracker.

Covers the Codex adapter selection, hook-derived ``interrupted``, deny-abort
blocked settling, compaction continuity and idle-heuristic suppression,
terminal-gap publication, the Claude TUI-derived-interrupt regression, and the
provider-neutral gateway prompt-admission policy.
"""

from __future__ import annotations

from pathlib import Path

from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime
from houmao.hook_observation.reader import HookObservationChannel
from houmao.hook_observation.store import HookObservationStore
from houmao.server.models import (
    HoumaoParsedSurface,
    HoumaoTrackedSessionIdentity,
    HoumaoTerminalStateResponse,
)
from houmao.server.tui.tracking import LiveSessionTracker
from houmao.shared_tui_tracking.models import TrackedStateSnapshot


SESSION_ID = "codex-session"
TURN_1 = "turn-1"
TURN_2 = "turn-2"


class _StaticTrackerSession:
    """Tracker session stub returning one fixed tracked-state snapshot."""

    def __init__(self, *, state: TrackedStateSnapshot) -> None:
        """Store the fixed snapshot."""

        self.m_state = state

    def current_state(self) -> TrackedStateSnapshot:
        """Return the fixed snapshot."""

        return self.m_state

    def on_snapshot(self, _raw_text: str) -> None:
        """Accept one raw snapshot without reducing it."""

        return

    def on_input_submitted(self) -> None:
        """Accept one input submission without changing state."""

        return

    def close(self) -> None:
        """Close the stub."""

        return


class _StaticTrackingRuntime:
    """TUI tracking runtime stub exposing one tracked state for admission tests."""

    def __init__(self, *, state: HoumaoTerminalStateResponse) -> None:
        """Store the state under test."""

        self.m_state = state

    def current_state(self) -> HoumaoTerminalStateResponse:
        """Return the state under test."""

        return self.m_state


def _identity(*, tool: str = "codex") -> HoumaoTrackedSessionIdentity:
    """Return one tracked-session identity for the selected adapter."""

    return HoumaoTrackedSessionIdentity(
        tracked_session_id=f"{tool}-session",
        session_name=f"{tool}-session",
        tool=tool,
        observed_tool_version="0.163.0" if tool == "codex" else "2.1.296",
        tmux_session_name=f"HOUMAO-{tool}",
        terminal_aliases=["abcd1234"],
    )


def _tracker_state(
    *,
    surface_ready_posture: str = "yes",
    turn_phase: str = "ready",
    last_turn_result: str = "none",
    last_turn_source: str = "none",
    active_reasons: tuple[str, ...] = (),
) -> TrackedStateSnapshot:
    """Return one static shared-tracker snapshot."""

    return TrackedStateSnapshot(
        surface_accepting_input="yes" if surface_ready_posture == "yes" else "no",
        surface_editing_input="no",
        surface_ready_posture=surface_ready_posture,
        surface_pending_input="no",
        turn_phase=turn_phase,
        last_turn_result=last_turn_result,
        last_turn_source=last_turn_source,
        detector_name="codex_tui",
        detector_version="0.162.x",
        active_reasons=active_reasons,
        notes=(),
        stability_signature="sig",
        stable=True,
        stable_for_seconds=0.0,
        stable_since_seconds=0.0,
        observed_at_seconds=0.0,
    )


def _surface(
    *,
    ui_context: str = "normal_prompt",
    business_state: str = "idle",
) -> HoumaoParsedSurface:
    """Return one submit-ready parsed surface."""

    text = f"{ui_context}-{business_state}"
    return HoumaoParsedSurface(
        parser_family="codex_tui_shadow",
        parser_preset_id="codex",
        parser_preset_version="1.0.0",
        availability="supported",
        business_state=business_state,
        input_mode="freeform" if business_state == "idle" else "closed",
        ui_context=ui_context,
        normalized_projection_text=text,
        dialog_text=text,
        dialog_head=text,
        dialog_tail=text,
        anomaly_codes=[],
        baseline_invalidated=False,
        operator_blocked_excerpt=None,
    )


class _Harness:
    """One store, channel, and tracker wired for a selected adapter."""

    def __init__(
        self,
        tmp_path: Path,
        *,
        adapter: str = "codex",
        state: TrackedStateSnapshot | None = None,
    ) -> None:
        """Build the adapter-owned store and attach its channel."""

        self.adapter = adapter
        self.store = HookObservationStore(tmp_path, generation=1, adapter=adapter)
        channel = HookObservationChannel.from_session_root(tmp_path, adapter=adapter)
        assert channel is not None
        self.tracker = LiveSessionTracker(
            identity=_identity(tool=adapter),
            recent_transition_limit=24,
            stability_threshold_seconds=1.0,
            completion_stability_seconds=1.0,
            unknown_to_stalled_timeout_seconds=30.0,
            final_stable_active_recovery_seconds=20.0,
            hook_channel=channel,
        )
        self.set_state(state or _tracker_state())

    def set_state(self, state: TrackedStateSnapshot) -> None:
        """Install one static tracker snapshot."""

        self.tracker.m_tracker_session = _StaticTrackerSession(state=state)

    def append(self, event_name: str, **extra: object) -> None:
        """Append one raw provider event through the adapter store."""

        self.store.append_event({"hook_event_name": event_name, **extra})

    def cycle(
        self,
        *,
        at: float,
        state: TrackedStateSnapshot | None = None,
        surface: HoumaoParsedSurface | None = None,
        output_text: str | None = None,
        transport_state: str = "tmux_up",
        process_state: str = "tui_up",
        parse_status: str = "parsed",
        use_default_surface: bool = True,
    ) -> HoumaoTerminalStateResponse:
        """Record one tracker cycle at the given monotonic time."""

        if state is not None:
            self.set_state(state)
        parsed_surface = surface
        if parsed_surface is None and use_default_surface:
            parsed_surface = _surface()
        return self.tracker.record_cycle(
            identity=_identity(tool=self.adapter),
            observed_at_utc=f"2026-10-20T05:00:{int(at) % 60:02d}+00:00",
            monotonic_ts=at,
            transport_state=transport_state,  # type: ignore[arg-type]
            process_state=process_state,  # type: ignore[arg-type]
            parse_status=parse_status,  # type: ignore[arg-type]
            probe_snapshot=None,
            probe_error=None,
            parse_error=None,
            parsed_surface=parsed_surface,
            output_text=output_text,
        )


def _gateway_runtime_for(state: HoumaoTerminalStateResponse) -> GatewayServiceRuntime:
    """Build a gateway runtime shell bound to one static tracked state."""

    runtime = object.__new__(GatewayServiceRuntime)
    runtime.m_tui_tracking = _StaticTrackingRuntime(state=state)  # type: ignore[assignment]
    return runtime


def test_tracker_selects_codex_adapter_from_tool_identity(tmp_path: Path) -> None:
    codex_store = HookObservationStore(tmp_path, generation=1, adapter="codex")
    codex_store.append_event({"hook_event_name": "SessionStart", "source": "startup"})
    tracker = LiveSessionTracker(
        identity=_identity(tool="codex"),
        recent_transition_limit=8,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )

    assert tracker.ensure_hook_channel_from_session_root(str(tmp_path)) is True
    assert tracker.m_hook_adapter == "codex"
    assert tracker.m_hook_channel is not None
    assert tracker.m_hook_channel.adapter == "codex"
    assert tracker.m_hook_channel.events_path == (
        tmp_path / "hook-observation" / "codex" / "events.ndjson"
    )

    claude_root = tmp_path / "claude-root"
    claude_store = HookObservationStore(claude_root, generation=1)
    claude_store.append_event({"hook_event_name": "SessionStart"})
    claude_tracker = LiveSessionTracker(
        identity=_identity(tool="claude"),
        recent_transition_limit=8,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )

    assert claude_tracker.ensure_hook_channel_from_session_root(str(claude_root)) is True
    assert claude_tracker.m_hook_adapter == "claude"
    assert claude_tracker.m_hook_channel is not None
    assert claude_tracker.m_hook_channel.events_path == (
        claude_root / "hook-observation" / "claude" / "events.ndjson"
    )


def test_codex_esc_interrupt_settles_interrupted_from_hook_evidence(
    tmp_path: Path,
) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", turn_id=TURN_1, prompt="SECRET_PROMPT_TEXT")

    active = harness.cycle(at=0.0)

    assert active.turn.phase == "active"
    assert active.last_turn.result == "none"

    harness.append("Interrupt", turn_id=TURN_1)

    state = harness.cycle(at=1.0)

    assert state.turn.phase == "ready"
    assert state.last_turn.result == "interrupted"
    assert state.last_turn.source == "hook_observation"
    assert state.work == "unknown"
    assert state.settled is False
    assert state.observation_channels is not None
    assert state.observation_channels[0].provider == "codex"
    assert state.observation_channels[0].counters is not None
    assert state.observation_channels[0].counters.deny_settles == 0
    assert state.observation_channels[0].counters.terminal_gaps == 0
    assert "SECRET_PROMPT_TEXT" not in state.model_dump_json()


def test_codex_deny_abort_enters_blocked_then_settles_interrupted(
    tmp_path: Path,
) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", turn_id=TURN_1)
    harness.append(
        "PreToolUse",
        turn_id=TURN_1,
        tool_name="Bash",
        tool_use_id="tool-1",
        tool_input={"command": "rm -rf build"},
    )
    harness.append(
        "PermissionRequest",
        turn_id=TURN_1,
        tool_name="Bash",
        tool_input={"command": "rm -rf build", "description": "cleanup"},
    )

    blocked = harness.cycle(at=0.0)

    assert blocked.turn.phase == "blocked"
    assert blocked.operator_state is not None
    assert blocked.operator_state.status == "waiting_user_answer"
    assert blocked.operator_state.completion_state == "blocked"
    assert blocked.observation_channels is not None
    assert blocked.observation_channels[0].counters is not None
    assert blocked.observation_channels[0].counters.allow_settles == 0
    assert blocked.observation_channels[0].counters.deny_settles == 0

    # A ready-looking TUI surface must not dismiss a Codex hook blocked mark.
    still_blocked = harness.cycle(at=1.0)
    assert still_blocked.turn.phase == "blocked"

    harness.append("Interrupt", turn_id=TURN_1)

    state = harness.cycle(at=2.0)

    assert state.turn.phase == "ready"
    assert state.last_turn.result == "interrupted"
    assert state.last_turn.source == "hook_observation"
    assert state.work == "unknown"
    assert state.observation_channels is not None
    assert state.observation_channels[0].counters is not None
    assert state.observation_channels[0].counters.deny_settles == 1
    assert state.observation_channels[0].counters.terminal_gaps == 0


def test_codex_blocked_settles_active_only_on_the_paired_post_tool_use(
    tmp_path: Path,
) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", turn_id=TURN_1)
    harness.append(
        "PreToolUse",
        turn_id=TURN_1,
        tool_name="Bash",
        tool_use_id="tool-1",
        tool_input={"command": "make test"},
    )
    harness.append(
        "PermissionRequest",
        turn_id=TURN_1,
        tool_name="Bash",
        tool_input={"command": "make test"},
    )

    assert harness.cycle(at=0.0).turn.phase == "blocked"

    harness.append("PostToolUse", turn_id=TURN_1, tool_name="Bash", tool_use_id="tool-2")
    mismatched = harness.cycle(at=1.0)

    assert mismatched.turn.phase == "blocked"
    assert mismatched.observation_channels is not None
    assert mismatched.observation_channels[0].counters is not None
    assert mismatched.observation_channels[0].counters.allow_settles == 0

    harness.append("PostToolUse", turn_id=TURN_1, tool_name="Bash", tool_use_id="tool-1")
    allowed = harness.cycle(at=2.0)

    assert allowed.turn.phase == "active"
    assert allowed.last_turn.result == "none"
    assert allowed.observation_channels is not None
    assert allowed.observation_channels[0].counters is not None
    assert allowed.observation_channels[0].counters.allow_settles == 1

    harness.append("Stop", turn_id=TURN_1, stop_hook_active=False)
    settled = harness.cycle(at=3.0)

    assert settled.turn.phase == "ready"
    assert settled.last_turn.result == "success"
    assert settled.last_turn.source == "hook_observation"


def test_codex_compaction_holds_terminal_and_continues_the_next_epoch(
    tmp_path: Path,
) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", turn_id=TURN_1)
    harness.append("Stop", turn_id=TURN_1, stop_hook_active=False)

    settled = harness.cycle(at=0.0)

    assert settled.turn.phase == "ready"
    assert settled.last_turn.result == "success"
    assert settled.last_turn.source == "hook_observation"

    harness.append("PreCompact", trigger="auto", turn_id="compact-1")
    during = harness.cycle(at=1.0)

    assert during.turn.phase == "ready"
    assert during.last_turn.result == "success"
    assert harness.tracker.m_hook_posture is not None
    assert harness.tracker.m_hook_posture.maintenance_active is True

    # A compaction repaint can trip the TUI silent-abort inference. Codex
    # hook evidence is authoritative for its epoch, so success must stand.
    interrupted_tui = _tracker_state(
        last_turn_result="interrupted",
        last_turn_source="surface_inference",
    )
    repainted = harness.cycle(at=2.0, state=interrupted_tui)

    assert repainted.turn.phase == "ready"
    assert repainted.last_turn.result == "success"
    assert repainted.last_turn.source == "hook_observation"
    assert "hook_success_tui_interrupted" not in repainted.diagnostics.hook_conflict_reasons

    harness.append("PostCompact", trigger="auto", turn_id="compact-1")
    after_window = harness.cycle(at=3.0)
    assert after_window.turn.phase == "ready"
    assert after_window.last_turn.result == "success"

    harness.append("SessionStart", source="compact", session_id=SESSION_ID)
    boundary = harness.cycle(at=4.0)
    assert boundary.turn.phase == "ready"
    assert boundary.last_turn.result == "success"

    harness.append("UserPromptSubmit", turn_id=TURN_2)
    next_epoch = harness.cycle(at=5.0, state=_tracker_state())
    assert next_epoch.turn.phase == "active"
    assert next_epoch.last_turn.result == "none"

    harness.append("Stop", turn_id=TURN_2, stop_hook_active=False)
    final = harness.cycle(at=6.0)

    assert final.turn.phase == "ready"
    assert final.last_turn.result == "success"
    assert final.last_turn.source == "hook_observation"
    assert final.observation_channels is not None
    assert final.observation_channels[0].counters is not None
    assert final.observation_channels[0].counters.turn_epochs == 2
    assert final.observation_channels[0].counters.compaction_boundaries == 1


def test_codex_compaction_window_suppresses_tui_idle_heuristics(
    tmp_path: Path,
) -> None:
    harness = _Harness(
        tmp_path,
        state=_tracker_state(turn_phase="active", active_reasons=("status_row",)),
    )
    harness.append("PreCompact", trigger="manual", turn_id="compact-1")

    for at in (0.0, 1.0, 6.0, 21.0, 25.0):
        state = harness.cycle(at=at, output_text="compacting")
        assert state.turn.phase == "active"

    assert harness.tracker.m_hook_posture is not None
    assert harness.tracker.m_hook_posture.maintenance_active is True

    harness.append("PostCompact", trigger="manual", turn_id="compact-1")
    restored = harness.cycle(at=26.0)

    assert harness.tracker.m_hook_posture is not None
    assert harness.tracker.m_hook_posture.maintenance_active is False
    assert restored.turn.phase == "active"


def test_codex_kill_gap_publishes_unknown_and_never_success(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", turn_id=TURN_1)

    assert harness.cycle(at=0.0).turn.phase == "active"

    # The TUI is allowed to look settled in the last captured frame; the hook
    # stream proves the turn was still open when the provider died.
    misleading_tui = _tracker_state(
        turn_phase="ready",
        last_turn_result="success",
        last_turn_source="surface_inference",
    )
    gap = harness.cycle(
        at=1.0,
        state=misleading_tui,
        transport_state="tmux_missing",
        process_state="unknown",
        parse_status="transport_unavailable",
        use_default_surface=False,
    )

    assert gap.turn.phase == "unknown"
    assert gap.last_turn.result == "none"
    assert gap.last_turn.source == "none"
    assert gap.work == "unknown"
    assert gap.settled is False
    assert gap.diagnostics.hook_channel_state == "active"
    assert gap.diagnostics.hook_counters is not None
    assert gap.diagnostics.hook_counters.terminal_gaps == 1
    assert "hook_terminal_gap" in gap.diagnostics.hook_conflict_reasons
    assert gap.observation_channels is not None
    assert gap.observation_channels[0].provider == "codex"
    assert gap.observation_channels[0].counters is not None
    assert gap.observation_channels[0].counters.terminal_gaps == 1

    harness.store.begin_generation(2)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", turn_id=TURN_2)
    restarted = harness.cycle(at=2.0, state=_tracker_state())

    assert restarted.turn.phase == "active"
    assert restarted.last_turn.result == "none"


def test_codex_tui_interrupt_does_not_override_a_hook_success(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", turn_id=TURN_1)
    harness.append("Stop", turn_id=TURN_1, stop_hook_active=False)

    assert harness.cycle(at=0.0).last_turn.result == "success"

    state = harness.cycle(
        at=1.0,
        state=_tracker_state(
            last_turn_result="interrupted",
            last_turn_source="surface_inference",
        ),
    )

    assert state.turn.phase == "ready"
    assert state.last_turn.result == "success"
    assert state.last_turn.source == "hook_observation"
    assert "hook_success_tui_interrupted" not in state.diagnostics.hook_conflict_reasons


def test_claude_interrupted_stays_tui_derived(tmp_path: Path) -> None:
    harness = _Harness(tmp_path, adapter="claude")
    harness.append("SessionStart", source="startup")
    harness.append("UserPromptSubmit", prompt_id="p1")

    assert harness.cycle(at=0.0).turn.phase == "active"

    # Claude has no Interrupt hook event. Its TUI temporal interrupt evidence
    # remains load-bearing and overrides a hook success for the same turn.
    harness.append("Stop", prompt_id="p1", background_tasks=[])
    interrupted = harness.cycle(
        at=1.0,
        state=_tracker_state(
            last_turn_result="interrupted",
            last_turn_source="surface_inference",
        ),
    )

    assert interrupted.turn.phase == "ready"
    assert interrupted.last_turn.result == "interrupted"
    assert interrupted.last_turn.source == "hook_observation"
    assert interrupted.observation_channels is not None
    assert interrupted.observation_channels[0].provider == "claude"
    assert "hook_success_tui_interrupted" in interrupted.diagnostics.hook_conflict_reasons


def test_gateway_hook_admission_is_provider_neutral_for_codex_blocked(
    tmp_path: Path,
) -> None:
    codex_harness = _Harness(tmp_path / "codex")
    codex_harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    codex_harness.append("UserPromptSubmit", turn_id=TURN_1)
    codex_harness.append(
        "PreToolUse",
        turn_id=TURN_1,
        tool_name="Bash",
        tool_use_id="tool-1",
        tool_input={"command": "make deploy"},
    )
    codex_harness.append(
        "PermissionRequest",
        turn_id=TURN_1,
        tool_name="Bash",
        tool_input={"command": "make deploy"},
    )
    codex_blocked = codex_harness.cycle(at=0.0)

    claude_harness = _Harness(tmp_path / "claude", adapter="claude")
    claude_harness.append("UserPromptSubmit", prompt_id="p1")
    claude_harness.append("PermissionRequest", prompt_id="p1", tool_name="Bash")
    claude_blocked = claude_harness.cycle(at=0.0)

    assert codex_blocked.turn.phase == "blocked"
    assert claude_blocked.turn.phase == "blocked"
    assert codex_blocked.observation_channels is not None
    assert codex_blocked.observation_channels[0].provider == "codex"
    assert claude_blocked.observation_channels is not None
    assert claude_blocked.observation_channels[0].provider == "claude"

    codex_runtime = _gateway_runtime_for(codex_blocked)
    claude_runtime = _gateway_runtime_for(claude_blocked)

    for policy in ("ready_only", "if_no_pending"):
        codex_reasons = codex_runtime._hook_admission_reasons_locked(  # noqa: SLF001
            admission_policy=policy  # type: ignore[arg-type]
        )
        claude_reasons = claude_runtime._hook_admission_reasons_locked(  # noqa: SLF001
            admission_policy=policy  # type: ignore[arg-type]
        )
        assert codex_reasons == claude_reasons
        assert codex_reasons

    assert codex_runtime._hook_admission_reasons_locked(admission_policy="ready_only") == [  # noqa: SLF001
        "hook.turn_phase='blocked'"
    ]
    assert codex_runtime._hook_admission_reasons_locked(  # noqa: SLF001
        admission_policy="if_no_pending"
    ) == ["hook.blocked=true"]
    assert codex_runtime._hook_admission_reasons_locked(admission_policy="always") == []  # noqa: SLF001

    assert codex_blocked.observation_channels is not None
    degraded = codex_blocked.model_copy(
        update={
            "observation_channels": [
                codex_blocked.observation_channels[0].model_copy(update={"state": "stopped"})
            ]
        }
    )
    degraded_runtime = _gateway_runtime_for(degraded)
    assert (
        degraded_runtime._hook_admission_reasons_locked(  # noqa: SLF001
            admission_policy="ready_only"
        )
        == []
    )
