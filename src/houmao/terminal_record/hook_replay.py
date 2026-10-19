"""Replay an optional hook-event sidecar through the hook posture reducer.

A recorder run root may carry ``hook_events.ndjson`` with the same envelope
format as the live hook store. This module aligns each envelope with the
recorded snapshot time base, reduces the envelopes through
:mod:`houmao.hook_observation`, and joins the resulting posture with the
TUI-derived observed state to emit one hook observation row per sample.

The replay is intentionally read-only and sidecar-optional: when the sidecar
is absent, callers skip this module entirely and the recorded analysis output
is unchanged.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from houmao.hook_observation import (
    HookEventEnvelope,
    HookPosture,
    HookPostureDiagnostic,
    HookPostureReducer,
    normalize_envelope,
    read_store,
)

from .models import TerminalRecordPaneSnapshot


HOOK_STALENESS_SECONDS = 30.0
_SAMPLE_TIME_TOLERANCE_SECONDS = 2.0


@dataclass(frozen=True)
class HookReplayResult:
    """Per-sample hook observations derived from one sidecar replay."""

    rows: tuple[dict[str, Any], ...]
    envelope_count: int
    consumed_envelope_count: int
    skipped_line_count: int
    skipped_blank_lines: int
    skipped_garbage_lines: int
    skipped_oversized_lines: int
    skipped_invalid_lines: int
    skipped_incomplete_lines: int
    skipped_invalid_timestamp_count: int
    evidence_sample_count: int
    conflict_counts: dict[str, int]
    diagnostic_counts: dict[str, int]

    def summary_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable replay summary."""

        return {
            "envelope_count": self.envelope_count,
            "consumed_envelope_count": self.consumed_envelope_count,
            "skipped_line_count": self.skipped_line_count,
            "skipped_blank_lines": self.skipped_blank_lines,
            "skipped_garbage_lines": self.skipped_garbage_lines,
            "skipped_oversized_lines": self.skipped_oversized_lines,
            "skipped_invalid_lines": self.skipped_invalid_lines,
            "skipped_incomplete_lines": self.skipped_incomplete_lines,
            "skipped_invalid_timestamp_count": self.skipped_invalid_timestamp_count,
            "evidence_sample_count": self.evidence_sample_count,
            "conflict_counts": dict(sorted(self.conflict_counts.items())),
            "diagnostic_counts": dict(sorted(self.diagnostic_counts.items())),
        }


