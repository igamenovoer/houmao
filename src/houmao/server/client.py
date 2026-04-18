"""Client helpers for `houmao-server`."""

from __future__ import annotations

import json
from typing import TypeVar
from urllib import error, parse, request

from pydantic import BaseModel, ValidationError

from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputRequestV1,
    GatewayControlInputResultV1,
    GatewayHeadlessControlStateV1,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderCreateResultV1,
    GatewayReminderDeleteResultV1,
    GatewayReminderListV1,
    GatewayReminderPutV1,
    GatewayReminderV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
    GatewayMemoryActionResponseV1,
    GatewayMemoryMemoResponseV1,
    GatewayMemoryMemoWriteRequestV1,
    GatewayMemoryPagePathRequestV1,
    GatewayMemoryPagePathResolutionV1,
    GatewayMemoryPageResponseV1,
    GatewayMemoryPageTreeRequestV1,
    GatewayMemoryPageTreeResponseV1,
    GatewayMemoryPageWriteRequestV1,
    GatewayMemorySummaryV1,
)
from houmao.cao.rest_client import (
    DEFAULT_CAO_CREATE_TIMEOUT_SECONDS,
    DEFAULT_CAO_REQUEST_TIMEOUT_SECONDS,
    CaoApiError,
    CaoRestClient,
    _format_validation_error,
)
from houmao.cao.no_proxy import scoped_loopback_no_proxy_for_cao_base_url
from houmao.cao.models import CaoSessionDetail, CaoSuccessResponse

