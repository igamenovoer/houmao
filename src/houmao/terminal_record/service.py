"""Service layer for tmux-backed terminal recorder runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from houmao.agents.realm_controller.backends.shadow_parser_stack import ShadowParserStack
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    capture_tmux_pane,
    ensure_tmux_available,
    has_tmux_session,
    kill_tmux_session,
    list_tmux_clients,
    resolve_tmux_pane as resolve_tmux_pane_shared,
    run_tmux,
    tmux_error_detail,
)
from houmao.shared_tui_tracking.models import (
    RecordedInputEvent,
    RecordedObservation,
)
from houmao.shared_tui_tracking.reducer import replay_timeline

from .models import (
    DEFAULT_SAMPLE_INTERVAL_SECONDS,
    TERMINAL_RECORD_SCHEMA_VERSION,
    InputCaptureLevel,
    RecorderMode,
    RecorderStatus,
    TerminalRecordInputEvent,
    TerminalRecordLabel,
    TerminalRecordLabels,
    TerminalRecordLiveState,
    TerminalRecordManifest,
    TerminalRecordPaneSnapshot,
    TerminalRecordPaths,
    TerminalRecordTarget,
    InputEventSource,
    VisualRecordingKind,
    append_ndjson,
    load_labels,
    load_live_state,
    load_manifest,
    now_utc_iso,
    overwrite_ndjson,
    save_labels,
    save_live_state,
    save_manifest,
)
from .runtime_bridge import (
    clear_active_terminal_record_session,
    publish_active_terminal_record_session,
)


SUPPORTED_ANALYZE_TOOLS = {"claude", "codex", "kimi"}
SUPPORTED_RECORD_TOOLS = ("claude", "codex", "kimi")
DERIVED_2FPS_SAMPLE_INTERVAL_SECONDS = 0.5
PANE_CAPTURE_COMMAND = "tmux capture-pane -p -e -S -"
OUTPUT_TAG_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
DERIVED_SAMPLING_MODES = ("regular", "jittered", "bursty", "gapped")


class TerminalRecordError(RuntimeError):
    """Raised when terminal recorder operations cannot proceed."""


class TerminalRecordController:
    """Own one recorder run lifecycle."""

    def __init__(self, *, live_state_path: Path) -> None:
        self.m_live_state_path = live_state_path.resolve()
        self.m_live_state = load_live_state(self.m_live_state_path)
        self.m_manifest = load_manifest(Path(self.m_live_state.manifest_path))
        self.m_paths = TerminalRecordPaths.from_run_root(run_root=Path(self.m_manifest.run_root))
        self.m_repo_root = Path(self.m_manifest.repo_root)
        self.m_next_sample_index = _next_snapshot_index(self.m_paths.pane_snapshots_path)
        self.m_duration_elapsed = False

    def run(self) -> int:
        """Run the recorder controller loop."""

        try:
            self._write_live_state(status="running", controller_pid=os.getpid(), last_error=None)
            if self.m_manifest.mode == "active":
                publish_active_terminal_record_session(
                    session_name=self.m_manifest.target.session_name,
                    live_state_path=self.m_live_state_path,
                )
            self._launch_recorder_session()
            self._sampling_loop()
            self._finalize(stop_reason=self._resolve_stop_reason())
        except Exception as exc:  # noqa: BLE001
            self._write_live_state(status="failed", controller_pid=os.getpid(), last_error=str(exc))
            self._update_manifest(
                stopped_at_utc=now_utc_iso(),
                stop_reason=f"failed: {exc}",
            )
            try:
                if self.m_manifest.mode == "active":
                    clear_active_terminal_record_session(
                        session_name=self.m_manifest.target.session_name
                    )
            except TmuxCommandError:
                pass
            return 1
        return 0

    def _sampling_loop(self) -> None:
        """Persist pane snapshots until stop is requested or recorder exits."""

        visual_recording_exited = False
        while True:
            self._capture_snapshot()
            if self._active_mode_has_extra_clients():
                self._taint_run("multiple_clients_attached")
            if self._stop_requested():
                self._write_live_state(
                    status="stopping", controller_pid=os.getpid(), last_error=None
                )
                return
            if self._duration_reached():
                self.m_duration_elapsed = True
                self._write_live_state(
                    status="stopping", controller_pid=os.getpid(), last_error=None
                )
                return
            if self._recorder_session_stopped():
                if not visual_recording_exited:
                    self._taint_run("visual_recording_exited")
                    visual_recording_exited = True
            time.sleep(self.m_manifest.sample_interval_seconds)

    def _launch_recorder_session(self) -> None:
        """Launch the recorder tmux session that owns the `asciinema` command."""

        command = _build_recorder_shell_command(self.m_manifest)
        result = run_tmux(
            [
                "new-session",
                "-d",
                "-s",
                self.m_manifest.recorder_session_name,
                "-c",
                str(self.m_repo_root),
                command,
            ]
        )
        if result.returncode != 0:
            detail = tmux_error_detail(result)
            raise TerminalRecordError(
                f"Failed to launch recorder session `{self.m_manifest.recorder_session_name}`: "
                f"{detail or 'unknown tmux error'}"
            )

    def _capture_snapshot(self) -> None:
        """Capture one pane snapshot and append it to disk."""

        output_text = capture_tmux_pane(target=self.m_manifest.target.pane_id)
        width, height = _target_pane_dimensions(target=self.m_manifest.target.pane_id)
        snapshot = TerminalRecordPaneSnapshot(
            sample_id=f"s{self.m_next_sample_index:06d}",
            elapsed_seconds=_elapsed_seconds(self.m_manifest.started_at_utc),
            ts_utc=now_utc_iso(),
            target_pane_id=self.m_manifest.target.pane_id,
            output_text=output_text,
            target_pane_width=width,
            target_pane_height=height,
            capture_command=PANE_CAPTURE_COMMAND,
            output_text_sha256=hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        )
        append_ndjson(self.m_paths.pane_snapshots_path, snapshot.to_payload())
        self.m_next_sample_index += 1

    def _stop_requested(self) -> bool:
        """Return whether stop has been requested for this run."""

        live_state = load_live_state(self.m_live_state_path)
        self.m_live_state = live_state
        return live_state.stop_requested_at_utc is not None

    def _recorder_session_stopped(self) -> bool:
        """Return whether the recorder tmux session is no longer running."""

        result = has_tmux_session(session_name=self.m_manifest.recorder_session_name)
        return result.returncode != 0

    def _duration_reached(self) -> bool:
        """Return whether the optional capture duration has elapsed."""

        if self.m_manifest.duration_seconds is None:
            return False
        return _elapsed_seconds(self.m_manifest.started_at_utc) >= self.m_manifest.duration_seconds

    def _active_mode_has_extra_clients(self) -> bool:
        """Return whether active mode lost exclusive tmux-client posture."""

        if self.m_manifest.mode != "active":
            return False
        clients = list_tmux_clients(session_name=self.m_manifest.target.session_name)
        return len(clients) > 1

    def _taint_run(self, reason: str) -> None:
        """Record one taint reason and degrade capture level."""

        if reason in self.m_manifest.taint_reasons:
            return
        taint_reasons = tuple((*self.m_manifest.taint_reasons, reason))
        self.m_manifest = TerminalRecordManifest(
            schema_version=self.m_manifest.schema_version,
            run_id=self.m_manifest.run_id,
            mode=self.m_manifest.mode,
            repo_root=self.m_manifest.repo_root,
            run_root=self.m_manifest.run_root,
            target=self.m_manifest.target,
            tool=self.m_manifest.tool,
            sample_interval_seconds=self.m_manifest.sample_interval_seconds,
            visual_recording_kind=self.m_manifest.visual_recording_kind,
            input_capture_level=_degraded_capture_level(self.m_manifest.mode),
            run_tainted=True,
            taint_reasons=taint_reasons,
            recorder_session_name=self.m_manifest.recorder_session_name,
            attach_command=self.m_manifest.attach_command,
            started_at_utc=self.m_manifest.started_at_utc,
            stopped_at_utc=self.m_manifest.stopped_at_utc,
            stop_reason=self.m_manifest.stop_reason,
            duration_seconds=self.m_manifest.duration_seconds,
        )
        save_manifest(self.m_paths.manifest_path, self.m_manifest)

    def _resolve_stop_reason(self) -> str:
        """Return one finalized stop reason."""

        if self.m_live_state.stop_requested_at_utc is not None:
            return "stop_requested"
        if self.m_duration_elapsed:
            return "duration_elapsed"
        return "recorder_session_exited"

    def _finalize(self, *, stop_reason: str) -> None:
        """Finalize recorder artifacts and runtime bridge state."""

        self._capture_snapshot()
        self._stop_recorder_session()
        if self.m_manifest.mode == "active":
            self._merge_cast_input_events()
            clear_active_terminal_record_session(session_name=self.m_manifest.target.session_name)
        self._update_manifest(stopped_at_utc=now_utc_iso(), stop_reason=stop_reason)
        self._write_live_state(status="stopped", controller_pid=os.getpid(), last_error=None)

    def _stop_recorder_session(self) -> None:
        """Stop the recorder tmux session with a grace period."""

        result = has_tmux_session(session_name=self.m_manifest.recorder_session_name)
        if result.returncode != 0:
            return
        run_tmux(["send-keys", "-t", self.m_manifest.recorder_session_name, "C-c"])
        time.sleep(0.2)
        result = has_tmux_session(session_name=self.m_manifest.recorder_session_name)
        if result.returncode == 0:
            kill_tmux_session(session_name=self.m_manifest.recorder_session_name)

    def _merge_cast_input_events(self) -> None:
        """Append normalized `asciinema` input events after the recorder stops."""

        if not self.m_paths.cast_path.is_file():
            return
        manual_events = parse_asciinema_cast_input_events(
            cast_path=self.m_paths.cast_path,
            started_at_utc=self.m_manifest.started_at_utc,
        )
        existing_events = _load_input_events(self.m_paths.input_events_path)
        existing_events.extend(manual_events)
        existing_events.sort(key=lambda item: (item.elapsed_seconds, item.event_id))
        for index, item in enumerate(existing_events, start=1):
            existing_events[index - 1] = TerminalRecordInputEvent(
                event_id=f"i{index:06d}",
                elapsed_seconds=item.elapsed_seconds,
                ts_utc=item.ts_utc,
                source=item.source,
                sequence=item.sequence,
                escape_special_keys=item.escape_special_keys,
                tmux_target=item.tmux_target,
            )
        overwrite_ndjson(
            self.m_paths.input_events_path,
            [item.to_payload() for item in existing_events],
        )

    def _update_manifest(self, *, stopped_at_utc: str, stop_reason: str) -> None:
        """Persist final manifest state."""

        self.m_manifest = TerminalRecordManifest(
            schema_version=self.m_manifest.schema_version,
            run_id=self.m_manifest.run_id,
            mode=self.m_manifest.mode,
            repo_root=self.m_manifest.repo_root,
            run_root=self.m_manifest.run_root,
            target=self.m_manifest.target,
            tool=self.m_manifest.tool,
            sample_interval_seconds=self.m_manifest.sample_interval_seconds,
            visual_recording_kind=self.m_manifest.visual_recording_kind,
            input_capture_level=self.m_manifest.input_capture_level,
            run_tainted=self.m_manifest.run_tainted,
            taint_reasons=self.m_manifest.taint_reasons,
            recorder_session_name=self.m_manifest.recorder_session_name,
            attach_command=self.m_manifest.attach_command,
            started_at_utc=self.m_manifest.started_at_utc,
            stopped_at_utc=stopped_at_utc,
            stop_reason=stop_reason,
            duration_seconds=self.m_manifest.duration_seconds,
        )
        save_manifest(self.m_paths.manifest_path, self.m_manifest)

    def _write_live_state(
        self,
        *,
        status: RecorderStatus,
        controller_pid: int | None,
        last_error: str | None,
    ) -> None:
        """Persist one live-state update."""

        state = TerminalRecordLiveState(
            schema_version=TERMINAL_RECORD_SCHEMA_VERSION,
            run_id=self.m_live_state.run_id,
            mode=self.m_live_state.mode,
            status=status,
            repo_root=self.m_live_state.repo_root,
            run_root=self.m_live_state.run_root,
            manifest_path=self.m_live_state.manifest_path,
            controller_pid=controller_pid,
            target_session_name=self.m_live_state.target_session_name,
            target_pane_id=self.m_live_state.target_pane_id,
            stop_requested_at_utc=self.m_live_state.stop_requested_at_utc,
            last_error=last_error,
            updated_at_utc=now_utc_iso(),
        )
        self.m_live_state = state
        save_live_state(self.m_live_state_path, state)


def start_terminal_record(
    *,
    mode: RecorderMode,
    target_session: str,
    target_pane: str | None,
    tool: str | None,
    run_root: Path | None,
    sample_interval_seconds: float,
    duration_seconds: float | None = None,
) -> dict[str, Any]:
    """Start one terminal recorder controller process."""

    ensure_tmux_available()
    if sample_interval_seconds <= 0:
        raise TerminalRecordError("sample_interval_seconds must be positive")
    if duration_seconds is not None and duration_seconds <= 0:
        raise TerminalRecordError("duration_seconds must be positive when provided")
    target = resolve_terminal_record_target(
        target_session=target_session,
        target_pane=target_pane,
    )
    repo_root = _repo_root()
    selected_run_root = (
        run_root.resolve()
        if run_root is not None
        else _default_run_root(repo_root=repo_root, target_session=target.session_name)
    )
    if selected_run_root.exists():
        raise TerminalRecordError(f"Run root already exists: {selected_run_root}")
    paths = TerminalRecordPaths.from_run_root(run_root=selected_run_root)
    attach_command = None
    recorder_session_name = _recorder_session_name(run_id=selected_run_root.name)
    if mode == "active":
        attach_command = f"env -u TMUX tmux attach-session -t {recorder_session_name}"
    visual_recording_kind: VisualRecordingKind = (
        "interactive_client" if mode == "active" else "readonly_observer"
    )
    input_capture_level: InputCaptureLevel = (
        "authoritative_managed" if mode == "active" else "output_only"
    )
    manifest = TerminalRecordManifest(
        schema_version=TERMINAL_RECORD_SCHEMA_VERSION,
        run_id=selected_run_root.name,
        mode=mode,
        repo_root=str(repo_root),
        run_root=str(selected_run_root),
        target=target,
        tool=tool,
        sample_interval_seconds=sample_interval_seconds,
        visual_recording_kind=visual_recording_kind,
        input_capture_level=input_capture_level,
        run_tainted=False,
        taint_reasons=(),
        recorder_session_name=recorder_session_name,
        attach_command=attach_command,
        started_at_utc=now_utc_iso(),
        stopped_at_utc=None,
        stop_reason=None,
        duration_seconds=duration_seconds,
    )
    live_state = TerminalRecordLiveState(
        schema_version=TERMINAL_RECORD_SCHEMA_VERSION,
        run_id=manifest.run_id,
        mode=mode,
        status="starting",
        repo_root=str(repo_root),
        run_root=str(selected_run_root),
        manifest_path=str(paths.manifest_path),
        controller_pid=None,
        target_session_name=target.session_name,
        target_pane_id=target.pane_id,
        stop_requested_at_utc=None,
        last_error=None,
    )
    save_manifest(paths.manifest_path, manifest)
    save_live_state(paths.live_state_path, live_state)
    paths.run_root.mkdir(parents=True, exist_ok=True)

    with paths.controller_log_path.open("a", encoding="utf-8") as handle:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "houmao.terminal_record.cli",
                "_controller-run",
                "--live-state-path",
                str(paths.live_state_path),
            ],
            cwd=repo_root,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
        )
    _wait_for_controller(paths.live_state_path)
    current_state = load_live_state(paths.live_state_path)
    if current_state.status == "failed":
        raise TerminalRecordError(current_state.last_error or "recorder controller failed")
    return {
        "run_id": manifest.run_id,
        "mode": manifest.mode,
        "target_session": manifest.target.session_name,
        "target_pane": manifest.target.pane_id,
        "run_root": str(paths.run_root),
        "status": current_state.status,
        "attach_command": manifest.attach_command,
        "controller_pid": process.pid,
    }


def status_terminal_record(*, run_root: Path) -> dict[str, Any]:
    """Return status for one recorder run."""

    paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    live_state = load_live_state(paths.live_state_path)
    manifest = load_manifest(paths.manifest_path)
    is_alive = False
    if live_state.controller_pid is not None:
        try:
            os.kill(live_state.controller_pid, 0)
        except OSError:
            is_alive = False
        else:
            is_alive = True
    return {
        "run_id": manifest.run_id,
        "mode": manifest.mode,
        "status": live_state.status,
        "controller_pid": live_state.controller_pid,
        "controller_alive": is_alive,
        "target_session": manifest.target.session_name,
        "target_pane": manifest.target.pane_id,
        "run_root": manifest.run_root,
        "attach_command": manifest.attach_command,
        "input_capture_level": manifest.input_capture_level,
        "run_tainted": manifest.run_tainted,
        "taint_reasons": list(manifest.taint_reasons),
    }


def stop_terminal_record(*, run_root: Path) -> dict[str, Any]:
    """Request stop for one recorder run."""

    paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    live_state = load_live_state(paths.live_state_path)
    if live_state.status in {"stopped", "failed"}:
        return {
            "run_id": live_state.run_id,
            "status": live_state.status,
            "already_finalized": True,
        }
    requested = TerminalRecordLiveState(
        schema_version=live_state.schema_version,
        run_id=live_state.run_id,
        mode=live_state.mode,
        status=live_state.status,
        repo_root=live_state.repo_root,
        run_root=live_state.run_root,
        manifest_path=live_state.manifest_path,
        controller_pid=live_state.controller_pid,
        target_session_name=live_state.target_session_name,
        target_pane_id=live_state.target_pane_id,
        stop_requested_at_utc=now_utc_iso(),
        last_error=live_state.last_error,
    )
    save_live_state(paths.live_state_path, requested)
    _wait_for_final_status(paths.live_state_path)
    finalized = load_live_state(paths.live_state_path)
    manifest = load_manifest(paths.manifest_path)
    return {
        "run_id": finalized.run_id,
        "status": finalized.status,
        "run_root": manifest.run_root,
        "stopped_at_utc": manifest.stopped_at_utc,
        "stop_reason": manifest.stop_reason,
    }


def analyze_terminal_record(
    *,
    run_root: Path,
    tool: str | None,
    observed_version: str | None = None,
    detector_version_override: str | None = None,
    snapshots_path: Path | None = None,
    output_tag: str | None = None,
) -> dict[str, Any]:
    """Derive parser and state observations from one recorder run."""

    paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    manifest = load_manifest(paths.manifest_path)
    selected_tool = tool or manifest.tool
    if selected_tool not in SUPPORTED_ANALYZE_TOOLS:
        raise TerminalRecordError(
            "analyze requires recorder manifest tool to be one of `claude`, `codex`, or `kimi`, "
            "or an explicit --tool override."
        )

    parser_stack = None if selected_tool == "kimi" else ShadowParserStack(tool=selected_tool)
    selected_snapshots_path = (
        snapshots_path.resolve() if snapshots_path is not None else paths.pane_snapshots_path
    )
    parser_observed_path, state_observed_path = _observed_output_paths(
        paths=paths, output_tag=output_tag
    )
    parser_payloads: list[dict[str, Any]] = []
    observations: list[RecordedObservation] = []
    parser_payload_by_sample_id: dict[str, dict[str, Any]] = {}
    source_sample_by_sample_id: dict[str, str | None] = {}
    for snapshot in _load_snapshots(selected_snapshots_path):
        if parser_stack is None:
            parser_payload = _parse_kimi_snapshot_payload(snapshot)
        else:
            parsed = parser_stack.parse_snapshot(
                snapshot.output_text,
                baseline_pos=0,
            )
            assessment = parsed.surface_assessment
            projection = parsed.dialog_projection
            parser_payload = {
                "sample_id": snapshot.sample_id,
                "elapsed_seconds": snapshot.elapsed_seconds,
                "source_sample_id": snapshot.source_sample_id,
                "availability": assessment.availability,
                "business_state": assessment.business_state,
                "input_mode": assessment.input_mode,
                "ui_context": assessment.ui_context,
                "parser_preset_id": assessment.parser_metadata.parser_preset_id,
                "parser_preset_version": assessment.parser_metadata.parser_preset_version,
                "baseline_invalidated": assessment.parser_metadata.baseline_invalidated,
                "anomaly_codes": [
                    anomaly.code
                    for anomaly in (
                        *assessment.parser_metadata.anomalies,
                        *assessment.anomalies,
                        *projection.anomalies,
                    )
                ],
                "dialog_tail": projection.tail,
                "normalized_text": projection.normalized_text,
            }
        parser_payloads.append(parser_payload)
        parser_payload_by_sample_id[snapshot.sample_id] = parser_payload
        source_sample_by_sample_id[snapshot.sample_id] = snapshot.source_sample_id
        observations.append(
            RecordedObservation(
                sample_id=snapshot.sample_id,
                elapsed_seconds=snapshot.elapsed_seconds,
                ts_utc=snapshot.ts_utc,
                output_text=snapshot.output_text,
                runtime=None,
            )
        )
    input_events = [
        RecordedInputEvent(
            event_id=item.event_id,
            elapsed_seconds=item.elapsed_seconds,
            ts_utc=item.ts_utc,
            source=item.source,
        )
        for item in _load_input_events(paths.input_events_path)
    ]
    replay_timeline_rows, _ = replay_timeline(
        observations=observations,
        tool=selected_tool,
        observed_version=observed_version,
        settle_seconds=1.0,
        input_events=input_events,
        detector_version_override=detector_version_override,
    )
    state_payloads: list[dict[str, Any]] = []
    for item in replay_timeline_rows:
        parser_payload = parser_payload_by_sample_id[item.sample_id]
        state_payloads.append(
            {
                "sample_id": item.sample_id,
                "elapsed_seconds": item.elapsed_seconds,
                "source_sample_id": source_sample_by_sample_id.get(item.sample_id),
                "diagnostics_availability": item.diagnostics_availability,
                "surface_accepting_input": item.surface_accepting_input,
                "surface_editing_input": item.surface_editing_input,
                "surface_ready_posture": item.surface_ready_posture,
                "turn_phase": item.turn_phase,
                "last_turn_result": item.last_turn_result,
                "last_turn_source": item.last_turn_source,
                "detector_name": item.detector_name,
                "detector_version": item.detector_version,
                "business_state": parser_payload["business_state"],
                "input_mode": parser_payload["input_mode"],
                "ui_context": parser_payload["ui_context"],
                "baseline_invalidated": parser_payload["baseline_invalidated"],
                "anomaly_codes": parser_payload["anomaly_codes"],
                "readiness_state": _debug_readiness_state_from_parser(
                    business_state=parser_payload["business_state"],
                    input_mode=parser_payload["input_mode"],
                    ui_context=parser_payload["ui_context"],
                ),
                "completion_state": _debug_completion_state_from_parser(
                    business_state=parser_payload["business_state"],
                    input_mode=parser_payload["input_mode"],
                    ui_context=parser_payload["ui_context"],
                ),
            }
        )

    overwrite_ndjson(parser_observed_path, parser_payloads)
    overwrite_ndjson(state_observed_path, state_payloads)
    return {
        "run_id": manifest.run_id,
        "tool": selected_tool,
        "snapshots_path": str(selected_snapshots_path),
        "parser_observed_path": str(parser_observed_path),
        "state_observed_path": str(state_observed_path),
        "sample_count": len(parser_payloads),
    }


def derive_terminal_record_stream(
    *,
    run_root: Path,
    source_path: Path | None = None,
    output_path: Path | None = None,
    target_sample_interval_seconds: float = DERIVED_2FPS_SAMPLE_INTERVAL_SECONDS,
    sampling_mode: str = "regular",
    phase_offset_seconds: float = 0.0,
    seed: int = 0,
) -> dict[str, Any]:
    """Derive one low-rate snapshot stream from a high-rate source stream."""

    if target_sample_interval_seconds <= 0:
        raise TerminalRecordError("target_sample_interval_seconds must be positive")
    if sampling_mode not in DERIVED_SAMPLING_MODES:
        raise TerminalRecordError(
            f"sampling_mode must be one of {', '.join(DERIVED_SAMPLING_MODES)}"
        )
    paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    selected_source = (
        source_path.resolve() if source_path is not None else paths.pane_snapshots_path
    )
    selected_output = (
        output_path.resolve() if output_path is not None else paths.derived_2fps_snapshots_path
    )
    source_snapshots = _load_snapshots(selected_source)
    if not source_snapshots:
        raise TerminalRecordError(f"No source snapshots found in `{selected_source}`.")

    first_elapsed = source_snapshots[0].elapsed_seconds
    last_elapsed = source_snapshots[-1].elapsed_seconds
    selected_snapshots: list[TerminalRecordPaneSnapshot] = []
    boundaries = _derived_sample_boundaries(
        first_elapsed=first_elapsed,
        last_elapsed=last_elapsed,
        interval_seconds=target_sample_interval_seconds,
        sampling_mode=sampling_mode,
        phase_offset_seconds=phase_offset_seconds,
        seed=seed,
    )
    last_source_id: str | None = None
    for boundary in boundaries:
        nearest = min(source_snapshots, key=lambda item: abs(item.elapsed_seconds - boundary))
        if nearest.sample_id != last_source_id:
            selected_snapshots.append(nearest)
            last_source_id = nearest.sample_id

    derived: list[TerminalRecordPaneSnapshot] = []
    for index, source in enumerate(selected_snapshots, start=1):
        derived.append(
            TerminalRecordPaneSnapshot(
                sample_id=f"d{index:06d}",
                elapsed_seconds=source.elapsed_seconds,
                ts_utc=source.ts_utc,
                target_pane_id=source.target_pane_id,
                output_text=source.output_text,
                target_pane_width=source.target_pane_width,
                target_pane_height=source.target_pane_height,
                capture_command=source.capture_command,
                stream_kind="derived",
                source_sample_id=source.source_sample_id or source.sample_id,
                source_elapsed_seconds=source.source_elapsed_seconds or source.elapsed_seconds,
                output_text_sha256=source.output_text_sha256,
            )
        )
    overwrite_ndjson(selected_output, [item.to_payload() for item in derived])
    return {
        "run_root": str(paths.run_root),
        "source_path": str(selected_source),
        "output_path": str(selected_output),
        "target_sample_interval_seconds": target_sample_interval_seconds,
        "sampling_mode": sampling_mode,
        "phase_offset_seconds": phase_offset_seconds,
        "seed": seed,
        "source_sample_count": len(source_snapshots),
        "derived_sample_count": len(derived),
    }


def _derived_sample_boundaries(
    *,
    first_elapsed: float,
    last_elapsed: float,
    interval_seconds: float,
    sampling_mode: str,
    phase_offset_seconds: float = 0.0,
    seed: int = 0,
) -> tuple[float, ...]:
    """Return deterministic source-time targets for one derived capture schedule."""

    from houmao.terminal_record.schedules import derive_schedule_boundaries

    return derive_schedule_boundaries(
        first_elapsed=first_elapsed,
        last_elapsed=last_elapsed,
        interval_seconds=interval_seconds,
        sampling_mode=cast(Any, sampling_mode),
        phase_offset_seconds=phase_offset_seconds,
        seed=seed,
    )


def validate_terminal_record(
    *,
    run_root: Path,
    labels_path: Path | None = None,
    state_path: Path | None = None,
    parser_path: Path | None = None,
) -> dict[str, Any]:
    """Compare observed parser/tracker output against structured labels."""

    paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    selected_labels_path = labels_path.resolve() if labels_path is not None else paths.labels_path
    selected_state_path = (
        state_path.resolve() if state_path is not None else paths.state_observed_path
    )
    selected_parser_path = (
        parser_path.resolve() if parser_path is not None else paths.parser_observed_path
    )
    if not selected_labels_path.is_file():
        raise TerminalRecordError(f"Labels file does not exist: {selected_labels_path}")
    if not selected_state_path.is_file():
        raise TerminalRecordError(f"State observation file does not exist: {selected_state_path}")

    labels = load_labels(selected_labels_path)
    state_rows = _load_ndjson_payloads(selected_state_path)
    parser_rows = _load_ndjson_payloads(selected_parser_path)
    parser_by_sample_id = {
        str(item["sample_id"]): item for item in parser_rows if "sample_id" in item
    }
    sample_order = _sample_order_from_rows(state_rows)
    failures: list[dict[str, Any]] = []
    checked = 0

    for label in labels.labels:
        matching_rows = _rows_for_label(label=label, rows=state_rows, sample_order=sample_order)
        if not matching_rows:
            failures.append(
                {
                    "label_id": label.label_id,
                    "sample_id": label.sample_id,
                    "sample_end_id": label.sample_end_id,
                    "error": "no_observed_rows_for_label",
                }
            )
            continue
        for row in matching_rows:
            checked += 1
            merged = dict(row)
            parser_payload = parser_by_sample_id.get(str(row.get("sample_id")))
            if parser_payload is not None:
                for key, value in parser_payload.items():
                    merged.setdefault(key, value)
            for key, expected in label.expectations.items():
                actual = merged.get(key)
                if actual == expected:
                    continue
                failures.append(
                    {
                        "label_id": label.label_id,
                        "sample_id": row.get("sample_id"),
                        "source_sample_id": row.get("source_sample_id"),
                        "field": key,
                        "expected": expected,
                        "actual": actual,
                    }
                )

    return {
        "run_root": str(paths.run_root),
        "labels_path": str(selected_labels_path),
        "state_path": str(selected_state_path),
        "parser_path": str(selected_parser_path),
        "label_count": len(labels.labels),
        "checked_sample_count": checked,
        "failure_count": len(failures),
        "passed": not failures,
        "failures": failures,
    }


def add_terminal_record_label(
    *,
    run_root: Path,
    output_dir: Path | None,
    label_id: str,
    sample_id: str,
    sample_end_id: str | None,
    scenario_id: str | None,
    expectations: dict[str, Any],
    note: str | None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append or replace one structured recorder label."""

    paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    destination = (
        TerminalRecordPaths.from_run_root(run_root=output_dir).labels_path
        if output_dir is not None
        else paths.labels_path
    )
    if destination.is_file():
        labels = load_labels(destination)
        current = list(labels.labels)
    else:
        current = []
    filtered = [item for item in current if item.label_id != label_id]
    filtered.append(
        TerminalRecordLabel(
            label_id=label_id,
            scenario_id=scenario_id,
            sample_id=sample_id,
            sample_end_id=sample_end_id,
            expectations=expectations,
            note=note,
            evidence=evidence or {},
        )
    )
    save_labels(
        destination,
        TerminalRecordLabels(
            schema_version=TERMINAL_RECORD_SCHEMA_VERSION,
            labels=tuple(filtered),
        ),
    )
    return {
        "label_id": label_id,
        "output_path": str(destination),
        "label_count": len(filtered),
    }


