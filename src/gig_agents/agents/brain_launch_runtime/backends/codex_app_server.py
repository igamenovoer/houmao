"""Codex app-server backend implementation."""

from __future__ import annotations

import json
import os
import select
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from gig_agents.cao.no_proxy import inject_loopback_no_proxy_env

from ..errors import BackendExecutionError
from ..models import LaunchPlan, SessionControlResult, SessionEvent
from .codex_bootstrap import ensure_codex_home_bootstrap


@dataclass
class CodexSessionState:
    """Mutable Codex backend session state."""

    thread_id: str | None = None
    turn_index: int = 0
    current_turn_id: str | None = None
    pid: int | None = None
    process_started_at_utc: str | None = None


class CodexAppServerSession:
    """Long-lived Codex session over app-server JSON-RPC/stdin-stdout."""

    backend = "codex_app_server"

    def __init__(
        self,
        *,
        launch_plan: LaunchPlan,
        state: CodexSessionState | None = None,
        response_timeout_seconds: float = 60.0,
    ) -> None:
        self._plan = launch_plan
        self._state = state or CodexSessionState()
        self._response_timeout_seconds = response_timeout_seconds
        self._process: subprocess.Popen[str] | None = None
        self._request_id = 0
        self._pending_messages: list[dict[str, Any]] = []

    @property
    def state(self) -> CodexSessionState:
        """Return current mutable backend state."""

        return self._state

    def send_prompt(self, prompt: str) -> list[SessionEvent]:
        """Send one prompt turn to Codex app-server.

        Parameters
        ----------
        prompt:
            User prompt text.

        Returns
        -------
        list[SessionEvent]
            Streaming events emitted during turn execution.
        """

        if not prompt.strip():
            raise BackendExecutionError("Prompt must not be empty")

        self._ensure_started()
        self._ensure_thread_started()

        assert self._state.thread_id is not None
        turn_response = self._rpc_request(
            method="turn/start",
            params={
                "thread_id": self._state.thread_id,
                "input": {"type": "text", "text": prompt},
            },
            timeout_seconds=self._response_timeout_seconds,
        )
        turn_id = _extract_turn_id(turn_response)
        self._state.current_turn_id = turn_id

        events = self._collect_turn_events(turn_id=turn_id)
        self._state.turn_index += 1
        self._state.current_turn_id = None

        if not events or events[-1].kind not in {"done", "error", "interrupted"}:
            events.append(
                SessionEvent(
                    kind="done",
                    message="turn completed",
                    turn_index=self._state.turn_index,
                    payload={"turn_id": turn_id},
                )
            )
        return events

    def interrupt(self) -> SessionControlResult:
        """Best-effort cancel of active turn."""

        if self._process is None or self._process.poll() is not None:
            return SessionControlResult(
                status="ok",
                action="interrupt",
                detail="Codex process is not running",
            )

        if self._state.current_turn_id and self._state.thread_id:
            try:
                self._rpc_request(
                    method="turn/cancel",
                    params={
                        "thread_id": self._state.thread_id,
                        "turn_id": self._state.current_turn_id,
                    },
                    timeout_seconds=3.0,
                )
                return SessionControlResult(
                    status="ok",
                    action="interrupt",
                    detail="Sent turn/cancel request",
                )
            except BackendExecutionError:
                # fall back to terminate below
                pass

        self._process.terminate()
        return SessionControlResult(
            status="ok",
            action="interrupt",
            detail="Terminated Codex process as interruption fallback",
        )

    def terminate(self) -> SessionControlResult:
        """Terminate Codex backend process."""

        if self._process is None or self._process.poll() is not None:
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="Codex process is not running",
            )

        self._process.kill()
        return SessionControlResult(
            status="ok",
            action="terminate",
            detail="Killed Codex process",
        )

    def close(self) -> None:
        """Close the backend process handle."""

        self.terminate()

    def _ensure_started(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return

        env = os.environ.copy()
        env.update(self._plan.env)
        env[self._plan.home_env_var] = str(self._plan.home_path)
        inject_loopback_no_proxy_env(env)
        ensure_codex_home_bootstrap(
            home_path=self._plan.home_path,
            env=env,
            working_directory=self._plan.working_directory,
        )

        command = [self._plan.executable, *self._plan.args]
        self._process = subprocess.Popen(
            command,
            cwd=str(self._plan.working_directory),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._state.pid = self._process.pid
        self._state.process_started_at_utc = datetime.now(UTC).isoformat(timespec="seconds")

    def _ensure_thread_started(self) -> None:
        if self._state.thread_id is not None:
            return

        params: dict[str, Any] = {}
        if self._plan.role_injection.method == "native_developer_instructions":
            params["developer_instructions"] = self._plan.role_injection.prompt

        response = self._rpc_request(
            method="thread/start",
            params=params,
            timeout_seconds=self._response_timeout_seconds,
        )

        thread_id = _extract_thread_id(response)
        if thread_id is None:
            raise BackendExecutionError("thread/start response did not include thread id")
        self._state.thread_id = thread_id

    def _rpc_request(
        self,
        *,
        method: str,
        params: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        process = self._process
        if process is None or process.poll() is not None:
            raise BackendExecutionError("Codex app-server process is not running")

        self._request_id += 1
        request_id = self._request_id
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        assert process.stdin is not None
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()

        deadline = datetime.now(UTC).timestamp() + timeout_seconds
        while datetime.now(UTC).timestamp() < deadline:
            message = self._read_message(timeout_seconds=0.25)
            if message is None:
                continue

            if message.get("id") == request_id:
                if "error" in message:
                    raise BackendExecutionError(f"JSON-RPC {method} failed: {message['error']}")
                result = message.get("result")
                if isinstance(result, dict):
                    return result
                return {"value": result}

            self._pending_messages.append(message)

        raise BackendExecutionError(f"Timed out waiting for JSON-RPC response to {method}")

    def _collect_turn_events(self, *, turn_id: str | None) -> list[SessionEvent]:
        process = self._process
        if process is None:
            raise BackendExecutionError("Codex app-server process is not running")

        events: list[SessionEvent] = []
        timeout_budget_seconds = self._response_timeout_seconds
        deadline = datetime.now(UTC).timestamp() + timeout_budget_seconds

        while datetime.now(UTC).timestamp() < deadline:
            message = self._pop_pending_or_read_message(timeout_seconds=0.25)
            if message is None:
                if process.poll() is not None:
                    break
                continue

            event = _message_to_event(message, turn_index=self._state.turn_index + 1)
            if event is not None:
                events.append(event)

            if _is_turn_terminal_message(message, turn_id=turn_id):
                break

        return events

    def _pop_pending_or_read_message(self, *, timeout_seconds: float) -> dict[str, Any] | None:
        if self._pending_messages:
            return self._pending_messages.pop(0)
        return self._read_message(timeout_seconds=timeout_seconds)

    def _read_message(self, *, timeout_seconds: float) -> dict[str, Any] | None:
        process = self._process
        if process is None or process.stdout is None:
            return None

        stdout = process.stdout
        ready, _, _ = select.select([stdout], [], [], timeout_seconds)
        if not ready:
            return None

        line = stdout.readline()
        if not line:
            return None

        stripped = line.strip()
        if not stripped:
            return None

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return {
                "event": "diagnostic",
                "payload": {"raw": stripped},
            }

        if isinstance(parsed, dict):
            return parsed
        return {
            "event": "diagnostic",
            "payload": {"raw": parsed},
        }


def _extract_thread_id(payload: dict[str, Any]) -> str | None:
    for key in ("thread_id", "threadId", "id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value

    thread = payload.get("thread")
    if isinstance(thread, dict):
        nested = thread.get("id")
        if isinstance(nested, str) and nested:
            return nested
    return None


def _extract_turn_id(payload: dict[str, Any]) -> str | None:
    for key in ("turn_id", "turnId", "id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value

    turn = payload.get("turn")
    if isinstance(turn, dict):
        nested = turn.get("id")
        if isinstance(nested, str) and nested:
            return nested
    return None


def _message_to_event(message: dict[str, Any], *, turn_index: int) -> SessionEvent | None:
    if "method" in message and isinstance(message.get("method"), str):
        method = str(message["method"])
        params = message.get("params")
        payload = params if isinstance(params, dict) else None
        text = ""
        if isinstance(params, dict):
            text = str(params.get("text") or params.get("delta") or params.get("message") or method)
        if not text:
            text = method

        kind = "event"
        if "delta" in method or "output" in method:
            kind = "output"
        if "error" in method:
            kind = "error"
        if method in {"turn/completed", "turn/finished"}:
            kind = "done"
        if method in {"turn/cancelled", "turn/interrupted"}:
            kind = "interrupted"
        return SessionEvent(kind=kind, message=text, turn_index=turn_index, payload=payload)

    if message.get("event") == "diagnostic":
        payload = message.get("payload")
        text = "diagnostic"
        if isinstance(payload, dict) and "raw" in payload:
            text = str(payload["raw"])
        return SessionEvent(
            kind="diagnostic",
            message=text,
            turn_index=turn_index,
            payload=payload if isinstance(payload, dict) else None,
        )

    return None


def _is_turn_terminal_message(message: dict[str, Any], *, turn_id: str | None) -> bool:
    method = message.get("method")
    if isinstance(method, str) and method in {
        "turn/completed",
        "turn/finished",
        "turn/error",
        "turn/cancelled",
        "turn/interrupted",
    }:
        if turn_id is None:
            return True
        params = message.get("params")
        if not isinstance(params, dict):
            return True
        for key in ("turn_id", "turnId", "id"):
            candidate = params.get(key)
            if candidate is None:
                continue
            return str(candidate) == turn_id
        return True

    if "id" in message and "result" in message:
        result = message.get("result")
        if isinstance(result, dict):
            status = result.get("status")
            if status in {"completed", "failed", "cancelled", "interrupted"}:
                return True

    return False


def codex_backend_state_payload(state: CodexSessionState) -> dict[str, Any]:
    """Convert state to manifest backend payload."""

    return {
        "thread_id": state.thread_id,
        "turn_index": state.turn_index,
        "pid": state.pid,
        "process_started_at_utc": state.process_started_at_utc,
    }
