"""HTTP client for live agent gateway surfaces."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Mapping, TypeVar, cast
from urllib import error, request

from pydantic import BaseModel, ValidationError

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayControlInputRequestV1,
    GatewayControlInputResultV1,
    GatewayHeadlessControlStateV1,
    GatewayHeadlessNextPromptSessionRequestV1,
    GatewayHealthResponseV1,
    GatewayHost,
    GatewayJsonObject,
    GatewayJsonValue,
    GatewayMailActionResponseV1,
    GatewayMailArchiveRequestV1,
    GatewayMailLifecycleResponseV1,
    GatewayMailListRequestV1,
    GatewayMailListResponseV1,
    GatewayMailMarkRequestV1,
    GatewayMailMessageRequestV1,
    GatewayMailMessageResponseV1,
    GatewayMailMoveRequestV1,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayMailPostRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    GatewayMailStatusV1,
    GatewayPromptControlRequestV1,
    GatewayPromptControlResultV1,
    GatewayRequestCreateV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderCreateResultV1,
    GatewayReminderDeleteResultV1,
    GatewayReminderListV1,
    GatewayReminderPutV1,
    GatewayReminderV1,
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
from houmao.server.models import (
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)
GATEWAY_RESPECT_PROXY_ENV_VAR = "HOUMAO_GATEWAY_RESPECT_PROXY_ENV"


def gateway_client_respects_proxy_env(env: Mapping[str, str] | None = None) -> bool:
    """Return whether gateway HTTP clients should use ambient proxy settings."""

    source = os.environ if env is None else env
    return source.get(GATEWAY_RESPECT_PROXY_ENV_VAR) == "1"


@dataclass(frozen=True)
class GatewayEndpoint:
    """Resolved live gateway listener endpoint.

    Attributes
    ----------
    host:
        Bound listener host published by the runtime.
    port:
        Bound TCP port published by the runtime.
    """

    host: GatewayHost
    port: int


class GatewayClient:
    """HTTP client for a live per-agent gateway instance."""

    def __init__(self, *, endpoint: GatewayEndpoint, timeout_seconds: float = 5.0) -> None:
        """Initialize a gateway HTTP client.

        Parameters
        ----------
        endpoint:
            Live gateway listener endpoint discovered from runtime state.
        timeout_seconds:
            Per-request timeout used for HTTP round-trips.
        """

        self.m_endpoint = endpoint
        self.m_timeout_seconds = timeout_seconds
        self.m_opener = _build_gateway_client_opener(
            respect_proxy_env=gateway_client_respects_proxy_env()
        )

    def health(self) -> GatewayHealthResponseV1:
        """Call `GET /health`."""

        return self._request_model("GET", "/health", GatewayHealthResponseV1)

    def status(self) -> GatewayStatusV1:
        """Call `GET /v1/status`."""

        return self._request_model("GET", "/v1/status", GatewayStatusV1)

    def memory(self) -> GatewayMemorySummaryV1:
        """Call `GET /v1/memory`."""

        return self._request_model("GET", "/v1/memory", GatewayMemorySummaryV1)

    def read_memory_memo(self) -> GatewayMemoryMemoResponseV1:
        """Call `GET /v1/memory/memo`."""

        return self._request_model("GET", "/v1/memory/memo", GatewayMemoryMemoResponseV1)

    def write_memory_memo(
        self,
        payload: GatewayMemoryMemoWriteRequestV1,
    ) -> GatewayMemoryMemoResponseV1:
        """Call `PUT /v1/memory/memo`."""

        return self._request_model(
            "PUT",
            "/v1/memory/memo",
            GatewayMemoryMemoResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def append_memory_memo(
        self,
        payload: GatewayMemoryMemoWriteRequestV1,
    ) -> GatewayMemoryMemoResponseV1:
        """Call `POST /v1/memory/memo/append`."""

        return self._request_model(
            "POST",
            "/v1/memory/memo/append",
            GatewayMemoryMemoResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def list_memory_pages(
        self,
        payload: GatewayMemoryPageTreeRequestV1,
    ) -> GatewayMemoryPageTreeResponseV1:
        """Call `POST /v1/memory/pages/tree`."""

        return self._request_model(
            "POST",
            "/v1/memory/pages/tree",
            GatewayMemoryPageTreeResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def resolve_memory_page_path(
        self,
        payload: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryPagePathResolutionV1:
        """Call `POST /v1/memory/pages/resolve`."""

        return self._request_model(
            "POST",
            "/v1/memory/pages/resolve",
            GatewayMemoryPagePathResolutionV1,
            body=payload.model_dump(mode="json"),
        )

    def read_memory_page(
        self,
        payload: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryPageResponseV1:
        """Call `POST /v1/memory/pages/read`."""

        return self._request_model(
            "POST",
            "/v1/memory/pages/read",
            GatewayMemoryPageResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def write_memory_page(
        self,
        payload: GatewayMemoryPageWriteRequestV1,
    ) -> GatewayMemoryActionResponseV1:
        """Call `POST /v1/memory/pages/write`."""

        return self._request_model(
            "POST",
            "/v1/memory/pages/write",
            GatewayMemoryActionResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def append_memory_page(
        self,
        payload: GatewayMemoryPageWriteRequestV1,
    ) -> GatewayMemoryActionResponseV1:
        """Call `POST /v1/memory/pages/append`."""

        return self._request_model(
            "POST",
            "/v1/memory/pages/append",
            GatewayMemoryActionResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def delete_memory_page(
        self,
        payload: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryActionResponseV1:
        """Call `POST /v1/memory/pages/delete`."""

        return self._request_model(
            "POST",
            "/v1/memory/pages/delete",
            GatewayMemoryActionResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def mail_status(self) -> GatewayMailStatusV1:
        """Call `GET /v1/mail/status`."""

        return self._request_model("GET", "/v1/mail/status", GatewayMailStatusV1)

    def list_mail(self, payload: GatewayMailListRequestV1) -> GatewayMailListResponseV1:
        """Call `POST /v1/mail/list`."""

        return self._request_model(
            "POST",
            "/v1/mail/list",
            GatewayMailListResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def peek_mail(self, payload: GatewayMailMessageRequestV1) -> GatewayMailMessageResponseV1:
        """Call `POST /v1/mail/peek`."""

        return self._request_model(
            "POST",
            "/v1/mail/peek",
            GatewayMailMessageResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def read_mail(self, payload: GatewayMailMessageRequestV1) -> GatewayMailMessageResponseV1:
        """Call `POST /v1/mail/read`."""

        return self._request_model(
            "POST",
            "/v1/mail/read",
            GatewayMailMessageResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def send_mail(self, payload: GatewayMailSendRequestV1) -> GatewayMailActionResponseV1:
        """Call `POST /v1/mail/send`."""

        return self._request_model(
            "POST",
            "/v1/mail/send",
            GatewayMailActionResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def post_mail(self, payload: GatewayMailPostRequestV1) -> GatewayMailActionResponseV1:
        """Call `POST /v1/mail/post`."""

        return self._request_model(
            "POST",
            "/v1/mail/post",
            GatewayMailActionResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def reply_mail(self, payload: GatewayMailReplyRequestV1) -> GatewayMailActionResponseV1:
        """Call `POST /v1/mail/reply`."""

        return self._request_model(
            "POST",
            "/v1/mail/reply",
            GatewayMailActionResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def mark_mail(self, payload: GatewayMailMarkRequestV1) -> GatewayMailLifecycleResponseV1:
        """Call `POST /v1/mail/mark`."""

        return self._request_model(
            "POST",
            "/v1/mail/mark",
            GatewayMailLifecycleResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def move_mail(self, payload: GatewayMailMoveRequestV1) -> GatewayMailLifecycleResponseV1:
        """Call `POST /v1/mail/move`."""

        return self._request_model(
            "POST",
            "/v1/mail/move",
            GatewayMailLifecycleResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def archive_mail(self, payload: GatewayMailArchiveRequestV1) -> GatewayMailLifecycleResponseV1:
        """Call `POST /v1/mail/archive`."""

        return self._request_model(
            "POST",
            "/v1/mail/archive",
            GatewayMailLifecycleResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def create_request(self, payload: GatewayRequestCreateV1) -> GatewayAcceptedRequestV1:
        """Call `POST /v1/requests`."""

        return self._request_model(
            "POST",
            "/v1/requests",
            GatewayAcceptedRequestV1,
            body=payload.model_dump(mode="json"),
        )

    def create_reminders(
        self, payload: GatewayReminderCreateBatchV1
    ) -> GatewayReminderCreateResultV1:
        """Call `POST /v1/reminders`."""

        return self._request_model(
            "POST",
            "/v1/reminders",
            GatewayReminderCreateResultV1,
            body=payload.model_dump(mode="json"),
        )

    def list_reminders(self) -> GatewayReminderListV1:
        """Call `GET /v1/reminders`."""

        return self._request_model("GET", "/v1/reminders", GatewayReminderListV1)

    def get_reminder(self, *, reminder_id: str) -> GatewayReminderV1:
        """Call `GET /v1/reminders/{reminder_id}`."""

        return self._request_model("GET", f"/v1/reminders/{reminder_id}", GatewayReminderV1)

    def put_reminder(self, *, reminder_id: str, payload: GatewayReminderPutV1) -> GatewayReminderV1:
        """Call `PUT /v1/reminders/{reminder_id}`."""

        return self._request_model(
            "PUT",
            f"/v1/reminders/{reminder_id}",
            GatewayReminderV1,
            body=payload.model_dump(mode="json"),
        )

    def delete_reminder(self, *, reminder_id: str) -> GatewayReminderDeleteResultV1:
        """Call `DELETE /v1/reminders/{reminder_id}`."""

        return self._request_model(
            "DELETE",
            f"/v1/reminders/{reminder_id}",
            GatewayReminderDeleteResultV1,
        )

    def control_prompt(
        self,
        payload: GatewayPromptControlRequestV1,
    ) -> GatewayPromptControlResultV1:
        """Call `POST /v1/control/prompt`."""

        return self._request_model(
            "POST",
            "/v1/control/prompt",
            GatewayPromptControlResultV1,
            body=payload.model_dump(mode="json"),
        )

    def get_tui_state(self) -> HoumaoTerminalStateResponse:
        """Call `GET /v1/control/tui/state`."""

        return self._request_model(
            "GET",
            "/v1/control/tui/state",
            HoumaoTerminalStateResponse,
        )

    def get_tui_history(self, *, limit: int) -> HoumaoTerminalSnapshotHistoryResponse:
        """Call `GET /v1/control/tui/history?limit=...`."""

        return self._request_model(
            "GET",
            f"/v1/control/tui/history?limit={limit}",
            HoumaoTerminalSnapshotHistoryResponse,
        )

    def note_tui_prompt_submission(self, *, prompt: str) -> HoumaoTerminalStateResponse:
        """Call `POST /v1/control/tui/note-prompt`."""

        return self._request_model(
            "POST",
            "/v1/control/tui/note-prompt",
            HoumaoTerminalStateResponse,
            body={"prompt": prompt},
        )

    def send_control_input(
        self,
        payload: GatewayControlInputRequestV1,
    ) -> GatewayControlInputResultV1:
        """Call `POST /v1/control/send-keys`."""

        return self._request_model(
            "POST",
            "/v1/control/send-keys",
            GatewayControlInputResultV1,
            body=payload.model_dump(mode="json"),
        )

    def get_headless_control_state(self) -> GatewayHeadlessControlStateV1:
        """Call `GET /v1/control/headless/state`."""

        return self._request_model(
            "GET",
            "/v1/control/headless/state",
            GatewayHeadlessControlStateV1,
        )

    def set_headless_next_prompt_session(
        self,
        payload: GatewayHeadlessNextPromptSessionRequestV1,
    ) -> GatewayHeadlessControlStateV1:
        """Call `POST /v1/control/headless/next-prompt-session`."""

        return self._request_model(
            "POST",
            "/v1/control/headless/next-prompt-session",
            GatewayHeadlessControlStateV1,
            body=payload.model_dump(mode="json"),
        )

    def get_mail_notifier(self) -> GatewayMailNotifierStatusV1:
        """Call `GET /v1/mail-notifier`."""

        return self._request_model("GET", "/v1/mail-notifier", GatewayMailNotifierStatusV1)

    def put_mail_notifier(self, payload: GatewayMailNotifierPutV1) -> GatewayMailNotifierStatusV1:
        """Call `PUT /v1/mail-notifier`."""

        return self._request_model(
            "PUT",
            "/v1/mail-notifier",
            GatewayMailNotifierStatusV1,
            body=payload.model_dump(mode="json"),
        )

    def delete_mail_notifier(self) -> GatewayMailNotifierStatusV1:
        """Call `DELETE /v1/mail-notifier`."""

        return self._request_model("DELETE", "/v1/mail-notifier", GatewayMailNotifierStatusV1)

    def _request_model(
        self,
        method: str,
        path: str,
        model: type[_ModelT],
        *,
        body: GatewayJsonObject | None = None,
    ) -> _ModelT:
        """Send one HTTP request and validate the response model.

        Parameters
        ----------
        method:
            HTTP method to issue.
        path:
            Relative gateway route beginning with `/`.
        model:
            Pydantic model used to validate the decoded response payload.
        body:
            Optional JSON request body.

        Returns
        -------
        _ModelT
            Validated response payload.
        """

        url = self._build_url(path)
        payload: bytes | None = None
        headers: dict[str, str] = {}
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request_obj = request.Request(
            url=url,
            data=payload,
            method=method,
            headers=headers,
        )
        decoded = self._decode_response(
            method=method,
            url=url,
            response=self._open_request(request_obj=request_obj, method=method, url=url),
        )

        try:
            return model.model_validate(decoded)
        except ValidationError as exc:
            raise GatewayHttpError(
                method=method,
                url=url,
                detail=f"gateway returned invalid payload: {exc}",
            ) from exc

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: GatewayJsonObject | None = None,
    ) -> GatewayJsonValue:
        """Send one HTTP request and return decoded JSON."""

        url = self._build_url(path)
        payload: bytes | None = None
        headers: dict[str, str] = {}
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request_obj = request.Request(
            url=url,
            data=payload,
            method=method,
            headers=headers,
        )
        return self._decode_response(
            method=method,
            url=url,
            response=self._open_request(request_obj=request_obj, method=method, url=url),
        )

    def _open_request(self, *, request_obj: request.Request, method: str, url: str) -> bytes:
        """Open one gateway request without consulting environment proxy settings."""

        try:
            with self.m_opener.open(request_obj, timeout=self.m_timeout_seconds) as response:
                return cast(bytes, response.read())
        except error.HTTPError as exc:
            detail = self._decode_error_body(exc.read())
            raise GatewayHttpError(
                method=method,
                url=url,
                detail=detail,
                status_code=exc.code,
            ) from exc
        except error.URLError as exc:
            raise GatewayHttpError(
                method=method,
                url=url,
                detail=str(exc.reason),
            ) from exc
        except (TimeoutError, OSError) as exc:
            raise GatewayHttpError(
                method=method,
                url=url,
                detail=str(exc),
            ) from exc

    def _build_url(self, path: str) -> str:
        """Build the concrete local URL for one gateway route."""

        connect_host = "127.0.0.1" if self.m_endpoint.host == "0.0.0.0" else self.m_endpoint.host
        return f"http://{connect_host}:{self.m_endpoint.port}{path}"

    def _decode_response(
        self,
        *,
        method: str,
        url: str,
        response: bytes,
    ) -> GatewayJsonValue:
        """Decode one gateway JSON response body.

        Parameters
        ----------
        method:
            HTTP method used for the request.
        url:
            Fully resolved request URL.
        response:
            Raw response bytes returned by the server.

        Returns
        -------
        GatewayJsonValue
            Parsed JSON payload.
        """

        try:
            return cast(GatewayJsonValue, json.loads(response.decode("utf-8")))
        except json.JSONDecodeError as exc:
            raise GatewayHttpError(
                method=method,
                url=url,
                detail=f"gateway returned invalid JSON: {exc}",
            ) from exc

    def _decode_error_body(self, payload: bytes) -> str:
        """Decode one gateway error payload into a readable detail string.

        Parameters
        ----------
        payload:
            Raw error payload returned by the gateway.

        Returns
        -------
        str
            Human-readable error detail extracted from the payload.
        """

        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return payload.decode("utf-8", errors="replace")
        if isinstance(decoded, dict) and "detail" in decoded:
            detail = decoded["detail"]
            if isinstance(detail, str):
                return detail
            return json.dumps(detail, sort_keys=True)
        return json.dumps(decoded, sort_keys=True)


def _build_gateway_client_opener(*, respect_proxy_env: bool) -> request.OpenerDirector:
    """Build a gateway HTTP opener using the resolved proxy policy."""

    if respect_proxy_env:
        return request.build_opener()
    return request.build_opener(request.ProxyHandler({}))
