from __future__ import annotations

from pathlib import Path

from houmao.explore.claude_code_state_tracking.compare import compare_timelines
from houmao.explore.claude_code_state_tracking.detectors import select_claude_detector
from houmao.explore.claude_code_state_tracking.groundtruth import classify_groundtruth
from houmao.explore.claude_code_state_tracking.models import RecordedObservation, RuntimeObservation
from houmao.explore.claude_code_state_tracking.replay import replay_timeline
from houmao.explore.claude_code_state_tracking.scenario import load_scenario


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


def _ready_surface(prompt_text: str = "") -> str:
    return (
        "────────────────────────────────────────────────────────────────────────────────\n"
        f"❯ {prompt_text}\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
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


def _interrupted_surface() -> str:
    return (
        "❯ explain the repository carefully\n"
        "  ⎿ \u00a0Interrupted · What should Claude do instead?\n\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "❯\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
    )


def _known_failure_surface() -> str:
    return (
        "❯ hi\n"
        "\x1b[38;5;246m  ⎿  \x1b[38;5;211mNot logged in · Please run /login\x1b[39m\n\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "❯\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "  \x1b[38;5;246m? for shortcuts\x1b[39m                                                  "
        "\x1b[38;5;211mNot logged in · Run /login\x1b[39m\n"
    )


def _stale_failure_surface() -> str:
    return (
        "❯ hi\n"
        "\x1b[38;5;246m  ⎿  \x1b[38;5;211mNot logged in · Please run /login\x1b[39m\n\n"
        "❯ /model\n"
        "  ⎿  Set model to Sonnet 4.6 (default)\n\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "❯ I am typing something\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "  \x1b[38;5;246m? for shortcuts\x1b[39m                                                  "
        "\x1b[38;5;211mNot logged in · Run /login\x1b[39m\n"
    )


def _success_surface(answer_suffix: str = "") -> str:
    return (
        "● Here are today's top 10 trending papers on Hugging Face:\n"
        f"  1. Example paper{answer_suffix}\n\n"
        "✻ Worked for 35s\n\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "❯\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
    )


def _short_success_surface() -> str:
    return (
        "❯ Reply with the single word READY and stop.\n\n"
        "● READY\n\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "❯\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
    )


def _short_success_surface_with_footer_bullet() -> str:
    return (
        "❯ Reply with the single word RECOVERED and stop.\n\n"
        "● RECOVERED\n\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "❯\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
        "  ● high · /effort\n"
    )


def _success_candidate_with_truncated_active_footer() -> str:
    return (
        "❯ Write a long explanation.\n\n"
        "● 1. Event Sourcing — Instead of storing only the current state, every change is recorded.\n\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "❯\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to…\n"
    )


def _slash_menu_surface(*, active: bool) -> str:
    spinner = "✢ Musing…\n\n" if active else ""
    footer = (
        "  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt\n"
        if active
        else "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
    )
    return (
        "❯ Find ten recent interesting papers and summarize each one carefully.\n\n"
        f"{spinner}"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "❯ /\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "  /openspec-apply-change               Implement tasks from an OpenSpec change.\n"
        "  /add-dir                             Add a new working directory\n"
        f"{footer}"
    )


def test_load_scenario_reads_json_fixture() -> None:
    scenario = load_scenario(
        Path("scripts/explore/claude-code-state-tracking/scenarios/simple-success.json")
    )

    assert scenario.scenario_id == "simple-success"
    assert scenario.steps[1].action == "send_text"


def test_detector_matches_interrupted_signal() -> None:
    detector = select_claude_detector(observed_version="2.1.80 (Claude Code)")

    signals = detector.detect(output_text=_interrupted_surface())

    assert signals.interrupted is True
    assert signals.known_failure is False


def test_detector_matches_current_known_failure_and_suppresses_stale_failure() -> None:
    detector = select_claude_detector(observed_version="2.1.80 (Claude Code)")

    current_failure = detector.detect(output_text=_known_failure_surface())
    stale_failure = detector.detect(output_text=_stale_failure_surface())

    assert current_failure.known_failure is True
    assert stale_failure.known_failure is False


def test_detector_marks_live_spinner_variants_active() -> None:
    detector = select_claude_detector(observed_version="2.1.80 (Claude Code)")

    signals = detector.detect(output_text=_active_surface())

    assert signals.active_evidence is True
    assert "thinking_line" in signals.active_reasons


def test_detector_marks_non_active_slash_overlay_unknown() -> None:
    observations = [
        _observation(
            sample_id="s000001", elapsed_seconds=0.0, output_text=_slash_menu_surface(active=False)
        )
    ]

    timeline = classify_groundtruth(
        observations=observations,
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert timeline[0].turn_phase == "unknown"


def test_detector_keeps_active_slash_overlay_active() -> None:
    observations = [
        _observation(
            sample_id="s000001", elapsed_seconds=0.0, output_text=_slash_menu_surface(active=True)
        )
    ]

    timeline = classify_groundtruth(
        observations=observations,
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert timeline[0].turn_phase == "active"


def test_success_candidate_ignores_footer_bullet_lines() -> None:
    observations = [
        _observation(
            sample_id="s000001",
            elapsed_seconds=0.0,
            output_text=_short_success_surface_with_footer_bullet(),
        ),
        _observation(
            sample_id="s000002",
            elapsed_seconds=1.2,
            output_text=_short_success_surface_with_footer_bullet(),
        ),
    ]

    timeline = classify_groundtruth(
        observations=observations,
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert timeline[-1].last_turn_result == "success"


def test_detector_treats_truncated_interrupt_footer_as_active() -> None:
    detector = select_claude_detector(observed_version="2.1.80 (Claude Code)")

    signals = detector.detect(output_text=_success_candidate_with_truncated_active_footer())

    assert signals.footer_interruptable is True
    assert signals.active_evidence is True
    assert signals.success_candidate is False


def test_groundtruth_delays_success_until_stable_candidate_window() -> None:
    observations = [
        _observation(sample_id="s000001", elapsed_seconds=0.0, output_text=_active_surface()),
        _observation(
            sample_id="s000002", elapsed_seconds=1.0, output_text=_short_success_surface()
        ),
        _observation(
            sample_id="s000003", elapsed_seconds=2.2, output_text=_short_success_surface()
        ),
    ]

    timeline = classify_groundtruth(
        observations=observations,
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert timeline[0].turn_phase == "active"
    assert timeline[1].last_turn_result == "none"
    assert timeline[2].last_turn_result == "success"


def test_replay_delays_success_until_rx_timer_settles() -> None:
    observations = [
        _observation(sample_id="s000001", elapsed_seconds=0.0, output_text=_active_surface()),
        _observation(
            sample_id="s000002", elapsed_seconds=1.0, output_text=_short_success_surface()
        ),
        _observation(
            sample_id="s000003", elapsed_seconds=2.2, output_text=_short_success_surface()
        ),
    ]

    timeline, events = replay_timeline(
        observations=observations,
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert timeline[1].last_turn_result == "none"
    assert timeline[2].last_turn_result == "success"
    assert any(item.note == "success_settled" for item in events)


def test_replay_resets_success_timer_when_completion_surface_changes() -> None:
    observations = [
        _observation(sample_id="s000001", elapsed_seconds=0.0, output_text=_active_surface()),
        _observation(sample_id="s000002", elapsed_seconds=1.0, output_text=_success_surface()),
        _observation(
            sample_id="s000003", elapsed_seconds=1.6, output_text=_success_surface(" updated")
        ),
        _observation(
            sample_id="s000004", elapsed_seconds=2.8, output_text=_success_surface(" updated")
        ),
    ]

    timeline, _events = replay_timeline(
        observations=observations,
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert timeline[1].last_turn_result == "none"
    assert timeline[2].last_turn_result == "none"
    assert timeline[3].last_turn_result == "success"


def test_replay_invalidates_early_settled_success_when_surface_keeps_growing() -> None:
    observations = [
        _observation(sample_id="s000001", elapsed_seconds=0.0, output_text=_active_surface()),
        _observation(
            sample_id="s000002", elapsed_seconds=1.0, output_text=_short_success_surface()
        ),
        _observation(
            sample_id="s000003", elapsed_seconds=2.2, output_text=_short_success_surface()
        ),
        _observation(
            sample_id="s000004",
            elapsed_seconds=2.6,
            output_text=_success_surface(" updated"),
        ),
        _observation(
            sample_id="s000005",
            elapsed_seconds=3.8,
            output_text=_success_surface(" updated"),
        ),
    ]

    timeline, events = replay_timeline(
        observations=observations,
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert timeline[2].last_turn_result == "success"
    assert timeline[3].last_turn_result == "none"
    assert timeline[4].last_turn_result == "success"
    assert any(item.note == "success_invalidated" for item in events)


def test_groundtruth_uses_final_stable_success_surface_when_output_keeps_growing() -> None:
    observations = [
        _observation(sample_id="s000001", elapsed_seconds=0.0, output_text=_active_surface()),
        _observation(
            sample_id="s000002", elapsed_seconds=1.0, output_text=_short_success_surface()
        ),
        _observation(
            sample_id="s000003", elapsed_seconds=2.2, output_text=_short_success_surface()
        ),
        _observation(
            sample_id="s000004",
            elapsed_seconds=2.6,
            output_text=_success_surface(" updated"),
        ),
        _observation(
            sample_id="s000005",
            elapsed_seconds=3.8,
            output_text=_success_surface(" updated"),
        ),
    ]

    timeline = classify_groundtruth(
        observations=observations,
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert timeline[2].last_turn_result == "none"
    assert timeline[3].last_turn_result == "none"
    assert timeline[4].last_turn_result == "success"


def test_groundtruth_drops_early_settled_success_if_final_suffix_never_settles() -> None:
    observations = [
        _observation(sample_id="s000001", elapsed_seconds=0.0, output_text=_active_surface()),
        _observation(
            sample_id="s000002", elapsed_seconds=1.0, output_text=_short_success_surface()
        ),
        _observation(
            sample_id="s000003", elapsed_seconds=2.2, output_text=_short_success_surface()
        ),
        _observation(
            sample_id="s000004",
            elapsed_seconds=2.6,
            output_text=_success_surface(" updated"),
        ),
    ]

    timeline = classify_groundtruth(
        observations=observations,
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert all(item.last_turn_result == "none" for item in timeline)


def test_groundtruth_and_replay_map_process_loss_to_tui_down() -> None:
    runtime = RuntimeObservation(
        ts_utc="2026-03-20T00:00:00+00:00",
        elapsed_seconds=0.0,
        session_exists=True,
        pane_exists=True,
        pane_dead=False,
        pane_pid=1234,
        pane_pid_alive=False,
        supported_process_pid=None,
        supported_process_alive=False,
    )
    observations = [
        _observation(
            sample_id="s000001",
            elapsed_seconds=0.0,
            output_text=_ready_surface(),
            runtime=runtime,
        )
    ]

    groundtruth = classify_groundtruth(
        observations=observations,
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )
    replay, _events = replay_timeline(
        observations=observations,
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )

    assert groundtruth[0].diagnostics_availability == "tui_down"
    assert groundtruth[0].turn_phase == "unknown"
    assert replay[0].diagnostics_availability == "tui_down"
    assert replay[0].turn_phase == "unknown"


def test_compare_timelines_reports_first_divergence() -> None:
    observations = [
        _observation(sample_id="s000001", elapsed_seconds=0.0, output_text=_ready_surface()),
        _observation(sample_id="s000002", elapsed_seconds=1.0, output_text=_active_surface()),
    ]
    groundtruth = classify_groundtruth(
        observations=observations,
        observed_version="2.1.80 (Claude Code)",
        settle_seconds=1.0,
    )
    replay = list(groundtruth)
    replay[1] = replay[1].__class__(
        sample_id=replay[1].sample_id,
        elapsed_seconds=replay[1].elapsed_seconds,
        ts_utc=replay[1].ts_utc,
        diagnostics_availability=replay[1].diagnostics_availability,
        surface_accepting_input=replay[1].surface_accepting_input,
        surface_editing_input=replay[1].surface_editing_input,
        surface_ready_posture=replay[1].surface_ready_posture,
        turn_phase="unknown",
        last_turn_result=replay[1].last_turn_result,
        detector_name=replay[1].detector_name,
        detector_version=replay[1].detector_version,
        active_reasons=replay[1].active_reasons,
        notes=replay[1].notes,
    )

    comparison, markdown = compare_timelines(groundtruth=groundtruth, replay=replay)

    assert comparison.mismatch_count == 1
    assert comparison.first_divergence_sample_id == "s000002"
    assert "turn_phase" in comparison.first_divergence_fields
    assert "s000002" in markdown
