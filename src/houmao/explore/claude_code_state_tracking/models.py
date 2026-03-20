"""Shared models for the Claude Code state-tracking explore harness.

This module intentionally mirrors the simplified tracked-state vocabulary from
OpenSpec without importing `houmao-server` tracker implementation code.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast


Tristate = Literal["yes", "no", "unknown"]
Availability = Literal["available", "unavailable", "tui_down", "error", "unknown"]
TurnPhase = Literal["ready", "active", "unknown"]
LastTurnResult = Literal["success", "interrupted", "known_failure", "none"]
InteractiveWatchStatus = Literal["starting", "running", "stopping", "stopped", "failed"]


@dataclass(frozen=True)
class HarnessPaths:
    """Canonical artifact paths for one harness run."""

    run_root: Path
    artifacts_dir: Path
    logs_dir: Path
    analysis_dir: Path
    terminal_record_run_root: Path
    capture_manifest_path: Path
    drive_events_path: Path
    runtime_observations_path: Path
    replay_events_path: Path
    groundtruth_timeline_path: Path
    replay_timeline_path: Path
    comparison_json_path: Path
    comparison_markdown_path: Path

    @classmethod
    def from_run_root(cls, *, run_root: Path) -> "HarnessPaths":
        """Return canonical paths rooted at one run directory.

        Parameters
        ----------
        run_root:
            Root directory for one harness run.
        """

        resolved = run_root.resolve()
        artifacts_dir = resolved / "artifacts"
        analysis_dir = resolved / "analysis"
        logs_dir = resolved / "logs"
        return cls(
            run_root=resolved,
            artifacts_dir=artifacts_dir,
            logs_dir=logs_dir,
            analysis_dir=analysis_dir,
            terminal_record_run_root=resolved / f"terminal-record-{resolved.name}",
            capture_manifest_path=artifacts_dir / "capture_manifest.json",
            drive_events_path=artifacts_dir / "drive_events.ndjson",
            runtime_observations_path=artifacts_dir / "runtime_observations.ndjson",
            replay_events_path=analysis_dir / "replay_events.ndjson",
            groundtruth_timeline_path=analysis_dir / "groundtruth_timeline.ndjson",
            replay_timeline_path=analysis_dir / "replay_timeline.ndjson",
            comparison_json_path=analysis_dir / "comparison.json",
            comparison_markdown_path=analysis_dir / "comparison.md",
        )


@dataclass(frozen=True)
class RuntimeObservation:
    """One runtime liveness sample captured alongside pane snapshots."""

    ts_utc: str
    elapsed_seconds: float
    session_exists: bool
    pane_exists: bool
    pane_dead: bool
    pane_pid: int | None
    pane_pid_alive: bool
    supported_process_pid: int | None
    supported_process_alive: bool

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "RuntimeObservation":
        """Parse one runtime-observation payload."""

        return cls(
            ts_utc=str(payload["ts_utc"]),
            elapsed_seconds=float(payload["elapsed_seconds"]),
            session_exists=bool(payload["session_exists"]),
            pane_exists=bool(payload["pane_exists"]),
            pane_dead=bool(payload.get("pane_dead", False)),
            pane_pid=_optional_int(payload.get("pane_pid")),
            pane_pid_alive=bool(payload.get("pane_pid_alive", False)),
            supported_process_pid=_optional_int(payload.get("supported_process_pid")),
            supported_process_alive=bool(payload.get("supported_process_alive", False)),
        )


@dataclass(frozen=True)
class RecordedObservation:
    """One replay-grade observation combining pane text and runtime diagnostics."""

    sample_id: str
    elapsed_seconds: float
    ts_utc: str
    output_text: str
    runtime: RuntimeObservation | None


@dataclass(frozen=True)
class DetectedSignals:
    """Normalized detector output for one visible surface."""

    detector_name: str
    detector_version: str
    accepting_input: Tristate
    editing_input: Tristate
    ready_posture: Tristate
    prompt_visible: bool
    prompt_text: str | None
    footer_interruptable: bool
    active_evidence: bool
    active_reasons: tuple[str, ...]
    interrupted: bool
    known_failure: bool
    current_error_present: bool
    success_candidate: bool
    completion_marker: str | None
    latest_status_line: str | None
    surface_signature: str
    notes: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class TimelineState:
    """One sample-aligned state timeline row."""

    sample_id: str
    elapsed_seconds: float
    ts_utc: str
    diagnostics_availability: Availability
    surface_accepting_input: Tristate
    surface_editing_input: Tristate
    surface_ready_posture: Tristate
    turn_phase: TurnPhase
    last_turn_result: LastTurnResult
    detector_name: str
    detector_version: str
    active_reasons: tuple[str, ...]
    notes: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TimelineState":
        """Parse one timeline payload."""

        return cls(
            sample_id=str(payload["sample_id"]),
            elapsed_seconds=float(payload["elapsed_seconds"]),
            ts_utc=str(payload["ts_utc"]),
            diagnostics_availability=cast(Availability, str(payload["diagnostics_availability"])),
            surface_accepting_input=cast(Tristate, str(payload["surface_accepting_input"])),
            surface_editing_input=cast(Tristate, str(payload["surface_editing_input"])),
            surface_ready_posture=cast(Tristate, str(payload["surface_ready_posture"])),
            turn_phase=cast(TurnPhase, str(payload["turn_phase"])),
            last_turn_result=cast(LastTurnResult, str(payload["last_turn_result"])),
            detector_name=str(payload["detector_name"]),
            detector_version=str(payload["detector_version"]),
            active_reasons=tuple(str(item) for item in payload.get("active_reasons", [])),
            notes=tuple(str(item) for item in payload.get("notes", [])),
        )


@dataclass(frozen=True)
class ReplayEvent:
    """One internal replay state-change event."""

    source: Literal["observation", "timer"]
    at_seconds: float
    diagnostics_availability: Availability
    turn_phase: TurnPhase
    last_turn_result: LastTurnResult
    sample_id: str | None
    note: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class LiveStateSample:
    """One live state sample or timer-driven state emission."""

    source: Literal["observation", "timer"]
    sample_id: str | None
    elapsed_seconds: float
    ts_utc: str
    diagnostics_availability: Availability
    surface_accepting_input: Tristate
    surface_editing_input: Tristate
    surface_ready_posture: Tristate
    turn_phase: TurnPhase
    last_turn_result: LastTurnResult
    detector_name: str
    detector_version: str
    active_reasons: tuple[str, ...]
    notes: tuple[str, ...]
    transition_note: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class InteractiveWatchPaths:
    """Filesystem layout for one interactive watch run."""

    run_root: Path
    runtime_root: Path
    workdir: Path
    artifacts_dir: Path
    logs_dir: Path
    analysis_dir: Path
    traces_dir: Path
    terminal_record_run_root: Path
    watch_manifest_path: Path
    live_state_path: Path
    runtime_observations_path: Path
    latest_state_path: Path
    state_samples_path: Path
    transitions_path: Path
    report_path: Path

    @classmethod
    def from_run_root(cls, *, run_root: Path) -> "InteractiveWatchPaths":
        """Return canonical paths for one interactive watch run root."""

        resolved = run_root.resolve()
        artifacts_dir = resolved / "artifacts"
        return cls(
            run_root=resolved,
            runtime_root=resolved / "runtime",
            workdir=resolved / "workdir",
            artifacts_dir=artifacts_dir,
            logs_dir=resolved / "logs",
            analysis_dir=resolved / "analysis",
            traces_dir=resolved / "traces",
            terminal_record_run_root=resolved / f"terminal-record-{resolved.name}",
            watch_manifest_path=artifacts_dir / "interactive_watch_manifest.json",
            live_state_path=artifacts_dir / "interactive_watch_live_state.json",
            runtime_observations_path=artifacts_dir / "runtime_observations.ndjson",
            latest_state_path=artifacts_dir / "latest_state.json",
            state_samples_path=artifacts_dir / "state_samples.ndjson",
            transitions_path=artifacts_dir / "transitions.ndjson",
            report_path=resolved / "analysis" / "interactive_watch_report.md",
        )


@dataclass(frozen=True)
class InteractiveWatchManifest:
    """Persisted manifest for one interactive watch run."""

    schema_version: int
    run_id: str
    repo_root: str
    run_root: str
    runtime_root: str
    recipe_path: str
    brain_home_path: str
    brain_manifest_path: str
    launch_helper_path: str
    workdir: str
    claude_session_name: str
    claude_attach_command: str
    dashboard_session_name: str
    dashboard_attach_command: str
    dashboard_command: str
    terminal_record_run_root: str
    sample_interval_seconds: float
    settle_seconds: float
    observed_version: str | None
    trace_enabled: bool
    started_at_utc: str
    stopped_at_utc: str | None
    stop_reason: str | None

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "InteractiveWatchManifest":
        """Parse one persisted interactive watch manifest."""

        return cls(
            schema_version=int(payload.get("schema_version", 0)),
            run_id=str(payload["run_id"]),
            repo_root=str(payload["repo_root"]),
            run_root=str(payload["run_root"]),
            runtime_root=str(payload["runtime_root"]),
            recipe_path=str(payload["recipe_path"]),
            brain_home_path=str(payload["brain_home_path"]),
            brain_manifest_path=str(payload["brain_manifest_path"]),
            launch_helper_path=str(payload["launch_helper_path"]),
            workdir=str(payload["workdir"]),
            claude_session_name=str(payload["claude_session_name"]),
            claude_attach_command=str(payload["claude_attach_command"]),
            dashboard_session_name=str(payload["dashboard_session_name"]),
            dashboard_attach_command=str(payload["dashboard_attach_command"]),
            dashboard_command=str(payload["dashboard_command"]),
            terminal_record_run_root=str(payload["terminal_record_run_root"]),
            sample_interval_seconds=float(payload["sample_interval_seconds"]),
            settle_seconds=float(payload["settle_seconds"]),
            observed_version=_optional_string(payload.get("observed_version")),
            trace_enabled=bool(payload.get("trace_enabled", False)),
            started_at_utc=str(payload["started_at_utc"]),
            stopped_at_utc=_optional_string(payload.get("stopped_at_utc")),
            stop_reason=_optional_string(payload.get("stop_reason")),
        )


@dataclass(frozen=True)
class InteractiveWatchLiveState:
    """Mutable live-state record for one interactive watch run."""

    schema_version: int
    run_id: str
    run_root: str
    status: InteractiveWatchStatus
    latest_state_path: str
    stop_requested_at_utc: str | None
    last_error: str | None
    updated_at_utc: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "InteractiveWatchLiveState":
        """Parse one interactive watch live-state payload."""

        return cls(
            schema_version=int(payload.get("schema_version", 0)),
            run_id=str(payload["run_id"]),
            run_root=str(payload["run_root"]),
            status=cast(InteractiveWatchStatus, str(payload["status"])),
            latest_state_path=str(payload["latest_state_path"]),
            stop_requested_at_utc=_optional_string(payload.get("stop_requested_at_utc")),
            last_error=_optional_string(payload.get("last_error")),
            updated_at_utc=str(payload["updated_at_utc"]),
        )


def append_ndjson(path: Path, payload: dict[str, Any]) -> None:
    """Append one NDJSON payload.

    Parameters
    ----------
    path:
        Output NDJSON file.
    payload:
        One JSON-serializable record.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def overwrite_ndjson(path: Path, payloads: list[dict[str, Any]]) -> None:
    """Overwrite one NDJSON file with the provided payloads."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for payload in payloads:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    """Load one NDJSON file into memory."""

    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def save_json(path: Path, payload: dict[str, Any]) -> None:
    """Persist one JSON payload with indentation."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any] | None:
    """Load one JSON payload when the file exists."""

    if not path.is_file():
        return None
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def load_runtime_observations(path: Path) -> list[RuntimeObservation]:
    """Load runtime observations from disk."""

    return [RuntimeObservation.from_payload(item) for item in load_ndjson(path)]


def load_timeline(path: Path) -> list[TimelineState]:
    """Load one serialized timeline."""

    return [TimelineState.from_payload(item) for item in load_ndjson(path)]


def _optional_int(value: object) -> int | None:
    """Return one optional integer parsed from an arbitrary value."""

    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    return None


def _optional_string(value: object) -> str | None:
    """Return one optional string value."""

    if value is None:
        return None
    return str(value)
