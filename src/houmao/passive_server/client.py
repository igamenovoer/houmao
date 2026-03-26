"""Pair-facing client adapter for `houmao-passive-server`."""

from __future__ import annotations

from urllib import parse
import uuid

from houmao.agents.realm_controller.gateway_models import GatewayStatusV1
from houmao.cao.models import CaoSuccessResponse
from houmao.cao.rest_client import CaoApiError
from houmao.passive_server.compatibility import managed_identity_from_discovered_summary
from houmao.passive_server.models import (
    DiscoveredAgentListResponse,
    DiscoveredAgentSummary,
    PassiveAgentActionResponse,
    PassiveHeadlessLaunchRequest,
    PassiveHeadlessLaunchResponse,
    PassiveHeadlessTurnAcceptedResponse,
    PassiveHeadlessTurnEventsResponse,
    PassiveHeadlessTurnRequest,
    PassiveHeadlessTurnStatusResponse,
    PassivePromptRequest,
    PassiveRequestAcceptedResponse,
    PassiveShutdownResponse,
)
from houmao.server.client import HoumaoServerClient
from houmao.server.models import (
    HoumaoCurrentInstance,
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoHeadlessTurnEventsResponse,
    HoumaoHeadlessTurnRequest,
    HoumaoHeadlessTurnStatusResponse,
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayRequestAcceptedResponse,
    HoumaoManagedAgentGatewayRequestCreate,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentListResponse,
    HoumaoManagedAgentMailActionResponse,
    HoumaoManagedAgentMailCheckRequest,
    HoumaoManagedAgentMailCheckResponse,
    HoumaoManagedAgentMailReplyRequest,
    HoumaoManagedAgentMailSendRequest,
    HoumaoManagedAgentMailStatusResponse,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentRequestEnvelope,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentSubmitPromptRequest,
)


