"""Owner-bound CCCC chat routes and a supervised immediate receiver connection."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import datetime, timedelta, timezone
import json
import math
import re
from typing import Literal, cast

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from houmao.gateway.plugins import (
    PluginContext,
    PluginDispatchError,
    PluginEvent,
    plugin_route_action,
)
from houmao_cccc.client import ProviderClient, ProviderError
from houmao_cccc.configuration import CcccConfiguration, validate_credentials
from houmao_cccc.mail import MAIL_OPERATIONS, MailService
from houmao_cccc.references import ReferenceCodec, ReferenceError

_CHAT_OPERATIONS = frozenset(
    {
        "binding",
        "capabilities",
        "members",
        "lease.acquire",
        "lease.renew",
        "lease.release",
        "lease.next",
        "lease.outcome",
        "chat.send",
        "chat.reply",
        "chat.retry",
        "chat.history",
        "chat.deliveries",
    }
)


class BindingRequest(BaseModel):
    """Require the caller's current binding before any connection or mutation."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_binding_id: str = Field(min_length=1, max_length=256)


class SendRequest(BindingRequest):
    """Send ordinary chat to explicitly selected CCCC recipients."""

    operation_id: str = Field(min_length=1, max_length=128, pattern=r"^[\w.:-]+$")
    to: list[str] = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=65536)
    mode: Literal["send", "request_reply"] = "send"

    @field_validator("text")
    @classmethod
    def _nonblank_text(cls, value: str) -> str:
        """Reject an empty operation without changing caller text."""

        if not value.strip():
            raise ValueError("Chat text must not be blank")
        return value

    @field_validator("to")
    @classmethod
    def _recipients(cls, values: list[str]) -> list[str]:
        """Keep qualified Actor addressing separate from email and other Groups."""

        if any(re.fullmatch(r"@?[A-Za-z0-9][A-Za-z0-9_-]{0,127}", v) is None for v in values):
            raise ValueError("Recipients must be explicit CCCC Actor identifiers")
        if len(set(values)) != len(values):
            raise ValueError("Recipients must not repeat")
        if any(v.lstrip("@") == "user" for v in values) and len(values) != 1:
            raise ValueError("Human and Actor audiences must be separate")
        return values


class ReplyRequest(BindingRequest):
    """Reply through one opaque, owner-scoped CCCC event reference."""

    operation_id: str = Field(min_length=1, max_length=128, pattern=r"^[\w.:-]+$")
    event_ref: str = Field(min_length=1, max_length=8192)
    text: str = Field(min_length=1, max_length=65536)
    mode: Literal["send"] = "send"

    @field_validator("text")
    @classmethod
    def _nonblank_text(cls, value: str) -> str:
        """Reject blank replies without silently editing the message."""

        return SendRequest._nonblank_text(value)


class RetryRequest(BindingRequest):
    """Request a fresh sender-authorized attempt, separate from a stored send."""

    event_ref: str = Field(min_length=1, max_length=8192)
    actor_ids: list[str] = Field(min_length=1, max_length=100)
    allow_uncertain_retry: bool = False

    @field_validator("actor_ids")
    @classmethod
    def _recipients(cls, values: list[str]) -> list[str]:
        """Validate concrete recipient selections before provider access."""

        return SendRequest._recipients(values)


def _object(value: JsonValue) -> dict[str, JsonValue]:
    """Require a provider object before projecting its fields."""

    if not isinstance(value, dict):
        raise ProviderError("invalid_provider_response", 503, False)
    return value


def _string(value: JsonValue) -> str:
    """Require a finite nonempty provider identifier or content field."""

    if not isinstance(value, str) or not value:
        raise ProviderError("invalid_provider_response", 503, False)
    return value


