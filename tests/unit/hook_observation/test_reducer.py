"""Unit tests for the pure hook posture reducer and its pipeline."""

from __future__ import annotations

import json

from reactivex.subject import Subject
from reactivex.testing import TestScheduler

from houmao.hook_observation.models import (
    HookObservation,
    HookPosture,
    NormalizedHookKind,
)
from houmao.hook_observation.normalizer import normalize_provider_event
from houmao.hook_observation.reducer import HookPostureReducer, build_hook_posture_pipeline


def _obs(
    kind: NormalizedHookKind,
    *,
    generation: int = 1,
    sequence: int | None = None,
    event_name: str | None = None,
    received_at_utc: str = "2026-10-19T13:00:00+00:00",
    prompt_id: str | None = None,
    session_id: str | None = None,
    tool_name: str | None = None,
    error_class: str | None = None,
    background_work_pending: bool | None = None,
    stop_hook_active: bool | None = None,
    last_assistant_message_present: bool | None = None,
    provider_initiated: bool = False,
    source: str | None = None,
    is_interrupt: bool | None = None,
    malformed: bool = False,
    malformed_reason: str | None = None,
) -> HookObservation:
    return HookObservation(
        kind=kind,
        event_name=event_name or kind,
        channel_generation=generation,
        received_at_utc=received_at_utc,
        sequence=sequence,
        session_id=session_id,
        prompt_id=prompt_id,
        tool_name=tool_name,
        error_class=error_class,
        background_work_pending=background_work_pending,
        stop_hook_active=stop_hook_active,
        last_assistant_message_present=last_assistant_message_present,
        provider_initiated=provider_initiated,
        source=source,
        is_interrupt=is_interrupt,
        malformed=malformed,
        malformed_reason=malformed_reason,
    )


class _Harness:
    def __init__(self, *, reducer: HookPostureReducer | None = None) -> None:
        self.scheduler = TestScheduler()
        self.subject: Subject[HookObservation] = Subject()
        self.results: list[HookPosture] = []
        build_hook_posture_pipeline(
            self.subject,
            scheduler=self.scheduler,
            reducer=reducer,
        ).subscribe(self.results.append)

    def emit(self, at: float, observation: HookObservation) -> HookPosture:
        self.scheduler.advance_to(at)
        self.subject.on_next(observation)
        return self.results[-1]


def test_ordered_turn_arms_and_settles_success() -> None:
    harness = _Harness()
    posture = harness.emit(
        0.0,
        _obs("session_started", sequence=1, session_id="session-1", source="startup"),
    )
    assert posture.session_started is True
    assert posture.session_id == "session-1"
    assert posture.turn_phase == "unknown"

    posture = harness.emit(1.0, _obs("prompt_submitted", sequence=2, prompt_id="p1"))
    assert posture.turn_phase == "active"
    assert posture.active_prompt_id == "p1"
    assert posture.armed_prompt_count == 1
    assert posture.queued_prompt_count == 0

    posture = harness.emit(
        2.0,
        _obs(
            "turn_completed",
            sequence=3,
            prompt_id="p1",
            background_work_pending=False,
            last_assistant_message_present=True,
            stop_hook_active=False,
        ),
    )
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "success"
    assert posture.terminal_prompt_id == "p1"
    assert posture.terminal_consumed_prompt_id == "p1"
    assert posture.terminal_stop_hook_active is False
    assert posture.terminal_message_present is True
    assert posture.work == "clear"
    assert posture.armed_prompt_count == 0
    assert posture.settled is True
    assert posture.counters.normalized_events == 3
    assert posture.diagnostics == ()


def test_out_of_order_terminal_before_prompt_is_orphan() -> None:
    harness = _Harness()
    posture = harness.emit(0.0, _obs("turn_completed", sequence=1, prompt_id="p1"))
    assert posture.turn_phase == "unknown"
    assert posture.terminal_result == "none"
    assert posture.counters.orphan_terminals == 1
    assert posture.diagnostics[-1].kind == "hook_orphan_terminal"

    posture = harness.emit(1.0, _obs("prompt_submitted", sequence=2, prompt_id="p1"))
    assert posture.turn_phase == "active"

    posture = harness.emit(2.0, _obs("turn_completed", sequence=3, prompt_id="p1"))
    assert posture.terminal_result == "success"
    assert posture.counters.orphan_terminals == 1


