"""Synthesize a plausible hook-event sidecar from recorder labels.

This is a test and qualification utility, not a runtime capture path. It maps
label windows to the two hook events that bracket a turn: ``UserPromptSubmit``
at the first sample of a window whose labeled ``turn_phase`` is ``active`` and
a terminal event at that window's last sample. ``StopFailure`` is used when
the next labeled window records ``last_turn_result=known_failure``; otherwise
``Stop`` is used. A generation boundary and a ``SessionStart`` open the stream.

Envelope timestamps are reconstructed from ``manifest.json``'s start time plus
each snapshot's ``elapsed_seconds`` so synthesized events map to exact sample
ids even when ``ts_utc`` only carries whole-second precision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

from .models import (
    TerminalRecordLabel,
    TerminalRecordPaths,
    load_labels,
    load_manifest,
    overwrite_ndjson,
)


_SAMPLE_TIME_TOLERANCE_SECONDS = 2.0
_GENERATION_BOUNDARY_RANK = 0
_SESSION_START_RANK = 1
_PROMPT_RANK = 2
_TERMINAL_RANK = 3


@dataclass(frozen=True)
class _SnapshotTime:
    """One snapshot's replay sample id and reconstructed event time."""

    sample_id: str
    received_at_utc: str


@dataclass(frozen=True)
class HookSidecarSynthesisResult:
    """Outcome of one label-derived sidecar synthesis."""

    output_path: Path
    envelope_count: int
    event_count: int
    turn_count: int
    skipped_label_count: int
    mappings: tuple[dict[str, Any], ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable synthesis report."""

        return {
            "output_path": str(self.output_path),
            "envelope_count": self.envelope_count,
            "event_count": self.event_count,
            "turn_count": self.turn_count,
            "skipped_label_count": self.skipped_label_count,
            "mappings": [dict(item) for item in self.mappings],
        }


def synthesize_hook_sidecar(
    *,
    run_root: Path,
    labels_path: Path | None = None,
    snapshots_path: Path | None = None,
    output_path: Path | None = None,
) -> HookSidecarSynthesisResult:
    """Write a synthetic ``hook_events.ndjson`` from one run's labels.

    Parameters
    ----------
    run_root:
        Recorder run root that provides default artifact paths.
    labels_path:
        Labels file to read. Defaults to ``<run_root>/labels.json``.
    snapshots_path:
        Snapshot stream that supplies sample ids and elapsed times. Defaults
        to ``<run_root>/pane_snapshots.ndjson``.
    output_path:
        Sidecar destination. Defaults to ``<run_root>/hook_events.ndjson``.

    Returns
    -------
    HookSidecarSynthesisResult
        Written path, counters, and the event-to-sample mapping.
    """

    paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    selected_labels_path = labels_path.resolve() if labels_path is not None else paths.labels_path
    selected_snapshots_path = (
        snapshots_path.resolve() if snapshots_path is not None else paths.pane_snapshots_path
    )
    destination = output_path.resolve() if output_path is not None else paths.hook_events_path
    if not selected_labels_path.is_file():
        raise ValueError(f"Labels file does not exist: {selected_labels_path}")
    if not selected_snapshots_path.is_file():
        raise ValueError(f"Snapshots file does not exist: {selected_snapshots_path}")

    snapshots = _load_snapshot_times(
        snapshots_path=selected_snapshots_path,
        recording_start=_recording_start(paths),
    )
    if not snapshots:
        raise ValueError(f"No snapshots found in `{selected_snapshots_path}`.")
    sample_index = {item.sample_id: index for index, item in enumerate(snapshots)}
    labels = list(load_labels(selected_labels_path).labels)
    ordered = sorted(
        enumerate(labels),
        key=lambda item: (sample_index.get(item[1].sample_id, len(snapshots)), item[0]),
    )

    session_id = f"synthetic:{paths.run_root.name}"
    records: list[tuple[datetime, int, int, dict[str, Any]]] = []
    mappings: list[dict[str, Any]] = []
    skipped_label_count = 0
    if snapshots:
        first_time = _parse_utc(snapshots[0].received_at_utc)
        if first_time is not None:
            records.append(
                (
                    first_time,
                    _GENERATION_BOUNDARY_RANK,
                    -1,
                    {
                        "received_at_utc": snapshots[0].received_at_utc,
                        "channel_generation": 1,
                        "via": "http",
                        "provider_event": {},
                        "record_type": "generation_boundary",
                    },
                )
            )
            records.append(
                (
                    first_time,
                    _SESSION_START_RANK,
                    -1,
                    _event_payload(
                        received_at_utc=snapshots[0].received_at_utc,
                        via="command",
                        provider_event={
                            "hook_event_name": "SessionStart",
                            "session_id": session_id,
                            "source": "startup",
                        },
                    ),
                )
            )

    for position, (original_index, label) in enumerate(ordered):
        if label.expectations.get("turn_phase") != "active":
            continue
        start_index = sample_index.get(label.sample_id)
        end_sample_id = label.sample_end_id or label.sample_id
        end_index = sample_index.get(end_sample_id)
        if start_index is None or end_index is None:
            skipped_label_count += 1
            continue
        if end_index < start_index:
            start_index, end_index = end_index, start_index
        prompt_id = f"synth:{label.label_id}"
        prompt_time = _parse_utc(snapshots[start_index].received_at_utc)
        terminal_time = _parse_utc(snapshots[end_index].received_at_utc)
        if prompt_time is None or terminal_time is None:
            skipped_label_count += 1
            continue
        terminal_event = _terminal_event_name(ordered=ordered, position=position)
        records.append(
            (
                prompt_time,
                _PROMPT_RANK,
                original_index,
                _event_payload(
                    received_at_utc=snapshots[start_index].received_at_utc,
                    via="http",
                    provider_event={
                        "hook_event_name": "UserPromptSubmit",
                        "session_id": session_id,
                        "prompt_id": prompt_id,
                    },
                ),
            )
        )
        terminal_payload: dict[str, Any] = {
            "hook_event_name": terminal_event,
            "session_id": session_id,
            "prompt_id": prompt_id,
            "stop_hook_active": False,
        }
        if terminal_event == "Stop":
            terminal_payload["background_tasks"] = []
        else:
            terminal_payload["error"] = "synthetic_known_failure"
        records.append(
            (
                terminal_time,
                _TERMINAL_RANK,
                original_index,
                _event_payload(
                    received_at_utc=snapshots[end_index].received_at_utc,
                    via="http",
                    provider_event=terminal_payload,
                ),
            )
        )
        mappings.append(
            {
                "label_id": label.label_id,
                "prompt_sample_id": label.sample_id,
                "terminal_sample_id": end_sample_id,
                "prompt_received_at_utc": snapshots[start_index].received_at_utc,
                "terminal_received_at_utc": snapshots[end_index].received_at_utc,
                "terminal_event": terminal_event,
                "prompt_id": prompt_id,
            }
        )

    records.sort(key=lambda item: (item[0], item[1], item[2]))
    payloads: list[dict[str, Any]] = []
    sequence = 0
    for _received_at, _rank, _order, payload in records:
        if payload.get("record_type") == "generation_boundary":
            payload["sequence"] = None
        else:
            sequence += 1
            payload["sequence"] = sequence
        payloads.append(payload)
    overwrite_ndjson(destination, payloads)
    return HookSidecarSynthesisResult(
        output_path=destination,
        envelope_count=len(payloads),
        event_count=sequence,
        turn_count=len(mappings),
        skipped_label_count=skipped_label_count,
        mappings=tuple(mappings),
    )


def _load_snapshot_times(
    *,
    snapshots_path: Path,
    recording_start: datetime | None,
) -> list[_SnapshotTime]:
    """Load snapshot sample ids with reconstructed sub-second event times."""

    snapshots: list[_SnapshotTime] = []
    with snapshots_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            sample_id = str(payload["sample_id"])
            elapsed_seconds = float(payload["elapsed_seconds"])
            recorded_ts = _parse_utc(str(payload.get("ts_utc", "")))
            event_time = recorded_ts
            if recording_start is not None:
                reconstructed = recording_start + timedelta(seconds=elapsed_seconds)
                if recorded_ts is None:
                    event_time = reconstructed
                elif (
                    abs((reconstructed - recorded_ts).total_seconds())
                    <= _SAMPLE_TIME_TOLERANCE_SECONDS
                ):
                    event_time = reconstructed
            if event_time is None:
                raise ValueError(f"Snapshot `{sample_id}` has no parseable timestamp")
            snapshots.append(
                _SnapshotTime(
                    sample_id=sample_id,
                    received_at_utc=event_time.isoformat(timespec="microseconds"),
                )
            )
    return snapshots


def _recording_start(paths: TerminalRecordPaths) -> datetime | None:
    """Return the manifest start time when the manifest is readable."""

    try:
        manifest = load_manifest(paths.manifest_path)
    except (FileNotFoundError, ValueError):
        return None
    return _parse_utc(manifest.started_at_utc)


def _terminal_event_name(
    *,
    ordered: Sequence[tuple[int, TerminalRecordLabel]],
    position: int,
) -> str:
    """Return the terminal event implied by the next labeled window."""

    if position + 1 >= len(ordered):
        return "Stop"
    next_label = ordered[position + 1][1]
    if next_label.expectations.get("last_turn_result") == "known_failure":
        return "StopFailure"
    return "Stop"


def _event_payload(
    *,
    received_at_utc: str,
    via: str,
    provider_event: dict[str, Any],
) -> dict[str, Any]:
    """Build one event envelope payload without a sequence stamp."""

    return {
        "received_at_utc": received_at_utc,
        "channel_generation": 1,
        "via": via,
        "provider_event": provider_event,
    }


def _parse_utc(value: str | None) -> datetime | None:
    """Parse one ISO-8601 timestamp into an aware UTC datetime."""

    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


__all__ = ["HookSidecarSynthesisResult", "synthesize_hook_sidecar"]
