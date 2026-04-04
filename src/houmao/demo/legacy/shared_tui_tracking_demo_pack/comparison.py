"""Timeline comparison helpers for the tracked-TUI demo pack."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from houmao.shared_tui_tracking.models import TrackedTimelineState


@dataclass(frozen=True)
class TimelineComparison:
    """Comparison summary for ground truth versus replay timelines."""

    sample_count: int
    mismatch_count: int
    first_divergence_sample_id: str | None
    first_divergence_fields: tuple[str, ...]
    transition_order_matches: bool
    false_positive_terminal_samples: tuple[str, ...]
    diagnostics_mismatch_samples: tuple[str, ...]
    mismatched_samples: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


def compare_timelines(
    *,
    groundtruth: list[TrackedTimelineState],
    replay: list[TrackedTimelineState],
) -> tuple[TimelineComparison, str]:
    """Compare two sample-aligned timelines and return JSON/Markdown outputs."""

    if len(groundtruth) != len(replay):
        raise ValueError("groundtruth and replay timelines must have equal sample counts")

    mismatched_samples: list[str] = []
    diagnostics_mismatch_samples: list[str] = []
    false_positive_terminal_samples: list[str] = []
    first_divergence_sample_id: str | None = None
    first_divergence_fields: tuple[str, ...] = ()

    for ground_item, replay_item in zip(groundtruth, replay, strict=True):
        differing_fields = _differing_fields(ground_item=ground_item, replay_item=replay_item)
        if differing_fields:
            mismatched_samples.append(ground_item.sample_id)
            if first_divergence_sample_id is None:
                first_divergence_sample_id = ground_item.sample_id
                first_divergence_fields = tuple(differing_fields)
        if ground_item.diagnostics_availability != replay_item.diagnostics_availability:
            diagnostics_mismatch_samples.append(ground_item.sample_id)
        if (
            replay_item.last_turn_result != "none"
            and replay_item.last_turn_result != ground_item.last_turn_result
        ):
            false_positive_terminal_samples.append(ground_item.sample_id)

    comparison = TimelineComparison(
        sample_count=len(groundtruth),
        mismatch_count=len(mismatched_samples),
        first_divergence_sample_id=first_divergence_sample_id,
        first_divergence_fields=first_divergence_fields,
        transition_order_matches=_transition_sequence(groundtruth) == _transition_sequence(replay),
        false_positive_terminal_samples=tuple(false_positive_terminal_samples),
        diagnostics_mismatch_samples=tuple(diagnostics_mismatch_samples),
        mismatched_samples=tuple(mismatched_samples),
    )
    return comparison, _comparison_markdown(comparison=comparison)


def _differing_fields(
    *,
    ground_item: TrackedTimelineState,
    replay_item: TrackedTimelineState,
) -> list[str]:
    """Return public-state fields whose values differ."""

    fields: list[str] = []
    if ground_item.diagnostics_availability != replay_item.diagnostics_availability:
        fields.append("diagnostics_availability")
    if ground_item.surface_accepting_input != replay_item.surface_accepting_input:
        fields.append("surface_accepting_input")
    if ground_item.surface_editing_input != replay_item.surface_editing_input:
        fields.append("surface_editing_input")
    if ground_item.surface_ready_posture != replay_item.surface_ready_posture:
        fields.append("surface_ready_posture")
    if ground_item.turn_phase != replay_item.turn_phase:
        fields.append("turn_phase")
    if ground_item.last_turn_result != replay_item.last_turn_result:
        fields.append("last_turn_result")
    if ground_item.last_turn_source != replay_item.last_turn_source:
        fields.append("last_turn_source")
    return fields


def _transition_sequence(
    timeline: list[TrackedTimelineState],
) -> list[tuple[str, str, str, str, str, str, str]]:
    """Return ordered public-state transitions for one timeline."""

    transitions: list[tuple[str, str, str, str, str, str, str]] = []
    previous: tuple[str, str, str, str, str, str, str] | None = None
    for item in timeline:
        current = (
            item.diagnostics_availability,
            item.surface_accepting_input,
            item.surface_editing_input,
            item.surface_ready_posture,
            item.turn_phase,
            item.last_turn_result,
            item.last_turn_source,
        )
        if current != previous:
            transitions.append(current)
            previous = current
    return transitions


def _comparison_markdown(*, comparison: TimelineComparison) -> str:
    """Render one compact Markdown comparison summary."""

    lines = [
        "# Shared TUI Tracking Comparison",
        "",
        f"- Sample count: `{comparison.sample_count}`",
        f"- Mismatch count: `{comparison.mismatch_count}`",
        f"- Transition order matches: `{comparison.transition_order_matches}`",
        f"- First divergence sample: `{comparison.first_divergence_sample_id}`",
        f"- First divergence fields: `{', '.join(comparison.first_divergence_fields) or 'none'}`",
        f"- False-positive terminal samples: `{', '.join(comparison.false_positive_terminal_samples) or 'none'}`",
        f"- Diagnostics mismatch samples: `{', '.join(comparison.diagnostics_mismatch_samples) or 'none'}`",
    ]
    return "\n".join(lines) + "\n"
