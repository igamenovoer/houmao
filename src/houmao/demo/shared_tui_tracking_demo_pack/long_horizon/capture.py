"""Recorder-backed execution of compiled long-horizon TUI operations."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.backends.tmux_runtime import (
    parse_tmux_control_input,
    run_tmux,
    send_tmux_control_input,
)
from houmao.demo.shared_tui_tracking_demo_pack.recorded import RuntimeObserver
from houmao.terminal_record.runtime_bridge import (
    append_managed_control_input_for_tmux_session,
)
from houmao.terminal_record.models import TerminalRecordPaths, load_manifest
from houmao.terminal_record.service import start_terminal_record, stop_terminal_record
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.attempts import (
    load_attempt_state,
    transition_attempt,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.checkpoints import (
    CheckpointResult,
    finalize_project_evidence,
    persist_engineering_verdict,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.models import (
    LongHorizonSuite,
    PlannedCell,
    ProviderName,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.operations import (
    CompiledOperation,
    GateKind,
    compile_cell_operations,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.paths import (
    LongHorizonRunPaths,
    save_json_atomic,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.preflight import (
    PreparedProviderHome,
    detect_ready_marker,
    find_confirmation_violation,
    remove_sensitive_provider_home,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.projects import (
    PreparedProject,
    recording_evidence_sha256,
)
from houmao.demo.shared_tui_tracking_demo_pack.tooling import (
    build_tool_session_name,
    capture_visible_pane_text,
    kill_tmux_session_if_exists,
    launch_tmux_session,
    resolve_active_pane_id,
)


_ACTIVE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"esc to interrupt",
        r"ctrl\+c to interrupt",
        r"working\s*[….(]",
        r"running\s+(?:tool|command)",
        r"press esc to cancel",
        r"ctrl-s to steer immediately",
    )
)


class CaptureFailure(RuntimeError):
    """Raised when one recorded attempt cannot produce qualifying evidence."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class OperationExecution:
    """Retained execution evidence for one compiled user operation."""

    event_id: str
    number: int
    started_at_utc: str
    completed_at_utc: str
    delivered_sequence: str | None
    tmux_commands: tuple[tuple[str, ...], ...]
    before_gate: GateKind
    after_gate: GateKind
    visible_after_sha256: str
    visible_after_path: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible operation execution payload."""

        return asdict(self)


@dataclass(frozen=True)
class CaptureResult:
    """Summary and retained paths for one completed live capture attempt."""

    schema_version: int
    cell_id: str
    attempt_id: str
    session_name: str
    pane_id: str
    recording_root: str
    recording_sha256: str
    operation_count: int
    engineering_verdict: str
    phase: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible capture-result payload."""

        return asdict(self)


