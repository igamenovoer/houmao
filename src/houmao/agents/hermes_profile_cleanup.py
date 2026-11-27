"""Settle native Hermes profile deletion and its separately owned project link."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict

from houmao.agents.hermes_installation import (
    PreparedHermesInstallation,
    load_prepared_hermes_installation,
)
from houmao.agents.hermes_profile import (
    HERMES_PROFILE_RECORD,
    HermesProfileBinding,
    read_hermes_profile_record,
    require_hermes_installation_context,
)
from houmao.agents.launch_env import owner_launch_baseline
from houmao.agents.realm_controller.backends.hermes_native import (
    HermesDaemon,
    write_hermes_evidence,
)
from houmao.agents.realm_controller.backends.service_runtime import (
    ManagedServiceSessionState,
    read_service_record,
    service_component,
)
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.manifest import default_manifest_path
from houmao.execution.context import current_execution_binding, current_execution_deadline


HermesProfileCleanupAction = Literal["delete", "purge_identity", "absent"]


class HermesProfileCleanupError(RuntimeError):
    """Report a scoped cleanup failure while retaining the recorded ownership."""


class _DeletionReceipt(BaseModel):
    """Pin a partially removed directory to the binding that started its deletion."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    binding: HermesProfileBinding
    device: int
    inode: int
    identity_settled: bool = False


def _receipt_path(binding: HermesProfileBinding) -> Path:
    """Keep retry evidence outside the native directory that Hermes removes."""

    return binding.prepared_root / ".houmao-host" / f"delete-{binding.profile_name}.json"


def _read_receipt(binding: HermesProfileBinding) -> _DeletionReceipt | None:
    """Refuse receipts for a different owner even if the native name is identical."""

    path = _receipt_path(binding)
    if path.parent.resolve() != path.parent:
        raise HermesProfileCleanupError("Hermes cleanup evidence has a redirected parent.")
    try:
        receipt = _DeletionReceipt.model_validate_json(read_service_record(path))
    except FileNotFoundError:
        return None
    if receipt.binding != binding:
        raise HermesProfileCleanupError(
            "The recorded Hermes deletion belongs to a different profile binding."
        )
    return receipt


def require_unused_hermes_profile_name(binding: HermesProfileBinding) -> None:
    """Reserve cleanup receipts against reuse of a native name by replacement builds."""

    if _read_receipt(binding) is not None:
        raise HermesProfileCleanupError("The Hermes profile name has recorded deletion evidence.")


def _private_directory(path: Path, *, project_link_parent: bool = False) -> None:
    """Require a canonical directory owned by the operating account."""

    info = path.lstat()
    if (
        path.resolve() != path
        or not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.geteuid()
        or info.st_mode & (0o002 if project_link_parent else 0o022)
    ):
        raise HermesProfileCleanupError("Hermes cleanup requires an owner-controlled directory.")


def _check_installation(binding: HermesProfileBinding) -> PreparedHermesInstallation:
    """Requalify the exact recorded prepared root before invoking native cleanup."""

    owner = current_execution_binding()
    if owner is not None and owner.context_id != binding.context_id:
        raise HermesProfileCleanupError(
            "The Hermes profile belongs to a different execution context."
        )
    installation = load_prepared_hermes_installation(
        binding.executable, expected_root=binding.prepared_root
    )
    if (
        installation.evidence.build != binding.installation_build
        or installation.lock_dir != binding.gateway_lock_dir
    ):
        raise HermesProfileCleanupError(
            "The prepared Hermes installation differs from the saved binding."
        )
    require_hermes_installation_context(binding.prepared_root, binding.context_id)
    _private_directory(binding.profile_home.parent)
    return installation


def _native_daemon(binding: HermesProfileBinding) -> HermesDaemon:
    """Construct a read-only native authority probe for the recorded owner root."""

    return HermesDaemon.from_inputs(
        executable=str(binding.executable),
        home=binding.profile_home,
        workspace=binding.prepared_root,
        env={},
        root=binding.prepared_root / ".houmao-host",
        profile=binding,
    )


def require_hermes_profile_quiescent(binding: HermesProfileBinding) -> None:
    """Protect session evidence if the saved native profile can still write."""

    _native_daemon(binding).verify_profile_released()


def stop_hermes_from_saved_session(manifest_path: Path, payload: SessionManifestPayloadV4) -> None:
    """Retire the recorded native owner even after its tmux surface has disappeared."""

    execution = payload.runtime.execution_binding
    session_id = payload.runtime.session_id
    home = Path(payload.launch_plan.home_selector.home_path)
    workspace = Path(payload.working_directory)
    if (
        payload.tool != "hermes"
        or execution is None
        or session_id is None
        or manifest_path
        != default_manifest_path(Path(execution.runtime_root), payload.backend, session_id)
        or home.resolve() != home
        or workspace.resolve() != workspace
    ):
        raise HermesProfileCleanupError("The recorded Hermes shutdown authority is unavailable.")
    if payload.backend == "hermes_service":
        service = ManagedServiceSessionState.from_payload(payload.backend_state)
        native = manifest_path.parent / "service" / service_component(service.service_incarnation)
    elif payload.backend == "hermes_tui":
        native = manifest_path.parent / f".{manifest_path.stem}.hermes"
    elif payload.backend == "hermes_headless":
        native = manifest_path.parent / "hermes-native"
    else:
        raise HermesProfileCleanupError("The recorded Hermes backend cannot be retired.")
    profile = payload.launch_plan.hermes_profile
    if profile is not None:
        verify_hermes_profile_owner(profile)
    HermesDaemon.from_inputs(
        executable=payload.launch_plan.executable,
        home=home,
        workspace=workspace,
        env={},
        root=native,
        profile=profile,
    ).stop()