def test_non_monotonic_sequence_is_processed_in_arrival_order() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("prompt_submitted", sequence=10, prompt_id="p1"))
    posture = harness.emit(1.0, _obs("turn_completed", sequence=9, prompt_id="p1"))

    assert posture.terminal_result == "success"
    assert posture.counters.duplicate_events == 0


def test_duplicate_terminal_is_idempotent() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("prompt_submitted", sequence=2, prompt_id="p1"))
    posture = harness.emit(1.0, _obs("turn_completed", sequence=3, prompt_id="p1"))
    assert posture.terminal_result == "success"

    posture = harness.emit(2.0, _obs("turn_completed", sequence=3, prompt_id="p1"))
    assert posture.terminal_result == "success"
    assert posture.counters.duplicate_events == 1
    assert posture.counters.orphan_terminals == 0
    assert posture.diagnostics[-1].kind == "hook_duplicate_event"


def test_stop_hook_active_terminal_is_not_treated_as_terminal() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("prompt_submitted", sequence=1, prompt_id="p1"))
    posture = harness.emit(
        1.0,
        _obs("turn_completed", sequence=2, prompt_id="p1", stop_hook_active=True),
    )

    assert posture.turn_phase == "active"
    assert posture.terminal_result == "none"
    assert posture.armed_prompt_count == 1
    assert posture.diagnostics[-1].kind == "hook_stop_hook_active"

    posture = harness.emit(
        2.0,
        _obs("turn_completed", sequence=3, prompt_id="p1", stop_hook_active=False),
    )
    assert posture.terminal_result == "success"


def test_terminal_redelivery_with_new_sequence_is_idempotent() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("prompt_submitted", sequence=2, prompt_id="p1"))
    harness.emit(1.0, _obs("turn_completed", sequence=3, prompt_id="p1"))

    posture = harness.emit(2.0, _obs("turn_completed", sequence=4, prompt_id="p1"))
    assert posture.terminal_result == "success"
    assert posture.counters.duplicate_events == 1
    assert posture.counters.orphan_terminals == 0
    assert posture.diagnostics[-1].kind == "hook_duplicate_event"


def test_orphan_terminal_never_manufactures_last_turn() -> None:
    harness = _Harness()
    posture = harness.emit(
        0.0,
        _obs("turn_failed", sequence=1, prompt_id="p1", error_class="overloaded_error"),
    )

    assert posture.turn_phase == "unknown"
    assert posture.terminal_result == "none"
    assert posture.terminal_error_class is None
    assert posture.counters.orphan_terminals == 1


def test_stale_generation_is_dropped_and_new_generation_resets() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("generation_started", generation=1, event_name="generation_boundary"))
    posture = harness.emit(1.0, _obs("prompt_submitted", generation=1, sequence=2, prompt_id="p1"))
    assert posture.turn_phase == "active"

    posture = harness.emit(
        2.0,
        _obs("generation_started", generation=2, event_name="generation_boundary"),
    )
    assert posture.generation == 2
    assert posture.turn_phase == "unknown"
    assert posture.armed_prompt_count == 0

    posture = harness.emit(3.0, _obs("prompt_submitted", generation=1, sequence=3, prompt_id="p1"))
    assert posture.generation == 2
    assert posture.turn_phase == "unknown"
    assert posture.counters.orphan_generations == 1
    assert posture.diagnostics[-1].kind == "hook_orphan_generation"

    harness.emit(4.0, _obs("prompt_submitted", generation=2, sequence=1, prompt_id="p2"))
    posture = harness.emit(5.0, _obs("turn_completed", generation=2, sequence=2, prompt_id="p2"))
    assert posture.terminal_result == "success"


