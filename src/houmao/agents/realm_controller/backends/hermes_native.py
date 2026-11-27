"""Discover and control the Hermes daemon launched for a managed home."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field, replace
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
import yaml

from houmao.agents.hermes_configuration import (
    HERMES_API_KEY_ENV,
    HERMES_CONFIG_FILENAME,
    hermes_owned_environment_name,
    hermes_unattended_approval_policy,
)
from houmao.agents.hermes_installation import (
    PreparedHermesInstallation,
    load_prepared_hermes_installation,
)
from houmao.agents.hermes_profile import (
    HERMES_PROFILE_PARKED,
    HermesProfileBinding,
    require_hermes_installation_context,
    require_hermes_profile_owner,
)
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
from houmao.execution.context import current_execution_deadline, execution_deadline_scope

_CANONICAL_PROTOCOL = "hermes-gateway-v1"
_TICKET_PREFIX = "hermes-gateway-ticket."
_CONTROL_TIMEOUT = 2.0
_RPC_TIMEOUT = 30.0
_MAX_CONTROL_BYTES = 512 * 1024
_MAX_FRAME_BYTES = 8 * 1024 * 1024
_STARTUP_TIMEOUT = 45.0
_STOP_TIMEOUT = 15.0
_PROFILE_WAIT_TIMEOUT = 15.0
_PARKED_MARKER = HERMES_PROFILE_PARKED
_PROFILE_CAPABILITIES = frozenset(
    {"durable-admission-v1", "event-replay-v1", "acp-editor-policy-v1", "session-client-v1"}
)


class HermesNativeError(BackendExecutionError):
    """Report an unavailable or mismatched native Hermes authority."""


class HermesApprovalCompatibilityError(HermesNativeError):
    """Report an unqualified native command-approval posture at startup."""


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
    gateway_root: Path | None = None


@dataclass(frozen=True)
class _HermesSharedHost:
    """Identify a ready owner-controlled gateway independently of a worker's epoch."""

    pid: int
    birth_token: str
    instance_id: str
    authority_epoch: int
    websocket_url: str
    serves_profile: bool


