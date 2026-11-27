"""Discover and control the Hermes daemon launched for a managed home."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import select
import signal
import socket
import stat
import struct
import subprocess
import tempfile
import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from websockets.exceptions import WebSocketException
from websockets.sync.client import connect
from websockets.sync.connection import Connection
from websockets.typing import Subprotocol

from houmao.agents.launch_env import owner_launch_baseline
from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessProcessMetadata,
    _pinned_worker,
    _signal_worker,
)
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.models import LaunchPlan
from houmao.agents.realm_controller.startup_rollback import (
    current_runtime_startup,
    stop_owned_startup_child,
)
from houmao.agents.realm_controller.owner_admission import owner_process_has_exited
from houmao.execution.context import current_execution_deadline

_CANONICAL_PROTOCOL = "hermes-gateway-v1"
_TICKET_PREFIX = "hermes-gateway-ticket."
_CONTROL_TIMEOUT = 2.0
_RPC_TIMEOUT = 30.0
_MAX_CONTROL_BYTES = 512 * 1024
_MAX_FRAME_BYTES = 8 * 1024 * 1024
_STARTUP_TIMEOUT = 45.0
_STOP_TIMEOUT = 15.0


class HermesNativeError(BackendExecutionError):
    """Report an unavailable or mismatched native Hermes authority."""


class HermesDeadlineExpired(HermesNativeError):
    """Refuse a native operation that has no remaining time before it starts."""


def _native_timeout(limit: float) -> float:
    """Cap a native wait at the active delegated execution deadline."""

    deadline = current_execution_deadline()
    if deadline is None:
        return limit
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise HermesDeadlineExpired("The execution deadline expired before the Hermes operation.")
    return min(remaining, limit)


class HermesRpcRefused(HermesNativeError):
    """A correlated native RPC explicitly refused the request."""

    def __init__(self, reason: str) -> None:
        """Record a bounded native reason code."""

        self.m_reason = reason
        super().__init__(f"Hermes refused the native request ({reason}).")

    @property
    def reason(self) -> str:
        """Return the native reason code suitable for recovery decisions."""

        return self.m_reason


@dataclass(frozen=True)
class HermesDaemonIdentity:
    """Identify a daemon, its owning home, and the current native authority."""

    home: Path
    pid: int
    birth_token: str
    instance_id: str
    authority_epoch: int
    profile_id: str = field(repr=False)
    websocket_url: str = field(repr=False)


@dataclass(frozen=True)
class HermesSessionSnapshot:
    """Return a verified logical conversation in the recorded workspace."""

    session_id: str
    payload: dict[str, Any] = field(repr=False)
    daemon_instance_id: str | None = None

    @property
    def ready(self) -> bool:
        """Require an explicit idle snapshot without pending native work."""

        return (
            self.payload.get("running") is False
            and all(self.payload.get(key) == [] for key in ("pending", "prompts", "open_requests"))
            and not self.payload.get("pending_connection")
        )


def hermes_daemon_environment(home: Path, env: Mapping[str, str]) -> dict[str, str]:
    """Scope the daemon and stock clients to the same isolated Hermes home."""

    selected = {**owner_launch_baseline(os.environ), **env}
    for name in ("HERMES_TUI_GATEWAY_URL", "HERMES_TUI_SIDECAR_URL", "TMUX", "TMUX_PANE"):
        selected.pop(name, None)
    selected["HERMES_HOME"] = str(home)
    selected["HERMES_GATEWAY_LOCK_DIR"] = str(home / ".houmao-gateway-locks")
    return selected


class HermesClient:
    """A bounded request/response stream to one authenticated Hermes incarnation."""

    def __init__(self, connection: Connection, identity: HermesDaemonIdentity) -> None:
        """Initialize the private connection with increasing request IDs."""

        self.m_connection: Connection = connection
        self.m_identity: HermesDaemonIdentity = identity
        self.m_request_id: int = 0

    @property
    def identity(self) -> HermesDaemonIdentity:
        """Return the incarnation proved by this connection's bootstrap."""

        return self.m_identity

    def rpc(self, method: str, **params: Any) -> dict[str, Any]:
        """Return one correlated native response, ignoring unrelated notifications."""

        self.m_request_id += 1
        request_id = self.m_request_id
        deadline = time.monotonic() + _native_timeout(_RPC_TIMEOUT)
        frame = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        serialized = json.dumps(frame)
        try:
            if current_execution_deadline() is None:
                self.m_connection.send(serialized)
            else:
                self.m_connection.socket.settimeout(_native_timeout(_RPC_TIMEOUT))
                try:
                    self.m_connection.send(serialized)
                finally:
                    self.m_connection.socket.settimeout(None)
            while time.monotonic() < deadline:
                incoming = json.loads(
                    self.m_connection.recv(timeout=max(0, deadline - time.monotonic()))
                )
                if not isinstance(incoming, dict):
                    raise HermesNativeError("Hermes returned a malformed RPC frame.")
                if incoming.get("id") != request_id or "method" in incoming:
                    continue
                if "error" in incoming:
                    error = incoming["error"]
                    data = error.get("data") if isinstance(error, dict) else None
                    reason = error.get("message") if isinstance(error, dict) else None
                    if isinstance(data, dict) and isinstance(data.get("reason"), str):
                        reason = data["reason"]
                    raise HermesRpcRefused(_bounded_reason(reason))
                result = incoming.get("result")
                if isinstance(result, dict):
                    return result
                raise HermesNativeError("Hermes returned a malformed RPC result.")
        except (OSError, TimeoutError, WebSocketException, ValueError) as exc:
            raise HermesNativeError(f"Hermes RPC connection failed during {method}.") from exc
        raise HermesNativeError(f"Hermes RPC timed out during {method}.")


