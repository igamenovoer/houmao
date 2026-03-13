from __future__ import annotations

from houmao.agents.realm_controller.backends.cao_rest import _TurnMonitor
from houmao.agents.realm_controller.backends.shadow_parser_core import (
    DialogProjection,
    ProjectionMetadata,
    ShadowParserMetadata,
    SurfaceAssessment,
)


def _metadata() -> ShadowParserMetadata:
    return ShadowParserMetadata(
        provider_id="claude",
        parser_preset_id="test_shadow",
        parser_preset_version="0.0.0",
        output_format="test_shadow",
        output_variant="test_surface",
        output_format_match=True,
    )


def _surface(
    *,
    availability: str = "supported",
    business_state: str,
    input_mode: str,
    ui_context: str = "normal_prompt",
    operator_blocked_excerpt: str | None = None,
) -> SurfaceAssessment:
    return SurfaceAssessment(
        availability=availability,
        business_state=business_state,
        input_mode=input_mode,
        ui_context=ui_context,
        parser_metadata=_metadata(),
        operator_blocked_excerpt=operator_blocked_excerpt,
    )


def _projection(dialog_text: str) -> DialogProjection:
    metadata = _metadata()
    return DialogProjection(
        raw_text=dialog_text,
        normalized_text=dialog_text,
        dialog_text=dialog_text,
        head=dialog_text,
        tail=dialog_text,
        projection_metadata=ProjectionMetadata(
            provider_id="claude",
            source_kind="tui_snapshot",
            projector_id="test_projection",
            parser_metadata=metadata,
            dialog_line_count=len(dialog_text.splitlines()) if dialog_text else 0,
            head_line_count=len(dialog_text.splitlines()) if dialog_text else 0,
            tail_line_count=len(dialog_text.splitlines()) if dialog_text else 0,
        ),
    )


def test_turn_monitor_readiness_distinguishes_modal_from_operator_blocked() -> None:
    monitor = _TurnMonitor(phase="readiness", m_state="awaiting_ready")

    modal_state = monitor.observe_readiness(
        surface_assessment=_surface(
            business_state="idle",
            input_mode="modal",
            ui_context="slash_command",
        ),
        parser_family="claude_shadow",
        now_monotonic=10.0,
        timeout_seconds=5.0,
    )
    blocked_state = monitor.observe_readiness(
        surface_assessment=_surface(
            business_state="awaiting_operator",
            input_mode="modal",
            ui_context="trust_prompt",
            operator_blocked_excerpt="Allow Claude to work in this folder? [y/n]",
        ),
        parser_family="claude_shadow",
        now_monotonic=11.0,
        timeout_seconds=5.0,
    )

    assert modal_state == "awaiting_ready"
    assert blocked_state == "blocked_operator"


def test_turn_monitor_completion_waits_for_submit_ready_after_working_freeform() -> None:
    monitor = _TurnMonitor(phase="completion", m_state="submitted_waiting_activity")
    monitor.record_submit(baseline_projection=_projection("baseline"))

    in_progress = monitor.observe_completion(
        surface_assessment=_surface(
            business_state="working",
            input_mode="freeform",
        ),
        dialog_projection=_projection("baseline"),
        parser_family="claude_shadow",
        now_monotonic=20.0,
        timeout_seconds=5.0,
    )
    completed = monitor.observe_completion(
        surface_assessment=_surface(
            business_state="idle",
            input_mode="freeform",
        ),
        dialog_projection=_projection("baseline"),
        parser_family="claude_shadow",
        now_monotonic=21.0,
        timeout_seconds=5.0,
    )

    assert in_progress == "in_progress"
    assert completed == "completed"


def test_turn_monitor_completion_keeps_working_modal_in_progress_until_submit_ready() -> None:
    monitor = _TurnMonitor(phase="completion", m_state="submitted_waiting_activity")
    monitor.record_submit(baseline_projection=_projection("baseline"))

    in_progress = monitor.observe_completion(
        surface_assessment=_surface(
            business_state="working",
            input_mode="modal",
            ui_context="slash_command",
        ),
        dialog_projection=_projection("baseline"),
        parser_family="claude_shadow",
        now_monotonic=30.0,
        timeout_seconds=5.0,
    )
    completed = monitor.observe_completion(
        surface_assessment=_surface(
            business_state="idle",
            input_mode="freeform",
        ),
        dialog_projection=_projection("baseline\nfinal answer"),
        parser_family="claude_shadow",
        now_monotonic=31.0,
        timeout_seconds=5.0,
    )

    assert in_progress == "in_progress"
    assert completed == "completed"


def test_turn_monitor_known_business_state_with_unknown_input_mode_stays_non_stalled() -> None:
    monitor = _TurnMonitor(phase="readiness", m_state="awaiting_ready")

    first = monitor.observe_readiness(
        surface_assessment=_surface(
            business_state="idle",
            input_mode="unknown",
            ui_context="unknown",
        ),
        parser_family="claude_shadow",
        now_monotonic=40.0,
        timeout_seconds=1.0,
    )
    second = monitor.observe_readiness(
        surface_assessment=_surface(
            business_state="idle",
            input_mode="unknown",
            ui_context="unknown",
        ),
        parser_family="claude_shadow",
        now_monotonic=42.0,
        timeout_seconds=1.0,
    )

    assert first == "awaiting_ready"
    assert second == "awaiting_ready"
    assert monitor.elapsed_unknown_seconds(now_monotonic=42.0) is None
