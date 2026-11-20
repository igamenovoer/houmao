"""Resolve the caller's runtime manifest using read-only ownership checks."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from houmao.agents.realm_controller.agent_identity import (
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    SELF_TMUX_SESSION_ENV_VAR,
    SELF_TMUX_SOCKET_ENV_VAR,
)
from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.backends.dsh_acp_connection import _read_process_lineage
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    read_tmux_session_environment_value,
    run_tmux,
)
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.manifest import (
    default_manifest_path,
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.registry_models import ManagedAgentRegistryRecordV3
from houmao.agents.realm_controller.registry_storage import (
    is_managed_agent_record_active,
    load_managed_agent_record_by_agent_id,
)
from houmao.execution.context import current_execution_binding, validate_execution_owner
from houmao.execution.tmux import tmux_server_scope, validate_tmux_socket_path
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR


@dataclass(frozen=True)
class VerifiedSelfManifest:
    """One current runtime manifest and the live record that verified its owner."""

    path: Path
    payload: SessionManifestPayloadV4
    record: ManagedAgentRegistryRecordV3

    @property
    def manifest_path(self) -> Path:
        """Return the manifest path for shared runtime consumers."""

        return self.path

    @property
    def agent_id(self) -> str:
        """Return the authoritative agent ID."""

        return self.payload.agent_id


def resolve_self_manifest() -> VerifiedSelfManifest:
    """Read the manifest bound to the caller and verify its live registry generation."""

    try:
        return _resolve_self_manifest()
    except (OSError, SessionManifestError, TmuxCommandError) as exc:
        raise ValueError(f"Cannot verify the current managed runtime: {exc}") from exc


def _resolve_self_manifest() -> VerifiedSelfManifest:
    """Select the current runtime and validate its saved authority."""

    owner = _self_tmux_session()
    published_agent_id = None
    if owner is None:
        pointer = os.environ.get(AGENT_MANIFEST_PATH_ENV_VAR)
    else:
        socket, session = owner
        target = f"={session}"
        with tmux_server_scope(socket):
            pointer = read_tmux_session_environment_value(
                session_name=target, variable_name=AGENT_MANIFEST_PATH_ENV_VAR
            )
            published_agent_id = read_tmux_session_environment_value(
                session_name=target, variable_name=AGENT_ID_ENV_VAR
            )
        if pointer is None and published_agent_id is not None:
            admitted = current_execution_binding()
            registry_env = (
                {HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: admitted.registry_root} if admitted else None
            )
            record = load_managed_agent_record_by_agent_id(published_agent_id, env=registry_env)
            if record is not None:
                pointer = record.runtime.manifest_path

    if not pointer:
        raise ValueError("Self commands require the manifest of the current managed runtime.")
    path = Path(pointer)
    if (
        not path.is_absolute()
        or path.name != "manifest.json"
        or path.resolve() != path
        or not path.is_file()
    ):
        raise ValueError("The self locator must identify a confined runtime manifest.")

    handle = load_session_manifest(path)
    payload = parse_session_manifest_payload(handle.payload, source=str(path))
    binding = payload.runtime.execution_binding
    if binding is None:
        raise ValueError("The self manifest is missing its execution binding.")
    if path != default_manifest_path(Path(binding.runtime_root), payload.backend, path.parent.name):
        raise ValueError("The self manifest is outside the owning runtime's session directory.")
    validate_execution_owner(binding)

    record = load_managed_agent_record_by_agent_id(
        payload.agent_id, env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: binding.registry_root}
    )
    if record is None or not is_managed_agent_record_active(record):
        raise ValueError("The self manifest requires a current live registry record.")
    if record.generation_id != payload.registry_generation_id:
        raise ValueError("The self manifest uses a stale registry generation.")
    if (
        Path(record.runtime.manifest_path) != path
        or record.agent_id != payload.agent_id
        or record.execution_binding != binding
        or record.mode != payload.mode
        or record.identity.backend != payload.backend
        or record.identity.tool != payload.tool
        or record.native_surface != payload.native_surface
        or published_agent_id is not None
        and published_agent_id != payload.agent_id
    ):
        raise ValueError("The self manifest does not match the current managed runtime.")

    registry_tmux = record.terminal.socket_path, record.terminal.current_session_name
    if (
        payload.tmux is not None
        and (
            payload.tmux.socket_path,
            payload.tmux.session_name,
        )
        != registry_tmux
    ):
        raise ValueError("The self manifest tmux binding does not match the live registry record.")
    if owner is None and payload.mode != "headless":
        raise ValueError("Self lookup requires the owning tmux socket and session.")
    if owner is not None and (payload.tmux is None or owner != registry_tmux):
        raise ValueError("The self manifest does not match the owning tmux socket and session.")

    if os.environ.get(SELF_TMUX_SOCKET_ENV_VAR):
        _require_web_caller(payload)
    return VerifiedSelfManifest(path=path, payload=payload, record=record)


def _self_tmux_session() -> tuple[str, str] | None:
    """Select the owning server and session without tmux's last-active fallback."""

    socket_hint = os.environ.get(SELF_TMUX_SOCKET_ENV_VAR)
    session_hint = os.environ.get(SELF_TMUX_SESSION_ENV_VAR)
    if socket_hint or session_hint:
        if not socket_hint or not session_hint:
            raise ValueError("The Web tool context requires both its tmux socket and session.")
        return validate_tmux_socket_path(socket_hint), session_hint

    inherited = os.environ.get("TMUX")
    if not inherited:
        return None
    parts = inherited.rsplit(",", 2)
    if len(parts) != 3 or not all(part.isascii() and part.isdigit() for part in parts[1:]):
        raise ValueError("The current tmux context is malformed.")
    socket = validate_tmux_socket_path(parts[0])
    with tmux_server_scope(socket):
        result = run_tmux(["display-message", "-p", "-t", f"${parts[2]}:", "#{session_name}"])
    session = result.stdout.strip()
    if result.returncode != 0 or not session:
        raise ValueError("Cannot find the caller's current managed tmux session.")
    return socket, session


def _require_web_caller(payload: SessionManifestPayloadV4) -> None:
    """Verify that detached context belongs to the captured native Web process."""

    pid = payload.backend_state.get("native_pid")
    birth = payload.backend_state.get("native_birth_token")
    if (
        payload.mode != "web"
        or type(pid) is not int
        or pid <= 0
        or not isinstance(birth, str)
        or _dispatch_origin_birth_token(pid) != birth
    ):
        raise ValueError("The self locator does not identify a current native Web owner.")

    if os.getsid(0) == pid:
        return
    current = os.getpid()
    # Detached tool runners may lead a child process group of their own.
    while current > 1:
        if current == pid:
            return
        lineage = _read_process_lineage(current)
        if lineage is None or lineage[0] == current:
            break
        current = lineage[0]
    raise ValueError("The caller does not belong to the managed native Web process.")
