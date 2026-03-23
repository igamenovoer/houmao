"""Shared headless CLI runner for JSON/JSONL streaming turns."""

from __future__ import annotations

import errno
import json
import os
import shlex
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import BackendExecutionError
from ..models import SessionControlResult, SessionEvent
from .tmux_runtime import (
    HEADLESS_AGENT_WINDOW_NAME,
    TmuxCommandError,
    headless_agent_pane_target as headless_agent_pane_target_shared,
    prepare_headless_agent_window as prepare_headless_agent_window_shared,
    run_tmux as run_tmux_shared,
    tmux_error_detail as tmux_error_detail_shared,
    wait_for_tmux_signal as wait_for_tmux_signal_shared,
)

_DEFAULT_COMPLETION_TIMEOUT_SECONDS = 300.0
_DEFAULT_COMPLETION_POLL_INTERVAL_SECONDS = 0.1


@dataclass(frozen=True)
class HeadlessProcessMetadata:
    """Durable process identity for one tmux-backed headless turn."""

    runner_pid: int | None = None
    child_pid: int | None = None
    launched_at_utc: str | None = None


@dataclass(frozen=True)
class HeadlessRunResult:
    """Result for one headless CLI invocation."""

    events: list[SessionEvent]
    stderr: str
    returncode: int
    session_id: str | None
    stdout_path: Path | None = None
    stderr_path: Path | None = None
    status_path: Path | None = None
    process_path: Path | None = None
    process_metadata: HeadlessProcessMetadata | None = None
    completion_source: str = "direct_process"


