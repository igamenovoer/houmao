"""Request-scoped launch fencing for immediate headless message dispatch."""

from __future__ import annotations

from collections.abc import Callable
import json
import math
import os
from pathlib import Path
import subprocess
import threading
import time
import uuid

from houmao.agents.realm_controller.errors import BackendExecutionError


class HeadlessDispatchControl:
    """Fence one client launch and report its confirmed process handoff.

    A permission sidecar contains only an expiry and execution identity. It is
    never a message store and cannot authorize replay after a failed request.
    """

    def __init__(self) -> None:
        """Initialize an inactive dispatch controller."""

        self.m_allowed: Callable[[], bool] = lambda: False
        self.m_confirmed: Callable[[], None] = lambda: None
        self.m_deadline: float = 0.0
        self.m_cancelled: threading.Event = threading.Event()
        self.m_lock: threading.Lock = threading.Lock()
        self.m_permission_path: Path | None = None
        self.m_manifest_path: Path | None = None
        self.m_generation_id: str | None = None
        self.m_origin_pid: int = os.getpid()
        self.m_origin_birth_token: str | None = _dispatch_origin_birth_token(self.m_origin_pid)
        self.m_handoff_confirmed: threading.Event = threading.Event()
        self.m_input_started: threading.Event = threading.Event()
        self.m_handoff_alive: Callable[[], bool] = lambda: True

    @classmethod
    def from_callbacks(
        cls,
        *,
        allowed: Callable[[], bool],
        confirmed: Callable[[], None],
        deadline: float,
        manifest_path: Path | None = None,
        generation_id: str | None = None,
    ) -> HeadlessDispatchControl:
        """Create request-scoped launch permission from the live caller."""

        instance = cls()
        instance.m_allowed = allowed
        instance.m_confirmed = confirmed
        instance.m_deadline = deadline
        instance.m_manifest_path = manifest_path
        instance.m_generation_id = generation_id
        return instance

    def require_allowed(self) -> None:
        """Reject canceled, expired, or superseded execution before handoff."""

        if self.m_cancelled.is_set() or time.monotonic() >= self.m_deadline or not self.m_allowed():
            raise BackendExecutionError("Immediate dispatch permission is no longer active")

    def prepare_bridge_permission(self, turn_dir: Path) -> Path:
        """Publish a payload-free launch fence for the separate bridge process."""

        self.require_allowed()
        if self.m_origin_birth_token is None:
            raise BackendExecutionError("Immediate dispatch origin identity is unavailable")
        with self.m_lock:
            self.m_permission_path = turn_dir / ".dispatch-permission.json"
            self._write_permission_locked(active=not self.m_cancelled.is_set())
            return self.m_permission_path

    def confirm_handoff(self) -> None:
        """Notify the caller only after launching its actual client process."""

        if self.m_handoff_confirmed.is_set():
            return
        self.require_allowed()
        self.m_handoff_confirmed.set()
        self.m_confirmed()

    def cancel(self) -> None:
        """Permanently revoke this attempt, including a bridge not yet launched."""

        self.m_cancelled.set()
        with self.m_lock:
            self._write_permission_locked(active=False)

    def _write_permission_locked(self, *, active: bool) -> None:
        """Atomically replace launch permission without retaining event content."""

        path = self.m_permission_path
        if path is None:
            return
        payload = {
            "active": active,
            "expires_at": time.time() + max(0.0, self.m_deadline - time.monotonic()),
            "manifest_path": str(self.m_manifest_path) if self.m_manifest_path else None,
            "registry_generation_id": self.m_generation_id,
            "origin_pid": self.m_origin_pid,
            "origin_birth_token": self.m_origin_birth_token,
        }
        temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def headless_dispatch_permission_allowed(path: Path) -> bool:
    """Validate a bridge's request permission immediately before client launch."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("active") is not True:
            return False
        expires_at = payload.get("expires_at")
        if (
            isinstance(expires_at, bool)
            or not isinstance(expires_at, (int, float))
            or not math.isfinite(expires_at)
        ):
            return False
        if not time.time() < expires_at:
            return False
        origin_pid = payload.get("origin_pid")
        origin_birth_token = payload.get("origin_birth_token")
        if (
            type(origin_pid) is not int
            or origin_pid <= 0
            or not isinstance(origin_birth_token, str)
            or not origin_birth_token
            or _dispatch_origin_birth_token(origin_pid) != origin_birth_token
        ):
            return False
        manifest_path = payload.get("manifest_path")
        generation = payload.get("registry_generation_id")
        if manifest_path is not None:
            if not isinstance(manifest_path, str) or not isinstance(generation, str):
                return False
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                return False
            if manifest.get("registry_generation_id") != generation:
                return False
        return True
    except (OSError, ValueError, TypeError):
        return False


def _dispatch_origin_birth_token(pid: int) -> str | None:
    """Read one live process birth identity, including PID-reuse protection."""

    try:
        raw_stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return _dispatch_origin_ps_birth_token(pid)
    fields = raw_stat.rpartition(")")[2].split()
    if len(fields) < 20 or fields[0] in {"Z", "X", "x"} or not fields[19].isdigit():
        return None
    return f"proc:{fields[19]}"


def _dispatch_origin_ps_birth_token(pid: int) -> str | None:
    """Use POSIX process start time when procfs is unavailable, failing closed."""

    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "lstart=", "-o", "stat="],
            check=False,
            capture_output=True,
            text=True,
            timeout=1.0,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        return None
    fields = result.stdout.split()
    if result.returncode != 0 or len(fields) != 6 or fields[5].startswith(("Z", "X", "x")):
        return None
    return "ps:" + " ".join(fields[:5])
