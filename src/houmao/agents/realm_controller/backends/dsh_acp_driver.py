"""Execute one exclusively owned DSH ACP interval without prompt replay.

The managed envelope supplies private invocation/control files. Native receipts
establish admission; stdout contains driver events and the provider transcript
is preserved separately. This driver never substitutes a new session on resume.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import sys
import threading
import time
from typing import Any, TextIO

from houmao.agents.realm_controller.backends.dispatch_control import (
    headless_dispatch_permission_allowed,
)
from houmao.agents.realm_controller.backends.dsh_acp_connection import (
    DshAcpConnection,
    DshAcpProtocolError,
    reject_dsh_acp_permission,
    validate_dsh_acp_initialization,
)
from houmao.agents.realm_controller.backends.dsh_diagnostics import (
    dsh_diagnostic_secrets,
    dsh_diagnostic_tail,
    sanitize_dsh_diagnostic,
)


@dataclass(frozen=True)
class DshAcpInvocation:
    """Private inputs for one fenced native interval, never public metadata."""

    command: tuple[str, ...]
    working_directory: Path
    environment: dict[str, str]
    prompt: str
    session_id: str | None
    attempt_id: str
    runtime_session_id: str
    generation: str
    turn_dir: Path
    lock_path: Path
    evidence_path: Path
    dispatch_guard: Path | None = None
    setup_timeout: float = 60.0
    close_timeout: float = 10.0
    cancellation_timeout: float = 5.0
    mcp_servers: tuple[dict[str, Any], ...] = ()
    persistence_root: Path | None = None
    model: tuple[str, str] | None = None
    reasoning_effort: str | None = None
    secret_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class DshAcpOutcome:
    """Separate native settlement from persistence and transport cleanup."""

    session_id: str
    stop_reason: str
    handoff_confirmed: bool


def run_dsh_acp_turn(
    invocation: DshAcpInvocation,
    *,
    emit: Callable[[dict[str, Any]], None],
    interrupted: threading.Event,
    confirmed: Callable[[], None],
    prepare: Callable[[DshAcpInvocation], DshAcpInvocation] | None = None,
) -> DshAcpOutcome:
    """Run one explicitly selected conversation interval under a session lock.

    Parameters
    ----------
    invocation:
        Resolved private native configuration and exact continuation selection.
    emit:
        Consumer of canonicalizable driver events, separate from ACP frames.
    interrupted:
        An explicit cancellation signal; it never authorizes a retry.
    confirmed:
        Called once after this attempt's verified native handoff evidence.
    """

    if not invocation.prompt.strip():
        raise ValueError("DSH prompt must not be empty")
    invocation.turn_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    invocation.lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(invocation.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DshAcpProtocolError(
                "DSH runtime session already has an active invocation"
            ) from exc
        prepared = prepare(invocation) if prepare is not None else invocation
        try:
            return _run_locked(prepared, emit=emit, interrupted=interrupted, confirmed=confirmed)
        except (DshAcpProtocolError, TimeoutError) as exc:
            reason = str(exc) if isinstance(exc, DshAcpProtocolError) else "ACP request timed out"
            diagnostics = dsh_diagnostic_tail(prepared.turn_dir / "provider-stderr.log")
            secret_values = (*dsh_diagnostic_secrets(prepared.environment), *prepared.secret_values)
            summary = sanitize_dsh_diagnostic(diagnostics, secret_values=secret_values)
            if summary:
                raise DshAcpProtocolError(f"{reason}. Worker stderr: {summary}") from None
            if isinstance(exc, TimeoutError):
                raise DshAcpProtocolError(reason) from None
            raise
    finally:
        os.close(descriptor)


def _run_locked(
    invocation: DshAcpInvocation,
    *,
    emit: Callable[[dict[str, Any]], None],
    interrupted: threading.Event,
    confirmed: Callable[[], None],
) -> DshAcpOutcome:
    """Own the connection until native close and process reaping have settled."""

    session_id = invocation.session_id
    connection: DshAcpConnection | None = None
    raw_path = invocation.turn_dir / "provider-stdout.jsonl"
    receipt = _NativeReceipts(invocation)
    closed = False
    with (
        _open_private_diagnostics(raw_path) as raw,
        _open_private_diagnostics(invocation.turn_dir / "provider-stderr.log") as stderr,
    ):

        def permission(method: str, params: dict[str, Any]) -> dict[str, Any]:
            """Answer only requests belonging to the already selected session."""

            if session_id is None:
                raise DshAcpProtocolError("ACP interaction arrived before session selection")
            return reject_dsh_acp_permission(method, params, session_id=session_id)

        def frame(line: str) -> None:
            """Preserve native stdout unchanged in its private provider artifact."""

            raw.write(line)
            raw.flush()

        def stderr_line(line: str) -> None:
            """Keep raw worker stderr available for private inspection."""

            stderr.write(line)
            stderr.flush()

        try:
            _require_dispatch(invocation)
            connection = DshAcpConnection.from_command(
                invocation.command,
                cwd=invocation.working_directory,
                env=invocation.environment,
                request_handler=permission,
                frame_sink=frame,
                stderr_sink=stderr_line,
                secret_values=invocation.secret_values,
            )
            receipt.bind_process(connection.process.pid)
            result = connection.request(
                "initialize",
                {
                    "protocolVersion": 1,
                    "clientInfo": {"name": "houmao", "version": "1"},
                    "clientCapabilities": {},
                },
            ).result(timeout=invocation.setup_timeout)
            validate_dsh_acp_initialization(result, require_resume=session_id is not None)
            params: dict[str, Any] = {
                "cwd": str(invocation.working_directory.resolve()),
                "mcpServers": list(invocation.mcp_servers),
            }
            if session_id is not None:
                params["sessionId"] = session_id
            selected = connection.request(
                "session/resume" if session_id is not None else "session/new", params
            ).result(timeout=invocation.setup_timeout)
            if session_id is None:
                value = selected.get("sessionId")
                if not isinstance(value, str) or not value:
                    raise DshAcpProtocolError("DSH session creation returned no native identity")
                session_id = value
            elif selected.get("sessionId", session_id) != session_id:
                raise DshAcpProtocolError("DSH resume returned a different native session")
            receipt.bind_session(session_id)
            _write_private_json(
                invocation.turn_dir / "dsh-native-binding.json",
                {
                    "version": 1,
                    "attempt_id": invocation.attempt_id,
                    "runtime_session_id": invocation.runtime_session_id,
                    "generation": invocation.generation,
                    "native_session_id": session_id,
                    "working_directory": str(invocation.working_directory.resolve()),
                    "process_id": connection.process.pid,
                    "process_birth_token": connection.process_birth_token,
                    "evidence_path": str(invocation.evidence_path),
                    "persistence_root": str(invocation.persistence_root)
                    if invocation.persistence_root is not None
                    else None,
                    "source_revision": "39163dd30f703a79079e2d2446545cff3c453738",
                },
            )
            emit({"type": "session_init", "session_id": session_id})
            _select_native_configuration(connection, invocation, selected, session_id)
            _drain_updates(connection, session_id, emit)
            if interrupted.is_set():
                raise DshAcpProtocolError("DSH attempt was interrupted before native input")
            _require_dispatch(invocation)
            pending = connection.request(
                "session/prompt",
                {"sessionId": session_id, "prompt": [{"type": "text", "text": invocation.prompt}]},
            )
            admitted = False
            cancel_deadline: float | None = None
            while not pending.done():
                _drain_updates(connection, session_id, emit)
                if not admitted and receipt.has_admission():
                    confirmed()
                    admitted = True
                if interrupted.is_set() and cancel_deadline is None:
                    connection.notify("session/cancel", {"sessionId": session_id})
                    cancel_deadline = time.monotonic() + invocation.cancellation_timeout
                if cancel_deadline is not None and time.monotonic() >= cancel_deadline:
                    raise DshAcpProtocolError("DSH native cancellation did not settle")
                if not admitted and invocation.dispatch_guard is not None:
                    _require_dispatch(invocation)
                time.sleep(0.01)
            terminal = _settlement(pending)
            _drain_updates(connection, session_id, emit)
            if not admitted:
                confirmed()
                admitted = True
            emit({"type": "native_result", "session_id": session_id, "stop_reason": terminal})
            connection.request("session/close", {"sessionId": session_id}).result(
                timeout=invocation.close_timeout
            )
            closed = True
            return DshAcpOutcome(session_id, terminal, admitted)
        finally:
            if connection is not None:
                primary_error = sys.exception()
                cleanup_error: Exception | None = None
                try:
                    if session_id is not None and not closed:
                        connection.request("session/close", {"sessionId": session_id}).result(
                            timeout=invocation.close_timeout
                        )
                except Exception as exc:
                    cleanup_error = exc
                    emit(
                        {
                            "type": "driver_cleanup_error",
                            "stage": "native_close",
                            "error_kind": type(exc).__name__,
                            "message": "DSH native closure could not be confirmed",
                        }
                    )
                try:
                    connection.close(timeout=invocation.close_timeout)
                except Exception as exc:
                    cleanup_error = cleanup_error or exc
                    emit(
                        {
                            "type": "driver_cleanup_error",
                            "stage": "process_cleanup",
                            "error_kind": type(exc).__name__,
                            "message": "DSH process cleanup failed",
                        }
                    )
                if primary_error is None and cleanup_error is not None:
                    raise cleanup_error
                if primary_error is None and closed and connection.process.returncode != 0:
                    raise DshAcpProtocolError(
                        "DSH worker exited unsuccessfully after native closure"
                    )


def _open_private_diagnostics(path: Path) -> TextIO:
    """Create a user-private provider log without reopening an earlier artifact."""

    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    return os.fdopen(descriptor, "w", encoding="utf-8")


def _settlement(pending: Future[dict[str, Any]]) -> str:
    """Validate a correlated native outcome without flattening incomplete work."""

    result = pending.result()
    reason = result.get("stopReason")
    if not isinstance(reason, str) or not reason:
        raise DshAcpProtocolError("ACP prompt settled without a stop reason")
    return reason


def _select_native_configuration(
    connection: DshAcpConnection,
    invocation: DshAcpInvocation,
    selected: dict[str, Any],
    session_id: str,
) -> None:
    """Select advertised opaque route and effort values before resumed work begins."""

    state = selected
    for config_id, desired in (
        ("model", invocation.model),
        ("reasoning_effort", invocation.reasoning_effort),
    ):
        if desired is None:
            continue
        options = state.get("configOptions", [])
        if not isinstance(options, list):
            raise DshAcpProtocolError("DSH returned invalid native configuration options")
        option = next(
            (
                entry
                for entry in options
                if isinstance(entry, dict) and entry.get("id") == config_id
            ),
            None,
        )
        if option is None or option.get("type") != "select":
            raise DshAcpProtocolError(f"DSH does not advertise the requested {config_id} selection")
        choices: list[Any] = list(option.get("options", []))
        value: str | None = None
        while choices:
            choice = choices.pop(0)
            if not isinstance(choice, dict):
                raise DshAcpProtocolError("DSH returned an invalid native configuration choice")
            if "options" in choice:
                if not isinstance(choice["options"], list):
                    raise DshAcpProtocolError("DSH returned an invalid native configuration group")
                choices.extend(choice["options"])
                continue
            opaque = choice.get("value")
            if not isinstance(opaque, str):
                continue
            if config_id == "model":
                try:
                    matches = json.loads(opaque) == list(desired)
                except (ValueError, TypeError):
                    matches = False
            else:
                matches = opaque == desired
            if matches:
                value = opaque
                break
        if value is None:
            raise DshAcpProtocolError(
                f"Requested DSH {config_id} is absent from the native catalog"
            )
        if option.get("currentValue") == value:
            continue
        state = connection.request(
            "session/set_config_option",
            {"sessionId": session_id, "configId": config_id, "value": value},
        ).result(timeout=invocation.setup_timeout)


def _drain_updates(
    connection: DshAcpConnection, session_id: str, emit: Callable[[dict[str, Any]], None]
) -> None:
    """Project only the selected native session's semantic notifications."""

    while (frame := connection.next_notification()) is not None:
        params = frame.get("params", {})
        if frame.get("method") == "session/update" and params.get("sessionId") == session_id:
            emit(
                {
                    "type": "session_update",
                    "session_id": session_id,
                    "update": params.get("update", {}),
                }
            )