def capture_attempt(
    *,
    paths: LongHorizonRunPaths,
    suite: LongHorizonSuite,
    cell: PlannedCell,
    attempt_number: int,
    project: PreparedProject,
    provider_home: PreparedProviderHome,
    ready_timeout_seconds: float = 90.0,
    turn_timeout_seconds: float = 600.0,
) -> CaptureResult:
    """Launch, record, drive, and freeze one exact UC-02 cell attempt."""

    attempt_root = paths.attempt_root(cell_id=cell.cell_id, attempt_number=attempt_number)
    attempt_state = load_attempt_state(attempt_root=attempt_root)
    if attempt_state.phase != "preflight_passed":
        raise ValueError(
            f"Capture requires preflight_passed, observed {attempt_state.phase}: {attempt_root}"
        )
    project_root = Path(project.copied_project_path)
    source_root = Path(project.source_path)
    session_name = build_tool_session_name(
        tool=cell.provider,
        run_id=f"lh-{cell.procedure_id}-a{attempt_number:03d}",
    )
    runtime_dir = attempt_root / "runtime"
    save_json_atomic(
        runtime_dir / "owned-resources.json",
        {
            "schema_version": 1,
            "cell_id": cell.cell_id,
            "attempt_id": f"a{attempt_number:03d}",
            "tmux_session_name": session_name,
            "provider_home": str(provider_home.home_path),
        },
    )
    pane_id: str | None = None
    recording_root = attempt_root / "recording" / "terminal-record"
    recorder_started = False
    runtime_observer: RuntimeObserver | None = None
    capture_error: BaseException | None = None
    transition_attempt(
        attempt_root=attempt_root,
        expected_phase="preflight_passed",
        new_phase="capturing",
    )
    try:
        launch_tmux_session(
            session_name=session_name,
            workdir=project_root,
            launch_script=provider_home.launch_helper_path,
            retain_shell_after_exit=True,
        )
        pane_id = resolve_active_pane_id(session_name=session_name)
        _wait_for_gate(
            gate="ready",
            provider=cell.provider,
            pane_id=pane_id,
            baseline_text="",
            timeout_seconds=ready_timeout_seconds,
        )
        start_terminal_record(
            mode="active",
            target_session=session_name,
            target_pane=pane_id,
            tool=cell.provider,
            run_root=recording_root,
            sample_interval_seconds=suite.capture_sample_interval_seconds,
        )
        recorder_started = True
        recorder_manifest = load_manifest(recording_root / "manifest.json")
        runtime_observer = RuntimeObserver(
            tool=cell.provider,
            session_name=session_name,
            pane_id=pane_id,
            output_path=runtime_dir / "runtime-observations.ndjson",
            recorder_started_at=datetime.fromisoformat(recorder_manifest.started_at_utc),
            poll_interval_seconds=suite.capture_sample_interval_seconds,
        )
        runtime_observer.start()
        operations = compile_cell_operations(
            cell=cell,
            safe_prefix=suite.safe_prefix,
            pane_id=pane_id,
            launch_command=shlex.quote(str(provider_home.launch_helper_path)),
        )
        executions = execute_operations(
            provider=cell.provider,
            session_name=session_name,
            pane_id=pane_id,
            operations=operations,
            attempt_root=attempt_root,
            turn_timeout_seconds=turn_timeout_seconds,
        )
        runtime_observer.stop()
        runtime_observer = None
        stop_terminal_record(run_root=recording_root)
        recorder_started = False
        _wait_for_recording_quiescence(recording_root=recording_root)
        _validate_recording_complete(
            recording_root=recording_root,
            expected_operation_count=len(operations),
            expanded_log=attempt_root / "expanded-operations.ndjson",
        )
        final_project = finalize_project_evidence(
            project_root=project_root,
            source_root=source_root,
            source_sha256_before=project.source_sha256,
            procedure_id=cell.procedure_id,
            allowed_paths=cell.allowed_final_paths,
            output_dir=attempt_root / "engineering",
        )
        operation_results = tuple(
            CheckpointResult(
                evaluator="operation_delivery",
                status="pass",
                description=f"Operation {item.number} delivered and stabilized",
                evidence={"event_id": item.event_id, "visible_after_path": item.visible_after_path},
            )
            for item in executions
        )
        engineering = persist_engineering_verdict(
            output_dir=attempt_root / "engineering",
            checkpoint_results=operation_results,
            final_project=final_project,
        )
        recording_digest = recording_evidence_sha256(recording_root)
        transition_attempt(
            attempt_root=attempt_root,
            expected_phase="capturing",
            new_phase="awaiting_manual_labels",
            input_digests={"recording": recording_digest},
        )
        result = CaptureResult(
            schema_version=1,
            cell_id=cell.cell_id,
            attempt_id=f"a{attempt_number:03d}",
            session_name=session_name,
            pane_id=pane_id,
            recording_root=str(recording_root),
            recording_sha256=recording_digest,
            operation_count=len(executions),
            engineering_verdict=engineering.code,
            phase="awaiting_manual_labels",
        )
        save_json_atomic(attempt_root / "capture-result.json", result.to_payload())
        return result
    except BaseException as exc:
        capture_error = exc
        if runtime_observer is not None:
            runtime_observer.stop()
            runtime_observer = None
        if recorder_started and recording_root.exists():
            try:
                stop_terminal_record(run_root=recording_root)
            except Exception:
                pass
        current = load_attempt_state(attempt_root=attempt_root)
        if current.phase == "capturing":
            code = exc.code if isinstance(exc, CaptureFailure) else "capture_failed"
            transition_attempt(
                attempt_root=attempt_root,
                expected_phase="capturing",
                new_phase="failed",
                failure_code=code,
            )
        raise
    finally:
        kill_tmux_session_if_exists(session_name=session_name)
        try:
            remove_sensitive_provider_home(paths=paths, prepared=provider_home)
            shutil.rmtree(attempt_root / "runtime" / "definition-workdir", ignore_errors=True)
        except (FileNotFoundError, ValueError):
            if capture_error is None:
                raise


