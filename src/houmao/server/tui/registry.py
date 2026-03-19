"""Known-session registry loading for the server-owned TUI tracker."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    runtime_owned_session_root_from_manifest_path,
)
from houmao.agents.realm_controller.registry_models import LiveAgentRegistryRecordV2
from houmao.agents.realm_controller.registry_storage import (
    resolve_live_agent_record,
    resolve_live_agent_record_by_agent_id,
)
from houmao.agents.realm_controller.backends.tmux_runtime import list_tmux_sessions
from houmao.server.config import HoumaoServerConfig
from houmao.server.models import HoumaoRegisterLaunchRequest, HoumaoTrackedSessionIdentity


@dataclass(frozen=True)
class KnownSessionRecord:
    """One live known-session entry admitted into server tracking."""

    tracked_session_id: str
    session_name: str
    tool: str
    terminal_id: str
    tmux_session_name: str
    tmux_window_name: str | None
    manifest_path: Path | None
    session_root: Path | None
    agent_name: str | None
    agent_id: str | None

    def to_identity(self) -> HoumaoTrackedSessionIdentity:
        """Return the public tracked-session identity model."""

        return HoumaoTrackedSessionIdentity(
            tracked_session_id=self.tracked_session_id,
            session_name=self.session_name,
            tool=self.tool,
            tmux_session_name=self.tmux_session_name,
            tmux_window_name=self.tmux_window_name,
            terminal_aliases=(self.terminal_id,),
            agent_name=self.agent_name,
            agent_id=self.agent_id,
            manifest_path=str(self.manifest_path) if self.manifest_path is not None else None,
            session_root=str(self.session_root) if self.session_root is not None else None,
        )


class KnownSessionRegistry:
    """Load live known-session entries from server-owned registration records."""

    def __init__(self, *, config: HoumaoServerConfig) -> None:
        """Initialize the registry loader."""

        self.m_config = config

    def load_live_sessions(self) -> dict[str, KnownSessionRecord]:
        """Return live known sessions verified against current tmux liveness."""

        live_tmux_sessions = list_tmux_sessions()
        records: dict[str, KnownSessionRecord] = {}
        if not self.m_config.sessions_dir.exists():
            return records

        for registration_path in sorted(self.m_config.sessions_dir.glob("*/registration.json")):
            record = self._load_record(
                registration_path=registration_path.resolve(),
                live_tmux_sessions=live_tmux_sessions,
            )
            if record is None:
                continue
            records[record.tracked_session_id] = record
        return records

    def _load_record(
        self,
        *,
        registration_path: Path,
        live_tmux_sessions: set[str],
    ) -> KnownSessionRecord | None:
        """Load and enrich one registration-backed known-session entry."""

        try:
            payload = json.loads(registration_path.read_text(encoding="utf-8"))
            registration = HoumaoRegisterLaunchRequest.model_validate(payload)
        except Exception:
            return None
        return known_session_record_from_registration(
            registration=registration,
            live_tmux_sessions=live_tmux_sessions,
            allow_shared_registry_enrichment=True,
        )

    @staticmethod
    def _shared_registry_record(
        *,
        agent_id: str | None,
        agent_name: str | None,
    ) -> LiveAgentRegistryRecordV2 | None:
        """Return optional shared-registry evidence for enrichment only."""

        if agent_id is not None:
            return resolve_live_agent_record_by_agent_id(agent_id)
        if agent_name is not None:
            return resolve_live_agent_record(agent_name)
        return None


def known_session_record_from_registration(
    *,
    registration: HoumaoRegisterLaunchRequest,
    live_tmux_sessions: set[str] | None = None,
    allow_shared_registry_enrichment: bool,
) -> KnownSessionRecord | None:
    """Build one known-session record from a registration payload."""

    manifest_path = _optional_path(registration.manifest_path)
    session_root = _optional_path(registration.session_root)
    agent_name = registration.agent_name
    agent_id = registration.agent_id
    terminal_id = registration.terminal_id
    tmux_session_name = registration.tmux_session_name or registration.session_name
    tmux_window_name = registration.tmux_window_name
    tool = registration.tool

    if allow_shared_registry_enrichment:
        shared_registry_record = KnownSessionRegistry._shared_registry_record(
            agent_id=agent_id,
            agent_name=agent_name,
        )
        if shared_registry_record is not None:
            if manifest_path is None:
                manifest_path = _optional_path(shared_registry_record.runtime.manifest_path)
            if session_root is None:
                session_root = _optional_path(shared_registry_record.runtime.session_root)
            if agent_name is None:
                agent_name = shared_registry_record.agent_name
            if agent_id is None:
                agent_id = shared_registry_record.agent_id
            if not tmux_session_name.strip():
                tmux_session_name = shared_registry_record.terminal.session_name

    if manifest_path is not None and manifest_path.is_file():
        manifest_metadata = _load_manifest_metadata(manifest_path=manifest_path)
        terminal_id = terminal_id or manifest_metadata.terminal_id
        tmux_window_name = tmux_window_name or manifest_metadata.tmux_window_name
        tmux_session_name = manifest_metadata.tmux_session_name or tmux_session_name
        tool = manifest_metadata.tool or tool
        if session_root is None:
            session_root = manifest_metadata.session_root

    if terminal_id is None or not terminal_id.strip():
        return None
    if live_tmux_sessions is not None and tmux_session_name not in live_tmux_sessions:
        return None

    return KnownSessionRecord(
        tracked_session_id=registration.session_name,
        session_name=registration.session_name,
        tool=tool,
        terminal_id=terminal_id,
        tmux_session_name=tmux_session_name,
        tmux_window_name=tmux_window_name,
        manifest_path=manifest_path,
        session_root=session_root,
        agent_name=agent_name,
        agent_id=agent_id,
    )


@dataclass(frozen=True)
class _ManifestMetadata:
    """Manifest-backed enrichment values for a tracked session."""

    tool: str | None
    terminal_id: str | None
    tmux_session_name: str | None
    tmux_window_name: str | None
    session_root: Path | None


def _load_manifest_metadata(*, manifest_path: Path) -> _ManifestMetadata:
    """Return manifest-backed metadata used to enrich one registration."""

    try:
        handle = load_session_manifest(manifest_path)
    except Exception:
        return _ManifestMetadata(
            tool=None,
            terminal_id=None,
            tmux_session_name=None,
            tmux_window_name=None,
            session_root=None,
        )

    payload = handle.payload
    tool = _optional_string(payload.get("tool"))
    backend_state = payload.get("backend_state")
    tmux_session_name: str | None = None
    if isinstance(backend_state, dict):
        tmux_session_name = _optional_string(backend_state.get("tmux_session_name"))

    terminal_id: str | None = None
    tmux_window_name: str | None = None
    for section_key in ("houmao_server", "cao"):
        section = payload.get(section_key)
        if not isinstance(section, dict):
            continue
        terminal_id = terminal_id or _optional_string(section.get("terminal_id"))
        tmux_window_name = tmux_window_name or _optional_string(section.get("tmux_window_name"))
        tmux_session_name = tmux_session_name or _optional_string(section.get("session_name"))

    return _ManifestMetadata(
        tool=tool,
        terminal_id=terminal_id,
        tmux_session_name=tmux_session_name,
        tmux_window_name=tmux_window_name,
        session_root=runtime_owned_session_root_from_manifest_path(manifest_path),
    )


def _optional_path(value: str | None) -> Path | None:
    """Return one resolved optional path."""

    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return Path(stripped).expanduser().resolve()


def _optional_string(value: object) -> str | None:
    """Return one normalized optional string."""

    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