def resolve_terminal_record_target(
    *,
    target_session: str,
    target_pane: str | None,
) -> TerminalRecordTarget:
    """Resolve one tmux recorder target from session and optional pane."""

    result = has_tmux_session(session_name=target_session)
    if result.returncode != 0:
        raise TerminalRecordError(f"Target tmux session does not exist: {target_session}")
    try:
        pane = resolve_tmux_pane_shared(session_name=target_session, pane_id=target_pane)
    except TmuxCommandError as exc:
        detail = str(exc)
        if target_pane is None and "Ambiguous tmux pane target" in detail:
            raise TerminalRecordError(
                f"Target session `{target_session}` has multiple panes; provide --target-pane."
            ) from exc
        if target_pane is not None and f"pane id `{target_pane}`" in detail:
            raise TerminalRecordError(
                f"Target pane `{target_pane}` was not found in session `{target_session}`."
            ) from exc
        raise TerminalRecordError(detail) from exc
    return TerminalRecordTarget(
        session_name=pane.session_name,
        pane_id=pane.pane_id,
        window_id=pane.window_id,
        window_name=pane.window_name,
    )


def parse_asciinema_cast_input_events(
    *,
    cast_path: Path,
    started_at_utc: str,
) -> list[TerminalRecordInputEvent]:
    """Return normalized input events parsed from one `asciinema` cast."""

    events: list[TerminalRecordInputEvent] = []
    started_at = datetime.fromisoformat(started_at_utc)
    with cast_path.open("r", encoding="utf-8") as handle:
        next(handle, None)
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, list) or len(payload) != 3:
                continue
            elapsed, event_kind, data = payload
            if event_kind != "i" or not isinstance(data, str):
                continue
            elapsed_seconds = float(elapsed)
            ts_value = (started_at + _duration_from_seconds(elapsed_seconds)).isoformat(
                timespec="seconds"
            )
            events.append(
                TerminalRecordInputEvent(
                    event_id=f"i{len(events) + 1:06d}",
                    elapsed_seconds=elapsed_seconds,
                    ts_utc=ts_value,
                    source="asciinema_input",
                    sequence=data,
                    escape_special_keys=False,
                    tmux_target=None,
                )
            )
    return events


