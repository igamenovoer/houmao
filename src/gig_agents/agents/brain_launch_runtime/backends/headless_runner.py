"""Shared headless CLI runner for JSON/JSONL streaming turns."""

from __future__ import annotations

import json
import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import BackendExecutionError
from ..models import SessionControlResult, SessionEvent
from .tmux_runtime import (
    TmuxCommandError,
    run_tmux as run_tmux_shared,
    tmux_error_detail as tmux_error_detail_shared,
    wait_for_tmux_signal as wait_for_tmux_signal_shared,
)

_DEFAULT_COMPLETION_TIMEOUT_SECONDS = 300.0
_DEFAULT_COMPLETION_POLL_INTERVAL_SECONDS = 0.1


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
    completion_source: str = "direct_process"


class HeadlessCliRunner:
    """Run one headless turn and stream parsed events."""

    def __init__(self) -> None:
        self._active_process: subprocess.Popen[str] | None = None
        self._active_tmux_session_name: str | None = None
        self._active_tmux_window_id: str | None = None
        self._active_tmux_wait_signal: str | None = None

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
        completion_timeout_seconds: float = _DEFAULT_COMPLETION_TIMEOUT_SECONDS,
        completion_poll_interval_seconds: float = (
            _DEFAULT_COMPLETION_POLL_INTERVAL_SECONDS
        ),
    ) -> HeadlessRunResult:
        """Execute a headless command and parse events."""

        if output_format not in {"json", "stream-json"}:
            raise BackendExecutionError(
                f"Unsupported headless output format: {output_format}"
            )

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

        window_id = self._active_tmux_window_id
        if window_id is None:
            return SessionControlResult(
                status="ok",
                action="interrupt",
                detail="No in-flight headless process",
            )

        try:
            result = run_tmux_shared(["kill-window", "-t", window_id])
        except TmuxCommandError as exc:
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail=f"Failed to interrupt tmux turn window: {exc}",
            )
        if result.returncode != 0:
            detail = tmux_error_detail_shared(result) or "unknown tmux error"
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail=f"Failed to interrupt tmux turn window: {detail}",
            )
        return SessionControlResult(
            status="ok",
            action="interrupt",
            detail="Killed in-flight tmux turn window",
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

        window_id = self._active_tmux_window_id
        if window_id is None:
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="No active headless process",
            )

        try:
            result = run_tmux_shared(["kill-window", "-t", window_id])
        except TmuxCommandError as exc:
            return SessionControlResult(
                status="error",
                action="terminate",
                detail=f"Failed to terminate tmux turn window: {exc}",
            )
        if result.returncode != 0:
            detail = tmux_error_detail_shared(result) or "unknown tmux error"
            return SessionControlResult(
                status="error",
                action="terminate",
                detail=f"Failed to terminate tmux turn window: {detail}",
            )
        return SessionControlResult(
            status="ok",
            action="terminate",
            detail="Killed active tmux turn window",
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
        completion_timeout_seconds: float,
        completion_poll_interval_seconds: float,
    ) -> HeadlessRunResult:
        turn_dir = (turn_artifacts_root / f"turn-{turn_index:04d}").resolve()
        turn_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = turn_dir / "stdout.jsonl"
        stderr_path = turn_dir / "stderr.log"
        status_path = turn_dir / "exitcode"
        wait_signal = (
            f"agentsys-headless-turn-{turn_index}-{uuid.uuid4().hex[:10]}".lower()
        )
        window_name = f"turn-{turn_index}"

        command_text = shlex.join(command)
        script = "\n".join(
            [
                "set +e",
                f"cd {shlex.quote(str(cwd))}",
                f"{command_text} > {shlex.quote(str(stdout_path))} "
                f"2> {shlex.quote(str(stderr_path))}",
                "status=$?",
                f"printf '%s\\n' \"$status\" > {shlex.quote(str(status_path))}",
                f"tmux wait-for -S {shlex.quote(wait_signal)} >/dev/null 2>&1 || true",
                "exit \"$status\"",
            ]
        )

        try:
            launch = run_tmux_shared(
                [
                    "new-window",
                    "-d",
                    "-P",
                    "-F",
                    "#{window_id}",
                    "-t",
                    tmux_session_name,
                    "-n",
                    window_name,
                    "sh",
                    "-lc",
                    script,
                ]
            )
        except TmuxCommandError as exc:
            raise BackendExecutionError(
                f"Failed to launch tmux headless turn: {exc}"
            ) from exc

        if launch.returncode != 0:
            detail = tmux_error_detail_shared(launch) or "unknown tmux error"
            raise BackendExecutionError(
                f"Failed to launch tmux headless turn in `{tmux_session_name}`: {detail}"
            )

        window_id = ""
        for raw_line in launch.stdout.splitlines():
            line = raw_line.strip()
            if line:
                window_id = line
                break
        if not window_id:
            raise BackendExecutionError(
                "Failed to resolve tmux turn window id from `tmux new-window` output."
            )

        self._active_tmux_session_name = tmux_session_name
        self._active_tmux_window_id = window_id
        self._active_tmux_wait_signal = wait_signal

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
        returncode = _read_turn_return_code(status_path=status_path)
        events = _parse_headless_output(
            output_format=output_format,
            stdout_text=stdout_text,
            turn_index=turn_index,
        )
        session_id = extract_session_id(events)

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

        self._active_tmux_session_name = None
        self._active_tmux_window_id = None
        self._active_tmux_wait_signal = None

        return HeadlessRunResult(
            events=events,
            stderr=stderr_text,
            returncode=returncode,
            session_id=session_id,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            status_path=status_path,
            completion_source=completion_source,
        )


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


def _parse_headless_output(
    *,
    output_format: str,
    stdout_text: str,
    turn_index: int,
) -> list[SessionEvent]:
    events: list[SessionEvent] = []
    if output_format == "stream-json":
        for raw_line in stdout_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            events.append(_parse_stream_json_line(line=line, turn_index=turn_index))
        return events
    return _parse_json_payload(text=stdout_text, turn_index=turn_index)


def _read_turn_return_code(*, status_path: Path) -> int:
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
    return SessionEvent(
        kind=kind, message=message, turn_index=turn_index, payload=payload
    )


def _parse_json_payload(*, text: str, turn_index: int) -> list[SessionEvent]:
    stripped = text.strip()
    if not stripped:
        return []

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise BackendExecutionError(
            f"Could not parse JSON headless payload: {exc}"
        ) from exc

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