class HeadlessCliRunner:
    """Run one headless turn and stream parsed events."""

    def __init__(self) -> None:
        self._active_process: subprocess.Popen[str] | None = None
        self._active_tmux_session_name: str | None = None
        self._active_tmux_pane_target: str | None = None
        self._active_tmux_wait_signal: str | None = None
        self._active_process_path: Path | None = None
        self._active_process_metadata: HeadlessProcessMetadata | None = None

    def run(
        self,
        *,
        command: list[str],
        env: dict[str, str],
        cwd: Path,
        turn_index: int,
        output_format: str,
        tmux_session_name: str | None = None,
        turn_artifacts_root: Path | None = None,
        turn_artifact_dir_name: str | None = None,
        completion_timeout_seconds: float = _DEFAULT_COMPLETION_TIMEOUT_SECONDS,
        completion_poll_interval_seconds: float = (_DEFAULT_COMPLETION_POLL_INTERVAL_SECONDS),
    ) -> HeadlessRunResult:
        """Execute a headless command and parse events."""

        if output_format not in {"json", "stream-json"}:
            raise BackendExecutionError(f"Unsupported headless output format: {output_format}")

        if tmux_session_name is None:
            return self._run_direct_subprocess(
                command=command,
                env=env,
                cwd=cwd,
                turn_index=turn_index,
                output_format=output_format,
            )

        return self._run_in_tmux(
            command=command,
            cwd=cwd,
            turn_index=turn_index,
            output_format=output_format,
            tmux_session_name=tmux_session_name,
            turn_artifacts_root=turn_artifacts_root
            if turn_artifacts_root is not None
            else cwd / ".agentsys-headless-turns",
            turn_artifact_dir_name=turn_artifact_dir_name,
            completion_timeout_seconds=completion_timeout_seconds,
            completion_poll_interval_seconds=completion_poll_interval_seconds,
        )

    def interrupt(self) -> SessionControlResult:
        """Interrupt an in-flight process with best-effort termination."""

        process = self._active_process
        if process is not None and process.poll() is None:
            process.terminate()
            return SessionControlResult(
                status="ok",
                action="interrupt",
                detail="Sent terminate signal to headless process",
            )

        if self._signal_active_tmux_process(signal.SIGTERM):
            return SessionControlResult(
                status="ok",
                action="interrupt",
                detail="Sent terminate signal to active tmux-backed headless process",
            )

        pane_target = self._active_tmux_pane_target
        if pane_target is None:
            return SessionControlResult(
                status="ok",
                action="interrupt",
                detail="No in-flight headless process",
            )

        try:
            result = run_tmux_shared(["send-keys", "-t", pane_target, "C-c"])
        except TmuxCommandError as exc:
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail=f"Failed to interrupt tmux {HEADLESS_AGENT_WINDOW_NAME} surface: {exc}",
            )
        if result.returncode != 0:
            detail = tmux_error_detail_shared(result) or "unknown tmux error"
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail=f"Failed to interrupt tmux {HEADLESS_AGENT_WINDOW_NAME} surface: {detail}",
            )
        return SessionControlResult(
            status="ok",
            action="interrupt",
            detail="Sent control input to active tmux-backed headless agent surface",
        )

    def terminate(self) -> SessionControlResult:
        """Force kill an in-flight process."""

        process = self._active_process
        if process is not None and process.poll() is None:
            process.kill()
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="Killed headless process",
            )

        if self._signal_active_tmux_process(signal.SIGKILL):
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="Killed active tmux-backed headless process",
            )

        pane_target = self._active_tmux_pane_target
        if pane_target is None:
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="No active headless process",
            )

        try:
            result = run_tmux_shared(["send-keys", "-t", pane_target, "C-c"])
        except TmuxCommandError as exc:
            return SessionControlResult(
                status="error",
                action="terminate",
                detail=f"Failed to terminate tmux {HEADLESS_AGENT_WINDOW_NAME} surface: {exc}",
            )
        if result.returncode != 0:
            detail = tmux_error_detail_shared(result) or "unknown tmux error"
            return SessionControlResult(
                status="error",
                action="terminate",
                detail=f"Failed to terminate tmux {HEADLESS_AGENT_WINDOW_NAME} surface: {detail}",
            )
        return SessionControlResult(
            status="ok",
            action="terminate",
            detail="Sent control input to active tmux-backed headless agent surface",
        )

    def _run_direct_subprocess(
        self,
        *,
        command: list[str],
        env: dict[str, str],
        cwd: Path,
        turn_index: int,
        output_format: str,
    ) -> HeadlessRunResult:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._active_process = process

        events: list[SessionEvent] = []
        raw_stdout_chunks: list[str] = []

        assert process.stdout is not None
        for raw_line in process.stdout:
            raw_stdout_chunks.append(raw_line)
            line = raw_line.strip()
            if not line:
                continue
            if output_format == "stream-json":
                events.append(_parse_stream_json_line(line=line, turn_index=turn_index))

        returncode = process.wait()

        stderr_text = ""
        if process.stderr is not None:
            stderr_text = process.stderr.read()

        if output_format == "json":
            events.extend(
                _parse_json_payload(
                    text="".join(raw_stdout_chunks),
                    turn_index=turn_index,
                )
            )

        session_id = extract_session_id(events)
        self._active_process = None

        if returncode != 0:
            message = stderr_text.strip() or f"command exited with code {returncode}"
            events.append(
                SessionEvent(
                    kind="error",
                    message=message,
                    turn_index=turn_index,
                    payload={"returncode": returncode},
                )
            )

        return HeadlessRunResult(
            events=events,
            stderr=stderr_text,
            returncode=returncode,
            session_id=session_id,
        )

    def _run_in_tmux(
        self,
        *,
        command: list[str],
        cwd: Path,
        turn_index: int,
        output_format: str,
        tmux_session_name: str,
        turn_artifacts_root: Path,
        turn_artifact_dir_name: str | None,
        completion_timeout_seconds: float,
        completion_poll_interval_seconds: float,
    ) -> HeadlessRunResult:
        turn_dir_name = turn_artifact_dir_name or f"turn-{turn_index:04d}"
        turn_dir = (turn_artifacts_root / turn_dir_name).resolve()
        turn_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = turn_dir / "stdout.jsonl"
        stderr_path = turn_dir / "stderr.log"
        status_path = turn_dir / "exitcode"
        process_path = turn_dir / "process.json"
        process_tmp_path = turn_dir / f".process-{uuid.uuid4().hex}.tmp"
        status_tmp_path = turn_dir / f".exitcode-{uuid.uuid4().hex}.tmp"
        stdout_pipe_path = turn_dir / f".stdout-{uuid.uuid4().hex}.pipe"
        stderr_pipe_path = turn_dir / f".stderr-{uuid.uuid4().hex}.pipe"
        wait_signal = f"agentsys-headless-turn-{turn_index}-{uuid.uuid4().hex[:10]}".lower()
        pane_target = headless_agent_pane_target_shared(session_name=tmux_session_name)

        command_text = shlex.join(command)
        script = "\n".join(
            [
                "set +e",
                f"cd {shlex.quote(str(cwd))}",
                'started_at_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"',
                f"rm -f {shlex.quote(str(stdout_pipe_path))} {shlex.quote(str(stderr_pipe_path))}",
                f"mkfifo {shlex.quote(str(stdout_pipe_path))} {shlex.quote(str(stderr_pipe_path))}",
                (
                    "trap "
                    f"'rm -f {shlex.quote(str(stdout_pipe_path))} "
                    f"{shlex.quote(str(stderr_pipe_path))}' EXIT HUP INT TERM"
                ),
                f": > {shlex.quote(str(stdout_path))}",
                f": > {shlex.quote(str(stderr_path))}",
                (
                    f"tee -a {shlex.quote(str(stdout_path))} "
                    f"< {shlex.quote(str(stdout_pipe_path))} &"
                ),
                "stdout_tee_pid=$!",
                (
                    f"tee -a {shlex.quote(str(stderr_path))} "
                    f"< {shlex.quote(str(stderr_pipe_path))} >&2 &"
                ),
                "stderr_tee_pid=$!",
                (
                    f"( exec {command_text} > {shlex.quote(str(stdout_pipe_path))} "
                    f"2> {shlex.quote(str(stderr_pipe_path))} ) &"
                ),
                "child_pid=$!",
                (
                    "printf "
                    '\'{"runner_pid":%s,"child_pid":%s,"launched_at_utc":"%s"}\\n\' '
                    f'"$$" "$child_pid" "$started_at_utc" > {shlex.quote(str(process_tmp_path))}'
                ),
                (f"mv {shlex.quote(str(process_tmp_path))} {shlex.quote(str(process_path))}"),
                'wait "$child_pid"',
                "status=$?",
                'wait "$stdout_tee_pid" || true',
                'wait "$stderr_tee_pid" || true',
                f"printf '%s\\n' \"$status\" > {shlex.quote(str(status_tmp_path))}",
                (f"mv {shlex.quote(str(status_tmp_path))} {shlex.quote(str(status_path))}"),
                f"tmux wait-for -S {shlex.quote(wait_signal)} >/dev/null 2>&1 || true",
                'idle_shell="${SHELL:-/bin/sh}"',
                'exec "$idle_shell" -l',
            ]
        )
        pane_command = f"sh -lc {shlex.quote(script)}"

        try:
            prepare_headless_agent_window_shared(session_name=tmux_session_name)
        except TmuxCommandError as exc:
            raise BackendExecutionError(
                f"Failed to prepare tmux headless agent surface in `{tmux_session_name}`: {exc}"
            ) from exc

        try:
            launch = run_tmux_shared(
                [
                    "respawn-pane",
                    "-k",
                    "-t",
                    pane_target,
                    pane_command,
                ]
            )
        except TmuxCommandError as exc:
            raise BackendExecutionError(f"Failed to launch tmux headless turn: {exc}") from exc

        if launch.returncode != 0:
            detail = tmux_error_detail_shared(launch) or "unknown tmux error"
            raise BackendExecutionError(
                f"Failed to launch tmux headless turn in `{tmux_session_name}` on the "
                f"stable {HEADLESS_AGENT_WINDOW_NAME} surface: {detail}"
            )

        self._active_tmux_session_name = tmux_session_name
        self._active_tmux_pane_target = pane_target
        self._active_tmux_wait_signal = wait_signal
        self._active_process_path = process_path
        self._active_process_metadata = self._wait_for_process_metadata(
            process_path=process_path,
            timeout_seconds=1.0,
        )

        completion_source = "status_polling"
        try:
            wait_result = wait_for_tmux_signal_shared(
                signal_name=wait_signal,
                timeout_seconds=completion_timeout_seconds,
            )
            if wait_result.returncode == 0:
                completion_source = "tmux_wait_for"
        except TmuxCommandError:
            completion_source = "status_polling"

        deadline = time.monotonic() + max(completion_timeout_seconds, 0.0)
        while True:
            if status_path.is_file():
                break
            if time.monotonic() >= deadline:
                raise BackendExecutionError(
                    "Timed out waiting for tmux headless turn completion marker."
                )
            time.sleep(max(completion_poll_interval_seconds, 0.01))

        stderr_text = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
        stdout_text = stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else ""
        returncode = read_headless_turn_return_code(status_path=status_path)
        events = parse_headless_output_text(
            output_format=output_format,
            stdout_text=stdout_text,
            turn_index=turn_index,
        )
        session_id = extract_session_id(events)
        process_metadata = self._read_process_metadata_best_effort(process_path=process_path)

        if returncode != 0:
            message = stderr_text.strip() or f"command exited with code {returncode}"
            events.append(
                SessionEvent(
                    kind="error",
                    message=message,
                    turn_index=turn_index,
                    payload={"returncode": returncode},
                )
            )
        try:
            return HeadlessRunResult(
                events=events,
                stderr=stderr_text,
                returncode=returncode,
                session_id=session_id,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                status_path=status_path,
                process_path=process_path,
                process_metadata=process_metadata,
                completion_source=completion_source,
            )
        finally:
            self._active_tmux_session_name = None
            self._active_tmux_pane_target = None
            self._active_tmux_wait_signal = None
            self._active_process_path = None
            self._active_process_metadata = None

    def _signal_active_tmux_process(self, sig: int) -> bool:
        """Signal the active tmux-backed process identity when available."""

        metadata = self._active_process_metadata
        if metadata is None and self._active_process_path is not None:
            metadata = self._read_process_metadata_best_effort(
                process_path=self._active_process_path
            )
            if metadata is not None:
                self._active_process_metadata = metadata
        if metadata is None:
            return False
        if _signal_pid(metadata.child_pid, sig):
            return True
        return _signal_pid(metadata.runner_pid, sig)

    def _wait_for_process_metadata(
        self,
        *,
        process_path: Path,
        timeout_seconds: float,
    ) -> HeadlessProcessMetadata | None:
        """Wait briefly for launch-time process metadata to be published."""

        deadline = time.monotonic() + max(timeout_seconds, 0.0)
        while time.monotonic() < deadline:
            metadata = self._read_process_metadata_best_effort(process_path=process_path)
            if metadata is not None:
                return metadata
            time.sleep(0.05)
        return self._read_process_metadata_best_effort(process_path=process_path)

    def _read_process_metadata_best_effort(
        self,
        *,
        process_path: Path,
    ) -> HeadlessProcessMetadata | None:
        """Read durable process metadata without surfacing parse failures."""

        try:
            return load_headless_process_metadata(process_path=process_path)
        except (FileNotFoundError, ValueError, json.JSONDecodeError):
            return None


