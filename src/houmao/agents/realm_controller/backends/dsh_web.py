"""Supervise an owned local DSH Web Host and control its exact native conversation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, fields
from importlib.resources import files
import json
import math
import os
from pathlib import Path
import shlex
import signal
import stat
import subprocess
import sys
import threading
import time
from typing import Any, cast
from urllib.parse import urlsplit
from uuid import uuid4

from houmao.agents.dsh_configuration import DshEffectiveToolParams, prepare_dsh_home
from houmao.agents.launch_policy import LaunchPolicyError, validate_packaged_tool_version
from houmao.agents.model_mapping_policy import resolve_reasoning_mapping
from houmao.agents.model_selection import ModelConfig
from houmao.agents.realm_controller.backends.dispatch_control import (
    HeadlessDispatchControl,
    _dispatch_origin_birth_token,
)
from houmao.agents.realm_controller.backends.dsh_acp_driver import _write_private_json
from houmao.agents.realm_controller.backends.dsh_diagnostics import (
    dsh_diagnostic_secrets,
    dsh_diagnostic_tail,
    sanitize_dsh_diagnostic,
)
from houmao.agents.realm_controller.backends.dsh_web_client import DshWebClient, DshWebError
from houmao.agents.realm_controller.backends.dsh_web_supervisor import (
    _signal_owned,
    web_tool_environment,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    create_tmux_session,
    generate_tmux_session_name,
    has_tmux_session,
    kill_tmux_session,
    prepare_headless_agent_window,
    run_tmux,
)
from houmao.agents.realm_controller.backends.web_entry import NativeWebEntry, owns_ipv4_web_listener
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.models import (
    HeadlessTurnSessionSelection,
    LaunchPlan,
    RelaunchChatSessionSelection,
    SessionControlResult,
    SessionEvent,
)
from houmao.agents.realm_controller.native_surface import WebNativeSurfaceV1
from houmao.agents.realm_controller.usage_support import UsageService, write_usage_json
from houmao.agents.tool_params.dsh import DshPermissionParams

_STARTUP_TIMEOUT_SECONDS = 45.0
_SUPERVISOR_STOP_TIMEOUT_SECONDS = 25.0


def _startup_failure_detail(root: Path, secret_values: tuple[str, ...]) -> str:
    """Read the supervisor's exit reason and native log without exposing credentials."""

    try:
        recorded = json.loads(dsh_diagnostic_tail(root / "exit.json"))
    except ValueError:
        recorded = None
    try:
        boot = json.loads(dsh_diagnostic_tail(root / "bootstrap.json"))
    except ValueError:
        boot = None
    if isinstance(boot, dict) and isinstance(boot.get("launch_token"), str):
        secret_values = (*secret_values, boot["launch_token"])

    reason = recorded.get("error") if isinstance(recorded, dict) else None
    returncode = recorded.get("returncode") if isinstance(recorded, dict) else None
    diagnostic = "\n".join(
        filter(
            None,
            (
                reason if isinstance(reason, str) else "",
                dsh_diagnostic_tail(root / "native-private.log"),
            ),
        )
    )
    summary = sanitize_dsh_diagnostic(diagnostic, secret_values=secret_values)
    status = f" (native exit {returncode})" if type(returncode) is int else ""
    detail = summary or "verified native bootstrap is unavailable"
    return f"DSH Web startup failed{status}: {detail}"


@dataclass
class DshWebSessionState:
    """Persist public execution identity separately from private credential references."""

    origin: str
    web_identity: dict[str, Any]
    bootstrap_path: str
    cookie_path: str
    control_path: str
    supervisor_pid: int
    supervisor_birth_token: str
    tmux_session_name: str
    evidence_path: str
    working_directory: str
    turn_index: int = 0
    role_name: str = ""
    tmux_window_id: str | None = None
    tmux_pane_id: str | None = None
    native_pid: int | None = None
    native_birth_token: str | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> DshWebSessionState:
        """Validate an existing owned binding without activating any native session."""

        names = {entry.name for entry in fields(cls)}
        state = cls(**{key: value for key, value in payload.items() if key in names})
        state.native_surface
        if (
            state.web_identity.get("protocol_version") != 1
            or any(
                not isinstance(state.web_identity.get(key), str) or not state.web_identity[key]
                for key in (
                    "agent_id",
                    "runtime_session_id",
                    "generation",
                    "host_incarnation",
                    "native_session_id",
                    "agent_incarnation",
                )
            )
            or type(state.supervisor_pid) is not int
            or state.supervisor_pid <= 0
            or not isinstance(state.supervisor_birth_token, str)
            or not state.supervisor_birth_token
            or type(state.native_pid) is not int
            or state.native_pid <= 0
            or not isinstance(state.native_birth_token, str)
            or not state.native_birth_token
        ):
            raise BackendExecutionError("DSH Web persisted ownership is incomplete")
        for value in (
            state.bootstrap_path,
            state.cookie_path,
            state.control_path,
            state.evidence_path,
        ):
            if not Path(value).is_absolute():
                raise BackendExecutionError("DSH Web private authority paths must be absolute")
        return state

    def to_payload(self) -> dict[str, Any]:
        """Return JSON-safe ownership metadata containing references rather than credentials."""

        return {**asdict(self), "browser_url": self.browser_url}

    @property
    def browser_url(self) -> str:
        """Return the clean origin; native browser session selection remains explicit."""

        return self.origin

    @property
    def native_surface(self) -> WebNativeSurfaceV1:
        """Return the verified browser surface independently of its supervisor pane."""

        return WebNativeSurfaceV1(
            origin=self.origin, native_session_id=self.web_identity["native_session_id"]
        )


