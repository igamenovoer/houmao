"""Issue private, expiring proofs of Hermes's native tool execution context."""

from __future__ import annotations

import base64
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
import fcntl
import hashlib
import hmac
from importlib import resources
import json
import os
from pathlib import Path
import secrets
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
from typing import TYPE_CHECKING, Any

from houmao.agents.launch_env import owner_launch_baseline
from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.errors import BackendExecutionError, SessionManifestError

if TYPE_CHECKING:
    from houmao.agents.realm_controller.hermes_self import HermesSelfAuthority


HERMES_TOOL_ORIGIN_ENV = "HOUMAO_HERMES_TOOL_ORIGIN"
HERMES_TOOL_ORIGIN_PLUGIN = "houmao-tool-origin"
HERMES_TOOL_ORIGIN_VERSION = "1.0.0"

_MANIFEST = (
    f"name: {HERMES_TOOL_ORIGIN_PLUGIN}\n"
    f"version: {HERMES_TOOL_ORIGIN_VERSION}\n"
    "description: Attributes local tool execution to the current managed worker.\n"
).encode()
_MAX_FRAME = 16384
_IO_TIMEOUT = 2.0
_LIFETIME_NS = 5 * 60 * 10**9
_UNAVAILABLE = "The current Hermes tool origin is unavailable."


def hermes_tool_origin_socket(root: Path, context_id: str) -> Path:
    """Select a short Linux socket path scoped to the owner, root, and context."""

    digest = hashlib.sha256(f"{root}\0{context_id}".encode()).hexdigest()[:40]
    return Path("/tmp") / f"houmao-hermes-origin-{os.geteuid()}" / f"{digest}.sock"


def _qualified_payload(broker_socket: Path) -> dict[str, bytes]:
    """Read the shipped, dependency-free plugin and its exact private configuration."""

    if not hasattr(socket, "SO_PEERCRED") or not broker_socket.is_absolute():
        raise ValueError(_UNAVAILABLE)
    native = resources.files("houmao.agents.realm_controller.assets").joinpath(
        "hermes_tool_origin.py"
    )
    return {
        "plugin.yaml": _MANIFEST,
        "__init__.py": native.read_bytes(),
        "broker-socket": os.fsencode(broker_socket) + b"\n",
    }