@dataclass(frozen=True)
class HermesSessionSnapshot:
    """Return a verified logical conversation in the recorded workspace."""

    session_id: str
    payload: dict[str, Any] = field(repr=False)
    daemon_instance_id: str | None = None

    @property
    def approval_pending(self) -> bool | None:
        """Read only approvals attributable to the snapshot's current execution."""

        prompts = self.payload.get("prompts")
        running = self.payload.get("running")
        if not isinstance(prompts, list) or type(running) is not bool:
            return None
        generation = self.payload.get("execution_generation")
        pending = False
        for prompt in prompts:
            if not isinstance(prompt, dict) or not isinstance(prompt.get("kind"), str):
                return None
            if prompt["kind"] != "approval":
                continue
            prompt_generation = prompt.get("execution_generation")
            prompt_id = prompt.get("prompt_id")
            if (
                type(generation) is not int
                or generation < 0
                or type(prompt_generation) is not int
                or prompt_generation < 1
                or prompt_generation > generation
                or not isinstance(prompt_id, str)
                or not prompt_id.strip()
            ):
                return None
            if prompt_generation == generation:
                if not running:
                    return None
                pending = True
        return pending

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
        self.m_profile: HermesProfileBinding | None = None
        self.m_installation: PreparedHermesInstallation | None = None
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
        profile: HermesProfileBinding | None = None,
    ) -> HermesDaemon:
        """Create owner control from an already resolved native launch."""

        daemon = cls()
        daemon.m_executable = executable
        daemon.m_home = home.resolve()
        daemon.m_workspace = workspace.resolve()
        daemon.m_env = hermes_daemon_environment(daemon.m_home, env)
        daemon.m_root = root.resolve()
        daemon.m_profile = profile
        if profile is not None and daemon.m_home != profile.profile_home:
            raise HermesNativeError("Hermes launch home differs from the recorded profile.")
        return daemon

    @classmethod
    def from_launch_plan(cls, plan: LaunchPlan, root: Path) -> HermesDaemon:
        """Create owner control from a managed launch plan."""

        if (
            plan.hermes_profile is not None
            and plan.execution_binding is not None
            and plan.hermes_profile.context_id != plan.execution_binding.context_id
        ):
            raise HermesNativeError("Hermes profile differs from the recorded execution owner.")
        return cls.from_inputs(
            executable=plan.executable,
            home=plan.home_path,
            workspace=plan.working_directory,
            env=plan.env,
            root=root,
            profile=plan.hermes_profile,
        )

    @property
    def workspace(self) -> Path:
        """Return the expected canonical workspace."""

        return self.m_workspace

    @property
    def shared(self) -> bool:
        """Report whether the recorded binding uses a prepared shared host."""

        return self.m_profile is not None

    @property
    def control_home(self) -> Path:
        """Address the exact launch root of the bound native gateway."""

        return self.m_home if self.m_profile is None else self.m_profile.prepared_root

    def _profile(self) -> HermesProfileBinding:
        """Require a recorded shared profile before any shared-host operation."""

        if self.m_profile is None:
            raise HermesNativeError("Hermes shared profile authority is unavailable.")
        return self.m_profile

    def _prepared(self) -> PreparedHermesInstallation:
        """Requalify the recorded installation before launching native code."""

        profile = self._profile()
        try:
            installation = load_prepared_hermes_installation(
                profile.executable, expected_root=profile.prepared_root
            )
            require_hermes_installation_context(installation.root, profile.context_id)
        except (OSError, ValueError) as exc:
            raise HermesNativeError(str(exc)) from exc
        if (
            installation.root != profile.prepared_root
            or installation.evidence.build != profile.installation_build
            or installation.lock_dir != profile.gateway_lock_dir
            or installation.executable != self.m_executable
        ):
            raise HermesNativeError(
                "Hermes owner installation differs from the recorded launch. "
                "Requalify the owner installation before starting the profile."
            )
        self.m_installation = installation
        return installation

    def _require_shared_home(self) -> None:
        """Refuse native control after the canonical home has changed ownership."""

        try:
            require_hermes_profile_owner(self._profile())
        except (OSError, ValueError) as exc:
            raise HermesNativeError("The named Hermes profile ownership is unavailable.") from exc

    def native_command(self, arguments: list[str]) -> tuple[list[str], dict[str, str]]:
        """Construct a native client from the verified canonical profile."""

        if not self.shared:
            return [self.m_executable, *arguments], dict(self.m_env)
        installation = self.m_installation or self._prepared()
        environment = {
            name: value
            for name, value in self.m_env.items()
            if (name == HERMES_API_KEY_ENV or not hermes_owned_environment_name(name))
            and name not in {"NODE_OPTIONS", "NODE_PATH", "GATEWAY_MULTIPLEX_PROFILES"}
        }
        environment.update(installation.native_environment(self.m_home))
        return [
            installation.executable,
            "--profile",
            self._profile().profile_name,
            *arguments,
        ], environment

    def _identify_process(self) -> tuple[dict[str, Any], int, str] | None:
        """Verify the launch home and process even while native RPC is unavailable."""

        try:
            answer, peer_pid = _control_query(self.control_home, "identify")
        except (FileNotFoundError, ConnectionRefusedError):
            return None
        daemon_home = answer.get("hermes_home")
        if (
            not isinstance(daemon_home, str)
            or not Path(daemon_home).is_absolute()
            or Path(daemon_home).resolve() != self.control_home
            or (self.shared and daemon_home != str(self.control_home))
        ):
            raise HermesNativeError("The discovered Hermes daemon has a different launch home.")
        pid = answer.get("pid")
        if (
            type(pid) is not int
            or pid <= 1
            or pid == os.getpid()
            or (peer_pid != pid if self.shared else peer_pid not in (None, pid))
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

        if self.shared:
            host = self._discover_shared_host()
            if host is None or not host.serves_profile:
                return None
            with self._shared_client(host) as native:
                return native.identity
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

    def ensure(
        self, *, unattended: bool = False, start_shared_host: bool = True
    ) -> HermesDaemonIdentity:
        """Start a vacant home or adopt its existing daemon through native discovery."""

        if self.shared:
            return self._ensure_shared(unattended=unattended, start_host=start_shared_host)
        with _lifecycle_lock(self.m_root):
            deadline = time.monotonic() + _STARTUP_TIMEOUT
            launched = False
            try:
                while time.monotonic() < deadline:
                    identity = self.discover()
                    if identity is not None:
                        if unattended:
                            self.require_unattended_approval_policy(identity)
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

    def _discover_shared_host(self) -> _HermesSharedHost | None:
        """Verify the prepared root's exact live owner and its first-stage endpoint."""

        process = self._identify_process()
        if process is None:
            return None
        answer, pid, birth = process
        if answer.get("state") in {"starting", "draining"}:
            return None
        profile = self._profile()
        capabilities = answer.get("capabilities")
        epoch, instance = answer.get("authority_epoch"), answer.get("instance_id")
        served = answer.get("served_profiles")
        if (
            answer.get("state") != "ready"
            or answer.get("code_sha") != profile.installation_build
            or answer.get("runtime_protocol") != 1
            or not isinstance(capabilities, list)
            or "session-authority-v1" not in capabilities
            or type(epoch) is not int
            or epoch <= 0
            or not isinstance(instance, str)
            or not instance
            or not isinstance(served, list)
        ):
            raise HermesNativeError("The verified Hermes root gateway is incompatible.")
        matching = [
            row
            for row in served
            if isinstance(row, dict)
            and (row.get("home") == str(self.m_home) or row.get("profile_id") == str(self.m_home))
        ]
        if matching and (
            len(matching) != 1
            or matching[0].get("home") != str(self.m_home)
            or matching[0].get("profile_id") != str(self.m_home)
        ):
            raise HermesNativeError(
                "The shared Hermes gateway reported a different managed profile."
            )
        return _HermesSharedHost(
            pid, birth, instance, epoch, _websocket_url(answer.get("api_origin")), bool(matching)
        )

    @contextmanager
    def _shared_client(self, host: _HermesSharedHost) -> Iterator[HermesClient]:
        """Resolve the selected profile and authenticate its own authority epoch."""

        self._require_shared_home()
        profile = self._profile()
        result, pid = _control_query(
            self.control_home, "resolve-profile", {"home": str(self.m_home)}
        )
        endpoint = result.get("endpoint")
        if (
            pid != host.pid
            or result.get("resolve_protocol") != 1
            or result.get("state") != "ready"
            or result.get("attachable") is not True
            or result.get("update_fenced") is not False
            or result.get("control") != "host"
            or result.get("install_code_sha") != profile.installation_build
            or not isinstance(endpoint, dict)
            or endpoint.get("control_home") != str(self.control_home)
            or endpoint.get("code_sha") != profile.installation_build
            or endpoint.get("profile_id") != str(self.m_home)
            or endpoint.get("instance_id") != host.instance_id
            or endpoint.get("authority_epoch") != host.authority_epoch
            or endpoint.get("runtime_protocol") != 1
            or endpoint.get("ws_protocol") != _CANONICAL_PROTOCOL
            or endpoint.get("ticket_protocol_prefix") != _TICKET_PREFIX
            or endpoint.get("ws_url") != host.websocket_url
        ):
            raise HermesNativeError("Hermes did not confirm the exact shared profile endpoint.")
        identity = HermesDaemonIdentity(
            home=self.m_home,
            pid=host.pid,
            birth_token=host.birth_token,
            instance_id=host.instance_id,
            authority_epoch=0,
            profile_id=str(self.m_home),
            websocket_url=host.websocket_url,
            gateway_root=self.control_home,
        )
        with self._connect_identity(identity) as native:
            yield native

    def _host_lifecycle_root(self) -> Path:
        """Select a private lock directory shared by every worker for this installation."""

        return self.control_home / ".houmao-host"

    def ensure_shared_host(self) -> None:
        """Acquire the context-owned host outside a per-agent service subreaper."""

        installation = self._prepared()
        with _lifecycle_lock(self._host_lifecycle_root(), private=True):
            self._require_shared_home()
            host = self._ensure_shared_host(installation)
            self._ensure_tool_origin(host)

    def _ensure_shared_host(self, installation: PreparedHermesInstallation) -> _HermesSharedHost:
        """Acquire the shared host once while preserving other workers' ownership."""

        deadline = time.monotonic() + _native_timeout(_STARTUP_TIMEOUT)
        log_path = self._host_lifecycle_root() / "hermes-daemon.log"
        child: subprocess.Popen[bytes] | None = None
        child_birth: str | None = None
        try:
            while time.monotonic() < deadline:
                host = self._discover_shared_host()
                if host is not None:
                    if child is not None and child.pid != host.pid:
                        _stop_failed_shared_host(child, child_birth)
                    return host
                if child is not None and child.poll() is not None:
                    raise HermesNativeError(
                        f"Hermes shared gateway exited with status {child.returncode}. "
                        f"See private diagnostics in {log_path}."
                    )
                if child is None and not _runtime_lock_held(self.control_home):
                    descriptor = os.open(
                        log_path, os.O_APPEND | os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600
                    )
                    environment = owner_launch_baseline(os.environ)
                    environment.update(installation.native_environment(self.control_home))
                    environment["GATEWAY_MULTIPLEX_PROFILES"] = "1"
                    with os.fdopen(descriptor, "ab") as log:
                        child = subprocess.Popen(
                            [
                                installation.executable,
                                "gateway",
                                "run",
                                "--external-supervisor",
                                "--no-supervise",
                            ],
                            cwd=self.control_home,
                            env=environment,
                            stdin=subprocess.DEVNULL,
                            stdout=log,
                            stderr=log,
                            start_new_session=True,
                        )
                        child_birth = _dispatch_origin_birth_token(child.pid)
                time.sleep(0.05)
            raise HermesNativeError(
                f"Hermes shared gateway did not become ready. See private diagnostics in "
                f"{log_path}."
            )
        except BaseException:
            if child is not None:
                _stop_failed_shared_host(child, child_birth)
            raise

    def _ensure_tool_origin(self, host: _HermesSharedHost) -> None:
        """Ensure only the verified owner gateway can obtain managed tool proofs."""

        from houmao.agents.realm_controller.hermes_tool_origin import (
            ensure_hermes_tool_origin_broker,
        )

        profile = self._profile()
        origin = ensure_hermes_tool_origin_broker(
            self.control_home,
            profile.context_id,
            daemon_pid=host.pid,
            daemon_birth_token=host.birth_token,
        )
        if origin != profile.broker_socket:
            raise HermesNativeError("Hermes shared tool origin authority is inconsistent.")

    def _ensure_shared(self, *, unattended: bool, start_host: bool) -> HermesDaemonIdentity:
        """Serve only the recorded profile and prove its effective native readiness."""

        # Verify installation currency before acquiring or modifying a profile.
        installation = self._prepared()
        with _lifecycle_lock(self._host_lifecycle_root(), private=True):
            self._require_shared_home()
            host = (
                self._ensure_shared_host(installation)
                if start_host
                else self._discover_shared_host()
            )
            if host is None:
                raise HermesNativeError("The owner-managed Hermes shared gateway is unavailable.")
            if start_host:
                self._ensure_tool_origin(host)
            parked = self.m_home / _PARKED_MARKER
            acquired = os.path.lexists(parked)
            if acquired:
                _private_node(parked, stat.S_ISREG)
                if host.serves_profile or _runtime_lock_held(self.m_home):
                    raise HermesNativeError("The parked Hermes profile still has a native owner.")
                parked.unlink()
            try:
                if not host.serves_profile:
                    self._profile_verb(host, "serve-profile")
                identity = self._wait_for_profile(host)
                self._verify_shared_readiness(identity, unattended=unattended)
                self._record(identity)
            except BaseException:
                if acquired:
                    try:
                        self._park_shared_locked(expected=None)
                    except (BackendExecutionError, OSError) as cleanup_failure:
                        raise HermesNativeError(
                            "Hermes profile startup failed and reservation release remains "
                            "unconfirmed. Inspect the managed profile and its private diagnostics."
                        ) from cleanup_failure
                raise
            startup = current_runtime_startup()
            if acquired and startup is not None:
                startup.add("new managed Hermes profile", lambda: self.stop(expected=identity))
            return identity

    def _profile_verb(self, host: _HermesSharedHost, verb: str) -> None:
        """Send a bounded physical profile operation to the exact verified root peer."""

        _, pid = _control_query(
            self.control_home, verb, {"name": self._profile().profile_name}, wait=8.0
        )
        if pid != host.pid or _dispatch_origin_birth_token(host.pid) != host.birth_token:
            raise HermesNativeError("The shared Hermes gateway changed during profile control.")

    def _wait_for_profile(self, host: _HermesSharedHost) -> HermesDaemonIdentity:
        """Confirm the scoped route after a native acknowledgement or pending result."""

        deadline = time.monotonic() + _native_timeout(_PROFILE_WAIT_TIMEOUT)
        with execution_deadline_scope(deadline):
            while time.monotonic() < deadline:
                current = self._discover_shared_host()
                if current is None or (current.pid, current.birth_token, current.instance_id) != (
                    host.pid,
                    host.birth_token,
                    host.instance_id,
                ):
                    raise HermesNativeError(
                        "The shared Hermes gateway changed during profile startup."
                    )
                if current.serves_profile:
                    with self._shared_client(current) as native:
                        return native.identity
                time.sleep(0.05)
        raise HermesNativeError("Hermes did not publish the selected named profile.")

    def _verify_shared_readiness(self, identity: HermesDaemonIdentity, *, unattended: bool) -> None:
        """Check stock tool-origin support and profile-local approvals before managed admission."""

        from houmao.agents.realm_controller.hermes_tool_origin import (
            require_hermes_tool_origin_hook,
        )

        try:
            require_hermes_tool_origin_hook(
                self.m_home, broker_socket=self._profile().broker_socket
            )
            with self.client() as native:
                if native.identity != identity:
                    raise HermesNativeError("The shared Hermes profile authority changed.")
                plugins = native.rpc("plugins.list").get("plugins")
                origin = (
                    [
                        plugin
                        for plugin in plugins
                        if isinstance(plugin, dict) and plugin.get("key") == "houmao-tool-origin"
                    ]
                    if isinstance(plugins, list)
                    else []
                )
                if (
                    len(origin) != 1
                    or origin[0].get("enabled") is not True
                    or origin[0].get("version") != "1.0.0"
                    or origin[0].get("error") != ""
                ):
                    raise HermesNativeError(
                        "Hermes did not load the required managed tool-origin hook."
                    )
                expected = (
                    hermes_unattended_approval_policy()
                    if unattended
                    else self._authored_profile_approvals()
                )
                self._require_approvals(native, expected)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            raise HermesNativeError(
                "The shared Hermes profile configuration is unavailable."
            ) from exc

    def _authored_profile_approvals(self) -> dict[str, str | bool]:
        """Read only launch-owned approval values from the canonical private profile."""

        path = self.m_home / HERMES_CONFIG_FILENAME
        _private_node(path, stat.S_ISREG)
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        values = config.get("approvals") if isinstance(config, dict) else None
        expected: dict[str, str | bool] = {}
        for key in hermes_unattended_approval_policy():
            value = values.get(key) if isinstance(values, dict) else None
            if not isinstance(value, (str, bool)):
                raise HermesApprovalCompatibilityError(
                    "Hermes profile approval settings are missing."
                )
            expected[key] = value
        return expected

    def require_unattended_approval_policy(self, identity: HermesDaemonIdentity) -> None:
        """Confirm the authenticated launch home's effective command approval keys."""

        error = "Hermes did not confirm its native unattended command approval policy."
        try:
            with self.client() as native:
                if native.identity != identity:
                    raise HermesApprovalCompatibilityError(error)
                self._require_approvals(native, hermes_unattended_approval_policy())
        except (HermesNativeError, OSError, ValueError) as exc:
            raise HermesApprovalCompatibilityError(error) from exc

    @staticmethod
    def _require_approvals(native: HermesClient, expected: Mapping[str, str | bool]) -> None:
        """Read back effective approval fields against the selected native profile."""

        mode = native.rpc("config.get", key="approvals.mode")
        settings = native.rpc("config.get", key="full").get("config")
        approvals = settings.get("approvals") if isinstance(settings, dict) else None
        configured_mode = expected["mode"]
        if isinstance(configured_mode, bool):
            configured_mode = "manual" if configured_mode else "off"
        if (
            mode.get("value") != configured_mode
            or not isinstance(approvals, dict)
            or any(approvals.get(key) != value for key, value in expected.items())
        ):
            raise HermesApprovalCompatibilityError(
                "Hermes did not confirm the selected native command approval policy."
            )

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
                **(
                    {"gateway_root": str(identity.gateway_root), "profile_id": identity.profile_id}
                    if identity.gateway_root is not None
                    else {}
                ),
            },
        )

    @contextmanager
    def client(self) -> Iterator[HermesClient]:
        """Mint a single-use native ticket and verify the connected authority."""

        if self.shared:
            host = self._discover_shared_host()
            if host is None or not host.serves_profile:
                raise HermesNativeError("The managed Hermes profile is unavailable.")
            with self._shared_client(host) as native:
                yield native
            return
        identity = self.discover()
        if identity is None:
            raise HermesNativeError("The daemon in the managed Hermes home is unavailable.")
        with self._connect_identity(identity) as native:
            self._record(identity)
            yield native

    @contextmanager
    def _connect_identity(self, identity: HermesDaemonIdentity) -> Iterator[HermesClient]:
        """Authenticate the exact root/provisional profile and obtain its native epoch."""

        try:
            ticket, peer_pid = _control_query(
                self.control_home,
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
                or (
                    peer_pid != identity.pid
                    if self.shared
                    else peer_pid not in (None, identity.pid)
                )
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
                epoch = description.get("authority_epoch")
                if (
                    description.get("instance_id") != identity.instance_id
                    or description.get("profile_id") != identity.profile_id
                    or type(epoch) is not int
                    or epoch <= 0
                    or (not self.shared and epoch != identity.authority_epoch)
                    or (
                        self.shared
                        and _dispatch_origin_birth_token(identity.pid) != identity.birth_token
                    )
                ):
                    raise HermesNativeError("Hermes reported a different native authority.")
                if self.shared:
                    capabilities = description.get("capabilities")
                    if (
                        not isinstance(capabilities, list)
                        or not all(isinstance(value, str) for value in capabilities)
                        or not _PROFILE_CAPABILITIES.issubset(capabilities)
                    ):
                        raise HermesNativeError(
                            "The Hermes profile lacks required native controls."
                        )
                    native.m_identity = replace(identity, authority_epoch=epoch)
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

    def verify_shared_session(self, session_id: str) -> HermesDaemonIdentity:
        """Read authenticated exact-session evidence without serving or mounting a profile."""

        self._profile()
        with self.client() as native:
            info = native.rpc("session.info", session_id=session_id)
            if (
                info.get("profile_id") != native.identity.profile_id
                or info.get("profile_name") != self._profile().profile_name
                or info.get("cwd") != str(self.m_workspace)
                or info.get("session_id", session_id) != session_id
            ):
                raise HermesNativeError("Hermes did not verify the exact managed profile session.")
            return native.identity

    def recover_shared(self, session_id: str | None, *, unattended: bool) -> HermesDaemonIdentity:
        """Rebind a previously live profile and exact conversation without replay."""

        self._prepared()
        if os.path.lexists(self.m_home / _PARKED_MARKER):
            raise HermesNativeError("The selected Hermes profile is parked.")
        record = read_hermes_evidence(self.m_root / "hermes-daemon.json")
        if (
            record is None
            or record.get("gateway_root") != str(self.control_home)
            or record.get("home") != str(self.m_home)
            or record.get("profile_id") != str(self.m_home)
        ):
            raise HermesNativeError("The prior Hermes profile authority is unavailable.")
        identity = self.discover()
        if identity is not None and (
            record.get("instance_id"),
            record.get("authority_epoch"),
            record.get("pid"),
            record.get("birth_token"),
        ) == (identity.instance_id, identity.authority_epoch, identity.pid, identity.birth_token):
            return identity
        if identity is None:
            self.ensure_shared_host()
            identity = self.discover()
            if identity is None:
                raise HermesNativeError("Hermes did not recover the recorded profile.")
        self._verify_shared_readiness(identity, unattended=unattended)
        if session_id is not None:
            snapshot = self.resolve_session(session_id)
            if snapshot.daemon_instance_id != identity.instance_id or self.discover() != identity:
                raise HermesNativeError("Hermes changed while recovering the exact conversation.")
        self._record(identity)
        return identity

    def require_recorded_authority(self, identity: HermesDaemonIdentity) -> None:
        """Reject a changed profile epoch until verified recovery records it."""

        record = read_hermes_evidence(self.m_root / "hermes-daemon.json")
        expected = {
            "home": str(identity.home),
            "workspace": str(self.m_workspace),
            "gateway_root": str(identity.gateway_root),
            "profile_id": identity.profile_id,
            "pid": identity.pid,
            "birth_token": identity.birth_token,
            "instance_id": identity.instance_id,
            "authority_epoch": identity.authority_epoch,
        }
        if record is None or any(record.get(key) != value for key, value in expected.items()):
            raise HermesNativeError("The selected Hermes profile requires verified recovery.")

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

    def stop(self, *, expected: HermesDaemonIdentity | None = None) -> None:
        """Stop the exact same-home daemon and wait for that process to exit."""

        if self.shared:
            with _lifecycle_lock(self._host_lifecycle_root(), private=True):
                self._park_shared_locked(expected=expected)
            return
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

    def require_released(self) -> None:
        """Verify that native profile routing and its reservation have settled independently."""

        self._profile()
        with _lifecycle_lock(self._host_lifecycle_root(), private=True):
            self.verify_profile_released()

    def verify_profile_released(self, *, require_parked: bool = True) -> None:
        """Verify a quiescent parked profile inside its owner lifecycle transaction."""

        self._profile()
        host = self._discover_shared_host()
        if (host is not None and host.serves_profile) or _runtime_lock_held(self.m_home):
            raise HermesNativeError("The Hermes profile has not released its native reservation.")
        if require_parked and self.m_home.exists():
            _private_node(self.m_home / _PARKED_MARKER, stat.S_ISREG)

    def _park_shared_locked(self, *, expected: HermesDaemonIdentity | None) -> None:
        """Fence one profile's ingress and await release without touching the host."""

        if not os.path.lexists(self.m_home):
            host = self._discover_shared_host()
            if host is not None and host.serves_profile:
                raise HermesNativeError("The missing Hermes profile still has a native route.")
            return
        self._require_shared_home()
        host = self._discover_shared_host()
        if expected is not None and host is not None and host.serves_profile:
            with self._shared_client(host) as native:
                if native.identity != expected:
                    raise HermesNativeError("The selected Hermes profile authority has changed.")
        marker = self.m_home / _PARKED_MARKER
        try:
            descriptor = os.open(
                marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600
            )
        except FileExistsError:
            _private_node(marker, stat.S_ISREG)
        else:
            os.close(descriptor)
        deadline = time.monotonic() + _native_timeout(_PROFILE_WAIT_TIMEOUT)
        with execution_deadline_scope(deadline):
            if host is not None and host.serves_profile:
                self._profile_verb(host, "unserve-profile")
            while time.monotonic() < deadline:
                current = self._discover_shared_host()
                if (current is None or not current.serves_profile) and not _runtime_lock_held(
                    self.m_home
                ):
                    return
                time.sleep(0.05)
        raise HermesNativeError("Hermes parked the profile but native release remains unconfirmed.")


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
    home: Path, verb: str, params: dict[str, Any] | None = None, *, wait: float = _CONTROL_TIMEOUT
) -> tuple[dict[str, Any], int | None]:
    """Use the same-user Unix control socket for one bounded native bootstrap request."""

    request = {"protocol": 1, "id": 1, "verb": verb, "params": params or {}}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
            timeout = _native_timeout(wait)
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
def _lifecycle_lock(root: Path, *, private: bool = False) -> Iterator[None]:
    """Serialize startup and stop for the recorded managed runtime."""

    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if private:
        _private_node(root, stat.S_ISDIR)
    descriptor = os.open(
        root / "hermes-lifecycle.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "rb+") as stream:
        if current_execution_deadline() is None:
            fcntl.flock(stream, fcntl.LOCK_EX)
        else:
            while True:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    time.sleep(_native_timeout(0.05))
        yield


@contextmanager
def hermes_profile_lifecycle_lock(root: Path) -> Iterator[None]:
    """Serialize owner profile publication, activation, and settlement."""

    with _lifecycle_lock(root / ".houmao-host", private=True):
        yield


def _stop_failed_shared_host(process: subprocess.Popen[bytes], birth: str | None) -> None:
    """Reap the exact unqualified child and descendants from this host acquisition."""

    if birth is None:
        stop_owned_startup_child(process)
        return
    from houmao.agents.realm_controller.backends.dsh_web_supervisor import _signal_owned

    descendants: dict[int, str] = {}
    _signal_owned(process.pid, birth, signal.SIGTERM, descendants)
    with suppress(subprocess.TimeoutExpired):
        process.wait(timeout=2)
    _signal_owned(process.pid, birth, signal.SIGKILL, descendants)
    process.wait(timeout=2)


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
