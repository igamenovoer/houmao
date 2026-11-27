"""Publish and verify generation-bound detached Hermes daemon authority."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path
import stat
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.backends.dsh_acp_connection import _read_process_lineage
from houmao.agents.realm_controller.backends.hermes_native import (
    HermesDaemon,
    HermesDaemonIdentity,
    write_hermes_evidence,
)
from houmao.agents.realm_controller.backends.service_runtime import (
    ManagedServiceSessionState,
    read_service_record,
    service_component,
)
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.errors import BackendExecutionError, SessionManifestError
from houmao.agents.realm_controller.hermes_tool_origin import hermes_tool_origin_socket
from houmao.agents.realm_controller.manifest import (
    default_manifest_path,
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.models import LaunchPlan
from houmao.agents.realm_controller.registry_models import ManagedAgentRegistryRecordV3
from houmao.agents.realm_controller.registry_storage import (
    _managed_agent_record_lock,
    is_managed_agent_record_active,
    load_managed_agent_record_by_agent_id,
)
from houmao.execution.models import ExecutionBindingV1
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR


HERMES_DETACHED_SELF_BACKENDS = frozenset({"hermes_service", "hermes_tui"})
_LOCATOR_NAME = ".houmao-managed-self.json"
_UNAVAILABLE = "Current Hermes daemon authority is unavailable."


def hermes_daemon_self_supported(backend: str, *, named_profile: bool) -> bool:
    """Allow baseline detached modes and named Headless workers with a saved session."""

    return backend in HERMES_DETACHED_SELF_BACKENDS or (
        named_profile and backend == "hermes_headless"
    )


class HermesSelfLocator(BaseModel):
    """Identify a candidate runtime without granting caller authority."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    manifest_path: str
    agent_id: str
    generation_id: str
    pid: int = Field(gt=1)
    birth_token: str = Field(min_length=1)
    profile_epoch: int | None = Field(default=None, gt=0)


class HermesSelfAuthority(HermesSelfLocator):
    """Verify the selected daemon and its native binding for one generation."""

    execution_binding: ExecutionBindingV1
    home: str
    workspace: str
    native_session_id: str = Field(min_length=1)
    instance_id: str = Field(min_length=1)
    authority_epoch: int = Field(gt=0)
    gateway_root: str | None = None
    profile_id: str | None = None
    broker_socket: str | None = None

    @property
    def locator(self) -> HermesSelfLocator:
        """Return the matching home discovery record for this published proof."""

        return HermesSelfLocator(
            manifest_path=self.manifest_path,
            agent_id=self.agent_id,
            generation_id=self.generation_id,
            pid=self.pid,
            birth_token=self.birth_token,
            profile_epoch=self.profile_epoch,
        )

    @property
    def fingerprint(self) -> str:
        """Identify this exact immutable runtime binding without disclosing its fields."""

        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class _HermesAcpBinding(BaseModel):
    """Read the selected service's private native-session evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    native_session_id: str
    generation_id: str
    service_incarnation: str
    workspace: str
    protocol_version: Literal[1]
    binding_method: Literal["session/new", "session/load"]


class _HermesDaemonProcess(BaseModel):
    """Read the native controller's last verified daemon incarnation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    home: str
    workspace: str
    pid: int
    birth_token: str
    instance_id: str
    authority_epoch: int
    gateway_root: str | None = None
    profile_id: str | None = None


@dataclass(frozen=True)
class _RuntimeDaemonBinding:
    """Select the exact evidence path and native binding from the manifest."""

    locator: Path
    root: Path
    home: Path
    execution_binding: ExecutionBindingV1
    generation_id: str
    native_session_id: str
    service_incarnation: str | None = None

    @property
    def authority_path(self) -> Path:
        """Keep each managed generation's self authority in its own record."""

        return self.root / f"houmao-self-{service_component(self.generation_id)}.json"


