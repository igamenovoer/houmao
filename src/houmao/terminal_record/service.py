"""Service layer for tmux-backed terminal recorder runs."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.backends.shadow_parser_stack import ShadowParserStack
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    capture_tmux_pane,
    ensure_tmux_available,
    has_tmux_session,
    kill_tmux_session,
    list_tmux_clients,
    list_tmux_panes,
    run_tmux,
    tmux_error_detail,
)
from houmao.demo.cao_dual_shadow_watch.models import (
    AgentSessionState,
    MonitorObservation,
)
from houmao.demo.cao_dual_shadow_watch.monitor import AgentStateTracker

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

        while True:
            self._capture_snapshot()
            if self._active_mode_has_extra_clients():
                self._taint_run("multiple_clients_attached")
            if self._stop_requested():
                self._write_live_state(status="stopping", controller_pid=os.getpid(), last_error=None)
                return
            if self._recorder_session_stopped():
                self._write_live_state(status="stopping", controller_pid=os.getpid(), last_error=None)
                return
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
        existing_count = 0
        if self.m_paths.pane_snapshots_path.is_file():
            existing_count = sum(1 for _ in self.m_paths.pane_snapshots_path.open("r", encoding="utf-8"))
        snapshot = TerminalRecordPaneSnapshot(
            sample_id=f"s{existing_count + 1:06d}",
            elapsed_seconds=_elapsed_seconds(self.m_manifest.started_at_utc),
            ts_utc=now_utc_iso(),
            target_pane_id=self.m_manifest.target.pane_id,
            output_text=output_text,
        )
        append_ndjson(self.m_paths.pane_snapshots_path, snapshot.to_payload())

    def _stop_requested(self) -> bool:
        """Return whether stop has been requested for this run."""

        live_state = load_live_state(self.m_live_state_path)
        self.m_live_state = live_state
        return live_state.stop_requested_at_utc is not None

    def _recorder_session_stopped(self) -> bool:
        """Return whether the recorder tmux session is no longer running."""

        result = has_tmux_session(session_name=self.m_manifest.recorder_session_name)
        return result.returncode != 0

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
        )
        save_manifest(self.m_paths.manifest_path, self.m_manifest)

    def _resolve_stop_reason(self) -> str:
        """Return one finalized stop reason."""

        if self.m_live_state.stop_requested_at_utc is not None:
            return "stop_requested"
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
) -> dict[str, Any]:
    """Start one terminal recorder controller process."""

    ensure_tmux_available()
    if sample_interval_seconds <= 0:
        raise TerminalRecordError("sample_interval_seconds must be positive")
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
    visual_recording_kind = (
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


def analyze_terminal_record(*, run_root: Path, tool: str | None) -> dict[str, Any]:
    """Derive parser and state observations from one recorder run."""

    paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    manifest = load_manifest(paths.manifest_path)
    selected_tool = tool or manifest.tool
    if selected_tool not in {"claude", "codex"}:
        raise TerminalRecordError(
            "analyze requires recorder manifest tool to be one of `claude` or `codex`, "
            "or an explicit --tool override."
        )

    parser_stack = ShadowParserStack(tool=selected_tool)
    tracker = AgentStateTracker(
        session=_dummy_agent_session(tool=selected_tool, session_name=manifest.target.session_name),
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )
    parser_payloads: list[dict[str, Any]] = []
    state_payloads: list[dict[str, Any]] = []
    for snapshot in _load_snapshots(paths.pane_snapshots_path):
        parsed = parser_stack.parse_snapshot(
            snapshot.output_text,
            baseline_pos=0,
        )
        assessment = parsed.surface_assessment
        projection = parsed.dialog_projection
        parser_payloads.append(
            {
                "sample_id": snapshot.sample_id,
                "elapsed_seconds": snapshot.elapsed_seconds,
                "availability": assessment.availability,
                "business_state": assessment.business_state,
                "input_mode": assessment.input_mode,
                "ui_context": assessment.ui_context,
                "parser_preset_id": assessment.parser_metadata.parser_preset_id,
                "parser_preset_version": assessment.parser_metadata.parser_preset_version,
                "baseline_invalidated": assessment.parser_metadata.baseline_invalidated,
                "dialog_tail": projection.tail,
                "normalized_text": projection.normalized_text,
            }
        )
        observation = MonitorObservation(
            slot="recorded",
            tool=selected_tool,
            terminal_id=manifest.target.pane_id,
            tmux_session_name=manifest.target.session_name,
            cao_status="recorded",
            parser_family=parser_stack.parser_family,
            parser_preset_id=assessment.parser_metadata.parser_preset_id,
            parser_preset_version=assessment.parser_metadata.parser_preset_version,
            availability=assessment.availability,
            business_state=assessment.business_state,
            input_mode=assessment.input_mode,
            ui_context=assessment.ui_context,
            normalized_projection_text=projection.normalized_text,
            dialog_tail=projection.tail,
            operator_blocked_excerpt=assessment.operator_blocked_excerpt,
            anomaly_codes=tuple(
                anomaly.code
                for anomaly in (
                    *assessment.parser_metadata.anomalies,
                    *assessment.anomalies,
                    *projection.anomalies,
                )
            ),
            baseline_invalidated=assessment.parser_metadata.baseline_invalidated,
            monotonic_ts=snapshot.elapsed_seconds,
            error_detail=None,
        )
        state, _ = tracker.observe(observation)
        state_payloads.append(
            {
                "sample_id": snapshot.sample_id,
                "elapsed_seconds": snapshot.elapsed_seconds,
                "readiness_state": state.readiness_state,
                "completion_state": state.completion_state,
                "business_state": state.business_state,
                "input_mode": state.input_mode,
                "ui_context": state.ui_context,
                "projection_changed": state.projection_changed,
                "baseline_invalidated": state.baseline_invalidated,
                "anomaly_codes": list(state.anomaly_codes),
            }
        )

    overwrite_ndjson(paths.parser_observed_path, parser_payloads)
    overwrite_ndjson(paths.state_observed_path, state_payloads)
    return {
        "run_id": manifest.run_id,
        "tool": selected_tool,
        "parser_observed_path": str(paths.parser_observed_path),
        "state_observed_path": str(paths.state_observed_path),
        "sample_count": len(parser_payloads),
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
    panes = list_tmux_panes(session_name=target_session)
    if target_pane is None:
        if len(panes) != 1:
            raise TerminalRecordError(
                f"Target session `{target_session}` has {len(panes)} panes; provide --target-pane."
            )
        pane = panes[0]
    else:
        try:
            pane = next(item for item in panes if item.pane_id == target_pane)
        except StopIteration as exc:
            raise TerminalRecordError(
                f"Target pane `{target_pane}` was not found in session `{target_session}`."
            ) from exc
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
            ts_value = (started_at + _duration_from_seconds(elapsed_seconds)).isoformat(timespec="seconds")
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
    start.add_argument("--tool", choices=["claude", "codex"], default=None)
    start.add_argument("--run-root", type=Path, default=None)
    start.add_argument(
        "--sample-interval-seconds",
        type=float,
        default=DEFAULT_SAMPLE_INTERVAL_SECONDS,
    )

    status = subparsers.add_parser("status", help="Inspect one recorder run")
    status.add_argument("--run-root", type=Path, required=True)

    stop = subparsers.add_parser("stop", help="Stop one recorder run")
    stop.add_argument("--run-root", type=Path, required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze one recorder run")
    analyze.add_argument("--run-root", type=Path, required=True)
    analyze.add_argument("--tool", choices=["claude", "codex"], default=None)

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
    add_label.add_argument("--readiness-state", default=None)
    add_label.add_argument("--completion-state", default=None)
    add_label.add_argument("--note", default=None)

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
            )
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if args.command == "status":
            print(json.dumps(status_terminal_record(run_root=args.run_root), indent=2, sort_keys=True))
            return 0
        if args.command == "stop":
            print(json.dumps(stop_terminal_record(run_root=args.run_root), indent=2, sort_keys=True))
            return 0
        if args.command == "analyze":
            print(json.dumps(analyze_terminal_record(run_root=args.run_root, tool=args.tool), indent=2, sort_keys=True))
            return 0
        if args.command == "add-label":
            expectations = {
                key: value
                for key, value in {
                    "business_state": args.business_state,
                    "input_mode": args.input_mode,
                    "ui_context": args.ui_context,
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
                        sample_end_id=str(args.sample_end_id) if args.sample_end_id is not None else None,
                        scenario_id=str(args.scenario_id) if args.scenario_id is not None else None,
                        expectations=expectations,
                        note=str(args.note) if args.note is not None else None,
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


def _duration_from_seconds(value: float):
    """Return one timedelta from seconds without importing globally."""

    from datetime import timedelta

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


def _dummy_agent_session(*, tool: str, session_name: str) -> AgentSessionState:
    """Return one minimal demo-session model for state tracking reuse."""

    return AgentSessionState(
        slot="recorded",
        tool=tool,
        blueprint_path="recorded",
        brain_recipe_path="recorded",
        role_name="recorded",
        workdir="recorded",
        brain_home_path="recorded",
        brain_manifest_path="recorded",
        launch_helper_path="recorded",
        session_manifest_path="recorded",
        agent_identity="recorded",
        agent_id="recorded",
        tmux_session_name=session_name,
        cao_session_name="recorded",
        terminal_id="recorded",
        parsing_mode="shadow_only",
    )


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
            events.append(
                TerminalRecordInputEvent(
                    event_id=str(payload["event_id"]),
                    elapsed_seconds=float(payload["elapsed_seconds"]),
                    ts_utc=str(payload["ts_utc"]),
                    source=str(payload["source"]),
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
