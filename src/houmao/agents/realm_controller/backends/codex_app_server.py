"""Persistent owner-private Codex app-server with exact thread and turn control."""

from __future__ import annotations

from collections import deque
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
import fcntl
import json
import os
from pathlib import Path
import stat
import threading
import time
from typing import Any, TextIO
from uuid import UUID

from packaging.version import InvalidVersion, Version

from houmao.agents.launch_policy import LaunchPolicyError, validate_packaged_tool_version
from houmao.agents.model_selection import ModelConfig
from houmao.agents.realm_controller.backends.dsh_acp_connection import (
    DshAcpConnection,
    DshAcpProtocolError,
    DshAcpRequestError,
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
from houmao.agents.realm_controller.usage_collection import complete_file_position
from houmao.agents.realm_controller.usage_store import UsageStoreError
from houmao.agents.realm_controller.usage_support import UsageService, persist_terminal_evidence
from houmao.cao.no_proxy import inject_loopback_no_proxy_env


_ARGUMENTS = ("app-server", "--listen", "stdio://")
_SETUP_TIMEOUT = 10.0
_WRITE_TIMEOUT = 5.0
_HANDLE_TIMEOUT = 20.0
_PROMPT_TIMEOUT = 300.0
_INTERRUPT_TIMEOUT = 15.0
_MAX_QUEUED_EVENTS = 256
_MAX_EVENT_BUFFER = 4 * 1024 * 1024
_MAX_ITEMS = 256
_MAX_ITEM_CHARS = 128 * 1024
_MAX_ROLLOUT_META = 4 * 1024 * 1024
_SANDBOX_POLICY_TYPES = {
    "read-only": "readOnly",
    "workspace-write": "workspaceWrite",
    "danger-full-access": "dangerFullAccess",
}
_TERMINAL_OUTCOMES: dict[str, ServiceOutcome] = {
    "completed": "completed",
    "failed": "failed",
    "interrupted": "interrupted",
}
_TURN_NOTIFICATIONS = frozenset(
    {"turn/started", "turn/completed", "item/started", "item/completed", "item/agentMessage/delta"}
)
_TOOL_ITEMS = frozenset(
    {"commandExecution", "fileChange", "mcpToolCall", "dynamicToolCall", "collabAgentToolCall"}
)


@dataclass
class _ActiveTurn:
    """One reserved request and its response-correlated event buffer."""

    operation: ServiceOperationContext
    turn_index: int
    authorized: bool = False
    native_turn_id: str | None = None
    hinted_turn_id: str | None = None
    has_client_message: bool = False
    cancelling: bool = False
    terminal: ServiceOutcome | None = None
    rollout_baseline_offset: int = 0
    notifications: deque[tuple[dict[str, Any], int]] = field(default_factory=deque)
    buffered: int = 0
    completed_items: set[str] = field(default_factory=set)
    started_tools: set[str] = field(default_factory=set)
    assistant_deltas: dict[str, str] = field(default_factory=dict)
    events: list[SessionEvent] = field(default_factory=list)


class CodexAppServerProvider:
    """Own one persistent Codex child, one native thread and its managed turn."""

    def __init__(self, config: ServiceOwnerConfig) -> None:
        """Bind expected owner identity before starting its child."""

        self.m_config: ServiceOwnerConfig = config
        self.m_home: Path = config.home_path.resolve()
        self.m_workspace: Path = config.working_directory.resolve()
        self.m_thread_id: str = ""
        self.m_thread_status: str = "unknown"
        self.m_rollout: Path | None = None
        self.m_connection: DshAcpConnection | None = None
        self.m_stderr: TextIO | None = None
        self.m_home_lock: int | None = None
        self.m_condition: threading.Condition = threading.Condition()
        self.m_active: _ActiveTurn | None = None
        self.m_retired_turns: deque[str] = deque(maxlen=256)
        self.m_turn_index: int = 0
        self.m_available: bool = False

    def start(self) -> None:
        """Verify the selected executable and establish its exact native thread."""

        config = self.m_config
        if tuple(config.arguments) != _ARGUMENTS or config.environment.get("CODEX_HOME") != str(
            self.m_home
        ):
            raise BackendExecutionError("Codex service requires the owned private stdio launch")
        metadata = config.metadata.get("codex_app_server")
        if not isinstance(metadata, dict):
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_EXECUTABLE_VERSION)
        detected_version = metadata.get("detected_version")
        try:
            expected_version = validate_packaged_tool_version(
                tool="codex",
                backend="codex_app_server",
                version=detected_version if isinstance(detected_version, str) else None,
            )
        except LaunchPolicyError as exc:
            raise ServiceStartupCompatibilityError(
                ServiceStartupCheck.CODEX_EXECUTABLE_VERSION
            ) from exc
        self.m_home_lock = os.open(
            self.m_home / ".houmao-codex-service.lock",
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
            0o600,
        )
        try:
            fcntl.flock(self.m_home_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BackendExecutionError("Codex home already has a service owner") from None
        stderr_fd = os.open(
            config.root / "provider-stderr.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        self.m_stderr = os.fdopen(stderr_fd, "w", buffering=1, encoding="utf-8")
        environment = dict(config.environment)
        inject_loopback_no_proxy_env(environment)
        self.m_connection = DshAcpConnection.from_command(
            [config.executable, *config.arguments],
            cwd=self.m_workspace,
            env=environment,
            request_handler=self._answer_native_request,
            notification_sink=self._receive,
            stderr_sink=self._diagnostic_line,
            retain_notifications=False,
            write_timeout=_WRITE_TIMEOUT,
            framing="codex",
        )
        try:
            initialized = self._call(
                "initialize",
                {
                    "clientInfo": {"name": "houmao", "version": "1"},
                    "capabilities": {"experimentalApi": False},
                },
            )
            version = _check_handshake(initialized, self.m_home, Version(expected_version.raw))
            self._connection().notify("initialized", {})
        except (DshAcpProtocolError, DshAcpRequestError, TimeoutError) as exc:
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_INITIALIZE) from exc
        try:
            self._bind_thread(config, metadata)
        except ServiceStartupCompatibilityError:
            raise
        except (
            BackendExecutionError,
            DshAcpProtocolError,
            DshAcpRequestError,
            TimeoutError,
        ) as exc:
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_THREAD) from exc
        birth = self.process_birth_token
        if birth is None:
            raise BackendExecutionError("Codex app-server process birth identity is unavailable")
        write_service_record(
            config.root / "codex-app-server-binding.json",
            {
                "version": 1,
                "agent_id": config.agent_id,
                "runtime_session_id": config.runtime_session_id,
                "generation_id": config.generation_id,
                "service_incarnation": config.service_incarnation,
                "native_session_id": self.m_thread_id,
                "process_id": self.process_id,
                "process_birth_token": birth,
                "tool_version": version,
                "working_directory": str(self.m_workspace),
                "rollout_path": str(self.m_rollout) if self.m_rollout else None,
            },
        )
        self.m_available = True

    def _bind_thread(self, config: ServiceOwnerConfig, metadata: dict[str, Any]) -> None:
        """Create or resume a durable thread within the exact home and workspace."""

        parameters: dict[str, Any] = {}
        native_config = metadata.get("thread_config")
        if isinstance(native_config, dict) and native_config:
            parameters["config"] = native_config
        if config.role_prompt:
            parameters["developerInstructions"] = config.role_prompt
        permissions = metadata.get("permissions", {})
        if not isinstance(permissions, dict):
            raise BackendExecutionError("Codex app-server launch permissions are invalid")
        approval_policy = permissions.get("approval_policy")
        if approval_policy is not None:
            if approval_policy not in ("never", "on-request", "untrusted"):
                raise BackendExecutionError("Codex app-server approval policy is invalid")
            parameters["approvalPolicy"] = approval_policy
        sandbox_mode = permissions.get("sandbox_mode")
        if sandbox_mode is not None:
            if not isinstance(sandbox_mode, str) or sandbox_mode not in _SANDBOX_POLICY_TYPES:
                raise BackendExecutionError("Codex app-server sandbox mode is invalid")
            parameters["sandbox"] = sandbox_mode
        expected = config.session_id
        prior_rollout: Path | None = None
        if expected is None:
            parameters.update(cwd=str(self.m_workspace), ephemeral=False)
            response = self._call("thread/start", parameters)
        else:
            exact = _uuid(expected)
            if exact is None:
                raise BackendExecutionError("Codex app-server exact thread identity is invalid")
            historical = self._call("thread/read", {"threadId": exact, "includeTurns": False})
            _, prior_rollout, state = self._thread(historical, expected=exact)
            if state == "active" or not _rollout_matches(prior_rollout, exact, self.m_workspace):
                raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_ROLLOUT)
            parameters.update(threadId=exact, excludeTurns=True)
            response = self._call("thread/resume", parameters)
        thread_id, rollout, state = self._thread(response, expected=expected)
        if not _is_workspace(response.get("cwd"), self.m_workspace) or state != "idle":
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_THREAD)
        if prior_rollout is not None and rollout != prior_rollout:
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_ROLLOUT)
        if approval_policy is not None and response.get("approvalPolicy") != approval_policy:
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_APPROVAL)
        if sandbox_mode is not None:
            sandbox = response.get("sandbox")
            if (
                not isinstance(sandbox, dict)
                or sandbox.get("type") != _SANDBOX_POLICY_TYPES[sandbox_mode]
            ):
                raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_SANDBOX)
        if isinstance(native_config, dict):
            for key, native_key in (("model", "model"), ("model_provider", "modelProvider")):
                value = native_config.get(key)
                if isinstance(value, str) and response.get(native_key) != value:
                    raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_MODEL)
        self.m_thread_id = thread_id
        self.m_thread_status = state
        self.m_rollout = rollout

    def _thread(self, response: dict[str, Any], *, expected: str | None) -> tuple[str, Path, str]:
        """Check native thread identity, cwd, persistence, and its bounded status."""

        thread = response.get("thread")
        if not isinstance(thread, dict):
            raise DshAcpProtocolError("Codex app-server did not return a native thread")
        actual = _uuid(thread.get("id"))
        status = thread.get("status")
        state = status.get("type") if isinstance(status, dict) else None
        if (
            actual is None
            or (expected is not None and actual != expected)
            or not _is_workspace(thread.get("cwd"), self.m_workspace)
            or thread.get("ephemeral") is not False
            or state not in ("idle", "active", "notLoaded", "systemError")
        ):
            raise BackendExecutionError("Codex app-server thread binding does not match the owner")
        path = _rollout_path(thread.get("path"), home=self.m_home, thread_id=actual)
        if path is None:
            raise BackendExecutionError("Codex app-server thread rollout is outside its owned home")
        return actual, path, state

    @property
    def native_session_id(self) -> str:
        """Return the verified Codex thread used as the native session identity."""

        return self.m_thread_id

    @property
    def process_id(self) -> int:
        """Return the exact worker captured by the private transport."""

        return self._connection().process.pid

    @property
    def process_birth_token(self) -> str | None:
        """Return the worker birth identity for managed cleanup."""

        return self._connection().process_birth_token

    @property
    def connection_ready(self) -> bool:
        """Report a live connection and a usable native thread."""

        return (
            self.m_available
            and self._connection().healthy
            and (self.m_active is not None or self.m_thread_status == "idle")
        )

    def prompt(
        self,
        prompt: str,
        *,
        execution_model: ModelConfig | None,
        operation: ServiceOperationContext,
    ) -> ServicePromptResult:
        """Submit exactly one input and wait for its verified terminal notification."""

        if execution_model is not None and not execution_model.is_empty():
            raise BackendExecutionError(
                "Codex service per-prompt execution overrides are unsupported"
            )
        if not prompt.strip():
            raise BackendExecutionError("Codex service requires non-empty prompt text")
        with self.m_condition:
            if not self.connection_ready or self.m_active is not None:
                raise BackendExecutionError("Codex app-server is unavailable or busy")
            self.m_turn_index += 1
            active = _ActiveTurn(operation, self.m_turn_index)
            self.m_active = active
        began = time.monotonic()
        try:
            self._verify_idle()
            birth = self.process_birth_token
            if birth is None:
                raise BackendExecutionError("Codex app-server process authority is unavailable")
            write_service_record(
                operation.turn_dir / "process.json",
                {"child_pid": self.process_id, "child_birth_token": birth},
            )
            usage = self._begin_usage(active)
            start = (
                self._connection()
                .request(
                    "turn/start",
                    {
                        "threadId": self.m_thread_id,
                        "clientUserMessageId": operation.request_id,
                        "input": [{"type": "text", "text": prompt, "textElements": []}],
                    },
                    before_write=lambda: self._authorize(active),
                )
                .result(timeout=_HANDLE_TIMEOUT)
            )
            native_turn = self._bind_turn(active, start)
            operation.confirm_native_handoff(native_turn)
            outcome = self._await_terminal(active, deadline=began + _PROMPT_TIMEOUT)
            self._persist_turn(active, outcome, birth, usage, began)
            return ServicePromptResult(
                events=active.events, outcome=outcome, native_turn_id=native_turn
            )
        except (
            DshAcpProtocolError,
            DshAcpRequestError,
            BackendExecutionError,
            OSError,
            TimeoutError,
            ValueError,
        ):
            if not active.authorized:
                raise
            self.m_available = False
            self._preserve_partial(active)
            active.events.append(
                SessionEvent(
                    "error",
                    "Codex app-server could not verify the native outcome",
                    active.turn_index,
                )
            )
            return ServicePromptResult(
                events=active.events, outcome="uncertain", native_turn_id=active.native_turn_id
            )
        finally:
            with self.m_condition:
                if active.native_turn_id is not None:
                    self.m_retired_turns.append(active.native_turn_id)
                if self.m_active is active:
                    self.m_active = None
                self.m_condition.notify_all()

    def _verify_idle(self) -> None:
        """Refuse to let turn/start steer existing native work."""

        response = self._call("thread/read", {"threadId": self.m_thread_id, "includeTurns": False})
        _, rollout, state = self._thread(response, expected=self.m_thread_id)
        self.m_thread_status = state
        if state != "idle" or rollout != self.m_rollout:
            raise BackendExecutionError("Codex native thread cannot accept a new turn")

    def _authorize(self, active: _ActiveTurn) -> None:
        """Recheck native and owner admission immediately before the pipe write."""

        with self.m_condition:
            if self.m_active is not active or self.m_thread_status != "idle":
                raise BackendExecutionError(
                    "Codex app-server active thread changed before dispatch"
                )
            rollout = self.m_rollout
            if rollout is not None and _rollout_matches(
                rollout, self.m_thread_id, self.m_workspace
            ):
                with suppress(OSError):
                    active.rollout_baseline_offset = complete_file_position(rollout)
            active.operation.authorize_native_write()
            active.authorized = True

    def _bind_turn(self, active: _ActiveTurn, response: dict[str, Any]) -> str:
        """Establish the native turn handle from the correlated RPC response."""

        native = response.get("turn")
        if not isinstance(native, dict):
            raise DshAcpProtocolError("Codex app-server omitted the native turn handle")
        turn_id = _uuid(native.get("id"))
        with self.m_condition:
            if (
                turn_id is None
                or native.get("status") != "inProgress"
                or self.m_active is not active
                or turn_id in self.m_retired_turns
            ):
                raise DshAcpProtocolError(
                    "Codex app-server returned an invalid or mismatched turn handle"
                )
            active.native_turn_id = turn_id
            return turn_id

    def _receive(self, frame: dict[str, Any], size: int) -> None:
        """Buffer only bounded notifications from the exact native thread."""

        method = frame["method"]
        params = frame.get("params", {})
        if params.get("threadId") != self.m_thread_id:
            return
        with self.m_condition:
            if method == "thread/status/changed":
                status = params.get("status")
                if isinstance(status, dict) and status.get("type") in (
                    "idle",
                    "active",
                    "notLoaded",
                    "systemError",
                ):
                    self.m_thread_status = status["type"]
                return
            active = self.m_active
            if (
                active is None
                or not active.authorized
                or active.terminal
                or method not in _TURN_NOTIFICATIONS
            ):
                return
            turn_id = _notification_turn(frame)
            if (
                turn_id is None
                or turn_id in self.m_retired_turns
                or active.native_turn_id not in (None, turn_id)
            ):
                return
            if method == "turn/started" and active.native_turn_id is None:
                if active.hinted_turn_id not in (None, turn_id):
                    raise DshAcpProtocolError("Codex app-server reported two candidate turns")
                active.hinted_turn_id = turn_id
            if (
                len(active.notifications) >= _MAX_QUEUED_EVENTS
                or active.buffered + size > _MAX_EVENT_BUFFER
            ):
                raise DshAcpProtocolError("Codex app-server notification buffer exceeded its bound")
            active.notifications.append((frame, size))
            active.buffered += size
            self.m_condition.notify_all()

    def _await_terminal(self, active: _ActiveTurn, *, deadline: float) -> ServiceOutcome:
        """Keep reading the owned turn through a typed terminal or bounded loss."""

        while True:
            with self.m_condition:
                if active.notifications:
                    frame, size = active.notifications.popleft()
                    active.buffered -= size
                else:
                    if time.monotonic() >= deadline or not self._connection().healthy:
                        raise DshAcpProtocolError("Codex app-server turn settlement unavailable")
                    self.m_condition.wait(timeout=0.05)
                    continue
            if _notification_turn(frame) != active.native_turn_id:
                continue
            outcome = self._turn_event(active, frame)
            if outcome is not None:
                return outcome

    def _turn_event(self, active: _ActiveTurn, frame: dict[str, Any]) -> ServiceOutcome | None:
        """Map stable item and terminal events without double-counting text."""

        method, params = frame["method"], frame["params"]
        if method == "item/agentMessage/delta":
            item_id, delta = params.get("itemId"), params.get("delta")
            if (
                isinstance(item_id, str)
                and isinstance(delta, str)
                and item_id not in active.completed_items
            ):
                if item_id in active.assistant_deltas or len(active.assistant_deltas) < _MAX_ITEMS:
                    previous = active.assistant_deltas.get(item_id, "")
                    active.assistant_deltas[item_id] = (previous + delta)[:_MAX_ITEM_CHARS]
        elif method == "item/started":
            self._tool_progress(active, params.get("item"), finished=False)
        elif method == "item/completed":
            self._item(active, params.get("item"))
        elif method == "turn/completed":
            turn = params["turn"]
            status = turn.get("status")
            if not isinstance(status, str) or status not in _TERMINAL_OUTCOMES:
                raise DshAcpProtocolError("Codex app-server did not report a terminal turn status")
            outcome = _TERMINAL_OUTCOMES[status]
            if status == "completed" and turn.get("error") is not None:
                raise DshAcpProtocolError("Codex app-server terminal status contradicts its error")
            with self.m_condition:
                active.terminal = outcome
                self.m_thread_status = "idle"
                self.m_condition.notify_all()
            items = turn.get("items")
            if isinstance(items, list):
                for item in items:
                    self._item(active, item)
            self._preserve_partial(active)
            if outcome == "failed":
                self._publish(active, "error", "Codex native turn failed")
            self._publish(
                active, "completion", f"Codex native turn {outcome}", {"native_status": status}
            )
            return outcome
        return None

    def _item(self, active: _ActiveTurn, item: object) -> None:
        """Use completed item identity once and verify available managed user provenance."""

        if not isinstance(item, dict):
            return
        item_id, kind = item.get("id"), item.get("type")
        if not isinstance(item_id, str) or not item_id or item_id in active.completed_items:
            return
        if kind == "userMessage":
            client = item.get("clientId")
            if client is not None and client != active.operation.request_id:
                raise DshAcpProtocolError(
                    "Codex app-server user item belongs to a different caller"
                )
            active.has_client_message |= client == active.operation.request_id
        if len(active.completed_items) >= _MAX_ITEMS:
            raise DshAcpProtocolError("Codex app-server item capacity exceeded")
        active.completed_items.add(item_id)
        if kind == "agentMessage" and isinstance(item.get("text"), str):
            active.assistant_deltas.pop(item_id, None)
            self._publish(active, "assistant", item["text"][:_MAX_ITEM_CHARS], {"item_id": item_id})
        else:
            self._tool_progress(active, item, finished=True)

    def _tool_progress(self, active: _ActiveTurn, item: object, *, finished: bool) -> None:
        """Project tool lifecycle without exposing native arguments or raw output."""

        if not isinstance(item, dict):
            return
        item_id, kind = item.get("id"), item.get("type")
        if not isinstance(item_id, str) or not isinstance(kind, str) or kind not in _TOOL_ITEMS:
            return
        if not finished:
            if item_id in active.started_tools or item_id in active.completed_items:
                return
            if len(active.started_tools) >= _MAX_ITEMS:
                raise DshAcpProtocolError("Codex app-server active tool capacity exceeded")
            active.started_tools.add(item_id)
        phase = "completed" if finished else "started"
        self._publish(
            active,
            "status",
            f"Codex {kind} {phase}",
            {"item_id": item_id, "native_item_type": kind, "native_item_phase": phase},
        )

    def _preserve_partial(self, active: _ActiveTurn) -> None:
        """Keep verified partial assistant output when there is no final item."""

        for item_id, content in active.assistant_deltas.items():
            if content:
                self._publish(active, "assistant", content, {"item_id": item_id, "partial": True})
        active.assistant_deltas.clear()

    def _publish(
        self, active: _ActiveTurn, kind: str, message: str, extra: dict[str, Any] | None = None
    ) -> None:
        """Store canonical request-scoped progress with native turn provenance."""

        event = SessionEvent(
            kind,
            message,
            active.turn_index,
            {
                "native_session_id": self.m_thread_id,
                "native_turn_id": active.native_turn_id,
                **(extra or {}),
            },
        )
        active.events.append(event)
        active.operation.publish_event(event)

    def cancel(self, operation_id: str) -> bool:
        """Send one interrupt for the exact active native thread and turn."""

        with self.m_condition:
            active = self.m_active
            if (
                active is None
                or active.operation.request_id != operation_id
                or active.native_turn_id is None
                or active.cancelling
                or active.terminal
            ):
                return False
            active.cancelling = True
            turn_id = active.native_turn_id
        try:
            deadline = time.monotonic() + _INTERRUPT_TIMEOUT
            guarded = self._connection().request(
                "turn/interrupt",
                {"threadId": self.m_thread_id, "turnId": turn_id},
                before_write=lambda: self._verify_cancel(active),
            )
            guarded.result(timeout=max(0.0, deadline - time.monotonic()))
            with self.m_condition:
                while active.terminal is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or self.m_active is not active:
                        return False
                    self.m_condition.wait(timeout=remaining)
                return active.terminal == "interrupted"
        except (DshAcpRequestError, BackendExecutionError):
            return False
        except (DshAcpProtocolError, TimeoutError):
            if not active.terminal:
                self.m_available = False
            return False

    def _verify_cancel(self, active: _ActiveTurn) -> None:
        """Fence a delayed interrupt at the locked pipe write boundary."""

        with self.m_condition:
            if self.m_active is not active or active.terminal:
                raise BackendExecutionError("Codex native turn settled before interruption")

    def _answer_native_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Decline only supported human interactions on the verified current turn."""

        with self.m_condition:
            active = self.m_active
            turn = _uuid(params.get("turnId"))
            if (
                params.get("threadId") != self.m_thread_id
                or turn is None
                or active is None
                or not active.authorized
                or active.terminal
                or turn != (active.native_turn_id or active.hinted_turn_id)
            ):
                raise NotImplementedError
            if method in (
                "item/commandExecution/requestApproval",
                "item/fileChange/requestApproval",
            ):
                return {"decision": "decline"}
            if method == "item/permissions/requestApproval":
                return {"permissions": {}, "scope": "turn"}
            if method == "item/tool/requestUserInput":
                return {"answers": {}}
        raise NotImplementedError

    def _begin_usage(self, active: _ActiveTurn) -> UsageService | None:
        """Preserve an accounting baseline before sending the prompt."""

        try:
            usage = UsageService.from_manifest(self.m_config.manifest_path)
            usage.begin_headless_turn(
                turn_id=active.operation.request_id,
                turn_dir=active.operation.turn_dir,
                turn_index=active.turn_index,
                new_session=False,
            )
            return usage
        except (OSError, ValueError, UsageStoreError):
            return None

    def _persist_turn(
        self,
        active: _ActiveTurn,
        outcome: ServiceOutcome,
        birth: str,
        usage: UsageService | None,
        began: float,
    ) -> None:
        """Persist exact native outcome and separate optional rollout accounting."""

        config = self.m_config
        timestamp = datetime.now(UTC).isoformat()
        rollout = self.m_rollout
        write_service_record(
            active.operation.turn_dir / "codex-native-turn.json",
            {
                "version": 1,
                "agent_id": config.agent_id,
                "runtime_session_id": config.runtime_session_id,
                "generation_id": config.generation_id,
                "service_incarnation": config.service_incarnation,
                "request_id": active.operation.request_id,
                "native_session_id": self.m_thread_id,
                "native_turn_id": active.native_turn_id,
                "native_client_message_id": active.operation.request_id
                if active.has_client_message
                else None,
                "process_id": self.process_id,
                "process_birth_token": birth,
                "working_directory": str(self.m_workspace),
                "rollout_baseline_offset": active.rollout_baseline_offset,
                "rollout_path": (
                    str(rollout)
                    if rollout is not None
                    and _rollout_matches(rollout, self.m_thread_id, self.m_workspace)
                    else None
                ),
                "terminal": outcome,
                "settled_at_utc": timestamp,
            },
        )
        if usage is not None:
            with suppress(OSError, ValueError, UsageStoreError):
                persist_terminal_evidence(
                    active.operation.turn_dir,
                    returncode=0 if outcome == "completed" else 1,
                    completed_at_utc=timestamp,
                    wall_time_ms=(time.monotonic() - began) * 1000,
                    interrupted=outcome == "interrupted",
                )
                usage.finalize_headless_turn(
                    active.operation.turn_dir, provider_session_id=self.m_thread_id
                )

    def close(self) -> None:
        """Close private stdio and reap the exact owned process on explicit stop."""

        self.m_available = False
        try:
            if self.m_connection is not None:
                self.m_connection.close(timeout=3.0)
        finally:
            if self.m_stderr is not None:
                self.m_stderr.close()
            if self.m_home_lock is not None:
                os.close(self.m_home_lock)
                self.m_home_lock = None

    def _call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Issue one bounded native handshake or read request."""

        return self._connection().request(method, params).result(timeout=_SETUP_TIMEOUT)

    def _connection(self) -> DshAcpConnection:
        """Return the explicitly started private stdio transport."""

        if self.m_connection is None:
            raise BackendExecutionError("Codex app-server process has not started")
        return self.m_connection

    def _diagnostic_line(self, line: str) -> None:
        """Keep native stderr private and continuously drained."""

        if self.m_stderr is not None:
            self.m_stderr.write(line)