def execute_operations(
    *,
    provider: ProviderName,
    session_name: str,
    pane_id: str,
    operations: tuple[CompiledOperation, ...],
    attempt_root: Path,
    turn_timeout_seconds: float,
) -> tuple[OperationExecution, ...]:
    """Execute compiled operations and preserve exact semantic input evidence."""

    expanded_log = attempt_root / "expanded-operations.ndjson"
    events_log = attempt_root / "logs" / "drive-events.ndjson"
    frames_dir = attempt_root / "runtime" / "operation-frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    delivered_by_number: dict[int, str] = {}
    executions: list[OperationExecution] = []
    action_baseline = capture_visible_pane_text(pane_id=pane_id)
    for operation in operations:
        if operation.before_gate != "none":
            _wait_for_gate(
                gate=operation.before_gate,
                provider=operation.provider,
                pane_id=pane_id,
                baseline_text=action_baseline,
                timeout_seconds=turn_timeout_seconds,
            )
        started_at = _now_utc()
        sequence = operation.sequence
        if operation.action_kind == "repeat_operation":
            repeat_number = operation.repeat_operation_number
            if repeat_number is None or repeat_number not in delivered_by_number:
                raise CaptureFailure(
                    "operation_compile_failed",
                    f"Operation {operation.number} cannot repeat {repeat_number}",
                )
            sequence = delivered_by_number[repeat_number]
        _append_ndjson(expanded_log, {**operation.to_payload(), "delivered_sequence": sequence})
        action_baseline = capture_visible_pane_text(pane_id=pane_id)
        if sequence is not None:
            _send_recorded_sequence(
                provider=provider,
                session_name=session_name,
                pane_id=pane_id,
                sequence=sequence,
            )
            delivered_by_number[operation.number] = sequence
        for command in operation.tmux_commands:
            run_tmux(list(command))
        if operation.after_gate != "none":
            _wait_for_gate(
                gate=operation.after_gate,
                provider=operation.provider,
                pane_id=pane_id,
                baseline_text=action_baseline,
                timeout_seconds=turn_timeout_seconds,
            )
        if operation.hold_after_seconds > 0:
            time.sleep(operation.hold_after_seconds)
        visible_after = capture_visible_pane_text(pane_id=pane_id)
        violation = find_confirmation_violation(visible_text=visible_after)
        if violation is not None:
            raise CaptureFailure(
                "unattended_confirmation_violation",
                f"Operation {operation.number} exposed intervention: {violation}",
            )
        frame_path = frames_dir / f"op-{operation.number:03d}-after.ansi.txt"
        frame_path.write_text(visible_after, encoding="utf-8")
        execution = OperationExecution(
            event_id=operation.event_id,
            number=operation.number,
            started_at_utc=started_at,
            completed_at_utc=_now_utc(),
            delivered_sequence=sequence,
            tmux_commands=operation.tmux_commands,
            before_gate=operation.before_gate,
            after_gate=operation.after_gate,
            visible_after_sha256=hashlib.sha256(visible_after.encode("utf-8")).hexdigest(),
            visible_after_path=str(frame_path),
        )
        _append_ndjson(events_log, execution.to_payload())
        executions.append(execution)
    return tuple(executions)