def test_queued_prompt_fifo_matches_s7_sequence() -> None:
    harness = _Harness()
    first = harness.emit(0.0, _obs("prompt_submitted", sequence=2, prompt_id="in-flight"))
    assert first.active_prompt_id == "in-flight"

    posture = harness.emit(1.0, _obs("prompt_submitted", sequence=3, prompt_id="in-flight"))
    assert posture.armed_prompt_count == 2
    assert posture.queued_prompt_count == 1
    assert posture.active_prompt_id == "in-flight"

    posture = harness.emit(
        2.0,
        _obs("turn_completed", sequence=4, prompt_id="in-flight", background_work_pending=False),
    )
    assert posture.terminal_result == "success"
    assert posture.terminal_prompt_id == "in-flight"
    assert posture.terminal_consumed_prompt_id == "in-flight"
    assert posture.armed_prompt_count == 1
    assert posture.turn_phase == "active"

    posture = harness.emit(
        3.0,
        _obs("turn_completed", sequence=5, prompt_id="queued-turn", background_work_pending=False),
    )
    assert posture.terminal_result == "success"
    assert posture.terminal_prompt_id == "queued-turn"
    assert posture.terminal_consumed_prompt_id == "in-flight"
    assert posture.armed_prompt_count == 0
    assert posture.turn_phase == "ready"
    assert posture.counters.orphan_terminals == 0
    assert posture.counters.duplicate_events == 0


def test_ghost_turn_clears_work_axis_matches_s5_sequence() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("prompt_submitted", sequence=2, prompt_id="p1"))
    posture = harness.emit(
        1.0,
        _obs("turn_completed", sequence=3, prompt_id="p1", background_work_pending=True),
    )
    assert posture.work == "pending"
    assert posture.settled is False

    posture = harness.emit(
        2.0,
        _obs("prompt_submitted", sequence=5, prompt_id="ghost", provider_initiated=True),
    )
    assert posture.turn_phase == "active"
    assert posture.active_prompt_provider_initiated is True

    posture = harness.emit(
        3.0,
        _obs("turn_completed", sequence=6, prompt_id="ghost", background_work_pending=False),
    )
    assert posture.work == "clear"
    assert posture.terminal_result == "success"
    assert posture.counters.orphan_terminals == 0


def test_turn_failed_makes_no_work_statement() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("prompt_submitted", sequence=1, prompt_id="p1"))
    posture = harness.emit(
        1.0,
        _obs("turn_completed", sequence=2, prompt_id="p1", background_work_pending=True),
    )
    assert posture.work == "pending"

    harness.emit(2.0, _obs("prompt_submitted", sequence=3, prompt_id="p2"))
    posture = harness.emit(
        3.0,
        _obs(
            "turn_failed",
            sequence=4,
            prompt_id="p2",
            error_class="overloaded_error",
            background_work_pending=None,
        ),
    )
    assert posture.terminal_result == "known_failure"
    assert posture.terminal_error_class == "overloaded_error"
    assert posture.work == "pending"


def test_permission_blocks_and_post_tool_use_resolves_matches_s3_allow() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("prompt_submitted", sequence=1, prompt_id="p1"))

    posture = harness.emit(
        1.0,
        _obs("permission_requested", sequence=2, prompt_id="p1", tool_name="Write"),
    )
    assert posture.turn_phase == "blocked"
    assert posture.blocked is True
    assert posture.blocked_tool_name == "Write"

    posture = harness.emit(
        2.0,
        _obs("activity", sequence=3, prompt_id="p1", tool_name="Write"),
    )
    assert posture.turn_phase == "active"
    assert posture.blocked is False
    assert posture.blocked_tool_name is None

    posture = harness.emit(3.0, _obs("turn_completed", sequence=4, prompt_id="p1"))
    assert posture.terminal_result == "success"


def test_denial_silence_stays_blocked_without_a_terminal_matches_s3_deny() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("prompt_submitted", sequence=1, prompt_id="p1"))
    posture = harness.emit(
        1.0,
        _obs("permission_requested", sequence=2, prompt_id="p1", tool_name="Write"),
    )

    assert posture.turn_phase == "blocked"
    assert posture.terminal_result == "none"
    assert posture.armed_prompt_count == 1
    assert posture.counters.orphan_terminals == 0
    assert posture.work == "unknown"


def test_permission_without_armed_prompt_does_not_block() -> None:
    harness = _Harness()
    posture = harness.emit(
        0.0,
        _obs("permission_requested", sequence=1, prompt_id="p1", tool_name="Write"),
    )

    assert posture.turn_phase == "unknown"
    assert posture.blocked_tool_name is None
    assert posture.diagnostics[-1].kind == "permission_without_armed_prompt"