def _build_parser() -> argparse.ArgumentParser:
    """Build the terminal-record CLI parser."""

    parser = argparse.ArgumentParser(description="Record and replay tmux-backed terminal sessions.")
    subparsers = parser.add_subparsers(dest="command")

    start = subparsers.add_parser("start", help="Start one recorder run")
    start.add_argument("--mode", choices=["active", "passive"], required=True)
    start.add_argument("--target-session", required=True)
    start.add_argument("--target-pane", default=None)
    start.add_argument("--tool", choices=SUPPORTED_RECORD_TOOLS, default=None)
    start.add_argument("--run-root", type=Path, default=None)
    start.add_argument(
        "--sample-interval-seconds",
        type=float,
        default=DEFAULT_SAMPLE_INTERVAL_SECONDS,
    )
    start.add_argument("--duration-seconds", type=float, default=None)

    status = subparsers.add_parser("status", help="Inspect one recorder run")
    status.add_argument("--run-root", type=Path, required=True)

    stop = subparsers.add_parser("stop", help="Stop one recorder run")
    stop.add_argument("--run-root", type=Path, required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze one recorder run")
    analyze.add_argument("--run-root", type=Path, required=True)
    analyze.add_argument("--tool", choices=SUPPORTED_RECORD_TOOLS, default=None)
    analyze.add_argument("--observed-version", default=None)
    analyze.add_argument("--detector-version-override", default=None)
    analyze.add_argument("--snapshots-path", type=Path, default=None)
    analyze.add_argument("--output-tag", default=None)

    derive_stream = subparsers.add_parser(
        "derive-stream",
        help="Derive a low-rate snapshot stream from a high-rate recorder stream",
    )
    derive_stream.add_argument("--run-root", type=Path, required=True)
    derive_stream.add_argument("--source-path", type=Path, default=None)
    derive_stream.add_argument("--output-path", type=Path, default=None)
    derive_stream.add_argument(
        "--target-sample-interval-seconds",
        type=float,
        default=DERIVED_2FPS_SAMPLE_INTERVAL_SECONDS,
    )
    derive_stream.add_argument("--sampling-mode", choices=DERIVED_SAMPLING_MODES, default="regular")
    derive_stream.add_argument("--phase-offset-seconds", type=float, default=0.0)
    derive_stream.add_argument("--seed", type=int, default=0)

    validate = subparsers.add_parser("validate", help="Validate observations against labels")
    validate.add_argument("--run-root", type=Path, required=True)
    validate.add_argument("--labels-path", type=Path, default=None)
    validate.add_argument("--state-path", type=Path, default=None)
    validate.add_argument("--parser-path", type=Path, default=None)

    add_label = subparsers.add_parser("add-label", help="Persist one structured recorder label")
    add_label.add_argument("--run-root", type=Path, required=True)
    add_label.add_argument("--output-dir", type=Path, default=None)
    add_label.add_argument("--label-id", required=True)
    add_label.add_argument("--scenario-id", default=None)
    add_label.add_argument("--sample-id", required=True)
    add_label.add_argument("--sample-end-id", default=None)
    add_label.add_argument("--business-state", default=None)
    add_label.add_argument("--input-mode", default=None)
    add_label.add_argument("--ui-context", default=None)
    add_label.add_argument("--diagnostics-availability", default=None)
    add_label.add_argument("--surface-accepting-input", default=None)
    add_label.add_argument("--surface-editing-input", default=None)
    add_label.add_argument("--surface-ready-posture", default=None)
    add_label.add_argument("--turn-phase", default=None)
    add_label.add_argument("--last-turn-result", default=None)
    add_label.add_argument("--last-turn-source", default=None)
    add_label.add_argument("--readiness-state", default=None)
    add_label.add_argument("--completion-state", default=None)
    add_label.add_argument("--note", default=None)
    add_label.add_argument("--evidence-note", action="append", default=[])
    add_label.add_argument("--evidence-json", default=None)

    controller = subparsers.add_parser("_controller-run")
    controller.add_argument("--live-state-path", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the terminal-record CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    try:
        if args.command == "start":
            payload = start_terminal_record(
                mode=args.mode,
                target_session=str(args.target_session),
                target_pane=str(args.target_pane) if args.target_pane is not None else None,
                tool=str(args.tool) if args.tool is not None else None,
                run_root=args.run_root,
                sample_interval_seconds=float(args.sample_interval_seconds),
                duration_seconds=(
                    float(args.duration_seconds) if args.duration_seconds is not None else None
                ),
            )
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if args.command == "status":
            print(
                json.dumps(status_terminal_record(run_root=args.run_root), indent=2, sort_keys=True)
            )
            return 0
        if args.command == "stop":
            print(
                json.dumps(stop_terminal_record(run_root=args.run_root), indent=2, sort_keys=True)
            )
            return 0
        if args.command == "analyze":
            print(
                json.dumps(
                    analyze_terminal_record(
                        run_root=args.run_root,
                        tool=args.tool,
                        observed_version=args.observed_version,
                        detector_version_override=args.detector_version_override,
                        snapshots_path=args.snapshots_path,
                        output_tag=args.output_tag,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "derive-stream":
            print(
                json.dumps(
                    derive_terminal_record_stream(
                        run_root=args.run_root,
                        source_path=args.source_path,
                        output_path=args.output_path,
                        target_sample_interval_seconds=float(args.target_sample_interval_seconds),
                        sampling_mode=str(args.sampling_mode),
                        phase_offset_seconds=float(args.phase_offset_seconds),
                        seed=int(args.seed),
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "validate":
            print(
                json.dumps(
                    validate_terminal_record(
                        run_root=args.run_root,
                        labels_path=args.labels_path,
                        state_path=args.state_path,
                        parser_path=args.parser_path,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "add-label":
            expectations = {
                key: value
                for key, value in {
                    "business_state": args.business_state,
                    "input_mode": args.input_mode,
                    "ui_context": args.ui_context,
                    "diagnostics_availability": args.diagnostics_availability,
                    "surface_accepting_input": args.surface_accepting_input,
                    "surface_editing_input": args.surface_editing_input,
                    "surface_ready_posture": args.surface_ready_posture,
                    "turn_phase": args.turn_phase,
                    "last_turn_result": args.last_turn_result,
                    "last_turn_source": args.last_turn_source,
                    "readiness_state": args.readiness_state,
                    "completion_state": args.completion_state,
                }.items()
                if value is not None
            }
            print(
                json.dumps(
                    add_terminal_record_label(
                        run_root=args.run_root,
                        output_dir=args.output_dir,
                        label_id=str(args.label_id),
                        sample_id=str(args.sample_id),
                        sample_end_id=str(args.sample_end_id)
                        if args.sample_end_id is not None
                        else None,
                        scenario_id=str(args.scenario_id) if args.scenario_id is not None else None,
                        expectations=expectations,
                        note=str(args.note) if args.note is not None else None,
                        evidence=_build_label_evidence(
                            evidence_json=args.evidence_json,
                            evidence_notes=tuple(str(item) for item in args.evidence_note),
                        ),
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "_controller-run":
            controller = TerminalRecordController(live_state_path=args.live_state_path)
            return controller.run()
    except (TerminalRecordError, TmuxCommandError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    parser.print_help()
    return 1


def _repo_root() -> Path:
    """Return the repository root from this module location."""

    return Path(__file__).resolve().parents[3]


def _parse_kimi_snapshot_payload(snapshot: TerminalRecordPaneSnapshot) -> dict[str, Any]:
    """Return parser-facing Kimi observations for one recorded snapshot."""

    from houmao.shared_tui_tracking.apps.kimi_code.profile import analyze_kimi_surface

    analysis = analyze_kimi_surface(snapshot.output_text)
    if analysis.approval_visible:
        business_state = "awaiting_operator"
        input_mode = "modal"
        ui_context = "approval"
    elif analysis.activity_visible:
        business_state = "working"
        input_mode = "none"
        ui_context = "normal_prompt"
    elif analysis.prompt.prompt_visible:
        business_state = "idle"
        input_mode = "freeform"
        ui_context = "normal_prompt"
    else:
        business_state = "unknown"
        input_mode = "unknown"
        ui_context = "unknown"

    return {
        "sample_id": snapshot.sample_id,
        "elapsed_seconds": snapshot.elapsed_seconds,
        "source_sample_id": snapshot.source_sample_id,
        "availability": "available",
        "business_state": business_state,
        "input_mode": input_mode,
        "ui_context": ui_context,
        "parser_preset_id": "kimi_code_tui_recorded",
        "parser_preset_version": "0.1",
        "baseline_invalidated": False,
        "anomaly_codes": [],
        "dialog_tail": None,
        "normalized_text": "\n".join(snapshot.output_text.splitlines()[-40:]),
        "approval_header": analysis.approval_header,
        "approval_choice_count": analysis.approval_choice_count,
        "prompt_style": analysis.prompt.prompt_style,
        "prompt_text": analysis.prompt.prompt_text,
        "footer_model_thinking": analysis.footer_model_thinking,
        "notes": list(analysis.notes),
    }


def _observed_output_paths(
    *,
    paths: TerminalRecordPaths,
    output_tag: str | None,
) -> tuple[Path, Path]:
    """Return parser/state output paths for one optional stream tag."""

    if output_tag is None:
        return paths.parser_observed_path, paths.state_observed_path
    if OUTPUT_TAG_RE.match(output_tag) is None:
        raise TerminalRecordError("output_tag may only contain letters, digits, `_`, `.`, or `-`")
    return (
        paths.run_root / f"parser_observed_{output_tag}.ndjson",
        paths.run_root / f"state_observed_{output_tag}.ndjson",
    )


def _target_pane_dimensions(*, target: str) -> tuple[int | None, int | None]:
    """Return target pane dimensions when tmux can report them."""

    try:
        result = run_tmux(["display-message", "-p", "-t", target, "#{pane_width} #{pane_height}"])
    except TmuxCommandError:
        return None, None
    if result.returncode != 0:
        return None, None
    parts = result.stdout.strip().split()
    if len(parts) != 2:
        return None, None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None


def _next_snapshot_index(path: Path) -> int:
    """Return the next source snapshot index for one NDJSON stream."""

    if not path.is_file():
        return 1
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()) + 1


def _load_ndjson_payloads(path: Path) -> list[dict[str, Any]]:
    """Load one NDJSON object stream."""

    if not path.is_file():
        return []
    payloads: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"Expected object row in `{path}`.")
            payloads.append(payload)
    return payloads


def _sample_order_from_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Return sample/source-sample order from observed rows."""

    order: dict[str, int] = {}
    for index, row in enumerate(rows):
        sample_id = row.get("sample_id")
        if isinstance(sample_id, str):
            order.setdefault(sample_id, index)
        source_sample_id = row.get("source_sample_id")
        if isinstance(source_sample_id, str):
            order.setdefault(source_sample_id, index)
    return order


def _rows_for_label(
    *,
    label: TerminalRecordLabel,
    rows: list[dict[str, Any]],
    sample_order: dict[str, int],
) -> list[dict[str, Any]]:
    """Return observed rows covered by one sample/range label."""

    return [
        row for row in rows if _row_matches_label(label=label, row=row, sample_order=sample_order)
    ]


def _row_matches_label(
    *,
    label: TerminalRecordLabel,
    row: dict[str, Any],
    sample_order: dict[str, int],
) -> bool:
    """Return whether one observed row falls inside a label range."""

    for key in ("sample_id", "source_sample_id"):
        sample_id = row.get(key)
        if isinstance(sample_id, str) and _sample_id_in_label_range(
            sample_id=sample_id,
            label=label,
            sample_order=sample_order,
        ):
            return True
    return False


def _sample_id_in_label_range(
    *,
    sample_id: str,
    label: TerminalRecordLabel,
    sample_order: dict[str, int],
) -> bool:
    """Return whether one sample id is inside a label's inclusive range."""

    if sample_id == label.sample_id:
        return True
    if label.sample_end_id is None:
        return False
    start = sample_order.get(label.sample_id)
    end = sample_order.get(label.sample_end_id)
    current = sample_order.get(sample_id)
    if start is None or end is None or current is None:
        return _sample_id_in_numeric_range(
            sample_id=sample_id,
            start_sample_id=label.sample_id,
            end_sample_id=label.sample_end_id,
        )
    lower = min(start, end)
    upper = max(start, end)
    return lower <= current <= upper


def _sample_id_in_numeric_range(
    *,
    sample_id: str,
    start_sample_id: str,
    end_sample_id: str,
) -> bool:
    """Return whether one sample id falls between two same-prefix ids."""

    parsed_current = _parse_sample_id(sample_id)
    parsed_start = _parse_sample_id(start_sample_id)
    parsed_end = _parse_sample_id(end_sample_id)
    if parsed_current is None or parsed_start is None or parsed_end is None:
        return False
    current_prefix, current_number = parsed_current
    start_prefix, start_number = parsed_start
    end_prefix, end_number = parsed_end
    if current_prefix != start_prefix or current_prefix != end_prefix:
        return False
    lower = min(start_number, end_number)
    upper = max(start_number, end_number)
    return lower <= current_number <= upper


def _parse_sample_id(sample_id: str) -> tuple[str, int] | None:
    """Parse one sample identifier such as `s000001` or `d000001`."""

    match = re.match(r"^([A-Za-z]+)(\d+)$", sample_id)
    if match is None:
        return None
    return match.group(1), int(match.group(2))


def _build_label_evidence(
    *,
    evidence_json: str | None,
    evidence_notes: tuple[str, ...],
) -> dict[str, Any]:
    """Build one label evidence payload from CLI arguments."""

    evidence: dict[str, Any] = {}
    if evidence_json is not None:
        payload = json.loads(evidence_json)
        if not isinstance(payload, dict):
            raise ValueError("--evidence-json must decode to a JSON object")
        evidence.update(payload)
    if evidence_notes:
        existing_notes = evidence.get("notes", [])
        if not isinstance(existing_notes, list):
            raise ValueError("evidence.notes must be a list when present")
        evidence["notes"] = [*existing_notes, *evidence_notes]
    return evidence


def _default_run_root(*, repo_root: Path, target_session: str) -> Path:
    """Return one default run root for a new recorder session."""

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return repo_root / "tmp" / "terminal_record" / f"{stamp}-{target_session}"


def _recorder_session_name(*, run_id: str) -> str:
    """Return one recorder tmux session name."""

    normalized = run_id.replace(":", "-").replace(".", "-")
    return f"HMREC-{normalized}"


def _build_recorder_shell_command(manifest: TerminalRecordManifest) -> str:
    """Return one shell command that launches the repo-owned `asciinema` recorder."""

    tmux_parts = ["env", "-u", "TMUX", "tmux", "attach-session"]
    if manifest.mode == "active":
        tmux_parts.append("-d")
    if manifest.mode == "passive":
        tmux_parts.append("-r")
    tmux_parts.extend(["-t", manifest.target.session_name])
    tmux_command = shlex.join(tmux_parts)
    if manifest.target.pane_id:
        tmux_command = f"{tmux_command} \\; select-pane -t {shlex.quote(manifest.target.pane_id)}"

    record_args = [
        "pixi",
        "run",
        "asciinema",
        "record",
        "--overwrite",
        "--output-format",
        "asciicast-v3",
        "--log-file",
        str(Path(manifest.run_root) / "asciinema.log"),
    ]
    if manifest.mode == "active":
        record_args.append("--capture-input")
    record_args.extend(
        [
            str(Path(manifest.run_root) / "session.cast"),
            "--command",
            tmux_command,
        ]
    )
    return shlex.join(record_args)


def _duration_from_seconds(value: float) -> timedelta:
    """Return one timedelta from seconds without importing globally."""

    return timedelta(seconds=value)


def _elapsed_seconds(started_at_utc: str) -> float:
    """Return elapsed seconds since one recorded UTC timestamp."""

    started_at = datetime.fromisoformat(started_at_utc)
    return max((datetime.now(started_at.tzinfo) - started_at).total_seconds(), 0.0)


def _wait_for_controller(live_state_path: Path) -> None:
    """Wait briefly for controller status to move beyond startup."""

    deadline = time.time() + 5.0
    while time.time() < deadline:
        if not live_state_path.is_file():
            time.sleep(0.05)
            continue
        state = load_live_state(live_state_path)
        if state.status != "starting":
            return
        time.sleep(0.05)


def _wait_for_final_status(live_state_path: Path) -> None:
    """Wait for one recorder run to finalize after stop request."""

    deadline = time.time() + 5.0
    while time.time() < deadline:
        state = load_live_state(live_state_path)
        if state.status in {"stopped", "failed"}:
            return
        time.sleep(0.05)


def _debug_readiness_state_from_parser(
    *,
    business_state: str,
    input_mode: str,
    ui_context: str,
) -> str:
    """Return one conservative debug-only readiness state from parser fields."""

    if input_mode == "modal" or ui_context in {"selection_menu", "slash_command"}:
        return "blocked"
    if business_state == "awaiting_operator":
        return "blocked"
    if business_state == "working":
        return "waiting"
    if input_mode == "freeform" and business_state == "idle":
        return "ready"
    return "unknown"


def _debug_completion_state_from_parser(
    *,
    business_state: str,
    input_mode: str,
    ui_context: str,
) -> str:
    """Return one conservative debug-only completion state from parser fields."""

    readiness_state = _debug_readiness_state_from_parser(
        business_state=business_state,
        input_mode=input_mode,
        ui_context=ui_context,
    )
    if readiness_state == "blocked":
        return "blocked"
    if business_state == "working":
        return "in_progress"
    if input_mode == "freeform" and business_state == "idle":
        return "inactive"
    return "waiting"


def _load_snapshots(path: Path) -> list[TerminalRecordPaneSnapshot]:
    """Load recorder snapshots from NDJSON."""

    snapshots: list[TerminalRecordPaneSnapshot] = []
    if not path.is_file():
        return snapshots
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
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
                    target_pane_width=(
                        int(payload["target_pane_width"])
                        if payload.get("target_pane_width") is not None
                        else None
                    ),
                    target_pane_height=(
                        int(payload["target_pane_height"])
                        if payload.get("target_pane_height") is not None
                        else None
                    ),
                    capture_command=str(payload.get("capture_command", PANE_CAPTURE_COMMAND)),
                    stream_kind=cast(
                        Any,
                        str(payload.get("stream_kind", "source")),
                    ),
                    source_sample_id=(
                        str(payload["source_sample_id"])
                        if payload.get("source_sample_id") is not None
                        else None
                    ),
                    source_elapsed_seconds=(
                        float(payload["source_elapsed_seconds"])
                        if payload.get("source_elapsed_seconds") is not None
                        else None
                    ),
                    output_text_sha256=(
                        str(payload["output_text_sha256"])
                        if payload.get("output_text_sha256") is not None
                        else None
                    ),
                )
            )
    return snapshots


def _load_input_events(path: Path) -> list[TerminalRecordInputEvent]:
    """Load recorder input events from NDJSON."""

    events: list[TerminalRecordInputEvent] = []
    if not path.is_file():
        return events
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            source = str(payload["source"])
            events.append(
                TerminalRecordInputEvent(
                    event_id=str(payload["event_id"]),
                    elapsed_seconds=float(payload["elapsed_seconds"]),
                    ts_utc=str(payload["ts_utc"]),
                    source=cast(InputEventSource, source),
                    sequence=str(payload["sequence"]),
                    escape_special_keys=bool(payload["escape_special_keys"]),
                    tmux_target=(
                        str(payload["tmux_target"])
                        if payload.get("tmux_target") is not None
                        else None
                    ),
                )
            )
    return events


def _degraded_capture_level(mode: RecorderMode) -> InputCaptureLevel:
    """Return degraded capture level for one recorder mode."""

    return "managed_only" if mode == "active" else "output_only"