from .models import (
    HoumaoCurrentInstance,
    HoumaoHeadlessLaunchRequest,
    HoumaoHeadlessLaunchResponse,
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoHeadlessTurnEventsResponse,
    HoumaoHeadlessTurnRequest,
    HoumaoHeadlessTurnStatusResponse,
    HoumaoHealthResponse,
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentGatewayAttachRequest,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayInternalHeadlessPromptRequest,
    HoumaoManagedAgentGatewayNextPromptSessionRequest,
    HoumaoManagedAgentGatewayPromptControlRequest,
    HoumaoManagedAgentGatewayPromptControlResponse,
    HoumaoManagedAgentGatewayRequestAcceptedResponse,
    HoumaoManagedAgentGatewayRequestCreate,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentListResponse,
    HoumaoManagedAgentMailActionResponse,
    HoumaoManagedAgentMailArchiveRequest,
    HoumaoManagedAgentMailLifecycleResponse,
    HoumaoManagedAgentMailListRequest,
    HoumaoManagedAgentMailListResponse,
    HoumaoManagedAgentMailMarkRequest,
    HoumaoManagedAgentMailMessageRequest,
    HoumaoManagedAgentMailMessageResponse,
    HoumaoManagedAgentMailMoveRequest,
    HoumaoManagedAgentMailPostRequest,
    HoumaoManagedAgentMailReplyRequest,
    HoumaoManagedAgentMailSendRequest,
    HoumaoManagedAgentMailStatusResponse,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentRequestEnvelope,
    HoumaoManagedAgentStateResponse,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
    WorkingDirectoryResponse,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class HoumaoServerClient(CaoRestClient):
    """HTTP client for `houmao-server` compatibility and extension routes."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = DEFAULT_CAO_REQUEST_TIMEOUT_SECONDS,
        create_timeout_seconds: float = DEFAULT_CAO_CREATE_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the pair-owned server client."""

        super().__init__(
            base_url,
            timeout_seconds=timeout_seconds,
            create_timeout_seconds=create_timeout_seconds,
            path_prefix="/cao",
        )

    @property
    def pair_authority_kind(self) -> str:
        """Return the old server pair-authority identity."""

        return "houmao-server"

    def health_extended(self) -> HoumaoHealthResponse:
        """Call `GET /health` and parse Houmao extensions."""

        return self._request_root_model("GET", "/health", HoumaoHealthResponse)

    def get_session(self, session_name: str) -> CaoSessionDetail:
        """Call `GET /sessions/{session_name}`."""

        return self.get_session_detail(session_name)

    def delete_session(self, session_name: str) -> CaoSuccessResponse:
        """Call `DELETE /sessions/{session_name}`."""

        escaped = parse.quote(session_name, safe="")
        return self._request_model("DELETE", f"/sessions/{escaped}", CaoSuccessResponse)

    def get_terminal_working_directory(self, terminal_id: str) -> WorkingDirectoryResponse:
        """Call `GET /terminals/{terminal_id}/working-directory`."""

        escaped = parse.quote(terminal_id, safe="")
        return self._request_model(
            "GET",
            f"/terminals/{escaped}/working-directory",
            WorkingDirectoryResponse,
        )

    def current_instance(self) -> HoumaoCurrentInstance:
        """Call `GET /houmao/server/current-instance`."""

        return self._request_root_model(
            "GET",
            "/houmao/server/current-instance",
            HoumaoCurrentInstance,
        )

    def shutdown_server(self) -> CaoSuccessResponse:
        """Call `POST /houmao/server/shutdown`."""

        return self._request_root_model(
            "POST",
            "/houmao/server/shutdown",
            CaoSuccessResponse,
        )

    def terminal_state(self, terminal_id: str) -> HoumaoTerminalStateResponse:
        """Call `GET /houmao/terminals/{terminal_id}/state`."""

        escaped = parse.quote(terminal_id, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/terminals/{escaped}/state",
            HoumaoTerminalStateResponse,
        )

    def terminal_history(
        self,
        terminal_id: str,
        *,
        limit: int | None = None,
    ) -> HoumaoTerminalHistoryResponse:
        """Call `GET /houmao/terminals/{terminal_id}/history`."""

        escaped = parse.quote(terminal_id, safe="")
        params: dict[str, str] | None = None
        if limit is not None:
            params = {"limit": str(limit)}
        return self._request_root_model(
            "GET",
            f"/houmao/terminals/{escaped}/history",
            HoumaoTerminalHistoryResponse,
            params=params,
        )

    def register_launch(
        self, request_model: HoumaoRegisterLaunchRequest
    ) -> HoumaoRegisterLaunchResponse:
        """Call `POST /houmao/launches/register`."""

        query_params = {
            key: value
            for key, value in request_model.model_dump(mode="json").items()
            if value is not None
        }
        return self._request_root_model(
            "POST",
            "/houmao/launches/register",
            HoumaoRegisterLaunchResponse,
            params={key: str(value) for key, value in query_params.items()},
        )

    def list_managed_agents(self) -> HoumaoManagedAgentListResponse:
        """Call `GET /houmao/agents`."""

        return self._request_root_model("GET", "/houmao/agents", HoumaoManagedAgentListResponse)

    def get_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentIdentity:
        """Call `GET /houmao/agents/{agent_ref}`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}",
            HoumaoManagedAgentIdentity,
        )

    def get_managed_agent_state(self, agent_ref: str) -> HoumaoManagedAgentStateResponse:
        """Call `GET /houmao/agents/{agent_ref}/state`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/state",
            HoumaoManagedAgentStateResponse,
        )

    def get_managed_agent_state_detail(self, agent_ref: str) -> HoumaoManagedAgentDetailResponse:
        """Call `GET /houmao/agents/{agent_ref}/state/detail`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/state/detail",
            HoumaoManagedAgentDetailResponse,
        )

    def get_managed_agent_history(
        self,
        agent_ref: str,
        *,
        limit: int | None = None,
    ) -> HoumaoManagedAgentHistoryResponse:
        """Call `GET /houmao/agents/{agent_ref}/history`."""

        escaped = parse.quote(agent_ref, safe="")
        params: dict[str, str] | None = None
        if limit is not None:
            params = {"limit": str(limit)}
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/history",
            HoumaoManagedAgentHistoryResponse,
            params=params,
        )

    def submit_managed_agent_request(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentRequestEnvelope,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        """Call `POST /houmao/agents/{agent_ref}/requests`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/requests",
            HoumaoManagedAgentRequestAcceptedResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def launch_headless_agent(
        self,
        request_model: HoumaoHeadlessLaunchRequest,
    ) -> HoumaoHeadlessLaunchResponse:
        """Call `POST /houmao/agents/headless/launches`."""

        return self._request_root_model(
            "POST",
            "/houmao/agents/headless/launches",
            HoumaoHeadlessLaunchResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def stop_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        """Call `POST /houmao/agents/{agent_ref}/stop`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/stop",
            HoumaoManagedAgentActionResponse,
        )

    def submit_headless_turn(
        self,
        agent_ref: str,
        request_model: HoumaoHeadlessTurnRequest,
    ) -> HoumaoHeadlessTurnAcceptedResponse:
        """Call `POST /houmao/agents/{agent_ref}/turns`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/turns",
            HoumaoHeadlessTurnAcceptedResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def get_headless_turn_status(
        self,
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnStatusResponse:
        """Call `GET /houmao/agents/{agent_ref}/turns/{turn_id}`."""

        escaped_agent = parse.quote(agent_ref, safe="")
        escaped_turn = parse.quote(turn_id, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped_agent}/turns/{escaped_turn}",
            HoumaoHeadlessTurnStatusResponse,
        )

    def get_headless_turn_events(
        self,
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnEventsResponse:
        """Call `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`."""

        escaped_agent = parse.quote(agent_ref, safe="")
        escaped_turn = parse.quote(turn_id, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped_agent}/turns/{escaped_turn}/events",
            HoumaoHeadlessTurnEventsResponse,
        )

    def get_headless_turn_artifact_text(
        self,
        agent_ref: str,
        turn_id: str,
        *,
        artifact_name: str,
    ) -> str:
        """Call one raw headless artifact route and return the text body."""

        escaped_agent = parse.quote(agent_ref, safe="")
        escaped_turn = parse.quote(turn_id, safe="")
        payload, _status_code, _url = self._request_root_json(
            "GET",
            f"/houmao/agents/{escaped_agent}/turns/{escaped_turn}/artifacts/{artifact_name}",
            raw_text_ok=True,
        )
        if isinstance(payload, str):
            return payload
        return json.dumps(payload)

    def interrupt_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        """Call `POST /houmao/agents/{agent_ref}/interrupt`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/interrupt",
            HoumaoManagedAgentActionResponse,
        )

    def get_managed_agent_gateway_status(self, agent_ref: str) -> GatewayStatusV1:
        """Call `GET /houmao/agents/{agent_ref}/gateway`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/gateway",
            GatewayStatusV1,
        )

    def attach_managed_agent_gateway(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayAttachRequest | None = None,
    ) -> GatewayStatusV1:
        """Call `POST /houmao/agents/{agent_ref}/gateway/attach`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/attach",
            GatewayStatusV1,
            json_body=(
                request_model.model_dump(mode="json") if request_model is not None else None
            ),
        )

    def detach_managed_agent_gateway(self, agent_ref: str) -> GatewayStatusV1:
        """Call `POST /houmao/agents/{agent_ref}/gateway/detach`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/detach",
            GatewayStatusV1,
        )

    def get_managed_agent_gateway_memory(self, agent_ref: str) -> GatewayMemorySummaryV1:
        """Call `GET /houmao/agents/{agent_ref}/gateway/memory`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/gateway/memory",
            GatewayMemorySummaryV1,
        )

    def get_managed_agent_gateway_memory_memo(
        self,
        agent_ref: str,
    ) -> GatewayMemoryMemoResponseV1:
        """Call `GET /houmao/agents/{agent_ref}/gateway/memory/memo`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/gateway/memory/memo",
            GatewayMemoryMemoResponseV1,
        )

    def put_managed_agent_gateway_memory_memo(
        self,
        agent_ref: str,
        request_model: GatewayMemoryMemoWriteRequestV1,
    ) -> GatewayMemoryMemoResponseV1:
        """Call `PUT /houmao/agents/{agent_ref}/gateway/memory/memo`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "PUT",
            f"/houmao/agents/{escaped}/gateway/memory/memo",
            GatewayMemoryMemoResponseV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def append_managed_agent_gateway_memory_memo(
        self,
        agent_ref: str,
        request_model: GatewayMemoryMemoWriteRequestV1,
    ) -> GatewayMemoryMemoResponseV1:
        """Call `POST /houmao/agents/{agent_ref}/gateway/memory/memo/append`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/memory/memo/append",
            GatewayMemoryMemoResponseV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def list_managed_agent_gateway_memory_pages(
        self,
        agent_ref: str,
        request_model: GatewayMemoryPageTreeRequestV1,
    ) -> GatewayMemoryPageTreeResponseV1:
        """Call `POST /houmao/agents/{agent_ref}/gateway/memory/pages/tree`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/memory/pages/tree",
            GatewayMemoryPageTreeResponseV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def resolve_managed_agent_gateway_memory_page(
        self,
        agent_ref: str,
        request_model: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryPagePathResolutionV1:
        """Call `POST /houmao/agents/{agent_ref}/gateway/memory/pages/resolve`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/memory/pages/resolve",
            GatewayMemoryPagePathResolutionV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def read_managed_agent_gateway_memory_page(
        self,
        agent_ref: str,
        request_model: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryPageResponseV1:
        """Call `POST /houmao/agents/{agent_ref}/gateway/memory/pages/read`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/memory/pages/read",
            GatewayMemoryPageResponseV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def write_managed_agent_gateway_memory_page(
        self,
        agent_ref: str,
        request_model: GatewayMemoryPageWriteRequestV1,
    ) -> GatewayMemoryActionResponseV1:
        """Call `POST /houmao/agents/{agent_ref}/gateway/memory/pages/write`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/memory/pages/write",
            GatewayMemoryActionResponseV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def append_managed_agent_gateway_memory_page(
        self,
        agent_ref: str,
        request_model: GatewayMemoryPageWriteRequestV1,
    ) -> GatewayMemoryActionResponseV1:
        """Call `POST /houmao/agents/{agent_ref}/gateway/memory/pages/append`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/memory/pages/append",
            GatewayMemoryActionResponseV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def delete_managed_agent_gateway_memory_page(
        self,
        agent_ref: str,
        request_model: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryActionResponseV1:
        """Call `POST /houmao/agents/{agent_ref}/gateway/memory/pages/delete`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/memory/pages/delete",
            GatewayMemoryActionResponseV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def get_managed_agent_gateway_tui_state(self, agent_ref: str) -> HoumaoTerminalStateResponse:
        """Call `GET /houmao/agents/{agent_ref}/gateway/tui/state`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/gateway/tui/state",
            HoumaoTerminalStateResponse,
        )

    def get_managed_agent_gateway_tui_history(
        self,
        agent_ref: str,
        *,
        limit: int = 100,
    ) -> HoumaoTerminalSnapshotHistoryResponse:
        """Call `GET /houmao/agents/{agent_ref}/gateway/tui/history?limit=...`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/gateway/tui/history?limit={limit}",
            HoumaoTerminalSnapshotHistoryResponse,
        )

    def note_managed_agent_gateway_tui_prompt(
        self,
        agent_ref: str,
        *,
        prompt: str,
    ) -> HoumaoTerminalStateResponse:
        """Call `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/tui/note-prompt",
            HoumaoTerminalStateResponse,
            json_body=GatewayRequestPayloadSubmitPromptV1(prompt=prompt).model_dump(mode="json"),
        )

    def submit_managed_agent_gateway_request(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayRequestCreate,
    ) -> HoumaoManagedAgentGatewayRequestAcceptedResponse:
        """Call `POST /houmao/agents/{agent_ref}/gateway/requests`."""

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
        """Call `POST /houmao/agents/{agent_ref}/gateway/control/prompt`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/control/prompt",
            HoumaoManagedAgentGatewayPromptControlResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def get_managed_agent_gateway_headless_control_state(
        self,
        agent_ref: str,
    ) -> GatewayHeadlessControlStateV1:
        """Call `GET /houmao/agents/{agent_ref}/gateway/control/headless/state`."""

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
        """Call `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/control/headless/next-prompt-session",
            GatewayHeadlessControlStateV1,
            json_body=request_model.model_dump(mode="json"),
        )

    def submit_managed_agent_gateway_internal_headless_prompt(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayInternalHeadlessPromptRequest,
    ) -> CaoSuccessResponse:
        """Call `POST /houmao/agents/{agent_ref}/gateway/internal/headless-prompt`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/gateway/internal/headless-prompt",
            CaoSuccessResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def send_managed_agent_gateway_control_input(
        self,
        agent_ref: str,
        request_model: GatewayControlInputRequestV1,
    ) -> GatewayControlInputResultV1:
        """Call `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`."""

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
    ) -> GatewayMailNotifierStatusV1:
        """Call `GET /houmao/agents/{agent_ref}/gateway/mail-notifier`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/gateway/mail-notifier",
            GatewayMailNotifierStatusV1,
        )

    def put_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
        request_model: GatewayMailNotifierPutV1,
    ) -> GatewayMailNotifierStatusV1:
        """Call `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "PUT",
            f"/houmao/agents/{escaped}/gateway/mail-notifier",
            GatewayMailNotifierStatusV1,
            json_body=request_model.model_dump(mode="json", exclude_unset=True),
        )

    def delete_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
    ) -> GatewayMailNotifierStatusV1:
        """Call `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "DELETE",
            f"/houmao/agents/{escaped}/gateway/mail-notifier",
            GatewayMailNotifierStatusV1,
        )

    def list_managed_agent_gateway_reminders(
        self,
        agent_ref: str,
    ) -> GatewayReminderListV1:
        """Call `GET /houmao/agents/{agent_ref}/gateway/reminders`."""

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
        """Call `POST /houmao/agents/{agent_ref}/gateway/reminders`."""

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
        """Call `GET /houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}`."""

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
        """Call `PUT /houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}`."""

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
        """Call `DELETE /houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}`."""

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
        """Call `GET /houmao/agents/{agent_ref}/mail/status`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/mail/status",
            HoumaoManagedAgentMailStatusResponse,
        )

    def get_managed_agent_mail_resolve_live(
        self,
        agent_ref: str,
    ) -> dict[str, object]:
        """Call `GET /houmao/agents/{agent_ref}/mail/resolve-live`."""

        escaped = parse.quote(agent_ref, safe="")
        payload, _, _url = self._request_root_json(
            "GET",
            f"/houmao/agents/{escaped}/mail/resolve-live",
        )
        if not isinstance(payload, dict):
            raise CaoApiError(
                method="GET",
                url=f"{self.base_url}/houmao/agents/{escaped}/mail/resolve-live",
                detail="Expected an object response.",
                payload=payload,
            )
        return payload

    def list_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailListRequest,
    ) -> HoumaoManagedAgentMailListResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/list`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/list",
            HoumaoManagedAgentMailListResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def peek_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailMessageRequest,
    ) -> HoumaoManagedAgentMailMessageResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/peek`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/peek",
            HoumaoManagedAgentMailMessageResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def read_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailMessageRequest,
    ) -> HoumaoManagedAgentMailMessageResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/read`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/read",
            HoumaoManagedAgentMailMessageResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def send_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailSendRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/send`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/send",
            HoumaoManagedAgentMailActionResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def post_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailPostRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/post`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/post",
            HoumaoManagedAgentMailActionResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def reply_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailReplyRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/reply`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/reply",
            HoumaoManagedAgentMailActionResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def mark_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailMarkRequest,
    ) -> HoumaoManagedAgentMailLifecycleResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/mark`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/mark",
            HoumaoManagedAgentMailLifecycleResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def move_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailMoveRequest,
    ) -> HoumaoManagedAgentMailLifecycleResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/move`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/move",
            HoumaoManagedAgentMailLifecycleResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def archive_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailArchiveRequest,
    ) -> HoumaoManagedAgentMailLifecycleResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/archive`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/archive",
            HoumaoManagedAgentMailLifecycleResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def _request_root_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: object | None = None,
        raw_text_ok: bool = False,
    ) -> tuple[object, int, str]:
        query = parse.urlencode(params or {})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"

        data: bytes | None = None
        headers = {"Accept": "application/json"}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if method.upper() in {"POST", "PUT", "PATCH"}:
            data = b"" if data is None else data

        req = request.Request(url, data=data, method=method, headers=headers)
        try:
            with scoped_loopback_no_proxy_for_cao_base_url(self.base_url):
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    body_text = response.read().decode("utf-8")
                    try:
                        payload = json.loads(body_text)
                    except json.JSONDecodeError:
                        if raw_text_ok:
                            payload = body_text
                        else:
                            raise
                    return payload, int(response.status), url
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            payload = None
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = {"detail": body.strip() or str(exc)}
            detail = _extract_detail(payload)
            raise CaoApiError(
                method=method,
                url=url,
                detail=detail,
                status_code=int(exc.code),
                payload=payload,
            ) from exc
        except error.URLError as exc:
            raise CaoApiError(
                method=method,
                url=url,
                detail=str(exc.reason),
            ) from exc
        except (TimeoutError, OSError) as exc:
            raise CaoApiError(
                method=method,
                url=url,
                detail=f"Connection failed after {self.timeout_seconds}s: {exc}",
            ) from exc

    def _request_root_model(
        self,
        method: str,
        path: str,
        model: type[_ModelT],
        *,
        params: dict[str, str] | None = None,
        json_body: object | None = None,
    ) -> _ModelT:
        payload, status_code, url = self._request_root_json(
            method,
            path,
            params=params,
            json_body=json_body,
        )
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            raise CaoApiError(
                method=method,
                url=url,
                status_code=status_code,
                detail=_format_validation_error(exc),
                payload=payload,
            ) from exc


def _extract_detail(payload: object) -> str:
    if isinstance(payload, dict) and "detail" in payload:
        return str(payload["detail"])
    return f"Unexpected response payload type: {type(payload).__name__}"
