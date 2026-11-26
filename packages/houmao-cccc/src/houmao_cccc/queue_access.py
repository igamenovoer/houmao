"""Bounded access to sealed CCCC chat while a gateway receiver is running."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import secrets
from typing import TYPE_CHECKING, Literal, cast

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from houmao.gateway.plugins import plugin_route_action
from houmao_cccc.client import MAX_BATCH_MESSAGES, ProviderError
from houmao_cccc.delivery import ChatSelection, DeliveryBuffer
from houmao_cccc.models import (
    QUEUE_MAX_WAIT_SECONDS,
    QUEUE_OPERATION_ID_PATTERN,
    QUEUE_TOKEN_MAX_LENGTH,
)

if TYPE_CHECKING:
    from houmao_cccc.plugin import CcccPlugin


QUEUE_OPERATIONS = frozenset({"chat.gateway-read.claim", "chat.gateway-read.result", "chat.ack"})
_QUEUE_READ = plugin_route_action("plugin.cccc.chat.queue.read")
_QUEUE_CONSUME = plugin_route_action("plugin.cccc.chat.queue.consume")
_SNAPSHOT_LIFETIME_SECONDS = 30.0
_SNAPSHOT_PATTERN = re.compile(r"q1\.[a-f0-9]{16}\.[a-f0-9]{2}\.[a-f0-9]{64}\.[a-f0-9]{64}")
_SHA256_PATTERN = r"^[a-f0-9]{64}$"
_RECEIPT_PATTERN = r"^[a-f0-9]{32}$"
_REQUEST_KIND = "cccc_chat_requests"


class PopRequest(BaseModel):
    """Name the snapshot and operation whose result the caller wants."""

    model_config = ConfigDict(extra="forbid", strict=True)
    snapshot: str = Field(min_length=1, max_length=QUEUE_TOKEN_MAX_LENGTH)
    operation_id: str = Field(pattern=QUEUE_OPERATION_ID_PATTERN)


class AckRequest(BaseModel):
    """Acknowledge a provider-issued exact gateway read receipt."""

    model_config = ConfigDict(extra="forbid", strict=True)
    receipt: str = Field(pattern=_RECEIPT_PATTERN)


class ReadMessage(BaseModel):
    """Validate one original message and its provider attempt across a read recovery."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    attempt_id: str = Field(min_length=1, max_length=128)
    event_id: str = Field(min_length=1, max_length=512)
    sequence: int = Field(gt=0)
    sender: str = Field(min_length=1, max_length=256)
    timestamp: str = Field(min_length=1, max_length=64)
    message_mode: Literal["send", "request_reply"]
    text: str = Field(min_length=1)

    def public(self, handle: str) -> dict[str, JsonValue]:
        """Expose ordinary request content with a current gateway handle."""

        return {
            "sender": self.sender,
            "timestamp": self.timestamp,
            "mode": self.message_mode,
            "text": self.text,
            "handle": handle,
        }


class ReadDecision(BaseModel):
    """Validate a durable gateway read decision before exposing its messages."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    found: Literal[True]
    operation_id: str = Field(pattern=QUEUE_OPERATION_ID_PATTERN)
    snapshot_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    receipt: str = Field(pattern=_RECEIPT_PATTERN)
    status: Literal["pending", "acknowledged", "uncertain"]
    groups: list[list[ReadMessage]] = Field(min_length=1)


def _encoded(value: JsonValue) -> bytes:
    """Match compact UTF-8 JSON used in provider and gateway responses."""

    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def _digest(value: bytes) -> str:
    """Identify exact metadata without publishing the metadata itself."""

    return hashlib.sha256(value).hexdigest()


def _attempt_groups(selection: ChatSelection) -> list[list[str]]:
    """Preserve exact staged attempt order and sealed boundaries."""

    return [[message.attempt_id for message in batch] for batch in selection]


def _read_groups(selection: ChatSelection) -> list[list[ReadMessage]]:
    """Use the same message fields for budget preflight and provider recovery."""

    try:
        return [
            [
                ReadMessage(
                    attempt_id=message.attempt_id,
                    event_id=message.event_id,
                    sequence=message.sequence,
                    sender=message.sender,
                    timestamp=message.timestamp,
                    message_mode=message.mode,
                    text=message.text,
                )
                for message in batch
            ]
            for batch in selection
        ]
    except ValidationError:
        raise ProviderError("invalid_provider_response") from None


def _observe_claim(task: asyncio.Task[dict[str, JsonValue]]) -> None:
    """Retire the waiter independently without losing the claim task's error."""

    if not task.cancelled():
        task.exception()


