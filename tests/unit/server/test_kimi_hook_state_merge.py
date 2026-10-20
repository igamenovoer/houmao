"""Kimi hook-posture merge tests for the live session tracker.

Covers the Kimi adapter selection, hook-derived ``interrupted``, the
``PermissionResult``-settled blocked window for both decisions, compaction
continuity and idle-heuristic suppression, terminal-gap publication, queue and
steer evidence, resume generation reset, the Claude TUI-derived-interrupt
regression, the Codex deny-aborts-turn regression, and the provider-neutral
gateway prompt-admission policy.
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


SESSION_ID = "session_e5946585-0949-4cf4-8ecb-cef0c6d5565c"
TURN_0 = "0"
TURN_1 = "1"
TOOL_1 = "tool_8IHFsvSl8v9sJ7a260y2kiOV"
_OBSERVED_VERSIONS = {"claude": "2.1.296", "codex": "0.163.0", "kimi": "2.2.0"}
_DETECTOR_NAMES = {"claude": "claude_code", "codex": "codex_tui", "kimi": "kimi_code"}


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


def _identity(*, tool: str = "kimi") -> HoumaoTrackedSessionIdentity:
    """Return one tracked-session identity for the selected adapter."""

    return HoumaoTrackedSessionIdentity(
        tracked_session_id=f"{tool}-session",
        session_name=f"{tool}-session",
        tool=tool,
        observed_tool_version=_OBSERVED_VERSIONS[tool],
        tmux_session_name=f"HOUMAO-{tool}",
        terminal_aliases=["abcd1234"],
    )


def _tracker_state(
    *,
    tool: str = "kimi",
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
        detector_name=_DETECTOR_NAMES[tool],
        detector_version="2.1.x" if tool == "kimi" else "1.0.x",
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
    tool: str = "kimi",
    ui_context: str = "normal_prompt",
    business_state: str = "idle",
) -> HoumaoParsedSurface:
    """Return one submit-ready parsed surface."""

    text = f"{ui_context}-{business_state}"
    return HoumaoParsedSurface(
        parser_family=f"{tool}_tui_shadow",
        parser_preset_id=tool,
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


def _prompt(text: str = "Create a scratch file.") -> list[dict[str, str]]:
    """Return one Kimi ContentPart[] prompt payload."""

    return [{"text": text, "type": "text"}]


class _Harness:
    """One store, channel, and tracker wired for a selected adapter."""

    def __init__(
        self,
        tmp_path: Path,
        *,
        adapter: str = "kimi",
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
        self.set_state(state or _tracker_state(tool=adapter))

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
            parsed_surface = _surface(tool=self.adapter)
        return self.tracker.record_cycle(
            identity=_identity(tool=self.adapter),
            observed_at_utc=f"2026-10-20T13:36:{int(at) % 60:02d}+00:00",
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


def test_tracker_selects_kimi_adapter_from_tool_identity(tmp_path: Path) -> None:
    kimi_store = HookObservationStore(tmp_path, generation=1, adapter="kimi")
    kimi_store.append_event({"hook_event_name": "SessionStart", "source": "startup"})
    tracker = LiveSessionTracker(
        identity=_identity(tool="kimi"),
        recent_transition_limit=8,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )

    assert tracker.ensure_hook_channel_from_session_root(str(tmp_path)) is True
    assert tracker.m_hook_adapter == "kimi"
    assert tracker.m_hook_channel is not None
    assert tracker.m_hook_channel.adapter == "kimi"
    assert tracker.m_hook_channel.events_path == (
        tmp_path / "hook-observation" / "kimi" / "events.ndjson"
    )


def test_kimi_esc_interrupt_settles_interrupted_from_hook_evidence(
    tmp_path: Path,
) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", is_steer=False, prompt=_prompt("SECRET_PROMPT_TEXT"))
    harness.append("TurnStarted", origin_kind="user", turn_id=0)

    active = harness.cycle(at=0.0)

    assert active.turn.phase == "active"
    assert active.last_turn.result == "none"

    # Esc produces the hook event within ~50 ms; the TUI repaint that follows
    # is corroboration, not authority.
    harness.append("Interrupt", reason="cancelled", turn_id=0)

    state = harness.cycle(at=1.0)

    assert state.turn.phase == "ready"
    assert state.last_turn.result == "interrupted"
    assert state.last_turn.source == "hook_observation"
    assert state.work == "unknown"
    assert state.settled is False
    assert state.observation_channels is not None
    assert state.observation_channels[0].provider == "kimi"
    assert state.observation_channels[0].counters is not None
    assert state.observation_channels[0].counters.deny_settles == 0
    assert state.observation_channels[0].counters.terminal_gaps == 0
    assert harness.tracker.m_hook_posture is not None
    assert harness.tracker.m_hook_posture.counters.interrupts == 1
    assert "SECRET_PROMPT_TEXT" not in state.model_dump_json()


def test_kimi_permission_allow_window_settles_active_at_permission_result(
    tmp_path: Path,
) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", is_steer=False, prompt=_prompt())
    harness.append("TurnStarted", origin_kind="user", turn_id=0)
    harness.append("PreToolUse", tool_call_id=TOOL_1, tool_name="Write")
    harness.append(
        "PermissionRequest",
        turn_id=0,
        tool_call_id=TOOL_1,
        tool_name="Write",
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

    # On the allow path the tool may proceed and report PostToolUse before the
    # permission result arrives; only PermissionResult settles the window.
    harness.append("PostToolUse", tool_call_id=TOOL_1, tool_name="Write")
    still_blocked = harness.cycle(at=1.0)

    assert still_blocked.turn.phase == "blocked"
    assert still_blocked.observation_channels is not None
    assert still_blocked.observation_channels[0].counters is not None
    assert still_blocked.observation_channels[0].counters.allow_settles == 0

    harness.append(
        "PermissionResult",
        turn_id=0,
        tool_call_id=TOOL_1,
        tool_name="Write",
        decision="approved",
    )
    allowed = harness.cycle(at=2.0)

    assert allowed.turn.phase == "active"
    assert allowed.last_turn.result == "none"
    assert allowed.observation_channels is not None
    assert allowed.observation_channels[0].counters is not None
    assert allowed.observation_channels[0].counters.allow_settles == 1
    assert allowed.observation_channels[0].counters.deny_settles == 0

    harness.append("Stop", stop_hook_active=False)
    settled = harness.cycle(at=3.0)

    assert settled.turn.phase == "ready"
    assert settled.last_turn.result == "success"
    assert settled.last_turn.source == "hook_observation"


def test_kimi_permission_deny_window_is_non_terminal_and_settles_success_at_stop(
    tmp_path: Path,
) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", is_steer=False, prompt=_prompt())
    harness.append("TurnStarted", origin_kind="user", turn_id=0)
    harness.append("PreToolUse", tool_call_id=TOOL_1, tool_name="Write")
    harness.append(
        "PermissionRequest",
        turn_id=0,
        tool_call_id=TOOL_1,
        tool_name="Write",
    )
    assert harness.cycle(at=0.0).turn.phase == "blocked"

    harness.append(
        "PermissionResult",
        turn_id=0,
        tool_call_id=TOOL_1,
        tool_name="Write",
        decision="rejected",
    )
    denied = harness.cycle(at=1.0)

    assert denied.turn.phase == "active"
    assert denied.last_turn.result == "none"
    assert denied.observation_channels is not None
    assert denied.observation_channels[0].counters is not None
    assert denied.observation_channels[0].counters.deny_settles == 1
    assert denied.observation_channels[0].counters.allow_settles == 0

    # Kimi has no deny-aborts-turn semantics: the failed call is non-terminal
    # evidence and the turn continues to a normal Stop.
    harness.append(
        "PostToolUseFailure",
        tool_call_id=TOOL_1,
        tool_name="Write",
        error={"code": "internal", "message": "rejected"},
    )
    continued = harness.cycle(at=2.0)

    assert continued.turn.phase == "active"
    assert continued.last_turn.result == "none"

    harness.append("Stop", stop_hook_active=False)
    settled = harness.cycle(at=3.0)

    assert settled.turn.phase == "ready"
    assert settled.last_turn.result == "success"
    assert settled.last_turn.source == "hook_observation"
    assert settled.observation_channels is not None
    assert settled.observation_channels[0].counters is not None
    assert settled.observation_channels[0].counters.deny_settles == 1
    assert settled.observation_channels[0].counters.terminal_gaps == 0


def test_kimi_compaction_holds_terminal_and_continues_the_next_epoch(
    tmp_path: Path,
) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", is_steer=False, prompt=_prompt())
    harness.append("TurnStarted", origin_kind="user", turn_id=0)
    harness.append("Stop", stop_hook_active=False)

    settled = harness.cycle(at=0.0)

    assert settled.turn.phase == "ready"
    assert settled.last_turn.result == "success"
    assert settled.last_turn.source == "hook_observation"

    harness.append("PreCompact", trigger="auto")
    during = harness.cycle(at=1.0)

    assert during.turn.phase == "ready"
    assert during.last_turn.result == "success"
    assert harness.tracker.m_hook_posture is not None
    assert harness.tracker.m_hook_posture.maintenance_active is True

    # A compaction repaint can trip the TUI silent-abort inference. Kimi
    # settles interrupted from its Interrupt hook event, so the latched
    # success must stand.
    interrupted_tui = _tracker_state(
        last_turn_result="interrupted",
        last_turn_source="surface_inference",
    )
    repainted = harness.cycle(at=2.0, state=interrupted_tui)

    assert repainted.turn.phase == "ready"
    assert repainted.last_turn.result == "success"
    assert repainted.last_turn.source == "hook_observation"
    assert "hook_success_tui_interrupted" not in repainted.diagnostics.hook_conflict_reasons

    harness.append("PostCompact", trigger="auto")
    after_window = harness.cycle(at=3.0)
    assert after_window.turn.phase == "ready"
    assert after_window.last_turn.result == "success"

    # Kimi emits no SessionStart(source=compact); the post-compaction turn
    # arms a fresh epoch and binds the continuing integer turn counter.
    harness.append("UserPromptSubmit", is_steer=False, prompt=_prompt())
    harness.append("TurnStarted", origin_kind="user", turn_id=1)
    next_epoch = harness.cycle(at=4.0, state=_tracker_state())
    assert next_epoch.turn.phase == "active"
    assert next_epoch.last_turn.result == "none"

    harness.append("Stop", stop_hook_active=False)
    final = harness.cycle(at=5.0)

    assert final.turn.phase == "ready"
    assert final.last_turn.result == "success"
    assert final.last_turn.source == "hook_observation"
    assert final.observation_channels is not None
    assert final.observation_channels[0].counters is not None
    assert final.observation_channels[0].counters.turn_epochs == 2
    assert final.observation_channels[0].counters.compaction_boundaries == 1


def test_kimi_compaction_window_suppresses_tui_idle_heuristics(
    tmp_path: Path,
) -> None:
    harness = _Harness(
        tmp_path,
        state=_tracker_state(turn_phase="active", active_reasons=("status_row",)),
    )
    harness.append("PreCompact", trigger="manual")

    for at in (0.0, 1.0, 6.0, 21.0, 25.0):
        state = harness.cycle(at=at, output_text="compacting")
        assert state.turn.phase == "active"

    assert harness.tracker.m_hook_posture is not None
    assert harness.tracker.m_hook_posture.maintenance_active is True

    harness.append("PostCompact", trigger="manual")
    restored = harness.cycle(at=26.0)

    assert harness.tracker.m_hook_posture is not None
    assert harness.tracker.m_hook_posture.maintenance_active is False
    assert restored.turn.phase == "active"


def test_kimi_kill_gap_publishes_unknown_and_never_success(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", is_steer=False, prompt=_prompt())
    harness.append("TurnStarted", origin_kind="user", turn_id=0)

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
    assert gap.observation_channels[0].provider == "kimi"
    assert gap.observation_channels[0].counters is not None
    assert gap.observation_channels[0].counters.terminal_gaps == 1

    harness.store.begin_generation(2)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", is_steer=False, prompt=_prompt())
    harness.append("TurnStarted", origin_kind="user", turn_id=1)
    restarted = harness.cycle(at=2.0, state=_tracker_state())

    assert restarted.turn.phase == "active"
    assert restarted.last_turn.result == "none"


def test_kimi_queue_and_steer_do_not_arm_a_second_turn(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", is_steer=False, prompt=_prompt())
    harness.append("TurnStarted", origin_kind="user", turn_id=0)

    assert harness.cycle(at=0.0).turn.phase == "active"

    harness.append("UserPromptQueued", prompt_id="msg_1", queue_length=1)
    harness.append("UserPromptSubmit", is_steer=True, prompt=_prompt("Steer this turn."))
    queued = harness.cycle(at=1.0)

    assert queued.turn.phase == "active"
    assert queued.last_turn.result == "none"
    assert queued.observation_channels is not None
    assert queued.observation_channels[0].counters is not None
    assert queued.observation_channels[0].counters.steer_events == 1
    assert queued.observation_channels[0].counters.turn_epochs == 1
    assert harness.tracker.m_hook_posture is not None
    assert harness.tracker.m_hook_posture.counters.queued_prompts == 1

    harness.append("Stop", stop_hook_active=False)
    settled = harness.cycle(at=2.0)

    assert settled.turn.phase == "ready"
    assert settled.last_turn.result == "success"
    assert settled.observation_channels is not None
    assert settled.observation_channels[0].counters is not None
    assert settled.observation_channels[0].counters.turn_epochs == 1


def test_kimi_resume_generation_resets_turn_state(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", is_steer=False, prompt=_prompt())
    harness.append("TurnStarted", origin_kind="user", turn_id=0)
    harness.append("Stop", stop_hook_active=False)

    settled = harness.cycle(at=0.0)

    assert settled.last_turn.result == "success"
    assert settled.observation_channels is not None
    assert settled.observation_channels[0].generation == 1

    harness.store.begin_generation(2)
    harness.append("SessionStart", source="resume", session_id=SESSION_ID)
    resumed = harness.cycle(at=1.0, state=_tracker_state())

    assert resumed.turn.phase == "ready"
    assert resumed.last_turn.result == "none"
    assert resumed.last_turn.source == "none"
    assert resumed.observation_channels is not None
    assert resumed.observation_channels[0].generation == 2
    assert "hook_orphan_generation" not in resumed.diagnostics.hook_conflict_reasons

    # The integer turn counter continues across the resume generation.
    harness.append("UserPromptSubmit", is_steer=False, prompt=_prompt())
    harness.append("TurnStarted", origin_kind="user", turn_id=1)
    active = harness.cycle(at=2.0)

    assert active.turn.phase == "active"
    assert active.last_turn.result == "none"

    harness.append("Stop", stop_hook_active=False)
    final = harness.cycle(at=3.0)

    assert final.last_turn.result == "success"
    assert final.observation_channels is not None
    assert final.observation_channels[0].counters is not None
    assert final.observation_channels[0].counters.turn_epochs == 2


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
            tool="claude",
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


def test_codex_deny_still_aborts_the_turn(tmp_path: Path) -> None:
    harness = _Harness(tmp_path, adapter="codex")
    harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    harness.append("UserPromptSubmit", turn_id="turn-1")
    harness.append(
        "PreToolUse",
        turn_id="turn-1",
        tool_name="Bash",
        tool_use_id="tool-1",
        tool_input={"command": "rm -rf build"},
    )
    harness.append(
        "PermissionRequest",
        turn_id="turn-1",
        tool_name="Bash",
        tool_input={"command": "rm -rf build"},
    )

    assert harness.cycle(at=0.0).turn.phase == "blocked"

    harness.append("Interrupt", turn_id="turn-1")
    state = harness.cycle(at=1.0)

    assert state.turn.phase == "ready"
    assert state.last_turn.result == "interrupted"
    assert state.last_turn.source == "hook_observation"
    assert state.observation_channels is not None
    assert state.observation_channels[0].provider == "codex"
    assert state.observation_channels[0].counters is not None
    assert state.observation_channels[0].counters.deny_settles == 1


def test_gateway_hook_admission_is_provider_neutral_for_kimi_blocked(
    tmp_path: Path,
) -> None:
    kimi_harness = _Harness(tmp_path / "kimi")
    kimi_harness.append("SessionStart", source="startup", session_id=SESSION_ID)
    kimi_harness.append("UserPromptSubmit", is_steer=False, prompt=_prompt())
    kimi_harness.append("TurnStarted", origin_kind="user", turn_id=0)
    kimi_harness.append("PreToolUse", tool_call_id=TOOL_1, tool_name="Write")
    kimi_harness.append(
        "PermissionRequest",
        turn_id=0,
        tool_call_id=TOOL_1,
        tool_name="Write",
    )
    kimi_blocked = kimi_harness.cycle(at=0.0)

    claude_harness = _Harness(tmp_path / "claude", adapter="claude")
    claude_harness.append("UserPromptSubmit", prompt_id="p1")
    claude_harness.append("PermissionRequest", prompt_id="p1", tool_name="Bash")
    claude_blocked = claude_harness.cycle(at=0.0)

    assert kimi_blocked.turn.phase == "blocked"
    assert claude_blocked.turn.phase == "blocked"
    assert kimi_blocked.observation_channels is not None
    assert kimi_blocked.observation_channels[0].provider == "kimi"

    kimi_runtime = _gateway_runtime_for(kimi_blocked)
    claude_runtime = _gateway_runtime_for(claude_blocked)

    for policy in ("ready_only", "if_no_pending"):
        kimi_reasons = kimi_runtime._hook_admission_reasons_locked(  # noqa: SLF001
            admission_policy=policy  # type: ignore[arg-type]
        )
        claude_reasons = claude_runtime._hook_admission_reasons_locked(  # noqa: SLF001
            admission_policy=policy  # type: ignore[arg-type]
        )
        assert kimi_reasons == claude_reasons
        assert kimi_reasons

    assert kimi_runtime._hook_admission_reasons_locked(admission_policy="ready_only") == [  # noqa: SLF001
        "hook.turn_phase='blocked'"
    ]
    assert kimi_runtime._hook_admission_reasons_locked(  # noqa: SLF001
        admission_policy="if_no_pending"
    ) == ["hook.blocked=true"]
    assert kimi_runtime._hook_admission_reasons_locked(admission_policy="always") == []  # noqa: SLF001

    assert kimi_blocked.observation_channels is not None
    degraded = kimi_blocked.model_copy(
        update={
            "observation_channels": [
                kimi_blocked.observation_channels[0].model_copy(update={"state": "stopped"})
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
