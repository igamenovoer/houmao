"""HTTP client for live agent gateway surfaces."""

from __future__ import annotations

from houmao.mailbox.online_models import (
    OnlineAttachRequest,
    OnlineControlRequest,
    OnlineBindingStatus,
)

import json
import os
import ssl
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, TypeVar, cast
from urllib import error, parse, request

from pydantic import BaseModel, ValidationError

from houmao.ag_ui.models import AgUiEventPublishRequest, AgUiEventPublishResponse
from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.usage_models import UsagePage
from houmao.agents.realm_controller.native_refresh_models import (
    CommonPluginObservationV1,
    NativeHomeV1,
    NativeRefreshRequestV1,
    NativeRefreshResultV1,
    native_home_etag,
)
from houmao.mailbox.models import MailChannel
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
    GatewayWebControlStateV1,
    GatewayWebHistoryV1,
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
from houmao.gateway.plugins import GatewayPluginStatusResponse, PluginStatus
from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    GatewayAdminKey,
    GatewayChallenge,
    GatewayChallengeRequest,
    GatewayClientBinding,
    GatewayRequestBinding,
    load_gateway_signer,
    parse_access_document,
    public_key_text,
    sign_sshsig,
    sshsig_header,
)
from houmao.gateway.deployment import (
    GatewayEndpointDescriptor,
    owner_gateway_base_url,
    validate_gateway_base_url,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)
