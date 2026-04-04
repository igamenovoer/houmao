from __future__ import annotations

import pytest
from reactivex.subject import Subject
from reactivex.testing import TestScheduler

from houmao.agents.realm_controller.backends.cao_rx_monitor import (
    BlockedResult,
    CompletedResult,
    FailedResult,
    ReadyResult,
    ShadowObservation,
    StalledResult,
    build_completion_pipeline,
    build_readiness_pipeline,
)
from houmao.agents.realm_controller.backends.shadow_parser_core import (
    ANOMALY_STALLED_ENTERED,
    ANOMALY_STALLED_RECOVERED,
    DialogProjection,
    ParsedShadowSnapshot,
    ProjectionMetadata,
    ShadowParserMetadata,
    SurfaceAssessment,
)
from houmao.cao.models import CaoTerminalOutputResponse


def _metadata() -> ShadowParserMetadata:
    return ShadowParserMetadata(
        provider_id="codex",
        parser_preset_id="codex_shadow_v1",
        parser_preset_version="0.1.0",
        output_format="codex_shadow_v1",
        output_variant="codex_label_v1",
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


def _projection(text: str) -> DialogProjection:
    metadata = _metadata()
    line_count = len(text.splitlines()) if text else 0
    return DialogProjection(
        raw_text=text,
        normalized_text=text,
        dialog_text=text,
        head=text,
        tail=text,
        projection_metadata=ProjectionMetadata(
            provider_id="codex",
            source_kind="tui_snapshot",
            projector_id="test_projection",
            parser_metadata=metadata,
            dialog_line_count=line_count,
            head_line_count=line_count,
            tail_line_count=line_count,
        ),
    )


def _observation(
    *,
    at: float,
    business_state: str,
    input_mode: str,
    projection_text: str = "baseline",
    raw_output_text: str | None = None,
    availability: str = "supported",
    ui_context: str = "normal_prompt",
    operator_blocked_excerpt: str | None = None,
    parser_family: str = "codex_shadow",
) -> ShadowObservation:
    projection = _projection(projection_text)
    snapshot = ParsedShadowSnapshot(
        surface_assessment=_surface(
            availability=availability,
            business_state=business_state,
            input_mode=input_mode,
            ui_context=ui_context,
            operator_blocked_excerpt=operator_blocked_excerpt,
        ),
        dialog_projection=projection,
    )
    return ShadowObservation(
        output=CaoTerminalOutputResponse(
            output=raw_output_text or projection_text,
            mode="full",
        ),
        snapshot=snapshot,
        projection=projection,
        monotonic_ts=at,
        parser_family=parser_family,
    )


def _emit_observation(
    *,
    scheduler: TestScheduler,
    subject: Subject[ShadowObservation],
    observation: ShadowObservation,
) -> None:
    scheduler.advance_to(observation.monotonic_ts)
    subject.on_next(observation)


def test_readiness_pipeline_distinguishes_modal_from_operator_blocked() -> None:
    scheduler = TestScheduler()
    subject: Subject[ShadowObservation] = Subject()
    results: list[object] = []
    build_readiness_pipeline(
        subject,
        stall_timeout_seconds=5.0,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            business_state="idle",
            input_mode="modal",
            ui_context="slash_command",
        ),
    )
    assert results == []

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=1.0,
            business_state="awaiting_operator",
            input_mode="modal",
            ui_context="trust_prompt",
            operator_blocked_excerpt="Choose an option",
        ),
    )
    assert isinstance(results[-1], BlockedResult)


def test_readiness_pipeline_unknown_to_stalled_transition() -> None:
    scheduler = TestScheduler()
    subject: Subject[ShadowObservation] = Subject()
    results: list[object] = []
    build_readiness_pipeline(
        subject,
        stall_timeout_seconds=5.0,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            business_state="unknown",
            input_mode="unknown",
            ui_context="unknown",
        ),
    )
    scheduler.advance_to(4.9)
    assert results == []

    scheduler.advance_to(5.0)
    assert isinstance(results[-1], StalledResult)
    stalled_result = results[-1]
    assert stalled_result.elapsed_unknown_seconds == pytest.approx(5.0)
    assert stalled_result.anomalies[-1].code == ANOMALY_STALLED_ENTERED


def test_readiness_pipeline_recovers_after_stall() -> None:
    scheduler = TestScheduler()
    subject: Subject[ShadowObservation] = Subject()
    results: list[object] = []
    build_readiness_pipeline(
        subject,
        stall_timeout_seconds=5.0,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            business_state="unknown",
            input_mode="unknown",
            ui_context="unknown",
        ),
    )
    scheduler.advance_to(5.0)
    assert isinstance(results[-1], StalledResult)

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=6.0,
            business_state="idle",
            input_mode="freeform",
            projection_text="ready",
        ),
    )
    assert isinstance(results[-1], ReadyResult)
    anomaly_codes = [anomaly.code for anomaly in results[-1].anomalies]
    assert anomaly_codes == [ANOMALY_STALLED_ENTERED, ANOMALY_STALLED_RECOVERED]


@pytest.mark.parametrize("availability", ["unsupported", "disconnected"])
def test_readiness_pipeline_emits_failed_for_unusable_surfaces(availability: str) -> None:
    scheduler = TestScheduler()
    subject: Subject[ShadowObservation] = Subject()
    results: list[object] = []
    build_readiness_pipeline(
        subject,
        stall_timeout_seconds=5.0,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            availability=availability,
            business_state="idle",
            input_mode="freeform",
        ),
    )
    assert isinstance(results[-1], FailedResult)