class QueueAccess:
    """Project and claim one existing gateway buffer under its current lease."""

    def __init__(self) -> None:
        """Prepare routes and keep lease secrets only in memory."""

        self.m_plugin: CcccPlugin | None = None
        self.m_router: APIRouter = APIRouter()
        self.m_signing_key: bytes = b""
        self.m_binding_tag: str = ""

    @classmethod
    def from_plugin(cls, plugin: CcccPlugin) -> QueueAccess:
        """Mount authorized routes without opening any resources."""

        result = cls()
        result.m_plugin = plugin
        result.m_router.add_api_route(
            "/chat/queue", result.peek, methods=["GET"], openapi_extra=_QUEUE_READ
        )
        result.m_router.add_api_route(
            "/chat/queue/pop", result.pop, methods=["POST"], openapi_extra=_QUEUE_CONSUME
        )
        result.m_router.add_api_route(
            "/chat/queue/pops/{operation_id}",
            result.pop_result,
            methods=["GET"],
            openapi_extra=_QUEUE_CONSUME,
        )
        result.m_router.add_api_route(
            "/chat/queue/ack", result.ack, methods=["POST"], openapi_extra=_QUEUE_CONSUME
        )
        return result

    @property
    def router(self) -> APIRouter:
        """Expose the explicitly authorized relative gateway routes."""

        return self.m_router

    def _plugin(self) -> CcccPlugin:
        """Resolve the owner of the supervised CCCC connection."""

        assert self.m_plugin is not None
        return self.m_plugin

    def start_lease(self) -> None:
        """Give the new lease an independent snapshot authentication key."""

        self.m_signing_key = secrets.token_bytes(32)
        context = self._plugin()._context()
        self.m_binding_tag = _digest(
            _encoded(
                [
                    "cccc-chat-read-v1",
                    context.owner.agent_id,
                    context.instance_id,
                    context.binding_id,
                ]
            )
        )

    def qualified(self) -> bool:
        """Require the optional feature and all of its provider operations."""

        capabilities = self._plugin().m_provider_capabilities
        features = capabilities.get("features")
        operations = capabilities.get("operations")
        return (
            isinstance(features, dict)
            and features.get("chat_gateway_queue_reads") is True
            and isinstance(operations, list)
            and QUEUE_OPERATIONS.issubset(v for v in operations if isinstance(v, str))
        )

    def _assert_qualified(self) -> None:
        """Distinguish a known older provider from an unavailable connection."""

        if not self.qualified():
            if not self._plugin().m_provider_capabilities:
                raise ProviderError("receiver_unavailable", 503, True)
            raise ProviderError("queue_access_unsupported", 422)

    def _current(self, buffer: DeliveryBuffer) -> bool:
        """Fence routes against loss or replacement of their selected buffer."""

        plugin = self._plugin()
        return (
            plugin.m_buffer is buffer
            and plugin.m_lease is not None
            and plugin.m_connection_token is not None
            and plugin.m_phase == "connected"
            and plugin._intaking(plugin.m_epoch)
        )

    def _buffer(self) -> DeliveryBuffer:
        """Require a qualified provider with current in-memory staging."""

        self._assert_qualified()
        buffer = self._plugin().m_buffer
        if buffer is None or not self._current(buffer):
            raise ProviderError("receiver_unavailable", 503, True)
        return buffer

    def _max_count(self) -> int:
        """Use the receiver's effective staged message limit."""

        return cast(int, self._plugin()._limits()["max_batch_messages"])

    def _max_bytes(self) -> int:
        """Use the negotiated complete public response limit."""

        return cast(int, self._plugin()._limits()["max_response_bytes"])

    def _provider_bytes(self) -> int:
        """Fit both the provider read bound and the local RPC response bound."""

        return min(cast(int, self._plugin()._limits()["max_batch_bytes"]), self._max_bytes())

    def _snapshot(self, selection: ChatSelection, now: float) -> str:
        """Sign a finite selection without embedding any identity or attempt IDs."""

        expiry = min(
            now + _SNAPSHOT_LIFETIME_SECONDS, *(m.expires_at for b in selection for m in b)
        )
        groups_digest = _digest(_encoded(cast(JsonValue, _attempt_groups(selection))))
        prefix = f"q1.{int(expiry * 1000):016x}.{len(selection):02x}.{groups_digest}"
        signature = hmac.digest(self.m_signing_key, prefix.encode(), "sha256").hex()
        return f"{prefix}.{signature}"

    def _selection(self, snapshot: str, buffer: DeliveryBuffer) -> ChatSelection:
        """Validate a current snapshot against the exact still-eligible FIFO prefix."""

        if _SNAPSHOT_PATTERN.fullmatch(snapshot) is None:
            raise ProviderError("queue_snapshot_stale", 409)
        prefix, signature = snapshot.rsplit(".", 1)
        if not hmac.compare_digest(
            hmac.digest(self.m_signing_key, prefix.encode(), "sha256").hex(), signature
        ):
            raise ProviderError("queue_snapshot_stale", 409)
        _, expiry, size, digest = prefix.split(".")
        count = int(size, 16)
        now = asyncio.get_running_loop().time()
        selection = buffer.sealed[:count]
        if (
            int(expiry, 16) <= int(now * 1000)
            or not count
            or len(selection) != count
            or any(m.expires_at <= now for b in selection for m in b)
            or _digest(_encoded(cast(JsonValue, _attempt_groups(selection)))) != digest
        ):
            raise ProviderError("queue_snapshot_stale", 409)
        return selection

    def _batches(self, groups: list[list[ReadMessage]], *, mint: bool) -> JsonValue:
        """Use equal-length handles for size estimates and final projections."""

        plugin = self._plugin()
        sample = f"msg_{plugin._context().instance_id}." + "0" * 16
        return cast(
            JsonValue,
            [
                [m.public(plugin._mint_handle(m.event_id) if mint else sample) for m in batch]
                for batch in groups
            ],
        )

    def _peek_view(
        self,
        groups: list[list[ReadMessage]],
        snapshot: str | None,
        buffer: DeliveryBuffer,
        *,
        mint: bool,
    ) -> dict[str, JsonValue]:
        """Return only sealed request content and progress for remaining staged work."""

        return {
            "kind": _REQUEST_KIND,
            "batches": self._batches(groups, mint=mint),
            "snapshot": snapshot,
            "additional_queued": len(buffer.sealed) > len(groups),
            "open_batch_count": buffer.open_count,
        }

    def _read_view(self, read: ReadDecision, *, mint: bool = True) -> dict[str, JsonValue]:
        """Project a durable decision using handles for this gateway run."""

        return {
            "kind": _REQUEST_KIND,
            "found": True,
            "operation_id": read.operation_id,
            "status": read.status,
            "receipt": read.receipt,
            "batches": self._batches(read.groups, mint=mint),
        }

    def _fits_read(self, groups: list[list[ReadMessage]]) -> bool:
        """Preflight the full tool envelope and the recoverable provider response."""

        sample = ReadDecision(
            found=True,
            operation_id="x" * 128,
            snapshot_fingerprint="0" * 64,
            receipt="0" * 32,
            status="acknowledged",
            groups=groups,
        )
        return (
            len(_encoded(self._read_view(sample, mint=False))) <= self._max_bytes()
            and len(_encoded({"ok": True, "result": sample.model_dump(mode="json")}))
            <= self._provider_bytes()
        )

    def _preview(self, buffer: DeliveryBuffer, now: float) -> ChatSelection:
        """Choose the longest eligible, fully encoded prefix of sealed batches."""

        if buffer.reserved:
            return ()
        chosen: ChatSelection = ()
        for end, batch in enumerate(buffer.sealed, start=1):
            if any(m.expires_at <= now for m in batch):
                break
            candidate = (*chosen, batch)
            if sum(len(b) for b in candidate) > self._max_count():
                break
            groups = _read_groups(candidate)
            snapshot = self._snapshot(candidate, now)
            view = self._peek_view(groups, snapshot, buffer, mint=False)
            if len(_encoded(view)) > self._max_bytes() or not self._fits_read(groups):
                if end == 1:
                    raise ProviderError("content_limit", 422)
                break
            chosen = candidate
        return chosen

    async def peek(
        self,
        request: Request,
        min_messages: int = Query(default=1, ge=1),
        wait_seconds: float = Query(default=0, ge=0, le=QUEUE_MAX_WAIT_SECONDS),
    ) -> dict[str, JsonValue]:
        """Preview eligible batches or wait for a finite amount of new work."""

        plugin = self._plugin()
        allowed = {"min_messages", "wait_seconds"}
        plugin._queries(request, allowed)
        try:
            buffer = self._buffer()
            if min_messages > self._max_count() or any(
                len(request.query_params.getlist(key)) > 1 for key in allowed
            ):
                raise ProviderError("invalid_args", 422)
            loop = asyncio.get_running_loop()
            deadline = loop.time() + wait_seconds
            while self._current(buffer):
                now = loop.time()
                selection = self._preview(buffer, now)
                if sum(len(batch) for batch in selection) >= min_messages or now >= deadline:
                    snapshot = self._snapshot(selection, now) if selection else None
                    view = self._peek_view(_read_groups(selection), snapshot, buffer, mint=True)
                    if len(_encoded(view)) > self._max_bytes():
                        raise ProviderError("content_limit", 422)
                    return view
                await plugin._wait_for_delivery_change(deadline - now)
            raise ProviderError("receiver_unavailable", 503, True)
        except ProviderError as exc:
            raise HTTPException(exc.status_code, detail=exc.to_detail()) from None

    def _decode(self, result: dict[str, JsonValue], operation: str) -> ReadDecision:
        """Accept exact, ordered provider decisions with a bounded group layout."""

        try:
            read = ReadDecision.model_validate(result)
        except ValidationError:
            raise ProviderError("invalid_provider_response") from None
        messages = [message for batch in read.groups for message in batch]
        sequences = [m.sequence for m in messages]
        if (
            read.operation_id != operation
            or any(not batch for batch in read.groups)
            or len(messages) > MAX_BATCH_MESSAGES
            or len(set(m.attempt_id for m in messages)) != len(messages)
            or sequences != sorted(set(sequences))
        ):
            raise ProviderError("invalid_provider_response")
        return read

    async def _lookup(self, operation: str) -> ReadDecision | None:
        """Resolve only this recorded provider operation under its stable binding."""

        result = await self._plugin()._call(
            "chat.gateway-read.result",
            {"binding_tag": self.m_binding_tag, "operation_id": operation},
        )
        if result == {"found": False, "operation_id": operation}:
            return None
        return self._decode(result, operation)

    def _complete(self, read: ReadDecision) -> dict[str, JsonValue]:
        """Return the complete view or preserve the recorded claim on a limit error."""

        if len(_encoded(self._read_view(read, mint=False))) > self._max_bytes():
            raise ProviderError("content_limit", 422)
        return self._read_view(read)

    async def _claim(
        self,
        buffer: DeliveryBuffer,
        selection: ChatSelection,
        arguments: dict[str, JsonValue],
        operation: str,
        fingerprint: str,
        deadline: float,
    ) -> dict[str, JsonValue]:
        """Keep one reservation until durable success, refusal, or lease retirement."""

        plugin = self._plugin()
        committed = False
        uncertain = False
        try:
            if not self._current(buffer):
                raise ProviderError("queue_snapshot_stale", 409)
            async with asyncio.timeout_at(deadline):
                try:
                    uncertain = True
                    result = await plugin._call("chat.gateway-read.claim", arguments, mutation=True)
                except ProviderError as exc:
                    uncertain = exc.outcome == "unknown"
                    if not uncertain:
                        raise
                    read = await self._lookup(operation)
                    if read is None:
                        raise ProviderError("queue_claim_unknown", 503, True, "unknown")
                else:
                    read = self._decode(result, operation)
                if read.snapshot_fingerprint != fingerprint or read.groups != _read_groups(
                    selection
                ):
                    raise ProviderError("invalid_provider_response")
                committed = True
                uncertain = False
                return self._complete(read)
        except TimeoutError:
            raise ProviderError("queue_claim_unknown", 503, True, "unknown") from None
        except ProviderError:
            if uncertain:
                raise ProviderError("queue_claim_unknown", 503, True, "unknown") from None
            raise
        finally:
            if uncertain and self._current(buffer):
                plugin.m_rotate.set()
            buffer.release(selection, consume=committed)
            plugin._signal_delivery_change()

    async def pop(self, body: PopRequest, request: Request) -> dict[str, JsonValue]:
        """Claim the exact preview once and return it as tool output."""

        plugin = self._plugin()
        plugin._queries(request, set())
        operation = body.operation_id
        fingerprint = _digest(body.snapshot.encode())
        try:
            buffer = self._buffer()
            timeout = plugin._config().request_timeout_seconds
            deadline = asyncio.get_running_loop().time() + timeout
            prior = await self._lookup(operation)
            if prior is not None:
                if prior.snapshot_fingerprint != fingerprint:
                    raise ProviderError("operation_conflict", 409)
                return self._complete(prior)
            if not self._current(buffer):
                raise ProviderError("queue_snapshot_stale", 409)
            selection = self._selection(body.snapshot, buffer)
            if not self._fits_read(_read_groups(selection)):
                raise ProviderError("content_limit", 422)
            lease = plugin.m_lease
            assert lease is not None
            arguments = {
                **plugin._lease_arguments(lease),
                "binding_tag": self.m_binding_tag,
                "operation_id": operation,
                "snapshot_fingerprint": fingerprint,
                "groups": cast(JsonValue, _attempt_groups(selection)),
                "max_bytes": self._provider_bytes(),
            }
            if not buffer.reserve(selection):
                raise ProviderError("queue_snapshot_stale", 409)
            task = asyncio.create_task(
                self._claim(buffer, selection, arguments, operation, fingerprint, deadline)
            )
            task.add_done_callback(_observe_claim)
            return await asyncio.shield(task)
        except ProviderError as exc:
            raise HTTPException(
                exc.status_code, detail={**exc.to_detail(), "operation_id": operation}
            ) from None

    async def pop_result(
        self, request: Request, operation_id: str = Path(pattern=QUEUE_OPERATION_ID_PATTERN)
    ) -> dict[str, JsonValue]:
        """Recover the original recorded result under the same logical binding."""

        self._plugin()._queries(request, set())
        try:
            self._buffer()
            result = await self._lookup(operation_id)
            if result is None:
                return {"found": False, "operation_id": operation_id}
            return self._complete(result)
        except ProviderError as exc:
            raise HTTPException(exc.status_code, detail=exc.to_detail()) from None

    async def ack(self, body: AckRequest, request: Request) -> dict[str, JsonValue]:
        """Confirm the exact durable read under the Actor's current binding."""

        plugin = self._plugin()
        plugin._queries(request, set())
        try:
            self._buffer()
            result = await plugin._call(
                "chat.ack",
                {"binding_tag": self.m_binding_tag, "receipt": body.receipt},
                mutation=True,
            )
            attempts = result.get("attempt_ids")
            if (
                result.get("receipt") != body.receipt
                or result.get("acknowledged") is not True
                or not isinstance(attempts, list)
                or not 1 <= len(attempts) <= MAX_BATCH_MESSAGES
                or not all(isinstance(value, str) and value for value in attempts)
            ):
                raise ProviderError("invalid_provider_response", outcome="unknown")
            return {"receipt": body.receipt, "acknowledged": True}
        except ProviderError as exc:
            raise HTTPException(exc.status_code, detail=exc.to_detail()) from None
