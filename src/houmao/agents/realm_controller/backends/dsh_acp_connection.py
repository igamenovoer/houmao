"""Concurrent JSON-RPC stdio transport for a managed native worker.

The reader never waits for an outgoing request or a permission decision. Callers
own operation deadlines and must treat a timed-out mutation as uncertain rather
than resubmit it. This module does not infer native admission from a sent frame.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
import json
import os
from pathlib import Path
import queue
import select
import signal
import subprocess
import threading
import time
from typing import Any, Literal

from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.backends.dsh_diagnostics import (
    dsh_diagnostic_secrets,
    sanitize_dsh_diagnostic,
)


class DshAcpProtocolError(RuntimeError):
    """Indicate invalid protocol input or loss of the owned connection."""


class DshAcpRequestError(RuntimeError):
    """Expose a remote JSON-RPC code and safe diagnostic without treating it as completion."""

    def __init__(self, error: dict[str, Any], *, secret_values: Sequence[str] = ()) -> None:
        """Capture the code and scrub message text before crossing the protocol boundary."""

        raw_code = error.get("code")
        code = raw_code if type(raw_code) is int and -(2**31) <= raw_code < 2**31 else "unknown"
        raw_message = error.get("message")
        message = (
            sanitize_dsh_diagnostic(raw_message, secret_values=secret_values)
            if isinstance(raw_message, str)
            else ""
        )
        suffix = f": {message}" if message else ""
        super().__init__(f"ACP request failed ({code}){suffix}")
        self.m_error: dict[str, Any] = {"code": code, "message": message}

    @property
    def error(self) -> dict[str, Any]:
        """Return a copy of the redacted error fields."""

        return dict(self.m_error)


class _AcpPrewriteRejected(RuntimeError):
    """Carry a caller-side rejection that left the transport untouched."""

    def __init__(self, error: Exception) -> None:
        """Keep the original caller exception for its request thread."""

        super().__init__("ACP request refused before writing")
        self.m_error: Exception = error


_MAX_RPC_LINE = 16 * 1024 * 1024


class DshAcpConnection:
    """Demultiplex one owned native worker's protocol frames and diagnostics."""

    def __init__(self) -> None:
        """Create an inactive connection; use ``from_command`` to start it."""

        self.m_process: subprocess.Popen[str] | None = None
        self.m_process_birth_token: str | None = None
        self.m_owned_processes: dict[int, str] = {}
        self.m_pending: dict[int, Future[dict[str, Any]]] = {}
        self.m_next_id: int = 1
        self.m_lock: threading.Lock = threading.Lock()
        self.m_write_lock: threading.Lock = threading.Lock()
        self.m_notifications: queue.Queue[dict[str, Any]] = queue.Queue()
        self.m_retain_notifications: bool = True
        self.m_notification_sink: Callable[[dict[str, Any], int], None] | None = None
        self.m_framing: Literal["acp", "codex"] = "acp"
        self.m_write_timeout: float | None = None
        self.m_diagnostics: deque[str] = deque(maxlen=128)
        self.m_failure: DshAcpProtocolError | None = None
        self.m_request_handler: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None
        self.m_frame_sink: Callable[[str], None] | None = None
        self.m_stderr_sink: Callable[[str], None] | None = None
        self.m_secret_values: tuple[str, ...] = ()
        self.m_reader: threading.Thread | None = None
        self.m_stderr_reader: threading.Thread | None = None
        self.m_requests: ThreadPoolExecutor | None = None
        self.m_request_slots: threading.BoundedSemaphore = threading.BoundedSemaphore(16)

    @classmethod
    def from_command(
        cls,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        request_handler: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        frame_sink: Callable[[str], None] | None = None,
        stderr_sink: Callable[[str], None] | None = None,
        secret_values: Sequence[str] = (),
        retain_notifications: bool = True,
        write_timeout: float | None = None,
        framing: Literal["acp", "codex"] = "acp",
        notification_sink: Callable[[dict[str, Any], int], None] | None = None,
    ) -> DshAcpConnection:
        """Start an explicitly configured worker and its independent readers.

        Parameters
        ----------
        command:
            Actual executable and ACP profile arguments.
        cwd, env:
            Resolved workspace and complete isolated process environment.
        request_handler:
            Qualified permission handler. Missing handlers reject requests.
        frame_sink:
            Private raw-provider artifact writer, separate from rendered output.
        stderr_sink:
            Private raw stderr writer, separate from error summaries.
        secret_values:
            Additional resolved credentials allowed only in private native IO.
        retain_notifications:
            Keep notifications for consumers that read the notification queue.
        write_timeout:
            Bound pipe backpressure. A timeout may leave a partial frame.
        framing:
            Codex uses an unversioned envelope. ACP requires ``jsonrpc: 2.0``.
        notification_sink:
            Nonblocking notification handler with its own bounded retention.
        """

        instance = cls()
        instance.m_request_handler = request_handler
        instance.m_frame_sink = frame_sink
        instance.m_stderr_sink = stderr_sink
        instance.m_secret_values = (*dsh_diagnostic_secrets(env), *secret_values)
        instance.m_retain_notifications = retain_notifications
        instance.m_notification_sink = notification_sink
        instance.m_framing = framing
        instance.m_write_timeout = write_timeout
        instance.m_process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="strict",
            bufsize=1,
            start_new_session=True,
        )
        instance.m_process_birth_token = _dispatch_origin_birth_token(instance.m_process.pid)
        if write_timeout is not None:
            assert instance.m_process.stdin is not None
            os.set_blocking(instance.m_process.stdin.fileno(), False)
        if instance.m_process_birth_token is not None:
            instance.m_owned_processes[instance.m_process.pid] = instance.m_process_birth_token
        instance.m_requests = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="dsh-acp-request"
        )
        instance.m_reader = threading.Thread(
            target=instance._read_stdout, name="dsh-acp-reader", daemon=True
        )
        instance.m_stderr_reader = threading.Thread(
            target=instance._read_stderr, name="dsh-acp-stderr", daemon=True
        )
        instance.m_stderr_reader.start()
        instance.m_reader.start()
        return instance

    @property
    def process(self) -> subprocess.Popen[str]:
        """Return the owned process; never resolve a process by executable name."""

        if self.m_process is None:
            raise DshAcpProtocolError("ACP worker has not started")
        return self.m_process

    @property
    def diagnostics(self) -> str:
        """Return bounded private stderr diagnostics."""

        return "".join(self.m_diagnostics)

    @property
    def process_birth_token(self) -> str | None:
        """Return the immutable birth identity captured when this worker started."""

        return self.m_process_birth_token

    @property
    def healthy(self) -> bool:
        """Report a live owned process and an open protocol reader."""

        with self.m_lock:
            return (
                self.m_failure is None
                and self.m_process is not None
                and self.m_process.poll() is None
            )

    def request(
        self,
        method: str,
        params: dict[str, Any],
        *,
        before_write: Callable[[], None] | None = None,
    ) -> Future[dict[str, Any]]:
        """Send one request exactly once and return its correlated result."""

        with self.m_lock:
            if self.m_failure is not None:
                raise self.m_failure
            request_id = self.m_next_id
            self.m_next_id += 1
            future: Future[dict[str, Any]] = Future()
            self.m_pending[request_id] = future
        try:
            self._write(
                {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
                before_write=before_write,
            )
        except _AcpPrewriteRejected as exc:
            with self.m_lock:
                self.m_pending.pop(request_id, None)
            raise exc.m_error from None
        except (OSError, ValueError, DshAcpProtocolError) as exc:
            self._fail(DshAcpProtocolError(f"ACP write failed: {type(exc).__name__}"))
            if before_write is not None:
                # The caller cannot certify a complete transport handoff.
                raise DshAcpProtocolError("ACP request write did not finish") from None
        return future

    def notify(self, method: str, params: dict[str, Any]) -> None:
        """Send a notification without claiming admission or settlement."""

        try:
            self._write({"jsonrpc": "2.0", "method": method, "params": params})
        except (OSError, ValueError, DshAcpProtocolError) as exc:
            failure = DshAcpProtocolError(f"ACP notification write failed: {type(exc).__name__}")
            self._fail(failure)
            raise failure from None

    def next_notification(self, *, timeout: float = 0.0) -> dict[str, Any] | None:
        """Read one queued notification independently of outstanding requests."""

        try:
            return self.m_notifications.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self, *, timeout: float = 2.0) -> None:
        """Reap the owned process after the caller's native session closure.

        This is transport cleanup, not a substitute for ACP session cancellation
        or persistence flush. Native descendants retain their captured birth
        identities; the managed envelope separately fences external controls.
        """

        process = self.process
        self._capture_owned_processes()
        try:
            if process.stdin is not None:
                try:
                    process.stdin.close()
                except (OSError, ValueError):
                    # A failed worker may have closed its read end already.
                    pass
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._signal_owned_group(signal.SIGTERM)
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    self._signal_owned_group(signal.SIGKILL)
                    process.wait(timeout=timeout)
            # A tool may retain a protocol pipe after the worker has exited.
            # Reap only descendants whose exact identities were observed while
            # their ancestry or original process-group ownership was proven.
            self._signal_owned_group(signal.SIGKILL)
            readers = (self.m_reader, self.m_stderr_reader)
            for reader in readers:
                if reader is not None:
                    reader.join(timeout=timeout)
            if any(reader is not None and reader.is_alive() for reader in readers):
                raise DshAcpProtocolError("ACP stream cleanup did not settle")
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        except subprocess.TimeoutExpired as exc:
            raise DshAcpProtocolError("ACP worker cleanup did not settle") from exc
        finally:
            if self.m_requests is not None:
                self.m_requests.shutdown(wait=False, cancel_futures=True)
            self._fail(DshAcpProtocolError("ACP connection closed"))

    def _capture_owned_processes(self) -> None:
        """Snapshot native descendants while their original ancestry is verifiable."""

        leader = self.process.pid
        expected = self.m_process_birth_token
        if expected is None:
            return
        original = _read_process_lineage(leader)
        if original is not None and original[3] != expected:
            return
        roots = {
            pid
            for pid, birth in self.m_owned_processes.items()
            if _dispatch_origin_birth_token(pid) == birth
        }
        if original is not None:
            roots.add(leader)
        if not roots:
            return
        try:
            entries = list(Path("/proc").iterdir())
        except OSError:
            return
        observed = {
            int(path.name): identity
            for path in entries
            if path.name.isdigit()
            if (identity := _read_process_lineage(int(path.name))) is not None
        }
        owned = set(roots)
        while True:
            descendants = {pid for pid, identity in observed.items() if identity[0] in owned}
            if descendants.issubset(owned):
                break
            owned.update(descendants)
        if original is not None and original[1:3] == (leader, leader):
            owned.update(
                pid for pid, identity in observed.items() if identity[1:3] == (leader, leader)
            )
        for pid in owned:
            if pid in observed:
                self.m_owned_processes[pid] = observed[pid][3]

    def _signal_owned_group(self, signum: int) -> bool:
        """Signal the original group or its captured descendants, never a reused leader PID."""

        self._capture_owned_processes()
        leader = self.process.pid
        original = _read_process_lineage(leader)
        group_signalled = False
        if (
            self.m_process_birth_token is not None
            and original is not None
            and original[3] == self.m_process_birth_token
            and original[1:3] == (leader, leader)
        ):
            try:
                os.killpg(leader, signum)
                group_signalled = True
            except ProcessLookupError:
                pass
        signalled = group_signalled
        for pid, birth in tuple(self.m_owned_processes.items()):
            if _dispatch_origin_birth_token(pid) != birth:
                continue
            identity = _read_process_lineage(pid)
            if group_signalled and identity is not None and identity[1] == leader:
                continue
            try:
                os.kill(pid, signum)
                signalled = True
            except ProcessLookupError:
                pass
        return signalled

    def _write(
        self, frame: dict[str, Any], *, before_write: Callable[[], None] | None = None
    ) -> None:
        """Serialize writes from driver requests and permission responses."""

        if self.m_framing == "codex":
            frame = {key: value for key, value in frame.items() if key != "jsonrpc"}
        encoded = json.dumps(frame, ensure_ascii=False, allow_nan=False) + "\n"
        payload = memoryview(encoded.encode("utf-8")) if self.m_write_timeout is not None else None
        with self.m_write_lock:
            stream = self.process.stdin
            if stream is None or stream.closed:
                raise DshAcpProtocolError("ACP input is closed")
            if before_write is not None:
                if not self.healthy:
                    raise DshAcpProtocolError("ACP connection is not available for mutation")
                try:
                    before_write()
                except Exception as exc:
                    raise _AcpPrewriteRejected(exc) from exc
            if payload is None:
                stream.write(encoded)
                stream.flush()
                return
            assert self.m_write_timeout is not None
            self._write_bounded(stream.fileno(), payload, self.m_write_timeout)

    @staticmethod
    def _write_bounded(fd: int, payload: memoryview, timeout: float) -> None:
        """Write a complete frame to a nonblocking pipe within its deadline."""

        deadline = time.monotonic() + timeout
        while payload:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
                raise DshAcpProtocolError("ACP input write timed out")
            try:
                count = os.write(fd, payload)
            except BlockingIOError:
                continue
            payload = payload[count:]

    def _read_stdout(self) -> None:
        """Route frames until EOF, failing every unresolved request on loss."""

        stream = self.process.stdout
        assert stream is not None
        try:
            while line := stream.readline(_MAX_RPC_LINE + 1):
                if len(line) > _MAX_RPC_LINE or not line.endswith("\n"):
                    raise DshAcpProtocolError("Native RPC frame incomplete or exceeds its bound")
                if self.m_frame_sink is not None:
                    self.m_frame_sink(line)
                frame = json.loads(line, parse_constant=_reject_nonfinite)
                if not isinstance(frame, dict) or (
                    (self.m_framing == "acp" and frame.get("jsonrpc") != "2.0")
                    or (self.m_framing == "codex" and "jsonrpc" in frame)
                ):
                    raise DshAcpProtocolError("Invalid native JSON-RPC envelope")
                self._route(frame, len(line))
            self._fail(DshAcpProtocolError("ACP output closed before connection shutdown"))
        except (OSError, ValueError, DshAcpProtocolError) as exc:
            self._fail(DshAcpProtocolError(f"ACP protocol failure: {type(exc).__name__}"))

    def _route(self, frame: dict[str, Any], size: int) -> None:
        """Keep native notifications, server requests, and responses distinct."""

        if "method" in frame:
            if not isinstance(frame["method"], str) or not isinstance(
                frame.get("params", {}), dict
            ):
                raise DshAcpProtocolError("Invalid ACP method or parameters")
            if "id" in frame:
                if type(frame["id"]) not in (str, int):
                    raise DshAcpProtocolError("Invalid ACP server request ID")
                assert self.m_requests is not None
                if not self.m_request_slots.acquire(blocking=False):
                    raise DshAcpProtocolError("ACP reverse request capacity exceeded")
                try:
                    pending_response = self.m_requests.submit(self._answer_request, frame)
                except RuntimeError:
                    self.m_request_slots.release()
                    raise DshAcpProtocolError("ACP reverse request worker is closed") from None
                pending_response.add_done_callback(lambda _: self.m_request_slots.release())
            elif self.m_notification_sink is not None:
                self.m_notification_sink(frame, size)
            elif self.m_retain_notifications:
                self.m_notifications.put(frame)
            return
        request_id = frame.get("id")
        if type(request_id) is not int or (("result" in frame) == ("error" in frame)):
            raise DshAcpProtocolError("Invalid ACP response")
        with self.m_lock:
            future = self.m_pending.pop(request_id, None)
        if future is None:
            raise DshAcpProtocolError("Uncorrelated ACP response")
        if future.cancelled():
            return
        if "error" in frame:
            error = frame["error"]
            if not isinstance(error, dict):
                future.set_exception(DshAcpProtocolError("Invalid ACP error"))
            else:
                future.set_exception(DshAcpRequestError(error, secret_values=self.m_secret_values))
        elif frame["result"] is None:
            future.set_result({})
        elif not isinstance(frame["result"], dict):
            future.set_exception(DshAcpProtocolError("Invalid ACP result"))
        else:
            future.set_result(frame["result"])

    def _answer_request(self, frame: dict[str, Any]) -> None:
        """Answer supported requests without occupying the protocol reader."""

        response: dict[str, Any] = {"jsonrpc": "2.0", "id": frame["id"]}
        if self.m_request_handler is None:
            response["error"] = {"code": -32601, "message": "Unsupported ACP client request"}
        else:
            try:
                response["result"] = self.m_request_handler(
                    frame["method"], frame.get("params", {})
                )
            except NotImplementedError:
                response["error"] = {"code": -32601, "message": "Unsupported ACP client request"}
            except Exception:
                response["error"] = {"code": -32603, "message": "ACP client request refused"}
        try:
            self._write(response)
        except (OSError, ValueError, DshAcpProtocolError):
            self._fail(DshAcpProtocolError("ACP client response could not be written"))

    def _read_stderr(self) -> None:
        """Continuously drain diagnostics so pipe pressure cannot stall ACP."""

        stream = self.process.stderr
        assert stream is not None
        try:
            for line in stream:
                self.m_diagnostics.append(line[-4096:])
                if self.m_stderr_sink is not None:
                    self.m_stderr_sink(line)
        except (OSError, ValueError):
            self._fail(DshAcpProtocolError("ACP diagnostic stream failed"))

    def _fail(self, error: DshAcpProtocolError) -> None:
        """Permanently fail the connection; never replay pending requests."""

        with self.m_lock:
            if self.m_failure is None:
                self.m_failure = error
            pending = list(self.m_pending.values())
            self.m_pending.clear()
        for future in pending:
            if not future.done():
                future.set_exception(error)


