"""Project managed-agent identity from its verified runtime manifest."""

from pathlib import Path

from houmao.agents.realm_controller.backends.tmux_runtime import HEADLESS_AGENT_WINDOW_NAME
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.server.models import HoumaoManagedAgentIdentity


def tmux_window_name_from_manifest(
    payload: SessionManifestPayloadV4, *, default: str | None
) -> str | None:
    """Return the window name captured in the runtime's committed state."""

    if payload.tmux is not None and payload.tmux.primary_window_name:
        return payload.tmux.primary_window_name
    if payload.interactive is not None and payload.interactive.tmux_window_name:
        return payload.interactive.tmux_window_name
    backend_window = payload.backend_state.get("tmux_window_name")
    if isinstance(backend_window, str) and backend_window.strip():
        return backend_window.strip()
    return default


def identity_from_manifest(
    path: Path, payload: SessionManifestPayloadV4
) -> HoumaoManagedAgentIdentity:
    """Return the maintained identity fields without opening files or querying the owner."""

    binding = payload.runtime.execution_binding
    return HoumaoManagedAgentIdentity(
        tracked_agent_id=payload.agent_id,
        transport=payload.mode,
        mode=payload.mode,
        backend=payload.backend,
        native_surface=payload.native_surface,
        tool=payload.tool,
        session_name=payload.tmux_session_name if payload.mode == "tui" else None,
        runtime_session_id=payload.runtime.session_id
        if payload.mode == "web"
        else path.parent.name,
        tmux_session_name=payload.tmux_session_name,
        tmux_window_name=tmux_window_name_from_manifest(
            payload,
            default=(
                HEADLESS_AGENT_WINDOW_NAME
                if payload.mode == "headless" or payload.backend == "local_interactive"
                else None
            ),
        ),
        manifest_path=str(path),
        session_root=str(path.parent),
        agent_name=payload.agent_name,
        agent_id=payload.agent_id,
        management_kind="local_lifecycle",
        lifecycle_owner="local",
        execution_context=binding,
        execution_status="available" if binding is not None else None,
    )