class PassiveServerClient(HoumaoServerClient):
    """Typed client adapter that normalizes passive-server routes for pair consumers."""

    @property
    def pair_authority_kind(self) -> str:
        """Return the passive-server pair-authority identity."""

        return "houmao-passive-server"

    def current_instance(self) -> HoumaoCurrentInstance:
        """Call `GET /houmao/server/current-instance` and normalize the response."""

        return self._request_root_model(
            "GET",
            "/houmao/server/current-instance",
            HoumaoCurrentInstance,
        )

    def shutdown_server(self) -> CaoSuccessResponse:
        """Call `POST /houmao/server/shutdown` and normalize to `CaoSuccessResponse`."""

        self._request_root_model(
            "POST",
            "/houmao/server/shutdown",
            PassiveShutdownResponse,
        )
        return CaoSuccessResponse(success=True)

    def list_managed_agents(self) -> HoumaoManagedAgentListResponse:
        """Call passive discovery and normalize into managed-agent identities."""

        response = self._request_root_model(
            "GET",
            "/houmao/agents",
            DiscoveredAgentListResponse,
        )
        agents: list[HoumaoManagedAgentIdentity] = []
        for summary in response.agents:
            try:
                agents.append(self.get_managed_agent(summary.agent_id))
            except CaoApiError:
                agents.append(managed_identity_from_discovered_summary(summary))
        agents.sort(key=lambda item: (item.transport, item.tracked_agent_id))
        return HoumaoManagedAgentListResponse(agents=agents)

    def get_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentIdentity:
        """Resolve one passive managed-agent identity for pair consumers."""

        escaped = parse.quote(agent_ref, safe="")
        summary = self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}",
            DiscoveredAgentSummary,
        )
        fallback = managed_identity_from_discovered_summary(summary)
        try:
            return self.get_managed_agent_state(agent_ref).identity
        except CaoApiError:
            return fallback

    def get_managed_agent_state(self, agent_ref: str) -> HoumaoManagedAgentStateResponse:
        """Call `GET /houmao/agents/{agent_ref}/managed-state`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/managed-state",
            HoumaoManagedAgentStateResponse,
        )

    def get_managed_agent_state_detail(self, agent_ref: str) -> HoumaoManagedAgentDetailResponse:
        """Call `GET /houmao/agents/{agent_ref}/managed-state/detail`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/managed-state/detail",
            HoumaoManagedAgentDetailResponse,
        )

    def get_managed_agent_history(
        self,
        agent_ref: str,
        *,
        limit: int | None = None,
    ) -> HoumaoManagedAgentHistoryResponse:
        """Call `GET /houmao/agents/{agent_ref}/managed-history`."""

        escaped = parse.quote(agent_ref, safe="")
        params: dict[str, str] | None = None
        if limit is not None:
            params = {"limit": str(limit)}
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/managed-history",
            HoumaoManagedAgentHistoryResponse,
            params=params,
        )

    def submit_managed_agent_request(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentRequestEnvelope,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        """Normalize passive prompt and interrupt delivery into the managed request model."""

        identity = self.get_managed_agent(agent_ref)
        if isinstance(request_model, HoumaoManagedAgentSubmitPromptRequest):
            if identity.transport == "headless":
                accepted = self.submit_headless_turn(
                    agent_ref,
                    HoumaoHeadlessTurnRequest(prompt=request_model.prompt),
                )
                return HoumaoManagedAgentRequestAcceptedResponse(
                    success=True,
                    tracked_agent_id=accepted.tracked_agent_id,
                    request_id=f"headless-turn:{accepted.turn_id}",
                    request_kind="submit_prompt",
                    disposition="accepted",
                    detail=accepted.detail,
                    headless_turn_id=accepted.turn_id,
                    headless_turn_index=accepted.turn_index,
                )
            escaped = parse.quote(agent_ref, safe="")
            accepted = self._request_root_model(
                "POST",
                f"/houmao/agents/{escaped}/requests",
                PassiveRequestAcceptedResponse,
                json_body=PassivePromptRequest(prompt=request_model.prompt).model_dump(mode="json"),
            )
            return HoumaoManagedAgentRequestAcceptedResponse(
                success=True,
                tracked_agent_id=identity.tracked_agent_id,
                request_id=accepted.request_id,
                request_kind="submit_prompt",
                disposition="accepted",
                detail=accepted.detail,
            )

        action = self.interrupt_managed_agent(agent_ref)
        return HoumaoManagedAgentRequestAcceptedResponse(
            success=action.success,
            tracked_agent_id=action.tracked_agent_id,
            request_id=self._generated_request_id(prefix="interrupt"),
            request_kind="interrupt",
            disposition="accepted",
            detail=action.detail,
        )

    def stop_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        """Call passive stop and normalize into the shared action response."""

        identity = self.get_managed_agent(agent_ref)
        escaped = parse.quote(agent_ref, safe="")
        response = self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/stop",
            PassiveAgentActionResponse,
        )
        return HoumaoManagedAgentActionResponse(
            success=True,
            tracked_agent_id=identity.tracked_agent_id,
            detail=response.detail,
        )

    def interrupt_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        """Call passive interrupt and normalize into the shared action response."""

        identity = self.get_managed_agent(agent_ref)
        escaped = parse.quote(agent_ref, safe="")
        response = self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/interrupt",
            PassiveAgentActionResponse,
        )
        return HoumaoManagedAgentActionResponse(
            success=True,
            tracked_agent_id=identity.tracked_agent_id,
            detail=response.detail,
        )

    def get_managed_agent_gateway_status(self, agent_ref: str) -> GatewayStatusV1:
        """Call passive gateway status for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/gateway",
            GatewayStatusV1,
        )

    def submit_managed_agent_gateway_request(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayRequestCreate,
    ) -> HoumaoManagedAgentGatewayRequestAcceptedResponse:
        """Call passive gateway request submission for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/requests",
            HoumaoManagedAgentGatewayRequestAcceptedResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def get_managed_agent_mail_status(
        self,
        agent_ref: str,
    ) -> HoumaoManagedAgentMailStatusResponse:
        """Call passive mail status for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/mail/status",
            HoumaoManagedAgentMailStatusResponse,
        )

    def check_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailCheckRequest,
    ) -> HoumaoManagedAgentMailCheckResponse:
        """Call passive mail check for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/check",
            HoumaoManagedAgentMailCheckResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def send_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailSendRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        """Call passive mail send for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/send",
            HoumaoManagedAgentMailActionResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def reply_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailReplyRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        """Call passive mail reply for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/reply",
            HoumaoManagedAgentMailActionResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def submit_headless_turn(
        self,
        agent_ref: str,
        request_model: HoumaoHeadlessTurnRequest,
    ) -> HoumaoHeadlessTurnAcceptedResponse:
        """Call passive headless turn submission and normalize the response."""

        escaped = parse.quote(agent_ref, safe="")
        accepted = self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/turns",
            PassiveHeadlessTurnAcceptedResponse,
            json_body=PassiveHeadlessTurnRequest(prompt=request_model.prompt).model_dump(mode="json"),
        )
        return HoumaoHeadlessTurnAcceptedResponse(
            success=True,
            tracked_agent_id=accepted.tracked_agent_id,
            turn_id=accepted.turn_id,
            turn_index=accepted.turn_index,
            status=accepted.turn_status,
            detail=accepted.detail,
        )

    def launch_passive_headless_agent(
        self,
        request_model: PassiveHeadlessLaunchRequest,
    ) -> PassiveHeadlessLaunchResponse:
        """Call the passive headless-launch endpoint with the passive request model."""

        return self._request_root_model(
            "POST",
            "/houmao/agents/headless/launches",
            PassiveHeadlessLaunchResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def get_headless_turn_status(
        self,
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnStatusResponse:
        """Call passive headless turn status and normalize the response."""

        escaped_agent = parse.quote(agent_ref, safe="")
        escaped_turn = parse.quote(turn_id, safe="")
        status = self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped_agent}/turns/{escaped_turn}",
            PassiveHeadlessTurnStatusResponse,
        )
        return HoumaoHeadlessTurnStatusResponse(
            tracked_agent_id=status.tracked_agent_id,
            turn_id=status.turn_id,
            turn_index=status.turn_index,
            status=status.status,
            started_at_utc=status.started_at_utc,
            completed_at_utc=status.completed_at_utc,
            returncode=status.returncode,
            completion_source=status.completion_source,
            stdout_path=status.stdout_path,
            stderr_path=status.stderr_path,
            status_path=None,
            history_summary=None,
            error=status.error,
        )

    def get_headless_turn_events(
        self,
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnEventsResponse:
        """Call passive headless turn events and normalize the response."""

        escaped_agent = parse.quote(agent_ref, safe="")
        escaped_turn = parse.quote(turn_id, safe="")
        events = self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped_agent}/turns/{escaped_turn}/events",
            PassiveHeadlessTurnEventsResponse,
        )
        return HoumaoHeadlessTurnEventsResponse(
            tracked_agent_id=events.tracked_agent_id,
            turn_id=events.turn_id,
            entries=events.entries,
        )

    def _generated_request_id(self, *, prefix: str) -> str:
        """Return one client-generated managed request id."""

        return f"passive-{prefix}-{uuid.uuid4().hex[:12]}"