def _read_process_lineage(pid: int) -> tuple[int, int, int, str] | None:
    """Read parent, group, session and birth identity, retaining unreaped zombie leaders."""

    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        fields = raw.rpartition(")")[2].split()
        if len(fields) < 20 or not fields[19].isdigit():
            return None
        return int(fields[1]), int(fields[2]), int(fields[3]), f"proc:{fields[19]}"
    except (OSError, ValueError, UnicodeError):
        return None


def signal_dsh_native_process(turn_dir: Path, signum: int) -> bool:
    """Fence external cleanup against the captured native process birth and group."""

    try:
        binding = json.loads((turn_dir / "dsh-native-binding.json").read_text())
        pid = binding.get("process_id")
        birth = binding.get("process_birth_token")
        if (
            type(pid) is not int
            or pid <= 0
            or not isinstance(birth, str)
            or _dispatch_origin_birth_token(pid) != birth
            or os.getpgid(pid) != pid
        ):
            return False
        os.killpg(pid, signum)
        return True
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def _reject_nonfinite(value: str) -> None:
    """Reject JavaScript-style non-finite numbers outside JSON's wire grammar."""

    raise ValueError(f"Invalid JSON numeric constant: {value}")


def validate_dsh_acp_initialization(result: Mapping[str, Any], *, require_resume: bool) -> None:
    """Require the pinned standard ACP lifecycle without trusting its version label.

    Parameters
    ----------
    result:
        Correlated ``initialize`` result from the actual owned worker.
    require_resume:
        Whether this invocation selects an exact existing conversation.
    """

    if type(result.get("protocolVersion")) is not int or result["protocolVersion"] != 1:
        raise DshAcpProtocolError("DSH does not advertise supported ACP protocol version 1")
    info = result.get("agentInfo")
    if not isinstance(info, dict) or info.get("name") != "deepseek-harness-acp":
        raise DshAcpProtocolError("ACP worker does not identify itself as DeepSeek Harness")
    capabilities = result.get("agentCapabilities")
    sessions = capabilities.get("sessionCapabilities") if isinstance(capabilities, dict) else None
    required = {"close", "resume"} if require_resume else {"close"}
    if not isinstance(sessions, dict) or any(
        not isinstance(sessions.get(name), dict) for name in required
    ):
        raise DshAcpProtocolError("DSH is missing required ACP session lifecycle capabilities")


def reject_dsh_acp_permission(
    method: str, params: Mapping[str, Any], *, session_id: str
) -> dict[str, Any]:
    """Reject external approval without overriding native startup grants or denies.

    Unattended authorization is configured in the native profile. A remaining
    question requires a responder that the managed headless transport does not
    supply. Unknown methods and wrong-session requests fail explicitly.
    """

    if method != "session/request_permission" or params.get("sessionId") != session_id:
        raise DshAcpProtocolError("Unsupported or unbound ACP client interaction")
    options = params.get("options")
    if not isinstance(options, list):
        raise DshAcpProtocolError("ACP permission options are missing")
    for option in options:
        if (
            isinstance(option, dict)
            and option.get("kind") == "reject_once"
            and isinstance(option.get("optionId"), str)
        ):
            return {"outcome": {"outcome": "selected", "optionId": option["optionId"]}}
    return {"outcome": {"outcome": "cancelled"}}
