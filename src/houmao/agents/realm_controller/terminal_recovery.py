"""Validate selected tmux authority before terminal recovery."""

from __future__ import annotations

from pathlib import Path

from houmao.agents.realm_controller.agent_identity import (
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxBackedAuthorityHealth,
    read_tmux_session_environment_value,
)
from houmao.agents.realm_controller.boundary_models import (
    SessionManifestPayloadV4,
    SessionManifestTmuxSectionV1,
)
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.manifest import validate_registry_mode_authority
from houmao.agents.realm_controller.registry_models import ManagedAgentRegistryRecordV3
from houmao.execution.context import require_owner_tmux_socket
from houmao.execution.tmux import TmuxCommandError, tmux_server_scope


class OwnerTerminalInspectionUnavailable(SessionManifestError):
    """The selected agent's recorded terminal could not be verified."""


def terminal_inspection_unavailable(
    record: ManagedAgentRegistryRecordV3, reason: str | TmuxCommandError
) -> OwnerTerminalInspectionUnavailable:
    """Report a safe reason and where the operator can verify it."""

    if isinstance(reason, TmuxCommandError):
        reason = (
            f"The terminal query exited with status {reason.returncode}"
            if reason.returncode is not None
            else "The terminal query did not complete"
        )
    return OwnerTerminalInspectionUnavailable(
        f"Owner terminal inspection unavailable for `{record.agent_name}` "
        f"(`{record.agent_id}`) on its recorded tmux socket. {reason.rstrip('.')}. "
        "Verify the session from the recorded execution owner and retry."
    )


def recorded_tmux_binding(
    record: ManagedAgentRegistryRecordV3, manifest: SessionManifestPayloadV4 | None
) -> SessionManifestTmuxSectionV1:
    """Select the current agent's terminal using saved authority."""

    name = record.terminal.session_name
    socket = record.terminal.socket_path
    tmux = None
    if manifest is not None:
        validate_registry_mode_authority(record, manifest)
        tmux = manifest.tmux
        if (
            tmux is None
            or name != tmux.session_name
            or (socket is not None and socket != tmux.socket_path)
        ):
            raise SessionManifestError("Registry and manifest tmux authority differ")
        socket = tmux.socket_path
    try:
        socket = require_owner_tmux_socket(record.execution_binding, socket)
    except (ValueError, OSError) as exc:
        raise terminal_inspection_unavailable(
            record, "The recorded owner route is unavailable"
        ) from exc
    if not name:
        raise terminal_inspection_unavailable(record, "No tmux session name is recorded")
    return tmux or SessionManifestTmuxSectionV1(session_name=name, socket_path=socket)


def require_same_recovery_record(
    selected: ManagedAgentRegistryRecordV3, current: ManagedAgentRegistryRecordV3 | None
) -> None:
    """Fence recovery to the same generation, runtime, terminal, and lifecycle."""

    if (
        current is None
        or current.agent_id != selected.agent_id
        or current.generation_id != selected.generation_id
        or current.identity != selected.identity
        or current.mode != selected.mode
        or current.runtime != selected.runtime
        or current.execution_binding != selected.execution_binding
        or current.terminal != selected.terminal
        or current.lifecycle.state != selected.lifecycle.state
    ):
        raise SessionManifestError(
            "Shared-registry generation or owner authority changed before recovery for "
            f"`{selected.agent_id}`. Retry the command against the current record."
        )


def require_same_recovery_manifest(
    previous: SessionManifestPayloadV4 | None, current: SessionManifestPayloadV4 | None
) -> None:
    """Fence a terminal mutation to the observed runtime and its primary binding."""

    if previous is None and current is None:
        return
    if (
        previous is None
        or current is None
        or current.agent_id != previous.agent_id
        or current.tool != previous.tool
        or current.backend != previous.backend
        or current.mode != previous.mode
        or current.registry_generation_id != previous.registry_generation_id
        or current.runtime.session_id != previous.runtime.session_id
        or current.runtime.execution_binding != previous.runtime.execution_binding
        or current.tmux != previous.tmux
    ):
        raise SessionManifestError(
            "Runtime manifest generation or owner authority changed before recovery. "
            "Retry the command against the current record."
        )


def require_owned_degraded_tmux_session(
    record: ManagedAgentRegistryRecordV3,
    binding: SessionManifestTmuxSectionV1,
    observation: TmuxBackedAuthorityHealth,
) -> str:
    """Verify the observed remnant still identifies the selected managed agent."""

    session_id = observation.session_id
    if binding.socket_path is None or session_id is None:
        raise terminal_inspection_unavailable(record, "The observed session has no exact handle")
    try:
        with tmux_server_scope(binding.socket_path):
            agent_id = read_tmux_session_environment_value(
                session_name=binding.session_name,
                session_id=session_id,
                variable_name=AGENT_ID_ENV_VAR,
            )
            manifest_path = read_tmux_session_environment_value(
                session_name=binding.session_name,
                session_id=session_id,
                variable_name=AGENT_MANIFEST_PATH_ENV_VAR,
            )
    except TmuxCommandError as exc:
        raise terminal_inspection_unavailable(
            record, "Could not verify the observed session's managed identity"
        ) from exc
    if agent_id != record.agent_id or manifest_path != str(
        Path(record.runtime.manifest_path).resolve()
    ):
        raise terminal_inspection_unavailable(
            record, "The observed session's managed identity differs from the selected record"
        )
    return session_id
