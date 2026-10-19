"""Tests for the optional hook-event sidecar and its recorded replay."""

from __future__ import annotations

import gzip
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from houmao.terminal_record.hook_replay import replay_hook_sidecar
from houmao.terminal_record.hook_sidecar import synthesize_hook_sidecar
from houmao.terminal_record.models import (
    TERMINAL_RECORD_SCHEMA_VERSION,
    TerminalRecordManifest,
    TerminalRecordPaneSnapshot,
    TerminalRecordPaths,
    TerminalRecordTarget,
    save_manifest,
)
from houmao.terminal_record.service import analyze_terminal_record


_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "shared_tui_tracking"
    / "claude"
    / "qualification"
)
_SESSION1_FIXTURE = _FIXTURE_ROOT / "session1_lifecycle"
_BASELINE_PARSER_SHA256 = "399423dfc48bf7359a85664925c5f228866e6d7ff5895d2d8ad9f0907a991e50"
_BASELINE_STATE_SHA256 = "243c877a9fed38e9261cb8af2795e78a1ad6af99b17dc6a98fcd6693b00caaa1"


def _materialize_session1_fixture(*, tmp_path: Path) -> Path:
    """Unpack the session1 Claude fixture into a recorder run root."""

    run_root = tmp_path / _SESSION1_FIXTURE.name
    run_root.mkdir()
    shutil.copy(_SESSION1_FIXTURE / "manifest.json", run_root / "manifest.json")
    shutil.copy(_SESSION1_FIXTURE / "input_events.ndjson", run_root / "input_events.ndjson")
    with (
        gzip.open(_SESSION1_FIXTURE / "pane_snapshots.ndjson.gz", "rb") as source,
        (run_root / "pane_snapshots.ndjson").open("wb") as target,
    ):
        shutil.copyfileobj(source, target)
    return run_root


def _read_ndjson(path: Path) -> list[dict[str, Any]]:
    """Load one NDJSON file into a row list."""

    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _write_sidecar(path: Path, entries: list[dict[str, Any]]) -> None:
    """Write one hand-built hook sidecar."""

    path.write_text(
        "\n".join(json.dumps(item, sort_keys=True) for item in entries) + "\n",
        encoding="utf-8",
    )


def _envelope(
    *,
    sequence: int | None,
    received_at_utc: str,
    provider_event: dict[str, Any],
) -> dict[str, Any]:
    """Build one sidecar envelope payload."""

    return {
        "sequence": sequence,
        "received_at_utc": received_at_utc,
        "channel_generation": 1,
        "via": "http",
        "provider_event": provider_event,
    }


def _write_minimal_run(*, tmp_path: Path, sample_count: int) -> TerminalRecordPaths:
    """Write a minimal codex recorder run with empty pane snapshots."""

    run_root = tmp_path / "run-hook-sidecar"
    paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    target = TerminalRecordTarget(
        session_name="HOUMAO-gpu",
        pane_id="%1",
        window_id="@2",
        window_name="developer-1",
    )
    manifest = TerminalRecordManifest(
        schema_version=TERMINAL_RECORD_SCHEMA_VERSION,
        run_id=run_root.name,
        mode="passive",
        repo_root=str(tmp_path),
        run_root=str(run_root),
        target=target,
        tool="codex",
        sample_interval_seconds=1.0,
        visual_recording_kind="readonly_observer",
        input_capture_level="output_only",
        run_tainted=False,
        taint_reasons=(),
        recorder_session_name=f"HMREC-{run_root.name}",
        attach_command=None,
        started_at_utc="2026-03-19T00:00:00+00:00",
        stopped_at_utc="2026-03-19T00:01:00+00:00",
        stop_reason="stop_requested",
    )
    save_manifest(paths.manifest_path, manifest)
    rows = [
        {
            "sample_id": f"s{index:06d}",
            "elapsed_seconds": float(index - 1),
            "ts_utc": f"2026-03-19T00:00:{index - 1:02d}+00:00",
            "target_pane_id": "%1",
            "output_text": "",
        }
        for index in range(1, sample_count + 1)
    ]
    paths.pane_snapshots_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return paths


