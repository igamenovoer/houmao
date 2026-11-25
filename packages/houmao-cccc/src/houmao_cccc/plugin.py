"""Owner-bound CCCC chat routes and a supervised immediate receiver connection."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, aclosing, asynccontextmanager
from datetime import datetime, timedelta, timezone
import hmac
import json
import math
import re
import secrets
from typing import Literal, cast

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from houmao.gateway.plugins import (
    PluginContext,
    PluginDispatchError,
    PluginEvent,
    PluginRequestBinding,
    PluginRequestMessage,
    PluginRequestPresentation,
    plugin_route_action,
)
from houmao_cccc.client import ProviderClient, ProviderError
from houmao_cccc.configuration import CcccConfiguration, validate_credentials
from houmao_cccc.delivery import ChatOffer, DeliveryBuffer, DeliverySettings
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
        "lease.start",
        "lease.settle",
        "lease.notice.next",
        "lease.stream",
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


class SendRequest(BaseModel):
    """Send ordinary chat to explicitly selected CCCC recipients."""

    model_config = ConfigDict(extra="forbid", strict=True)
    connection_token: str = Field(min_length=1, max_length=64)
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


class ReplyRequest(BaseModel):
    """Reply through one opaque, owner-scoped CCCC event reference."""

    model_config = ConfigDict(extra="forbid", strict=True)
    operation_id: str = Field(min_length=1, max_length=128, pattern=r"^[\w.:-]+$")
    handle: str = Field(min_length=1, max_length=128)
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


class DeliveryUpdate(BaseModel):
    """Replace current-run settings only at the selected revision."""

    model_config = ConfigDict(extra="forbid", strict=True)
    revision: int = Field(ge=0)
    settings: DeliverySettings


_HANDLE_TTL_SECONDS = 3600.0
_HANDLE_LIMIT = 4096
_STAGING_COUNT = 32
_OFFER_FRAME_RESERVE_BYTES = 128


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
        self.m_desired: DeliverySettings = DeliverySettings()
        self.m_effective: DeliverySettings | None = None
        self.m_delivery_revision: int = 0
        self.m_delivery_change: asyncio.Event = asyncio.Event()
        self.m_rotate: asyncio.Event = asyncio.Event()
        self.m_buffer: DeliveryBuffer | None = None
        self.m_connection_token: str | None = None
        self.m_handles: dict[str, tuple[str, float]] = {}

    @classmethod
    def from_config(cls, context: PluginContext, config: CcccConfiguration) -> CcccPlugin:
        """Stage relative routes without reading private state or credentials."""

        plugin = cls()
        plugin.m_context = context
        plugin.m_config = config
        plugin.m_desired = config.delivery
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
            rotate = False
            try:
                self._report("connecting")
                self.m_rotate.clear()
                await client.verify_binding()
                capabilities = await client.capabilities()
                self._validate_capabilities(capabilities)
                self.m_provider_capabilities = capabilities
                transport = self.m_desired.transport
                self._require_transport(capabilities, transport)
                limits = self._limits()
                lease = await client.request(
                    "lease.acquire",
                    {
                        "transport": transport,
                        "receiver": "gateway",
                        "max_offer_bytes": min(
                            cast(int, limits["max_event_bytes"]),
                            cast(int, limits["max_batch_bytes"]) - _OFFER_FRAME_RESERVE_BYTES,
                        ),
                    },
                )
                _string(lease.get("lease_id"))
                if type(lease.get("lease_generation")) not in (int, str):
                    raise ProviderError("invalid_provider_response", 503, False)
                if not self._current(epoch):
                    continue
                if transport != self.m_desired.transport:
                    continue
                self.m_lease = lease
                self.m_effective = self.m_desired
                self.m_buffer = DeliveryBuffer.from_settings(
                    self.m_effective,
                    max_count=cast(int, limits["max_batch_messages"]),
                    max_bytes=cast(int, limits["max_batch_bytes"]),
                )
                self.m_connection_token = secrets.token_urlsafe(18)
                self._report("connected")
                self.m_session_task = asyncio.create_task(
                    self._receive_session(client, lease, epoch, self.m_buffer)
                )
                await self.m_session_task
                rotate = self.m_rotate.is_set()
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
                self.m_connection_token = None
                self.m_effective = None
                self.m_buffer = None
                self.m_handles.clear()
                if lease is not None:
                    await self._release(client, lease)
                if epoch == self.m_epoch:
                    self.m_lease = None
            if self._current(epoch) and not rotate:
                await self._pause(retry_delay)

    def _validate_capabilities(self, capabilities: dict[str, JsonValue]) -> None:
        """Require qualified chat and receiver operations before intake."""

        operations = capabilities.get("operations")
        required = _CHAT_OPERATIONS - {"binding", "capabilities", "lease.stream"}
        if (
            type(capabilities.get("protocol_version")) is not int
            or capabilities.get("protocol_version") != 2
            or not isinstance(operations, list)
        ):
            raise ProviderError("receiver_incompatible", 503, False)
        if not required.issubset({v for v in operations if isinstance(v, str)}):
            raise ProviderError("receiver_incompatible", 503, False)
        limits = capabilities.get("limits")
        if not isinstance(limits, dict):
            raise ProviderError("receiver_incompatible", 503, False)
        for name in (
            "max_event_bytes",
            "max_history_limit",
            "max_response_bytes",
            "lease_seconds",
            "max_batch_messages",
            "max_batch_bytes",
            "max_handoff_seconds",
        ):
            value = limits.get(name)
            minimum = _OFFER_FRAME_RESERVE_BYTES if name == "max_batch_bytes" else 0
            if type(value) is not int or value <= minimum:
                raise ProviderError("receiver_incompatible", 503, False)

    @staticmethod
    def _require_transport(capabilities: dict[str, JsonValue], transport: str) -> None:
        """Verify provider qualification for the requested intake transport."""

        features = capabilities.get("features")
        operations = capabilities.get("operations")
        qualifier = "chat_push_stream" if transport == "push" else "chat_batch_pull"
        if (
            not isinstance(features, dict)
            or features.get(qualifier) is not True
            or features.get("chat_pending") is not True
            or features.get("chat_batch_settlement") is not True
            or not isinstance(operations, list)
            or (transport == "push" and "lease.stream" not in operations)
        ):
            raise ProviderError("receiver_incompatible", 503, False)

    def _limits(self) -> dict[str, JsonValue]:
        """Expose only negotiated finite limits, constrained by local implementation."""

        config = self._config()
        defaults = {
            "max_event_bytes": config.max_event_bytes,
            "max_history_limit": 100,
            "max_response_bytes": config.max_response_bytes,
            "lease_seconds": 45,
            "max_batch_messages": _STAGING_COUNT,
            "max_batch_bytes": min(config.max_response_bytes, config.max_event_bytes),
            "max_handoff_seconds": 15,
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
        self,
        client: ProviderClient,
        lease: dict[str, JsonValue],
        epoch: int,
        buffer: DeliveryBuffer,
    ) -> None:
        """Supervise intake, notices, and one orderly dispatcher on this lease."""

        settings = self.m_effective
        assert settings is not None
        intake = self._pull if settings.transport == "pull" else self._push
        intake_task = asyncio.create_task(intake(client, lease, epoch, buffer))
        notices = asyncio.create_task(self._notices(client, lease, epoch, settings.transport))
        dispatch = asyncio.create_task(self._dispatch_batches(client, lease, epoch, buffer))
        rotation = asyncio.create_task(self.m_rotate.wait())
        tasks = [
            asyncio.create_task(self._renew(client, lease, epoch)),
            asyncio.create_task(self._seal_due_batches(buffer, epoch)),
            intake_task,
            notices,
            dispatch,
            rotation,
        ]
        try:
            done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
            if self.m_rotate.is_set():
                intake_task.cancel()
                notices.cancel()
                self._signal_delivery_change()
                try:
                    async with asyncio.timeout(self._config().request_timeout_seconds + 2.0):
                        await dispatch
                except TimeoutError:
                    pass
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

    def _signal_delivery_change(self) -> None:
        """Wake all current lease workers without clearing another waiter's signal."""

        self.m_delivery_change.set()
        self.m_delivery_change = asyncio.Event()

    async def _wait_for_delivery_change(self, timeout: float) -> None:
        """Wait for changed capacity, settings, or a bounded timer."""

        try:
            async with asyncio.timeout(max(timeout, 0.001)):
                await self.m_delivery_change.wait()
        except TimeoutError:
            pass

    async def _seal_due_batches(self, buffer: DeliveryBuffer, epoch: int) -> None:
        """Seal open batches on schedule even while older work awaits readiness."""

        loop = asyncio.get_running_loop()
        while self._intaking(epoch):
            now = loop.time()
            deadline = buffer.deadline
            if deadline is not None and deadline <= now:
                buffer.close_due(now)
                self._signal_delivery_change()
                continue
            await self._wait_for_delivery_change(1.0 if deadline is None else deadline - now)

    def _intaking(self, epoch: int) -> bool:
        """Reject new work once an orderly transport rotation has been requested."""

        return self._current(epoch) and not self.m_rotate.is_set()

    def _parse_offer(self, offer: dict[str, JsonValue], lease: dict[str, JsonValue]) -> ChatOffer:
        """Fence a chat offer to this selected registration and live lease."""

        config = self._config()
        sequence, remaining = offer.get("sequence"), offer.get("remaining_seconds")
        mode = offer.get("message_mode")
        if (
            offer.get("kind", "chat") != "chat"
            or offer.get("group_id") != config.group_id
            or offer.get("actor_id") != config.actor_id
            or offer.get("actor_generation") != config.actor_generation
            or offer.get("lease_generation") != lease.get("lease_generation")
            or type(sequence) is not int
            or sequence <= 0
            or type(remaining) not in (int, float)
            or not math.isfinite(cast(float, remaining))
            or cast(float, remaining) <= 0
            or not isinstance(mode, str)
            or mode not in {"send", "request_reply"}
        ):
            raise ProviderError("invalid_offer", 422, False)
        return ChatOffer(
            attempt_id=_string(offer.get("attempt_id")),
            event_id=_string(offer.get("event_id")),
            sequence=sequence,
            sender=_string(offer.get("sender")),
            timestamp=_string(offer.get("timestamp")),
            mode=cast(Literal["send", "request_reply"], mode),
            text=_string(offer.get("text")),
            expires_at=asyncio.get_running_loop().time() + cast(float, remaining),
            size=len(json.dumps(offer, ensure_ascii=False, separators=(",", ":")).encode()),
        )

    def _stage(
        self, lease: dict[str, JsonValue], buffer: DeliveryBuffer, offers: list[JsonValue]
    ) -> None:
        """Stage parsed offers atomically and signal the lease's dispatcher."""

        try:
            buffer.stage(
                [self._parse_offer(_object(offer), lease) for offer in offers],
                asyncio.get_running_loop().time(),
            )
        except ValueError:
            raise ProviderError("invalid_provider_response", 503, False) from None
        self._signal_delivery_change()

    async def _pull(
        self,
        client: ProviderClient,
        lease: dict[str, JsonValue],
        epoch: int,
        buffer: DeliveryBuffer,
    ) -> None:
        """Seal exactly one notification per scheduled provider snapshot."""

        lease_args = self._lease_arguments(lease)
        loop = asyncio.get_running_loop()
        last = -math.inf
        while self._intaking(epoch):
            settings = self.m_effective
            assert settings is not None
            delay = last + settings.pull_interval - loop.time()
            count, byte_limit = buffer.credit
            if delay > 0 or count == 0 or byte_limit <= _OFFER_FRAME_RESERVE_BYTES:
                await self._wait_for_delivery_change(delay if delay > 0 else 1.0)
                continue
            last = loop.time()
            try:
                result = await client.request(
                    "lease.next", {**lease_args, "limit": count, "max_bytes": byte_limit}
                )
            except ProviderError as exc:
                if exc.code != "event_too_large":
                    raise
                continue
            if self._intaking(epoch):
                offers = result.get("offers")
                if not isinstance(offers, list):
                    raise ProviderError("invalid_provider_response", 503, False)
                self._stage(lease, buffer, offers)

    async def _push(
        self,
        client: ProviderClient,
        lease: dict[str, JsonValue],
        epoch: int,
        buffer: DeliveryBuffer,
    ) -> None:
        """Grant bounded stream credit and stage each newly received offer on arrival."""

        lease_id = _string(lease.get("lease_id"))
        generation = cast(int | str, lease["lease_generation"])
        while self._intaking(epoch):
            limit, byte_limit = buffer.credit
            if limit == 0 or byte_limit <= _OFFER_FRAME_RESERVE_BYTES:
                await self._wait_for_delivery_change(1.0)
                continue
            before = buffer.highest_sequence
            try:
                async with aclosing(
                    client.offer_stream(
                        lease_id,
                        generation,
                        kind="chat",
                        limit=limit,
                        max_bytes=byte_limit,
                        after_sequence=before,
                    )
                ) as stream:
                    async for offer in stream:
                        if not self._intaking(epoch):
                            return
                        self._stage(lease, buffer, [offer])
            except ProviderError as exc:
                if exc.code != "event_too_large":
                    raise
            if buffer.highest_sequence == before:
                await self._wait_for_delivery_change(0.1)

    async def _notices(
        self, client: ProviderClient, lease: dict[str, JsonValue], epoch: int, transport: str
    ) -> None:
        """Keep immediate Mail notice intake independent of chat credit and batching."""

        lease_args = self._lease_arguments(lease)
        if transport == "pull":
            while self._intaking(epoch):
                result = await client.request("lease.notice.next", lease_args)
                offer = result.get("offer")
                if self._intaking(epoch) and offer is not None:
                    await self._offer(client, lease, _object(offer), epoch)
                await self._wait_for_delivery_change(0.5)
            return
        lease_id = _string(lease.get("lease_id"))
        generation = cast(int | str, lease["lease_generation"])
        sequence = 0
        while self._intaking(epoch):
            async with aclosing(
                client.offer_stream(
                    lease_id,
                    generation,
                    kind="mail_notice",
                    limit=1,
                    max_bytes=cast(int, self._limits()["max_batch_bytes"]),
                    after_sequence=sequence,
                )
            ) as stream:
                async for offer in stream:
                    if not self._intaking(epoch):
                        return
                    current = offer.get("sequence")
                    if type(current) is not int or current <= 0:
                        raise ProviderError("invalid_offer", 422, False)
                    if current > sequence:
                        await self._offer(client, lease, offer, epoch)
                        sequence = current

    @staticmethod
    async def _decision(
        client: ProviderClient, operation: str, arguments: dict[str, JsonValue]
    ) -> dict[str, JsonValue]:
        """Reconcile one ambiguous provider response using the original decision ID."""

        try:
            return await client.request(operation, arguments)
        except ProviderError as error:
            if not error.retryable and error.outcome != "unknown":
                raise
            return await client.request(operation, arguments)

    def _batch_event(self, batch: tuple[ChatOffer, ...]) -> PluginEvent:
        """Project sender attribution and exact handles while retaining correlation internally."""

        config = self._config()
        return PluginEvent(
            source_event_id=f"cccc:{batch[0].attempt_id}",
            presentation=PluginRequestPresentation(
                binding=PluginRequestBinding(group_id=config.group_id, actor_id=config.actor_id),
                messages=[
                    PluginRequestMessage(
                        sender=offer.sender,
                        timestamp=offer.timestamp,
                        mode=offer.mode,
                        text=offer.text,
                        handle=self._mint_handle(offer.event_id),
                    )
                    for offer in batch
                ],
            ),
            metadata={"backend": "cccc-chat"},
        )

    async def _dispatch_batches(
        self,
        client: ProviderClient,
        lease: dict[str, JsonValue],
        epoch: int,
        buffer: DeliveryBuffer,
    ) -> None:
        """Advance one sealed batch through ready-only handoff and exact settlement."""

        loop = asyncio.get_running_loop()
        events = self._context().events
        while self._intaking(epoch):
            buffer.close_due(loop.time())
            batch = buffer.head
            if batch is None:
                await self._wait_for_delivery_change(1.0)
                continue
            event = self._batch_event(batch)
            limit = min(offer.expires_at for offer in batch)
            validation_error = None
            try:
                events.validate(event)
            except PluginDispatchError as error:
                validation_error = error
            while self._intaking(epoch):
                remaining = limit - loop.time()
                if remaining <= 0:
                    self.m_rotate.set()
                    return
                readiness = None
                if validation_error is None:
                    try:
                        readiness = await events.wait_until_ready(
                            timeout_seconds=min(0.2, remaining)
                        )
                    except PluginDispatchError as error:
                        if error.error_code != "body_replaced":
                            raise
                    if readiness is None:
                        continue
                if not self._intaking(epoch):
                    return
                dispatch_id = secrets.token_urlsafe(18)
                key = {**self._lease_arguments(lease), "dispatch_id": dispatch_id}
                ids: list[JsonValue] = [offer.attempt_id for offer in batch]
                handoff_deadline = loop.time() + cast(int, self._limits()["max_handoff_seconds"])
                start = await self._decision(client, "lease.start", {**key, "attempt_ids": ids})
                if (
                    start.get("dispatch_id") != dispatch_id
                    or start.get("attempt_ids") != ids
                    or start.get("outcome") != "started"
                ):
                    raise ProviderError("invalid_provider_response", 503, False)
                outcome = "deferred"
                code: str | None = "connection_retired"
                retryable = True
                try:
                    if validation_error is not None:
                        raise validation_error
                    remaining = min(limit, handoff_deadline) - loop.time()
                    if self._intaking(epoch) and remaining > 0:
                        async with asyncio.timeout(
                            min(self._config().request_timeout_seconds, remaining)
                        ):
                            await events.dispatch(event, readiness=readiness)
                        outcome, code, retryable = "accepted", None, False
                except PluginDispatchError as error:
                    if error.dispatch_outcome == "unknown":
                        outcome = "uncertain"
                    elif error.error_code in {"not_ready", "body_replaced", "plugin_unavailable"}:
                        outcome = "deferred"
                    else:
                        outcome = "failed"
                    code, retryable = error.error_code, error.retryable
                except TimeoutError:
                    outcome, code, retryable = "uncertain", "dispatch_timeout", True
                except asyncio.CancelledError:
                    try:
                        async with asyncio.timeout(1.0):
                            await client.request(
                                "lease.settle",
                                {
                                    **key,
                                    "outcome": "uncertain",
                                    "retryable": True,
                                    "error_code": "dispatch_cancelled",
                                },
                            )
                    except (ProviderError, TimeoutError):
                        pass
                    raise
                except Exception:
                    outcome, code, retryable = "uncertain", "dispatch_failed", True
                settled = await self._decision(
                    client,
                    "lease.settle",
                    {
                        **key,
                        "outcome": outcome,
                        "retryable": retryable,
                        "error_code": code,
                    },
                )
                if (
                    settled.get("dispatch_id") != dispatch_id
                    or settled.get("attempt_ids") != ids
                    or settled.get("outcome") != outcome
                ):
                    raise ProviderError("invalid_provider_response", 503, False)
                if outcome != "deferred":
                    buffer.finish(batch)
                    self._signal_delivery_change()
                    break

    async def _offer(
        self,
        client: ProviderClient,
        lease: dict[str, JsonValue],
        offer: dict[str, JsonValue],
        epoch: int,
    ) -> None:
        """Dispatch one content-free Mail notice and settle its immediate outcome."""

        arguments = self._lease_arguments(lease)
        arguments["attempt_id"] = _string(offer.get("attempt_id"))
        arguments.update(outcome="failed", retryable=False, error_code="invalid_offer")
        try:
            event_id = _string(offer.get("event_id"))
            pending_count = offer.get("pending_count")
            remaining = offer.get("remaining_seconds")
            config = self._config()
            if (
                not self._current(epoch)
                or offer.get("kind") != "mail_notice"
                or self.m_mail is None
                or not self.m_mail.qualified()
                or offer.get("group_id") != config.group_id
                or offer.get("actor_id") != config.actor_id
                or offer.get("actor_generation") != config.actor_generation
                or offer.get("lease_generation") != lease.get("lease_generation")
                or type(pending_count) is not int
                or not 0 <= pending_count <= 2147483647
                or type(remaining) not in (int, float)
                or not math.isfinite(cast(float, remaining))
                or cast(float, remaining) <= 0
            ):
                raise ProviderError("invalid_offer", 422, False)
            context = self._context()
            listener = context.listener
            endpoint = (
                f"{listener.base_url}/v1/plugins/{context.instance_id}"
                if listener is not None
                else f"/v1/plugins/{context.instance_id}"
            )
            self.m_mail.observe_notice(pending_count)
            event = PluginEvent(
                source_event_id=event_id,
                text=(
                    f"CCCC deferred Mail is pending for instance {context.instance_id}, "
                    f"binding {context.binding_id}. Inspect {endpoint}/mail/peek and "
                    f"{endpoint}/mail/cursor explicitly. Consume only through POST "
                    f"{endpoint}/mail/read with an operation_id and expected_cursor. "
                    "A notice does not consume Mail."
                ),
                metadata={
                    "backend": "cccc-mail",
                    "kind": "mail_notice",
                    "pending_count": pending_count,
                },
            )
            max_event_bytes = cast(int, self._limits()["max_event_bytes"])
            if len(event.model_dump_json().encode("utf-8")) > max_event_bytes:
                raise ProviderError("event_too_large", 422, False)
            async with asyncio.timeout(min(cast(float, remaining), config.request_timeout_seconds)):
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
        token = self.m_connection_token
        if (
            client is None
            or token is None
            or self.m_phase != "connected"
            or not self._intaking(epoch)
        ):
            raise ProviderError("receiver_unavailable", 503, True)
        task = cast(asyncio.Task[object], asyncio.current_task())
        self.m_operations.add(task)
        try:
            result = await client.request(operation, arguments)
            if not self._intaking(epoch) or token != self.m_connection_token:
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

    def _mint_handle(self, event_id: str) -> str:
        """Issue a bounded gateway-run and receiver-generation scoped message handle."""

        now = asyncio.get_running_loop().time()
        while self.m_handles:
            oldest = next(iter(self.m_handles))
            if len(self.m_handles) < _HANDLE_LIMIT and self.m_handles[oldest][1] > now:
                break
            del self.m_handles[oldest]
        handle = f"msg_{self._context().instance_id}.{secrets.token_urlsafe(12)}"
        self.m_handles[handle] = event_id, now + _HANDLE_TTL_SECONDS
        return handle

    def _handle_event_id(self, handle: str) -> str:
        """Resolve a live handle without interpreting provider-controlled input as an ID."""

        entry = self.m_handles.get(handle)
        if (
            entry is None
            or entry[1] <= asyncio.get_running_loop().time()
            or self.m_connection_token is None
            or self.m_rotate.is_set()
        ):
            raise HTTPException(
                409,
                detail={
                    "error_code": "message_handle_stale",
                    "retryable": False,
                    "guidance": "Select the exact message in authorized CCCC chat history.",
                },
            )
        return entry[0]

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
        if self.m_connection_token is not None:
            event["handle"] = self._mint_handle(event_id)
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
            "/discovery",
            self.discovery,
            methods=["GET"],
            openapi_extra=plugin_route_action("plugin.cccc.discovery.read"),
        )
        self.m_router.add_api_route(
            "/delivery",
            self.delivery_settings,
            methods=["GET"],
            openapi_extra=plugin_route_action("plugin.cccc.delivery.read"),
        )
        self.m_router.add_api_route(
            "/delivery",
            self.update_delivery,
            methods=["PUT"],
            openapi_extra=plugin_route_action("plugin.cccc.delivery.update"),
        )
        self.m_router.add_api_route(
            "/messages/{handle}",
            self.message,
            methods=["GET"],
            openapi_extra=plugin_route_action("plugin.cccc.messages.read"),
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
            "protocol_version": 2,
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
            connection_token = self.m_connection_token
            result = await self._call("members", {})
            if connection_token is None or connection_token != self.m_connection_token:
                raise ProviderError("connection_retired", 503, True)
            members = result.get("members")
            if not isinstance(members, list):
                raise ProviderError("invalid_provider_response", 503, False)
            allowed = {"id", "title", "role", "enabled", "receive_status"}
            return {
                "members": [{k: v for k, v in _object(m).items() if k in allowed} for m in members],
                "connection_token": connection_token,
            }
        except ProviderError as exc:
            raise HTTPException(exc.status_code, detail=exc.to_detail()) from None

    async def discovery(self, request: Request) -> dict[str, JsonValue]:
        """Return the validated Actor scope and operations for direct calls."""

        self._queries(request, set())
        if self.m_phase != "connected" or self.m_rotate.is_set():
            raise HTTPException(
                503, detail={"error_code": "receiver_unavailable", "retryable": True}
            )
        config = self._config()
        operations = self.m_provider_capabilities.get("operations")
        assert isinstance(operations, list)
        return {
            "endpoint": config.endpoint,
            "group_id": config.group_id,
            "actor_id": config.actor_id,
            "actor_generation": config.actor_generation,
            "protocol_version": 2,
            "operations": [name for name in operations if isinstance(name, str)],
        }

    def _delivery_state(self) -> dict[str, JsonValue]:
        """Report desired settings separately from settings held by the live session."""

        effective = self.m_effective
        transition = "applying"
        if effective == self.m_desired and not self.m_rotate.is_set():
            transition = "active"
        elif self.m_phase in {"disconnected", "degraded"}:
            transition = self.m_phase
        return {
            "revision": self.m_delivery_revision,
            "desired": self.m_desired.model_dump(mode="json"),
            "effective": effective.model_dump(mode="json") if effective else None,
            "transition": transition,
            "error_code": self.m_error_code,
        }

    async def delivery_settings(self, request: Request) -> dict[str, JsonValue]:
        """Read the current instance's desired and effective settings."""

        self._queries(request, set())
        return self._delivery_state()

    async def update_delivery(self, update: DeliveryUpdate) -> dict[str, JsonValue]:
        """Apply a same-lease policy edit or request an orderly transport switch."""

        async with self.m_transition:
            if update.revision != self.m_delivery_revision:
                raise HTTPException(409, detail={"error_code": "delivery_revision_conflict"})
            if not self.m_active:
                raise HTTPException(503, detail={"error_code": "plugin_unavailable"})
            try:
                self._require_transport(self.m_provider_capabilities, update.settings.transport)
            except ProviderError as exc:
                raise HTTPException(exc.status_code, detail=exc.to_detail()) from None
            if update.settings != self.m_desired:
                self.m_delivery_revision += 1
                self.m_desired = update.settings
                if self.m_effective is not None:
                    if self.m_effective.transport != update.settings.transport:
                        self.m_rotate.set()
                    elif not self.m_rotate.is_set():
                        assert self.m_buffer is not None
                        self.m_buffer.configure(update.settings)
                        self.m_effective = update.settings
                        self._signal_delivery_change()
                self.m_change.set()
            return self._delivery_state()

    async def message(self, request: Request, handle: str) -> dict[str, JsonValue]:
        """Project one exact Actor-visible event without returning internal references."""

        self._queries(request, set())
        event_id = self._handle_event_id(handle)
        try:
            result = await self._call("chat.history", {"event_id": event_id})
            messages = result.get("messages")
            if not isinstance(messages, list) or len(messages) != 1:
                raise ProviderError("message_unavailable", 409, False)
            event = _object(messages[0])
            if event.get("id") != event_id:
                raise ProviderError("invalid_provider_response", 503, False)
            data = _object(event.get("data"))
            return {
                "handle": handle,
                "sender": _string(event.get("by")),
                "timestamp": _string(event.get("ts")),
                "mode": _string(data.get("message_mode", "send")),
                "text": _string(data.get("text")),
                "reply_to": data.get("reply_to"),
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

        token = self.m_connection_token
        if (
            token is None
            or self.m_rotate.is_set()
            or not hmac.compare_digest(token.encode(), body.connection_token.encode())
        ):
            raise HTTPException(
                409, detail={"error_code": "stale_connection_token", "retryable": False}
            )
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

        event_id = self._handle_event_id(body.handle)
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
        event_id: str | None = Query(default=None, max_length=512),
    ) -> dict[str, JsonValue]:
        """Read bounded Actor-visible history without consumption or dispatch."""

        self._queries(request, {"limit", "cursor", "event_ref", "event_id"})
        if sum(value is not None for value in (cursor, event_ref, event_id)) > 1:
            raise HTTPException(422, detail={"error_code": "incompatible_history_parameters"})
        limits = self._limits()
        arguments: dict[str, JsonValue] = {
            "limit": min(limit, cast(int, limits["max_history_limit"])),
            "max_bytes": limits["max_response_bytes"],
        }
        if event_ref:
            arguments = {"event_id": self._event_id(event_ref)}
        if event_id:
            arguments = {"event_id": event_id}
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
