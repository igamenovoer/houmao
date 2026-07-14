"""Automated binary labeling from frozen pane snapshots."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, cast

from houmao.terminal_record.models import TerminalRecordPaneSnapshot  # type: ignore[import-untyped]

from .models import (
    LabelRow,
    LabelSummary,
    LifecycleManifest,
    PendingCountLabel,
    PendingCountPatterns,
    SpanSummary,
    TristateLabel,
)
from .pattern_poller import strip_ansi


def analyze_snapshots(
    *,
    manifest: LifecycleManifest,
    snapshots: tuple[TerminalRecordPaneSnapshot, ...],
) -> tuple[dict[str, LabelRow], LabelSummary]:
    """Assign binary labels and a pending-count estimate to every source snapshot."""

    compiled = {name: spec.compile() for name, spec in manifest.patterns.items()}
    count_extractor = _build_count_extractor(manifest.pending_count_patterns)
    labels: dict[str, LabelRow] = {}
    spans: list[SpanSummary] = []
    counts: dict[str, int] = {
        "can_accept_input_yes": 0,
        "can_accept_input_no": 0,
        "can_accept_input_unknown": 0,
        "has_pending_message_yes": 0,
        "has_pending_message_no": 0,
        "has_pending_message_unknown": 0,
        "pending_count_0": 0,
        "pending_count_1": 0,
        "pending_count_2": 0,
        "pending_count_3": 0,
        "pending_count_unknown": 0,
    }

    current_span: SpanSummary | None = None

    for snapshot in snapshots:
        plain_text = _visible_plain_text(snapshot)
        matched = {name: bool(pattern.search(plain_text)) for name, pattern in compiled.items()}
        label = _decide_label(matched, count_extractor, plain_text)
        labels[snapshot.sample_id] = label

        counts[f"can_accept_input_{label.can_accept_input}"] += 1
        counts[f"has_pending_message_{label.has_pending_message}"] += 1
        counts[f"pending_count_{label.pending_count}"] += 1

        if (
            current_span is None
            or current_span.can_accept_input != label.can_accept_input
            or current_span.has_pending_message != label.has_pending_message
            or current_span.pending_count != label.pending_count
        ):
            if current_span is not None:
                spans.append(current_span)
            current_span = SpanSummary(
                can_accept_input=label.can_accept_input,
                has_pending_message=label.has_pending_message,
                pending_count=label.pending_count,
                first_sample_id=snapshot.sample_id,
                last_sample_id=snapshot.sample_id,
                sample_count=1,
                start_elapsed_seconds=snapshot.elapsed_seconds,
                end_elapsed_seconds=snapshot.elapsed_seconds,
            )
        else:
            current_span = SpanSummary(
                can_accept_input=current_span.can_accept_input,
                has_pending_message=current_span.has_pending_message,
                pending_count=current_span.pending_count,
                first_sample_id=current_span.first_sample_id,
                last_sample_id=snapshot.sample_id,
                sample_count=current_span.sample_count + 1,
                start_elapsed_seconds=current_span.start_elapsed_seconds,
                end_elapsed_seconds=snapshot.elapsed_seconds,
            )

    if current_span is not None:
        spans.append(current_span)

    summary = LabelSummary(
        schema_version=1,
        provider=manifest.provider,
        calibrated_version=manifest.calibrated_version,
        total_samples=len(snapshots),
        counts=counts,
        spans=tuple(spans),
    )
    return labels, summary


def _visible_plain_text(snapshot: TerminalRecordPaneSnapshot) -> str:
    """Return ANSI-stripped text for the currently visible screen lines only.

    The recorder persists the full scrollback (`tmux capture-pane -S -`), so
    labels must restrict pattern matching to the last `target_pane_height`
    screen lines to avoid stale history false matches.
    """

    lines = snapshot.output_text.splitlines()
    height = snapshot.target_pane_height
    if height is not None and height > 0 and len(lines) > height:
        lines = lines[-height:]
    return strip_ansi("\n".join(lines))


def _decide_label(
    matched: dict[str, bool],
    count_extractor: Callable[[str], PendingCountLabel],
    plain_text: str,
) -> LabelRow:
    """Map pattern-match booleans to one binary label row with queue-depth estimate."""

    pending = matched.get("pending", False)
    active = matched.get("active", False)
    ready = matched.get("ready", False)

    evidence = [name for name, value in matched.items() if value]
    note = f"matched: {', '.join(evidence)}" if evidence else "no pattern matched"

    if pending:
        count = count_extractor(plain_text)
        if count == "unknown":
            note += "; count unknown"
        else:
            note += f"; counted {count} pending markers"
        return LabelRow(
            can_accept_input="no",
            has_pending_message="yes",
            pending_count=count,
            evidence_note=note,
        )

    if active:
        return LabelRow(
            can_accept_input="no",
            has_pending_message="no",
            pending_count=0,
            evidence_note=note,
        )

    if ready:
        return LabelRow(
            can_accept_input="yes",
            has_pending_message="no",
            pending_count=0,
            evidence_note=note,
        )

    return LabelRow(
        can_accept_input="unknown",
        has_pending_message="unknown",
        pending_count="unknown",
        evidence_note=note,
    )


def _build_count_extractor(
    patterns: PendingCountPatterns | None,
) -> Callable[[str], PendingCountLabel]:
    """Return a function that estimates pending count from visible pane text."""

    if patterns is None:
        return lambda _text: "unknown"

    if patterns.extractor == "regex_group" and patterns.regex:
        compiled = re.compile(patterns.regex, re.IGNORECASE)
        group_index = patterns.group_index

        def _regex_count(text: str) -> PendingCountLabel:
            match = compiled.search(text)
            if not match:
                return "unknown"
            try:
                value = int(match.group(group_index))
            except (ValueError, IndexError):
                return "unknown"
            if 0 <= value <= 3:
                return cast(PendingCountLabel, value)
            return "unknown"

        return _regex_count

    if patterns.extractor == "count_markers" and patterns.marker_regex:
        compiled = re.compile(patterns.marker_regex, re.MULTILINE | re.IGNORECASE)

        def _marker_count(text: str) -> PendingCountLabel:
            count = len(compiled.findall(text))
            if 0 <= count <= 3:
                return cast(PendingCountLabel, count)
            return "unknown"

        return _marker_count

    return lambda _text: "unknown"


def load_snapshots(path: Path) -> tuple[TerminalRecordPaneSnapshot, ...]:
    """Load source pane snapshots from one NDJSON file."""

    snapshots: list[TerminalRecordPaneSnapshot] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            snapshots.append(
                TerminalRecordPaneSnapshot(
                    sample_id=str(payload["sample_id"]),
                    elapsed_seconds=float(payload["elapsed_seconds"]),
                    ts_utc=str(payload["ts_utc"]),
                    target_pane_id=str(payload["target_pane_id"]),
                    output_text=str(payload["output_text"]),
                    target_pane_width=payload.get("target_pane_width"),
                    target_pane_height=payload.get("target_pane_height"),
                    capture_command=payload.get("capture_command", "tmux capture-pane -p -e -S -"),
                    stream_kind=payload.get("stream_kind", "source"),
                    source_sample_id=payload.get("source_sample_id"),
                    source_elapsed_seconds=payload.get("source_elapsed_seconds"),
                    output_text_sha256=payload.get("output_text_sha256"),
                )
            )
    return tuple(snapshots)


@dataclass(frozen=True)
class LabelsFile:
    """On-disk binary label template."""

    schema_version: int
    provider: str
    calibrated_version: str
    labels: dict[str, LabelRow]

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider": self.provider,
            "calibrated_version": self.calibrated_version,
            "labels": {
                sample_id: {
                    "can_accept_input": row.can_accept_input,
                    "has_pending_message": row.has_pending_message,
                    "pending_count": row.pending_count,
                    "evidence_note": row.evidence_note,
                }
                for sample_id, row in self.labels.items()
            },
        }


def load_labels_file(path: Path) -> dict[str, LabelRow]:
    """Load a binary label template and return rows keyed by sample id."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    labels: dict[str, LabelRow] = {}
    for sample_id, row in payload.get("labels", {}).items():
        labels[str(sample_id)] = LabelRow(
            can_accept_input=cast(TristateLabel, row["can_accept_input"]),
            has_pending_message=cast(TristateLabel, row["has_pending_message"]),
            pending_count=cast(PendingCountLabel, row.get("pending_count", "unknown")),
            evidence_note=str(row["evidence_note"]),
        )
    return labels


def save_labels_file(
    *,
    path: Path,
    manifest: LifecycleManifest,
    labels: dict[str, LabelRow],
) -> None:
    """Persist the binary label template."""

    payload = LabelsFile(
        schema_version=1,
        provider=manifest.provider,
        calibrated_version=manifest.calibrated_version,
        labels=labels,
    ).to_payload()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def save_label_summary(*, path: Path, summary: LabelSummary) -> None:
    """Persist the label summary as JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": summary.schema_version,
                "provider": summary.provider,
                "calibrated_version": summary.calibrated_version,
                "total_samples": summary.total_samples,
                "counts": summary.counts,
                "spans": [asdict(span) for span in summary.spans],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