def hermes_tui_native_root(manifest_path: Path) -> Path:
    """Return the manifest-specific directory used for Hermes TUI control."""

    return manifest_path.parent / f".{manifest_path.stem}.hermes"


def _runtime_daemon_binding(
    manifest_path: Path, payload: SessionManifestPayloadV4
) -> _RuntimeDaemonBinding:
    """Select the saved home and exact native root without probing tmux."""

    execution = payload.runtime.execution_binding
    generation = payload.registry_generation_id
    profile = payload.launch_plan.hermes_profile
    headless = payload.backend == "hermes_headless"
    native_session = payload.backend_state.get("native_session_id")
    if headless:
        native_session = payload.backend_state.get("session_id")
    home = Path(payload.launch_plan.home_selector.home_path)
    workspace = Path(payload.working_directory)
    if (
        execution is None
        or generation is None
        or not isinstance(native_session, str)
        or not native_session
        or payload.tool != "hermes"
        or not hermes_daemon_self_supported(payload.backend, named_profile=profile is not None)
        or manifest_path
        != default_manifest_path(
            Path(execution.runtime_root), payload.backend, manifest_path.parent.name
        )
        or not all(path.is_absolute() and path.resolve() == path for path in (home, workspace))
        or payload.backend_state.get("working_directory") != str(workspace)
        or profile is not None
        and (
            home != Path(profile.profile_home)
            or profile.context_id != execution.context_id
            or Path(profile.broker_socket)
            != hermes_tool_origin_socket(Path(profile.prepared_root), profile.context_id)
        )
    ):
        raise SessionManifestError(_UNAVAILABLE)

    incarnation = None
    if payload.backend == "hermes_service":
        state = ManagedServiceSessionState.from_payload(payload.backend_state)
        incarnation = service_component(state.service_incarnation)
        if (
            state.generation_id != generation
            or state.runtime_session_id != manifest_path.parent.name
        ):
            raise SessionManifestError(_UNAVAILABLE)
        root = manifest_path.parent / "service" / incarnation
    elif headless:
        root = manifest_path.parent / "hermes-native"
    else:
        if payload.backend_state.get("home") != str(home):
            raise SessionManifestError(_UNAVAILABLE)
        root = hermes_tui_native_root(manifest_path)
    return _RuntimeDaemonBinding(
        locator=home / _LOCATOR_NAME,
        root=root,
        home=home,
        execution_binding=execution,
        generation_id=generation,
        native_session_id=native_session,
        service_incarnation=incarnation,
    )


def _read_private_record(path: Path) -> bytes:
    """Reject redirected parents and open one bounded, private authority record."""

    try:
        resolved = path.resolve()
    except RuntimeError as exc:
        raise SessionManifestError(_UNAVAILABLE) from exc
    if not path.is_absolute() or path != resolved:
        raise SessionManifestError(_UNAVAILABLE)
    return read_service_record(path)


def _require_service_binding(binding: _RuntimeDaemonBinding, workspace: str) -> None:
    """Check the exact ACP incarnation and logical session recorded by its owner."""

    if binding.service_incarnation is None:
        return
    native = _HermesAcpBinding.model_validate_json(
        _read_private_record(binding.root / "hermes-acp-binding.json")
    )
    if (
        native.generation_id != binding.generation_id
        or native.service_incarnation != binding.service_incarnation
        or native.native_session_id != binding.native_session_id
        or native.workspace != workspace
    ):
        raise SessionManifestError(_UNAVAILABLE)


def read_hermes_self_locator(home: Path) -> HermesSelfLocator | None:
    """Locate a managed runtime from canonical Hermes home evidence, if present."""

    try:
        return HermesSelfLocator.model_validate_json(_read_private_record(home / _LOCATOR_NAME))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise SessionManifestError(_UNAVAILABLE) from exc