class HermesDaemon:
    """Manage the daemon launched for one exact Houmao-owned Hermes home."""

    def __init__(self) -> None:
        """Initialize configuration before discovery or startup."""

        self.m_executable: str = ""
        self.m_home: Path = Path()
        self.m_workspace: Path = Path()
        self.m_env: dict[str, str] = {}
        self.m_root: Path = Path()
        self.m_child: subprocess.Popen[bytes] | None = None

    @classmethod
    def from_inputs(
        cls,
        *,
        executable: str,
        home: Path,
        workspace: Path,
        env: Mapping[str, str],
        root: Path,
    ) -> HermesDaemon:
        """Create owner control from an already resolved native launch."""

        daemon = cls()
        daemon.m_executable = executable
        daemon.m_home = home.resolve()
        daemon.m_workspace = workspace.resolve()
        daemon.m_env = hermes_daemon_environment(daemon.m_home, env)
        daemon.m_root = root.resolve()
        return daemon

    @classmethod
    def from_launch_plan(cls, plan: LaunchPlan, root: Path) -> HermesDaemon:
        """Create owner control from a managed launch plan."""

        return cls.from_inputs(
            executable=plan.executable,
            home=plan.home_path,
            workspace=plan.working_directory,
            env=plan.env,
            root=root,
        )

    @property
    def workspace(self) -> Path:
        """Return the expected canonical workspace."""

        return self.m_workspace

    def _identify_process(self) -> tuple[dict[str, Any], int, str] | None:
        """Verify the launch home and process even while native RPC is unavailable."""

        try:
            answer, peer_pid = _control_query(self.m_home, "identify")
        except (FileNotFoundError, ConnectionRefusedError):
            return None
        daemon_home = answer.get("hermes_home")
        if (
            not isinstance(daemon_home, str)
            or not Path(daemon_home).is_absolute()
            or (Path(daemon_home).resolve() != self.m_home)
        ):
            raise HermesNativeError("The discovered Hermes daemon has a different launch home.")
        pid = answer.get("pid")
        if (
            type(pid) is not int
            or pid <= 1
            or pid == os.getpid()
            or (peer_pid is not None and peer_pid != pid)
        ):
            raise HermesNativeError("Cannot verify the Hermes daemon process identity.")
        birth = _dispatch_origin_birth_token(pid)
        start_time = answer.get("start_time")
        if (
            birth is None
            or type(start_time) is not int
            or (birth.startswith("proc:") and birth != f"proc:{start_time}")
        ):
            raise HermesNativeError("The Hermes daemon process identity is stale or unavailable.")
        return answer, pid, birth

    def discover(self) -> HermesDaemonIdentity | None:
        """Read a ready daemon identity for the exact home without spawning a process."""

        process = self._identify_process()
        if process is None:
            return None
        answer, pid, birth = process
        if answer.get("state") in ("starting", "draining"):
            return None
        capabilities = answer.get("capabilities")
        authority_epoch = answer.get("authority_epoch")
        instance_id = answer.get("instance_id")
        if (
            answer.get("state") != "ready"
            or answer.get("runtime_protocol") != 1
            or not isinstance(capabilities, list)
            or "session-authority-v1" not in capabilities
            or type(authority_epoch) is not int
            or authority_epoch <= 0
            or not isinstance(instance_id, str)
            or not instance_id.strip()
        ):
            raise HermesNativeError("Hermes has no ready native session authority.")
        profiles = answer.get("served_profiles")
        profile = _launch_profile(profiles, self.m_home)
        return HermesDaemonIdentity(
            home=self.m_home,
            pid=pid,
            birth_token=birth,
            instance_id=instance_id,
            authority_epoch=authority_epoch,
            profile_id=profile,
            websocket_url=_websocket_url(answer.get("api_origin")),
        )

    def ensure(self) -> HermesDaemonIdentity:
        """Start a vacant home or adopt its existing daemon through native discovery."""

        with _lifecycle_lock(self.m_root):
            deadline = time.monotonic() + _STARTUP_TIMEOUT
            launched = False
            try:
                while time.monotonic() < deadline:
                    identity = self.discover()
                    if identity is not None:
                        self._record(identity)
                        return identity
                    if launched and self.m_child is not None and self.m_child.poll() is not None:
                        if not _runtime_lock_held(self.m_home):
                            raise HermesNativeError(
                                f"Hermes daemon exited with status {self.m_child.returncode}. "
                                f"See the private startup log at {self.m_root / 'hermes-daemon.log'}."
                            )
                    if not launched and not _runtime_lock_held(self.m_home):
                        self._start()
                        launched = True
                    time.sleep(0.05)
                raise HermesNativeError(
                    "Timed out waiting for the daemon in the managed Hermes home."
                )
            except (HermesNativeError, OSError, KeyboardInterrupt):
                if launched and self.m_child is not None and self.m_child.poll() is None:
                    self.m_child.terminate()
                    try:
                        self.m_child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.m_child.kill()
                        with suppress(subprocess.TimeoutExpired):
                            self.m_child.wait(timeout=2)
                raise

    def _start(self) -> None:
        """Start the foreground daemon with private stderr and stdout."""

        log_path = self.m_root / "hermes-daemon.log"
        startup = current_runtime_startup()
        try:
            descriptor = os.open(
                log_path,
                os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(descriptor, "ab") as log:
                if startup is not None:
                    startup.retain_diagnostic(log_path)
                process = subprocess.Popen(
                    [self.m_executable, "gateway", "run", "--external-supervisor"],
                    cwd=self.m_workspace,
                    env=self.m_env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
                self.m_child = process
                if startup is not None:
                    startup.add("new Hermes daemon", lambda: stop_owned_startup_child(process))
        except OSError as exc:
            raise HermesNativeError(
                f"Could not start the local Hermes daemon ({exc.strerror})."
            ) from exc

    def _record(self, identity: HermesDaemonIdentity) -> None:
        """Persist process evidence without persisting endpoints, tickets, or configuration."""

        write_hermes_evidence(
            self.m_root / "hermes-daemon.json",
            {
                "home": str(identity.home),
                "workspace": str(self.m_workspace),
                "pid": identity.pid,
                "birth_token": identity.birth_token,
                "instance_id": identity.instance_id,
                "authority_epoch": identity.authority_epoch,
            },
        )

    @contextmanager
    def client(self) -> Iterator[HermesClient]:
        """Mint a single-use native ticket and verify the connected authority."""

        identity = self.discover()
        if identity is None:
            raise HermesNativeError("The daemon in the managed Hermes home is unavailable.")
        try:
            ticket, peer_pid = _control_query(
                self.m_home,
                "session-ticket",
                {
                    "profile_id": identity.profile_id,
                    "instance_id": identity.instance_id,
                    "purpose": "interactive",
                    "scope": "profile",
                },
            )
            credential = ticket.get("ticket")
            if (
                ticket.get("instance_id") != identity.instance_id
                or ticket.get("profile_id") != identity.profile_id
                or (peer_pid is not None and peer_pid != identity.pid)
                or not isinstance(credential, str)
                or not credential
            ):
                raise HermesNativeError("The Hermes daemon changed during native discovery.")
            socket_options = [
                Subprotocol(_CANONICAL_PROTOCOL),
                Subprotocol(_TICKET_PREFIX + credential),
            ]
            with connect(
                identity.websocket_url,
                subprotocols=socket_options,
                proxy=None,
                open_timeout=_native_timeout(_CONTROL_TIMEOUT),
                close_timeout=_CONTROL_TIMEOUT if current_execution_deadline() is None else 0,
                max_size=_MAX_FRAME_BYTES,
            ) as ws:
                if ws.subprotocol != _CANONICAL_PROTOCOL:
                    raise HermesNativeError("Hermes failed native protocol negotiation.")
                native = HermesClient(ws, identity)
                description = native.rpc("runtime.describe")
                if any(
                    description.get(key) != value
                    for key, value in {
                        "instance_id": identity.instance_id,
                        "profile_id": identity.profile_id,
                        "authority_epoch": identity.authority_epoch,
                    }.items()
                ):
                    raise HermesNativeError("Hermes reported a different native authority.")
                self._record(identity)
                try:
                    yield native
                finally:
                    deadline = current_execution_deadline()
                    if deadline is not None:
                        ws.close_timeout = max(
                            0.0, min(_CONTROL_TIMEOUT, deadline - time.monotonic())
                        )
        except (OSError, ValueError, WebSocketException) as exc:
            raise HermesNativeError("Could not authenticate to the local Hermes daemon.") from exc

    def create_session(self, *, source: str, request_id: str) -> HermesSessionSnapshot:
        """Create an idempotent native conversation in the selected workspace."""

        with self.client() as native:
            created = native.rpc(
                "session.create", source=source, cwd=str(self.m_workspace), request_id=request_id
            )
            return self.verify_snapshot(created, native.identity)

    def resolve_session(self, session_id: str) -> HermesSessionSnapshot:
        """Mount an exact native conversation without title or latest lookup."""

        with self.client() as native:
            return self.resume_session(native, session_id)

    def resume_session(self, native: HermesClient, session_id: str) -> HermesSessionSnapshot:
        """Verify an exact native conversation on an already authenticated connection."""

        snapshot = native.rpc("session.resume", session_id=session_id, omit_messages=True)
        return self.verify_snapshot(snapshot, native.identity, session_id=session_id)

    def verify_snapshot(
        self,
        snapshot: dict[str, Any],
        identity: HermesDaemonIdentity,
        *,
        session_id: str | None = None,
    ) -> HermesSessionSnapshot:
        """Accept the durable native logical ID, including native compression lineage."""

        logical_id = snapshot.get("stored_session_id")
        info = snapshot.get("info")
        if (
            not isinstance(logical_id, str)
            or not logical_id.strip()
            or snapshot.get("session_id") != logical_id
            or (session_id is not None and session_id != logical_id)
            or snapshot.get("authority_epoch") != identity.authority_epoch
            or not isinstance(info, dict)
            or info.get("profile_id") != identity.profile_id
            or not isinstance(info.get("cwd"), str)
            or not Path(info["cwd"]).is_absolute()
            or Path(info["cwd"]).resolve() != self.m_workspace
        ):
            raise HermesNativeError(
                "Hermes did not verify the exact session in the managed workspace."
            )
        return HermesSessionSnapshot(logical_id, snapshot, identity.instance_id)

    def stop(self) -> None:
        """Stop the exact same-home daemon and wait for that process to exit."""

        with _lifecycle_lock(self.m_root):
            process = self._identify_process()
            if process is not None:
                _, pid, birth = process
            else:
                record = read_hermes_evidence(self.m_root / "hermes-daemon.json")
                if record is None or record.get("home") != str(self.m_home):
                    if _runtime_lock_held(self.m_home):
                        raise HermesNativeError(
                            "Cannot verify which Hermes daemon should be stopped."
                        )
                    return
                saved_pid, saved_birth = record.get("pid"), record.get("birth_token")
                if type(saved_pid) is not int or saved_pid <= 1 or not isinstance(saved_birth, str):
                    raise HermesNativeError("The recorded Hermes daemon identity is invalid.")
                pid, birth = saved_pid, saved_birth
            if owner_process_has_exited(pid, birth):
                if _runtime_lock_held(self.m_home):
                    raise HermesNativeError("Cannot verify which Hermes daemon should be stopped.")
                return
            _stop_identity(pid, birth)
            if self.m_child is not None and self.m_child.pid == pid:
                self.m_child.poll()
            else:
                with suppress(ChildProcessError):
                    os.waitpid(pid, os.WNOHANG)


def _launch_profile(profiles: object, home: Path) -> str:
    """Read the profile ticket scope matching the verified launch home."""

    if isinstance(profiles, list):
        matching = [
            profile.get("profile_id")
            for profile in profiles
            if isinstance(profile, dict) and profile.get("home") == str(home)
        ]
        if len(matching) == 1 and isinstance(matching[0], str) and matching[0]:
            return matching[0]
    raise HermesNativeError("Hermes did not advertise the exact managed launch home.")


def _bounded_reason(reason: object) -> str:
    """Suppress uncontrolled strings from a native refusal."""

    if isinstance(reason, str) and re.fullmatch(r"[A-Za-z0-9_]{1,80}", reason):
        return reason
    return "request_failed"


def _websocket_url(origin: object) -> str:
    """Convert a literal loopback API origin to the private RPC endpoint."""

    if isinstance(origin, str):
        with suppress(ValueError):
            parts = urlsplit(origin)
            if (
                parts.scheme in {"http", "https"}
                and parts.username is None
                and parts.password is None
                and not (parts.path or parts.query or parts.fragment)
                and parts.hostname
                and ipaddress.ip_address(parts.hostname).is_loopback
                and parts.port
            ):
                return urlunsplit(
                    ("wss" if parts.scheme == "https" else "ws", parts.netloc, "/api/ws", "", "")
                )
    raise HermesNativeError("Hermes did not publish a private loopback endpoint.")


def _private_node(path: Path, check: Any) -> None:
    """Validate a private socket or directory without following symlinks."""

    info = path.lstat()
    if not check(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise HermesNativeError("Hermes native control is not in an owner-private location.")


def _socket_path(home: Path) -> Path:
    """Find the normal or long-path fallback socket for this exact home."""

    _private_node(home, stat.S_ISDIR)
    direct = home / "gateway.sock"
    if os.path.lexists(direct):
        _private_node(direct, stat.S_ISSOCK)
        return direct
    pointer = home / "gateway.sock.path"
    descriptor = os.open(pointer, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise HermesNativeError("Hermes gateway socket metadata is not private.")
        path_data = stream.read(4097)
    if len(path_data) > 4096:
        raise HermesNativeError("Hermes gateway socket metadata is invalid.")
    try:
        target = Path(path_data.decode("utf-8").strip())
    except UnicodeError as exc:
        raise HermesNativeError("Hermes gateway socket metadata is invalid.") from exc
    handle = hashlib.sha256(os.path.normcase(str(home)).encode()).hexdigest()[:16]
    if (
        not target.is_absolute()
        or target.name != "control.sock"
        or target.parent.name != f"hermes-gw-{handle}"
    ):
        raise HermesNativeError("Hermes gateway socket metadata names a different home.")
    _private_node(target.parent, stat.S_ISDIR)
    _private_node(target, stat.S_ISSOCK)
    return target


def _control_query(
    home: Path, verb: str, params: dict[str, Any] | None = None
) -> tuple[dict[str, Any], int | None]:
    """Use the same-user Unix control socket for one bounded native bootstrap request."""

    request = {"protocol": 1, "id": 1, "verb": verb, "params": params or {}}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
            timeout = _native_timeout(_CONTROL_TIMEOUT)
            deadline = time.monotonic() + timeout
            peer.settimeout(timeout)
            peer.connect(str(_socket_path(home)))
            pid = _verify_control_peer(peer)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            peer.settimeout(remaining)
            peer.sendall(json.dumps(request).encode() + b"\n")
            data = bytearray()
            while b"\n" not in data:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                peer.settimeout(remaining)
                chunk = peer.recv(min(8192, _MAX_CONTROL_BYTES + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > _MAX_CONTROL_BYTES:
                    raise HermesNativeError(
                        "Hermes native control response exceeds its size limit."
                    )
        response = json.loads(bytes(data).split(b"\n", 1)[0])
    except (FileNotFoundError, ConnectionRefusedError):
        raise
    except (OSError, ValueError) as exc:
        raise HermesNativeError(f"Hermes native control failed during {verb}.") from exc
    if (
        not isinstance(response, dict)
        or response.get("ok") is not True
        or response.get("id") != 1
        or response.get("protocol") != 1
        or not isinstance(response.get("result"), dict)
    ):
        raise HermesNativeError(f"Hermes native control refused {verb}.")
    return response["result"], pid


def _verify_control_peer(peer: socket.socket) -> int | None:
    """Verify same-user peer credentials where POSIX exposes them."""

    if hasattr(socket, "SO_PEERCRED"):
        size = struct.calcsize("3i")
        pid, uid, _ = struct.unpack(
            "3i", peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, size)
        )
        if uid != os.getuid():
            raise HermesNativeError("Hermes native control is owned by a different user.")
        return int(pid)
    return None


def _runtime_lock_held(home: Path) -> bool:
    """Observe an in-progress Hermes startup without creating the lock file."""

    try:
        descriptor = os.open(home / "gateway.lock", os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise HermesNativeError("Cannot verify the managed Hermes home lock.") from exc
    with os.fdopen(descriptor, "rb+") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise HermesNativeError("The managed Hermes home lock is invalid.")
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False


@contextmanager
def _lifecycle_lock(root: Path) -> Iterator[None]:
    """Serialize startup and stop for the recorded managed runtime."""

    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(
        root / "hermes-lifecycle.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "rb+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def _stop_identity(pid: int, birth: str) -> None:
    """Signal a pinned process handle to prevent PID reuse from retargeting stop."""

    try:
        with _pinned_worker(HeadlessProcessMetadata(child_pid=pid, child_birth_token=birth)) as fd:
            _signal_worker(fd, signal.SIGTERM)
            poller = select.poll()
            poller.register(fd, select.POLLIN)
            if not poller.poll(round(_STOP_TIMEOUT * 1000)):
                raise HermesNativeError("The selected Hermes daemon did not exit after stop.")
    except (OSError, ValueError, AttributeError) as exc:
        if not owner_process_has_exited(pid, birth):
            raise HermesNativeError(
                "Cannot safely stop the selected Hermes daemon process."
            ) from exc


def write_hermes_evidence(path: Path, payload: dict[str, Any]) -> None:
    """Publish one owner-private evidence file atomically."""

    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        with suppress(FileNotFoundError):
            os.unlink(name)


def read_hermes_evidence(path: Path) -> dict[str, Any] | None:
    """Read an owner-private evidence object if one exists."""

    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    try:
        with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise HermesNativeError("Hermes evidence is not owner-private.")
            record = json.load(stream)
    except (OSError, ValueError) as exc:
        raise HermesNativeError("Hermes evidence could not be read.") from exc
    if not isinstance(record, dict):
        raise HermesNativeError("Hermes evidence is malformed.")
    return record
