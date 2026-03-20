from __future__ import annotations

from houmao.shared_tui_tracking.models import (
    RecordedInputEvent,
    RecordedObservation,
    RuntimeObservation,
)
from houmao.shared_tui_tracking.reducer import replay_timeline


def _observation(
    *,
    sample_id: str,
    elapsed_seconds: float,
    output_text: str,
    runtime: RuntimeObservation | None = None,
) -> RecordedObservation:
    return RecordedObservation(
        sample_id=sample_id,
        elapsed_seconds=elapsed_seconds,
        ts_utc=f"2026-03-20T00:00:{int(elapsed_seconds):02d}+00:00",
        output_text=output_text,
        runtime=runtime,
    )


def _input_event(*, event_id: str, elapsed_seconds: float) -> RecordedInputEvent:
    return RecordedInputEvent(
        event_id=event_id,
        elapsed_seconds=elapsed_seconds,
        ts_utc=f"2026-03-20T00:00:{int(elapsed_seconds):02d}+00:00",
        source="managed_send_keys",
    )


def _active_surface() -> str:
    return (
        "❯ explain the repository carefully\n\n"
        "✢ Unfurling…\n\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "❯\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt\n"
    )


def _success_surface() -> str:
    return (
        "● READY\n\n"
        "✻ Worked for 3s\n\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "❯\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
    )


def test_shared_replay_delays_success_until_settle() -> None:
    observations = [
        _observation(sample_id="s000001", elapsed_seconds=0.0, output_text=_active_surface()),
        _observation(sample_id="s000002", elapsed_seconds=1.0, output_text=_success_surface()),
        _observation(sample_id="s000003", elapsed_seconds=2.2, output_text=_success_surface()),
    ]

    timeline, events = replay_timeline(
        observations=observations,
        tool="claude",
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert timeline[1].last_turn_result == "none"
    assert timeline[2].last_turn_result == "success"
    assert timeline[2].last_turn_source == "surface_inference"
    assert any(item.note == "success_settled" for item in events)


def test_shared_replay_preserves_explicit_input_authority() -> None:
    observations = [
        _observation(sample_id="s000001", elapsed_seconds=0.4, output_text=_active_surface()),
        _observation(sample_id="s000002", elapsed_seconds=1.2, output_text=_success_surface()),
        _observation(sample_id="s000003", elapsed_seconds=2.4, output_text=_success_surface()),
    ]
    input_events = [_input_event(event_id="i000001", elapsed_seconds=0.1)]

    timeline, _events = replay_timeline(
        observations=observations,
        input_events=input_events,
        tool="claude",
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert timeline[-1].last_turn_result == "success"
    assert timeline[-1].last_turn_source == "explicit_input"


def test_shared_replay_uses_surface_inference_without_input_events() -> None:
    observations = [
        _observation(sample_id="s000001", elapsed_seconds=0.4, output_text=_active_surface()),
        _observation(sample_id="s000002", elapsed_seconds=1.2, output_text=_success_surface()),
        _observation(sample_id="s000003", elapsed_seconds=2.4, output_text=_success_surface()),
    ]

    timeline, _events = replay_timeline(
        observations=observations,
        tool="claude",
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert timeline[-1].last_turn_result == "success"
    assert timeline[-1].last_turn_source == "surface_inference"


def test_shared_replay_maps_runtime_loss_to_tui_down() -> None:
    observations = [
        _observation(
            sample_id="s000001",
            elapsed_seconds=0.0,
            output_text=_active_surface(),
            runtime=RuntimeObservation(
                ts_utc="2026-03-20T00:00:00+00:00",
                elapsed_seconds=0.0,
                session_exists=True,
                pane_exists=True,
                pane_dead=True,
                pane_pid=1234,
                pane_pid_alive=False,
                supported_process_pid=4321,
                supported_process_alive=False,
            ),
        )
    ]

    timeline, _events = replay_timeline(
        observations=observations,
        tool="claude",
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert timeline[0].diagnostics_availability == "tui_down"
    assert timeline[0].turn_phase == "unknown"
    assert timeline[0].last_turn_result == "none"