def require_live_hermes_daemon_authority(
    manifest_path: Path, payload: SessionManifestPayloadV4
) -> HermesSelfAuthority:
    """Verify exact current-generation daemon evidence without testing caller ancestry."""

    proof = _require_published_hermes_daemon_authority(manifest_path, payload)
    profile = payload.launch_plan.hermes_profile
    if profile is not None:
        binding = _runtime_daemon_binding(manifest_path, payload)
        try:
            daemon = HermesDaemon.from_inputs(
                executable=str(profile.executable),
                home=binding.home,
                workspace=Path(proof.workspace),
                env={},
                root=binding.root,
                profile=profile,
            ).verify_shared_session(binding.native_session_id)
            if (
                daemon.home != binding.home
                or daemon.gateway_root != Path(proof.gateway_root or "")
                or daemon.pid != proof.pid
                or daemon.birth_token != proof.birth_token
                or daemon.instance_id != proof.instance_id
                or daemon.authority_epoch != proof.authority_epoch
                or daemon.profile_id != proof.profile_id
            ):
                raise SessionManifestError(_UNAVAILABLE)
        except (OSError, ValueError, BackendExecutionError) as exc:
            raise SessionManifestError(_UNAVAILABLE) from exc
    return proof


def _require_published_hermes_daemon_authority(
    manifest_path: Path, payload: SessionManifestPayloadV4
) -> HermesSelfAuthority:
    """Validate owner publication without calling back into a blocked native tool spawn."""

    try:
        binding = _runtime_daemon_binding(manifest_path, payload)
        _require_service_binding(binding, payload.working_directory)
        proof = HermesSelfAuthority.model_validate_json(
            _read_private_record(binding.authority_path)
        )
        process = _HermesDaemonProcess.model_validate_json(
            _read_private_record(binding.root / "hermes-daemon.json")
        )
        profile = payload.launch_plan.hermes_profile
        if (
            proof.manifest_path != str(manifest_path)
            or proof.agent_id != payload.agent_id
            or proof.generation_id != binding.generation_id
            or proof.execution_binding != binding.execution_binding
            or proof.home != str(binding.home)
            or proof.workspace != payload.working_directory
            or proof.native_session_id != binding.native_session_id
            or proof.gateway_root != (str(profile.prepared_root) if profile is not None else None)
            or proof.profile_id != (str(binding.home) if profile is not None else None)
            or proof.broker_socket != (str(profile.broker_socket) if profile is not None else None)
            or proof.profile_epoch != (proof.authority_epoch if profile is not None else None)
            or any(getattr(proof, key) != value for key, value in process.model_dump().items())
            or read_hermes_self_locator(binding.home) != proof.locator
            or _dispatch_origin_birth_token(proof.pid) != proof.birth_token
        ):
            raise SessionManifestError(_UNAVAILABLE)
        return proof
    except (OSError, ValueError, BackendExecutionError) as exc:
        raise SessionManifestError(_UNAVAILABLE) from exc


def load_hermes_tool_authority(
    home: Path,
    session_id: str,
    *,
    gateway_root: Path,
    context_id: str,
    broker_socket: Path,
    pid: int,
    birth_token: str,
) -> HermesSelfAuthority:
    """Resolve only a live published profile and session within this broker's owner scope."""

    if home.parent != gateway_root / "profiles":
        raise SessionManifestError(_UNAVAILABLE)
    locator = read_hermes_self_locator(home)
    if locator is None:
        raise SessionManifestError(_UNAVAILABLE)
    path = Path(locator.manifest_path)
    if path.resolve() != path or path.name != "manifest.json":
        raise SessionManifestError(_UNAVAILABLE)
    saved = load_session_manifest(path)
    payload = parse_session_manifest_payload(saved.payload, source="Hermes tool authority")
    proof = _require_published_hermes_daemon_authority(path, payload)
    record = load_managed_agent_record_by_agent_id(
        proof.agent_id,
        env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: proof.execution_binding.registry_root},
    )
    if (
        record is None
        or not is_managed_agent_record_active(record)
        or record.generation_id != proof.generation_id
        or record.runtime.manifest_path != str(path)
        or record.execution_binding != proof.execution_binding
        or record.identity.backend != payload.backend
        or proof.home != str(home)
        or proof.gateway_root != str(gateway_root)
        or proof.execution_binding.context_id != context_id
        or proof.broker_socket != str(broker_socket)
        or proof.native_session_id != session_id
        or proof.pid != pid
        or proof.birth_token != birth_token
    ):
        raise SessionManifestError(_UNAVAILABLE)
    return proof