def replay_hook_sidecar(
    *,
    sidecar_path: Path,
    snapshots: Sequence[TerminalRecordPaneSnapshot],
    state_rows: Sequence[Mapping[str, Any]],
    recording_started_at_utc: str | None = None,
) -> HookReplayResult:
    """Reduce one optional hook sidecar against the recorded snapshot stream.

    Envelope times are compared with each snapshot's wall-clock time. When the
    recording start and snapshot ``elapsed_seconds`` agree with ``ts_utc``
    within a small tolerance, the reconstructed start-plus-elapsed time is
    preferred because it recovers sub-second precision that ``ts_utc`` may
    truncate. Envelopes at or before a sample time are reduced before that
    sample's posture is recorded.

    Parameters
    ----------
    sidecar_path:
        Path to ``hook_events.ndjson``. Missing files yield no evidence rows.
    snapshots:
        Recorded snapshots in replay order.
    state_rows:
        TUI-derived observed rows keyed by ``sample_id``.
    recording_started_at_utc:
        Manifest start time used to reconstruct sub-second sample times.

    Returns
    -------
    HookReplayResult
        One observation row per snapshot plus replay counters.
    """

    store = read_store(sidecar_path)
    timestamped = _timestamped_envelopes(store.envelopes)
    skipped_invalid_timestamp_count = len(store.envelopes) - len(timestamped)
    recording_start = _parse_utc(recording_started_at_utc)
    state_by_sample_id = {
        str(row["sample_id"]): row for row in state_rows if isinstance(row.get("sample_id"), str)
    }

    reducer = HookPostureReducer()
    posture = reducer.posture
    cursor = 0
    consumed_envelope_count = 0
    evidence_sample_count = 0
    conflict_counts: Counter[str] = Counter()
    diagnostic_counts: Counter[str] = Counter()
    seen_diagnostics: set[tuple[str, str, str, str | None]] = set()
    previous_conflicts: list[str] = []
    previous_stale = False
    previous_signature: tuple[Any, ...] | None = None
    rows: list[dict[str, Any]] = []

    for snapshot in snapshots:
        sample_time = _snapshot_time(snapshot=snapshot, recording_start=recording_start)
        if sample_time is not None:
            while cursor < len(timestamped) and timestamped[cursor][0] <= sample_time:
                posture = reducer.reduce(normalize_envelope(timestamped[cursor][1]))
                cursor += 1
                consumed_envelope_count += 1
        state_row = state_by_sample_id.get(snapshot.sample_id, {})
        signature = _tui_signature(state_row)
        tui_changed = previous_signature is not None and signature != previous_signature
        stale = _is_stale(
            posture=posture,
            sample_time=sample_time,
            tui_changed=tui_changed,
        )
        diagnostics = _new_diagnostics(posture=posture, seen=seen_diagnostics)
        diagnostic_counts.update(item.kind for item in diagnostics)
        conflicts = _conflict_kinds(
            posture=posture,
            state_row=state_row,
            stale=stale,
            previous_stale=previous_stale,
        )
        conflict_counts.update(conflicts)
        new_conflicts = [item for item in conflicts if item not in previous_conflicts]
        evidence = posture.last_event_name is not None
        if evidence:
            evidence_sample_count += 1
        rows.append(
            _observation_row(
                snapshot=snapshot,
                state_row=state_row,
                posture=posture,
                evidence=evidence,
                stale=stale,
                conflicts=conflicts,
                new_conflicts=new_conflicts,
                diagnostics=diagnostics,
            )
        )
        previous_conflicts = conflicts
        previous_stale = stale
        previous_signature = signature

    return HookReplayResult(
        rows=tuple(rows),
        envelope_count=len(store.envelopes),
        consumed_envelope_count=consumed_envelope_count,
        skipped_line_count=store.skipped_lines,
        skipped_blank_lines=store.skipped_blank_lines,
        skipped_garbage_lines=store.skipped_garbage_lines,
        skipped_oversized_lines=store.skipped_oversized_lines,
        skipped_invalid_lines=store.skipped_invalid_lines,
        skipped_incomplete_lines=store.skipped_incomplete_lines,
        skipped_invalid_timestamp_count=skipped_invalid_timestamp_count,
        evidence_sample_count=evidence_sample_count,
        conflict_counts=dict(conflict_counts),
        diagnostic_counts=dict(diagnostic_counts),
    )


def _timestamped_envelopes(
    envelopes: Sequence[HookEventEnvelope],
) -> list[tuple[datetime, HookEventEnvelope]]:
    """Return envelopes with parsed receive times in arrival-time order."""

    timestamped: list[tuple[datetime, HookEventEnvelope]] = []
    for envelope in envelopes:
        received_at = _parse_utc(envelope.received_at_utc)
        if received_at is None:
            continue
        timestamped.append((received_at, envelope))
    timestamped.sort(key=lambda item: item[0])
    return timestamped


def _snapshot_time(
    *,
    snapshot: TerminalRecordPaneSnapshot,
    recording_start: datetime | None,
) -> datetime | None:
    """Return one snapshot's wall-clock time, preferring sub-second precision."""

    recorded_ts = _parse_utc(snapshot.ts_utc)
    if recording_start is None:
        return recorded_ts
    reconstructed = recording_start + timedelta(seconds=snapshot.elapsed_seconds)
    if recorded_ts is None:
        return reconstructed
    if abs((reconstructed - recorded_ts).total_seconds()) <= _SAMPLE_TIME_TOLERANCE_SECONDS:
        return reconstructed
    return recorded_ts


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


