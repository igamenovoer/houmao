"""Unit tests for the lifecycle execution engine."""

from __future__ import annotations

from tui_pending_state_capture.lifecycle import LifecycleExecutor
from tui_pending_state_capture.models import (
    LifecycleManifest,
    PatternSpec,
    SendKeyStep,
    SendTextStep,
    WaitForPatternAbsentStep,
    WaitForPatternStep,
    WaitSecondsStep,
)
from tui_pending_state_capture.pattern_poller import FakePatternPoller


def _manifest(
    *,
    steps: tuple[object, ...],
    pending_regex: str = "pending",
) -> LifecycleManifest:
    return LifecycleManifest(
        schema_version=1,
        provider="codex",
        calibrated_version="test",
        patterns={
            "ready": PatternSpec(name="ready", regex="ready", description=""),
            "active": PatternSpec(name="active", regex="active", description=""),
            "pending": PatternSpec(name="pending", regex=pending_regex, description=""),
        },
        prompts={"first": "go", "second": "again"},
        steps=steps,
    )


def _repeat(frames: list[str], times: int) -> list[str]:
    """Repeat a frame sequence to survive the per-step confirmation check."""

    result: list[str] = []
    for frame in frames:
        result.extend([frame] * times)
    return result


def test_lifecycle_records_transition_times() -> None:
    poller = FakePatternPoller()
    poller.set_frames(
        _repeat(
            [
                "startup",
                "ready",
                "active first prompt",
                "active second prompt pending",
                "active done",
                "ready",
            ],
            times=10,
        )
    )
    manifest = _manifest(
        steps=(
            WaitSecondsStep(kind="wait_seconds", seconds=0.0),
            WaitForPatternStep(kind="wait_for_pattern", pattern="ready", timeout_seconds=10),
            SendTextStep(kind="send_text", text="go"),
            SendKeyStep(kind="send_key", key="Enter"),
            WaitForPatternStep(kind="wait_for_pattern", pattern="active", timeout_seconds=10),
            SendTextStep(kind="send_text", text="again"),
            SendKeyStep(kind="send_key", key="Enter"),
            WaitForPatternStep(kind="wait_for_pattern", pattern="pending", timeout_seconds=10),
            WaitForPatternAbsentStep(
                kind="wait_for_pattern_absent", pattern="pending", timeout_seconds=10
            ),
            WaitForPatternAbsentStep(
                kind="wait_for_pattern_absent", pattern="active", timeout_seconds=10
            ),
            WaitForPatternStep(kind="wait_for_pattern", pattern="ready", timeout_seconds=10),
        )
    )
    executor = LifecycleExecutor(manifest=manifest, poller=poller, start_monotonic=0.0)
    result = executor.run()

    assert result.success
    assert result.transition_times["active_onset"] is not None
    assert result.transition_times["pending_onset"] is not None
    assert result.transition_times["pending_offset"] is not None
    assert result.transition_times["done_onset"] is not None
    assert result.transition_times["ready_return"] is not None


def test_lifecycle_fails_when_required_pattern_missing() -> None:
    poller = FakePatternPoller()
    poller.set_frames(["startup"] * 50)
    manifest = _manifest(
        steps=(WaitForPatternStep(kind="wait_for_pattern", pattern="ready", timeout_seconds=1),)
    )
    executor = LifecycleExecutor(manifest=manifest, poller=poller, start_monotonic=0.0)
    result = executor.run()

    assert not result.success
    assert result.failure_code == "pattern_timeout:ready"


def test_lifecycle_fails_on_confirmation_violation() -> None:
    poller = FakePatternPoller()
    poller.set_frames(["do you trust this command?"] * 50)
    manifest = _manifest(steps=(WaitSecondsStep(kind="wait_seconds", seconds=0.0),))
    executor = LifecycleExecutor(manifest=manifest, poller=poller, start_monotonic=0.0)
    result = executor.run()

    assert not result.success
    assert result.failure_code == "unattended_confirmation_violation"


def test_lifecycle_uses_pattern_lookup() -> None:
    poller = FakePatternPoller()
    poller.set_frames(["ready"] * 50)
    manifest = _manifest(
        steps=(WaitForPatternStep(kind="wait_for_pattern", pattern="ready", timeout_seconds=1),)
    )
    executor = LifecycleExecutor(manifest=manifest, poller=poller, start_monotonic=0.0)
    result = executor.run()

    assert result.success
    assert result.transition_times["ready_return"] is not None


def test_lifecycle_non_fatal_timeout_continues_and_taints() -> None:
    poller = FakePatternPoller()
    poller.set_frames(
        _repeat(
            [
                "startup",
                "ready",
                "active first prompt",
                "active second prompt pending",
                "active done",
                "ready",
            ],
            times=10,
        )
    )
    manifest = _manifest(
        steps=(
            WaitSecondsStep(kind="wait_seconds", seconds=0.0),
            WaitForPatternStep(kind="wait_for_pattern", pattern="ready", timeout_seconds=10),
            WaitForPatternStep(
                kind="wait_for_pattern",
                pattern="pending",
                timeout_seconds=1,
                non_fatal_on_timeout=True,
            ),
            WaitForPatternStep(kind="wait_for_pattern", pattern="ready", timeout_seconds=10),
        )
    )
    executor = LifecycleExecutor(manifest=manifest, poller=poller, start_monotonic=0.0)
    result = executor.run()

    assert result.success
    assert "pattern_timeout_non_fatal:pending" in result.taint_reasons


def test_lifecycle_required_timeout_still_fails() -> None:
    poller = FakePatternPoller()
    poller.set_frames(["startup"] * 50)
    manifest = _manifest(
        steps=(
            WaitForPatternStep(
                kind="wait_for_pattern",
                pattern="ready",
                timeout_seconds=1,
                non_fatal_on_timeout=False,
            ),
        )
    )
    executor = LifecycleExecutor(manifest=manifest, poller=poller, start_monotonic=0.0)
    result = executor.run()

    assert not result.success
    assert result.failure_code == "pattern_timeout:ready"
    assert result.taint_reasons == ()