def create_codex_service_provider(config: ServiceOwnerConfig) -> ServiceProvider:
    """Create one Codex provider and clean up any partial startup."""

    provider = CodexAppServerProvider(config)
    try:
        provider.start()
    except BaseException:
        with suppress(Exception):
            provider.close()
        raise
    return provider


def _check_handshake(response: dict[str, Any], home: Path, expected_version: Version) -> str:
    """Verify the private home and identify the live build from the native handshake."""

    user_agent = response.get("userAgent")
    token = user_agent.partition(" ")[0] if isinstance(user_agent, str) else ""
    client, _, reported_version = token.partition("/")
    if client != "houmao" or not reported_version:
        raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_HANDSHAKE)
    try:
        version = Version(reported_version)
    except InvalidVersion as exc:
        raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_HANDSHAKE) from exc
    if version != expected_version:
        raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_VERSION)
    if not _is_workspace(response.get("codexHome"), home):
        raise ServiceStartupCompatibilityError(ServiceStartupCheck.CODEX_HOME)
    return reported_version


def _uuid(value: object) -> str | None:
    """Keep canonical native UUID strings and refuse empty or malformed selectors."""

    if not isinstance(value, str):
        return None
    try:
        return value if str(UUID(value)) == value else None
    except ValueError:
        return None


