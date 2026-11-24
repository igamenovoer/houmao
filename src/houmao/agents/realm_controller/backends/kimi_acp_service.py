"""Persistent Kimi ACP with owner-qualified stdio and exact native journal settlement."""

from __future__ import annotations

from concurrent.futures import Future
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
import fcntl
import hashlib
import os
from pathlib import Path
import threading
import time
from typing import Any, TextIO

from packaging.version import InvalidVersion, Version

from houmao.agents.kimi_configuration import kimi_launch_diagnostic_secrets
from houmao.agents.launch_policy import LaunchPolicyError, validate_packaged_tool_version
from houmao.agents.model_selection import ModelConfig
from houmao.agents.realm_controller.backends.dsh_acp_connection import (
    DshAcpConnection,
    DshAcpProtocolError,
    DshAcpRequestError,
)
from houmao.agents.realm_controller.backends.kimi_acp_journal import (
    KimiJournalInterval,
    KimiTurnClosure,
    kimi_session_journal,
)
from houmao.agents.realm_controller.backends.service_runtime import (
    ServiceOperationContext,
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
from houmao.agents.realm_controller.usage_store import UsageStoreError
from houmao.agents.realm_controller.usage_support import UsageService, persist_terminal_evidence
from houmao.agents.tool_params.kimi import KIMI_PERMISSION_MODES


_STARTUP_TIMEOUT = 8.0
_PIPE_WRITE_TIMEOUT = 5.0
_PROMPT_TIMEOUT = 300.0
_CANCEL_TIMEOUT = 20.0
_JOURNAL_TIMEOUT = 3.0
_CLOSE_TIMEOUT = 3.0
_STOP_REASONS = frozenset({"end_turn", "cancelled", "max_tokens", "max_turn_requests", "refusal"})


@dataclass
class _ActivePrompt:
    """Identify the one provider operation allowed to use the bound session."""

    request_id: str
    pending: Future[dict[str, Any]] | None = None
    cancel_deadline: float | None = None


class KimiAcpServiceProvider:
    """Own one private Kimi process, one native session, and its current prompt."""

    def __init__(self, config: ServiceOwnerConfig) -> None:
        """Hold immutable service identity before connecting to the executable."""

        self.m_config: ServiceOwnerConfig = config
        self.m_workspace: Path = config.working_directory.resolve()
        self.m_home: Path = config.home_path.resolve()
        self.m_lock: threading.Lock = threading.Lock()
        self.m_home_lock: int | None = None
        self.m_connection: DshAcpConnection | None = None
        self.m_stderr: TextIO | None = None
        self.m_session_id: str = ""
        self.m_journal: Path | None = None
        self.m_close_supported: bool = False
        self.m_available: bool = False
        self.m_active: _ActivePrompt | None = None
        self.m_turn_index: int = 0

    def start(self) -> None:
        """Negotiate and verify one private native session before making it ready."""

        config = self.m_config
        if config.arguments != ["acp"] or config.environment.get("KIMI_CODE_HOME") != str(
            self.m_home
        ):
            raise BackendExecutionError(
                "Kimi service requires its exact native ACP command and home"
            )
        metadata = config.metadata.get("kimi_acp")
        if not isinstance(metadata, dict):
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.KIMI_EXECUTABLE_VERSION)
        detected_version = metadata.get("detected_version")
        try:
            executable_version = validate_packaged_tool_version(
                tool="kimi",
                backend="kimi_acp",
                version=detected_version if isinstance(detected_version, str) else None,
            )
        except LaunchPolicyError as exc:
            raise ServiceStartupCompatibilityError(
                ServiceStartupCheck.KIMI_EXECUTABLE_VERSION
            ) from exc
        permission_mode = metadata.get("permission_mode")
        if permission_mode is not None and permission_mode not in KIMI_PERMISSION_MODES:
            raise BackendExecutionError("Kimi ACP launch permission_mode is invalid")
        self.m_home_lock = os.open(
            self.m_home / ".houmao-kimi-acp.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        try:
            fcntl.flock(self.m_home_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BackendExecutionError("Kimi ACP home already has a service owner") from None
        if config.session_id is not None:
            kimi_session_journal(self.m_home, self.m_workspace, config.session_id)
        self.m_stderr = _open_private_log(config.root / "provider-stderr.log")
        self.m_connection = DshAcpConnection.from_command(
            [config.executable, *config.arguments],
            cwd=self.m_workspace,
            env=config.environment,
            request_handler=self._interaction,
            stderr_sink=self._diagnostic_line,
            secret_values=kimi_launch_diagnostic_secrets(config.environment),
            retain_notifications=False,
            write_timeout=_PIPE_WRITE_TIMEOUT,
        )
        initialized = self._call(
            "initialize",
            {
                "protocolVersion": 1,
                "clientInfo": {"name": "houmao", "version": "1"},
                "clientCapabilities": {},
            },
            check=ServiceStartupCheck.KIMI_INITIALIZE,
        )
        version, capabilities = _initialize(initialized, expected_version=executable_version.raw)
        available = capabilities.get("sessionCapabilities", {})
        self.m_close_supported = isinstance(available.get("close"), dict)
        parameters: dict[str, Any] = {"cwd": str(self.m_workspace), "mcpServers": []}
        method = "session/new"
        exact = config.session_id
        if exact is not None:
            parameters["sessionId"] = exact
            if isinstance(available.get("resume"), dict):
                method = "session/resume"
            elif capabilities.get("loadSession") is True:
                method = "session/load"
            else:
                raise ServiceStartupCompatibilityError(ServiceStartupCheck.KIMI_CONTINUATION)
        selected = self._call(method, parameters, check=ServiceStartupCheck.KIMI_SESSION)
        actual = selected.get("sessionId", exact)
        if not isinstance(actual, str) or (exact is not None and actual != exact):
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.KIMI_SESSION)
        self.m_session_id = actual
        self.m_journal = self._await_journal(actual)
        configured = metadata.get("configured_model")
        model = _advertised_selection(selected, "model")
        if model is None or (isinstance(configured, str) and configured and model != configured):
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.KIMI_MODEL)
        mode = _advertised_selection(selected, "mode")
        expected_mode = "default" if permission_mode == "manual" else permission_mode
        if expected_mode is not None and mode != expected_mode:
            updated = self._call(
                "session/set_config_option",
                {"sessionId": actual, "configId": "mode", "value": expected_mode},
                check=ServiceStartupCheck.KIMI_PERMISSION_MODE,
            )
            mode = _advertised_selection(updated, "mode")
            if mode != expected_mode or _advertised_selection(updated, "model") != model:
                raise ServiceStartupCompatibilityError(ServiceStartupCheck.KIMI_PERMISSION_MODE)
        birth = self.process_birth_token
        if birth is None:
            raise BackendExecutionError("Kimi ACP process birth identity is unavailable")
        write_service_record(
            config.root / "kimi-acp-binding.json",
            {
                "version": 1,
                "generation_id": config.generation_id,
                "service_incarnation": config.service_incarnation,
                "native_session_id": actual,
                "process_id": self.process_id,
                "process_birth_token": birth,
                "tool_version": version,
                "protocol_version": 1,
                "agent_capabilities": capabilities,
                "binding_method": method,
                "working_directory": str(self.m_workspace),
                "selected_model": model,
                "native_mode": mode,
            },
        )
        self.m_available = True

    def _await_journal(self, session_id: str) -> Path:
        """Wait for the selected workspace metadata and its complete journal baseline."""

        deadline = time.monotonic() + _JOURNAL_TIMEOUT
        while True:
            try:
                journal = kimi_session_journal(self.m_home, self.m_workspace, session_id)
                KimiJournalInterval.capture(journal)
                return journal
            except (OSError, BackendExecutionError):
                if time.monotonic() >= deadline or not self._connection().healthy:
                    raise ServiceStartupCompatibilityError(
                        ServiceStartupCheck.KIMI_SESSION
                    ) from None
                time.sleep(0.025)

    @property
    def native_session_id(self) -> str:
        """Return the single verified Kimi session bound to this incarnation."""

        return self.m_session_id

    @property
    def connection_ready(self) -> bool:
        """Report a usable child after binding and before any unresolved mutation."""

        return self.m_available and self._connection().healthy

    @property
    def process_id(self) -> int:
        """Return the captured worker PID instead of discovering processes by name."""

        return self._connection().process.pid

    @property
    def process_birth_token(self) -> str | None:
        """Return the immutable worker birth identity for managed cleanup."""

        return self._connection().process_birth_token

    def prompt(
        self,
        prompt: str,
        *,
        execution_model: ModelConfig | None,
        operation: ServiceOperationContext,
    ) -> ServicePromptResult:
        """Send one ordinary text prompt and qualify its exact native outcome."""

        if execution_model is not None and not execution_model.is_empty():
            raise BackendExecutionError("Kimi ACP per-prompt execution overrides are unsupported")
        if not prompt.strip() or prompt.lstrip().startswith("/"):
            raise BackendExecutionError(
                "Kimi ACP requires ordinary text without a native slash command"
            )
        with self.m_lock:
            if self.m_active is not None or not self.connection_ready:
                raise BackendExecutionError("Kimi ACP service is unavailable or busy")
            active = _ActivePrompt(operation.request_id)
            self.m_active = active
            self.m_turn_index += 1
        began = time.monotonic()
        authorized = False
        try:
            birth = self.process_birth_token
            journal = self.m_journal
            assert journal is not None and birth is not None
            write_service_record(
                operation.turn_dir / "process.json",
                {"child_pid": self.process_id, "child_birth_token": birth},
            )
            usage = self._begin_usage(operation)
            prompt_digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            interval = KimiJournalInterval.capture(journal)

            def authorize() -> None:
                """Persist approved input under the same lock that writes its native frame."""

                nonlocal authorized
                operation.authorize_native_write()
                authorized = True

            with self.m_lock:
                active.pending = self._connection().request(
                    "session/prompt",
                    {
                        "sessionId": self.m_session_id,
                        "prompt": [{"type": "text", "text": prompt}],
                    },
                    before_write=authorize,
                )
                operation.confirm_native_handoff()
            stop_reason = self._await_reply(active, began)
            closure = self._settlement(interval, prompt_digest, stop_reason, active)
            if closure is None:
                # A correlated cancellation can settle before a native turn ever exists.
                return self._terminal_result("cancelled", None)
            operation.confirm_native_handoff(closure.turn_id)
            self._persist_closure(operation, interval, closure, birth, usage, began)
            return self._terminal_result(stop_reason, closure)
        except (
            DshAcpProtocolError,
            DshAcpRequestError,
            BackendExecutionError,
            OSError,
            ValueError,
        ):
            if not authorized:
                raise
            self.m_available = False
            return ServicePromptResult(
                events=[
                    SessionEvent(
                        kind="error",
                        message="Kimi ACP could not verify the native outcome",
                        turn_index=self.m_turn_index,
                    )
                ],
                outcome="uncertain",
            )
        finally:
            with self.m_lock:
                if self.m_active is active:
                    self.m_active = None

    def _await_reply(self, active: _ActivePrompt, began: float) -> str:
        """Keep the native reader live and require the same prompt's correlated response."""

        pending = active.pending
        assert pending is not None
        while not pending.done():
            with self.m_lock:
                deadline = min(active.cancel_deadline or float("inf"), began + _PROMPT_TIMEOUT)
            try:
                pending.result(timeout=min(max(0.0, deadline - time.monotonic()), 0.1))
            except TimeoutError:
                if time.monotonic() >= deadline:
                    raise DshAcpProtocolError("Kimi ACP prompt settlement timed out") from None
            except DshAcpRequestError:
                break
        try:
            stop = pending.result().get("stopReason")
        except DshAcpRequestError:
            return "rpc_error"
        if not isinstance(stop, str) or stop not in _STOP_REASONS:
            raise DshAcpProtocolError("Kimi ACP did not report a supported prompt stop reason")
        return stop

    def _settlement(
        self,
        interval: KimiJournalInterval,
        prompt_digest: str,
        stop: str,
        active: _ActivePrompt,
    ) -> KimiTurnClosure | None:
        """Match protocol settlement to Kimi's distinct persisted native outcome."""

        deadline = time.monotonic() + _JOURNAL_TIMEOUT
        while True:
            closure = interval.closure(prompt_digest)
            if closure is not None:
                allowed = {
                    "completed": {"end_turn", "max_tokens", "max_turn_requests"},
                    "interrupted": {"cancelled"},
                    "failed": {"end_turn", "refusal", "rpc_error"},
                }
                if stop not in allowed[closure.outcome]:
                    raise DshAcpProtocolError(
                        "Kimi ACP reply contradicts its native terminal record"
                    )
                return closure
            if time.monotonic() >= deadline:
                # An empty interval proves the owner has no native turn to attribute.
                if (
                    stop == "cancelled"
                    and active.cancel_deadline is not None
                    and KimiJournalInterval.capture(interval.path) == interval
                ):
                    return None
                raise DshAcpProtocolError("Kimi ACP did not persist attributable terminal evidence")
            time.sleep(0.025)

    def _terminal_result(
        self,
        stop: str,
        closure: KimiTurnClosure | None,
    ) -> ServicePromptResult:
        """Project only text and outcome proven by the exact managed operation."""

        native_turn = closure.turn_id if closure is not None else None
        provenance = {"native_session_id": self.m_session_id, "native_turn_id": native_turn}
        events: list[SessionEvent] = []
        if closure is not None and closure.text:
            events.append(SessionEvent("assistant", closure.text, self.m_turn_index, provenance))
        if closure is not None and closure.outcome == "failed":
            events.append(
                SessionEvent("error", "Kimi native turn failed", self.m_turn_index, provenance)
            )
        events.append(
            SessionEvent(
                "completion",
                f"Kimi ACP prompt settled ({stop})",
                self.m_turn_index,
                {**provenance, "native_stop_reason": stop},
            )
        )
        return ServicePromptResult(
            events=events,
            outcome=closure.outcome if closure is not None else "interrupted",
            native_turn_id=native_turn,
        )

    def cancel(self, operation_id: str) -> bool:
        """Send the session-scoped notification only for the exact pending operation."""

        with self.m_lock:
            active = self.m_active
            if (
                active is None
                or active.request_id != operation_id
                or active.pending is None
                or active.pending.done()
                or active.cancel_deadline is not None
            ):
                return False
            try:
                self._connection().notify("session/cancel", {"sessionId": self.m_session_id})
            except (DshAcpProtocolError, OSError, ValueError):
                self.m_available = False
                return False
            active.cancel_deadline = time.monotonic() + _CANCEL_TIMEOUT
            return True

    def _interaction(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Decline remaining tool approvals and dismiss unsupported question forms."""

        if method != "session/request_permission":
            raise NotImplementedError
        with self.m_lock:
            active = self.m_active
            if (
                params.get("sessionId") != self.m_session_id
                or active is None
                or active.pending is None
                or active.pending.done()
            ):
                return {"outcome": {"outcome": "cancelled"}}
            options = params.get("options")
            if isinstance(options, list):
                for option in options:
                    if (
                        isinstance(option, dict)
                        and option.get("optionId") == "reject"
                        and option.get("kind") == "reject_once"
                    ):
                        return {"outcome": {"outcome": "selected", "optionId": "reject"}}
            return {"outcome": {"outcome": "cancelled"}}

    def _begin_usage(self, operation: ServiceOperationContext) -> UsageService | None:
        """Snapshot accounting before the protected prompt reaches the provider."""

        try:
            service = UsageService.from_manifest(self.m_config.manifest_path)
            service.begin_headless_turn(
                turn_id=operation.request_id,
                turn_dir=operation.turn_dir,
                turn_index=self.m_turn_index,
                new_session=False,
            )
            return service
        except (OSError, ValueError, UsageStoreError):
            return None

    def _persist_closure(
        self,
        operation: ServiceOperationContext,
        interval: KimiJournalInterval,
        closure: KimiTurnClosure,
        birth: str,
        usage: UsageService | None,
        began: float,
    ) -> None:
        """Persist a payload-free per-turn proof before qualified accounting."""

        config = self.m_config
        timestamp = datetime.now(UTC).isoformat()
        write_service_record(
            operation.turn_dir / "kimi-native-turn.json",
            {
                "version": 1,
                "agent_id": config.agent_id,
                "runtime_session_id": config.runtime_session_id,
                "generation_id": config.generation_id,
                "service_incarnation": config.service_incarnation,
                "request_id": operation.request_id,
                "native_session_id": self.m_session_id,
                "native_turn_id": closure.turn_id,
                "native_prompt_id": closure.prompt_id,
                "process_id": self.process_id,
                "process_birth_token": birth,
                "journal_path": str(interval.path),
                "journal_device": interval.device,
                "journal_inode": interval.inode,
                "journal_baseline_offset": interval.offset,
                "journal_settled_offset": closure.settled_offset,
                "terminal": closure.outcome,
                "settled_at_utc": timestamp,
            },
        )
        if usage is None:
            return
        with suppress(OSError, ValueError, UsageStoreError):
            persist_terminal_evidence(
                operation.turn_dir,
                returncode=0 if closure.outcome == "completed" else 1,
                completed_at_utc=timestamp,
                wall_time_ms=(time.monotonic() - began) * 1000,
                interrupted=closure.outcome == "interrupted",
            )
            usage.finalize_headless_turn(operation.turn_dir, provider_session_id=self.m_session_id)

    def close(self) -> None:
        """Close the selected session and reap the exact captured ACP process."""

        self.m_available = False
        try:
            connection = self.m_connection
            if connection is not None:
                if connection.healthy and self.m_close_supported and self.m_session_id:
                    with suppress(OSError, DshAcpProtocolError, DshAcpRequestError, TimeoutError):
                        connection.request(
                            "session/close", {"sessionId": self.m_session_id}
                        ).result(timeout=_CLOSE_TIMEOUT)
                connection.close()
        finally:
            if self.m_stderr is not None:
                self.m_stderr.close()
            if self.m_home_lock is not None:
                os.close(self.m_home_lock)
                self.m_home_lock = None

    def _connection(self) -> DshAcpConnection:
        """Return the private connection established by startup."""

        if self.m_connection is None:
            raise BackendExecutionError("Kimi ACP worker has not started")
        return self.m_connection

    def _call(
        self, method: str, params: dict[str, Any], *, check: ServiceStartupCheck
    ) -> dict[str, Any]:
        """Issue one finite setup request on an unpublished owner."""

        try:
            return self._connection().request(method, params).result(timeout=_STARTUP_TIMEOUT)
        except (DshAcpProtocolError, DshAcpRequestError, OSError, TimeoutError) as exc:
            raise ServiceStartupCompatibilityError(check) from exc

    def _diagnostic_line(self, line: str) -> None:
        """Drain the child diagnostics into the owner-private file."""

        if self.m_stderr is not None:
            self.m_stderr.write(line)


def create_kimi_service_provider(config: ServiceOwnerConfig) -> ServiceProvider:
    """Create a Kimi ACP provider and clean up any partial native startup."""

    provider = KimiAcpServiceProvider(config)
    try:
        provider.start()
    except BaseException:
        with suppress(Exception):
            provider.close()
        raise
    return provider


def _initialize(response: dict[str, Any], *, expected_version: str) -> tuple[str, dict[str, Any]]:
    """Verify protocol, capabilities, and the selected executable version."""

    if type(response.get("protocolVersion")) is not int or response["protocolVersion"] != 1:
        raise ServiceStartupCompatibilityError(ServiceStartupCheck.KIMI_PROTOCOL)
    identity = response.get("agentInfo")
    version = identity.get("version") if isinstance(identity, dict) else None
    if not isinstance(version, str):
        raise ServiceStartupCompatibilityError(ServiceStartupCheck.KIMI_VERSION)
    try:
        if Version(version) != Version(expected_version):
            raise ServiceStartupCompatibilityError(ServiceStartupCheck.KIMI_VERSION)
    except InvalidVersion as exc:
        raise ServiceStartupCompatibilityError(ServiceStartupCheck.KIMI_VERSION) from exc
    capabilities = response.get("agentCapabilities")
    if not isinstance(capabilities, dict) or not isinstance(
        capabilities.get("sessionCapabilities", {}), dict
    ):
        raise ServiceStartupCompatibilityError(ServiceStartupCheck.KIMI_CAPABILITIES)
    return version, capabilities


def _advertised_selection(response: dict[str, Any], option_id: str) -> str | None:
    """Read a current configuration value only when its option advertises that value."""

    entries = response.get("configOptions")
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("id") != option_id:
            continue
        value, options = entry.get("currentValue"), entry.get("options")
        if isinstance(value, str) and value and isinstance(options, list):
            if any(isinstance(option, dict) and option.get("value") == value for option in options):
                return value
    return None


def _open_private_log(path: Path) -> TextIO:
    """Write diagnostics into a new owner-only service artifact."""

    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    return os.fdopen(descriptor, "w", buffering=1, encoding="utf-8")
