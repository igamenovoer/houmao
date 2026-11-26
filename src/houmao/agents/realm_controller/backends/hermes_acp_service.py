"""Persistent Hermes ACP adaptation over the owned bidirectional transport."""

from __future__ import annotations

from concurrent.futures import Future
from contextlib import suppress
from dataclasses import dataclass, field
import os
import threading
import time
from typing import Any, TextIO

from houmao.agents.hermes_configuration import HERMES_API_KEY_ENV
from houmao.agents.model_selection import ModelConfig
from houmao.agents.realm_controller.backends.dsh_acp_connection import (
    DshAcpConnection,
    DshAcpProtocolError,
    DshAcpRequestError,
)
from houmao.agents.realm_controller.backends.hermes_native import (
    HermesDaemon,
    HermesDaemonIdentity,
    hermes_daemon_environment,
)
from houmao.agents.realm_controller.backends.service_runtime import (
    ServiceOperationContext,
    ServiceOutcome,
    ServiceOwnerConfig,
    ServicePromptResult,
    ServiceProvider,
    write_service_record,
)
from houmao.agents.realm_controller.errors import (
    BackendExecutionError,
    ServiceStartupCheck,
    ServiceStartupCompatibilityError,
)
from houmao.agents.realm_controller.models import SessionEvent


_START_TIMEOUT = 30.0
_PROMPT_TIMEOUT = 300.0
_CANCEL_TIMEOUT = 20.0
_OUTPUT_LIMIT = 1024 * 1024
_TOOL_EVENT_LIMIT = 256
_TOOL_KINDS = frozenset(
    {
        "read",
        "edit",
        "delete",
        "move",
        "search",
        "execute",
        "think",
        "fetch",
        "switch_mode",
        "other",
    }
)


@dataclass
class _AcpPrompt:
    """Retain the matching response and notifications from one request interval."""

    request_id: str
    response: Future[dict[str, Any]] | None = None
    cancel_deadline: float | None = None
    text_chunks: list[str] = field(default_factory=list)
    text_size: int = 0
    tools: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    tool_events: list[SessionEvent] = field(default_factory=list)


