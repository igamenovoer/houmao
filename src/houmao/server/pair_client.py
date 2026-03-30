"""Shared pair-authority client protocol and resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputRequestV1,
    GatewayControlInputResultV1,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayStatusV1,
)
from houmao.cao.models import CaoSuccessResponse
from houmao.server.client import HoumaoServerClient
from houmao.server.models import (
    HoumaoCurrentInstance,
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoHeadlessTurnEventsResponse,
    HoumaoHeadlessTurnRequest,
    HoumaoHeadlessTurnStatusResponse,
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayPromptControlRequest,
    HoumaoManagedAgentGatewayPromptControlResponse,
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
    HoumaoManagedAgentMailStateRequest,
    HoumaoManagedAgentMailStateResponse,
    HoumaoManagedAgentMailStatusResponse,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentRequestEnvelope,
    HoumaoManagedAgentStateResponse,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
)


class PairAuthorityHealthProbe(BaseModel):
    """Lenient `/health` probe used for pair-authority detection."""

    model_config = ConfigDict(extra="ignore")

    status: str
    houmao_service: str | None = None


class PairAuthorityClientError(RuntimeError):
    """Base error raised while resolving a pair authority client."""


class PairAuthorityConnectionError(PairAuthorityClientError):
    """Raised when a pair authority cannot be reached."""

    def __init__(self, *, base_url: str, cause: Exception) -> None:
        self.m_base_url = base_url
        self.m_cause = cause
        super().__init__(f"Failed to reach a Houmao pair authority at {base_url}: {cause}")


class UnsupportedPairAuthorityError(PairAuthorityClientError):
    """Raised when `/health` does not identify a supported Houmao pair authority."""

    def __init__(self, *, base_url: str, houmao_service: str | None) -> None:
        self.m_base_url = base_url
        self.m_houmao_service = houmao_service
        if houmao_service is None:
            detail = (
                f"Target at {base_url} is not a supported Houmao pair authority. "
                "Supported pair authorities are `houmao-server` and `houmao-passive-server`; "
                "mixed usage with raw `cao-server` is unsupported."
            )
        else:
            detail = (
                f"Target at {base_url} reported unsupported houmao_service={houmao_service!r}. "
                "Supported pair authorities are `houmao-server` and `houmao-passive-server`; "
                "mixed usage with raw `cao-server` is unsupported."
            )
        super().__init__(detail)


class PairAuthorityClientProtocol(Protocol):
    """Shared pair-authority client surface used by pair-facing code."""

    @property
    def pair_authority_kind(self) -> str:
        """Return the remote pair-authority identity."""

    def current_instance(self) -> HoumaoCurrentInstance:
        """Return current-instance metadata."""

    def shutdown_server(self) -> CaoSuccessResponse:
        """Request graceful shutdown of the pair authority."""

    def list_managed_agents(self) -> HoumaoManagedAgentListResponse:
        """List pair-managed agents."""

    def get_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentIdentity:
        """Resolve one managed-agent identity."""

    def get_managed_agent_state(self, agent_ref: str) -> HoumaoManagedAgentStateResponse:
        """Return managed-agent summary state."""

    def get_managed_agent_state_detail(self, agent_ref: str) -> HoumaoManagedAgentDetailResponse:
        """Return managed-agent transport-specific detail."""

    def get_managed_agent_history(
        self,
        agent_ref: str,
        *,
        limit: int | None = None,
    ) -> HoumaoManagedAgentHistoryResponse:
        """Return managed-agent coarse history."""

    def submit_managed_agent_request(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentRequestEnvelope,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        """Submit one transport-neutral managed-agent request."""

    def stop_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        """Stop one managed agent."""

    def interrupt_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        """Interrupt one managed agent."""

    def get_managed_agent_gateway_status(self, agent_ref: str) -> GatewayStatusV1:
        """Return gateway status for one managed agent."""

    def attach_managed_agent_gateway(self, agent_ref: str) -> GatewayStatusV1:
        """Attach a managed-agent gateway."""

    def detach_managed_agent_gateway(self, agent_ref: str) -> GatewayStatusV1:
        """Detach a managed-agent gateway."""

    def get_managed_agent_gateway_tui_state(self, agent_ref: str) -> HoumaoTerminalStateResponse:
        """Return raw gateway-owned TUI state for one managed agent."""

    def get_managed_agent_gateway_tui_history(
        self,
        agent_ref: str,
        *,
        limit: int = 100,
    ) -> HoumaoTerminalSnapshotHistoryResponse:
        """Return raw gateway-owned TUI snapshot history for one managed agent."""

    def note_managed_agent_gateway_tui_prompt(
        self,
        agent_ref: str,
        *,
        prompt: str,
    ) -> HoumaoTerminalStateResponse:
        """Record prompt-note provenance through the managed-agent gateway TUI surface."""

    def submit_managed_agent_gateway_request(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayRequestCreate,
    ) -> HoumaoManagedAgentGatewayRequestAcceptedResponse:
        """Submit one managed-agent gateway request."""

    def control_managed_agent_gateway_prompt(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayPromptControlRequest,
    ) -> HoumaoManagedAgentGatewayPromptControlResponse:
        """Submit one managed-agent gateway direct prompt-control request."""

    def send_managed_agent_gateway_control_input(
        self,
        agent_ref: str,
        request_model: GatewayControlInputRequestV1,
    ) -> GatewayControlInputResultV1:
        """Send one managed-agent gateway raw control-input request."""

    def get_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
    ) -> GatewayMailNotifierStatusV1:
        """Return managed-agent gateway mail-notifier status."""

    def put_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
        request_model: GatewayMailNotifierPutV1,
    ) -> GatewayMailNotifierStatusV1:
        """Enable or update managed-agent gateway mail-notifier state."""

    def delete_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
    ) -> GatewayMailNotifierStatusV1:
        """Disable managed-agent gateway mail-notifier state."""

    def get_managed_agent_mail_status(
        self,
        agent_ref: str,
    ) -> HoumaoManagedAgentMailStatusResponse:
        """Return managed-agent mailbox status."""

    def check_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailCheckRequest,
    ) -> HoumaoManagedAgentMailCheckResponse:
        """Check managed-agent mail."""

    def send_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailSendRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        """Send managed-agent mail."""

    def reply_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailReplyRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        """Reply to managed-agent mail."""

    def update_managed_agent_mail_state(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailStateRequest,
    ) -> HoumaoManagedAgentMailStateResponse:
        """Update managed-agent mail state."""

    def submit_headless_turn(
        self,
        agent_ref: str,
        request_model: HoumaoHeadlessTurnRequest,
    ) -> HoumaoHeadlessTurnAcceptedResponse:
        """Submit one headless turn."""

    def get_headless_turn_status(
        self,
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnStatusResponse:
        """Return one headless turn status."""

    def get_headless_turn_events(
        self,
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnEventsResponse:
        """Return one headless turn event stream."""

    def get_headless_turn_artifact_text(
        self,
        agent_ref: str,
        turn_id: str,
        *,
        artifact_name: str,
    ) -> str:
        """Return one raw headless artifact payload."""


@dataclass(frozen=True)
class PairAuthorityClientResolution:
    """Resolved pair-authority client plus the detection probe payload."""

    client: PairAuthorityClientProtocol
    health: PairAuthorityHealthProbe


def resolve_pair_authority_client(
    *,
    base_url: str,
    timeout_seconds: float | None = None,
    create_timeout_seconds: float | None = None,
) -> PairAuthorityClientResolution:
    """Resolve one supported pair-authority client from `GET /health`."""

    client_kwargs: dict[str, float] = {}
    if timeout_seconds is not None:
        client_kwargs["timeout_seconds"] = timeout_seconds
    if create_timeout_seconds is not None:
        client_kwargs["create_timeout_seconds"] = create_timeout_seconds

    probe_client = HoumaoServerClient(base_url, **client_kwargs)
    try:
        health = probe_client._request_root_model("GET", "/health", PairAuthorityHealthProbe)
    except Exception as exc:  # pragma: no cover - transport-specific surface
        raise PairAuthorityConnectionError(base_url=base_url, cause=exc) from exc

    if health.houmao_service == "houmao-server":
        return PairAuthorityClientResolution(client=probe_client, health=health)
    if health.houmao_service == "houmao-passive-server":
        from houmao.passive_server.client import PassiveServerClient

        return PairAuthorityClientResolution(
            client=PassiveServerClient(base_url, **client_kwargs),
            health=health,
        )
    raise UnsupportedPairAuthorityError(base_url=base_url, houmao_service=health.houmao_service)
