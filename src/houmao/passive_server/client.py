"""Pair-facing client adapter for `houmao-passive-server`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar, cast
from urllib import error, parse, request
import uuid

from pydantic import BaseModel, ValidationError

from houmao.mailbox.models import MailChannel
from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputRequestV1,
    GatewayControlInputResultV1,
    GatewayHeadlessControlStateV1,
    GatewayWebControlStateV1,
    GatewayWebHistoryV1,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderCreateResultV1,
    GatewayReminderDeleteResultV1,
    GatewayReminderListV1,
    GatewayReminderPutV1,
    GatewayReminderV1,
    GatewayRequestCreateV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.native_refresh_models import (
    CommonPluginObservationV1,
    NativeHomeV1,
    NativeRefreshRequestV1,
    NativeRefreshResultV1,
)
from houmao.cao.models import CaoSuccessResponse
from houmao.cao.rest_client import (
    CaoApiError,
    DEFAULT_CAO_CREATE_TIMEOUT_SECONDS,
    DEFAULT_CAO_REQUEST_TIMEOUT_SECONDS,
)
from houmao.gateway.access import (
    GatewayAccessError,
    GatewayClientBinding,
    GatewayRequestBinding,
    parse_access_document,
)
from houmao.gateway.authorization_models import (
    DefaultFallbackReceipt,
    DefaultFallbackRequest,
    DefaultPermissionGroupReceipt,
    DefaultPermissionGroupRequest,
)
from houmao.gateway.owner_authority import (
    BACKING_HEADER,
    PassiveBackingBinding,
    issue_passive_backing,
)
from houmao.passive_server.admission import passive_client_challenge_path
from houmao.passive_server.compatibility import managed_identity_from_discovered_summary
from houmao.passive_server.models import (
    DiscoveredAgentListResponse,
    DiscoveredAgentSummary,
    PassiveAgentActionResponse,
    PassiveHealthResponse,
    PassiveProofEndpoint,
    PassiveHeadlessLaunchRequest,
    PassiveHeadlessLaunchResponse,
    PassiveHeadlessTurnAcceptedResponse,
    PassiveHeadlessTurnEventsResponse,
    PassiveHeadlessTurnRequest,
    PassiveHeadlessTurnStatusResponse,
    PassivePromptRequest,
    PassiveRequestAcceptedResponse,
    PassiveShutdownResponse,
    PassiveWorkRequestReceipt,
)
from houmao.server._http_transport import (
    RootResponseFormat,
    decode_root_response,
    request_root,
)
from houmao.server._pair_operations import ManagedPairOperations
from houmao.server.models import (
    HoumaoCurrentInstance,
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoHeadlessTurnEventsResponse,
    HoumaoHeadlessTurnRequest,
    HoumaoHeadlessTurnStatusResponse,
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayNextPromptSessionRequest,
    HoumaoManagedAgentGatewayInternalHeadlessPromptRequest,
    HoumaoManagedAgentGatewayPromptControlRequest,
    HoumaoManagedAgentGatewayPromptControlResponse,
    HoumaoManagedAgentGatewayRequestAcceptedResponse,
    HoumaoManagedAgentGatewayRequestCreate,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentListResponse,
    HoumaoManagedAgentMailActionResponse,
    HoumaoManagedAgentMailListRequest,
    HoumaoManagedAgentMailListResponse,
    HoumaoManagedAgentMailPostRequest,
    HoumaoManagedAgentMailReplyRequest,
    HoumaoManagedAgentMailSendRequest,
    HoumaoManagedAgentMailStatusResponse,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentRequestEnvelope,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentSubmitPromptRequest,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)
_SIGNED_RESPONSE_LIMIT = 16 * 1024 * 1024


class PassiveBackingClient:
    """Owner-local client for one gateway's scoped backing operations."""

    def __init__(self, *, private_root: Path, binding: PassiveBackingBinding) -> None:
        """Capture explicit service authority independently of caller admission."""

        def request_proof(method: str, path: str, body: bytes) -> dict[str, str]:
            """Issue one service token for the exact transmitted request."""

            endpoint = parse.urlsplit(path)
            try:
                binding_request = GatewayRequestBinding.from_request(
                    method, endpoint.path, endpoint.query, body
                )
                token = issue_passive_backing(
                    private_root, binding=binding, request=binding_request
                )
            except (GatewayAccessError, ValueError):
                raise GatewayHttpError(
                    method=method, url="", detail="Backing service proof is unavailable"
                ) from None
            return {BACKING_HEADER: token}

        self.m_client: GatewayClient = GatewayClient(
            base_url=binding.api_base_url, request_proof=request_proof, respect_proxy_env=False
        )
        self.m_base_route: str = f"/houmao/agents/{binding.tracked_agent_id}/gateway/internal"

    def inspect(self) -> HoumaoManagedAgentDetailResponse:
        """Read current backing posture through the service-only operation."""

        return self.m_client._request_model(
            "GET", f"{self.m_base_route}/inspect", HoumaoManagedAgentDetailResponse
        )

    def dispatch(
        self, payload: HoumaoManagedAgentGatewayInternalHeadlessPromptRequest
    ) -> CaoSuccessResponse:
        """Deliver one prompt through the bound owner-controlled backing path."""

        return self.m_client._request_model(
            "POST",
            f"{self.m_base_route}/headless-prompt",
            CaoSuccessResponse,
            body=payload.model_dump(mode="json"),
            timeout_seconds=8.0,
        )

    def interrupt(self) -> PassiveAgentActionResponse:
        """Interrupt only the selected backing controller."""

        return self.m_client._request_model(
            "POST", f"{self.m_base_route}/interrupt", PassiveAgentActionResponse
        )