def _native_tombstone(binding: HermesProfileBinding) -> bool:
    """Read the pinned stock tombstone for a partial deletion of an owned directory."""

    path = binding.profile_home.parent / ".deleted" / binding.profile_name
    try:
        _private_directory(path.parent)
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return False
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.geteuid()
            or info.st_mode & 0o022
            or stream.read(32) not in (b"incomplete\n", b"deleted\n")
        ):
            raise HermesProfileCleanupError("The native Hermes deletion marker is unverified.")
    return True


def verify_hermes_profile_owner(binding: HermesProfileBinding) -> None:
    """Pin the canonical directory to the exact builder-owned profile binding."""

    _private_directory(binding.profile_home)
    record = read_hermes_profile_record(binding.profile_home)
    if record != binding:
        raise HermesProfileCleanupError(
            "The native Hermes directory is owned by a different profile binding."
        )


def verify_hermes_profile_cleanup_owner(binding: HermesProfileBinding) -> None:
    """Preflight the existing build's ownership before any replacement stops it."""

    _check_installation(binding)
    verify_hermes_profile_owner(binding)
    preview_hermes_project_link(binding)


def _select_profile_action(
    binding: HermesProfileBinding, receipt: _DeletionReceipt | None
) -> HermesProfileCleanupAction:
    """Select exactly one safe native action from current ownership and release evidence."""

    daemon = _native_daemon(binding)
    try:
        state = binding.profile_home.lstat()
    except FileNotFoundError:
        daemon.verify_profile_released(require_parked=False)
        if receipt is None or receipt.identity_settled:
            return "absent"
        if not _native_tombstone(binding):
            raise HermesProfileCleanupError(
                "Hermes removed the profile but its deletion marker is unavailable."
            )
        return "purge_identity"

    _private_directory(binding.profile_home)
    if receipt is None:
        verify_hermes_profile_owner(binding)
        daemon.verify_profile_released()
    else:
        if receipt.identity_settled or (state.st_dev, state.st_ino) != (
            receipt.device,
            receipt.inode,
        ):
            raise HermesProfileCleanupError(
                "The native Hermes directory changed after cleanup began."
            )
        if os.path.lexists(binding.profile_home / HERMES_PROFILE_RECORD):
            verify_hermes_profile_owner(binding)
        elif not _native_tombstone(binding):
            raise HermesProfileCleanupError("The partial Hermes deletion lacks a native tombstone.")
        daemon.verify_profile_released(require_parked=not _native_tombstone(binding))
    return "delete"


def preview_hermes_profile_cleanup(binding: HermesProfileBinding) -> HermesProfileCleanupAction:
    """Verify removal eligibility without writing artifacts or taking a native reservation."""

    _check_installation(binding)
    return _select_profile_action(binding, _read_receipt(binding))


def settle_hermes_profile_cleanup(binding: HermesProfileBinding) -> HermesProfileCleanupAction:
    """Settle the native profile under the shared owner profile lifecycle lock."""

    installation = _check_installation(binding)
    receipt = _read_receipt(binding)
    action = _select_profile_action(binding, receipt)
    if action == "absent":
        return action
    if receipt is None:
        state = binding.profile_home.lstat()
        receipt = _DeletionReceipt(binding=binding, device=state.st_dev, inode=state.st_ino)
        write_hermes_evidence(_receipt_path(binding), receipt.model_dump(mode="json"))
    if action == "delete":
        args = ["delete", binding.profile_name, "--yes"]
    else:
        args = ["purge-identity", binding.profile_name]
    deadline = current_execution_deadline()
    timeout = min(75.0, deadline - time.monotonic()) if deadline is not None else 75.0
    if timeout <= 0:
        raise HermesProfileCleanupError(
            "The execution deadline has expired before native deletion."
        )
    try:
        result = subprocess.run(
            [str(binding.executable), "profile", *args],
            cwd=binding.prepared_root,
            env={
                **owner_launch_baseline(os.environ),
                **installation.native_environment(binding.prepared_root),
            },
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            umask=0o077,
            check=False,
        )
    except subprocess.SubprocessError as exc:
        raise HermesProfileCleanupError(
            "Native Hermes cleanup is incomplete. Retry the recorded cleanup."
        ) from exc
    if os.path.lexists(binding.profile_home):
        raise HermesProfileCleanupError(
            "The native Hermes profile directory remains. Retry the recorded cleanup."
        )
    if result.returncode != 0:
        raise HermesProfileCleanupError(
            "The native Hermes directory is absent and routing identity settlement is pending. "
            "Retry the recorded cleanup."
        )
    _native_daemon(binding).verify_profile_released(require_parked=False)
    write_hermes_evidence(
        _receipt_path(binding),
        receipt.model_copy(update={"identity_settled": True}).model_dump(mode="json"),
    )
    return action


def preview_hermes_project_link(binding: HermesProfileBinding) -> bool:
    """Check the recorded project directory and the link itself, including dangling links."""

    link = binding.project_home_link
    if link.parent.name != "homes" or link.parent.resolve() != link.parent:
        raise HermesProfileCleanupError("The recorded Hermes project home directory has changed.")
    if not os.path.lexists(link):
        return False
    _private_directory(link.parent, project_link_parent=True)
    entry = link.lstat()
    if (
        not stat.S_ISLNK(entry.st_mode)
        or entry.st_uid != os.geteuid()
        or Path(os.readlink(link)) != binding.profile_home
    ):
        raise HermesProfileCleanupError(
            "The Hermes project home link no longer points to the recorded profile."
        )
    return True


def unlink_hermes_project_home(binding: HermesProfileBinding) -> bool:
    """Unlink the verified lexical project entry without following its target."""

    if not preview_hermes_project_link(binding):
        return False
    binding.project_home_link.unlink()
    return True