def _private_node(path: Path, check: Callable[[int], bool]) -> os.stat_result:
    """Reject symlink, foreign-owner and shared-permission broker paths."""

    info = path.lstat()
    if not check(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError(_UNAVAILABLE)
    return info


def install_hermes_tool_origin_hook(profile_home: Path, *, broker_socket: Path) -> None:
    """Publish the qualified plugin inside a private profile or profile staging home."""

    parent = profile_home / "plugins"
    parent.mkdir(mode=0o700, exist_ok=True)
    _private_node(parent, stat.S_ISDIR)
    plugin = parent / HERMES_TOOL_ORIGIN_PLUGIN
    if not os.path.lexists(plugin):
        with tempfile.TemporaryDirectory(prefix=".houmao-origin-", dir=parent) as staging:
            staged = Path(staging)
            for name, data in _qualified_payload(broker_socket).items():
                descriptor = os.open(staged / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data)
            staged.rename(plugin)
    require_hermes_tool_origin_hook(profile_home, broker_socket=broker_socket)


def require_hermes_tool_origin_hook(profile_home: Path, *, broker_socket: Path) -> None:
    """Verify that the managed profile carries the expected native plugin bytes."""

    parent = profile_home / "plugins"
    plugin = parent / HERMES_TOOL_ORIGIN_PLUGIN
    _private_node(parent, stat.S_ISDIR)
    _private_node(plugin, stat.S_ISDIR)
    for name, expected in _qualified_payload(broker_socket).items():
        descriptor = os.open(plugin / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(descriptor)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077
                or stream.read(len(expected) + 1) != expected
            ):
                raise ValueError(_UNAVAILABLE)


def enable_hermes_tool_origin_hook(config: dict[str, Any]) -> None:
    """Add the Houmao-owned plugin to the profile's native enable list."""

    plugins = config.setdefault("plugins", {})
    if not isinstance(plugins, dict):
        raise ValueError("Hermes profile plugins configuration must be a mapping.")
    for key in ("enabled", "disabled"):
        entries = plugins.get(key, [])
        if not isinstance(entries, list) or any(not isinstance(entry, str) for entry in entries):
            raise ValueError(f"Hermes profile plugins.{key} configuration must be a string list.")
        plugins[key] = [entry for entry in entries if entry != HERMES_TOOL_ORIGIN_PLUGIN]
    plugins["enabled"].append(HERMES_TOOL_ORIGIN_PLUGIN)


@dataclass(frozen=True)
class _BrokerScope:
    """Pin the proof broker to one verified owner gateway incarnation."""

    root: Path
    context_id: str
    daemon_pid: int
    birth_token: str

    @property
    def path(self) -> Path:
        """Return this owner's broker socket."""

        return hermes_tool_origin_socket(self.root, self.context_id)

    def daemon_is_current(self) -> bool:
        """Check the pinned gateway process against the kernel birth identity."""

        return _dispatch_origin_birth_token(self.daemon_pid) == self.birth_token


def _peer_pid(peer: socket.socket) -> int:
    """Verify same-owner peer credentials and return the kernel's peer PID."""

    if not hasattr(socket, "SO_PEERCRED"):
        raise ValueError(_UNAVAILABLE)
    pid, uid, _ = struct.unpack(
        "3i", peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    )
    if uid != os.geteuid() or pid <= 1:
        raise ValueError(_UNAVAILABLE)
    return int(pid)


def _read_frame(peer: socket.socket) -> object:
    """Read one bounded JSON message without echoing its input in errors."""

    with peer.makefile("rb") as stream:
        data = stream.readline(_MAX_FRAME + 1)
    if len(data) > _MAX_FRAME or not data.endswith(b"\n"):
        raise ValueError(_UNAVAILABLE)
    return json.loads(data)


def _query(path: Path, payload: dict[str, object]) -> tuple[int, object]:
    """Check the private socket and exchange one message with its owner."""

    _private_node(path.parent, stat.S_ISDIR)
    _private_node(path, stat.S_ISSOCK)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
        peer.settimeout(_IO_TIMEOUT)
        peer.connect(str(path))
        pid = _peer_pid(peer)
        peer.sendall(json.dumps(payload).encode() + b"\n")
        return pid, _read_frame(peer)


def _current_broker_pid(scope: _BrokerScope) -> int | None:
    """Find a running broker pinned to the expected live gateway."""

    with suppress(OSError, ValueError):
        peer_pid, response = _query(scope.path, {"op": "ping"})
        if response == [scope.daemon_pid, scope.birth_token]:
            return peer_pid
    return None


def ensure_hermes_tool_origin_broker(
    root: Path, context_id: str, *, daemon_pid: int, daemon_birth_token: str
) -> Path:
    """Start or reuse the private broker under the shared gateway lifecycle lock."""

    scope = _BrokerScope(root, context_id, daemon_pid, daemon_birth_token)
    if not hasattr(socket, "SO_PEERCRED") or not scope.daemon_is_current():
        raise BackendExecutionError(_UNAVAILABLE)
    if _current_broker_pid(scope) is not None:
        return scope.path
    child = subprocess.Popen(
        [
            sys.executable,
            "-m",
            __name__,
            str(root),
            context_id,
            str(daemon_pid),
            daemon_birth_token,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=owner_launch_baseline(os.environ),
    )
    ready_pid = None
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            ready_pid = _current_broker_pid(scope)
            if ready_pid is not None:
                return scope.path
            if child.poll() is not None or not scope.daemon_is_current():
                break
            time.sleep(0.025)
    finally:
        if ready_pid != child.pid and child.poll() is None:
            child.terminate()
            with suppress(subprocess.TimeoutExpired):
                child.wait(timeout=2)
    raise BackendExecutionError(_UNAVAILABLE)


def require_hermes_tool_origin(authority: HermesSelfAuthority, token: str | None) -> None:
    """Verify an opaque proof for this exact current routed binding."""

    if authority.broker_socket is None or token is None or len(token) != 64 or not token.isascii():
        raise SessionManifestError(_UNAVAILABLE)
    try:
        _, verdict = _query(
            Path(authority.broker_socket),
            {
                "op": "verify",
                "home": authority.home,
                "session": authority.native_session_id,
                "binding": authority.fingerprint,
                "proof": token,
            },
        )
    except (OSError, ValueError):
        raise SessionManifestError(_UNAVAILABLE) from None
    if verdict is not True:
        raise SessionManifestError(_UNAVAILABLE)


def _token_signature(secret: bytes, binding: str, invocation: bytes) -> bytes:
    """Authenticate a bounded invocation for a single exact authority."""

    return hmac.digest(secret, binding.encode() + invocation, "sha256")


def _handle_request(scope: _BrokerScope, secret: bytes, pid: int, payload: object) -> object:
    """Issue only to the verified native daemon, and verify only current bindings."""

    # Deferred imports avoid recursive initialization when this module is the broker entrypoint.
    from houmao.agents.realm_controller.hermes_self import load_hermes_tool_authority

    if not isinstance(payload, dict) or not scope.daemon_is_current():
        return None
    op = payload.get("op")
    if op == "ping" and set(payload) == {"op"}:
        return [scope.daemon_pid, scope.birth_token]
    if op == "issue":
        if pid != scope.daemon_pid or set(payload) != {"op", "home", "session"}:
            return None
    elif op != "verify" or set(payload) != {"op", "home", "session", "binding", "proof"}:
        return None
    home = payload.get("home")
    session = payload.get("session")
    if not isinstance(home, str) or not isinstance(session, str):
        return None
    authority = load_hermes_tool_authority(
        Path(home),
        session,
        gateway_root=scope.root,
        context_id=scope.context_id,
        broker_socket=scope.path,
        pid=scope.daemon_pid,
        birth_token=scope.birth_token,
    )
    binding = authority.fingerprint
    now = time.monotonic_ns()
    if op == "issue":
        invocation = struct.pack("!Q", now + _LIFETIME_NS) + secrets.token_bytes(8)
        return base64.urlsafe_b64encode(
            invocation + _token_signature(secret, binding, invocation)
        ).decode()
    token = payload.get("proof")
    if payload.get("binding") != binding or not isinstance(token, str) or len(token) != 64:
        return False
    data = base64.b64decode(token, altchars=b"-_", validate=True)
    invocation = data[:16]
    expires = struct.unpack("!Q", invocation[:8])[0]
    return now < expires and hmac.compare_digest(
        data[16:], _token_signature(secret, binding, invocation)
    )


def _serve(scope: _BrokerScope) -> None:
    """Serve while the exact gateway lives, then remove the owned socket."""

    path = scope.path
    path.parent.mkdir(mode=0o700, exist_ok=True)
    _private_node(path.parent, stat.S_ISDIR)
    lock = os.open(path.with_suffix(".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(lock)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError(_UNAVAILABLE)
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not scope.daemon_is_current():
            return
        if os.path.lexists(path):
            _private_node(path, stat.S_ISSOCK)
            path.unlink()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(path))
            original = path.lstat()
            try:
                path.chmod(0o600)
                server.listen(16)
                server.settimeout(0.2)
                secret = secrets.token_bytes(32)
                while scope.daemon_is_current():
                    try:
                        peer, _ = server.accept()
                    except TimeoutError:
                        continue
                    with peer:
                        peer.settimeout(_IO_TIMEOUT)
                        try:
                            response = _handle_request(
                                scope, secret, _peer_pid(peer), _read_frame(peer)
                            )
                        except (OSError, ValueError, RuntimeError):
                            response = None
                        with suppress(OSError):
                            peer.sendall(json.dumps(response).encode() + b"\n")
            finally:
                with suppress(FileNotFoundError):
                    current = path.lstat()
                    if (current.st_dev, current.st_ino) == (original.st_dev, original.st_ino):
                        path.unlink()
    finally:
        os.close(lock)


if __name__ == "__main__":
    try:
        _serve(_BrokerScope(Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4]))
    except (OSError, ValueError, IndexError):
        raise SystemExit(1) from None