def _write_labels(path: Path, labels: list[dict[str, Any]]) -> None:
    """Write one labels payload with required expectations."""

    path.write_text(
        json.dumps(
            {
                "schema_version": TERMINAL_RECORD_SCHEMA_VERSION,
                "labels": labels,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_claude_fixture_without_hook_sidecar_is_byte_identical(tmp_path: Path) -> None:
    run_root = _materialize_session1_fixture(tmp_path=tmp_path)

    result = analyze_terminal_record(
        run_root=run_root,
        tool="claude",
        observed_version="2.1.296",
        output_tag="qualification",
    )

    parser_bytes = (run_root / "parser_observed_qualification.ndjson").read_bytes()
    state_bytes = (run_root / "state_observed_qualification.ndjson").read_bytes()
    assert hashlib.sha256(parser_bytes).hexdigest() == _BASELINE_PARSER_SHA256
    assert hashlib.sha256(state_bytes).hexdigest() == _BASELINE_STATE_SHA256
    assert not (run_root / "hook_observed_qualification.ndjson").exists()
    assert "hook_observed_path" not in result
    assert "hook_sidecar" not in result


def test_claude_fixture_with_synthesized_sidecar_emits_hook_observations(
    tmp_path: Path,
) -> None:
    run_root = _materialize_session1_fixture(tmp_path=tmp_path)

    synthesis = synthesize_hook_sidecar(
        run_root=run_root,
        labels_path=_SESSION1_FIXTURE / "labels.json",
    )
    mappings = {item["label_id"]: item for item in synthesis.mappings}

    assert synthesis.turn_count == 11
    assert synthesis.envelope_count == 24
    assert mappings["active-001"]["prompt_sample_id"] == "s000099"
    assert mappings["active-001"]["terminal_sample_id"] == "s000161"
    assert mappings["active-001"]["terminal_event"] == "Stop"
    assert mappings["active-006"]["prompt_sample_id"] == "s001372"
    assert mappings["active-006"]["terminal_sample_id"] == "s001398"
    assert "interrupted-001" not in mappings

    result = analyze_terminal_record(
        run_root=run_root,
        tool="claude",
        observed_version="2.1.296",
        output_tag="qualification",
    )
    rows = {
        row["sample_id"]: row
        for row in _read_ndjson(run_root / "hook_observed_qualification.ndjson")
    }

    assert len(rows) == 1563
    assert rows["s000098"]["hook_evidence_seen"] is True
    assert rows["s000099"]["hook_turn_phase"] == "active"
    assert rows["s000099"]["hook_last_event_name"] == "UserPromptSubmit"
    assert rows["s000099"]["hook_active_prompt_id"] == "synth:active-001"
    assert rows["s000099"]["hook_conflicts"] == []
    assert rows["s000160"]["hook_turn_phase"] == "active"
    assert rows["s000161"]["hook_turn_phase"] == "ready"
    assert rows["s000161"]["hook_terminal_result"] == "success"
    assert "hook_terminal_tui_active" in rows["s000161"]["hook_new_conflicts"]
    assert rows["s000162"]["hook_turn_phase"] == "ready"
    assert "hook_success_tui_interrupted" in rows["s001399"]["hook_conflicts"]
    assert "hook_success_tui_interrupted" in rows["s001563"]["hook_conflicts"]
    assert result["hook_sidecar_path"] == str(run_root / "hook_events.ndjson")
    assert result["hook_observed_path"] == str(run_root / "hook_observed_qualification.ndjson")
    assert result["hook_sidecar"]["envelope_count"] == 24
    assert result["hook_sidecar"]["evidence_sample_count"] == 1563


def test_analyze_counts_malformed_hook_sidecar_lines(tmp_path: Path) -> None:
    paths = _write_minimal_run(tmp_path=tmp_path, sample_count=2)
    valid = _envelope(
        sequence=1,
        received_at_utc="2026-03-19T00:00:00.500000+00:00",
        provider_event={
            "hook_event_name": "UserPromptSubmit",
            "prompt_id": "p1",
        },
    )
    paths.hook_events_path.write_text(
        "\n"
        + json.dumps(valid, sort_keys=True)
        + "\n"
        + "{not-json\n"
        + json.dumps({"sequence": 2})
        + "\n",
        encoding="utf-8",
    )

    result = analyze_terminal_record(
        run_root=paths.run_root,
        tool="codex",
        observed_version="0.162.1",
        output_tag="hooks",
    )

    sidecar = result["hook_sidecar"]
    assert sidecar["envelope_count"] == 1
    assert sidecar["skipped_blank_lines"] == 1
    assert sidecar["skipped_garbage_lines"] == 1
    assert sidecar["skipped_invalid_lines"] == 1
    rows = _read_ndjson(paths.run_root / "hook_observed_hooks.ndjson")
    assert rows[-1]["hook_evidence_seen"] is True
    assert rows[-1]["hook_last_event_name"] == "UserPromptSubmit"
    assert rows[-1]["hook_turn_phase"] == "active"


def test_synthesize_hook_sidecar_maps_active_windows_and_terminal_kinds(
    tmp_path: Path,
) -> None:
    paths = _write_minimal_run(tmp_path=tmp_path, sample_count=9)
    _write_labels(
        paths.labels_path,
        [
            {
                "label_id": "active-1",
                "sample_id": "s000001",
                "sample_end_id": "s000003",
                "expectations": {
                    "surface_pending_input": "no",
                    "turn_phase": "active",
                    "last_turn_result": "none",
                },
            },
            {
                "label_id": "ready-1",
                "sample_id": "s000004",
                "sample_end_id": "s000005",
                "expectations": {
                    "surface_pending_input": "no",
                    "turn_phase": "ready",
                    "last_turn_result": "success",
                },
            },
            {
                "label_id": "active-2",
                "sample_id": "s000006",
                "sample_end_id": "s000007",
                "expectations": {
                    "surface_pending_input": "no",
                    "turn_phase": "active",
                    "last_turn_result": "none",
                },
            },
            {
                "label_id": "ready-2",
                "sample_id": "s000008",
                "sample_end_id": "s000009",
                "expectations": {
                    "surface_pending_input": "no",
                    "turn_phase": "ready",
                    "last_turn_result": "known_failure",
                },
            },
        ],
    )

    result = synthesize_hook_sidecar(run_root=paths.run_root)

    rows = _read_ndjson(paths.hook_events_path)
    names = [
        row["provider_event"]["hook_event_name"]
        for row in rows
        if row.get("record_type") != "generation_boundary"
    ]
    assert names == ["SessionStart", "UserPromptSubmit", "Stop", "UserPromptSubmit", "StopFailure"]
    assert rows[0]["record_type"] == "generation_boundary"
    assert rows[0]["sequence"] is None
    assert rows[1]["sequence"] == 1
    assert rows[2]["sequence"] == 2
    assert rows[3]["sequence"] == 3
    assert rows[3]["received_at_utc"].startswith("2026-03-19T00:00:02")
    assert rows[5]["received_at_utc"].startswith("2026-03-19T00:00:06")
    assert result.turn_count == 2
    assert result.event_count == 5
    assert result.mappings[0]["prompt_sample_id"] == "s000001"
    assert result.mappings[0]["terminal_sample_id"] == "s000003"
    assert result.mappings[1]["terminal_event"] == "StopFailure"


def test_hook_replay_reports_merge_conflict_kinds(tmp_path: Path) -> None:
    snapshots = [
        TerminalRecordPaneSnapshot(
            sample_id=f"s{index:06d}",
            elapsed_seconds=float(index),
            ts_utc=f"2026-03-19T00:00:0{index}+00:00",
            target_pane_id="%1",
            output_text="",
        )
        for index in range(4)
    ]
    state_rows = [
        {
            "sample_id": "s000000",
            "turn_phase": "active",
            "surface_ready_posture": "no",
            "last_turn_result": "none",
        },
        {
            "sample_id": "s000001",
            "turn_phase": "ready",
            "surface_ready_posture": "yes",
            "last_turn_result": "none",
        },
        {
            "sample_id": "s000002",
            "turn_phase": "ready",
            "surface_ready_posture": "yes",
            "last_turn_result": "none",
        },
        {
            "sample_id": "s000003",
            "turn_phase": "active",
            "surface_ready_posture": "no",
            "last_turn_result": "success",
        },
    ]
    sidecar_path = tmp_path / "hook_events.ndjson"
    _write_sidecar(
        sidecar_path,
        [
            _envelope(
                sequence=1,
                received_at_utc="2026-03-19T00:00:00.500000+00:00",
                provider_event={"hook_event_name": "UserPromptSubmit", "prompt_id": "p1"},
            ),
            _envelope(
                sequence=2,
                received_at_utc="2026-03-19T00:00:01.500000+00:00",
                provider_event={"hook_event_name": "PermissionRequest", "tool_name": "Bash"},
            ),
            _envelope(
                sequence=3,
                received_at_utc="2026-03-19T00:00:02.500000+00:00",
                provider_event={
                    "hook_event_name": "StopFailure",
                    "prompt_id": "p1",
                    "error": "synthetic_known_failure",
                },
            ),
        ],
    )

    result = replay_hook_sidecar(
        sidecar_path=sidecar_path,
        snapshots=snapshots,
        state_rows=state_rows,
        recording_started_at_utc="2026-03-19T00:00:00+00:00",
    )

    rows = {row["sample_id"]: row for row in result.rows}
    assert rows["s000001"]["hook_turn_phase"] == "active"
    assert "hook_active_tui_ready" in rows["s000001"]["hook_new_conflicts"]
    assert rows["s000002"]["hook_turn_phase"] == "blocked"
    assert "hook_blocked_tui_ready" in rows["s000002"]["hook_new_conflicts"]
    assert rows["s000003"]["hook_terminal_result"] == "known_failure"
    assert "hook_terminal_tui_active" in rows["s000003"]["hook_new_conflicts"]
    assert "hook_failure_tui_success" in rows["s000003"]["hook_new_conflicts"]
    assert result.conflict_counts["hook_active_tui_ready"] == 1
    assert result.conflict_counts["hook_failure_tui_success"] == 1


def test_hook_replay_reports_staleness_and_recovery_correction(tmp_path: Path) -> None:
    snapshots = [
        TerminalRecordPaneSnapshot(
            sample_id="s000000",
            elapsed_seconds=0.0,
            ts_utc="2026-03-19T00:00:00+00:00",
            target_pane_id="%1",
            output_text="",
        ),
        TerminalRecordPaneSnapshot(
            sample_id="s000001",
            elapsed_seconds=31.0,
            ts_utc="2026-03-19T00:00:31+00:00",
            target_pane_id="%1",
            output_text="",
        ),
        TerminalRecordPaneSnapshot(
            sample_id="s000002",
            elapsed_seconds=32.0,
            ts_utc="2026-03-19T00:00:32+00:00",
            target_pane_id="%1",
            output_text="",
        ),
        TerminalRecordPaneSnapshot(
            sample_id="s000003",
            elapsed_seconds=33.0,
            ts_utc="2026-03-19T00:00:33+00:00",
            target_pane_id="%1",
            output_text="",
        ),
    ]
    state_rows = [
        {
            "sample_id": "s000000",
            "turn_phase": "active",
            "surface_ready_posture": "no",
            "surface_pending_input": "no",
            "last_turn_result": "none",
        },
        {
            "sample_id": "s000001",
            "turn_phase": "active",
            "surface_ready_posture": "no",
            "surface_pending_input": "yes",
            "last_turn_result": "none",
        },
        {
            "sample_id": "s000002",
            "turn_phase": "active",
            "surface_ready_posture": "no",
            "surface_pending_input": "no",
            "last_turn_result": "none",
        },
        {
            "sample_id": "s000003",
            "turn_phase": "ready",
            "surface_ready_posture": "yes",
            "surface_pending_input": "no",
            "last_turn_result": "success",
        },
    ]
    sidecar_path = tmp_path / "hook_events.ndjson"
    _write_sidecar(
        sidecar_path,
        [
            _envelope(
                sequence=1,
                received_at_utc="2026-03-19T00:00:00.500000+00:00",
                provider_event={"hook_event_name": "UserPromptSubmit", "prompt_id": "p1"},
            ),
            _envelope(
                sequence=2,
                received_at_utc="2026-03-19T00:00:32.500000+00:00",
                provider_event={"hook_event_name": "StopFailure", "prompt_id": "p1"},
            ),
        ],
    )

    result = replay_hook_sidecar(
        sidecar_path=sidecar_path,
        snapshots=snapshots,
        state_rows=state_rows,
        recording_started_at_utc="2026-03-19T00:00:00+00:00",
    )

    rows = {row["sample_id"]: row for row in result.rows}
    assert "hook_stale_tui_authoritative" in rows["s000001"]["hook_conflicts"]
    assert "hook_stale_tui_authoritative" in rows["s000002"]["hook_conflicts"]
    assert "hook_correction_after_staleness" in rows["s000003"]["hook_new_conflicts"]
    assert "hook_failure_tui_success" in rows["s000003"]["hook_new_conflicts"]