def _is_workspace(value: object, workspace: Path) -> bool:
    """Require the peer's absolute announced directory to be the selected directory."""

    if not isinstance(value, str) or not Path(value).is_absolute():
        return False
    try:
        return Path(value).resolve(strict=True) == workspace
    except (OSError, RuntimeError, ValueError):
        return False


def _rollout_path(value: object, *, home: Path, thread_id: str) -> Path | None:
    """Select only the thread-qualified native rollout inside the private sessions tree."""

    if not isinstance(value, str):
        return None
    path = Path(value)
    if (
        not path.is_absolute()
        or not path.is_relative_to(home / "sessions")
        or path.resolve() != path
        or not path.name.startswith("rollout-")
        or not path.name.endswith(f"-{thread_id}.jsonl")
    ):
        return None
    return path


def _rollout_matches(path: Path, thread_id: str, workdir: Path) -> bool:
    """Verify durable native metadata before exact resume or usage association."""

    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o022
            ):
                return False
            raw = stream.readline(_MAX_ROLLOUT_META + 1)
            if not raw.endswith(b"\n") or len(raw) > _MAX_ROLLOUT_META:
                return False
        row = json.loads(raw)
        if not isinstance(row, dict) or row.get("type") != "session_meta":
            return False
        meta = row.get("payload")
        return (
            isinstance(meta, dict)
            and meta.get("id") == thread_id
            and _is_workspace(meta.get("cwd"), workdir)
        )
    except (OSError, ValueError):
        return False


def _notification_turn(frame: dict[str, Any]) -> str | None:
    """Extract the exact native turn from typed stable notification forms."""

    params = frame.get("params", {})
    if frame.get("method") in ("turn/started", "turn/completed"):
        turn = params.get("turn")
        return _uuid(turn.get("id")) if isinstance(turn, dict) else None
    return _uuid(params.get("turnId"))
