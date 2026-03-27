"""Registry-driven agent discovery for the passive server."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from houmao.agents.realm_controller.agent_identity import (
    normalize_agent_identity_name,
    normalize_managed_agent_name,
)
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.registry_models import LiveAgentRegistryRecordV2
from houmao.agents.realm_controller.registry_storage import (
    global_registry_paths,
    is_live_agent_record_fresh,
)
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.models import DiscoveredAgentSummary

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscoveredAgent:
    """One validated, fresh, tmux-live agent in the index."""

    record: LiveAgentRegistryRecordV2
    summary: DiscoveredAgentSummary


class DiscoveredAgentIndex:
    """Thread-safe in-memory index of discovered agents.

    Keyed by ``agent_id`` with name-based secondary lookup.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._agents: dict[str, DiscoveredAgent] = {}

    def get_by_id(self, agent_id: str) -> DiscoveredAgent | None:
        """Return the agent matching ``agent_id``, or ``None``."""

        with self._lock:
            return self._agents.get(agent_id)

    def get_by_name(self, agent_name: str) -> list[DiscoveredAgent]:
        """Return all agents matching the canonical ``agent_name``."""

        requested_aliases = _normalized_agent_name_aliases(agent_name)
        if not requested_aliases:
            return []
        with self._lock:
            return [
                agent
                for agent in self._agents.values()
                if requested_aliases & _normalized_agent_name_aliases(agent.record.agent_name)
            ]

    def list_all(self) -> list[DiscoveredAgent]:
        """Return all discovered agents sorted by ``agent_name``."""

        with self._lock:
            return sorted(self._agents.values(), key=lambda a: a.record.agent_name)

    def replace(self, agents: dict[str, DiscoveredAgent]) -> None:
        """Atomically replace the entire index."""

        with self._lock:
            self._agents = dict(agents)


def _summary_from_record(record: LiveAgentRegistryRecordV2) -> DiscoveredAgentSummary:
    """Project a registry record into a ``DiscoveredAgentSummary``."""

    has_gateway = (
        record.gateway is not None
        and record.gateway.host is not None
        and record.gateway.port is not None
    )
    has_mailbox = record.mailbox is not None

    return DiscoveredAgentSummary(
        agent_id=record.agent_id,
        agent_name=record.agent_name,
        generation_id=record.generation_id,
        tool=record.identity.tool,
        backend=record.identity.backend,
        tmux_session_name=record.terminal.session_name,
        manifest_path=record.runtime.manifest_path,
        session_root=record.runtime.session_root or "",
        has_gateway=has_gateway,
        has_mailbox=has_mailbox,
        published_at=record.published_at,
        lease_expires_at=record.lease_expires_at,
    )


def _get_live_tmux_session_names() -> set[str] | None:
    """Return the set of live tmux session names, or ``None`` if tmux is unavailable."""

    try:
        import libtmux

        server = libtmux.Server()
        return {session.name for session in server.sessions if session.name is not None}
    except Exception:
        return None


def _normalized_agent_name_aliases(value: str) -> set[str]:
    """Return compatible managed-agent name aliases for lookup."""

    aliases: set[str] = set()
    try:
        aliases.add(normalize_managed_agent_name(value))
    except SessionManifestError:
        pass
    try:
        aliases.add(normalize_agent_identity_name(value).name_portion)
    except SessionManifestError:
        pass
    return aliases


class RegistryDiscoveryService:
    """Periodically scans the shared registry and maintains a ``DiscoveredAgentIndex``."""

    def __init__(self, config: PassiveServerConfig) -> None:
        self.m_config = config
        self.m_index = DiscoveredAgentIndex()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def index(self) -> DiscoveredAgentIndex:
        """Return the current agent index."""

        return self.m_index

    def start(self) -> None:
        """Start the background polling thread."""

        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="discovery-poll")
        self._thread.start()

    def stop(self) -> None:
        """Stop the background polling thread."""

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10.0)
            self._thread = None

    def scan_once(self) -> None:
        """Run a single scan cycle (useful for testing and startup)."""

        self._run_scan()

    def _poll_loop(self) -> None:
        """Background loop: scan, sleep, repeat until stopped."""

        while not self._stop_event.is_set():
            try:
                self._run_scan()
            except Exception:
                logger.exception("Discovery scan failed")
            self._stop_event.wait(timeout=self.m_config.discovery_poll_interval_seconds)

    def _run_scan(self) -> None:
        """Scan the registry, verify tmux liveness, and rebuild the index."""

        live_sessions = _get_live_tmux_session_names()
        if live_sessions is None:
            logger.warning("Tmux server unreachable — discovery index will be empty this cycle")
            self.m_index.replace({})
            return

        paths = global_registry_paths()
        if not paths.live_agents_dir.exists():
            self.m_index.replace({})
            return

        new_agents: dict[str, DiscoveredAgent] = {}
        for candidate_dir in sorted(paths.live_agents_dir.iterdir()):
            if not candidate_dir.is_dir():
                continue
            record_path = candidate_dir / "record.json"
            if not record_path.is_file():
                continue

            record = self._load_and_validate(record_path)
            if record is None:
                continue
            if not is_live_agent_record_fresh(record):
                continue
            if record.terminal.session_name not in live_sessions:
                continue

            summary = _summary_from_record(record)
            new_agents[record.agent_id] = DiscoveredAgent(record=record, summary=summary)

        self.m_index.replace(new_agents)

    @staticmethod
    def _load_and_validate(path: Path) -> LiveAgentRegistryRecordV2 | None:
        """Load one record, returning ``None`` on any parse/validation error."""

        import json

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return LiveAgentRegistryRecordV2.model_validate(payload)
        except (json.JSONDecodeError, Exception):
            logger.debug("Skipping invalid registry record: %s", path)
            return None