def extract_session_id(events: list[SessionEvent]) -> str | None:
    """Extract a backend `session_id` from parsed events."""

    for event in events:
        payload = event.payload
        if not isinstance(payload, dict):
            continue
        candidate = _extract_session_id_from_payload(payload)
        if candidate:
            return candidate
    return None


def parse_headless_output_text(
    *,
    output_format: str,
    stdout_text: str,
    turn_index: int,
) -> list[SessionEvent]:
    """Parse one persisted headless stdout payload into structured events."""

    events: list[SessionEvent] = []
    if output_format == "stream-json":
        for raw_line in stdout_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            events.append(_parse_stream_json_line(line=line, turn_index=turn_index))
        return events
    return _parse_json_payload(text=stdout_text, turn_index=turn_index)


def load_headless_turn_events(
    *,
    stdout_path: Path,
    output_format: str,
    turn_index: int,
) -> list[SessionEvent]:
    """Read one persisted headless stdout artifact and parse it."""

    stdout_text = stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else ""
    return parse_headless_output_text(
        output_format=output_format,
        stdout_text=stdout_text,
        turn_index=turn_index,
    )


def load_headless_process_metadata(*, process_path: Path) -> HeadlessProcessMetadata:
    """Read one persisted headless process metadata artifact."""

    payload = json.loads(process_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("headless process metadata must be a JSON object")
    return HeadlessProcessMetadata(
        runner_pid=_coerce_optional_pid(payload.get("runner_pid")),
        child_pid=_coerce_optional_pid(payload.get("child_pid")),
        launched_at_utc=_coerce_optional_string(payload.get("launched_at_utc")),
    )


def read_headless_turn_return_code(*, status_path: Path) -> int:
    """Read one persisted headless exit-code marker."""

    raw = status_path.read_text(encoding="utf-8").strip()
    if not raw:
        raise BackendExecutionError(
            f"Invalid headless turn status marker `{status_path}`: blank content."
        )
    try:
        return int(raw)
    except ValueError as exc:
        raise BackendExecutionError(
            f"Invalid headless turn status marker `{status_path}`: {raw!r}."
        ) from exc


def _parse_stream_json_line(*, line: str, turn_index: int) -> SessionEvent:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return SessionEvent(
            kind="diagnostic",
            message=line,
            turn_index=turn_index,
            payload={"raw": line},
        )

    kind = str(payload.get("type", "event"))
    message = _extract_text(payload) or kind
    return SessionEvent(kind=kind, message=message, turn_index=turn_index, payload=payload)


def _parse_json_payload(*, text: str, turn_index: int) -> list[SessionEvent]:
    stripped = text.strip()
    if not stripped:
        return []

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise BackendExecutionError(f"Could not parse JSON headless payload: {exc}") from exc

    if isinstance(payload, list):
        events: list[SessionEvent] = []
        for item in payload:
            if isinstance(item, dict):
                events.append(
                    SessionEvent(
                        kind=str(item.get("type", "event")),
                        message=_extract_text(item) or "event",
                        turn_index=turn_index,
                        payload=item,
                    )
                )
        return events

    if isinstance(payload, dict):
        return [
            SessionEvent(
                kind=str(payload.get("type", "result")),
                message=_extract_text(payload) or "result",
                turn_index=turn_index,
                payload=payload,
            )
        ]

    return [
        SessionEvent(
            kind="result",
            message=str(payload),
            turn_index=turn_index,
            payload={"value": payload},
        )
    ]


def _extract_text(payload: dict[str, Any]) -> str:
    for key in ("text", "message", "content", "output", "result"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    if isinstance(payload.get("delta"), str):
        return str(payload["delta"])
    return ""


def _extract_session_id_from_payload(payload: dict[str, Any]) -> str | None:
    for key in ("session_id", "sessionId", "thread_id", "threadId"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    session = payload.get("session")
    if isinstance(session, dict):
        nested = session.get("id")
        if isinstance(nested, str) and nested.strip():
            return nested

    thread = payload.get("thread")
    if isinstance(thread, dict):
        thread_id = thread.get("id")
        if isinstance(thread_id, str) and thread_id.strip():
            return thread_id

    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("session_id", "sessionId", "thread_id", "threadId"):
            nested_data = data.get(key)
            if isinstance(nested_data, str) and nested_data.strip():
                return nested_data

    return None


def _coerce_optional_pid(value: object) -> int | None:
    """Normalize one optional persisted pid field."""

    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("pid must not be boolean")
    if isinstance(value, int):
        if value <= 0:
            raise ValueError("pid must be > 0")
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        if parsed <= 0:
            raise ValueError("pid must be > 0")
        return parsed
    raise ValueError("pid must be an integer")


def _coerce_optional_string(value: object) -> str | None:
    """Normalize one optional persisted string field."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("value must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValueError("value must not be empty")
    return stripped


def _signal_pid(pid: int | None, sig: int) -> bool:
    """Deliver one POSIX signal when the pid is live."""

    if pid is None:
        return False
    try:
        os.kill(pid, sig)
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        raise
    return True