def test_maintenance_window_preserves_armed_turn_and_terminal() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("prompt_submitted", sequence=1, prompt_id="p1", session_id="s1"))
    posture = harness.emit(1.0, _obs("maintenance_started", sequence=2))
    assert posture.maintenance_active is True
    assert posture.turn_phase == "active"

    posture = harness.emit(
        2.0,
        _obs("session_started", sequence=3, session_id="s1", source="compact"),
    )
    assert posture.maintenance_active is True
    assert posture.turn_phase == "active"
    assert posture.session_id == "s1"

    posture = harness.emit(3.0, _obs("maintenance_ended", sequence=4))
    assert posture.maintenance_active is False
    assert posture.turn_phase == "active"

    posture = harness.emit(4.0, _obs("turn_completed", sequence=5, prompt_id="p1"))
    assert posture.terminal_result == "success"

    posture = harness.emit(5.0, _obs("maintenance_started", sequence=6))
    assert posture.maintenance_active is True
    assert posture.terminal_result == "success"

    posture = harness.emit(6.0, _obs("maintenance_ended", sequence=7))
    assert posture.maintenance_active is False
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "success"


def test_session_start_sources_reset_or_preserve_posture() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("prompt_submitted", sequence=1, prompt_id="p1", session_id="s1"))
    posture = harness.emit(1.0, _obs("turn_completed", sequence=2, prompt_id="p1"))
    assert posture.terminal_result == "success"

    posture = harness.emit(
        2.0,
        _obs("session_started", sequence=3, session_id="s1", source="resume"),
    )
    assert posture.terminal_result == "success"
    assert posture.session_id == "s1"

    posture = harness.emit(
        3.0,
        _obs("session_started", sequence=4, session_id="s2", source="startup"),
    )
    assert posture.terminal_result == "none"
    assert posture.turn_phase == "unknown"
    assert posture.session_id == "s2"
    assert posture.work == "unknown"


def test_unknown_and_malformed_observations_are_counted_and_excluded() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("prompt_submitted", sequence=1, prompt_id="p1"))

    posture = harness.emit(
        1.0,
        _obs("unknown", sequence=2, event_name="Notification"),
    )
    assert posture.turn_phase == "active"
    assert posture.counters.unknown_events == 1
    assert posture.counters.malformed_events == 0
    assert posture.diagnostics[-1].kind == "hook_unknown_event"

    posture = harness.emit(
        2.0,
        _obs(
            "unknown",
            sequence=3,
            event_name="<malformed>",
            malformed=True,
            malformed_reason="missing_event_name",
        ),
    )
    assert posture.turn_phase == "active"
    assert posture.counters.unknown_events == 1
    assert posture.counters.malformed_events == 1
    assert posture.diagnostics[-1].kind == "hook_malformed_event"
    assert posture.diagnostics[-1].detail == "missing_event_name"


def test_prompt_clears_the_previous_terminal_latch() -> None:
    harness = _Harness()
    harness.emit(0.0, _obs("prompt_submitted", sequence=1, prompt_id="p1"))
    posture = harness.emit(1.0, _obs("turn_completed", sequence=2, prompt_id="p1"))
    assert posture.terminal_result == "success"

    posture = harness.emit(2.0, _obs("prompt_submitted", sequence=3, prompt_id="p2"))
    assert posture.terminal_result == "none"
    assert posture.turn_phase == "active"
    assert posture.active_prompt_id == "p2"


def test_activity_without_an_armed_prompt_does_not_activate() -> None:
    harness = _Harness()
    posture = harness.emit(0.0, _obs("activity", sequence=1, tool_name="Bash"))

    assert posture.turn_phase == "unknown"
    assert posture.blocked_tool_name is None


def test_diagnostics_are_bounded_and_secret_free() -> None:
    reducer = HookPostureReducer(diagnostic_capacity=4)
    harness = _Harness(reducer=reducer)
    for index in range(10):
        harness.emit(
            float(index),
            _obs("unknown", sequence=index + 1, event_name="Notification"),
        )
    posture = harness.results[-1]
    assert len(posture.diagnostics) == 4
    assert posture.counters.unknown_events == 10

    secret_observation = normalize_provider_event(
        {
            "hook_event_name": "UserPromptSubmit",
            "prompt_id": "p1",
            "prompt": "SECRET_PROMPT_TEXT",
        },
        channel_generation=1,
        received_at_utc="2026-10-19T13:00:00+00:00",
        sequence=20,
    )
    posture = harness.emit(20.0, secret_observation)
    serialized = json.dumps(posture.to_payload())
    assert "SECRET_PROMPT_TEXT" not in serialized
