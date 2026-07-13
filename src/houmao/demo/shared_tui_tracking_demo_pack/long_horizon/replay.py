"""Deterministic multi-cadence replay for completed long-horizon labels."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, cast

from houmao.demo.shared_tui_tracking_demo_pack.comparison import compare_timelines
from houmao.demo.shared_tui_tracking_demo_pack.groundtruth import (
    expand_labels_to_groundtruth_timeline,
    load_fixture_inputs,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.attempts import (
    load_attempt_state,
    transition_attempt,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.labeling import (
    validate_label_completion,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.models import ProviderName
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.paths import (
    load_json_object,
    save_json_atomic,
)
from houmao.demo.shared_tui_tracking_demo_pack.models import load_input_events
from houmao.shared_tui_tracking.models import RecordedObservation, TrackedTimelineState
from houmao.shared_tui_tracking.reducer import replay_timeline
from houmao.terminal_record.models import overwrite_ndjson
from houmao.terminal_record.schedules import (
    DerivedScheduleSample,
    SamplingMode,
    ScheduleSourceSample,
    derive_sample_schedule,
)


@dataclass(frozen=True)
class ReplaySchedule:
    """One required fixed or irregular capture-delay schedule."""

    name: str
    interval_seconds: float | None
    sampling_mode: SamplingMode
    phase_offset_seconds: float
    seed: int


def required_replay_schedules() -> tuple[ReplaySchedule, ...]:
    """Return canonical, fixed-rate phase, and deterministic irregular schedules."""

    schedules = [ReplaySchedule("canonical", None, "regular", 0.0, 0)]
    for hz in (10, 5, 2):
        interval = 1.0 / hz
        schedules.extend(
            (
                ReplaySchedule(f"fixed-{hz}hz-phase-zero", interval, "regular", 0.0, 0),
                ReplaySchedule(f"fixed-{hz}hz-phase-half", interval, "regular", interval / 2.0, 0),
            )
        )
    schedules.extend(
        (
            ReplaySchedule("jitter-seed-1729", 0.2, "jittered", 0.0, 1729),
            ReplaySchedule("isolated-gaps", 0.2, "gapped", 0.0, 0),
            ReplaySchedule("uc02-bursts", 0.2, "bursty", 0.0, 0),
        )
    )
    return tuple(schedules)


def replay_attempt(
    *,
    attempt_root: Path,
    provider: ProviderName,
    settle_seconds: float = 1.0,
) -> dict[str, Any]:
    """Replay one frozen labeled attempt under every required schedule."""

    validate_label_completion(attempt_root=attempt_root)
    state = load_attempt_state(attempt_root=attempt_root)
    if state.phase == "labels_complete":
        transition_attempt(
            attempt_root=attempt_root,
            expected_phase="labels_complete",
            new_phase="replaying",
        )
    elif state.phase != "replaying":
        raise ValueError(f"Replay requires labels_complete or replaying, got {state.phase}")

    recording_root = attempt_root / "recording" / "terminal-record"
    fixture = load_fixture_inputs(
        recording_root=recording_root,
        runtime_observations_path=attempt_root / "runtime" / "runtime-observations.ndjson",
    )
    groundtruth = expand_labels_to_groundtruth_timeline(
        recording_root=recording_root,
        labels_path=attempt_root / "labels" / "labels.json",
    )
    input_events = load_input_events(recording_root / "input_events.ndjson")
    launch_manifest = load_json_object(attempt_root / "runtime" / "provider-launch-manifest.json")
    observed_version = str(launch_manifest.get("observed_version", "")) or None
    schedule_results: list[dict[str, Any]] = []
    for schedule in required_replay_schedules():
        schedule_dir = attempt_root / "replay" / "schedules" / schedule.name
        schedule_dir.mkdir(parents=True, exist_ok=True)
        mappings = _derive_mappings(schedule=schedule, observations=fixture.observations)
        observations, expected = _apply_mappings(
            mappings=mappings,
            source_observations=fixture.observations,
            source_groundtruth=groundtruth,
        )
        replay, events = replay_timeline(
            observations=observations,
            tool=provider,
            observed_version=observed_version,
            settle_seconds=settle_seconds,
            input_events=input_events,
        )
        comparison, comparison_markdown = compare_timelines(
            groundtruth=expected,
            replay=replay,
        )
        invariants = _evaluate_safety_oracles(expected=expected, replay=replay)
        strict_required = schedule.name == "canonical"
        status = (
            "pass"
            if (not strict_required or comparison.mismatch_count == 0)
            and all(item["status"] == "pass" for item in invariants)
            else "fail"
        )
        overwrite_ndjson(
            schedule_dir / "source-mapping.ndjson", [item.to_payload() for item in mappings]
        )
        overwrite_ndjson(
            schedule_dir / "groundtruth.ndjson", [item.to_payload() for item in expected]
        )
        overwrite_ndjson(
            schedule_dir / "tracker-timeline.ndjson", [item.to_payload() for item in replay]
        )
        overwrite_ndjson(
            schedule_dir / "tracker-events.ndjson", [item.to_payload() for item in events]
        )
        (schedule_dir / "comparison.md").write_text(comparison_markdown, encoding="utf-8")
        result = {
            "schema_version": 1,
            "schedule": asdict(schedule),
            "status": status,
            "strict_canonical": strict_required,
            "comparison": comparison.to_payload(),
            "invariants": invariants,
            "source_sample_count": len(fixture.observations),
            "replay_sample_count": len(replay),
        }
        save_json_atomic(schedule_dir / "result.json", result)
        _write_failure_slice(
            schedule_dir=schedule_dir,
            mappings=mappings,
            comparison_payload=comparison.to_payload(),
            invariants=invariants,
        )
        schedule_results.append(result)

    fixed_safe = all(
        item["status"] == "pass"
        for item in schedule_results
        if str(cast(dict[str, Any], item["schedule"])["name"]).startswith("fixed-")
    )
    canonical = next(item for item in schedule_results if item["schedule"]["name"] == "canonical")
    tracker_verdict = {
        "schema_version": 1,
        "status": "pass" if canonical["status"] == "pass" and fixed_safe else "fail",
        "code": (
            "tracker_qualified"
            if canonical["status"] == "pass" and fixed_safe
            else "tracker_not_qualified"
        ),
        "provider": provider,
        "canonical_status": canonical["status"],
        "fixed_rate_safe": fixed_safe,
        "schedule_count": len(schedule_results),
        "schedules": schedule_results,
    }
    save_json_atomic(attempt_root / "replay" / "tracker-verdict.json", tracker_verdict)
    transition_attempt(
        attempt_root=attempt_root,
        expected_phase="replaying",
        new_phase="reported",
    )
    return tracker_verdict


def _derive_mappings(
    *, schedule: ReplaySchedule, observations: list[RecordedObservation]
) -> tuple[DerivedScheduleSample, ...]:
    """Derive source mappings, preserving the canonical stream exactly."""

    if schedule.interval_seconds is None:
        return tuple(
            DerivedScheduleSample(
                derived_sample_id=item.sample_id,
                target_elapsed_seconds=item.elapsed_seconds,
                source_sample_id=item.sample_id,
                source_elapsed_seconds=item.elapsed_seconds,
            )
            for item in observations
        )
    return derive_sample_schedule(
        samples=tuple(
            ScheduleSourceSample(item.sample_id, item.elapsed_seconds) for item in observations
        ),
        interval_seconds=schedule.interval_seconds,
        sampling_mode=schedule.sampling_mode,
        phase_offset_seconds=schedule.phase_offset_seconds,
        seed=schedule.seed,
    )


def _apply_mappings(
    *,
    mappings: tuple[DerivedScheduleSample, ...],
    source_observations: list[RecordedObservation],
    source_groundtruth: list[TrackedTimelineState],
) -> tuple[list[RecordedObservation], list[TrackedTimelineState]]:
    """Build aligned observations and expected states from source mappings."""

    observations_by_id = {item.sample_id: item for item in source_observations}
    truth_by_id = {item.sample_id: item for item in source_groundtruth}
    observations: list[RecordedObservation] = []
    expected: list[TrackedTimelineState] = []
    for mapping in mappings:
        source_observation = observations_by_id[mapping.source_sample_id]
        source_truth = truth_by_id[mapping.source_sample_id]
        observations.append(
            replace(
                source_observation,
                sample_id=mapping.derived_sample_id,
                elapsed_seconds=mapping.target_elapsed_seconds,
            )
        )
        expected.append(
            replace(
                source_truth,
                sample_id=mapping.derived_sample_id,
                elapsed_seconds=mapping.target_elapsed_seconds,
            )
        )
    return observations, expected


def _evaluate_safety_oracles(
    *, expected: list[TrackedTimelineState], replay: list[TrackedTimelineState]
) -> list[dict[str, Any]]:
    """Evaluate delayed-cadence invariants that tolerate omitted transient states."""

    false_terminal = [
        observed.sample_id
        for truth, observed in zip(expected, replay, strict=True)
        if truth.last_turn_result == "none" and observed.last_turn_result != "none"
    ]
    nonmonotonic = [
        replay[index].sample_id
        for index in range(1, len(replay))
        if replay[index].elapsed_seconds < replay[index - 1].elapsed_seconds
    ]
    liveness = [
        observed.sample_id
        for truth, observed in zip(expected, replay, strict=True)
        if truth.diagnostics_availability == "tui_down"
        and observed.diagnostics_availability != "tui_down"
    ]
    terminal_before_active: list[str] = []
    active_seen = False
    prior_result = "none"
    for item in replay:
        if item.turn_phase == "active":
            active_seen = True
        if item.last_turn_result != "none" and prior_result == "none" and not active_seen:
            terminal_before_active.append(item.sample_id)
        if item.last_turn_result != "none":
            active_seen = False
        prior_result = item.last_turn_result
    return [
        _oracle("no_terminal_fabrication", false_terminal),
        _oracle("monotonic_transition_time", nonmonotonic),
        _oracle("liveness_loss_propagates", liveness),
        _oracle("active_precedes_terminal", terminal_before_active),
    ]


def _oracle(name: str, failures: list[str]) -> dict[str, Any]:
    """Return one invariant payload."""

    return {"name": name, "status": "pass" if not failures else "fail", "samples": failures}


def _write_failure_slice(
    *,
    schedule_dir: Path,
    mappings: tuple[DerivedScheduleSample, ...],
    comparison_payload: dict[str, Any],
    invariants: list[dict[str, Any]],
) -> None:
    """Persist a compact source-mapped slice around the first failure."""

    first_id = comparison_payload.get("first_divergence_sample_id")
    if first_id is None:
        first_id = next(
            (
                sample
                for invariant in invariants
                for sample in cast(list[str], invariant["samples"])
            ),
            None,
        )
    if first_id is None:
        return
    index = next(
        (idx for idx, item in enumerate(mappings) if item.derived_sample_id == first_id),
        0,
    )
    selected = mappings[max(0, index - 2) : index + 3]
    save_json_atomic(
        schedule_dir / "failure-slice.json",
        {
            "schema_version": 1,
            "first_failure_sample_id": first_id,
            "source_mappings": [item.to_payload() for item in selected],
        },
    )
