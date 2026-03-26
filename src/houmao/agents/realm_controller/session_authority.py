"""Manifest-derived gateway attach and control authority helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from houmao.agents.realm_controller.boundary_models import (
    SessionManifestPayloadV3,
    SessionManifestPayloadV4,
)
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.models import BackendKind, CaoParsingMode


@dataclass(frozen=True)
class ManifestGatewayAuthority:
    """Normalized manifest-derived gateway authority for one backend."""

    api_base_url: str | None = None
    managed_agent_ref: str | None = None
    terminal_id: str | None = None
    profile_name: str | None = None
    profile_path: str | None = None
    parsing_mode: CaoParsingMode | None = None
    tmux_window_name: str | None = None

    def require_pair_target(self) -> tuple[str, str]:
        """Return the pair-managed attach target or fail clearly."""

        if self.api_base_url is None or self.managed_agent_ref is None:
            raise SessionManifestError(
                "Manifest-backed pair authority is missing `api_base_url` or `managed_agent_ref`."
            )
        return self.api_base_url, self.managed_agent_ref

    def require_terminal_id(self) -> str:
        """Return the runtime-control terminal id or fail clearly."""

        if self.terminal_id is None:
            raise SessionManifestError(
                "Manifest-backed runtime control authority is missing `terminal_id`."
            )
        return self.terminal_id


@dataclass(frozen=True)
class ManifestSessionAuthority:
    """Normalized manifest-derived authority for one tmux-backed session."""

    manifest_path: Path
    backend: BackendKind
    tool: str
    tmux_session_name: str | None
    agent_name: str | None
    agent_id: str | None
    attach: ManifestGatewayAuthority
    control: ManifestGatewayAuthority


def resolve_manifest_session_authority(
    *,
    manifest_path: Path,
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
) -> ManifestSessionAuthority:
    """Normalize gateway attach and control authority from one parsed manifest."""

    if payload.backend == "cao_rest":
        if payload.cao is None:
            raise SessionManifestError(
                f"Manifest `{manifest_path}` is missing `cao` authority for backend `cao_rest`."
            )
        authority = ManifestGatewayAuthority(
            api_base_url=payload.cao.api_base_url,
            terminal_id=payload.cao.terminal_id,
            profile_name=payload.cao.profile_name,
            profile_path=payload.cao.profile_path,
            parsing_mode=payload.cao.parsing_mode,
            tmux_window_name=payload.cao.tmux_window_name,
        )
    elif payload.backend == "houmao_server_rest":
        if payload.houmao_server is None:
            raise SessionManifestError(
                "Manifest "
                f"`{manifest_path}` is missing `houmao_server` authority for backend "
                "`houmao_server_rest`."
            )
        authority = ManifestGatewayAuthority(
            api_base_url=payload.houmao_server.api_base_url,
            managed_agent_ref=payload.houmao_server.session_name,
            terminal_id=payload.houmao_server.terminal_id,
            parsing_mode=payload.houmao_server.parsing_mode,
            tmux_window_name=payload.houmao_server.tmux_window_name,
        )
    else:
        authority = ManifestGatewayAuthority()

    return ManifestSessionAuthority(
        manifest_path=manifest_path.resolve(),
        backend=payload.backend,
        tool=payload.tool,
        tmux_session_name=payload.tmux_session_name,
        agent_name=payload.agent_name,
        agent_id=payload.agent_id,
        attach=authority,
        control=authority,
    )