class CcccPlugin:
    """Manage one immutable Actor connection without owning the agent body."""

    def __init__(self) -> None:
        """Prepare resource-free state; the host owns activation and workers."""

        self.m_context: PluginContext | None = None
        self.m_config: CcccConfiguration | None = None
        self.m_router: APIRouter = APIRouter()
        self.m_codec: ReferenceCodec | None = None
        self.m_client: ProviderClient | None = None
        self.m_active: bool = False
        self.m_want_connected: bool = False
        self.m_epoch: int = 0
        self.m_phase: str = "unattached"
        self.m_error_code: str | None = None
        self.m_provider_capabilities: dict[str, JsonValue] = {}
        self.m_lease: dict[str, JsonValue] | None = None
        self.m_change: asyncio.Event = asyncio.Event()
        self.m_transition: asyncio.Lock = asyncio.Lock()
        self.m_session_task: asyncio.Task[None] | None = None
        self.m_operations: set[asyncio.Task[object]] = set()
        self.m_mail: MailService | None = None

    @classmethod
    def from_config(cls, context: PluginContext, config: CcccConfiguration) -> CcccPlugin:
        """Stage relative routes without reading private state or credentials."""

        plugin = cls()
        plugin.m_context = context
        plugin.m_config = config
        plugin.m_mail = MailService.from_plugin(plugin)
        plugin._register_routes()
        return plugin

    @property
    def router(self) -> APIRouter:
        """Return the host-staged relative HTTP route collection."""

        return self.m_router

    def lifespan(self) -> AbstractAsyncContextManager[None]:
        """Open selected resources only during host-authorized activation."""

        return self._lifespan()

    @asynccontextmanager
    async def _lifespan(self) -> AsyncIterator[None]:
        """Initialize the selected client and supervise background connection."""

        context = self._context()
        self.m_codec = ReferenceCodec.from_context(context)
        self.m_client = self._new_client()
        self.m_active = True
        self.m_want_connected = True
        context.workers.start_soon("cccc-receiver", self._connection_worker)
        try:
            yield
        finally:
            self.m_active = False
            await self._retire()
            # The host revokes its public ports before exiting plugin lifespans.
            # Its final snapshot owns the disconnected status after this cleanup.
            self.m_phase = "disconnected"
            self.m_error_code = None

    def _context(self) -> PluginContext:
        """Resolve the configured context without exposing implementation internals."""

        assert self.m_context is not None
        return self.m_context

    def _config(self) -> CcccConfiguration:
        """Resolve immutable settings after factory construction."""

        assert self.m_config is not None
        return self.m_config

    def _references(self) -> ReferenceCodec:
        """Require active-lifespan reference authority."""

        if self.m_codec is None:
            raise ProviderError("plugin_unavailable", 503, True)
        return self.m_codec

    def _new_client(self) -> ProviderClient:
        """Read only the selected credential document and validate fixed scope."""

        context = self._context()
        token = validate_credentials(
            self._config(), context.owner.agent_id, context.credentials.read()
        )
        return ProviderClient.from_config(self._config(), token)

    def _report(self, phase: str, error: ProviderError | None = None) -> None:
        """Publish content-free local and host connection snapshots."""

        self.m_phase = phase
        self.m_error_code = error.code if error else None
        state = "reconnecting" if phase == "connecting" else phase
        retry_at = None
        if error is not None and error.retry_after_seconds is not None:
            retry_at = (
                datetime.now(timezone.utc) + timedelta(seconds=error.retry_after_seconds)
            ).isoformat()
        self._context().report_connection(state, retry_at=retry_at)

    def _current(self, epoch: int) -> bool:
        """Fence work retired by disconnect, refresh, or host shutdown."""

        return self.m_active and self.m_want_connected and epoch == self.m_epoch

    async def _connection_worker(self) -> None:
        """Restore connectivity without replaying historical message payloads."""

        while self.m_active:
            if not self.m_want_connected:
                self.m_change.clear()
                if not self.m_want_connected and self.m_active:
                    await self.m_change.wait()
                continue
            epoch = self.m_epoch
            client = self.m_client
            if client is None:
                await self._pause(self._config().reconnect_delay_seconds)
                continue
            lease: dict[str, JsonValue] | None = None
            retry_delay = self._config().reconnect_delay_seconds
            try:
                self._report("connecting")
                binding = await client.request("binding", {})
                self._validate_binding(binding)
                capabilities = await client.request("capabilities", {})
                self._validate_capabilities(capabilities)
                lease = await client.request("lease.acquire", {})
                _string(lease.get("lease_id"))
                if type(lease.get("lease_generation")) not in (int, str):
                    raise ProviderError("invalid_provider_response", 503, False)
                if not self._current(epoch):
                    continue
                self.m_lease = lease
                self.m_provider_capabilities = capabilities
                self._report("connected")
                self.m_session_task = asyncio.create_task(
                    self._receive_session(client, lease, epoch)
                )
                await self.m_session_task
            except asyncio.CancelledError:
                if not self.m_active or epoch == self.m_epoch:
                    raise
            except ProviderError as exc:
                if self._current(epoch):
                    self._report("reconnecting" if exc.retryable else "degraded", exc)
                    if exc.retry_after_seconds is not None:
                        retry_delay = max(retry_delay, min(exc.retry_after_seconds, 45.0))
            except Exception:
                if self._current(epoch):
                    self._report("degraded", ProviderError("connection_failed", 503, True))
            finally:
                self.m_session_task = None
                if lease is not None:
                    await self._release(client, lease)
                if epoch == self.m_epoch:
                    self.m_lease = None
            if self._current(epoch):
                await self._pause(retry_delay)

    def _validate_binding(self, binding: dict[str, JsonValue]) -> None:
        """Reject another registration and incompatible stock Web interfaces."""

        config = self._config()
        if type(binding.get("protocol_version")) is not int or binding.get("protocol_version") != 1:
            raise ProviderError("receiver_incompatible", 503, False)
        for field in ("group_id", "actor_id", "actor_generation"):
            if binding.get(field) != getattr(config, field):
                raise ProviderError("actor_binding_changed", 409, False)

    def _validate_capabilities(self, capabilities: dict[str, JsonValue]) -> None:
        """Require qualified chat and receiver operations before intake."""

        operations = capabilities.get("operations")
        required = _CHAT_OPERATIONS - {"binding", "capabilities"}
        if (
            type(capabilities.get("protocol_version")) is not int
            or capabilities.get("protocol_version") != 1
            or not isinstance(operations, list)
        ):
            raise ProviderError("receiver_incompatible", 503, False)
        if not required.issubset({v for v in operations if isinstance(v, str)}):
            raise ProviderError("receiver_incompatible", 503, False)
        limits = capabilities.get("limits")
        if not isinstance(limits, dict):
            raise ProviderError("receiver_incompatible", 503, False)
        for name in ("max_event_bytes", "max_history_limit", "max_response_bytes", "lease_seconds"):
            value = limits.get(name)
            if type(value) is not int or value <= 0:
                raise ProviderError("receiver_incompatible", 503, False)

    def _limits(self) -> dict[str, JsonValue]:
        """Expose only negotiated finite limits, constrained by local implementation."""

        config = self._config()
        defaults = {
            "max_event_bytes": config.max_event_bytes,
            "max_history_limit": 100,
            "max_response_bytes": config.max_response_bytes,
            "lease_seconds": 45,
        }
        limits = self.m_provider_capabilities.get("limits")
        if not isinstance(limits, dict):
            return dict(defaults)
        return {
            name: min(limit, value) if type(value := limits.get(name)) is int else limit
            for name, limit in defaults.items()
        }

    async def _pause(self, seconds: float) -> None:
        """Wait for a bounded reconnect delay or an explicit transition."""

        self.m_change.clear()
        try:
            await asyncio.wait_for(self.m_change.wait(), timeout=max(seconds, 0.01))
        except TimeoutError:
            pass

    async def _receive_session(
        self, client: ProviderClient, lease: dict[str, JsonValue], epoch: int
    ) -> None:
        """Renew intake independently while long polling or dispatch is active."""

        tasks = [
            asyncio.create_task(self._renew(client, lease, epoch)),
            asyncio.create_task(self._poll(client, lease, epoch)),
        ]
        try:
            done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _lease_arguments(lease: dict[str, JsonValue]) -> dict[str, JsonValue]:
        """Forward only provider-issued lease identity and generation."""

        return {"lease_id": lease["lease_id"], "lease_generation": lease["lease_generation"]}

    async def _renew(self, client: ProviderClient, lease: dict[str, JsonValue], epoch: int) -> None:
        """Keep the current lease alive without granting replacement authority."""

        while self._current(epoch):
            await asyncio.sleep(self._config().renew_interval_seconds)
            if self._current(epoch):
                await client.request("lease.renew", self._lease_arguments(lease))

    async def _poll(self, client: ProviderClient, lease: dict[str, JsonValue], epoch: int) -> None:
        """Process only fresh provider offers, never recovered history."""

        while self._current(epoch):
            arguments = self._lease_arguments(lease)
            arguments["timeout_seconds"] = self._config().poll_timeout_seconds
            result = await client.request("lease.next", arguments)
            if not self._current(epoch):
                return
            offer = result.get("offer")
            if offer is not None:
                await self._offer(client, lease, _object(offer), epoch)
            else:
                await asyncio.sleep(0.01)

    async def _offer(
        self,
        client: ProviderClient,
        lease: dict[str, JsonValue],
        offer: dict[str, JsonValue],
        epoch: int,
    ) -> None:
        """Dispatch one request-scoped offer and settle its exact provider attempt."""

        arguments = self._lease_arguments(lease)
        arguments["attempt_id"] = _string(offer.get("attempt_id"))
        arguments.update(outcome="failed", retryable=False, error_code="invalid_offer")
        try:
            event_id = _string(offer.get("event_id"))
            notice = offer.get("kind") == "mail_notice"
            pending_count = offer.get("pending_count")
            if notice:
                if (
                    self.m_mail is None
                    or not self.m_mail.qualified()
                    or type(pending_count) is not int
                    or pending_count < 0
                    or pending_count > 2147483647
                ):
                    raise ProviderError("invalid_offer", 422, False)
                text = (
                    "CCCC deferred Mail is pending. Inspect this binding's /mail/peek and "
                    "/mail/cursor explicitly. Consume only through POST /mail/read with an "
                    "operation_id and expected_cursor. A notice does not consume Mail."
                )
            else:
                if offer.get("kind") not in (None, "chat"):
                    raise ProviderError("invalid_offer", 422, False)
                text = _string(offer.get("text"))
            sender = _string(offer.get("sender"))
            reply_to = offer.get("reply_to")
            remaining = offer.get("remaining_seconds")
            config = self._config()
            if (
                not self._current(epoch)
                or offer.get("group_id") != config.group_id
                or offer.get("actor_id") != config.actor_id
                or offer.get("actor_generation") != config.actor_generation
                or offer.get("lease_generation") != lease.get("lease_generation")
                or offer.get("message_mode") not in {"send", "request_reply"}
                or isinstance(remaining, bool)
                or not isinstance(remaining, (float, int))
                or not math.isfinite(remaining)
                or remaining <= 0
                or len(event_id) > 512
                or len(sender) > 256
                or any(ord(char) < 32 for char in sender)
                or (reply_to is not None and (not isinstance(reply_to, str) or len(reply_to) > 512))
            ):
                raise ProviderError("invalid_offer", 422, False)
            event_ref = self._references().encode("event", {"event_id": event_id})
            context = self._context()
            listener = context.listener
            endpoint_hint = (
                f"local_plugin_url={listener.base_url}/v1/plugins/{context.instance_id}\n"
                if listener is not None
                else ""
            )
            heading = "CCCC deferred Mail notice\n" if notice else "CCCC ordinary chat\n"
            reply_hint = (
                "Use the explicit Mail routes to inspect or consume the pending batch.\n\n"
                if notice
                else "To reply, use this local plugin's POST /chat/reply with expected_binding_id, "
                "a new operation_id, this event_ref, and text.\n\n"
            )
            if listener is not None and not notice:
                endpoint_hint = f"gateway_base_url={listener.base_url}\n{endpoint_hint}"
                reply_hint = (
                    "Use gateway_base_url for the CLI and local_plugin_url for HTTP.\n"
                    "Set the CLI variables from the fields above and supply a new operation ID "
                    "and reply text.\n"
                    'houmao-cccc --gateway-url "$GATEWAY_BASE_URL" --instance "$PLUGIN_INSTANCE" '
                    'chat reply --binding-id "$BINDING_ID" --event-ref "$EVENT_REF" '
                    '--operation-id "$NEW_OPERATION_ID" --text="$REPLY_TEXT"\n'
                    f"{reply_hint}"
                )
            metadata: dict[str, JsonValue] = {
                "backend": "cccc-mail" if notice else "cccc-chat",
                "event_ref": event_ref,
            }
            if notice:
                metadata.update(kind="mail_notice", pending_count=pending_count)
                assert self.m_mail is not None
                self.m_mail.observe_notice(cast(int, pending_count))
            event = PluginEvent(
                source_event_id=event_id,
                text=(
                    f"{heading}"
                    f"plugin_instance={context.instance_id}\n"
                    f"binding_id={context.binding_id}\n"
                    f"event_id={event_id}\nevent_ref={event_ref}\n"
                    f"sender={sender}\nmessage_mode={offer.get('message_mode')}\n"
                    f"reply_to={reply_to}\n{endpoint_hint}"
                    f"{reply_hint}"
                    f"{text}"
                ),
                metadata=metadata,
            )
            max_event_bytes = cast(int, self._limits()["max_event_bytes"])
            if len(event.model_dump_json().encode("utf-8")) > max_event_bytes:
                raise ProviderError("event_too_large", 422, False)
            async with asyncio.timeout(min(float(remaining), config.request_timeout_seconds)):
                await self._context().events.dispatch(event)
            if not self._current(epoch):
                raise ProviderError("connection_retired", 503, True, outcome="unknown")
            arguments.update(outcome="accepted", retryable=False, error_code=None)
        except PluginDispatchError as exc:
            outcome = (
                "uncertain"
                if exc.dispatch_outcome == "unknown"
                else "refused"
                if exc.status_code == 409
                else "failed"
            )
            arguments.update(outcome=outcome, retryable=exc.retryable, error_code=exc.error_code)
        except ProviderError as exc:
            arguments.update(
                outcome="uncertain" if exc.outcome == "unknown" else "failed",
                retryable=exc.retryable,
                error_code=exc.code,
            )
        except TimeoutError:
            arguments.update(outcome="uncertain", retryable=True, error_code="dispatch_timeout")
        except asyncio.CancelledError:
            arguments.update(outcome="uncertain", retryable=True, error_code="dispatch_cancelled")
            try:
                async with asyncio.timeout(1.0):
                    await client.request("lease.outcome", arguments)
            except Exception:
                pass
            raise
        except Exception:
            arguments.update(outcome="uncertain", retryable=True, error_code="dispatch_failed")
        await client.request("lease.outcome", arguments)

    async def _release(self, client: ProviderClient, lease: dict[str, JsonValue]) -> None:
        """Best-effort release of this process's lease, without forced takeover."""

        try:
            async with asyncio.timeout(1.0):
                await client.request("lease.release", self._lease_arguments(lease))
        except Exception:
            pass

    async def _retire(self) -> None:
        """Revoke the local epoch and drain live work before closing the client."""

        self.m_want_connected = False
        self.m_epoch += 1
        self.m_change.set()
        session = self.m_session_task
        if session is not None:
            session.cancel()
            await asyncio.gather(session, return_exceptions=True)
        current = asyncio.current_task()
        operations = [task for task in self.m_operations if task is not current]
        for operation in operations:
            operation.cancel()
        if operations:
            await asyncio.gather(*operations, return_exceptions=True)
        client, self.m_client = self.m_client, None
        lease, self.m_lease = self.m_lease, None
        if client is not None:
            if lease is not None:
                await self._release(client, lease)
            await client.aclose()

    async def _call(
        self, operation: str, arguments: dict[str, JsonValue], *, mutation: bool = False
    ) -> dict[str, JsonValue]:
        """Perform one current-binding call without mutation retry or rebind."""

        client = self.m_client
        epoch = self.m_epoch
        if client is None or self.m_phase != "connected" or not self._current(epoch):
            raise ProviderError("receiver_unavailable", 503, True)
        task = cast(asyncio.Task[object], asyncio.current_task())
        self.m_operations.add(task)
        try:
            result = await client.request(operation, arguments)
            if not self._current(epoch):
                raise ProviderError(
                    "connection_retired", 503, True, outcome="unknown" if mutation else "not_sent"
                )
            return result
        except asyncio.CancelledError:
            if not self._current(epoch):
                raise ProviderError(
                    "connection_retired", 503, True, outcome="unknown" if mutation else "not_sent"
                ) from None
            raise
        finally:
            self.m_operations.discard(task)

    def _expect_binding(self, binding_id: str) -> None:
        """Refuse stale selection before service reads or mutation."""

        if binding_id != self._context().binding_id:
            raise HTTPException(409, detail={"error_code": "binding_conflict", "retryable": False})

    @staticmethod
    def _queries(request: Request, allowed: set[str]) -> None:
        """Reject unsupported ordinary query inputs rather than accepting overrides."""

        if set(request.query_params) - allowed:
            raise HTTPException(422, detail={"error_code": "unsupported_query", "retryable": False})

    def _event_id(self, event_ref: str) -> str:
        """Validate an event targeting handle before issuing provider access."""

        try:
            value = self._references().decode(event_ref, "event")
            return _string(_object(value).get("event_id"))
        except (ReferenceError, ProviderError):
            raise HTTPException(422, detail={"error_code": "reference_scope_error"}) from None

    def _decorate_event(self, value: JsonValue) -> dict[str, JsonValue]:
        """Preserve native event provenance and attach an owner-scoped handle."""

        event = dict(_object(value))
        event_id = _string(event.get("id"))
        event["event_id"] = event_id
        event["event_ref"] = self._references().encode("event", {"event_id": event_id})
        return event

    def _decorate_result(self, result: dict[str, JsonValue]) -> dict[str, JsonValue]:
        """Attach current binding and scoped targeting without changing native facts."""

        projected = dict(result)
        projected.update(backend="cccc-chat", binding_id=self._context().binding_id)
        if projected.get("event") is not None:
            projected["event"] = self._decorate_event(projected["event"])
        return projected

    def _stored_result(
        self, result: dict[str, JsonValue], operation_id: str
    ) -> dict[str, JsonValue]:
        """Require provider storage evidence and preserve ambiguity on malformed replies."""

        try:
            if result.get("stored") is not True or not isinstance(result.get("event"), dict):
                raise ProviderError("invalid_provider_response")
            projected = self._decorate_result(result)
        except (ProviderError, ReferenceError):
            raise ProviderError("invalid_provider_response", 503, True, outcome="unknown") from None
        projected["operation_id"] = operation_id
        return projected

    def _register_routes(self) -> None:
        """Stage namespace-relative HTTP operations for host validation."""

        self.m_router.add_api_route(
            "/binding",
            self.binding,
            methods=["GET"],
            openapi_extra=plugin_route_action("plugin.cccc.binding.read"),
        )
        self.m_router.add_api_route(
            "/capabilities",
            self.capabilities,
            methods=["GET"],
            openapi_extra=plugin_route_action("plugin.cccc.capabilities.read"),
        )
        self.m_router.add_api_route(
            "/members",
            self.members,
            methods=["GET"],
            openapi_extra=plugin_route_action("plugin.cccc.members.read"),
        )
        self.m_router.add_api_route(
            "/connection/connect",
            self.connect,
            methods=["POST"],
            openapi_extra=plugin_route_action("plugin.cccc.connection.connect"),
        )
        self.m_router.add_api_route(
            "/connection/disconnect",
            self.disconnect,
            methods=["POST"],
            openapi_extra=plugin_route_action("plugin.cccc.connection.disconnect"),
        )
        self.m_router.add_api_route(
            "/connection/reconnect",
            self.reconnect,
            methods=["POST"],
            openapi_extra=plugin_route_action("plugin.cccc.connection.reconnect"),
        )
        self.m_router.add_api_route(
            "/connection/refresh-credentials",
            self.refresh_credentials,
            methods=["POST"],
            openapi_extra=plugin_route_action("plugin.cccc.connection.refresh-credentials"),
        )
        self.m_router.add_api_route(
            "/chat/send",
            self.send,
            methods=["POST"],
            openapi_extra=plugin_route_action("plugin.cccc.chat.send"),
        )
        self.m_router.add_api_route(
            "/chat/reply",
            self.reply,
            methods=["POST"],
            openapi_extra=plugin_route_action("plugin.cccc.chat.reply"),
        )
        self.m_router.add_api_route(
            "/chat/retry",
            self.retry,
            methods=["POST"],
            openapi_extra=plugin_route_action("plugin.cccc.chat.retry"),
        )
        self.m_router.add_api_route(
            "/chat/history",
            self.history,
            methods=["GET"],
            openapi_extra=plugin_route_action("plugin.cccc.chat.history.read"),
        )
        self.m_router.add_api_route(
            "/chat/deliveries",
            self.deliveries,
            methods=["GET"],
            openapi_extra=plugin_route_action("plugin.cccc.chat.deliveries.read"),
        )
        assert self.m_mail is not None
        self.m_router.include_router(self.m_mail.router)

    async def binding(self, request: Request) -> dict[str, JsonValue]:
        """Read a safe maintained binding snapshot without provider requests."""

        self._queries(request, set())
        config = self._config()
        return {
            "agent_id": self._context().owner.agent_id,
            "runtime_session_id": self._context().owner.runtime_session_id,
            "instance_id": self._context().instance_id,
            "binding_id": self._context().binding_id,
            "group_id": config.group_id,
            "actor_id": config.actor_id,
            "actor_generation": config.actor_generation,
            "connection": self.m_phase,
            "error_code": self.m_error_code,
        }

    async def capabilities(self, request: Request) -> dict[str, JsonValue]:
        """Project effective qualified capabilities without provider health calls."""

        self._queries(request, set())
        provider_operations = self.m_provider_capabilities.get("operations", [])
        effective: list[JsonValue] = (
            [v for v in provider_operations if isinstance(v, str) and v in _CHAT_OPERATIONS]
            if isinstance(provider_operations, list)
            else []
        )
        assert self.m_mail is not None
        mail = self.m_mail.capabilities()
        if mail["qualified"] is True:
            effective.extend(sorted(MAIL_OPERATIONS))
        return {
            "backend": "cccc-chat",
            "binding_id": self._context().binding_id,
            "available": self.m_phase == "connected",
            "protocol_version": 1,
            "operations": effective,
            "limits": self._limits(),
            "recipient_scope": "bound-group",
            "modes": ["send", "request_reply"],
            "mail": mail,
            "success_means": "provider_storage_acceptance; per-recipient handoff is separate",
        }

    async def members(self, request: Request) -> dict[str, JsonValue]:
        """Return public Actor-visible membership without private runtime settings."""

        self._queries(request, set())
        try:
            result = await self._call("members", {})
            members = result.get("members")
            if not isinstance(members, list):
                raise ProviderError("invalid_provider_response", 503, False)
            allowed = {"id", "title", "role", "enabled", "receive_status"}
            return {
                "members": [{k: v for k, v in _object(m).items() if k in allowed} for m in members]
            }
        except ProviderError as exc:
            raise HTTPException(exc.status_code, detail=exc.to_detail()) from None

    async def _change_connection(self, body: BindingRequest, connect: bool) -> dict[str, JsonValue]:
        """Serialize owner-selected connection transitions without account replacement."""

        self._expect_binding(body.expected_binding_id)
        if not self.m_active:
            raise HTTPException(503, detail={"error_code": "plugin_unavailable"})
        async with self.m_transition:
            try:
                candidate = self._new_client() if connect else None
            except ValueError:
                raise HTTPException(
                    422, detail={"error_code": "credential_binding_invalid"}
                ) from None
            await self._retire()
            self.m_client = candidate
            self.m_want_connected = connect
            self._report("reconnecting" if connect else "disconnected")
            self.m_change.set()
        return {"binding_id": self._context().binding_id, "connection": self.m_phase}

    async def connect(self, body: BindingRequest) -> dict[str, JsonValue]:
        """Connect only the configured owner/Actor using the selected source."""

        self._expect_binding(body.expected_binding_id)
        if self.m_want_connected and self.m_phase == "connected":
            return {"binding_id": self._context().binding_id, "connection": self.m_phase}
        return await self._change_connection(body, True)

    async def disconnect(self, body: BindingRequest) -> dict[str, JsonValue]:
        """Retire intake and live operations while preserving immutable selection."""

        return await self._change_connection(body, False)

    async def reconnect(self, body: BindingRequest) -> dict[str, JsonValue]:
        """Reconnect the same Actor without lease takeover or payload replay."""

        return await self._change_connection(body, True)

    async def refresh_credentials(self, body: BindingRequest) -> dict[str, JsonValue]:
        """Reread only the selected source after validating identical owner scope."""

        return await self._change_connection(body, True)

    async def send(self, body: SendRequest) -> dict[str, JsonValue]:
        """Create or reconcile one owner-bound provider chat event."""

        self._expect_binding(body.expected_binding_id)
        try:
            result = await self._call(
                "chat.send",
                {
                    "operation_id": body.operation_id,
                    "to": list(body.to),
                    "text": body.text,
                    "mode": body.mode,
                },
                mutation=True,
            )
            return self._stored_result(result, body.operation_id)
        except ProviderError as exc:
            detail = exc.to_detail()
            detail["operation_id"] = body.operation_id
            raise HTTPException(exc.status_code, detail=detail) from None

    async def reply(self, body: ReplyRequest) -> dict[str, JsonValue]:
        """Reply using a scoped handle while preserving native event ancestry."""

        self._expect_binding(body.expected_binding_id)
        event_id = self._event_id(body.event_ref)
        try:
            result = await self._call(
                "chat.reply",
                {
                    "operation_id": body.operation_id,
                    "event_id": event_id,
                    "text": body.text,
                    "mode": body.mode,
                },
                mutation=True,
            )
            return self._stored_result(result, body.operation_id)
        except ProviderError as exc:
            detail = exc.to_detail()
            detail["operation_id"] = body.operation_id
            raise HTTPException(exc.status_code, detail=detail) from None

    async def retry(self, body: RetryRequest) -> dict[str, JsonValue]:
        """Request one new delivery attempt without repeating a stored send."""

        self._expect_binding(body.expected_binding_id)
        event_id = self._event_id(body.event_ref)
        try:
            result = await self._call(
                "chat.retry",
                {
                    "event_id": event_id,
                    "actor_ids": list(body.actor_ids),
                    "allow_uncertain_retry": body.allow_uncertain_retry,
                },
                mutation=True,
            )
            return self._decorate_result(result)
        except ProviderError as exc:
            raise HTTPException(exc.status_code, detail=exc.to_detail()) from None

    async def history(
        self,
        request: Request,
        limit: int = Query(default=50, ge=1, le=100),
        cursor: str | None = Query(default=None, max_length=8192),
        event_ref: str | None = Query(default=None, max_length=8192),
    ) -> dict[str, JsonValue]:
        """Read bounded Actor-visible history without consumption or dispatch."""

        self._queries(request, {"limit", "cursor", "event_ref"})
        if cursor and event_ref:
            raise HTTPException(422, detail={"error_code": "incompatible_history_parameters"})
        limits = self._limits()
        arguments: dict[str, JsonValue] = {
            "limit": min(limit, cast(int, limits["max_history_limit"])),
            "max_bytes": limits["max_response_bytes"],
        }
        if event_ref:
            arguments = {"event_id": self._event_id(event_ref)}
        if cursor:
            try:
                target = _object(self._references().decode(cursor, "history"))
                if target.get("limit") != limit:
                    raise ReferenceError("History query scope changed")
                arguments["before_event_id"] = _string(target.get("before_event_id"))
            except (ReferenceError, ProviderError):
                raise HTTPException(422, detail={"error_code": "reference_scope_error"}) from None
        try:
            result = await self._call("chat.history", arguments)
            messages = result.get("messages")
            if not isinstance(messages, list) or type(result.get("has_more")) is not bool:
                raise ProviderError("invalid_provider_response", 503, False)
            projected = [self._decorate_event(m) for m in messages]
            has_more = result.get("has_more") is True
            if has_more and not projected:
                raise ProviderError("invalid_provider_response", 503, False)
            continuation = None
            if has_more and projected:
                continuation = self._references().encode(
                    "history", {"before_event_id": projected[-1]["event_id"], "limit": limit}
                )
            response: dict[str, JsonValue] = {
                "messages": cast(list[JsonValue], projected),
                "has_more": has_more,
                "cursor": continuation,
                "binding_id": self._context().binding_id,
                "backend": "cccc-chat",
            }
            if len(json.dumps(response).encode()) > self._config().max_response_bytes:
                raise ProviderError("history_response_too_large", 422, False)
            return response
        except ProviderError as exc:
            raise HTTPException(exc.status_code, detail=exc.to_detail()) from None

    async def deliveries(
        self,
        request: Request,
        event_ref: str = Query(max_length=8192),
        limit: int = Query(default=50, ge=1, le=100),
    ) -> dict[str, JsonValue]:
        """Read authoritative handoff receipts without acknowledging another event."""

        self._queries(request, {"event_ref", "limit"})
        event_id = self._event_id(event_ref)
        try:
            return self._decorate_result(
                await self._call("chat.deliveries", {"event_id": event_id, "limit": limit})
            )
        except ProviderError as exc:
            raise HTTPException(exc.status_code, detail=exc.to_detail()) from None