def test_readiness_pipeline_emits_ready_for_submit_ready_surface() -> None:
    scheduler = TestScheduler()
    subject: Subject[ShadowObservation] = Subject()
    results: list[object] = []
    build_readiness_pipeline(
        subject,
        stall_timeout_seconds=5.0,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            business_state="idle",
            input_mode="freeform",
            projection_text="ready",
        ),
    )
    assert isinstance(results[-1], ReadyResult)


def test_readiness_pipeline_known_business_state_with_unknown_input_mode_stays_non_stalled() -> (
    None
):
    scheduler = TestScheduler()
    subject: Subject[ShadowObservation] = Subject()
    results: list[object] = []
    build_readiness_pipeline(
        subject,
        stall_timeout_seconds=1.0,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            business_state="idle",
            input_mode="unknown",
            ui_context="unknown",
        ),
    )
    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=2.0,
            business_state="idle",
            input_mode="unknown",
            ui_context="unknown",
        ),
    )
    scheduler.advance_to(10.0)
    assert results == []


def test_readiness_pipeline_stall_timeout_scales_with_inter_emission_gaps() -> None:
    scheduler = TestScheduler()
    subject: Subject[ShadowObservation] = Subject()
    results: list[object] = []
    build_readiness_pipeline(
        subject,
        stall_timeout_seconds=5.0,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            business_state="unknown",
            input_mode="unknown",
            ui_context="unknown",
        ),
    )
    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=4.0,
            business_state="unknown",
            input_mode="unknown",
            ui_context="unknown",
        ),
    )
    scheduler.advance_to(8.9)
    assert results == []

    scheduler.advance_to(9.0)
    assert isinstance(results[-1], StalledResult)
    assert results[-1].elapsed_unknown_seconds == pytest.approx(9.0)


def test_completion_pipeline_transient_idle_flicker_does_not_complete() -> None:
    scheduler = TestScheduler()
    subject: Subject[ShadowObservation] = Subject()
    results: list[object] = []
    build_completion_pipeline(
        subject,
        stability_seconds=2.0,
        stall_timeout_seconds=5.0,
        baseline_projection=_projection("baseline"),
        completion_observer=None,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            business_state="working",
            input_mode="freeform",
            projection_text="baseline",
        ),
    )
    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=1.0,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline",
        ),
    )
    scheduler.advance_to(2.5)
    assert results == []

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=2.5,
            business_state="working",
            input_mode="modal",
            projection_text="baseline",
        ),
    )
    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=3.0,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline",
        ),
    )
    scheduler.advance_to(4.9)
    assert results == []

    scheduler.advance_to(5.0)
    assert isinstance(results[-1], CompletedResult)


def test_completion_pipeline_projection_change_resets_stability_window() -> None:
    scheduler = TestScheduler()
    subject: Subject[ShadowObservation] = Subject()
    results: list[object] = []
    build_completion_pipeline(
        subject,
        stability_seconds=1.0,
        stall_timeout_seconds=5.0,
        baseline_projection=_projection("baseline"),
        completion_observer=None,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            business_state="working",
            input_mode="modal",
            projection_text="baseline",
        ),
    )
    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=1.0,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline\nfirst answer",
        ),
    )
    scheduler.advance_to(1.8)
    assert results == []

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=1.8,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline\nfirst answer\nmore",
        ),
    )
    scheduler.advance_to(2.7)
    assert results == []

    scheduler.advance_to(2.8)
    assert isinstance(results[-1], CompletedResult)


def test_completion_pipeline_waits_for_submit_ready_after_working_freeform() -> None:
    scheduler = TestScheduler()
    subject: Subject[ShadowObservation] = Subject()
    results: list[object] = []
    build_completion_pipeline(
        subject,
        stability_seconds=1.0,
        stall_timeout_seconds=5.0,
        baseline_projection=_projection("baseline"),
        completion_observer=None,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            business_state="working",
            input_mode="freeform",
            projection_text="baseline",
        ),
    )
    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.5,
            business_state="idle",
            input_mode="modal",
            projection_text="baseline",
            ui_context="slash_command",
        ),
    )
    scheduler.advance_to(5.0)
    assert results == []

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=5.0,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline",
        ),
    )
    scheduler.advance_to(5.9)
    assert results == []

    scheduler.advance_to(6.0)
    assert isinstance(results[-1], CompletedResult)


def test_completion_pipeline_mailbox_observer_bypasses_stability_window() -> None:
    scheduler = TestScheduler()
    subject: Subject[ShadowObservation] = Subject()
    results: list[object] = []

    def _observer(
        raw_output_text: str,
        snapshot: ParsedShadowSnapshot,
        baseline_projection: DialogProjection,
    ) -> dict[str, object] | None:
        del snapshot, baseline_projection
        if "HOUMAO_MAIL_RESULT_BEGIN" not in raw_output_text:
            return None
        return {"mail_result_surfaces": [raw_output_text]}

    build_completion_pipeline(
        subject,
        stability_seconds=10.0,
        stall_timeout_seconds=5.0,
        baseline_projection=_projection("baseline"),
        completion_observer=_observer,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            business_state="working",
            input_mode="freeform",
            projection_text="baseline",
            raw_output_text="drafting",
        ),
    )
    assert results == []

    _emit_observation(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=1.0,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline\nsentinel",
            raw_output_text="HOUMAO_MAIL_RESULT_BEGIN\n{}\nHOUMAO_MAIL_RESULT_END",
        ),
    )
    assert isinstance(results[-1], CompletedResult)
    assert results[-1].completion_payload == {
        "mail_result_surfaces": ["HOUMAO_MAIL_RESULT_BEGIN\n{}\nHOUMAO_MAIL_RESULT_END"]
    }
