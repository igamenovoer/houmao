"""Keep one DSH ACP child and its exact native session alive across owner requests."""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import Future
from datetime import UTC, datetime
import fcntl
from importlib.resources import files
import json
import math
import os
from pathlib import Path
import sys
import threading
import time
from typing import Any, TextIO
from uuid import uuid4

from houmao.agents.dsh_configuration import (
    DshEffectiveToolParams,
    load_dsh_home,
    read_dsh_mcp_environment,
)
from houmao.agents.model_mapping_policy import resolve_reasoning_mapping
from houmao.agents.model_selection import ModelConfig
from houmao.agents.realm_controller.backends.dispatch_control import (
    _dispatch_origin_birth_token,
    headless_dispatch_permission_allowed,
)
from houmao.agents.realm_controller.backends.dsh_acp_connection import (
    DshAcpConnection,
    DshAcpProtocolError,
    DshAcpRequestError,
    reject_dsh_acp_permission,
    validate_dsh_acp_initialization,
)
from houmao.agents.realm_controller.backends.dsh_acp_driver import _open_private_diagnostics
from houmao.agents.realm_controller.backends.dsh_diagnostics import (
    dsh_diagnostic_secrets,
    sanitize_dsh_diagnostic,
)
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.models import SessionEvent
from houmao.agents.realm_controller.owner_admission import OwnerPromptClaim
from houmao.agents.realm_controller.backends.service_runtime import (
    ServiceOperationContext,
    ServiceOutcome,
    ServiceOwnerConfig,
    ServicePromptResult,
)
from houmao.agents.realm_controller.usage_adapters.dsh import (
    DSH_MAX_JOURNAL_ROW_BYTES,
    DSH_SOURCE_REVISION,
    select_dsh_journal,
)
from houmao.agents.realm_controller.usage_support import (
    UsageService,
    persist_terminal_evidence,
    write_usage_json,
)
from houmao.agents.realm_controller.usage_store import UsageStoreError


_SETUP_TIMEOUT = 40.0
_TURN_TIMEOUT = 300.0
_CANCEL_TIMEOUT = 12.0
_FLUSH_TIMEOUT = 8.0


