"""Shared models and persistence helpers for the tracked-TUI demo pack."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

from houmao.shared_tui_tracking.models import (
    RecordedInputEvent,
    RuntimeObservation,
    TrackedTimelineState,
)


ToolName = Literal["claude", "codex"]
InteractiveWatchStatus = Literal["starting", "running", "stopping", "stopped", "failed"]

DEFAULT_DEMO_ROOT_PARENT = Path("tmp/demo/shared-tui-tracking-demo-pack")
DEFAULT_RECORDED_RUN_ROOT_PARENT = DEFAULT_DEMO_ROOT_PARENT / "recorded"
DEFAULT_LIVE_RUN_ROOT_PARENT = DEFAULT_DEMO_ROOT_PARENT / "live"
DEFAULT_SWEEP_RUN_ROOT_PARENT = DEFAULT_DEMO_ROOT_PARENT / "sweeps"
DEFAULT_REVIEW_VIDEO_FPS = 8
DEMO_PACK_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RecordedValidationPaths:
    """Filesystem layout for one recorded-validation run."""

    run_root: Path
    artifacts_dir: Path
    analysis_dir: Path
    issues_dir: Path
    logs_dir: Path
    review_dir: Path
    frames_dir: Path
    manifest_path: Path
    resolved_config_path: Path
    runtime_observations_path: Path
    groundtruth_timeline_path: Path
    replay_timeline_path: Path
    replay_events_path: Path
    comparison_json_path: Path
    comparison_markdown_path: Path
    report_path: Path
    review_video_path: Path

    @classmethod
    def from_run_root(cls, *, run_root: Path) -> "RecordedValidationPaths":
        """Return canonical paths for one recorded-validation run."""

        resolved = run_root.resolve()
        artifacts_dir = resolved / "artifacts"
        analysis_dir = resolved / "analysis"
        review_dir = resolved / "review"
        return cls(
            run_root=resolved,
            artifacts_dir=artifacts_dir,
            analysis_dir=analysis_dir,
            issues_dir=resolved / "issues",
            logs_dir=resolved / "logs",
            review_dir=review_dir,
            frames_dir=review_dir / "frames",
            manifest_path=artifacts_dir / "recorded_validation_manifest.json",
            resolved_config_path=artifacts_dir / "resolved_demo_config.json",
            runtime_observations_path=artifacts_dir / "runtime_observations.ndjson",
            groundtruth_timeline_path=analysis_dir / "groundtruth_timeline.ndjson",
            replay_timeline_path=analysis_dir / "replay_timeline.ndjson",
            replay_events_path=analysis_dir / "replay_events.ndjson",
            comparison_json_path=analysis_dir / "comparison.json",
            comparison_markdown_path=analysis_dir / "comparison.md",
            report_path=analysis_dir / "summary_report.md",
            review_video_path=review_dir / "review.mp4",
        )


@dataclass(frozen=True)
class LiveWatchPaths:
    """Filesystem layout for one live-watch run."""

    run_root: Path
    runtime_root: Path
    workdir: Path
    artifacts_dir: Path
    analysis_dir: Path
    issues_dir: Path
    logs_dir: Path
    traces_dir: Path
    terminal_record_run_root: Path
    watch_manifest_path: Path
    resolved_config_path: Path
    live_state_path: Path
    runtime_observations_path: Path
    latest_state_path: Path
    state_samples_path: Path
    transitions_path: Path
    groundtruth_timeline_path: Path
    replay_timeline_path: Path
    replay_events_path: Path
    comparison_json_path: Path
    comparison_markdown_path: Path
    report_path: Path

    @classmethod
    def from_run_root(cls, *, run_root: Path) -> "LiveWatchPaths":
        """Return canonical paths for one live-watch run."""

        resolved = run_root.resolve()
        artifacts_dir = resolved / "artifacts"
        analysis_dir = resolved / "analysis"
        return cls(
            run_root=resolved,
            runtime_root=resolved / "runtime",
            workdir=resolved / "workdir",
            artifacts_dir=artifacts_dir,
            analysis_dir=analysis_dir,
            issues_dir=resolved / "issues",
            logs_dir=resolved / "logs",
            traces_dir=resolved / "traces",
            terminal_record_run_root=resolved / f"terminal-record-{resolved.name}",
            watch_manifest_path=artifacts_dir / "interactive_watch_manifest.json",
            resolved_config_path=artifacts_dir / "resolved_demo_config.json",
            live_state_path=artifacts_dir / "interactive_watch_live_state.json",
            runtime_observations_path=artifacts_dir / "runtime_observations.ndjson",
            latest_state_path=artifacts_dir / "latest_state.json",
            state_samples_path=artifacts_dir / "state_samples.ndjson",
            transitions_path=artifacts_dir / "transitions.ndjson",
            groundtruth_timeline_path=analysis_dir / "groundtruth_timeline.ndjson",
            replay_timeline_path=analysis_dir / "replay_timeline.ndjson",
            replay_events_path=analysis_dir / "replay_events.ndjson",
            comparison_json_path=analysis_dir / "comparison.json",
            comparison_markdown_path=analysis_dir / "comparison.md",
            report_path=analysis_dir / "summary_report.md",
        )


@dataclass(frozen=True)
class RecordedFixtureManifest:
    """Committed fixture metadata for one recorded case."""

    schema_version: int
    case_id: str
    tool: ToolName
    observed_version: str | None
    settle_seconds: float
    description: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "RecordedFixtureManifest":
        """Parse one fixture-manifest payload."""

        return cls(
            schema_version=int(payload.get("schema_version", 0)),
            case_id=str(payload["case_id"]),
            tool=cast(ToolName, str(payload["tool"])),
            observed_version=_optional_string(payload.get("observed_version")),
            settle_seconds=float(payload["settle_seconds"]),
            description=str(payload["description"]),
        )


@dataclass(frozen=True)
class RecordedValidationManifest:
    """Persisted manifest for one recorded-validation run."""

    schema_version: int
    run_id: str
    case_id: str
    tool: ToolName
    repo_root: str
    run_root: str
    fixture_root: str
    recording_root: str
    labels_path: str
    resolved_config_path: str
    observed_version: str | None
    settle_seconds: float
    review_video_fps: float
    capture_sample_interval_seconds: float
    started_at_utc: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class LiveWatchManifest:
    """Persisted manifest for one live-watch run."""

    schema_version: int
    run_id: str
    tool: ToolName
    repo_root: str
    run_root: str
    runtime_root: str
    recipe_path: str
    brain_home_path: str
    brain_manifest_path: str
    launch_helper_path: str
    workdir: str
    tool_session_name: str
    tool_attach_command: str
    dashboard_session_name: str
    dashboard_attach_command: str
    dashboard_command: str
    recorder_enabled: bool
    terminal_record_run_root: str | None
    resolved_config_path: str
    sample_interval_seconds: float
    runtime_observer_interval_seconds: float
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
    def from_payload(cls, payload: dict[str, Any]) -> "LiveWatchManifest":
        """Parse one live-watch manifest payload."""

        run_root = str(payload["run_root"])
        return cls(
            schema_version=int(payload.get("schema_version", 0)),
            run_id=str(payload["run_id"]),
            tool=cast(ToolName, str(payload["tool"])),
            repo_root=str(payload["repo_root"]),
            run_root=run_root,
            runtime_root=str(payload["runtime_root"]),
            recipe_path=str(payload["recipe_path"]),
            brain_home_path=str(payload["brain_home_path"]),
            brain_manifest_path=str(payload["brain_manifest_path"]),
            launch_helper_path=str(payload["launch_helper_path"]),
            workdir=str(payload["workdir"]),
            tool_session_name=str(payload["tool_session_name"]),
            tool_attach_command=str(payload["tool_attach_command"]),
            dashboard_session_name=str(payload["dashboard_session_name"]),
            dashboard_attach_command=str(payload["dashboard_attach_command"]),
            dashboard_command=str(payload["dashboard_command"]),
            recorder_enabled=_coerce_recorder_enabled(payload=payload, run_root=run_root),
            terminal_record_run_root=_coerce_terminal_record_run_root(
                payload=payload, run_root=run_root
            ),
            resolved_config_path=str(
                payload.get(
                    "resolved_config_path",
                    LiveWatchPaths.from_run_root(
                        run_root=Path(run_root)
                    ).resolved_config_path,
                )
            ),
            sample_interval_seconds=float(payload["sample_interval_seconds"]),
            runtime_observer_interval_seconds=float(
                payload.get(
                    "runtime_observer_interval_seconds",
                    payload["sample_interval_seconds"],
                )
            ),
            settle_seconds=float(payload["settle_seconds"]),
            observed_version=_optional_string(payload.get("observed_version")),
            trace_enabled=bool(payload.get("trace_enabled", False)),
            started_at_utc=str(payload["started_at_utc"]),
            stopped_at_utc=_optional_string(payload.get("stopped_at_utc")),
            stop_reason=_optional_string(payload.get("stop_reason")),
        )


@dataclass(frozen=True)
class LiveWatchLiveState:
    """Mutable live-state record for one live-watch run."""

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
    def from_payload(cls, payload: dict[str, Any]) -> "LiveWatchLiveState":
        """Parse one live-state payload."""

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


@dataclass(frozen=True)
class LiveWatchStartResult:
    """Summary of one started live-watch run."""

    run_root: Path
    manifest: LiveWatchManifest


@dataclass(frozen=True)
class RecordedSweepPaths:
    """Filesystem layout for one recorded-sweep run."""

    run_root: Path
    artifacts_dir: Path
    analysis_dir: Path
    issues_dir: Path
    variants_dir: Path
    manifest_path: Path
    resolved_config_path: Path
    report_path: Path
    summary_json_path: Path

    @classmethod
    def from_run_root(cls, *, run_root: Path) -> "RecordedSweepPaths":
        """Return canonical paths for one recorded-sweep run."""

        resolved = run_root.resolve()
        artifacts_dir = resolved / "artifacts"
        analysis_dir = resolved / "analysis"
        return cls(
            run_root=resolved,
            artifacts_dir=artifacts_dir,
            analysis_dir=analysis_dir,
            issues_dir=resolved / "issues",
            variants_dir=resolved / "variants",
            manifest_path=artifacts_dir / "recorded_sweep_manifest.json",
            resolved_config_path=artifacts_dir / "resolved_demo_config.json",
            report_path=analysis_dir / "summary_report.md",
            summary_json_path=analysis_dir / "summary.json",
        )


def append_ndjson(path: Path, payload: dict[str, Any]) -> None:
    """Append one JSON record to an NDJSON file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def overwrite_ndjson(path: Path, payloads: list[dict[str, Any]]) -> None:
    """Overwrite one NDJSON file with the provided payload sequence."""

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
    """Persist one JSON payload."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any] | None:
    """Load one JSON payload when present."""

    if not path.is_file():
        return None
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def load_runtime_observations(path: Path) -> list[RuntimeObservation]:
    """Load runtime observations from one NDJSON path."""

    return [RuntimeObservation.from_payload(item) for item in load_ndjson(path)]


def load_input_events(path: Path) -> list[RecordedInputEvent]:
    """Load replay-compatible recorded input events from disk."""

    events: list[RecordedInputEvent] = []
    for payload in load_ndjson(path):
        events.append(
            RecordedInputEvent(
                event_id=str(payload["event_id"]),
                elapsed_seconds=float(payload["elapsed_seconds"]),
                ts_utc=str(payload["ts_utc"]),
                source=str(payload.get("source", "unknown")),
            )
        )
    return events


def load_timeline(path: Path) -> list[TrackedTimelineState]:
    """Load one serialized tracked timeline."""

    return [TrackedTimelineState.from_payload(item) for item in load_ndjson(path)]


def ensure_directory_layout(
    paths: RecordedValidationPaths | LiveWatchPaths | RecordedSweepPaths,
) -> None:
    """Create the canonical directory tree for one run."""

    for field_name, value in paths.__dict__.items():
        if not isinstance(value, Path):
            continue
        if value.suffix:
            continue
        if field_name == "terminal_record_run_root":
            continue
        value.mkdir(parents=True, exist_ok=True)


def _optional_string(value: object) -> str | None:
    """Return one optional string value."""

    if value is None:
        return None
    return str(value)


def _coerce_terminal_record_run_root(*, payload: dict[str, Any], run_root: str) -> str | None:
    """Return the persisted recorder root when one is present."""

    raw_value = _optional_string(payload.get("terminal_record_run_root"))
    if raw_value is not None:
        return raw_value
    if payload.get("recorder_enabled") is True:
        return str(LiveWatchPaths.from_run_root(run_root=Path(run_root)).terminal_record_run_root)
    return None


def _coerce_recorder_enabled(*, payload: dict[str, Any], run_root: str) -> bool:
    """Infer recorder enablement for newer and older live-watch manifests."""

    raw_value = payload.get("recorder_enabled")
    if isinstance(raw_value, bool):
        return raw_value
    return _coerce_terminal_record_run_root(payload=payload, run_root=run_root) is not None