def require_hermes_daemon_caller(authority: HermesSelfAuthority) -> None:
    """Require a bounded process ancestry walk and a live matching daemon birth."""

    pid = os.getpid()
    for _ in range(128):
        if pid == authority.pid:
            if _dispatch_origin_birth_token(pid) == authority.birth_token:
                return
            break
        if pid <= 1:
            break
        lineage = _read_process_lineage(pid)
        if lineage is None or lineage[0] == pid:
            break
        pid = lineage[0]
    raise SessionManifestError("The caller does not belong to the current managed Hermes daemon.")


@contextmanager
def _home_locator_lock(home: Path, *, blocking: bool) -> Iterator[None]:
    """Serialize current locator publication across owners of the same home."""

    descriptor = os.open(
        home / ".houmao-managed-self.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise SessionManifestError(_UNAVAILABLE)
        fcntl.flock(descriptor, fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def publish_hermes_daemon_authority(
    manifest_path: Path,
    payload: SessionManifestPayloadV4,
    daemon: HermesDaemonIdentity,
    *,
    blocking: bool = True,
) -> None:
    """Publish evidence from a verified native binding for the current registry owner."""

    try:
        binding = _runtime_daemon_binding(manifest_path, payload)
        _require_service_binding(binding, payload.working_directory)
        if daemon.home != binding.home or binding.root.resolve() != binding.root:
            raise SessionManifestError(_UNAVAILABLE)
        registry_env = {HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: binding.execution_binding.registry_root}
        with (
            _home_locator_lock(binding.home, blocking=blocking),
            _managed_agent_record_lock(payload.agent_id, env=registry_env, blocking=blocking),
        ):
            current = load_managed_agent_record_by_agent_id(payload.agent_id, env=registry_env)
            selected = load_session_manifest(manifest_path)
            manifest = parse_session_manifest_payload(selected.payload, source=str(selected.path))
            if (
                current is None
                or not is_managed_agent_record_active(current)
                or current.generation_id != binding.generation_id
                or current.execution_binding != binding.execution_binding
                or current.runtime.manifest_path != str(manifest_path)
                or current.identity.backend != payload.backend
                or manifest.registry_generation_id != binding.generation_id
                or manifest.agent_id != payload.agent_id
                or manifest.runtime.execution_binding != binding.execution_binding
                or manifest.working_directory != payload.working_directory
                or _runtime_daemon_binding(manifest_path, manifest) != binding
                or _dispatch_origin_birth_token(daemon.pid) != daemon.birth_token
            ):
                raise SessionManifestError(_UNAVAILABLE)
            previous = read_hermes_self_locator(binding.home)
            profile = payload.launch_plan.hermes_profile
            if (profile is None) != (daemon.gateway_root is None) or (
                profile is not None
                and (
                    daemon.gateway_root != Path(profile.prepared_root)
                    or daemon.profile_id != str(binding.home)
                )
            ):
                raise SessionManifestError(_UNAVAILABLE)
            if (
                previous is not None
                and (previous.manifest_path, previous.agent_id, previous.generation_id)
                != (str(manifest_path), payload.agent_id, current.generation_id)
                and (previous.pid, previous.birth_token) == (daemon.pid, daemon.birth_token)
                and (profile is None or previous.profile_epoch in (None, daemon.authority_epoch))
            ):
                raise SessionManifestError(_UNAVAILABLE)
            locator = HermesSelfLocator(
                manifest_path=str(manifest_path),
                agent_id=payload.agent_id,
                generation_id=binding.generation_id,
                pid=daemon.pid,
                birth_token=daemon.birth_token,
                profile_epoch=daemon.authority_epoch if profile is not None else None,
            )
            proof = HermesSelfAuthority(
                **locator.model_dump(),
                execution_binding=binding.execution_binding,
                home=str(binding.home),
                workspace=payload.working_directory,
                native_session_id=binding.native_session_id,
                instance_id=daemon.instance_id,
                authority_epoch=daemon.authority_epoch,
                gateway_root=str(daemon.gateway_root) if profile is not None else None,
                profile_id=daemon.profile_id if profile is not None else None,
                broker_socket=str(profile.broker_socket) if profile is not None else None,
            )
            observed = _HermesDaemonProcess.model_validate_json(
                _read_private_record(binding.root / "hermes-daemon.json")
            )
            if any(getattr(proof, key) != value for key, value in observed.model_dump().items()):
                raise SessionManifestError(_UNAVAILABLE)
            write_hermes_evidence(
                binding.locator, locator.model_dump(mode="json", exclude_none=True)
            )
            write_hermes_evidence(
                binding.authority_path, proof.model_dump(mode="json", exclude_none=True)
            )
    except (OSError, ValueError, BackendExecutionError) as exc:
        raise SessionManifestError(_UNAVAILABLE) from exc


def publish_verified_hermes_daemon_for_generation(
    manifest_path: Path, generation: str, daemon: HermesDaemonIdentity
) -> None:
    """Refresh a replacement daemon after native submission verifies the saved conversation."""

    saved = load_session_manifest(manifest_path)
    payload = parse_session_manifest_payload(saved.payload, source=str(saved.path))
    binding = _runtime_daemon_binding(manifest_path, payload)
    if generation != binding.generation_id:
        raise SessionManifestError(_UNAVAILABLE)
    try:
        current = require_live_hermes_daemon_authority(manifest_path, payload)
    except SessionManifestError:
        current = None
    if current is not None and (
        current.pid,
        current.birth_token,
        current.instance_id,
        current.authority_epoch,
    ) == (
        daemon.pid,
        daemon.birth_token,
        daemon.instance_id,
        daemon.authority_epoch,
    ):
        return
    publish_hermes_daemon_authority(manifest_path, payload, daemon, blocking=False)


def refresh_hermes_daemon_authority(
    manifest_path: Path, record: ManagedAgentRegistryRecordV3, plan: LaunchPlan
) -> None:
    """Publish self authority after owner lifecycle has established a live registry record."""

    try:
        saved = load_session_manifest(manifest_path)
        payload = parse_session_manifest_payload(saved.payload, source=str(saved.path))
        binding = _runtime_daemon_binding(manifest_path, payload)
        if (
            record.generation_id != binding.generation_id
            or record.agent_id != payload.agent_id
            or plan.backend != payload.backend
            or plan.home_path.resolve() != binding.home
            or plan.working_directory.resolve() != Path(payload.working_directory)
        ):
            raise SessionManifestError(_UNAVAILABLE)
        try:
            proof = require_live_hermes_daemon_authority(manifest_path, payload)
        except SessionManifestError:
            proof = None
        if proof is not None:
            return

        daemon = HermesDaemon.from_launch_plan(plan, binding.root)
        if payload.launch_plan.hermes_profile is not None:
            identity = daemon.verify_shared_session(binding.native_session_id)
        elif payload.backend == "hermes_tui":
            with daemon.client() as native:
                daemon.resume_session(native, binding.native_session_id)
                identity = native.identity
        else:
            _require_service_binding(binding, payload.working_directory)
            discovered = daemon.discover()
            if discovered is None:
                raise SessionManifestError(_UNAVAILABLE)
            identity = discovered
        publish_hermes_daemon_authority(manifest_path, payload, identity)
    except (OSError, ValueError, BackendExecutionError) as exc:
        raise SessionManifestError(_UNAVAILABLE) from exc