def _wait_for_gate(
    *,
    gate: GateKind,
    provider: ProviderName,
    pane_id: str,
    baseline_text: str,
    timeout_seconds: float,
) -> str:
    """Wait on raw native text and process-independent surface predicates."""

    if provider not in {"claude", "codex", "kimi"}:
        raise ValueError(f"Unsupported provider gate: {provider}")
    deadline = time.monotonic() + timeout_seconds
    stable_ready_polls = 0
    while time.monotonic() < deadline:
        visible_text = capture_visible_pane_text(pane_id=pane_id)
        plain_text = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", visible_text)
        if re.search(r"API Error:\s*(?:401|403|429|5\d\d)", plain_text, re.IGNORECASE):
            raise CaptureFailure(
                "external_provider_error",
                "Provider returned an API error during the live qualification attempt",
            )
        violation = find_confirmation_violation(visible_text=visible_text)
        if violation is not None:
            raise CaptureFailure(
                "unattended_confirmation_violation",
                f"Native TUI exposed intervention: {violation}",
            )
        active = _looks_active(provider=provider, visible_text=visible_text)
        changed = visible_text != baseline_text
        if gate == "active" and active:
            return visible_text
        if (
            gate == "first_response"
            and changed
            and (active or len(visible_text) > len(baseline_text))
        ):
            return visible_text
        if gate == "ready":
            marker = detect_ready_marker(provider=provider, visible_text=visible_text)
            if marker is not None and not active:
                stable_ready_polls += 1
            else:
                stable_ready_polls = 0
            if stable_ready_polls >= 2:
                return visible_text
        time.sleep(0.25)
    code = "stimulus_too_short" if gate in {"active", "first_response"} else "surface_timeout"
    raise CaptureFailure(code, f"Timed out waiting for raw {gate} gate")


def _looks_active(*, provider: ProviderName, visible_text: str) -> bool:
    """Return whether raw native UI text contains a bounded busy marker."""

    plain_text = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", visible_text)
    if provider == "codex":
        return "esc to interrupt" in plain_text.lower()
    return any(pattern.search(plain_text) is not None for pattern in _ACTIVE_PATTERNS)


def _send_recorded_sequence(
    *, provider: ProviderName, session_name: str, pane_id: str, sequence: str
) -> None:
    """Send one exact sequence and append authoritative managed-input evidence."""

    segments = parse_tmux_control_input(sequence=sequence)
    if provider in {"codex", "kimi"}:
        for segment in segments:
            if segment.kind == "special" and segment.value == "Enter":
                time.sleep(1.0 if provider == "codex" else 0.15)
            send_tmux_control_input(target=pane_id, segments=(segment,))
    else:
        send_tmux_control_input(target=pane_id, segments=segments)
    append_managed_control_input_for_tmux_session(
        session_name=session_name,
        sequence=sequence,
        escape_special_keys=False,
        tmux_target=pane_id,
    )


def _validate_recording_complete(
    *, recording_root: Path, expected_operation_count: int, expanded_log: Path
) -> None:
    """Require finalized recorder artifacts spanning every semantic operation."""

    paths = TerminalRecordPaths.from_run_root(run_root=recording_root)
    manifest = load_manifest(paths.manifest_path)
    snapshot_count = (
        sum(
            1 for line in paths.pane_snapshots_path.read_text(encoding="utf-8").splitlines() if line
        )
        if paths.pane_snapshots_path.is_file()
        else 0
    )
    operation_count = (
        sum(1 for line in expanded_log.read_text(encoding="utf-8").splitlines() if line)
        if expanded_log.is_file()
        else 0
    )
    if (
        manifest.stopped_at_utc is None
        or snapshot_count == 0
        or operation_count != expected_operation_count
        or not paths.cast_path.is_file()
    ):
        raise CaptureFailure(
            "capture_incomplete",
            "Recorder artifacts do not cover the complete semantic operation catalog",
        )


def _wait_for_recording_quiescence(*, recording_root: Path, timeout_seconds: float = 30.0) -> None:
    """Wait until finalized recorder files stop changing after the recorder exits."""

    names = ("manifest.json", "pane_snapshots.ndjson", "input_events.ndjson", "session.cast")
    deadline = time.monotonic() + timeout_seconds
    prior: tuple[tuple[int, int], ...] | None = None
    stable_polls = 0
    while time.monotonic() < deadline:
        current = tuple(
            (path.stat().st_size, path.stat().st_mtime_ns)
            for path in (recording_root / name for name in names)
            if path.is_file()
        )
        if len(current) == len(names) and current == prior:
            stable_polls += 1
        else:
            stable_polls = 0
        if stable_polls >= 10:
            return
        prior = current
        time.sleep(0.2)
    raise CaptureFailure("capture_incomplete", "Recorder files did not reach quiescence")


def _append_ndjson(path: Path, payload: dict[str, Any]) -> None:
    """Append one JSON object as an NDJSON row."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def _now_utc() -> str:
    """Return an ISO UTC timestamp for semantic operation correlation."""

    return datetime.now(UTC).isoformat()
