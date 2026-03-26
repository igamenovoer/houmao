"""Core service for the passive server."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import (
    GatewayClient,
    GatewayEndpoint,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayMailActionResponseV1,
    GatewayMailCheckRequestV1,
    GatewayMailCheckResponseV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    GatewayMailStatusV1,
    GatewayRequestCreateV1,
    GatewayStatusV1,
)
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent, RegistryDiscoveryService
from houmao.passive_server.models import (
    AgentTuiDetailResponse,
    AgentTuiHistoryResponse,
    AgentTuiStateResponse,
    DiscoveredAgentConflictResponse,
    DiscoveredAgentListResponse,
    DiscoveredAgentSummary,
    PassiveCurrentInstance,
    PassiveHealthResponse,
)
from houmao.passive_server.observation import TuiObservationService


class PassiveServerService:
    """Passive-server lifecycle and request handling.

    This service owns startup/shutdown bookkeeping, discovery integration,
    and the methods backing the server's HTTP endpoints.
    """

    def __init__(self, config: PassiveServerConfig) -> None:
        self.m_config = config
        self.m_started_at_utc: str = ""
        self.m_discovery = RegistryDiscoveryService(config)
        self.m_observation = TuiObservationService(discovery=self.m_discovery, config=config)

    # -- lifecycle ------------------------------------------------------------

    def startup(self) -> None:
        """Create directories, write the on-disk marker, and start discovery."""

        self.m_started_at_utc = datetime.now(UTC).isoformat(timespec="seconds")
        self.m_config.run_dir.mkdir(parents=True, exist_ok=True)
        self._write_current_instance()
        self.m_discovery.start()
        self.m_observation.start()

    def shutdown(self) -> None:
        """Stop observation, discovery, and remove the on-disk current-instance marker."""

        self.m_observation.stop()
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

    # -- gateway proxy --------------------------------------------------------

    def _resolve_agent_or_error(
        self, agent_ref: str
    ) -> DiscoveredAgent | tuple[int, dict[str, Any]]:
        """Resolve an agent by id or name, returning an error tuple on failure."""

        by_id = self.m_discovery.index.get_by_id(agent_ref)
        if by_id is not None:
            return by_id

        by_name = self.m_discovery.index.get_by_name(agent_ref)
        if len(by_name) == 1:
            return by_name[0]
        if len(by_name) > 1:
            ids = [a.record.agent_id for a in by_name]
            return (
                409,
                DiscoveredAgentConflictResponse(
                    detail=f"Ambiguous agent name: {len(by_name)} agents share this name. "
                    f"Disambiguate by agent_id.",
                    agent_ids=ids,
                ).model_dump(mode="json"),
            )
        return (404, {"detail": f"Agent not found: {agent_ref}"})

    def _gateway_client_for_agent(self, agent: DiscoveredAgent) -> GatewayClient | None:
        """Build a ``GatewayClient`` from the agent's registry record, or ``None``."""

        gw = agent.record.gateway
        if gw is None or gw.host is None or gw.port is None:
            return None
        return GatewayClient(endpoint=GatewayEndpoint(host=gw.host, port=gw.port))

    def gateway_status(self, agent_ref: str) -> GatewayStatusV1 | tuple[int, dict[str, Any]]:
        """Proxy ``GET /v1/status`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.status()
        except GatewayHttpError as exc:
            return (502, {"detail": exc.detail})

    def gateway_create_request(
        self, agent_ref: str, payload: GatewayRequestCreateV1
    ) -> GatewayAcceptedRequestV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/requests`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.create_request(payload)
        except GatewayHttpError as exc:
            return (502, {"detail": exc.detail})

    def gateway_mail_status(
        self, agent_ref: str
    ) -> GatewayMailStatusV1 | tuple[int, dict[str, Any]]:
        """Proxy ``GET /v1/mail/status`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.mail_status()
        except GatewayHttpError as exc:
            return (502, {"detail": exc.detail})

    def gateway_mail_check(
        self, agent_ref: str, payload: GatewayMailCheckRequestV1
    ) -> GatewayMailCheckResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/mail/check`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.check_mail(payload)
        except GatewayHttpError as exc:
            return (502, {"detail": exc.detail})

    def gateway_mail_send(
        self, agent_ref: str, payload: GatewayMailSendRequestV1
    ) -> GatewayMailActionResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/mail/send`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.send_mail(payload)
        except GatewayHttpError as exc:
            return (502, {"detail": exc.detail})

    def gateway_mail_reply(
        self, agent_ref: str, payload: GatewayMailReplyRequestV1
    ) -> GatewayMailActionResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/mail/reply`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.reply_mail(payload)
        except GatewayHttpError as exc:
            return (502, {"detail": exc.detail})

    # -- agent TUI observation --------------------------------------------------

    def agent_state(self, agent_ref: str) -> AgentTuiStateResponse | tuple[int, dict[str, Any]]:
        """Return compact observation state for an agent."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        observer = self.m_observation.get_observer(resolved.record.agent_id)
        if observer is None:
            return (503, {"detail": "Observer not yet initialized for this agent"})
        return observer.current_state()

    def agent_state_detail(
        self, agent_ref: str
    ) -> AgentTuiDetailResponse | tuple[int, dict[str, Any]]:
        """Return detailed observation state for an agent."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        observer = self.m_observation.get_observer(resolved.record.agent_id)
        if observer is None:
            return (503, {"detail": "Observer not yet initialized for this agent"})
        return observer.current_detail()

    def agent_history(
        self, agent_ref: str, limit: int = 50
    ) -> AgentTuiHistoryResponse | tuple[int, dict[str, Any]]:
        """Return recent state transitions for an agent."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        observer = self.m_observation.get_observer(resolved.record.agent_id)
        if observer is None:
            return (503, {"detail": "Observer not yet initialized for this agent"})
        return observer.history(limit=limit)

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