def _tui_signature(state_row: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return the TUI surface/turn fields used to detect live churn."""

    return tuple(
        state_row.get(key)
        for key in (
            "surface_accepting_input",
            "surface_editing_input",
            "surface_ready_posture",
            "surface_pending_input",
            "turn_phase",
            "last_turn_result",
        )
    )


def _is_stale(
    *,
    posture: HookPosture,
    sample_time: datetime | None,
    tui_changed: bool,
) -> bool:
    """Return whether the channel is stale mid-turn while the TUI changes."""

    if not tui_changed or sample_time is None:
        return False
    if posture.turn_phase not in {"active", "blocked"}:
        return False
    last_event_at = _parse_utc(posture.last_event_at_utc)
    if last_event_at is None:
        return False
    return (sample_time - last_event_at).total_seconds() > HOOK_STALENESS_SECONDS


def _new_diagnostics(
    *,
    posture: HookPosture,
    seen: set[tuple[str, str, str, str | None]],
) -> list[HookPostureDiagnostic]:
    """Return reducer diagnostics not observed on an earlier sample."""

    fresh: list[HookPostureDiagnostic] = []
    for diagnostic in posture.diagnostics:
        key = (
            diagnostic.kind,
            diagnostic.event_name,
            diagnostic.received_at_utc,
            diagnostic.detail,
        )
        if key in seen:
            continue
        seen.add(key)
        fresh.append(diagnostic)
    return fresh


def _conflict_kinds(
    *,
    posture: HookPosture,
    state_row: Mapping[str, Any],
    stale: bool,
    previous_stale: bool,
) -> list[str]:
    """Return the merge conflict kinds visible at one sample.

    The vocabulary follows ``design/state-transitions.md`` section 9. TUI
    ``turn_phase`` drives the active side and surface readiness drives the
    ready-looking side, matching the merge rule that hook lifecycle facts hold
    against a false-ready surface.
    """

    conflicts: list[str] = []
    tui_turn_phase = state_row.get("turn_phase")
    tui_ready = tui_turn_phase == "ready" or state_row.get("surface_ready_posture") == "yes"
    if posture.turn_phase == "active" and tui_ready:
        conflicts.append("hook_active_tui_ready")
    if posture.turn_phase == "blocked" and tui_ready:
        conflicts.append("hook_blocked_tui_ready")
    if (
        posture.terminal_result != "none"
        and posture.turn_phase == "ready"
        and tui_turn_phase == "active"
    ):
        conflicts.append("hook_terminal_tui_active")
    if posture.terminal_result == "success" and state_row.get("last_turn_result") == "interrupted":
        conflicts.append("hook_success_tui_interrupted")
    if (
        posture.terminal_result == "known_failure"
        and state_row.get("last_turn_result") == "success"
    ):
        conflicts.append("hook_failure_tui_success")
    if stale:
        conflicts.append("hook_stale_tui_authoritative")
    if previous_stale and not stale and _terminal_disagrees_with_tui(posture, state_row):
        conflicts.append("hook_correction_after_staleness")
    return conflicts


def _terminal_disagrees_with_tui(posture: HookPosture, state_row: Mapping[str, Any]) -> bool:
    """Return whether a recovery terminal corrects an already-settled TUI result."""

    if posture.terminal_result not in {"success", "known_failure"}:
        return False
    tui_result = state_row.get("last_turn_result")
    if not isinstance(tui_result, str):
        return False
    if tui_result not in {"success", "known_failure", "interrupted"}:
        return False
    if posture.terminal_result == "success" and tui_result == "interrupted":
        return False
    return posture.terminal_result != tui_result


def _observation_row(
    *,
    snapshot: TerminalRecordPaneSnapshot,
    state_row: Mapping[str, Any],
    posture: HookPosture,
    evidence: bool,
    stale: bool,
    conflicts: list[str],
    new_conflicts: list[str],
    diagnostics: Sequence[HookPostureDiagnostic],
) -> dict[str, Any]:
    """Build one per-sample hook observation payload."""

    return {
        "sample_id": snapshot.sample_id,
        "elapsed_seconds": snapshot.elapsed_seconds,
        "ts_utc": snapshot.ts_utc,
        "source_sample_id": state_row.get("source_sample_id"),
        "hook_evidence_seen": evidence,
        "hook_generation": posture.generation,
        "hook_session_id": posture.session_id,
        "hook_session_started": posture.session_started,
        "hook_turn_phase": posture.turn_phase,
        "hook_terminal_result": posture.terminal_result,
        "hook_terminal_error_class": posture.terminal_error_class,
        "hook_blocked": posture.blocked,
        "hook_blocked_tool_name": posture.blocked_tool_name,
        "hook_maintenance_active": posture.maintenance_active,
        "hook_work": posture.work,
        "hook_active_prompt_id": posture.active_prompt_id,
        "hook_armed_prompt_count": posture.armed_prompt_count,
        "hook_queued_prompt_count": posture.queued_prompt_count,
        "hook_last_event_name": posture.last_event_name,
        "hook_last_event_kind": posture.last_event_kind,
        "hook_last_event_at_utc": posture.last_event_at_utc,
        "hook_last_sequence": posture.last_sequence,
        "hook_stale": stale,
        "hook_counters": posture.counters.to_payload(),
        "hook_conflicts": list(conflicts),
        "hook_new_conflicts": list(new_conflicts),
        "hook_diagnostics": [item.to_payload() for item in diagnostics],
    }
