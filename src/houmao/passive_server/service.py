"""Core service for the passive server."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import RegistryDiscoveryService
from houmao.passive_server.models import (
    DiscoveredAgentConflictResponse,
    DiscoveredAgentListResponse,
    DiscoveredAgentSummary,
    PassiveCurrentInstance,
    PassiveHealthResponse,
)


class PassiveServerService:
    """Passive-server lifecycle and request handling.

    This service owns startup/shutdown bookkeeping, discovery integration,
    and the methods backing the server's HTTP endpoints.
    """

    def __init__(self, config: PassiveServerConfig) -> None:
        self.m_config = config
        self.m_started_at_utc: str = ""
        self.m_discovery = RegistryDiscoveryService(config)

    # -- lifecycle ------------------------------------------------------------

    def startup(self) -> None:
        """Create directories, write the on-disk marker, and start discovery."""

        self.m_started_at_utc = datetime.now(UTC).isoformat(timespec="seconds")
        self.m_config.run_dir.mkdir(parents=True, exist_ok=True)
        self._write_current_instance()
        self.m_discovery.start()

    def shutdown(self) -> None:
        """Stop discovery and remove the on-disk current-instance marker."""

        self.m_discovery.stop()
        try:
            self.m_config.current_instance_path.unlink(missing_ok=True)
        except OSError:
            pass

    # -- endpoint helpers -----------------------------------------------------

    def health(self) -> PassiveHealthResponse:
        """Build the health response payload."""

        return PassiveHealthResponse()

    def current_instance(self) -> PassiveCurrentInstance:
        """Build the current-instance response payload."""

        return PassiveCurrentInstance(
            pid=os.getpid(),
            api_base_url=self.m_config.api_base_url,
            server_root=str(self.m_config.server_root),
            started_at_utc=self.m_started_at_utc,
        )

    def list_agents(self) -> DiscoveredAgentListResponse:
        """Return all discovered agents."""

        agents = self.m_discovery.index.list_all()
        return DiscoveredAgentListResponse(agents=[a.summary for a in agents])

    def resolve_agent(
        self, agent_ref: str
    ) -> DiscoveredAgentSummary | DiscoveredAgentConflictResponse | None:
        """Resolve one agent by id or name.

        Returns:
            ``DiscoveredAgentSummary`` on unique match,
            ``DiscoveredAgentConflictResponse`` on ambiguous name,
            ``None`` on not-found.
        """

        by_id = self.m_discovery.index.get_by_id(agent_ref)
        if by_id is not None:
            return by_id.summary

        by_name = self.m_discovery.index.get_by_name(agent_ref)
        if len(by_name) == 1:
            return by_name[0].summary
        if len(by_name) > 1:
            ids = [a.record.agent_id for a in by_name]
            return DiscoveredAgentConflictResponse(
                detail=f"Ambiguous agent name: {len(by_name)} agents share this name. "
                f"Disambiguate by agent_id.",
                agent_ids=ids,
            )
        return None

    def request_shutdown(self) -> None:
        """Schedule a deferred SIGTERM to allow the response to flush."""

        import signal
        import threading

        def _deferred() -> None:
            import time

            time.sleep(0.1)
            os.kill(os.getpid(), signal.SIGTERM)

        threading.Thread(target=_deferred, daemon=True).start()

    # -- internal -------------------------------------------------------------

    def _write_current_instance(self) -> None:
        """Persist the current-instance payload to disk."""

        payload = self.current_instance().model_dump(mode="json")
        self.m_config.current_instance_path.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