def _require_dispatch(invocation: DshAcpInvocation) -> None:
    """Recheck the existing payload-free permission before native submission."""

    if invocation.dispatch_guard is not None and not headless_dispatch_permission_allowed(
        invocation.dispatch_guard
    ):
        raise DshAcpProtocolError("DSH dispatch permission is unavailable or revoked")


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    """Publish durable native identity before admitting any user input."""

    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream)
        stream.flush()
        os.fsync(stream.fileno())


class _NativeReceipts:
    """Validate private companion evidence against this exact worker and attempt."""

    def __init__(self, invocation: DshAcpInvocation) -> None:
        """Initialize receipt reading before a worker is started."""

        self.m_invocation: DshAcpInvocation = invocation
        self.m_process_id: int | None = None
        self.m_session_id: str | None = None
        self.m_host_incarnation: str | None = None
        self.m_agent_incarnation: str | None = None

    def bind_process(self, process_id: int) -> None:
        """Record the process directly owned by the ACP connection."""

        self.m_process_id = process_id

    def bind_session(self, session_id: str) -> None:
        """Record the exact native session selected by the correlated response."""

        self.m_session_id = session_id
        if not any(row["event"] == "created" for row in self._records()):
            raise DshAcpProtocolError("DSH native companion did not publish identity evidence")

    def has_admission(self) -> bool:
        """Recognize bound native insertion or claim, never helper process launch."""

        return any(row["event"] in {"admitted", "claimed"} for row in self._records())

    def _records(self) -> list[dict[str, Any]]:
        """Read complete metadata rows; a partial tail cannot prove handoff."""

        try:
            text = self.m_invocation.evidence_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        rows: list[dict[str, Any]] = []
        for index, line in enumerate(text.splitlines(keepends=True)):
            if not line.endswith("\n"):
                break
            row = json.loads(line)
            if not isinstance(row, dict) or any(
                row.get(key) != expected
                for key, expected in {
                    "version": 1,
                    "sequence": index,
                    "attempt_id": self.m_invocation.attempt_id,
                    "runtime_session_id": self.m_invocation.runtime_session_id,
                    "generation": self.m_invocation.generation,
                    "process_id": self.m_process_id,
                }.items()
            ):
                raise DshAcpProtocolError("DSH native evidence does not match this invocation")
            host = row.get("host_incarnation")
            if not isinstance(host, str) or not host:
                raise DshAcpProtocolError("DSH companion host identity is missing")
            if self.m_host_incarnation is None:
                self.m_host_incarnation = host
            if host != self.m_host_incarnation:
                raise DshAcpProtocolError("DSH companion host identity changed")
            if row.get("event") != "loaded":
                incarnation = row.get("agent_incarnation")
                if self.m_agent_incarnation is None:
                    if not isinstance(incarnation, str) or not incarnation:
                        raise DshAcpProtocolError("DSH native agent identity is missing")
                    self.m_agent_incarnation = incarnation
                if row.get("native_session_id") != self.m_session_id:
                    raise DshAcpProtocolError("DSH receipt belongs to another native session")
                if (
                    not self.m_agent_incarnation
                    or row.get("agent_incarnation") != self.m_agent_incarnation
                ):
                    raise DshAcpProtocolError("DSH receipt belongs to another native agent")
            rows.append(row)
        return rows