class DshAcpServiceProvider:
    """Own native IO, session options, and one independently qualified prompt at a time."""

    def __init__(self, config: ServiceOwnerConfig) -> None:
        self.m_config: ServiceOwnerConfig = config
        self.m_lock: threading.Lock = threading.Lock()
        self.m_stop: threading.Event = threading.Event()
        self.m_connection: DshAcpConnection | None = None
        self.m_reader: threading.Thread | None = None
        self.m_raw: TextIO | None = None
        self.m_stderr: TextIO | None = None
        self.m_home_lock: int | None = None
        self.m_session_id: str = ""
        self.m_native_identity: dict[str, Any] = {}
        self.m_options: list[dict[str, Any]] = []
        self.m_secret_values: tuple[str, ...] = ()
        self.m_route: str = ""
        self.m_persistence_root: Path = config.home_path / "sessions"
        self.m_arm: Path = config.root / "dsh-native-arm.json"
        self.m_active_request: str | None = None
        self.m_pending: Future[dict[str, Any]] | None = None
        self.m_cancel_deadline: float | None = None
        self.m_unavailable: bool = False
        self.m_turn_index: int = 0

    def start(self) -> None:
        """Materialize private companion controls, then negotiate one native session."""

        config = self.m_config
        config.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(
            config.home_path / "houmao-invocation.lock", os.O_CREAT | os.O_RDWR, 0o600
        )
        self.m_home_lock = descriptor
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._initialize()
        except BaseException:
            try:
                self.close()
            except Exception:
                pass
            raise

    def _initialize(self) -> None:
        """Read the current native home at its process and session binding boundaries."""

        config = self.m_config
        setup_meta = config.metadata.get("dsh")
        setup_path = setup_meta.get("setup_path") if isinstance(setup_meta, dict) else None
        if not isinstance(setup_path, str):
            raise BackendExecutionError("DSH service setup projection is unavailable")
        setup = DshEffectiveToolParams.from_file(Path(setup_path))
        credentials = read_dsh_mcp_environment(setup, config.metadata.get("env_source_file"))
        loaded = load_dsh_home(
            config.home_path, setup, config.environment, credential_environment=credentials
        )
        self.m_secret_values = (
            *dsh_diagnostic_secrets(loaded.environment, key_name=setup.api_key_env),
            *credentials.values(),
        )
        self.m_route = setup.route
        self.m_persistence_root = loaded.persistence_root
        ready_path = config.root / "dsh-native-ready.json"
        control_path = config.root / "dsh-service-control.json"
        patch_path = config.root / "dsh-service-companion.patch.json"
        write_usage_json(
            control_path,
            {
                "version": 1,
                "attempt_id": config.service_incarnation,
                "runtime_session_id": config.runtime_session_id,
                "generation": config.generation_id,
                "expected_native_session_id": config.session_id,
                "evidence_path": str(ready_path),
                "abandoned_message_ids": [],
                "working_directory": str(config.working_directory.resolve()),
                "persistence_root": str(loaded.persistence_root),
                "source_revision": DSH_SOURCE_REVISION,
                "service": {
                    "manifest_path": str(config.manifest_path),
                    "arm_path": str(self.m_arm),
                    "turn_root": str(_turn_root(config.manifest_path)),
                    "python_executable": sys.executable,
                },
            },
        )
        companion = files("houmao.agents").joinpath("assets/dsh/managed-companion.mjs")
        with _open_private_diagnostics(patch_path) as stream:
            json.dump(
                [
                    {
                        "insert": [
                            {
                                "id": "houmao-managed",
                                "name": str(companion),
                                "config": {
                                    "controlFile": str(control_path),
                                    "roleFile": str(loaded.role_path),
                                },
                            }
                        ]
                    }
                ],
                stream,
            )
        arguments = list(config.arguments) or ["--profile", "acp"]
        if arguments[:2] != ["--profile", "acp"]:
            raise BackendExecutionError("DSH service requires the native ACP launch profile")
        command = [
            config.executable,
            *arguments,
            "--patch",
            str(loaded.patch_path),
            "--patch",
            str(patch_path),
        ]
        self.m_raw = _open_private_diagnostics(config.root / "provider-stdout.jsonl")
        self.m_stderr = _open_private_diagnostics(config.root / "provider-stderr.log")
        self.m_connection = DshAcpConnection.from_command(
            command,
            cwd=config.working_directory,
            env=loaded.environment,
            request_handler=self._permission,
            frame_sink=lambda line: self._private_line(self.m_raw, line),
            stderr_sink=lambda line: self._private_line(self.m_stderr, line),
            secret_values=self.m_secret_values,
        )
        connection = self._connection()
        self.m_reader = threading.Thread(
            target=self._drain, daemon=True, name="dsh-service-updates"
        )
        self.m_reader.start()
        initialized = connection.request(
            "initialize",
            {
                "protocolVersion": 1,
                "clientInfo": {"name": "houmao", "version": "1"},
                "clientCapabilities": {},
            },
        ).result(timeout=_SETUP_TIMEOUT)
        validate_dsh_acp_initialization(initialized, require_resume=True)
        parameters: dict[str, Any] = {
            "cwd": str(config.working_directory.resolve()),
            "mcpServers": list(loaded.mcp_servers),
        }
        if config.session_id is not None:
            parameters["sessionId"] = config.session_id
        selected = connection.request(
            "session/resume" if config.session_id else "session/new", parameters
        ).result(timeout=_SETUP_TIMEOUT)
        actual = selected.get("sessionId", config.session_id)
        if (
            not isinstance(actual, str)
            or not actual
            or (config.session_id and config.session_id != actual)
        ):
            raise DshAcpProtocolError("DSH did not bind the requested native session")
        identity = _read_object(ready_path)
        expected = {
            "version": 1,
            "service_incarnation": config.service_incarnation,
            "generation": config.generation_id,
            "runtime_session_id": config.runtime_session_id,
            "native_session_id": actual,
            "process_id": connection.process.pid,
        }
        if (
            self.process_birth_token is None
            or any(identity.get(key) != value for key, value in expected.items())
            or not all(
                isinstance(identity.get(key), str) and identity[key]
                for key in ("host_incarnation", "agent_incarnation")
            )
        ):
            raise DshAcpProtocolError("DSH native companion did not verify the selected session")
        self.m_native_identity = identity
        self.m_options = _options(selected)
        self.m_session_id = actual

    @property
    def native_session_id(self) -> str:
        """Return the exact native session selected during initialization."""

        return self.m_session_id

    @property
    def process_id(self) -> int:
        """Return the process captured by the owned connection."""

        return self._connection().process.pid

    @property
    def process_birth_token(self) -> str | None:
        """Return the captured birth identity of that process."""

        return self.m_connection.process_birth_token if self.m_connection is not None else None

    @property
    def connection_ready(self) -> bool:
        """Require a live verified ACP connection with known session settings."""

        connection = self.m_connection
        return bool(
            self.m_session_id
            and not self.m_unavailable
            and not self.m_stop.is_set()
            and connection is not None
            and connection.healthy
        )

    def _connection(self) -> DshAcpConnection:
        """Return the initialized process connection for native protocol work."""

        if self.m_connection is None:
            raise DshAcpProtocolError("DSH service connection is unavailable")
        return self.m_connection

    @staticmethod
    def _private_line(stream: TextIO | None, line: str) -> None:
        """Keep raw provider output in the user-private service directory."""

        if stream is not None:
            stream.write(line)
            stream.flush()

    def _drain(self) -> None:
        """Drain ACP updates continuously and retain raw frames privately.

        RC.3 updates carry a session ID and no turn ID. The exact native journal
        supplies the attributed semantic stream instead of relabeling these frames.
        """

        connection = self._connection()
        while not self.m_stop.is_set() and connection.healthy:
            connection.next_notification(timeout=0.1)

    def _permission(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Decline any remaining interactive permission under the exact active prompt."""

        with self.m_lock:
            if self.m_pending is None or self.m_pending.done():
                raise DshAcpProtocolError("ACP interaction has no active service prompt")
            return reject_dsh_acp_permission(method, params, session_id=self.m_session_id)

    def prompt(
        self,
        prompt: str,
        *,
        execution_model: ModelConfig | None,
        operation: ServiceOperationContext,
    ) -> ServicePromptResult:
        """Fence one native prompt, settle it, and verify restoration before release."""

        with self.m_lock:
            if self.m_active_request is not None or not self.connection_ready:
                raise BackendExecutionError("DSH service is unavailable or busy")
            self.m_active_request = operation.request_id
            self.m_turn_index += 1
        prior = _current_settings(self.m_options)
        changed: list[str] = []
        result = ServicePromptResult()
        try:
            authorized = execution_model is not None and not execution_model.is_empty()
            if authorized:
                operation.authorize_native_write()
            self._apply_override(execution_model, prior, changed)
            result = self._run_prompt(prompt, operation, already_authorized=authorized)
        except Exception as exc:
            result = ServicePromptResult(
                events=[self._error_event(exc)], outcome="uncertain" if self.m_pending else "failed"
            )
            if self.m_pending is not None and not self.m_pending.done():
                self.m_unavailable = True
        finally:
            self.m_arm.unlink(missing_ok=True)
            try:
                if changed:
                    self._restore_settings(prior, changed)
            except Exception as exc:
                self.m_unavailable = True
                result = ServicePromptResult(
                    events=[*result.events, self._error_event(exc)],
                    outcome="uncertain",
                    native_turn_id=result.native_turn_id,
                )
            finally:
                with self.m_lock:
                    self.m_active_request = None
                    self.m_pending = None
                    self.m_cancel_deadline = None
        return result

    def _run_prompt(
        self, text: str, operation: ServiceOperationContext, *, already_authorized: bool
    ) -> ServicePromptResult:
        """Send one request and use exact native inbox evidence for handoff."""

        config = self.m_config
        turn_dir = operation.turn_dir
        if (
            Path(operation.request_id).name != operation.request_id
            or operation.request_id in {"", ".", ".."}
            or turn_dir != _turn_root(config.manifest_path) / operation.request_id
        ):
            raise BackendExecutionError("DSH service turn path differs from its owner identity")
        turn_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        accounting = self._start_usage(operation)
        pid, birth = self.process_id, self.process_birth_token
        owner_birth = _dispatch_origin_birth_token(os.getpid())
        if birth is None or owner_birth is None:
            raise BackendExecutionError("DSH service process birth identity is unavailable")
        write_usage_json(turn_dir / "process.json", {"child_pid": pid, "child_birth_token": birth})
        if not already_authorized:
            operation.authorize_native_write()
        write_usage_json(
            self.m_arm,
            {
                "version": 1,
                "request_id": operation.request_id,
                "nonce": uuid4().hex,
                "expires_at": time.time() + _SETUP_TIMEOUT,
                "generation": config.generation_id,
                "service_incarnation": config.service_incarnation,
                "native_session_id": self.m_session_id,
                "process_id": pid,
                "process_birth_token": birth,
                "owner_pid": os.getpid(),
                "owner_birth_token": owner_birth,
            },
        )
        admitted = False
        began = time.monotonic()
        with self.m_lock:
            pending = self._connection().request(
                "session/prompt",
                {
                    "sessionId": self.m_session_id,
                    "prompt": [{"type": "text", "text": text}],
                },
            )
            self.m_pending = pending
        while True:
            if not admitted and self._handoff(operation):
                admitted = True
                operation.confirm_native_handoff()
            if pending.done():
                break
            with self.m_lock:
                deadline = self.m_cancel_deadline or began + _TURN_TIMEOUT
            if time.monotonic() >= deadline:
                self.m_unavailable = True
                raise DshAcpProtocolError("DSH service prompt did not settle before its deadline")
            time.sleep(0.02)
        outcome: ServiceOutcome
        try:
            reason = pending.result().get("stopReason")
            if reason not in {
                "end_turn",
                "cancelled",
                "max_tokens",
                "max_turn_requests",
                "refusal",
            }:
                raise DshAcpProtocolError("DSH service did not report a supported stop reason")
            outcome = (
                "completed"
                if reason == "end_turn"
                else "interrupted"
                if reason == "cancelled"
                else "failed"
            )
            errors: list[SessionEvent] = []
        except DshAcpRequestError as exc:
            reason = "error"
            outcome = "failed"
            errors = [self._error_event(exc)]
        if not admitted:
            if reason == "cancelled" and not (turn_dir / "dsh-native-binding.json").exists():
                return ServicePromptResult(
                    events=[
                        self._error_event(
                            DshAcpProtocolError("DSH cancelled before native admission")
                        )
                    ],
                    outcome="failed",
                )
            raise DshAcpProtocolError("DSH service did not prove native prompt admission")
        events, native_turn = self._flushed_events(operation, expected_reason=str(reason))
        self._finish_usage(accounting, turn_dir, began, str(outcome))
        events.append(
            SessionEvent(
                kind="completion",
                message=f"DSH ACP prompt settled ({reason})",
                turn_index=self.m_turn_index,
                payload={
                    "native_stop_reason": reason,
                    "native_session_id": self.m_session_id,
                    "native_turn_id": native_turn,
                },
            )
        )
        return ServicePromptResult(
            events=[*events, *errors], outcome=outcome, native_turn_id=native_turn
        )

    def _handoff(self, operation: ServiceOperationContext) -> bool:
        """Verify the native receipt against the original request, session, and worker."""

        receipt = operation.turn_dir / "dsh-native-handoff.json"
        if not receipt.is_file():
            return False
        binding = _read_object(receipt)
        if binding != _read_object(operation.turn_dir / "dsh-native-binding.json") or any(
            binding.get(key) != value
            for key, value in {
                "attempt_id": operation.request_id,
                "process_birth_token": self.process_birth_token,
                **{
                    key: value
                    for key, value in self.m_native_identity.items()
                    if key != "role_sha256"
                },
            }.items()
        ):
            raise DshAcpProtocolError(
                "DSH native prompt receipt does not match the service operation"
            )
        return True

    def _flushed_events(
        self, operation: ServiceOperationContext, *, expected_reason: str
    ) -> tuple[list[SessionEvent], str]:
        """Wait for the exact last native terminal record and read its journal output."""

        directory = operation.turn_dir
        binding = _read_object(directory / "dsh-native-binding.json")
        evidence = _records(directory / "dsh-native-evidence.jsonl")
        admitted = [row.get("message_id") for row in evidence if row.get("event") == "admitted"]
        claimed = [
            row.get("turn")
            for row in evidence
            if row.get("event") == "claimed" and row.get("message_id") in admitted
        ]
        if len(admitted) != 1 or not isinstance(admitted[0], str) or len(set(claimed)) != 1:
            raise DshAcpProtocolError("DSH native turn is not linked to its admitted input")
        roots = [row for row in evidence if row.get("event") == "turn/start"]
        endings = [row for row in evidence if row.get("event") == "turn/end"]
        if (
            not roots
            or not endings
            or any(any(row.get(key) != value for key, value in binding.items()) for row in evidence)
        ):
            raise DshAcpProtocolError(
                "DSH native turn evidence does not match the active operation"
            )
        terminal = endings[-1]
        owned_start = next((row for row in roots if row.get("turn") == claimed[0]), {})
        start_seq, end_seq, turn = (
            owned_start.get("native_sequence"),
            terminal.get("native_sequence"),
            terminal.get("turn"),
        )
        reason = terminal.get("reason", {}).get("kind")
        if not (
            type(start_seq) is int
            and type(end_seq) is int
            and type(turn) is int
            and start_seq <= end_seq
        ):
            raise DshAcpProtocolError("DSH service terminal sequence is unavailable")
        if expected_reason == "end_turn" and reason != "completed":
            raise DshAcpProtocolError("DSH protocol completion conflicts with its native journal")
        deadline = time.monotonic() + _FLUSH_TIMEOUT
        flush_path = directory / "dsh-native-flush.json"
        while time.monotonic() < deadline:
            if flush_path.is_file():
                flush = _read_object(flush_path)
                if flush.get("native_sequence") == end_seq:
                    if any(flush.get(key) != value for key, value in binding.items()) or (
                        flush.get("status") != "flushed" or flush.get("reason") != reason
                    ):
                        break
                    journal = select_dsh_journal(self.m_persistence_root, self.m_session_id)
                    if journal is not None:
                        return self._journal_events(journal, start_seq, end_seq, turn, reason), str(
                            turn
                        )
            time.sleep(0.025)
        raise DshAcpProtocolError("DSH service could not verify native journal flush")

    def _journal_events(
        self, journal: Path, start: int, end: int, turn: int, reason: object
    ) -> list[SessionEvent]:
        """Project exact journal output between this operation's native boundaries."""

        events: list[SessionEvent] = []
        for row in _iter_records(journal):
            seq = row.get("seq")
            if type(seq) is not int or seq < start:
                continue
            if seq > end:
                break
            data = row.get("data")
            if row.get("type") == "assistant/message" and isinstance(data, dict):
                content = data.get("message", {}).get("content", [])
                for block in content:
                    if not isinstance(block, dict) or not isinstance(block.get("text"), str):
                        continue
                    kind = block.get("type")
                    if kind in {"text", "reasoning"}:
                        events.append(
                            SessionEvent(
                                kind="assistant" if kind == "text" else "reasoning",
                                message=block["text"],
                                turn_index=self.m_turn_index,
                                payload={
                                    "native_session_id": self.m_session_id,
                                    "native_turn_id": str(data.get("turn")),
                                },
                            )
                        )
            if seq == end:
                if (
                    row.get("type") == "turn/end"
                    and isinstance(data, dict)
                    and data.get("turn") == turn
                    and (data.get("reason", {}).get("kind") == reason)
                ):
                    return events
                break
        raise DshAcpProtocolError("DSH native journal does not contain the bound terminal record")

    def _start_usage(self, operation: ServiceOperationContext) -> UsageService | None:
        """Register the logical service request against the exact existing conversation."""

        try:
            usage = UsageService.from_manifest(self.m_config.manifest_path)
            usage.begin_headless_turn(
                turn_id=operation.request_id,
                turn_dir=operation.turn_dir,
                turn_index=self.m_turn_index,
                new_session=False,
            )
            return usage
        except (OSError, ValueError, UsageStoreError):
            return None

    def _finish_usage(
        self, service: UsageService | None, turn_dir: Path, began: float, outcome: str
    ) -> None:
        """Finalize one v4 journal interval after the native ACP reply and flush."""

        if service is None:
            return
        try:
            persist_terminal_evidence(
                turn_dir,
                returncode=0 if outcome == "completed" else 1,
                completed_at_utc=datetime.now(UTC).isoformat(),
                wall_time_ms=(time.monotonic() - began) * 1000,
                interrupted=outcome == "interrupted",
            )
            service.finalize_headless_turn(turn_dir, provider_session_id=self.m_session_id)
        except (OSError, ValueError, UsageStoreError):
            pass

    def _apply_override(
        self, model: ModelConfig | None, prior: dict[str, str], changed: list[str]
    ) -> None:
        """Apply only native advertised selections whose prior values can be restored."""

        if model is None or model.is_empty():
            return
        if "model" not in prior:
            raise DshAcpProtocolError("DSH did not advertise a restorable model selection")
        current = json.loads(prior["model"])
        desired_model = model.name or current[1]
        desired_effort = None
        if model.reasoning is not None:
            if desired_model == current[1] and "reasoning_effort" not in prior:
                raise DshAcpProtocolError("DSH did not advertise a restorable reasoning selection")
            desired_effort = resolve_reasoning_mapping(
                tool="dsh",
                requested_level=model.reasoning.level,
                model_name=desired_model,
                home_path=self.m_config.home_path,
            ).get("profile_key")
            if not isinstance(desired_effort, str):
                raise DshAcpProtocolError("DSH reasoning selection is unavailable")
        if model.name is not None:
            selected = _choice(self.m_options, "model", [self.m_route, model.name])
            if selected != prior["model"]:
                changed.append("model")
                self._set("model", selected)
        if desired_effort is not None:
            value = _choice(self.m_options, "reasoning_effort", desired_effort)
            if value != _current_settings(self.m_options).get("reasoning_effort"):
                changed.append("reasoning_effort")
                self._set("reasoning_effort", value)

    def _restore_settings(self, prior: dict[str, str], changed: list[str]) -> None:
        """Restore the model before its model-dependent reasoning selection."""

        if self.m_unavailable or (self.m_pending is not None and not self.m_pending.done()):
            raise DshAcpProtocolError(
                "DSH settings cannot be restored while native state is unresolved"
            )
        if "model" in changed:
            self._set("model", prior["model"])
        if "reasoning_effort" in prior and (
            "reasoning_effort" in changed
            or _current_settings(self.m_options).get("reasoning_effort")
            != prior["reasoning_effort"]
        ):
            self._set("reasoning_effort", prior["reasoning_effort"])
        if _current_settings(self.m_options) != prior:
            raise DshAcpProtocolError("DSH prior session settings could not be verified")

    def _set(self, field: str, value: str) -> None:
        """Verify the complete options state returned by a correlated setting update."""

        pending = self._connection().request(
            "session/set_config_option",
            {"sessionId": self.m_session_id, "configId": field, "value": value},
        )
        try:
            result = pending.result(timeout=_SETUP_TIMEOUT)
        except TimeoutError:
            if not pending.done():
                self.m_unavailable = True
            raise DshAcpProtocolError("DSH session setting did not settle") from None
        self.m_options = _options(result)
        if _current_settings(self.m_options).get(field) != value:
            raise DshAcpProtocolError("DSH did not confirm the requested session setting")

    def cancel(self, operation_id: str) -> bool:
        """Serialize session-scoped cancel against the exact still-pending prompt."""

        with self.m_lock:
            if (
                self.m_active_request != operation_id
                or self.m_pending is None
                or self.m_pending.done()
            ):
                return False
            if self.m_cancel_deadline is None:
                self._connection().notify("session/cancel", {"sessionId": self.m_session_id})
                self.m_cancel_deadline = time.monotonic() + _CANCEL_TIMEOUT
            return True

    def _error_event(self, error: Exception) -> SessionEvent:
        """Expose bounded redacted diagnostics without copying native frames."""

        detail = sanitize_dsh_diagnostic(str(error), secret_values=self.m_secret_values)
        return SessionEvent(
            kind="error",
            message=detail or "DSH service operation failed",
            turn_index=self.m_turn_index,
        )

    def close(self) -> None:
        """Close the exact native session and reap this connection and process tree."""

        self.m_stop.set()
        self.m_arm.unlink(missing_ok=True)
        try:
            if self.m_connection is not None:
                connection = self.m_connection
                try:
                    if self.m_session_id and connection.healthy:
                        connection.request(
                            "session/close", {"sessionId": self.m_session_id}
                        ).result(timeout=10)
                finally:
                    connection.close(timeout=3)
        finally:
            if self.m_reader is not None:
                self.m_reader.join(timeout=1)
            for stream in (self.m_raw, self.m_stderr):
                if stream is not None:
                    stream.close()
            if self.m_home_lock is not None:
                os.close(self.m_home_lock)
                self.m_home_lock = None


def create_dsh_service_provider(config: ServiceOwnerConfig) -> DshAcpServiceProvider:
    """Create the single persistent native DSH provider for this service incarnation."""

    provider = DshAcpServiceProvider(config)
    try:
        provider.start()
    except (OSError, ValueError, DshAcpProtocolError, DshAcpRequestError, TimeoutError) as exc:
        diagnostics = provider.m_connection.diagnostics if provider.m_connection else ""
        detail = sanitize_dsh_diagnostic(
            " ".join(part for part in (str(exc), diagnostics) if part),
            secret_values=provider.m_secret_values,
        )
        raise BackendExecutionError(detail or "DSH service initialization failed") from None
    return provider


def _options(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the native settings table before using its current values."""

    options = result.get("configOptions", [])
    if not isinstance(options, list) or any(not isinstance(option, dict) for option in options):
        raise DshAcpProtocolError("DSH service reported invalid session settings")
    return options


def _current_settings(options: list[dict[str, Any]]) -> dict[str, str]:
    """Read the two session-scoped configuration controls Houmao can verify."""

    return {
        option["id"]: option["currentValue"]
        for option in options
        if option.get("id") in {"model", "reasoning_effort"}
        and option.get("type") == "select"
        and isinstance(option.get("currentValue"), str)
    }


def _choice(options: list[dict[str, Any]], field: str, desired: str | list[str]) -> str:
    """Resolve the exact advertised opaque value for a model or reasoning control."""

    roots = [option.get("options") for option in options if option.get("id") == field]
    remaining = list(roots[0]) if len(roots) == 1 and isinstance(roots[0], list) else []
    exact: set[str] = set()
    while remaining:
        option = remaining.pop()
        if not isinstance(option, dict):
            continue
        children = option.get("options")
        if isinstance(children, list):
            remaining.extend(children)
        value = option.get("value")
        if not isinstance(value, str):
            continue
        if isinstance(desired, list):
            try:
                matches = json.loads(value) == desired
            except ValueError:
                matches = False
        else:
            matches = value == desired
        if matches:
            exact.add(value)
    if len(exact) != 1:
        raise DshAcpProtocolError(f"DSH did not advertise one exact {field} option")
    return exact.pop()


def _turn_root(manifest: Path) -> Path:
    """Select the owner-private canonical request artifact directory."""

    return manifest.parent / f"{manifest.stem}.turn-artifacts"


def _read_object(path: Path) -> dict[str, Any]:
    """Read one private identity record of the expected shape."""

    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise DshAcpProtocolError("DSH service identity evidence is malformed")
    return result


def _iter_records(path: Path) -> Iterator[dict[str, Any]]:
    """Yield only complete bounded provider journal records."""

    with path.open("rb") as stream:
        while line := stream.readline(DSH_MAX_JOURNAL_ROW_BYTES + 1):
            if len(line) > DSH_MAX_JOURNAL_ROW_BYTES or not line.endswith(b"\n"):
                raise DshAcpProtocolError("DSH service native journal record is incomplete")
            row = json.loads(line)
            if not isinstance(row, dict):
                raise DshAcpProtocolError("DSH service native journal record is malformed")
            yield row


def _records(path: Path) -> list[dict[str, Any]]:
    """Read this operation's small payload-free native evidence stream."""

    return list(_iter_records(path))


def _verify_native_arm(arguments: list[str]) -> bool:
    """Fence the exact native call from the private companion before it writes user input."""

    try:
        arm_path, manifest, generation, incarnation, request_id, session_id, pid = arguments
        arm = _read_object(Path(arm_path))
        expiry = arm.get("expires_at")
        owner = arm.get("owner_pid")
        if (
            not isinstance(expiry, (int, float))
            or isinstance(expiry, bool)
            or not math.isfinite(expiry)
            or expiry <= time.time()
            or type(owner) is not int
            or not isinstance(arm.get("owner_birth_token"), str)
            or _dispatch_origin_birth_token(owner) != arm["owner_birth_token"]
            or not isinstance(arm.get("process_birth_token"), str)
            or _dispatch_origin_birth_token(int(pid)) != arm["process_birth_token"]
            or any(
                arm.get(key) != value
                for key, value in {
                    "version": 1,
                    "generation": generation,
                    "service_incarnation": incarnation,
                    "request_id": request_id,
                    "native_session_id": session_id,
                    "process_id": int(pid),
                }.items()
            )
        ):
            return False
        manifest_path = Path(manifest)
        guard = _turn_root(manifest_path) / request_id / ".dispatch-permission.json"
        proof = _read_object(guard)
        saved = _read_object(manifest_path)
        backend = saved.get("backend_state")
        return (
            isinstance(backend, dict)
            and saved.get("backend") == "dsh_acp"
            and backend.get("service_incarnation") == incarnation
            and backend.get("native_session_id") == session_id
            and proof.get("attempt_id") == request_id
            and proof.get("manifest_path") == manifest
            and proof.get("registry_generation_id") == generation
            and headless_dispatch_permission_allowed(guard)
            and OwnerPromptClaim(manifest_path, generation, request_id, "service").active()
        )
    except (OSError, ValueError, RuntimeError):
        return False


if __name__ == "__main__":
    raise SystemExit(
        0
        if len(sys.argv) == 9
        and sys.argv[1] == "--verify-native-arm"
        and _verify_native_arm(sys.argv[2:])
        else 1
    )
