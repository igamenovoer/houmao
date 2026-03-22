"""Ground-truth expansion helpers for recorded tracked-TUI fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from houmao.shared_tui_tracking.models import (
    RecordedObservation,
    RuntimeObservation,
    TrackedDiagnosticsAvailability,
    TrackedLastTurnResult,
    TrackedLastTurnSource,
    TrackedTimelineState,
    Tristate,
    TurnPhase,
)
from houmao.terminal_record.models import (
    TerminalRecordPaneSnapshot,
    TerminalRecordPaths,
    load_labels,
)

from .models import load_ndjson


_REQUIRED_EXPECTATION_FIELDS = (
    "diagnostics_availability",
    "surface_accepting_input",
    "surface_editing_input",
    "surface_ready_posture",
    "turn_phase",
    "last_turn_result",
    "last_turn_source",
)


@dataclass(frozen=True)
class FixtureInputs:
    """Resolved replay inputs for one recorded fixture."""

    snapshots: list[TerminalRecordPaneSnapshot]
    observations: list[RecordedObservation]
    runtime_rows: list[RuntimeObservation]


def load_fixture_inputs(
    *,
    recording_root: Path,
    runtime_observations_path: Path | None = None,
) -> FixtureInputs:
    """Load replay inputs from one recording root and optional runtime evidence."""

    snapshots = _load_snapshots(recording_root / "pane_snapshots.ndjson")
    runtime_rows = _load_runtime_observations(runtime_observations_path)
    observations: list[RecordedObservation] = []
    runtime_index = 0
    last_runtime: RuntimeObservation | None = None
    for snapshot in snapshots:
        while (
            runtime_index < len(runtime_rows)
            and runtime_rows[runtime_index].elapsed_seconds <= snapshot.elapsed_seconds
        ):
            last_runtime = runtime_rows[runtime_index]
            runtime_index += 1
        observations.append(
            RecordedObservation(
                sample_id=snapshot.sample_id,
                elapsed_seconds=snapshot.elapsed_seconds,
                ts_utc=snapshot.ts_utc,
                output_text=snapshot.output_text,
                runtime=last_runtime,
            )
        )
    return FixtureInputs(snapshots=snapshots, observations=observations, runtime_rows=runtime_rows)


def expand_labels_to_groundtruth_timeline(
    *,
    recording_root: Path,
    labels_path: Path | None = None,
) -> list[TrackedTimelineState]:
    """Expand structured recorder labels into a per-sample ground-truth timeline."""

    snapshots = _load_snapshots(recording_root / "pane_snapshots.ndjson")
    if not snapshots:
        raise ValueError(f"No pane snapshots found under {recording_root}")
    index_by_sample_id = {item.sample_id: idx for idx, item in enumerate(snapshots)}
    effective_labels_path = (
        labels_path or TerminalRecordPaths.from_run_root(run_root=recording_root).labels_path
    )
    labels = load_labels(effective_labels_path)
    coverage: list[dict[str, Any] | None] = [None for _ in snapshots]

    for label in labels.labels:
        missing_fields = [
            field for field in _REQUIRED_EXPECTATION_FIELDS if field not in label.expectations
        ]
        if missing_fields:
            raise ValueError(
                f"Label `{label.label_id}` is missing required fields: {', '.join(missing_fields)}"
            )
        if label.sample_id not in index_by_sample_id:
            raise ValueError(f"Unknown sample id in label `{label.label_id}`: {label.sample_id}")
        start_index = index_by_sample_id[label.sample_id]
        if label.sample_end_id is None:
            end_index = start_index
        else:
            if label.sample_end_id not in index_by_sample_id:
                raise ValueError(
                    f"Unknown sample end id in label `{label.label_id}`: {label.sample_end_id}"
                )
            end_index = index_by_sample_id[label.sample_end_id]
        if end_index < start_index:
            raise ValueError(
                f"Label `{label.label_id}` sample range is reversed: "
                f"{label.sample_id} -> {label.sample_end_id}"
            )
        for index in range(start_index, end_index + 1):
            if coverage[index] is not None:
                raise ValueError(
                    f"Overlapping labels detected at sample `{snapshots[index].sample_id}`"
                )
            coverage[index] = dict(label.expectations)

    missing_coverage = [
        snapshots[idx].sample_id for idx, item in enumerate(coverage) if item is None
    ]
    if missing_coverage:
        raise ValueError(
            "Ground-truth labels do not cover all samples: " + ", ".join(missing_coverage)
        )

    timeline: list[TrackedTimelineState] = []
    for snapshot, expectations in zip(snapshots, coverage, strict=True):
        assert expectations is not None
        timeline.append(
            TrackedTimelineState(
                sample_id=snapshot.sample_id,
                elapsed_seconds=snapshot.elapsed_seconds,
                ts_utc=snapshot.ts_utc,
                diagnostics_availability=cast(
                    TrackedDiagnosticsAvailability,
                    str(expectations["diagnostics_availability"]),
                ),
                surface_accepting_input=cast(
                    Tristate, str(expectations["surface_accepting_input"])
                ),
                surface_editing_input=cast(Tristate, str(expectations["surface_editing_input"])),
                surface_ready_posture=cast(Tristate, str(expectations["surface_ready_posture"])),
                turn_phase=cast(TurnPhase, str(expectations["turn_phase"])),
                last_turn_result=cast(
                    TrackedLastTurnResult,
                    str(expectations["last_turn_result"]),
                ),
                last_turn_source=cast(
                    TrackedLastTurnSource,
                    str(expectations["last_turn_source"]),
                ),
                detector_name="groundtruth",
                detector_version="labels",
                active_reasons=(),
                notes=(),
            )
        )
    return timeline


def _load_snapshots(path: Path) -> list[TerminalRecordPaneSnapshot]:
    """Load recorder pane snapshots from disk."""

    snapshots: list[TerminalRecordPaneSnapshot] = []
    for payload in load_ndjson(path):
        snapshots.append(
            TerminalRecordPaneSnapshot(
                sample_id=str(payload["sample_id"]),
                elapsed_seconds=float(payload["elapsed_seconds"]),
                ts_utc=str(payload["ts_utc"]),
                target_pane_id=str(payload["target_pane_id"]),
                output_text=str(payload["output_text"]),
            )
        )
    return snapshots


def _load_runtime_observations(path: Path | None) -> list[RuntimeObservation]:
    """Load runtime observations when present."""

    if path is None or not path.is_file():
        return []
    rows: list[RuntimeObservation] = []
    for payload in load_ndjson(path):
        rows.append(RuntimeObservation.from_payload(payload))
    return rows
