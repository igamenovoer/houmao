"""Managed endpoint operations shared by the passive and retained server clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar
from urllib import parse

from pydantic import BaseModel

from houmao.agents.realm_controller.gateway_models import (
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
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
)
from houmao.cao.models import CaoSuccessResponse
from houmao.cao.rest_client import CaoApiError
from houmao.mailbox.models import MailChannel
from houmao.mailbox.online_models import (
    OnlineAttachRequest,
    OnlineBindingStatus,
    OnlineControlRequest,
)
from houmao.server._http_transport import validate_root_model
from houmao.server.models import (
    HoumaoManagedAgentGatewayAttachRequest,
    HoumaoManagedAgentGatewayInternalHeadlessPromptRequest,
    HoumaoManagedAgentMailArchiveRequest,
    HoumaoManagedAgentMailLifecycleResponse,
    HoumaoManagedAgentMailMarkRequest,
    HoumaoManagedAgentMailMessageRequest,
    HoumaoManagedAgentMailMessageResponse,
    HoumaoManagedAgentMailMoveRequest,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class ManagedPairOperations(ABC):
    """Map shared managed operations onto each client's own request transport."""

    @abstractmethod
    def _request_root_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: object | None = None,
        timeout_seconds: float | None = None,
    ) -> tuple[object, int, str]:
        """Read a JSON payload, its response status, and its request URL."""

    def _request_root_model(
        self,
        method: str,
        path: str,
        model: type[_ModelT],
        *,
        params: dict[str, str] | None = None,
        json_body: object | None = None,
        timeout_seconds: float | None = None,
    ) -> _ModelT:
        """Send a typed request through the concrete client's transport."""

        if timeout_seconds is None:
            response = self._request_root_json(method, path, params=params, json_body=json_body)
        else:
            response = self._request_root_json(
                method, path, params=params, json_body=json_body, timeout_seconds=timeout_seconds
            )
        return validate_root_model(method, response, model)

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

    def get_managed_agent_online_binding(self, agent_ref: str) -> OnlineBindingStatus:
        """Read the agent's safe configured online binding."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/mail/online/binding",
            OnlineBindingStatus,
        )

    def attach_managed_agent_online_binding(
        self, agent_ref: str, request_model: OnlineAttachRequest
    ) -> OnlineBindingStatus:
        """Attach the agent's revision-pinned online binding."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "PUT",
            f"/houmao/agents/{escaped}/mail/online/binding",
            OnlineBindingStatus,
            json_body=request_model.model_dump(mode="json"),
            timeout_seconds=request_model.timeout_seconds * 8 + 10,
        )

    def refresh_managed_agent_online_binding(
        self, agent_ref: str, request_model: OnlineControlRequest
    ) -> OnlineBindingStatus:
        """Refresh the agent's revision-pinned online binding."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/online/binding/refresh",
            OnlineBindingStatus,
            json_body=request_model.model_dump(mode="json"),
            timeout_seconds=request_model.timeout_seconds * 8 + 10,
        )

    def reconnect_managed_agent_online_binding(
        self, agent_ref: str, request_model: OnlineControlRequest
    ) -> OnlineBindingStatus:
        """Reconnect the agent's revision-pinned online binding."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/online/binding/reconnect",
            OnlineBindingStatus,
            json_body=request_model.model_dump(mode="json"),
            timeout_seconds=request_model.timeout_seconds * 8 + 10,
        )

    def detach_managed_agent_online_binding(
        self, agent_ref: str, request_model: OnlineControlRequest
    ) -> OnlineBindingStatus:
        """Detach the agent's revision-pinned online binding."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "DELETE",
            f"/houmao/agents/{escaped}/mail/online/binding",
            OnlineBindingStatus,
            json_body=request_model.model_dump(mode="json"),
            timeout_seconds=request_model.timeout_seconds * 8 + 10,
        )

    def get_managed_agent_mail_resolve_live(
        self,
        agent_ref: str,
    ) -> dict[str, object]:
        """Call `GET /houmao/agents/{agent_ref}/mail/resolve-live`."""

        escaped = parse.quote(agent_ref, safe="")
        payload, _, url = self._request_root_json(
            "GET",
            f"/houmao/agents/{escaped}/mail/resolve-live",
        )
        if not isinstance(payload, dict):
            raise CaoApiError(
                method="GET",
                url=url,
                detail="Expected an object response.",
                payload=payload,
            )
        return payload

    def peek_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailMessageRequest,
        *,
        channel: MailChannel,
    ) -> HoumaoManagedAgentMailMessageResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/{channel}/peek`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/{channel}/peek",
            HoumaoManagedAgentMailMessageResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def read_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailMessageRequest,
        *,
        channel: MailChannel,
    ) -> HoumaoManagedAgentMailMessageResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/{channel}/read`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/{channel}/read",
            HoumaoManagedAgentMailMessageResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def mark_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailMarkRequest,
        *,
        channel: MailChannel,
    ) -> HoumaoManagedAgentMailLifecycleResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/{channel}/mark`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/{channel}/mark",
            HoumaoManagedAgentMailLifecycleResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def move_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailMoveRequest,
        *,
        channel: MailChannel,
    ) -> HoumaoManagedAgentMailLifecycleResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/{channel}/move`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/{channel}/move",
            HoumaoManagedAgentMailLifecycleResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def archive_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailArchiveRequest,
        *,
        channel: MailChannel,
    ) -> HoumaoManagedAgentMailLifecycleResponse:
        """Call `POST /houmao/agents/{agent_ref}/mail/{channel}/archive`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/mail/{channel}/archive",
            HoumaoManagedAgentMailLifecycleResponse,
            json_body=request_model.model_dump(mode="json"),
        )