class HermesAcpServiceProvider:
    """Own an ACP client bound to one logical conversation and its native gateway."""

    def __init__(self, config: ServiceOwnerConfig) -> None:
        """Retain the selected private home and service identity."""

        self.m_config: ServiceOwnerConfig = config
        self.m_daemon: HermesDaemon = HermesDaemon.from_inputs(
            executable=config.executable,
            home=config.home_path,
            workspace=config.working_directory,
            env=config.environment,
            root=config.root,
        )
        self.m_daemon_identity: HermesDaemonIdentity | None = None
        self.m_connection: DshAcpConnection | None = None
        self.m_log: TextIO | None = None
        self.m_session_id: str = ""
        self.m_ready: bool = False
        self.m_active: _AcpPrompt | None = None
        self.m_lock: threading.Lock = threading.Lock()
        self.m_turn_index: int = 0
        self.m_api_key: str | None = config.environment.get(HERMES_API_KEY_ENV)

    def start(self) -> None:
        """Open ACP and verify the native workspace before publishing readiness."""

        config = self.m_config
        if config.arguments != ["acp"]:
            raise BackendExecutionError("Hermes service requires the native ACP command")
        try:
            self.m_daemon_identity = self.m_daemon.ensure()
            if config.session_id is not None:
                self.m_daemon.resolve_session(config.session_id)
        except (BackendExecutionError, OSError, ValueError) as exc:
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.HERMES_DAEMON) from exc

        try:
            descriptor = os.open(
                config.root / "provider-stderr.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            self.m_log = os.fdopen(descriptor, "w", encoding="utf-8", buffering=1)
            self.m_connection = DshAcpConnection.from_command(
                [config.executable, "acp"],
                cwd=config.working_directory,
                env=hermes_daemon_environment(config.home_path, config.environment),
                request_handler=self._handle_request,
                notification_sink=self._retain_notification,
                stderr_sink=self._append_diagnostic,
                secret_values=(self.m_api_key,) if self.m_api_key else (),
                retain_notifications=False,
                write_timeout=5.0,
            )
        except (OSError, ValueError) as exc:
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.HERMES_PROCESS) from exc

        initialized = self._startup_request(
            "initialize",
            {
                "protocolVersion": 1,
                "clientInfo": {"name": "houmao", "version": "1"},
                "clientCapabilities": {},
            },
            ServiceStartupCheck.HERMES_INITIALIZE,
        )
        if (
            type(initialized.get("protocolVersion")) is not int
            or initialized["protocolVersion"] != 1
        ):
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.HERMES_INITIALIZE)
        capabilities = initialized.get("agentCapabilities", {})
        if not isinstance(capabilities, dict):
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.HERMES_INITIALIZE)
        parameters: dict[str, Any] = {
            "cwd": str(config.working_directory.resolve()),
            "mcpServers": [],
        }
        method = "session/new"
        if config.session_id is not None:
            if capabilities.get("loadSession") is not True:
                raise ServiceStartupCompatibilityError(ServiceStartupCheck.HERMES_SESSION)
            method = "session/load"
            parameters["sessionId"] = config.session_id
        selected = self._startup_request(method, parameters, ServiceStartupCheck.HERMES_SESSION)
        actual = selected.get("sessionId", config.session_id)
        if not isinstance(actual, str) or not actual or config.session_id not in {None, actual}:
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.HERMES_SESSION)

        try:
            self.m_daemon.resolve_session(actual)
            adopted = self.m_daemon.discover()
        except (BackendExecutionError, OSError, ValueError) as exc:
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.HERMES_SESSION) from exc
        if adopted is None:
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.HERMES_DAEMON)
        self.m_daemon_identity = adopted
        self.m_session_id = actual
        write_service_record(
            config.root / "hermes-acp-binding.json",
            {
                "native_session_id": actual,
                "generation_id": config.generation_id,
                "service_incarnation": config.service_incarnation,
                "workspace": str(config.working_directory.resolve()),
                "protocol_version": 1,
                "binding_method": method,
            },
        )
        self.m_ready = True

    @property
    def native_session_id(self) -> str:
        """Return the verified logical Hermes conversation."""

        return self.m_session_id

    @property
    def connection_ready(self) -> bool:
        """Report whether the initialized ACP client is still available."""

        if not self.m_ready or self.m_connection is None or not self.m_connection.healthy:
            return False
        try:
            return self.m_daemon.discover() == self.m_daemon_identity
        except (BackendExecutionError, OSError, ValueError):
            return False

    @property
    def process_id(self) -> int:
        """Return the ACP process identified at startup."""

        return self._connection().process.pid

    @property
    def process_birth_token(self) -> str | None:
        """Return the native client's captured birth token."""

        return self._connection().process_birth_token

    def prompt(
        self,
        prompt: str,
        *,
        execution_model: ModelConfig | None,
        operation: ServiceOperationContext,
    ) -> ServicePromptResult:
        """Submit one ordinary prompt through ACP and settle its correlated response."""

        if execution_model is not None and not execution_model.is_empty():
            raise BackendExecutionError("Hermes ACP uses the launch-selected model")
        if not prompt.strip() or prompt.lstrip().startswith("/"):
            raise BackendExecutionError("Hermes ACP requires ordinary prompt text")
        if self.m_daemon.discover() != self.m_daemon_identity:
            self.m_ready = False
            raise BackendExecutionError("Hermes ACP native gateway changed. Relaunch the service.")
        if not self.m_daemon.resolve_session(self.m_session_id).ready:
            raise BackendExecutionError("Hermes ACP native conversation is busy or unresolved")
        active = _AcpPrompt(operation.request_id)
        authorized = False

        def authorize() -> None:
            """Record that the request may reach the provider before writing the frame."""

            nonlocal authorized
            operation.authorize_native_write()
            authorized = True

        try:
            with self.m_lock:
                if self.m_active is not None or not self.connection_ready:
                    raise BackendExecutionError("Hermes ACP is busy or unavailable")
                self.m_active = active
                self.m_turn_index += 1
                active.response = self._connection().request(
                    "session/prompt",
                    {
                        "sessionId": self.m_session_id,
                        "prompt": [{"type": "text", "text": prompt}],
                    },
                    before_write=authorize,
                )
            stop_reason = self._await_prompt(active)
            if self.m_daemon.discover() != self.m_daemon_identity:
                raise BackendExecutionError("Hermes gateway changed during the ACP operation")
            if stop_reason == "cancelled" and active.cancel_deadline is None:
                # Hermes also reports this reason while reconciling older unresolved work.
                raise BackendExecutionError("Hermes ACP did not establish the cancelled operation")
            outcomes: dict[str, ServiceOutcome] = {
                "end_turn": "completed",
                "max_tokens": "completed",
                "max_turn_requests": "completed",
                "cancelled": "interrupted",
                "refusal": "failed",
            }
            if not isinstance(stop_reason, str) or stop_reason not in outcomes:
                raise BackendExecutionError("Hermes ACP returned an unsupported prompt result")
            operation.confirm_native_handoff()
            text = "".join(active.text_chunks)
            if self.m_api_key:
                text = text.replace(self.m_api_key, "[redacted]")
            events = active.tool_events[:]
            if text and outcomes[stop_reason] == "completed":
                events.append(SessionEvent("assistant", text, self.m_turn_index))
            return ServicePromptResult(events=events, outcome=outcomes[stop_reason])
        except (
            BackendExecutionError,
            DshAcpProtocolError,
            DshAcpRequestError,
            OSError,
            TimeoutError,
            ValueError,
        ):
            if not authorized:
                raise
            self.m_ready = False
            return ServicePromptResult(
                events=[
                    SessionEvent(
                        "error", "Hermes ACP could not verify the native outcome", self.m_turn_index
                    )
                ],
                outcome="uncertain",
            )
        finally:
            with self.m_lock:
                if self.m_active is active:
                    self.m_active = None

    def cancel(self, operation_id: str) -> bool:
        """Ask the ACP viewer to cancel its exact pending prompt."""

        with self.m_lock:
            active = self.m_active
            if (
                active is None
                or active.request_id != operation_id
                or active.response is None
                or active.response.done()
                or active.cancel_deadline is not None
            ):
                return False
            try:
                self._connection().notify("session/cancel", {"sessionId": self.m_session_id})
            except (DshAcpProtocolError, OSError, ValueError):
                self.m_ready = False
                return False
            active.cancel_deadline = time.monotonic() + _CANCEL_TIMEOUT
            return True

    def close(self) -> None:
        """Reap the ACP client and stop the verified managed daemon."""

        self.m_ready = False
        try:
            if self.m_connection is not None:
                self.m_connection.close()
        finally:
            try:
                if self.m_daemon_identity is not None:
                    self.m_daemon.stop()
            finally:
                if self.m_log is not None:
                    self.m_log.close()

    def _startup_request(
        self, method: str, parameters: dict[str, Any], check: ServiceStartupCheck
    ) -> dict[str, Any]:
        """Use the normal service startup diagnostic for a failed handshake."""

        try:
            return self._connection().request(method, parameters).result(timeout=_START_TIMEOUT)
        except (DshAcpProtocolError, DshAcpRequestError, OSError, TimeoutError, ValueError) as exc:
            raise ServiceStartupCompatibilityError(check) from exc

    def _await_prompt(self, active: _AcpPrompt) -> object:
        """Allow reverse interactions and bounded cancellation while waiting for settlement."""

        response = active.response
        assert response is not None
        deadline = time.monotonic() + _PROMPT_TIMEOUT
        while True:
            remaining = min(deadline, active.cancel_deadline or deadline) - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Hermes ACP prompt settlement timed out")
            try:
                return response.result(timeout=min(0.1, remaining)).get("stopReason")
            except TimeoutError:
                continue

    def _retain_notification(self, frame: dict[str, Any], _size: int) -> None:
        """Collect selected-session text and tool state during the active prompt."""

        if frame.get("method") != "session/update":
            return
        params = frame.get("params")
        if not isinstance(params, dict) or params.get("sessionId") != self.m_session_id:
            return
        update = params.get("update")
        if not isinstance(update, dict):
            return
        with self.m_lock:
            active = self.m_active
            if active is None or active.response is None or active.response.done():
                return
            kind = update.get("sessionUpdate")
            if kind in ("tool_call", "tool_call_update"):
                self._retain_tool_update(active, update)
                return
            content = update.get("content")
            if kind != "agent_message_chunk" or not isinstance(content, dict):
                return
            text = content.get("text")
            if content.get("type") != "text" or not isinstance(text, str):
                return
            retained = text[: max(0, _OUTPUT_LIMIT - active.text_size)]
            if retained:
                active.text_chunks.append(retained)
                active.text_size += len(retained)

    def _retain_tool_update(self, active: _AcpPrompt, update: dict[str, Any]) -> None:
        """Project status without retaining tool titles, inputs, or outputs."""

        native_id = update.get("toolCallId")
        status = update.get("status", "pending")
        if (
            len(active.tool_events) >= _TOOL_EVENT_LIMIT
            or not isinstance(native_id, str)
            or not 0 < len(native_id) <= 256
            or status not in ("pending", "in_progress", "completed", "failed")
        ):
            return
        earlier = active.tools.get(native_id)
        if update["sessionUpdate"] == "tool_call":
            if earlier is not None:
                return
            native_kind = update.get("kind")
            kind = (
                native_kind
                if isinstance(native_kind, str) and native_kind in _TOOL_KINDS
                else "other"
            )
            call_id = str(len(active.tools) + 1)
            event_kind = "tool_call"
        else:
            if earlier is None:
                return
            call_id, kind, previous_status = earlier
            if previous_status == status or previous_status in ("completed", "failed"):
                return
            event_kind = "tool_result" if status in ("completed", "failed") else "progress"
        active.tools[native_id] = (call_id, kind, status)
        active.tool_events.append(
            SessionEvent(
                event_kind,
                f"Hermes tool {kind} {status.replace('_', ' ')}",
                self.m_turn_index,
                {"tool_call_id": call_id, "tool_kind": kind, "status": status},
            )
        )

    def _handle_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Decline only using a rejection option advertised for the current session."""

        if method != "session/request_permission":
            raise NotImplementedError
        with self.m_lock:
            active = self.m_active
            options = params.get("options")
            if (
                active is not None
                and active.response is not None
                and not active.response.done()
                and params.get("sessionId") == self.m_session_id
                and isinstance(options, list)
            ):
                for option in options:
                    if isinstance(option, dict) and option.get("kind") == "reject_once":
                        option_id = option.get("optionId")
                        if isinstance(option_id, str) and option_id:
                            return {"outcome": {"outcome": "selected", "optionId": option_id}}
        return {"outcome": {"outcome": "cancelled"}}

    def _connection(self) -> DshAcpConnection:
        """Return the established private transport."""

        if self.m_connection is None:
            raise BackendExecutionError("Hermes ACP has not started")
        return self.m_connection

    def _append_diagnostic(self, line: str) -> None:
        """Write stderr to the private service log."""

        if self.m_log is not None:
            self.m_log.write(line)


def create_hermes_service_provider(config: ServiceOwnerConfig) -> ServiceProvider:
    """Start the provider and clean up partial initialization on failure."""

    provider = HermesAcpServiceProvider(config)
    try:
        provider.start()
    except BaseException:
        with suppress(Exception):
            provider.close()
        raise
    return provider