class DshWebSession:
    """Manage one owned resident Web Host without adopting another local process."""

    backend = "dsh_web"

    def __init__(self) -> None:
        """Initialize inactive control; use ``from_launch_plan`` to bind ownership."""

        self.m_plan: LaunchPlan | None = None
        self.m_manifest_path: Path | None = None
        self.m_state: DshWebSessionState | None = None
        self.m_client: DshWebClient | None = None
        self.m_dispatch_control: HeadlessDispatchControl | None = None
        self.m_binding_changed: Callable[[], None] | None = None
        self.m_active_operations: dict[int, str] = {}
        self.m_abandoning_operations: set[str] = set()
        self.m_operation_lock: threading.RLock = threading.RLock()
        self.m_usage_service: UsageService | None = None
        self.m_force_cleanup: bool = False

    @classmethod
    def from_launch_plan(
        cls,
        *,
        launch_plan: LaunchPlan,
        session_manifest_path: Path,
        role_name: str,
        state: DshWebSessionState | None = None,
        agent_def_dir: Path | None = None,
        tmux_session_name: str | None = None,
        provider_start: bool = False,
    ) -> DshWebSession:
        """Start only at an explicit lifecycle boundary, otherwise reconstruct control."""

        del agent_def_dir
        instance = cls()
        instance.m_plan = launch_plan
        instance.m_manifest_path = session_manifest_path.resolve()
        instance.m_state = state
        if provider_start:
            instance._start_owned_host(role_name=role_name, tmux_session_name=tmux_session_name)
        elif state is None:
            raise BackendExecutionError(
                "DSH Web reconstruction requires an owned persisted binding"
            )
        elif Path(state.working_directory).resolve() != launch_plan.working_directory.resolve():
            raise BackendExecutionError("DSH Web continuation requires its recorded workspace")
        return instance

    @property
    def state(self) -> DshWebSessionState:
        """Return the owned native and supervisor binding."""

        if self.m_state is None:
            raise BackendExecutionError("DSH Web has no verified owned binding")
        return self.m_state

    @property
    def plan(self) -> LaunchPlan:
        """Return the explicit managed launch configuration."""

        if self.m_plan is None:
            raise BackendExecutionError("DSH Web launch configuration is unavailable")
        return self.m_plan

    def set_binding_changed_callback(self, callback: Callable[[], None]) -> None:
        """Publish intentional native binding changes before admitting new input."""

        self.m_binding_changed = callback

    def configure_request_dispatch(self, control: HeadlessDispatchControl | None) -> None:
        """Bind immediate dispatch to its captured generation and caller lifetime."""

        self.m_dispatch_control = control

    def configure_stop_force_cleanup(self, *, force_cleanup: bool) -> None:
        """Choose whether explicit stop also removes the owned supervisor session."""

        self.m_force_cleanup = force_cleanup

    def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
        """Refresh managed bindings while preserving the owned home and workspace."""

        if (
            launch_plan.backend != self.backend
            or launch_plan.home_path.resolve() != self.plan.home_path.resolve()
            or launch_plan.working_directory.resolve() != self.plan.working_directory.resolve()
        ):
            raise BackendExecutionError(
                "DSH Web bindings require the same owned home and workspace"
            )
        self.m_plan = launch_plan

    def relaunch(
        self, *, chat_session: RelaunchChatSessionSelection | None = None
    ) -> SessionControlResult:
        """Explicitly replace the owned host with a new or exactly restored conversation."""

        selected = chat_session or RelaunchChatSessionSelection(mode="new")
        if selected.mode not in {"new", "exact"} or (
            selected.mode == "exact"
            and selected.session_id != self.state.web_identity["native_session_id"]
        ):
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail="DSH Web relaunch requires new or its exact recorded native session",
            )
        previous = self.state
        force_cleanup, self.m_force_cleanup = self.m_force_cleanup, False
        try:
            stopped = self.terminate()
            if stopped.status != "ok":
                return SessionControlResult(
                    status="error", action="relaunch", detail=stopped.detail
                )
            self._start_owned_host(
                role_name=previous.role_name,
                tmux_session_name=previous.tmux_session_name,
                new_session=selected.mode == "new",
            )
            return SessionControlResult(
                status="ok", action="relaunch", detail="Relaunched the owned native Web Host"
            )
        except (OSError, ValueError, BackendExecutionError) as exc:
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail=f"DSH Web relaunch failed: {self._diagnostic_detail(exc)}",
            )
        finally:
            self.m_force_cleanup = force_cleanup

    def _managed_identity(self) -> dict[str, str]:
        """Read launch-owned identity without deriving logical identity from a URL."""

        selected = self.plan.metadata.get("managed_web_identity")
        if not isinstance(selected, dict) and self.m_manifest_path is not None:
            manifest = json.loads(self.m_manifest_path.read_text(encoding="utf-8"))
            selected = {
                "agent_id": manifest.get("agent_id"),
                "runtime_session_id": manifest.get("runtime", {}).get("session_id"),
                "generation": manifest.get("registry_generation_id"),
            }
        if not isinstance(selected, dict) or any(
            not isinstance(selected.get(name), str) or not selected[name]
            for name in ("agent_id", "runtime_session_id", "generation")
        ):
            raise BackendExecutionError("DSH Web requires explicit managed execution identity")
        return {
            name: str(selected[name]) for name in ("agent_id", "runtime_session_id", "generation")
        }

    def _start_owned_host(
        self, *, role_name: str, tmux_session_name: str | None, new_session: bool = False
    ) -> None:
        """Prepare isolated native inputs and publish authority only after authenticated binding."""

        identity = self._managed_identity()
        existing = self.m_state
        if existing is not None and (
            _dispatch_origin_birth_token(existing.supervisor_pid) == existing.supervisor_birth_token
            or (
                existing.native_pid is not None
                and existing.native_birth_token is not None
                and _dispatch_origin_birth_token(existing.native_pid) == existing.native_birth_token
            )
        ):
            raise BackendExecutionError(
                "Explicit DSH Web relaunch requires stopping its owned host first"
            )
        setup_metadata = self.plan.metadata.get("dsh")
        if not isinstance(setup_metadata, dict) or not isinstance(
            setup_metadata.get("setup_path"), str
        ):
            raise BackendExecutionError("DSH Web requires an explicitly prepared tool setup")
        setup = DshEffectiveToolParams.from_file(Path(setup_metadata["setup_path"]))
        permissions = setup_metadata.get("permissions")
        prepared = prepare_dsh_home(
            self.plan.home_path,
            setup,
            {
                **{
                    name: os.environ[name]
                    for name in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SHELL", "TERM")
                    if name in os.environ
                },
                **self.plan.env,
            },
            self.plan.role_injection.prompt,
            selected_model=setup_metadata.get("model"),
            reasoning_level=setup_metadata.get("reasoning_level"),
            skill_roots=(self.plan.home_path / "skills",),
            operator_prompt_mode=setup_metadata.get("operator_prompt_mode", "unattended"),
            permissions=(
                DshPermissionParams.model_validate(permissions) if permissions is not None else None
            ),
        )
        secret_values = dsh_diagnostic_secrets(prepared.environment, key_name=setup.api_key_env)
        try:
            version = subprocess.run(
                [self.plan.executable, "--version"],
                env=prepared.environment,
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            ).stdout.strip()
        except subprocess.CalledProcessError as exc:
            diagnostic = sanitize_dsh_diagnostic(exc.stderr or "", secret_values=secret_values)
            suffix = f": {diagnostic}" if diagnostic else ""
            raise BackendExecutionError(
                f"DSH Web version probe exited with status {exc.returncode}{suffix}"
            ) from None
        except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
            raise BackendExecutionError(
                f"DSH Web version probe failed: {type(exc).__name__}"
            ) from None
        try:
            validate_packaged_tool_version(tool="dsh", backend="dsh_web", version=version)
        except LaunchPolicyError as exc:
            raise BackendExecutionError(
                sanitize_dsh_diagnostic(str(exc), secret_values=secret_values)
            ) from None
        root = self.plan.home_path / "houmao-web" / uuid4().hex
        root.mkdir(parents=True, mode=0o700)
        bootstrap = root / "bootstrap.json"
        control = root / "control.json"
        receipt_state = self.plan.home_path / "houmao-web-receipts.json"
        evidence = root / "native-evidence.jsonl"
        _write_private_json(
            control,
            {
                "version": 1,
                "mode": "web",
                **identity,
                "working_directory": str(self.plan.working_directory.resolve()),
                "expected_native_session_id": existing.web_identity["native_session_id"]
                if existing and not new_session
                else None,
                "state_path": str(receipt_state),
                "evidence_path": str(evidence),
                "bootstrap_path": str(bootstrap),
                "roleFile": str(prepared.role_path),
                "provider": prepared.provider,
                "model": prepared.model,
                "native_version": version,
                "permission_preset": prepared.metadata["permission_preset"],
            },
        )
        patch = [
            entry
            for entry in json.loads(prepared.patch_path.read_text())
            if entry.get("id") != "acp"
        ]
        patch.extend(
            [
                {
                    "id": "agent-default-model",
                    "config": {"provider": prepared.provider, "model": prepared.model},
                },
                {"id": "session-title-llm", "disabled": True},
                {
                    "insert": [
                        {
                            "id": "houmao-managed-web",
                            "name": str(
                                files("houmao.agents").joinpath("assets/dsh/managed-web.mjs")
                            ),
                            "config": {"controlFile": str(control)},
                        }
                    ]
                },
            ]
        )
        patch_path = root / "profile.patch.json"
        descriptor = os.open(patch_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(patch, stream)
        name = tmux_session_name or (
            existing.tmux_session_name
            if existing
            else generate_tmux_session_name(tool="dsh", role_name=role_name)
        )
        invocation = root / "supervisor-input.json"
        _write_private_json(
            invocation,
            {
                "root": str(root),
                "working_directory": str(self.plan.working_directory),
                "environment": web_tool_environment(prepared.environment, session_name=name),
                "command": [
                    self.plan.executable,
                    "--profile",
                    "web",
                    "--patch",
                    str(patch_path),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "0",
                    "--no-open",
                ],
            },
        )
        created = has_tmux_session(session_name=name).returncode == 1
        if not created and (existing is None or existing.tmux_session_name != name):
            raise BackendExecutionError("DSH Web refuses to adopt an existing supervisor session")
        if not created:
            ownership = run_tmux(["show-options", "-v", "-t", name, "@houmao_dsh_web_owner"])
            if (
                ownership.returncode != 0
                or existing is None
                or ownership.stdout.strip() != existing.control_path
            ):
                raise BackendExecutionError("DSH Web supervisor ownership has changed")
        try:
            if created:
                create_tmux_session(
                    session_name=name, working_directory=self.plan.working_directory
                )
                ownership = run_tmux(
                    ["set-option", "-t", name, "@houmao_dsh_web_owner", str(control)]
                )
                if ownership.returncode != 0:
                    raise BackendExecutionError(
                        "DSH Web supervisor ownership could not be recorded"
                    )
            surface = prepare_headless_agent_window(session_name=name, fresh_session=created)
            command = shlex.join(
                [
                    sys.executable,
                    "-m",
                    "houmao.agents.realm_controller.backends.dsh_web_supervisor",
                    "--input",
                    str(invocation),
                ]
            )
            result = run_tmux(["respawn-pane", "-k", "-t", surface.pane_id, command])
            if result.returncode != 0:
                raise BackendExecutionError("DSH Web supervisor could not start")
            deadline = time.monotonic() + _STARTUP_TIMEOUT_SECONDS
            while not bootstrap.is_file() or not (root / "supervisor.json").is_file():
                if (root / "exit.json").exists() or time.monotonic() >= deadline:
                    raise BackendExecutionError(_startup_failure_detail(root, secret_values))
                time.sleep(0.05)
            boot = json.loads(bootstrap.read_text())
            process = json.loads((root / "supervisor.json").read_text())
            self.m_client = DshWebClient.from_connection(
                boot["origin"],
                launch_token=boot["launch_token"],
                cookie_file=root / "api-credential.json",
                secret_values=secret_values,
            )
            native_identity = self.m_client.lifecycle_start(
                mode="exact" if existing and not new_session else "new",
                session_id=existing.web_identity["native_session_id"]
                if existing and not new_session
                else None,
                abandoned_operation_ids=self._abandoned_operations(receipt_state, existing)
                if not new_session
                else (),
            )
            if any(native_identity.get(key) != value for key, value in identity.items()):
                raise BackendExecutionError(
                    "DSH Web native identity does not match its launch owner"
                )
            self.m_state = DshWebSessionState(
                origin=boot["origin"],
                web_identity=native_identity,
                bootstrap_path=str(bootstrap),
                cookie_path=str(root / "api-credential.json"),
                control_path=str(control),
                supervisor_pid=process["supervisor_pid"],
                supervisor_birth_token=process["supervisor_birth_token"],
                tmux_session_name=name,
                evidence_path=str(evidence),
                working_directory=str(self.plan.working_directory.resolve()),
                turn_index=existing.turn_index if existing else 0,
                role_name=role_name,
                tmux_window_id=surface.window_id,
                tmux_pane_id=surface.pane_id,
                native_pid=process["native_pid"],
                native_birth_token=process["native_birth_token"],
            )
            self.state.native_surface
            self._bind_managed_accounting(new_session=existing is None or new_session)
            ownership = run_tmux(["set-option", "-t", name, "@houmao_dsh_web_owner", str(control)])
            if ownership.returncode != 0:
                raise BackendExecutionError("DSH Web supervisor ownership could not be recorded")
            write_usage_json(root / "owned-state.json", self.state.to_payload())
        except BaseException as exc:
            self.close_control_connection()
            self._stop_supervisor_file(root / "supervisor.json")
            if created and self._owns_supervisor_session(name, str(control)):
                kill_tmux_session(session_name=name)
            if isinstance(exc, DshWebError):
                raise BackendExecutionError(f"DSH Web startup failed: {exc}") from None
            raise

    def _abandoned_operations(
        self, receipt_state: Path, previous: DshWebSessionState | None
    ) -> tuple[str, ...]:
        """Select only proven failed ordinary operations during explicit continuation."""

        if previous is None or not receipt_state.is_file():
            return ()
        data = json.loads(receipt_state.read_text())
        receipts = data.get("receipts", [])
        if isinstance(receipts, dict):
            receipts = list(receipts.values())
        return tuple(
            str(receipt["operation_id"])
            for receipt in receipts
            if isinstance(receipt, dict)
            and receipt.get("operator") is False
            and receipt.get("status") not in {"terminal", "abandoned"}
            and receipt.get("identity", {}).get("native_session_id")
            == previous.web_identity["native_session_id"]
        )

    def _diagnostic_secrets(self) -> tuple[str, ...]:
        """Select only credential values from the current private launch plan."""

        if self.m_plan is None:
            return ()
        setup = self.m_plan.metadata.get("dsh")
        name = setup.get("api_key_env") if isinstance(setup, dict) else None
        return dsh_diagnostic_secrets(
            self.m_plan.env, key_name=name if isinstance(name, str) else None
        )

    def _diagnostic_detail(self, error: BaseException) -> str:
        """Return safe detail from native refusals and client-owned runtime errors."""

        if isinstance(error, BackendExecutionError):
            return sanitize_dsh_diagnostic(str(error), secret_values=self._diagnostic_secrets())
        return type(error).__name__

    def _client(self) -> DshWebClient:
        """Reconnect authentication only to the exact already owned live host."""

        if self.m_client is None:
            state = self.state
            if _dispatch_origin_birth_token(state.supervisor_pid) != state.supervisor_birth_token:
                raise BackendExecutionError("DSH Web owned host is unavailable")
            bootstrap_path = Path(state.bootstrap_path)
            if bootstrap_path.stat().st_mode & 0o077:
                raise BackendExecutionError("DSH Web bootstrap credentials must remain private")
            boot = json.loads(bootstrap_path.read_text())
            if boot.get("origin") != state.origin:
                raise BackendExecutionError("DSH Web bootstrap origin changed")
            cookie = bootstrap_path.parent / f"api-{uuid4().hex}.json"
            client = DshWebClient.from_connection(
                state.origin,
                launch_token=boot["launch_token"],
                cookie_file=cookie,
                secret_values=self._diagnostic_secrets(),
            )
            try:
                client.state(state.web_identity)
            except BaseException:
                client.close()
                raise
            state.cookie_path = str(cookie)
            self.m_client = client
        return self.m_client

    def observe_web_state(self) -> dict[str, Any]:
        """Read fresh native state without creating, restoring, or retargeting an Agent."""

        return self._client().state(self.state.web_identity)

    def observe_web_state_read_only(self) -> dict[str, Any]:
        """Read native state without writing a credential file or retaining the API peer."""

        state = self.state
        return self._read_web_state_with_temporary_peer(
            state, dict(state.web_identity), self._read_web_launch_token(state)
        )

    def browser_entry(self) -> NativeWebEntry:
        """Verify the live native binding through a temporary, independent API peer."""

        state = self.state
        identity = dict(state.web_identity)
        token = self._read_web_launch_token(state)
        live_state = self._read_web_state_with_temporary_peer(state, identity, token)
        if (
            live_state.get("available") is not True
            or live_state.get("identity") != identity
            or state.web_identity != identity
        ):
            raise DshWebError("stale_identity", "DSH Web execution identity changed")
        return NativeWebEntry(origin=state.native_surface.origin, query=(("token", token),))

    def _read_web_state_with_temporary_peer(
        self, state: DshWebSessionState, identity: dict[str, Any], token: str
    ) -> dict[str, Any]:
        """Fence a read-only native state query against changes in the owned listener."""

        origin = state.native_surface.origin
        port = urlsplit(origin).port
        pid, birth = state.native_pid, state.native_birth_token
        if port is None or origin != f"http://127.0.0.1:{port}" or pid is None or birth is None:
            raise DshWebError("stale_identity", "DSH Web listener ownership is unavailable")

        def require_owned_listener() -> None:
            """Fence credential use against a lost or replaced process and listener."""

            if (
                _dispatch_origin_birth_token(state.supervisor_pid) != state.supervisor_birth_token
                or not owns_ipv4_web_listener(pid, birth, port)
                or self.m_state is not state
            ):
                raise DshWebError("stale_identity", "DSH Web listener ownership changed")

        require_owned_listener()
        client = DshWebClient.from_connection(
            origin,
            launch_token=token,
            secret_values=self._diagnostic_secrets(),
            verify_listener=require_owned_listener,
        )
        try:
            live_state = client.state(identity)
        finally:
            client.close()
        require_owned_listener()
        return live_state

    @staticmethod
    def _read_web_launch_token(state: DshWebSessionState) -> str:
        """Read only the private regular bootstrap for the persisted Web owner."""

        try:
            path = Path(state.bootstrap_path)
            if path.resolve(strict=True) != path:
                raise ValueError
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, "rb") as stream:
                info = os.fstat(stream.fileno())
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_uid != os.geteuid()
                    or info.st_mode & 0o077
                    or info.st_size > 4096
                ):
                    raise ValueError
                bootstrap = stream.read(4097)
            if len(bootstrap) > 4096:
                raise ValueError
            payload = json.loads(bootstrap)
            token = payload.get("launch_token") if isinstance(payload, dict) else None
            if (
                isinstance(token, str)
                and token
                and type(payload.get("version")) is int
                and payload["version"] == 1
                and payload.get("origin") == state.origin
            ):
                return token
        except (OSError, ValueError, RuntimeError):
            pass
        raise DshWebError("invalid_credentials", "Private DSH Web bootstrap is unavailable")

    def observe_common_plugins(self) -> dict[str, Any]:
        """Read effective skill/MCP evidence from the already-owned native host."""

        return self._client().observe_common_plugins(self.state.web_identity)

    def refresh_common_plugins(
        self,
        timeout_seconds: float = 30.0,
        *,
        deadline_monotonic: float | None = None,
        expected_identity: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """Refresh through a separate owner connection so operator reads stay responsive.

        The native host retains maintenance authority if this request loses its
        response. Closing this connection never restarts or retries the agent.
        """

        if (
            not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
            or (deadline_monotonic is not None and not math.isfinite(deadline_monotonic))
        ):
            raise DshWebError("invalid_request", "Native refresh requires a finite deadline")
        deadline = min(
            deadline_monotonic if deadline_monotonic is not None else float("inf"),
            time.monotonic() + timeout_seconds,
        )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise DshWebError("expired", "Native refresh deadline elapsed before authentication")
        state = self.state
        identity = dict(state.web_identity)
        native_keys = (
            "agent_id",
            "runtime_session_id",
            "generation",
            "host_incarnation",
            "native_session_id",
            "agent_incarnation",
        )
        if expected_identity is not None and any(
            identity.get(key) != expected_identity.get(key) for key in native_keys
        ):
            raise DshWebError(
                "stale_identity", "Native refresh identity changed before authentication"
            )
        if _dispatch_origin_birth_token(state.supervisor_pid) != state.supervisor_birth_token:
            raise BackendExecutionError("DSH Web owned host is unavailable")
        bootstrap = Path(state.bootstrap_path)
        if bootstrap.stat().st_mode & 0o077:
            raise BackendExecutionError("DSH Web bootstrap credentials must remain private")
        payload = json.loads(bootstrap.read_text(encoding="utf-8"))
        if payload.get("origin") != state.origin:
            raise BackendExecutionError("DSH Web bootstrap origin changed")
        client = DshWebClient.from_connection(
            state.origin,
            launch_token=payload["launch_token"],
            timeout_seconds=remaining,
            secret_values=self._diagnostic_secrets(),
        )
        try:
            if self.m_state is not state or state.web_identity != identity:
                raise DshWebError(
                    "stale_identity", "Native refresh identity changed during authentication"
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DshWebError(
                    "expired", "Native refresh deadline elapsed during authentication"
                )
            return client.refresh_common_plugins(
                identity, timeout_seconds=remaining, deadline_monotonic=deadline
            )
        finally:
            client.close()

    def observe_web_history(self, after_sequence: int = -1, limit: int = 100) -> dict[str, Any]:
        """Read bounded native metadata history from this exact live incarnation."""

        return self._client().history(
            self.state.web_identity, after_sequence=after_sequence, limit=limit
        )

    def plugin_execution_identity(self) -> tuple[str, ...]:
        """Capture the exact generation, host, Agent, and session for ordinary dispatch."""

        self.observe_web_state()
        identity = self.state.web_identity
        return tuple(
            str(identity[name])
            for name in ("generation", "host_incarnation", "agent_incarnation", "native_session_id")
        )

    def send_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> list[SessionEvent]:
        """Submit ready-only semantic input without terminal or cold-session fallback."""

        return self.send_web_prompt(
            prompt,
            turn_artifact_dir_name=turn_artifact_dir_name,
            session_selection=session_selection,
            execution_model=execution_model,
            operator=self.m_dispatch_control is None,
        )

    def send_web_prompt(
        self,
        prompt: str,
        *,
        admission_policy: str = "ready_only",
        operator: bool = True,
        turn_artifact_dir_name: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
        deadline_epoch_ms: int | None = None,
        timeout_seconds: float = 300,
    ) -> list[SessionEvent]:
        """Admit once, then observe only the native turn proven to have claimed this input."""

        if not prompt.strip() or timeout_seconds <= 0:
            raise BackendExecutionError("DSH Web requires nonempty input and a positive timeout")
        if admission_policy not in {"ready_only", "if_no_pending", "always"}:
            raise BackendExecutionError("Unsupported DSH Web admission policy")
        if not operator and admission_policy != "ready_only":
            raise BackendExecutionError("Ordinary DSH Web delivery requires ready_only")
        control = self.m_dispatch_control
        if control is not None:
            control.require_allowed()
        client = self._client()
        if session_selection is not None:
            if session_selection.mode == "new":
                if not operator or admission_policy != "ready_only":
                    raise BackendExecutionError(
                        "DSH Web reset requires explicit ready_only control"
                    )
                identity = client.lifecycle_reset(self.state.web_identity)
                self._bind_native_identity(identity)
            elif (
                session_selection.mode != "exact"
                or session_selection.session_id != self.state.web_identity["native_session_id"]
            ):
                raise BackendExecutionError("DSH Web addresses only its bound native conversation")
        if execution_model is not None and not execution_model.is_empty():
            if not operator:
                raise BackendExecutionError("Ordinary Web delivery cannot change native models")
            self._set_explicit_model(execution_model)
        operation = turn_artifact_dir_name or f"web-{uuid4().hex}"
        if Path(operation).name != operation or operation in {".", ".."}:
            raise BackendExecutionError("DSH Web operation ID must be one path component")
        if self.m_manifest_path is None:
            raise BackendExecutionError("DSH Web runtime manifest is unavailable")
        turn_dir = (
            self.m_manifest_path.parent / f"{self.m_manifest_path.stem}.turn-artifacts" / operation
        )
        turn_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        attempt_path = turn_dir / "web-attempt.json"
        if attempt_path.exists():
            raise BackendExecutionError("A DSH Web operation ID cannot be submitted twice")
        identity = dict(self.state.web_identity)
        _write_private_json(
            attempt_path,
            {
                "version": 1,
                "operation_id": operation,
                "identity": identity,
                "operator": operator,
                "admission_policy": admission_policy,
                "status": "submitting",
                "evidence_path": self.state.evidence_path,
            },
        )
        observed = client.conversation(identity, limit=1000)
        cursor = int(observed["current_cursor"])
        self._begin_managed_accounting(operation)
        deadline = time.monotonic() + timeout_seconds
        if deadline_epoch_ms is None:
            remaining = (
                max(0.0, control.m_deadline - time.monotonic())
                if control
                else min(timeout_seconds, 30)
            )
            deadline_epoch_ms = int((time.time() + remaining) * 1000)
        events: list[SessionEvent] = []
        if control is not None:
            with self.m_operation_lock:
                self.m_active_operations[id(control)] = operation
        try:
            dispatch_permission = control.prepare_bridge_permission(turn_dir) if control else None
            receipt = client.prompt(
                identity,
                prompt,
                operation_id=operation,
                deadline_epoch_ms=deadline_epoch_ms,
                admission_policy=admission_policy,
                operator=operator,
                dispatch_permission_path=dispatch_permission,
            )
            if receipt.get("identity") != identity or receipt.get("operation_id") != operation:
                raise DshWebError("identity_mismatch", "Native admission receipt is mismatched")
            write_usage_json(turn_dir / "web-receipt.json", receipt)
            if control is not None:
                control.confirm_handoff()
            while True:
                current = client.receipt(identity, operation)
                if current is None:
                    raise DshWebError(
                        "outcome_uncertain", "Native admission receipt is unavailable"
                    )
                receipt = current
                self._note_managed_claims(operation, receipt)
                write_usage_json(turn_dir / "web-receipt.json", receipt)
                if receipt.get("status") in {"terminal", "abandoned"}:
                    break
                if time.monotonic() >= deadline:
                    raise BackendExecutionError(
                        "DSH Web controller wait expired; inspect the exact operation receipt"
                    )
                time.sleep(0.05)
            while True:
                page = client.conversation(identity, after_native_sequence=cursor, limit=1000)
                entries = page.get("entries", [])
                own_turns = set(receipt.get("turns", []))
                for entry in entries:
                    events.extend(self._semantic_events(entry, own_turns))
                cursor = int(page["cursor"])
                if not page.get("has_more"):
                    break
            result = str(receipt.get("result", "abandoned"))
            outcome = (
                "completed"
                if result == "completed"
                else "interrupted"
                if result in {"aborted", "cancelled", "abandoned"}
                else "failed"
            )
            self.state.turn_index += 1
            self._settle_managed_accounting(operation, receipt, outcome)
            events.append(
                SessionEvent(
                    kind="done",
                    message=f"Web turn {outcome}",
                    turn_index=self.state.turn_index,
                    payload={
                        "outcome": outcome,
                        "operation_id": operation,
                        "native_input_id": receipt.get("message_id"),
                        "native_turn_ids": receipt.get("turns", []),
                        "identity": identity,
                        "native_result": result,
                        "mixed_input": receipt.get("mixed_input", "unknown"),
                    },
                )
            )
            write_usage_json(
                turn_dir / "web-result.json",
                {
                    "operation_id": operation,
                    "outcome": outcome,
                    "identity": identity,
                    "receipt": receipt,
                },
            )
            return events
        except DshWebError as exc:
            if self.m_usage_service is not None:
                self.m_usage_service.settle_dsh_web_turn(
                    operation_id=operation,
                    outcome="failed"
                    if exc.code
                    in {
                        "not_ready",
                        "pending_input",
                        "interaction_wait",
                        "expired",
                        "cancelled",
                        "forbidden",
                        "stale_identity",
                        "invalid_policy",
                        "invalid_request",
                        "unknown_state",
                        "unavailable",
                        "authentication_failed",
                    }
                    else None,
                )
            write_usage_json(
                turn_dir / "web-error.json",
                {
                    "operation_id": operation,
                    "error_code": exc.code,
                    "identity": identity,
                    "outcome": "uncertain",
                },
            )
            raise
        finally:
            if control is not None:
                if not control.m_handoff_confirmed.is_set():
                    self.cancel_request_dispatch(control)
                with self.m_operation_lock:
                    self.m_active_operations.pop(id(control), None)

    def _bind_native_identity(self, identity: Mapping[str, Any]) -> None:
        """Publish only the exact identity returned by this explicit native lifecycle."""

        previous = self.state.web_identity
        if any(
            identity.get(name) != previous[name]
            for name in ("agent_id", "runtime_session_id", "generation", "host_incarnation")
        ):
            raise BackendExecutionError("Native Web reset changed its owned execution host")
        self.state.web_identity = dict(identity)
        self.state.native_surface
        self._bind_managed_accounting(new_session=True)
        if self.m_binding_changed is not None:
            self.m_binding_changed()

    def _set_explicit_model(self, config: ModelConfig) -> None:
        """Apply an explicit operator override without reapplying birth defaults."""

        setup_metadata = cast(dict[str, Any], self.plan.metadata["dsh"])
        setup = DshEffectiveToolParams.from_file(Path(setup_metadata["setup_path"]))
        selected = config.name or self.observe_web_state().get("model", {}).get("model")
        reasoning = None
        if config.reasoning is not None:
            mapping = resolve_reasoning_mapping(
                tool="dsh",
                requested_level=config.reasoning.level,
                model_name=selected,
                home_path=self.plan.home_path,
            )
            reasoning = mapping.get("native_value")
        model, _ = setup.select_model(selected)
        self._client().set_model(
            self.state.web_identity,
            provider=setup.route,
            model=model.id,
            reasoning_effort=reasoning,
        )

    def _semantic_events(self, entry: Mapping[str, Any], own_turns: set[int]) -> list[SessionEvent]:
        """Project native committed content only from this operation's proven turns."""

        if entry.get("turn") not in own_turns:
            return []
        events: list[SessionEvent] = []
        common = {
            "native_sequence": entry.get("native_sequence"),
            "native_turn": entry.get("turn"),
            "identity": dict(self.state.web_identity),
        }
        for block in entry.get("content", []) if entry.get("type") == "assistant/message" else []:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind in {"text", "reasoning"}:
                events.append(
                    SessionEvent(
                        kind="assistant" if kind == "text" else "reasoning",
                        message=str(block.get("text", "")),
                        turn_index=self.state.turn_index + 1,
                        payload={**common, "text": block.get("text", "")},
                    )
                )
            elif kind == "tool-call":
                events.append(
                    SessionEvent(
                        kind="tool_call",
                        message=str(block.get("name", "Native tool")),
                        turn_index=self.state.turn_index + 1,
                        payload={**common, **block},
                    )
                )
        if entry.get("type") == "tool/result":
            events.append(
                SessionEvent(
                    kind="tool_result",
                    message=str(entry.get("name", "Native tool result")),
                    turn_index=self.state.turn_index + 1,
                    payload={
                        **common,
                        "call_id": entry.get("call_id"),
                        "is_error": entry.get("is_error"),
                        "content": entry.get("content", []),
                    },
                )
            )
        return events

    def _bind_managed_accounting(self, *, new_session: bool) -> None:
        """Persist the journal boundary before publishing native browser authority."""

        if self.m_manifest_path is None:
            return
        self.m_usage_service = UsageService.from_launch(
            self.m_manifest_path, self.plan, self.state.web_identity["native_session_id"]
        )
        self.m_usage_service.bind_dsh_web(
            identity=dict(self.state.web_identity),
            evidence_path=Path(self.state.evidence_path),
            new_session=new_session,
        )

    def _begin_managed_accounting(self, operation: str) -> None:
        """Register an operation before native mutation to prevent duplicate human charging."""

        if self.m_usage_service is None:
            self._bind_managed_accounting(new_session=False)
        if self.m_usage_service is not None:
            self.m_usage_service.begin_dsh_web_turn(
                operation_id=operation, turn_index=self.state.turn_index + 1
            )

    def _note_managed_claims(self, operation: str, receipt: Mapping[str, Any]) -> None:
        """Associate native input claims before immutable accounting finalization."""

        if self.m_usage_service is not None:
            self.m_usage_service.settle_dsh_web_turn(operation_id=operation, receipt=dict(receipt))

    def _settle_managed_accounting(
        self, operation: str, receipt: Mapping[str, Any], outcome: str
    ) -> None:
        """Collect settled journal evidence independently of Web API event copies."""

        if self.m_usage_service is not None:
            self.m_usage_service.settle_dsh_web_turn(
                operation_id=operation, receipt=dict(receipt), outcome=outcome
            )
            self.m_usage_service.reconcile_dsh_web()

    def cancel_request_dispatch(self, control: HeadlessDispatchControl) -> None:
        """Abandon only native activity or pending input proven to belong to this attempt."""

        control.cancel()
        with self.m_operation_lock:
            operation = self.m_active_operations.get(id(control))
            if operation is None or operation in self.m_abandoning_operations:
                return
            self.m_abandoning_operations.add(operation)
        identity = dict(self.state.web_identity)

        def abandon() -> None:
            """Reconcile only this input after an in-flight HTTP preparation releases its lock."""

            try:
                self._client().interrupt(identity, turn_start_seq=None, operation_id=operation)
            except BackendExecutionError:
                pass
            finally:
                with self.m_operation_lock:
                    self.m_abandoning_operations.discard(operation)

        threading.Thread(target=abandon, name="dsh-web-abandon", daemon=True).start()

    def interrupt(self) -> SessionControlResult:
        """Capture and cancel one exact currently active native turn, including human work."""

        try:
            state = self.observe_web_state()
            active = state.get("active_turn")
            if active is None:
                return SessionControlResult(
                    status="ok", action="interrupt", detail="No active native Web turn"
                )
            return self.interrupt_web_turn(
                self.state.web_identity, turn_start_seq=active["start_sequence"]
            )
        except BackendExecutionError as exc:
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail=f"Web interruption unavailable: {self._diagnostic_detail(exc)}",
            )

    def interrupt_web_turn(
        self,
        identity: Mapping[str, Any],
        *,
        turn_start_seq: int,
        operation_id: str | None = None,
    ) -> SessionControlResult:
        """Cancel a previously captured exact turn without recapturing newer human work."""

        if dict(identity) != self.state.web_identity:
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail="Captured Web execution identity is no longer current",
            )
        try:
            self._client().interrupt(
                identity, turn_start_seq=turn_start_seq, operation_id=operation_id
            )
            return SessionControlResult(
                status="ok",
                action="interrupt",
                detail="Interrupted the captured native Web turn; retained inbox remains visible",
            )
        except BackendExecutionError as exc:
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail=f"Captured Web interruption refused: {self._diagnostic_detail(exc)}",
            )

    def terminate(self) -> SessionControlResult:
        """Stop the owned host while preserving native history and accounting artifacts."""

        try:
            try:
                self._client().stop(self.state.web_identity)
            except BackendExecutionError:
                pass
            finally:
                self.close_control_connection()
            self._stop_supervisor_file(Path(self.state.bootstrap_path).parent / "supervisor.json")
            if (
                self.m_force_cleanup
                and has_tmux_session(session_name=self.state.tmux_session_name).returncode == 0
            ):
                if not self._owns_supervisor_session(
                    self.state.tmux_session_name, self.state.control_path
                ):
                    raise BackendExecutionError("DSH Web supervisor ownership has changed")
                kill_tmux_session(session_name=self.state.tmux_session_name)
            return SessionControlResult(
                status="ok", action="terminate", detail="Stopped the owned native Web Host"
            )
        except (OSError, BackendExecutionError) as exc:
            return SessionControlResult(
                status="error",
                action="terminate",
                detail=f"Web cleanup failed: {self._diagnostic_detail(exc)}",
            )

    def close_control_connection(self) -> None:
        """Close only this API Peer, retaining the native host and browser session."""

        client, self.m_client = self.m_client, None
        if client is not None:
            client.close()

    def close(self) -> None:
        """Release observation/control resources independently of managed stop."""

        self.close_control_connection()

    @staticmethod
    def _owns_supervisor_session(name: str, control_path: str) -> bool:
        """Fence pane/session cleanup against the exact recorded supervisor owner."""

        result = run_tmux(["show-options", "-v", "-t", name, "@houmao_dsh_web_owner"])
        return result.returncode == 0 and result.stdout.strip() == control_path

    @staticmethod
    def _stop_supervisor_file(path: Path) -> None:
        """Stop only a captured supervisor while its process birth remains unchanged."""

        if not path.is_file():
            return
        process = json.loads(path.read_text())
        pid, birth = process.get("supervisor_pid"), process.get("supervisor_birth_token")
        if type(pid) is not int or not isinstance(birth, str):
            raise BackendExecutionError("DSH Web supervisor ownership is unavailable")
        if _dispatch_origin_birth_token(pid) == birth:
            os.kill(pid, signal.SIGTERM)
            deadline = time.monotonic() + _SUPERVISOR_STOP_TIMEOUT_SECONDS
            while _dispatch_origin_birth_token(pid) == birth and time.monotonic() < deadline:
                time.sleep(0.05)
            if _dispatch_origin_birth_token(pid) == birth:
                raise BackendExecutionError("DSH Web supervisor cleanup did not settle")
        native_pid, native_birth = process.get("native_pid"), process.get("native_birth_token")
        if (
            type(native_pid) is not int
            or not isinstance(native_birth, str)
            or _dispatch_origin_birth_token(native_pid) != native_birth
        ):
            return
        descendants: dict[int, str] = {}
        _signal_owned(native_pid, native_birth, signal.SIGTERM, descendants)
        deadline = time.monotonic() + 10
        while (
            _dispatch_origin_birth_token(native_pid) == native_birth and time.monotonic() < deadline
        ):
            time.sleep(0.05)
        _signal_owned(native_pid, native_birth, signal.SIGKILL, descendants)
        deadline = time.monotonic() + 5
        while any(
            _dispatch_origin_birth_token(child) == expected
            for child, expected in descendants.items()
        ):
            if time.monotonic() >= deadline:
                raise BackendExecutionError("DSH Web orphan process cleanup did not settle")
            time.sleep(0.05)
