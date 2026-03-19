"""Models and persistence helpers for terminal recorder runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal


TERMINAL_RECORD_SCHEMA_VERSION = 1
DEFAULT_SAMPLE_INTERVAL_SECONDS = 0.2

RecorderMode = Literal["active", "passive"]
RecorderStatus = Literal["starting", "running", "stopping", "stopped", "failed"]
InputCaptureLevel = Literal["authoritative_managed", "managed_only", "output_only"]
VisualRecordingKind = Literal["interactive_client", "readonly_observer"]
InputEventSource = Literal["asciinema_input", "managed_send_keys"]


@dataclass(frozen=True)
class TerminalRecordPaths:
    """Filesystem layout for one terminal-record run."""

    run_root: Path
    manifest_path: Path
    live_state_path: Path
    pane_snapshots_path: Path
    input_events_path: Path
    labels_path: Path
    parser_observed_path: Path
    state_observed_path: Path
    cast_path: Path
    controller_log_path: Path
    asciinema_log_path: Path

    @classmethod
    def from_run_root(cls, *, run_root: Path) -> "TerminalRecordPaths":
        """Return canonical artifact paths for one run root."""

        resolved = run_root.resolve()
        return cls(
            run_root=resolved,
            manifest_path=resolved / "manifest.json",
            live_state_path=resolved / "live_state.json",
            pane_snapshots_path=resolved / "pane_snapshots.ndjson",
            input_events_path=resolved / "input_events.ndjson",
            labels_path=resolved / "labels.json",
            parser_observed_path=resolved / "parser_observed.ndjson",
            state_observed_path=resolved / "state_observed.ndjson",
            cast_path=resolved / "session.cast",
            controller_log_path=resolved / "controller.log",
            asciinema_log_path=resolved / "asciinema.log",
        )


@dataclass(frozen=True)
class TerminalRecordTarget:
    """Resolved tmux target for one recorder run."""

    session_name: str
    pane_id: str
    window_id: str
    window_name: str


@dataclass(frozen=True)
class TerminalRecordManifest:
    """Persisted manifest for one recorder run."""

    schema_version: int
    run_id: str
    mode: RecorderMode
    repo_root: str
    run_root: str
    target: TerminalRecordTarget
    tool: str | None
    sample_interval_seconds: float
    visual_recording_kind: VisualRecordingKind
    input_capture_level: InputCaptureLevel
    run_tainted: bool
    taint_reasons: tuple[str, ...]
    recorder_session_name: str
    attach_command: str | None
    started_at_utc: str
    stopped_at_utc: str | None
    stop_reason: str | None

    def to_payload(self) -> dict[str, Any]:
        """Return one JSON-serializable payload."""

        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TerminalRecordManifest":
        """Parse one manifest payload."""

        target_payload = _require_mapping(payload.get("target"), context="target")
        target = TerminalRecordTarget(
            session_name=_require_string(target_payload.get("session_name"), context="target.session_name"),
            pane_id=_require_string(target_payload.get("pane_id"), context="target.pane_id"),
            window_id=_require_string(target_payload.get("window_id"), context="target.window_id"),
            window_name=_require_string(target_payload.get("window_name"), context="target.window_name"),
        )
        taint_reasons_raw = payload.get("taint_reasons", [])
        if not isinstance(taint_reasons_raw, list) or not all(
            isinstance(item, str) for item in taint_reasons_raw
        ):
            raise ValueError("taint_reasons must be a list[str]")
        return cls(
            schema_version=int(payload.get("schema_version", 0)),
            run_id=_require_string(payload.get("run_id"), context="run_id"),
            mode=_require_mode(payload.get("mode")),
            repo_root=_require_string(payload.get("repo_root"), context="repo_root"),
            run_root=_require_string(payload.get("run_root"), context="run_root"),
            target=target,
            tool=_optional_string(payload.get("tool")),
            sample_interval_seconds=float(payload.get("sample_interval_seconds", DEFAULT_SAMPLE_INTERVAL_SECONDS)),
            visual_recording_kind=_require_visual_recording_kind(payload.get("visual_recording_kind")),
            input_capture_level=_require_input_capture_level(payload.get("input_capture_level")),
            run_tainted=bool(payload.get("run_tainted")),
            taint_reasons=tuple(taint_reasons_raw),
            recorder_session_name=_require_string(
                payload.get("recorder_session_name"),
                context="recorder_session_name",
            ),
            attach_command=_optional_string(payload.get("attach_command")),
            started_at_utc=_require_string(payload.get("started_at_utc"), context="started_at_utc"),
            stopped_at_utc=_optional_string(payload.get("stopped_at_utc")),
            stop_reason=_optional_string(payload.get("stop_reason")),
        )


@dataclass(frozen=True)
class TerminalRecordLiveState:
    """Mutable controller state for one recorder run."""

    schema_version: int
    run_id: str
    mode: RecorderMode
    status: RecorderStatus
    repo_root: str
    run_root: str
    manifest_path: str
    controller_pid: int | None
    target_session_name: str
    target_pane_id: str
    stop_requested_at_utc: str | None
    last_error: str | None
    updated_at_utc: str = field(default_factory=lambda: now_utc_iso())

    def to_payload(self) -> dict[str, Any]:
        """Return one JSON-serializable payload."""

        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TerminalRecordLiveState":
        """Parse one live-state payload."""

        return cls(
            schema_version=int(payload.get("schema_version", 0)),
            run_id=_require_string(payload.get("run_id"), context="run_id"),
            mode=_require_mode(payload.get("mode")),
            status=_require_status(payload.get("status")),
            repo_root=_require_string(payload.get("repo_root"), context="repo_root"),
            run_root=_require_string(payload.get("run_root"), context="run_root"),
            manifest_path=_require_string(payload.get("manifest_path"), context="manifest_path"),
            controller_pid=_optional_int(payload.get("controller_pid")),
            target_session_name=_require_string(
                payload.get("target_session_name"),
                context="target_session_name",
            ),
            target_pane_id=_require_string(payload.get("target_pane_id"), context="target_pane_id"),
            stop_requested_at_utc=_optional_string(payload.get("stop_requested_at_utc")),
            last_error=_optional_string(payload.get("last_error")),
            updated_at_utc=_require_string(payload.get("updated_at_utc"), context="updated_at_utc"),
        )


@dataclass(frozen=True)
class TerminalRecordPaneSnapshot:
    """One pane snapshot entry."""

    sample_id: str
    elapsed_seconds: float
    ts_utc: str
    target_pane_id: str
    output_text: str

    def to_payload(self) -> dict[str, Any]:
        """Return one JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class TerminalRecordInputEvent:
    """One normalized recorder input event."""

    event_id: str
    elapsed_seconds: float
    ts_utc: str
    source: InputEventSource
    sequence: str
    escape_special_keys: bool
    tmux_target: str | None

    def to_payload(self) -> dict[str, Any]:
        """Return one JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class TerminalRecordLabel:
    """One persisted label over a recorded sample or range."""

    label_id: str
    scenario_id: str | None
    sample_id: str
    sample_end_id: str | None
    expectations: dict[str, Any]
    note: str | None


@dataclass(frozen=True)
class TerminalRecordLabels:
    """Collection of persisted recorder labels."""

    schema_version: int
    labels: tuple[TerminalRecordLabel, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return one JSON-serializable payload."""

        return {
            "schema_version": self.schema_version,
            "labels": [asdict(label) for label in self.labels],
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TerminalRecordLabels":
        """Parse one labels payload."""

        labels_raw = payload.get("labels", [])
        if not isinstance(labels_raw, list):
            raise ValueError("labels must be a list")
        labels: list[TerminalRecordLabel] = []
        for raw in labels_raw:
            item = _require_mapping(raw, context="labels[]")
            expectations = _require_mapping(item.get("expectations"), context="labels[].expectations")
            labels.append(
                TerminalRecordLabel(
                    label_id=_require_string(item.get("label_id"), context="labels[].label_id"),
                    scenario_id=_optional_string(item.get("scenario_id")),
                    sample_id=_require_string(item.get("sample_id"), context="labels[].sample_id"),
                    sample_end_id=_optional_string(item.get("sample_end_id")),
                    expectations=expectations,
                    note=_optional_string(item.get("note")),
                )
            )
        return cls(
            schema_version=int(payload.get("schema_version", 0)),
            labels=tuple(labels),
        )


def now_utc_iso() -> str:
    """Return current UTC timestamp in ISO format."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def save_manifest(path: Path, manifest: TerminalRecordManifest) -> None:
    """Persist one recorder manifest."""

    _write_json(path, manifest.to_payload())


def load_manifest(path: Path) -> TerminalRecordManifest:
    """Load one recorder manifest."""

    payload = _read_json(path)
    return TerminalRecordManifest.from_payload(payload)


def save_live_state(path: Path, state: TerminalRecordLiveState) -> None:
    """Persist one recorder live-state payload."""

    _write_json(path, state.to_payload())


def load_live_state(path: Path) -> TerminalRecordLiveState:
    """Load one recorder live-state payload."""

    payload = _read_json(path)
    return TerminalRecordLiveState.from_payload(payload)


def save_labels(path: Path, labels: TerminalRecordLabels) -> None:
    """Persist one label collection."""

    _write_json(path, labels.to_payload())


def load_labels(path: Path) -> TerminalRecordLabels:
    """Load one label collection."""

    payload = _read_json(path)
    return TerminalRecordLabels.from_payload(payload)


def append_ndjson(path: Path, payload: dict[str, Any]) -> None:
    """Append one NDJSON payload."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def overwrite_ndjson(path: Path, payloads: list[dict[str, Any]]) -> None:
    """Rewrite one NDJSON file from ordered payloads."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for payload in payloads:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write one JSON payload atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object payload."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in `{path}`.")
    return payload


def _require_mapping(value: Any, *, context: str) -> dict[str, Any]:
    """Return one mapping value or raise."""

    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    return value


def _require_string(value: Any, *, context: str) -> str:
    """Return one non-empty string value or raise."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    """Return one optional non-empty string value."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Optional string field must be a string when present")
    stripped = value.strip()
    return stripped or None


def _optional_int(value: Any) -> int | None:
    """Return one optional integer value."""

    if value is None:
        return None
    return int(value)


def _require_mode(value: Any) -> RecorderMode:
    """Return one validated recorder mode."""

    if value not in {"active", "passive"}:
        raise ValueError(f"Unsupported recorder mode: {value!r}")
    return value


def _require_status(value: Any) -> RecorderStatus:
    """Return one validated recorder status."""

    if value not in {"starting", "running", "stopping", "stopped", "failed"}:
        raise ValueError(f"Unsupported recorder status: {value!r}")
    return value


def _require_visual_recording_kind(value: Any) -> VisualRecordingKind:
    """Return one validated visual recording kind."""

    if value not in {"interactive_client", "readonly_observer"}:
        raise ValueError(f"Unsupported visual recording kind: {value!r}")
    return value


def _require_input_capture_level(value: Any) -> InputCaptureLevel:
    """Return one validated input capture level."""

    if value not in {"authoritative_managed", "managed_only", "output_only"}:
        raise ValueError(f"Unsupported input capture level: {value!r}")
    return value