class PassiveServerClient(ManagedPairOperations):
    """Typed client adapter that normalizes passive-server routes for pair consumers."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = DEFAULT_CAO_REQUEST_TIMEOUT_SECONDS,
        create_timeout_seconds: float = DEFAULT_CAO_CREATE_TIMEOUT_SECONDS,
        *,
        binding: GatewayClientBinding | None = None,
        target_incarnation: str | None = None,
        target_presence_id: str | None = None,
    ) -> None:
        """Select an explicitly bound signer for protected selected-agent calls."""

        self.base_url: str = base_url.rstrip("/")
        self.timeout_seconds: float = timeout_seconds
        self.create_timeout_seconds: float = create_timeout_seconds
        if binding is not None and binding.purpose == "register":
            raise ValueError("First enrollment is available at the agent gateway.")
        self.m_signed_transport: GatewayClient | None = (
            GatewayClient(
                base_url=self.base_url,
                binding=binding,
                target_incarnation=target_incarnation,
                target_presence_id=target_presence_id,
                timeout_seconds=timeout_seconds,
            )
            if binding is not None
            else None
        )

    def _request_root_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: object | None = None,
        raw_text: bool = False,
        timeout_seconds: float | None = None,
    ) -> tuple[object, int, str]:
        """Use exact request proof on a selected-agent operation when configured."""

        response_format: RootResponseFormat = "text" if raw_text else "json"
        transport = self.m_signed_transport
        if transport is None:
            return request_root(
                self.base_url,
                method,
                path,
                default_timeout_seconds=self.timeout_seconds,
                params=params,
                json_body=json_body,
                response_format=response_format,
                timeout_seconds=timeout_seconds,
            )
        route, _, existing_query = path.partition("?")
        query = "&".join(part for part in (existing_query, parse.urlencode(params or {})) if part)
        url = transport._build_url(route if not query else f"{route}?{query}")
        challenge_path = passive_client_challenge_path(method, route)
        data = json.dumps(json_body).encode("utf-8") if json_body is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if method in {"POST", "PUT", "PATCH"} and data is None:
            data = b""
        try:
            if challenge_path is not None:
                endpoint_url = transport._build_url(
                    f"{challenge_path.removesuffix('/challenge')}/endpoint"
                )
                descriptor = parse_access_document(
                    PassiveProofEndpoint,
                    transport._open_request(
                        request_obj=request.Request(endpoint_url, method="GET"),
                        method="GET",
                        url=endpoint_url,
                    ),
                )
                if descriptor.challenge_path != challenge_path:
                    raise ValueError(
                        "Passive proof endpoint differs from the selected target route."
                    )
                headers.update(
                    transport._signed_headers(
                        method,
                        route,
                        query,
                        data or b"",
                        challenge_path=challenge_path,
                        endpoint_binding=(descriptor.target, descriptor.presence_id),
                    )
                )
            outgoing = request.Request(url, data=data, method=method, headers=headers)
            with transport.m_opener.open(
                outgoing, timeout=timeout_seconds or self.timeout_seconds
            ) as response:
                raw = response.read(_SIGNED_RESPONSE_LIMIT + 1)
                if len(raw) > _SIGNED_RESPONSE_LIMIT:
                    raise ValueError("Passive response exceeds its limit.")
                payload = decode_root_response(raw, response_format)
                return payload, int(response.status), url
        except GatewayHttpError as exc:
            challenge = {"challenge_path": challenge_path} if exc.status_code == 401 else None
            raise CaoApiError(
                method=method,
                url=url,
                status_code=exc.status_code,
                detail=exc.detail,
                payload=challenge,
            ) from None
        except error.HTTPError as exc:
            raise _signed_passive_refusal(method, url, exc, challenge_path) from None
        except (OSError, ValueError):
            raise CaoApiError(
                method=method, url=url, detail="Passive transport or response failed."
            ) from None

    @property
    def pair_authority_kind(self) -> str:
        """Return the passive-server pair-authority identity."""

        return "houmao-passive-server"

    def health(self) -> PassiveHealthResponse:
        """Read passive server health from the root endpoint."""

        return self._request_root_model("GET", "/health", PassiveHealthResponse)

    def current_instance(self) -> HoumaoCurrentInstance:
        """Call `GET /houmao/server/current-instance` and normalize the response."""

        return self._request_root_model(
            "GET",
            "/houmao/server/current-instance",
            HoumaoCurrentInstance,
        )

    def set_default_permission_group(
        self, agent_ref: str, payload: DefaultPermissionGroupRequest
    ) -> DefaultPermissionGroupReceipt:
        """Mutate the selected target policy through direct passive ingress."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "PUT",
            f"/houmao/agents/{escaped}/admin/default-permission-group",
            DefaultPermissionGroupReceipt,
            json_body=payload.model_dump(mode="json"),
        )

    def set_default_fallback(
        self, agent_ref: str, principal_id: str, payload: DefaultFallbackRequest
    ) -> DefaultFallbackReceipt:
        """Set one principal's default fallback through direct passive ingress."""

        escaped = parse.quote(agent_ref, safe="")
        principal = parse.quote(principal_id, safe="")
        return self._request_root_model(
            "PUT",
            f"/houmao/agents/{escaped}/admin/principals/{principal}/default-fallback",
            DefaultFallbackReceipt,
            json_body=payload.model_dump(mode="json"),
        )

    def describe_agent_proof(self, agent_ref: str) -> PassiveProofEndpoint:
        """Observe the passive proof listener and its exact selected agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET", f"/houmao/agents/{escaped}/auth/endpoint", PassiveProofEndpoint
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
            if self.m_signed_transport is not None:
                agents.append(managed_identity_from_discovered_summary(summary))
                continue
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
        except CaoApiError as exc:
            if self.m_signed_transport is not None and exc.status_code in {401, 403, 503}:
                raise
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

    def submit_detached_work_request(
        self, agent_ref: str, payload: GatewayRequestCreateV1
    ) -> PassiveWorkRequestReceipt:
        """Submit one wrapped request to the direct detached passive route."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/work-requests",
            PassiveWorkRequestReceipt,
            json_body=payload.model_dump(mode="json"),
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
            passive_accepted = self._request_root_model(
                "POST",
                f"/houmao/agents/{escaped}/requests",
                PassiveRequestAcceptedResponse,
                json_body=PassivePromptRequest(prompt=request_model.prompt).model_dump(mode="json"),
            )
            return HoumaoManagedAgentRequestAcceptedResponse(
                success=True,
                tracked_agent_id=identity.tracked_agent_id,
                request_id=passive_accepted.request_id,
                request_kind="submit_prompt",
                disposition="accepted",
                detail=passive_accepted.detail,
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
            manifest_path=identity.manifest_path,
            session_root=identity.session_root,
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

    def get_managed_agent_gateway_native_home(self, agent_ref: str) -> NativeHomeV1:
        """Read the selected gateway's authoritative native home."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_native_refresh_model(
            "GET", f"/houmao/agents/{escaped}/gateway/native-home", NativeHomeV1
        )

    def get_managed_agent_gateway_common_plugin_state(
        self, agent_ref: str
    ) -> CommonPluginObservationV1:
        """Read common freshness without starting native refresh or provider work."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_native_refresh_model(
            "GET", f"/houmao/agents/{escaped}/gateway/control/refresh", CommonPluginObservationV1
        )

    def refresh_managed_agent_gateway_native(
        self, agent_ref: str, payload: NativeRefreshRequestV1
    ) -> NativeRefreshResultV1:
        """Forward one bounded refresh and retain typed non-success results without retry."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_native_refresh_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/control/refresh",
            NativeRefreshResultV1,
            json_body=payload.model_dump(mode="json"),
            timeout_seconds=payload.timeout_seconds + 10.0,
        )

    def _request_native_refresh_model(
        self,
        method: str,
        path: str,
        model: type[_ModelT],
        *,
        json_body: object | None = None,
        timeout_seconds: float | None = None,
    ) -> _ModelT:
        """Validate shared native contracts and suppress private invalid-response details."""

        try:
            data, status, url = self._request_root_json(
                method, path, json_body=json_body, timeout_seconds=timeout_seconds
            )
        except CaoApiError as exc:
            if method == "POST" and model is NativeRefreshResultV1:
                try:
                    return model.model_validate(exc.payload)
                except ValidationError:
                    pass
            raise CaoApiError(
                method=method,
                url=exc.url,
                status_code=exc.status_code,
                detail="Passive native refresh response is unavailable; the operation was not retried.",
            ) from None
        except ValueError:
            raise CaoApiError(
                method=method,
                url=f"{self.base_url}{path}",
                detail="Passive native refresh returned an invalid typed response.",
            ) from None
        try:
            return model.model_validate(data)
        except ValidationError:
            raise CaoApiError(
                method=method,
                url=url,
                status_code=status,
                detail="Passive native refresh returned an invalid typed response.",
            ) from None

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

    def control_managed_agent_gateway_prompt(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayPromptControlRequest,
    ) -> HoumaoManagedAgentGatewayPromptControlResponse:
        """Call passive gateway direct prompt control for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/control/prompt",
            HoumaoManagedAgentGatewayPromptControlResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def get_managed_agent_gateway_web_state(self, agent_ref: str) -> GatewayWebControlStateV1:
        """Read the attached gateway's structured native Web observation."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET", f"/houmao/agents/{escaped}/gateway/web/state", GatewayWebControlStateV1
        )

    def get_managed_agent_gateway_web_history(
        self, agent_ref: str, *, limit: int = 100
    ) -> GatewayWebHistoryV1:
        """Read the attached gateway's bounded native Web transitions."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/gateway/web/history?limit={limit}",
            GatewayWebHistoryV1,
        )

    def get_managed_agent_gateway_headless_control_state(
        self,
        agent_ref: str,
    ) -> GatewayHeadlessControlStateV1:
        """Call passive gateway headless control state for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/gateway/control/headless/state",
            GatewayHeadlessControlStateV1,
        )

    def set_managed_agent_gateway_headless_next_prompt_session(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayNextPromptSessionRequest,
    ) -> GatewayHeadlessControlStateV1:
        """Call passive gateway next-prompt-session for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/control/headless/next-prompt-session",
            GatewayHeadlessControlStateV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def send_managed_agent_gateway_control_input(
        self,
        agent_ref: str,
        request_model: GatewayControlInputRequestV1,
    ) -> GatewayControlInputResultV1:
        """Call passive raw gateway control input for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/control/send-keys",
            GatewayControlInputResultV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def get_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
        *,
        channel: MailChannel,
    ) -> GatewayMailNotifierStatusV1:
        """Call passive gateway mail-notifier status for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/gateway/mail-notifier/{channel}",
            GatewayMailNotifierStatusV1,
        )

    def put_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
        request_model: GatewayMailNotifierPutV1,
        *,
        channel: MailChannel,
    ) -> GatewayMailNotifierStatusV1:
        """Call passive gateway mail-notifier enable/update for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "PUT",
            f"/houmao/agents/{escaped}/gateway/mail-notifier/{channel}",
            GatewayMailNotifierStatusV1,
            json_body=request_model.model_dump(mode="json", exclude_unset=True),
        )

    def delete_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
        *,
        channel: MailChannel,
    ) -> GatewayMailNotifierStatusV1:
        """Call passive gateway mail-notifier disable for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "DELETE",
            f"/houmao/agents/{escaped}/gateway/mail-notifier/{channel}",
            GatewayMailNotifierStatusV1,
        )

    def list_managed_agent_gateway_reminders(
        self,
        agent_ref: str,
    ) -> GatewayReminderListV1:
        """Call passive gateway reminder listing for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/gateway/reminders",
            GatewayReminderListV1,
        )

    def create_managed_agent_gateway_reminders(
        self,
        agent_ref: str,
        request_model: GatewayReminderCreateBatchV1,
    ) -> GatewayReminderCreateResultV1:
        """Call passive gateway reminder creation for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/reminders",
            GatewayReminderCreateResultV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def get_managed_agent_gateway_reminder(
        self,
        agent_ref: str,
        reminder_id: str,
    ) -> GatewayReminderV1:
        """Call passive gateway reminder lookup for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        reminder_escaped = parse.quote(reminder_id, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/gateway/reminders/{reminder_escaped}",
            GatewayReminderV1,
        )

    def put_managed_agent_gateway_reminder(
        self,
        agent_ref: str,
        reminder_id: str,
        request_model: GatewayReminderPutV1,
    ) -> GatewayReminderV1:
        """Call passive gateway reminder update for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        reminder_escaped = parse.quote(reminder_id, safe="")
        return self._request_root_model(
            "PUT",
            f"/houmao/agents/{escaped}/gateway/reminders/{reminder_escaped}",
            GatewayReminderV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def delete_managed_agent_gateway_reminder(
        self,
        agent_ref: str,
        reminder_id: str,
    ) -> GatewayReminderDeleteResultV1:
        """Call passive gateway reminder deletion for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        reminder_escaped = parse.quote(reminder_id, safe="")
        return self._request_root_model(
            "DELETE",
            f"/houmao/agents/{escaped}/gateway/reminders/{reminder_escaped}",
            GatewayReminderDeleteResultV1,
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

    def list_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailListRequest,
        *,
        channel: MailChannel,
    ) -> HoumaoManagedAgentMailListResponse:
        """Call passive mail list for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/{channel}/list",
            HoumaoManagedAgentMailListResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def send_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailSendRequest,
        *,
        channel: MailChannel,
    ) -> HoumaoManagedAgentMailActionResponse:
        """Call passive mail send for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/{channel}/send",
            HoumaoManagedAgentMailActionResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def post_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailPostRequest,
        *,
        channel: MailChannel,
    ) -> HoumaoManagedAgentMailActionResponse:
        """Call passive mail post for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/{channel}/post",
            HoumaoManagedAgentMailActionResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def reply_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailReplyRequest,
        *,
        channel: MailChannel,
    ) -> HoumaoManagedAgentMailActionResponse:
        """Call passive mail reply for one managed agent."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/{channel}/reply",
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
            json_body=PassiveHeadlessTurnRequest(
                prompt=request_model.prompt,
                chat_session=request_model.chat_session,
                execution=request_model.execution,
            ).model_dump(mode="json"),
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

    def get_headless_turn_artifact_text(
        self,
        agent_ref: str,
        turn_id: str,
        *,
        artifact_name: str,
    ) -> str:
        """Read one headless artifact as the exact text sent by the server."""

        escaped_agent = parse.quote(agent_ref, safe="")
        escaped_turn = parse.quote(turn_id, safe="")
        payload, _status, _url = self._request_root_json(
            "GET",
            f"/houmao/agents/{escaped_agent}/turns/{escaped_turn}/artifacts/{artifact_name}",
            raw_text=True,
        )
        return cast(str, payload)

    def _generated_request_id(self, *, prefix: str) -> str:
        """Return one client-generated managed request id."""

        return f"passive-{prefix}-{uuid.uuid4().hex[:12]}"


def _signed_passive_refusal(
    method: str, url: str, exc: error.HTTPError, challenge_path: str | None
) -> CaoApiError:
    """Preserve typed passive outcomes while omitting untrusted access diagnostics."""

    status = exc.code
    payload = None
    if 300 <= status < 400:
        detail = "Passive redirects are refused."
    elif status in {401, 403}:
        detail = "Passive selected-agent proof was refused."
        if status == 401 and challenge_path is not None:
            payload = {"challenge_path": challenge_path}
    else:
        raw = exc.read(65_537)
        try:
            payload = json.loads(raw) if len(raw) <= 65_536 else None
        except (UnicodeError, ValueError, RecursionError):
            payload = None
        detail = "Passive operation failed."
    return CaoApiError(method=method, url=url, status_code=status, detail=detail, payload=payload)
