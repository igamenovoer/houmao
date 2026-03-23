"""Unit tests for the dual shadow-watch monitor tracker."""

from __future__ import annotations

from houmao.demo.cao_dual_shadow_watch.models import AgentSessionState, MonitorObservation
from houmao.demo.cao_dual_shadow_watch.monitor import AgentStateTracker


def _session(slot: str = "codex", tool: str = "codex") -> AgentSessionState:
    """Return one minimal persisted session state for tracker tests."""

    return AgentSessionState(
        slot=slot,
        tool=tool,
        blueprint_path=f"/repo/tests/fixtures/agents/blueprints/projection-demo-{tool}.yaml",
        brain_recipe_path=(
            f"/repo/tests/fixtures/agents/brains/brain-recipes/{tool}/projection-demo-default.yaml"
        ),
        role_name="projection-demo",
        workdir=f"/tmp/{slot}",
        brain_home_path=f"/tmp/{slot}/home",
        brain_manifest_path=f"/tmp/{slot}/manifest.json",
        launch_helper_path=f"/tmp/{slot}/launch.sh",
        session_manifest_path=f"/tmp/{slot}/session-manifest.json",
        agent_identity=f"projection-demo-{slot}",
        agent_id=f"AGENTSYS-projection-demo-{slot}",
        tmux_session_name=f"AGENTSYS-projection-demo-{slot}",
        cao_session_name=f"AGENTSYS-projection-demo-{slot}",
        terminal_id=f"term-{slot}",
        parsing_mode="shadow_only",
    )


def _observation(
    *,
    at: float,
    business_state: str,
    input_mode: str,
    projection_text: str = "baseline",
    availability: str = "supported",
    ui_context: str = "normal_prompt",
    baseline_invalidated: bool = False,
    anomaly_codes: tuple[str, ...] = (),
    operator_blocked_excerpt: str | None = None,
) -> MonitorObservation:
    """Return one synthetic monitor observation for tracker tests."""

    return MonitorObservation(
        slot="codex",
        tool="codex",
        terminal_id="term-codex",
        tmux_session_name="AGENTSYS-projection-demo-codex",
        cao_status="idle",
        parser_family="codex_shadow",
        parser_preset_id="codex_shadow_v1",
        parser_preset_version="0.1.0",
        availability=availability,
        business_state=business_state,
        input_mode=input_mode,
        ui_context=ui_context,
        normalized_projection_text=projection_text,
        dialog_tail=projection_text,
        operator_blocked_excerpt=operator_blocked_excerpt,
        anomaly_codes=anomaly_codes,
        baseline_invalidated=baseline_invalidated,
        monotonic_ts=at,
        error_detail=None,
    )


def test_tracker_reports_blocked_surface() -> None:
    """Operator-blocked surfaces should surface as blocked immediately."""

    tracker = AgentStateTracker(
        session=_session(),
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )

    state, _ = tracker.observe(
        _observation(
            at=0.0,
            business_state="awaiting_operator",
            input_mode="modal",
            ui_context="selection_menu",
            operator_blocked_excerpt="Press 1 to continue",
        )
    )

    assert state.readiness_state == "blocked"
    assert state.completion_state == "blocked"


def test_tracker_reaches_completed_after_stability_window() -> None:
    """A ready baseline plus working then stable idle should complete."""

    tracker = AgentStateTracker(
        session=_session(),
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )

    tracker.observe(_observation(at=0.0, business_state="idle", input_mode="freeform"))
    tracker.observe(_observation(at=0.5, business_state="working", input_mode="freeform"))
    candidate_state, _ = tracker.observe(
        _observation(at=1.0, business_state="idle", input_mode="freeform")
    )
    completed_state, _ = tracker.observe(
        _observation(at=2.1, business_state="idle", input_mode="freeform")
    )

    assert candidate_state.completion_state == "candidate_complete"
    assert completed_state.completion_state == "completed"


def test_tracker_projection_change_resets_completion_window() -> None:
    """Projection changes during candidate completion should reset stability timing."""

    tracker = AgentStateTracker(
        session=_session(),
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )

    tracker.observe(_observation(at=0.0, business_state="idle", input_mode="freeform"))
    tracker.observe(_observation(at=0.2, business_state="working", input_mode="modal"))
    tracker.observe(
        _observation(
            at=0.6,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline\nanswer-a",
        )
    )
    reset_candidate_state, _ = tracker.observe(
        _observation(
            at=1.1,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline\nanswer-a\nmore",
        )
    )
    not_done_state, _ = tracker.observe(
        _observation(
            at=1.9,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline\nanswer-a\nmore",
        )
    )
    done_state, _ = tracker.observe(
        _observation(
            at=2.2,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline\nanswer-a\nmore",
        )
    )

    assert reset_candidate_state.completion_state == "candidate_complete"
    assert not_done_state.completion_state == "candidate_complete"
    assert done_state.completion_state == "completed"


def test_tracker_unknown_to_stalled_transition() -> None:
    """Continuous unknown classification should become stalled after the timeout."""

    tracker = AgentStateTracker(
        session=_session(),
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=5.0,
    )

    first_unknown, _ = tracker.observe(
        _observation(at=0.0, business_state="unknown", input_mode="unknown", ui_context="unknown")
    )
    stalled_state, _ = tracker.observe(
        _observation(at=5.1, business_state="unknown", input_mode="unknown", ui_context="unknown")
    )

    assert first_unknown.readiness_state == "unknown"
    assert stalled_state.readiness_state == "stalled"
    assert stalled_state.completion_state == "stalled"
