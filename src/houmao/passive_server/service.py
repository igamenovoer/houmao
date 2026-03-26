"""Core service for the passive server."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from houmao.agents.realm_controller.backends.tmux_runtime import (
    kill_tmux_session,
)
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
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.registry_storage import (
    remove_live_agent_record,
)
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent, RegistryDiscoveryService
from houmao.passive_server.headless import HeadlessAgentService
from houmao.passive_server.models import (
    AgentTuiDetailResponse,
    AgentTuiHistoryResponse,
    AgentTuiStateResponse,
    DiscoveredAgentConflictResponse,
    DiscoveredAgentListResponse,
    DiscoveredAgentSummary,
    PassiveAgentActionResponse,
    PassiveCurrentInstance,
    PassiveHeadlessLaunchRequest,
    PassiveHeadlessLaunchResponse,
    PassiveHeadlessTurnAcceptedResponse,
    PassiveHeadlessTurnEventsResponse,
    PassiveHeadlessTurnRequest,
    PassiveHeadlessTurnStatusResponse,
    PassiveHealthResponse,
    PassivePromptRequest,
    PassiveRequestAcceptedResponse,
)
from houmao.passive_server.observation import TuiObservationService

log = logging.getLogger(__name__)


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
        self.m_headless = HeadlessAgentService(config)

    # -- lifecycle ------------------------------------------------------------

    def startup(self) -> None:
        """Create directories, write the on-disk marker, and start services."""

        self.m_started_at_utc = datetime.now(UTC).isoformat(timespec="seconds")
        self.m_config.run_dir.mkdir(parents=True, exist_ok=True)
        self._write_current_instance()
        self.m_discovery.start()
        self.m_observation.start()
        self.m_headless.start()

    def shutdown(self) -> None:
        """Stop services and remove the on-disk current-instance marker."""

        self.m_headless.stop()
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

    # -- request submission (Tier 6) -------------------------------------------

    def submit_request(
        self, agent_ref: str, payload: PassivePromptRequest
    ) -> PassiveRequestAcceptedResponse | tuple[int, dict[str, Any]]:
        """Forward a prompt request to the agent's gateway.

        The passive server never does ``tmux send-keys`` directly; requests
        are always mediated by the gateway.  Returns 502 when no gateway is
        attached.
        """

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent — cannot deliver request"})
        try:
            gw_payload = GatewayRequestCreateV1(
                kind="submit_prompt",
                payload=GatewayRequestPayloadSubmitPromptV1(prompt=payload.prompt),
            )
            gw_result = client.create_request(gw_payload)
            return PassiveRequestAcceptedResponse(
                request_id=gw_result.request_id,
                detail="Request forwarded to gateway",
            )
        except GatewayHttpError as exc:
            return (502, {"detail": exc.detail})

    def interrupt_agent(
        self, agent_ref: str
    ) -> PassiveAgentActionResponse | tuple[int, dict[str, Any]]:
        """Interrupt an agent via gateway or, for managed headless, directly."""

        managed_tracked_agent_id, resolved, error = self._resolve_managed_headless_target(agent_ref)
        if error is not None:
            return error
        if managed_tracked_agent_id is not None:
            return self.m_headless.interrupt_managed(managed_tracked_agent_id)
        if resolved is None:
            return (404, {"detail": f"Agent not found: {agent_ref}"})

        agent_id = resolved.record.agent_id

        # Otherwise try gateway
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (
                502,
                {
                    "detail": "No gateway attached and agent is not managed headless — cannot interrupt"
                },
            )
        try:
            gw_payload = GatewayRequestCreateV1(
                kind="interrupt",
                payload=GatewayRequestPayloadInterruptV1(),
            )
            client.create_request(gw_payload)
            return PassiveAgentActionResponse(
                agent_id=agent_id,
                detail="Interrupt forwarded to gateway",
            )
        except GatewayHttpError as exc:
            return (502, {"detail": exc.detail})

    def stop_agent(self, agent_ref: str) -> PassiveAgentActionResponse | tuple[int, dict[str, Any]]:
        """Stop an agent by killing its tmux session and cleaning up.

        For managed headless agents, delegates full cleanup to
        ``HeadlessAgentService``.  For discovered-only agents, performs
        direct tmux kill and registry cleanup.
        """

        managed_tracked_agent_id, resolved, error = self._resolve_managed_headless_target(agent_ref)
        if error is not None:
            return error
        if managed_tracked_agent_id is not None:
            return self.m_headless.stop_managed(managed_tracked_agent_id)
        if resolved is None:
            return (404, {"detail": f"Agent not found: {agent_ref}"})

        agent_id = resolved.record.agent_id

        # Discovered-only agent: kill tmux + clear registry
        tmux_session = resolved.record.terminal.session_name if resolved.record.terminal else None
        if tmux_session:
            try:
                kill_tmux_session(session_name=tmux_session)
            except Exception as exc:
                log.warning("Error killing tmux session %s: %s", tmux_session, exc)

        try:
            remove_live_agent_record(
                agent_id,
                generation_id=resolved.record.generation_id,
            )
        except Exception as exc:
            log.warning("Error clearing registry for %s: %s", agent_id, exc)

        return PassiveAgentActionResponse(
            agent_id=agent_id,
            detail=f"Agent {agent_id} stopped",
        )

    # -- headless management (Tier 7) -----------------------------------------

    def launch_headless(
        self, payload: PassiveHeadlessLaunchRequest
    ) -> PassiveHeadlessLaunchResponse | tuple[int, dict[str, Any]]:
        """Delegate headless launch to ``HeadlessAgentService``."""

        return self.m_headless.launch(payload)

    def submit_turn(
        self, agent_ref: str, payload: PassiveHeadlessTurnRequest
    ) -> PassiveHeadlessTurnAcceptedResponse | tuple[int, dict[str, Any]]:
        """Submit a turn to a managed headless agent."""

        managed_tracked_agent_id, _resolved, error = self._resolve_managed_headless_target(
            agent_ref
        )
        if error is not None:
            return error
        if managed_tracked_agent_id is None:
            return (400, {"detail": f"Agent {agent_ref} is not a managed headless agent"})

        return self.m_headless.submit_turn(managed_tracked_agent_id, payload.prompt)

    def turn_status(
        self, agent_ref: str, turn_id: str
    ) -> PassiveHeadlessTurnStatusResponse | tuple[int, dict[str, Any]]:
        """Return status of a headless turn."""

        managed_tracked_agent_id, _resolved, error = self._resolve_managed_headless_target(
            agent_ref
        )
        if error is not None:
            return error
        if managed_tracked_agent_id is None:
            return (400, {"detail": f"Agent {agent_ref} is not a managed headless agent"})

        return self.m_headless.turn_status(managed_tracked_agent_id, turn_id)

    def turn_events(
        self, agent_ref: str, turn_id: str
    ) -> PassiveHeadlessTurnEventsResponse | tuple[int, dict[str, Any]]:
        """Return structured events from a headless turn."""

        managed_tracked_agent_id, _resolved, error = self._resolve_managed_headless_target(
            agent_ref
        )
        if error is not None:
            return error
        if managed_tracked_agent_id is None:
            return (400, {"detail": f"Agent {agent_ref} is not a managed headless agent"})

        return self.m_headless.turn_events(managed_tracked_agent_id, turn_id)

    def turn_artifact_text(
        self, agent_ref: str, turn_id: str, name: str
    ) -> str | tuple[int, dict[str, Any]]:
        """Return text content of a turn artifact (stdout / stderr)."""

        managed_tracked_agent_id, _resolved, error = self._resolve_managed_headless_target(
            agent_ref
        )
        if error is not None:
            return error
        if managed_tracked_agent_id is None:
            return (400, {"detail": f"Agent {agent_ref} is not a managed headless agent"})

        return self.m_headless.turn_artifact_text(managed_tracked_agent_id, turn_id, name)

    def _resolve_managed_headless_target(
        self, agent_ref: str
    ) -> tuple[str | None, DiscoveredAgent | None, tuple[int, dict[str, Any]] | None]:
        """Resolve one agent reference onto the authoritative managed headless id."""

        direct_matches = self.m_headless.resolve_managed_matches(agent_ref)
        if len(direct_matches) > 1:
            return (
                None,
                None,
                (409, {"detail": f"Ambiguous managed headless agent reference: {agent_ref}"}),
            )
        if len(direct_matches) == 1:
            return (direct_matches[0], None, None)

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return (None, None, resolved)

        discovered_matches = self.m_headless.resolve_managed_matches(resolved.record.agent_id)
        if len(discovered_matches) > 1:
            return (
                None,
                None,
                (
                    409,
                    {
                        "detail": (
                            "Ambiguous managed headless agent reference after discovery "
                            f"resolution: {resolved.record.agent_id}"
                        )
                    },
                ),
            )
        if len(discovered_matches) == 1:
            return (discovered_matches[0], resolved, None)
        return (None, resolved, None)

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