GATEWAY_RESPECT_PROXY_ENV_VAR = "HOUMAO_GATEWAY_RESPECT_PROXY_ENV"
_UNSIGNED_ROUTES = {
    "/health",
    "/v1/endpoint",
    "/v1/auth/challenge",
    "/v1/messages",
    "/v1/public/prompt",
}
_MAX_RESPONSE_BYTES = 16 * 1024 * 1024


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

    def __init__(
        self,
        *,
        endpoint: GatewayEndpoint | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 5.0,
        binding: GatewayClientBinding | None = None,
        target_incarnation: str | None = None,
        ca_bundle_path: Path | None = None,
        registration_key: GatewayAdminKey | None = None,
        request_proof: Callable[[str, str, bytes], Mapping[str, str]] | None = None,
        respect_proxy_env: bool | None = None,
    ) -> None:
        """Initialize a gateway HTTP client.

        Parameters
        ----------
        endpoint:
            Live gateway listener endpoint discovered from runtime state.
        timeout_seconds:
            Per-request timeout used for HTTP round-trips.
        """

        if endpoint is not None:
            if base_url is not None:
                raise ValueError("Select one gateway endpoint.")
            if endpoint.host not in {"127.0.0.1", "0.0.0.0"}:
                raise ValueError("A listener coordinate requires an owner-local host.")
            base_url = owner_gateway_base_url(endpoint.port)
        if base_url is None:
            if binding is None:
                raise ValueError("A gateway endpoint is required.")
            base_url = binding.base_url
        self.m_base_url = validate_gateway_base_url(base_url)
        if binding is not None and (
            binding.base_url != self.m_base_url or request_proof is not None
        ):
            raise ValueError(
                "Gateway signer binding differs from the selected endpoint or proof source."
            )
        if (registration_key is not None) != (
            binding is not None and binding.purpose == "register"
        ):
            raise ValueError(
                "First registration requires an explicit proposed public key and signer."
            )
        if binding is not None and binding.ca_bundle_path is not None:
            selected_trust = Path(binding.ca_bundle_path)
            if ca_bundle_path is not None and ca_bundle_path != selected_trust:
                raise ValueError("Gateway binding selects different certificate trust.")
            ca_bundle_path = selected_trust
        self.m_binding = binding
        self.m_target_incarnation = target_incarnation
        self.m_registration_key = registration_key
        self.m_request_proof = request_proof
        self.m_timeout_seconds = timeout_seconds
        self.m_native_home_etag: str | None = None
        try:
            ssl_context = (
                ssl.create_default_context(cafile=str(ca_bundle_path) if ca_bundle_path else None)
                if self.m_base_url.startswith("https:")
                else None
            )
        except (OSError, ValueError):
            raise ValueError("Gateway certificate trust is unavailable.") from None
        self.m_opener = _build_gateway_client_opener(
            respect_proxy_env=(
                gateway_client_respects_proxy_env()
                if respect_proxy_env is None
                else respect_proxy_env
            ),
            ssl_context=ssl_context,
        )

    def health(self) -> GatewayHealthResponseV1:
        """Call `GET /health`."""

        return self._request_model("GET", "/health", GatewayHealthResponseV1)

    def describe_endpoint(self) -> GatewayEndpointDescriptor:
        """Read public live endpoint and access metadata."""

        return self._request_model("GET", "/v1/endpoint", GatewayEndpointDescriptor)

    def add_admin_key(self, key: GatewayAdminKey) -> str:
        """Enroll the proposed first key or add a key with a listed admin signer."""

        result = self._request_json("POST", "/v1/admin/keys", body=key.model_dump(mode="json"))
        if result != {"key_id": key.key_id}:
            raise GatewayHttpError(
                method="POST",
                url=self._build_url("/v1/admin/keys"),
                detail="Gateway did not confirm the selected key enrollment.",
            )
        return key.key_id

    def remove_admin_key(self, key_id: str) -> None:
        """Remove a key with current listed admin proof."""

        path = f"/v1/admin/keys/{parse.quote(key_id, safe='')}"
        url = self._build_url(path)
        request_obj = self._prepare_request("DELETE", path, None, {})
        self._open_request(request_obj=request_obj, method="DELETE", url=url)

    def request_plugin_json(
        self, method: str, path: str, *, body: GatewayJsonObject | None = None
    ) -> GatewayJsonValue:
        """Call one plugin operation through the same proof and transport path."""

        if not path.startswith("/v1/plugins/"):
            raise ValueError("Plugin operations must use the gateway plugin namespace.")
        return self._request_json(method, path, body=body)

    def status(self) -> GatewayStatusV1:
        """Call `GET /v1/status`."""

        return self._request_model("GET", "/v1/status", GatewayStatusV1)

    def get_native_home(self) -> NativeHomeV1:
        """Read the bound native home without inspecting configuration contents."""

        home = self._request_native_read_model("/v1/native-home", NativeHomeV1)
        self._require_native_home_matches(home, method="GET", path="/v1/native-home")
        return home

    def bind_native_home(self, home: NativeHomeV1) -> None:
        """Fence subsequent common-resource requests to captured native authority."""

        self.m_native_home_etag = native_home_etag(home)

    def _require_native_home_matches(self, home: NativeHomeV1, *, method: str, path: str) -> None:
        """Reject a response from another execution without exposing its private inputs."""

        if (
            self.m_native_home_etag is not None
            and native_home_etag(home) != self.m_native_home_etag
        ):
            raise GatewayHttpError(
                method=method,
                url=self._build_url(path),
                status_code=412,
                detail="Gateway native execution authority changed.",
            )

    def get_common_plugin_state(self) -> CommonPluginObservationV1:
        """Observe skills/MCP freshness without initiating native refresh."""

        observation = self._request_native_read_model(
            "/v1/control/refresh", CommonPluginObservationV1
        )
        self._require_native_home_matches(
            observation.home, method="GET", path="/v1/control/refresh"
        )
        return observation

    def _request_native_read_model(self, path: str, model: type[_ModelT]) -> _ModelT:
        """Keep invalid native configuration or transport details out of read errors."""

        try:
            return self._request_model("GET", path, model)
        except GatewayHttpError as exc:
            raise GatewayHttpError(
                method="GET",
                url=self._build_url(path),
                status_code=exc.status_code,
                detail="Gateway native resource observation is unavailable.",
            ) from None
        except ValueError:
            raise GatewayHttpError(
                method="GET",
                url=self._build_url(path),
                detail="Gateway native resource observation returned an invalid response.",
            ) from None

    def refresh_native(self, payload: NativeRefreshRequestV1) -> NativeRefreshResultV1:
        """Request one bounded native refresh and preserve typed refusal results.

        The native operation is never retried. Typed non-success responses are
        returned as outcomes so CLI and passive-server callers retain common
        observations, native effects, and restart/uncertainty information.
        """

        url = self._build_url("/v1/control/refresh")
        request_obj = self._prepare_request(
            "POST",
            "/v1/control/refresh",
            payload.model_dump_json().encode("utf-8"),
            {
                "Content-Type": "application/json",
                **({"If-Match": self.m_native_home_etag} if self.m_native_home_etag else {}),
            },
        )
        try:
            with self.m_opener.open(
                request_obj, timeout=(payload.timeout_seconds or 30.0) + 5.0
            ) as response:
                encoded = response.read(_MAX_RESPONSE_BYTES + 1)
        except error.HTTPError as exc:
            if exc.code in {401, 403} or 300 <= exc.code < 400:
                raise self._http_refusal("POST", url, exc) from None
            encoded = exc.read(_MAX_RESPONSE_BYTES + 1)
            try:
                result = NativeRefreshResultV1.model_validate_json(encoded)
            except ValidationError:
                if exc.code == 503:
                    raise GatewayHttpError(
                        method="POST", url=url, status_code=503, detail="Gateway is unavailable."
                    ) from None
                raise GatewayHttpError(
                    method="POST",
                    url=url,
                    status_code=exc.code,
                    detail="Gateway refresh returned an invalid typed refusal.",
                ) from None
            self._require_native_refresh_matches(result)
            return result
        except (error.URLError, TimeoutError, OSError):
            raise GatewayHttpError(
                method="POST",
                url=url,
                detail="Gateway refresh confirmation is unavailable; the operation was not retried.",
            ) from None
        try:
            result = NativeRefreshResultV1.model_validate_json(encoded)
        except ValidationError:
            raise GatewayHttpError(
                method="POST", url=url, detail="Gateway refresh returned an invalid result."
            ) from None
        self._require_native_refresh_matches(result)
        return result

    def _require_native_refresh_matches(self, result: NativeRefreshResultV1) -> None:
        """Keep both refresh observations within the client-captured execution."""

        for observation in (result.observation, result.before):
            if observation is not None:
                self._require_native_home_matches(
                    observation.home, method="POST", path="/v1/control/refresh"
                )

    def get_plugins(self) -> GatewayPluginStatusResponse:
        """Read host-maintained plugin status and active configuration identity."""

        return self._request_model("GET", "/v1/plugins", GatewayPluginStatusResponse)

    def get_plugin_status(self, instance_id: str) -> PluginStatus:
        """Read one host-maintained plugin status snapshot."""

        encoded = parse.quote(instance_id, safe="")
        return self._request_model("GET", f"/v1/plugins/{encoded}/_status", PluginStatus)

    def get_usage(self, *, after: str | None = None, limit: int = 100) -> UsagePage:
        """Read a bounded finalized usage page without changing agent execution.

        Parameters
        ----------
        after:
            Opaque cursor returned by an earlier page, including an empty page.
        limit:
            Maximum number of records, between one and 500.
        """

        query = {"limit": str(limit)}
        if after is not None:
            query["after"] = after
        return self._request_model("GET", f"/v1/usage?{parse.urlencode(query)}", UsagePage)

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

    def online_binding_status(self) -> OnlineBindingStatus:
        """Read the safe configured online binding."""

        return self._request_model("GET", "/v1/mail/online/binding", OnlineBindingStatus)

    def attach_online_binding(self, payload: OnlineAttachRequest) -> OnlineBindingStatus:
        """Attach a revision-pinned online binding."""

        return self._request_model(
            "PUT",
            "/v1/mail/online/binding",
            OnlineBindingStatus,
            body=payload.model_dump(mode="json"),
            timeout_seconds=payload.timeout_seconds * 8 + 5,
        )

    def refresh_online_binding(self, payload: OnlineControlRequest) -> OnlineBindingStatus:
        """Refresh a revision-pinned online binding."""

        return self._request_model(
            "POST",
            "/v1/mail/online/binding/refresh",
            OnlineBindingStatus,
            body=payload.model_dump(mode="json"),
            timeout_seconds=payload.timeout_seconds * 8 + 5,
        )

    def reconnect_online_binding(self, payload: OnlineControlRequest) -> OnlineBindingStatus:
        """Reconnect a revision-pinned online binding."""

        return self._request_model(
            "POST",
            "/v1/mail/online/binding/reconnect",
            OnlineBindingStatus,
            body=payload.model_dump(mode="json"),
            timeout_seconds=payload.timeout_seconds * 8 + 5,
        )

    def detach_online_binding(self, payload: OnlineControlRequest) -> OnlineBindingStatus:
        """Detach a revision-pinned online binding."""

        return self._request_model(
            "DELETE",
            "/v1/mail/online/binding",
            OnlineBindingStatus,
            body=payload.model_dump(mode="json"),
            timeout_seconds=payload.timeout_seconds * 8 + 5,
        )

    def mail_status(self) -> GatewayMailStatusV1:
        """Call `GET /v1/mail/status`."""

        return self._request_model("GET", "/v1/mail/status", GatewayMailStatusV1)

    def list_mail(
        self, payload: GatewayMailListRequestV1, *, channel: MailChannel
    ) -> GatewayMailListResponseV1:
        """Call `POST /v1/mail/list`."""

        return self._request_model(
            "POST",
            f"/v1/mail/{channel}/list",
            GatewayMailListResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def peek_mail(
        self, payload: GatewayMailMessageRequestV1, *, channel: MailChannel
    ) -> GatewayMailMessageResponseV1:
        """Call `POST /v1/mail/peek`."""

        return self._request_model(
            "POST",
            f"/v1/mail/{channel}/peek",
            GatewayMailMessageResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def read_mail(
        self, payload: GatewayMailMessageRequestV1, *, channel: MailChannel
    ) -> GatewayMailMessageResponseV1:
        """Call `POST /v1/mail/read`."""

        return self._request_model(
            "POST",
            f"/v1/mail/{channel}/read",
            GatewayMailMessageResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def send_mail(
        self, payload: GatewayMailSendRequestV1, *, channel: MailChannel
    ) -> GatewayMailActionResponseV1:
        """Call `POST /v1/mail/send`."""

        return self._request_model(
            "POST",
            f"/v1/mail/{channel}/send",
            GatewayMailActionResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def post_mail(
        self, payload: GatewayMailPostRequestV1, *, channel: MailChannel
    ) -> GatewayMailActionResponseV1:
        """Call `POST /v1/mail/post`."""

        return self._request_model(
            "POST",
            f"/v1/mail/{channel}/post",
            GatewayMailActionResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def reply_mail(
        self, payload: GatewayMailReplyRequestV1, *, channel: MailChannel
    ) -> GatewayMailActionResponseV1:
        """Call `POST /v1/mail/reply`."""

        return self._request_model(
            "POST",
            f"/v1/mail/{channel}/reply",
            GatewayMailActionResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def mark_mail(
        self, payload: GatewayMailMarkRequestV1, *, channel: MailChannel
    ) -> GatewayMailLifecycleResponseV1:
        """Call `POST /v1/mail/mark`."""

        return self._request_model(
            "POST",
            f"/v1/mail/{channel}/mark",
            GatewayMailLifecycleResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def move_mail(
        self, payload: GatewayMailMoveRequestV1, *, channel: MailChannel
    ) -> GatewayMailLifecycleResponseV1:
        """Call `POST /v1/mail/move`."""

        return self._request_model(
            "POST",
            f"/v1/mail/{channel}/move",
            GatewayMailLifecycleResponseV1,
            body=payload.model_dump(mode="json"),
        )

    def archive_mail(
        self, payload: GatewayMailArchiveRequestV1, *, channel: MailChannel
    ) -> GatewayMailLifecycleResponseV1:
        """Call `POST /v1/mail/archive`."""

        return self._request_model(
            "POST",
            f"/v1/mail/{channel}/archive",
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

    def get_web_state(self) -> GatewayWebControlStateV1:
        """Read the gateway's structured native Web observation."""

        return self._request_model("GET", "/v1/control/web/state", GatewayWebControlStateV1)

    def get_web_history(self, *, limit: int = 100) -> GatewayWebHistoryV1:
        """Read bounded native Web transitions."""

        return self._request_model(
            "GET", f"/v1/control/web/history?limit={limit}", GatewayWebHistoryV1
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

    def publish_ag_ui_events(
        self,
        payload: AgUiEventPublishRequest,
    ) -> AgUiEventPublishResponse:
        """Call `POST /v1/ag-ui/events`."""

        return self._request_model(
            "POST",
            "/v1/ag-ui/events",
            AgUiEventPublishResponse,
            body=cast(
                GatewayJsonObject,
                payload.model_dump(mode="json", by_alias=True, exclude_none=True),
            ),
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

    def get_mail_notifier(self, *, channel: MailChannel) -> GatewayMailNotifierStatusV1:
        """Call `GET /v1/mail-notifier`."""

        return self._request_model(
            "GET", f"/v1/mail-notifier/{channel}", GatewayMailNotifierStatusV1
        )

    def put_mail_notifier(
        self, payload: GatewayMailNotifierPutV1, *, channel: MailChannel
    ) -> GatewayMailNotifierStatusV1:
        """Call `PUT /v1/mail-notifier`."""

        return self._request_model(
            "PUT",
            f"/v1/mail-notifier/{channel}",
            GatewayMailNotifierStatusV1,
            body=payload.model_dump(mode="json", exclude_unset=True),
        )

    def delete_mail_notifier(self, *, channel: MailChannel) -> GatewayMailNotifierStatusV1:
        """Call `DELETE /v1/mail-notifier`."""

        return self._request_model(
            "DELETE", f"/v1/mail-notifier/{channel}", GatewayMailNotifierStatusV1
        )

    def _request_model(
        self,
        method: str,
        path: str,
        model: type[_ModelT],
        *,
        body: GatewayJsonObject | None = None,
        timeout_seconds: float | None = None,
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
        if path in {"/v1/native-home", "/v1/control/refresh"} and self.m_native_home_etag:
            headers["If-Match"] = self.m_native_home_etag
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request_obj = self._prepare_request(method, path, payload, headers)
        decoded = self._decode_response(
            method=method,
            url=url,
            response=(
                self._open_request(request_obj=request_obj, method=method, url=url)
                if timeout_seconds is None
                else self._open_request(
                    request_obj=request_obj, method=method, url=url, timeout_seconds=timeout_seconds
                )
            ),
        )

        try:
            return model.model_validate(decoded)
        except ValidationError:
            raise GatewayHttpError(
                method=method,
                url=url,
                detail="Gateway returned an invalid response payload.",
            ) from None

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

        request_obj = self._prepare_request(method, path, payload, headers)
        return self._decode_response(
            method=method,
            url=url,
            response=self._open_request(request_obj=request_obj, method=method, url=url),
        )

    def _prepare_request(
        self, method: str, path: str, payload: bytes | None, headers: dict[str, str]
    ) -> request.Request:
        """Attach proof to the exact bytes and request path that will be sent."""

        route, _, query = path.partition("?")
        if route not in _UNSIGNED_ROUTES:
            if self.m_binding is not None:
                headers.update(self._signed_headers(method, route, query, payload or b""))
            elif self.m_request_proof is not None:
                headers.update(self.m_request_proof(method, path, payload or b""))
        return request.Request(
            url=self._build_url(path), data=payload, method=method, headers=headers
        )

    def _signed_headers(
        self,
        method: str,
        path: str,
        query: str,
        payload: bytes,
        *,
        challenge_path: str = "/v1/auth/challenge",
    ) -> dict[str, str]:
        """Check server-authored challenge fields before signing once."""

        binding = self.m_binding
        assert binding is not None
        url = self._build_url(path)
        try:
            signer = load_gateway_signer(Path(binding.private_key_path))
            key = GatewayAdminKey(
                principal="signer", public_key=public_key_text(signer.public_key())
            )
            intended = GatewayRequestBinding.from_request(
                method=method, path=path, query=query, body=payload
            )
            proposed = self.m_registration_key
            if proposed is not None and (key.key_id != proposed.key_id or path != "/v1/admin/keys"):
                raise ValueError("Invalid first registration selection.")
            challenge_request = GatewayChallengeRequest(
                purpose=binding.purpose,
                request=intended,
                key_id=key.key_id if binding.purpose == "admin" else None,
                proposed_key=proposed,
            )
        except (OSError, ValueError):
            raise GatewayHttpError(
                method=method, url=url, detail="Gateway signer binding is unavailable."
            ) from None
        challenge_url = self._build_url(challenge_path)
        request_obj = request.Request(
            url=challenge_url,
            data=challenge_request.model_dump_json().encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        response = self._open_request(request_obj=request_obj, method="POST", url=challenge_url)
        try:
            challenge = parse_access_document(GatewayChallenge, response)
            now = time.time()
            if (
                challenge.issuer != self.m_base_url
                or challenge.target.owner != binding.owner
                or (
                    self.m_target_incarnation is not None
                    and challenge.target.incarnation != self.m_target_incarnation
                )
                or challenge.purpose != binding.purpose
                or challenge.request != intended
                or challenge.key_id != key.key_id
                or challenge.proposed_key != proposed
                or not now < challenge.expires_at <= now + 120
                or (
                    binding.purpose == "self"
                    and challenge.generation_id != challenge.target.incarnation
                )
            ):
                raise ValueError("Challenge differs from the selected binding.")
            signature = sshsig_header(sign_sshsig(signer, challenge.signing_bytes()))
        except (ValueError, OSError):
            raise GatewayHttpError(
                method=method, url=url, detail="Gateway challenge failed binding validation."
            ) from None
        return {CHALLENGE_HEADER: challenge.challenge_id, SIGNATURE_HEADER: signature}

    def _open_request(
        self,
        *,
        request_obj: request.Request,
        method: str,
        url: str,
        timeout_seconds: float | None = None,
    ) -> bytes:
        """Open one gateway request without consulting environment proxy settings."""

        try:
            with self.m_opener.open(
                request_obj, timeout=timeout_seconds or self.m_timeout_seconds
            ) as response:
                payload = cast(bytes, response.read(_MAX_RESPONSE_BYTES + 1))
                if len(payload) > _MAX_RESPONSE_BYTES:
                    raise GatewayHttpError(
                        method=method, url=url, detail="Gateway response exceeds its limit."
                    )
                return payload
        except error.HTTPError as exc:
            raise self._http_refusal(method, url, exc) from None
        except error.URLError:
            raise GatewayHttpError(
                method=method,
                url=url,
                detail="Gateway connection or certificate validation failed.",
            ) from None
        except (TimeoutError, OSError):
            raise GatewayHttpError(
                method=method,
                url=url,
                detail="Gateway connection failed.",
            ) from None

    def _http_refusal(self, method: str, url: str, exc: error.HTTPError) -> GatewayHttpError:
        """Preserve safe admission outcomes and refuse any redirect."""

        payload = exc.read(65537)
        if 300 <= exc.code < 400:
            detail = "Gateway redirects are refused."
        elif exc.code in {401, 403}:
            detail = "Gateway proof was refused."
        elif len(payload) > 65536:
            detail = "Gateway error response exceeds its limit."
        else:
            detail = self._decode_error_body(payload)
        return GatewayHttpError(method=method, url=url, detail=detail, status_code=exc.code)

    def _build_url(self, path: str) -> str:
        """Append an operation path without changing the selected origin or prefix."""

        route = path.partition("?")[0]
        decoded = parse.unquote(route, errors="strict")
        if (
            not decoded.startswith("/")
            or any(segment in {".", "..", ""} for segment in decoded[1:].split("/"))
            or any(c in decoded for c in "\\?#")
            or "#" in path
            or any(ord(c) <= 32 for c in path)
        ):
            raise ValueError("Invalid gateway operation path.")
        return f"{self.m_base_url}{path}"

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


class _RejectGatewayRedirect(request.HTTPRedirectHandler):
    """Disable urllib redirect handling for every gateway request."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        """Return no replacement request."""

        return None


def _build_gateway_client_opener(
    *, respect_proxy_env: bool, ssl_context: ssl.SSLContext | None = None
) -> request.OpenerDirector:
    """Build a gateway HTTP opener using the resolved proxy policy."""

    proxy = request.ProxyHandler() if respect_proxy_env else request.ProxyHandler({})
    return request.build_opener(
        proxy, _RejectGatewayRedirect(), request.HTTPSHandler(context=ssl_context)
    )
