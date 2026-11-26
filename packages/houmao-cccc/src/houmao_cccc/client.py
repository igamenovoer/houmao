"""Bounded RPC and offer streaming for one CCCC receiver v2 Actor."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
import json
import math
from typing import Literal

import httpx
from pydantic import JsonValue, ValidationError

from houmao_cccc.configuration import CcccConfiguration
from houmao_cccc.models import JSON_OBJECT, ProviderBinding

RECEIVER_PROTOCOL_VERSION = 2
RECEIVER_API_PATH = "/api/v1/external-receiver/v2"
MAX_BATCH_MESSAGES = 64
MAX_BATCH_BYTES = 262144
MAX_STREAM_SECONDS = 20

_OPERATIONS = frozenset(
    {
        "binding",
        "capabilities",
        "members",
        "lease.acquire",
        "lease.renew",
        "lease.release",
        "lease.next",
        "lease.notice.next",
        "lease.outcome",
        "lease.start",
        "lease.settle",
        "chat.ack",
        "chat.send",
        "chat.reply",
        "chat.retry",
        "chat.history",
        "chat.deliveries",
        "chat.gateway-read.claim",
        "chat.gateway-read.result",
        "mail.send",
        "mail.reply",
        "mail.peek",
        "mail.cursor",
        "mail.read",
        "mail.read-receipts",
    }
)
_READ_OPERATIONS = frozenset(
    {
        "binding",
        "capabilities",
        "members",
        "chat.history",
        "chat.deliveries",
        "chat.gateway-read.result",
        "mail.peek",
        "mail.cursor",
        "mail.read-receipts",
    }
)
_BOUNDED_OPERATIONS = frozenset({"lease.next", "chat.history", "mail.peek", "mail.read"})
_SAFE_CODES = frozenset(
    {
        "permission_denied",
        "invalid_grant",
        "receiver_lease_lost",
        "attempt_conflict",
        "uncertain_conflict",
        "daemon_unavailable",
        "event_too_large",
        "attempt_not_found",
        "unauthorized",
        "invalid_token",
        "grant_revoked",
        "stale_binding",
        "actor_not_found",
        "group_not_found",
        "actor_generation_mismatch",
        "actor_changed",
        "receiver_lease_conflict",
        "lease_conflict",
        "lease_expired",
        "stale_lease",
        "stale_attempt",
        "attempt_expired",
        "uncertain_delivery",
        "operation_conflict",
        "invalid_args",
        "invalid_recipient",
        "unsupported_recipient",
        "unsupported_operation",
        "unsupported_mode",
        "invalid_message_mode",
        "event_not_found",
        "content_limit",
        "payload_too_large",
        "cursor_stale",
        "cursor_conflict",
        "read_operation_conflict",
        "read_operation_expired",
        "mail_unsupported",
        "invalid_cursor",
        "receiver_unavailable",
        "service_unavailable",
        "dispatch_failed",
        "readiness_conflict",
        "body_unavailable",
        "uncertain_retry_requires_confirmation",
        "duplicate_operation",
        "group_inactive",
        "direct_receipt_expired",
        "receipt_expired",
        "receipt_conflict",
        "invalid_receipt",
        "stale_reference",
        "reference_scope_error",
        "unsupported_transport",
        "pending_capacity",
        "pending_expired",
        "receiver_transport_conflict",
        "dispatch_conflict",
        "dispatch_not_found",
        "receipt_not_found",
        "direct_ack_expired",
        "queue_snapshot_stale",
        "queue_read_expired",
        "receipt_scope_error",
    }
)


class ProviderError(RuntimeError):
    """Expose allowlisted provider failure metadata without private error text."""

    def __init__(
        self,
        code: str,
        status_code: int = 503,
        retryable: bool = False,
        outcome: Literal["not_sent", "unknown"] = "not_sent",
        retry_after_seconds: float | None = None,
    ) -> None:
        """Construct a content-free transport or service error."""

        super().__init__("CCCC operation failed")
        self.m_code: str = code
        self.m_status_code: int = status_code
        self.m_retryable: bool = retryable
        self.m_outcome: Literal["not_sent", "unknown"] = outcome
        self.m_retry_after_seconds: float | None = retry_after_seconds

    @property
    def code(self) -> str:
        """Return the safe machine-readable error code."""

        return self.m_code

    @property
    def error_code(self) -> str:
        """Return the SDK-compatible safe error code."""

        return self.m_code

    @property
    def status_code(self) -> int:
        """Return the safe response status."""

        return self.m_status_code

    @property
    def retryable(self) -> bool:
        """Return whether a caller-directed retry can be appropriate."""

        return self.m_retryable

    @property
    def outcome(self) -> Literal["not_sent", "unknown"]:
        """Return whether a state mutation may already have occurred."""

        return self.m_outcome

    @property
    def dispatch_outcome(self) -> Literal["not_sent", "unknown"]:
        """Return the SDK-compatible mutation outcome."""

        return self.m_outcome

    @property
    def retry_after_seconds(self) -> float | None:
        """Return safe bounded provider reconnect timing when available."""

        return self.m_retry_after_seconds

    def to_detail(self) -> dict[str, JsonValue]:
        """Serialize safe metadata without the original exception or response."""

        return {
            "error_code": self.m_code,
            "retryable": self.m_retryable,
            "dispatch_outcome": self.m_outcome,
            "retry_after_seconds": self.m_retry_after_seconds,
        }


def _reject_constant(_value: str) -> None:
    """Reject non-finite JSON extensions at the wire boundary."""

    raise ValueError("Non-finite JSON is unsupported")


def _finite_float(value: str) -> float:
    """Reject decimal syntax whose conversion overflows to a non-finite value."""

    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("Non-finite JSON is unsupported")
    return parsed


def _decode_object(data: bytes) -> dict[str, JsonValue]:
    """Parse a bounded strict JSON object from the provider."""

    return JSON_OBJECT.validate_python(
        json.loads(data, parse_constant=_reject_constant, parse_float=_finite_float), strict=True
    )


async def _bounded_body(
    response: httpx.Response, limit: int, outcome: Literal["not_sent", "unknown"]
) -> bytes:
    """Read a finite identity-encoded response body."""

    data = bytearray()
    async for chunk in response.aiter_bytes():
        if len(data) + len(chunk) > limit:
            raise ProviderError("provider_response_limit", 503, False, outcome)
        data.extend(chunk)
    return bytes(data)


async def _ndjson_frames(
    response: httpx.Response, *, frame_limit: int, wire_limit: int, deadline: float
) -> AsyncIterator[tuple[int, dict[str, JsonValue]]]:
    """Decode finite frames without buffering an unbounded line or response."""

    buffer = bytearray()
    received = 0
    chunks = response.aiter_bytes()
    while True:
        try:
            async with asyncio.timeout_at(deadline):
                chunk = await anext(chunks)
        except StopAsyncIteration:
            break
        received += len(chunk)
        if received > wire_limit:
            raise ProviderError("provider_response_limit", 503)
        buffer.extend(chunk)
        while (end := buffer.find(b"\n")) >= 0:
            if end > frame_limit:
                raise ProviderError("provider_response_limit", 503)
            data = bytes(buffer[:end])
            del buffer[: end + 1]
            yield end + 1, _decode_object(data)
        if len(buffer) > frame_limit:
            raise ProviderError("provider_response_limit", 503)
    if buffer:
        raise ProviderError("invalid_provider_response", 503)


class ProviderClient:
    """Own one asynchronous HTTP connection pool for a selected Actor grant."""

    def __init__(self) -> None:
        """Create a client without opening resources or reading credentials."""

        self.m_configuration: CcccConfiguration | None = None
        self.m_http: httpx.AsyncClient | None = None
        self.m_token: str | None = None

    @classmethod
    def from_config(
        cls,
        configuration: CcccConfiguration,
        token: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> ProviderClient:
        """Open a finite, redirect-free client using only the selected token."""

        if not token or len(token) > 8192 or any(not 33 <= ord(char) <= 126 for char in token):
            raise ValueError("Selected CCCC credential token is invalid")
        client = cls()
        client.m_configuration = configuration
        client.m_token = token
        client.m_http = httpx.AsyncClient(
            timeout=configuration.request_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
            headers={"Accept": "application/json", "Accept-Encoding": "identity"},
        )
        return client

    @classmethod
    def from_credentials(cls, configuration: CcccConfiguration, token: str) -> ProviderClient:
        """Construct a client from an already validated selected credential."""

        return cls.from_config(configuration, token)

    async def aclose(self) -> None:
        """Close resources and discard the selected credential from this object."""

        http = self.m_http
        self.m_http = None
        self.m_token = None
        if http is not None:
            await http.aclose()

    async def request(
        self, operation: str, arguments: dict[str, JsonValue] | None = None
    ) -> dict[str, JsonValue]:
        """Perform exactly one bounded RPC request without mutation replay."""

        if operation not in _OPERATIONS:
            raise ProviderError("unsupported_operation", 422)
        configuration, http, token = self.m_configuration, self.m_http, self.m_token
        if configuration is None or http is None or token is None:
            raise ProviderError("service_unavailable", 503, True)
        args = arguments if arguments is not None else {}
        max_response_bytes = (
            max(configuration.max_response_bytes, configuration.mail_max_bytes)
            if operation.startswith("mail.")
            else configuration.max_response_bytes
        )
        if any(
            key in args
            for key in (
                "by",
                "owner",
                "agent_id",
                "group_id",
                "actor_id",
                "actor_generation",
                "token",
            )
        ):
            raise ProviderError("invalid_args", 422)
        try:
            payload = json.dumps(
                {"operation": operation, "arguments": args}, allow_nan=False, separators=(",", ":")
            ).encode()
        except (TypeError, ValueError):
            raise ProviderError("invalid_args", 422) from None
        if len(payload) > max_response_bytes:
            raise ProviderError("payload_too_large", 422)
        outcome: Literal["not_sent", "unknown"] = (
            "not_sent" if operation in _READ_OPERATIONS else "unknown"
        )
        timeout = configuration.request_timeout_seconds
        if operation in {"lease.next", "lease.notice.next"}:
            timeout += configuration.poll_timeout_seconds
        try:
            async with asyncio.timeout(timeout):
                async with http.stream(
                    "POST",
                    configuration.endpoint + RECEIVER_API_PATH + "/rpc",
                    content=payload,
                    headers={
                        "Authorization": "Bearer " + token,
                        "Content-Type": "application/json",
                    },
                    timeout=timeout,
                ) as response:
                    self._check_transport_response(response, outcome)
                    limit = max_response_bytes
                    requested = args.get("max_bytes")
                    if (
                        response.is_success
                        and operation in _BOUNDED_OPERATIONS
                        and type(requested) is int
                        and requested > 0
                    ):
                        limit = min(limit, requested)
                    data = await _bounded_body(response, limit, outcome)
                    return self._decode_response(data, response.status_code, outcome)
        except (httpx.RequestError, TimeoutError):
            raise ProviderError("provider_unavailable", 503, True, outcome) from None

    async def verify_binding(self) -> ProviderBinding:
        """Verify version and exact Actor registration before any receiver operation."""

        result = await self.request("binding")
        if (
            type(result.get("protocol_version")) is not int
            or result.get("protocol_version") != RECEIVER_PROTOCOL_VERSION
        ):
            raise ProviderError("receiver_incompatible")
        try:
            binding = ProviderBinding.model_validate(result)
        except ValidationError:
            raise ProviderError("invalid_provider_response") from None
        configuration = self.m_configuration
        assert configuration is not None
        if (
            binding.group_id != configuration.group_id
            or binding.actor_id != configuration.actor_id
            or binding.actor_generation != configuration.actor_generation
        ):
            raise ProviderError("actor_generation_mismatch", 409)
        return binding

    async def capabilities(self) -> dict[str, JsonValue]:
        """Read validated version and operation advertisements for the current Actor."""

        capabilities = await self.request("capabilities")
        operations = capabilities.get("operations")
        if (
            type(capabilities.get("protocol_version")) is not int
            or capabilities.get("protocol_version") != RECEIVER_PROTOCOL_VERSION
            or not isinstance(operations, list)
            or not all(isinstance(operation, str) for operation in operations)
        ):
            raise ProviderError("receiver_incompatible")
        return capabilities

    async def offer_stream(
        self,
        lease_id: str,
        lease_generation: int | str,
        *,
        kind: Literal["chat", "mail_notice"],
        limit: int,
        max_bytes: int,
        after_sequence: int = 0,
    ) -> AsyncGenerator[dict[str, JsonValue], None]:
        """Yield ordered offers from one finite credit stream under the selected lease."""

        configuration, http, token = self.m_configuration, self.m_http, self.m_token
        if configuration is None or http is None or token is None:
            raise ProviderError("service_unavailable", 503, True)
        if (
            kind not in {"chat", "mail_notice"}
            or not isinstance(lease_id, str)
            or not 1 <= len(lease_id) <= 512
            or type(lease_generation) not in {int, str}
            or type(limit) is not int
            or not 1 <= limit <= MAX_BATCH_MESSAGES
            or type(max_bytes) is not int
            or not 1 <= max_bytes <= MAX_BATCH_BYTES
            or type(after_sequence) is not int
            or after_sequence < 0
        ):
            raise ProviderError("invalid_args", 422)
        params = {
            "lease_id": lease_id,
            "lease_generation": lease_generation,
            "kind": kind,
            "limit": limit,
            "max_bytes": max_bytes,
            "after_sequence": after_sequence,
        }
        timeout = configuration.request_timeout_seconds + MAX_STREAM_SECONDS
        deadline = asyncio.get_running_loop().time() + timeout
        try:
            async with http.stream(
                "GET",
                configuration.endpoint + RECEIVER_API_PATH + "/stream",
                params=params,
                headers={"Authorization": "Bearer " + token, "Accept": "application/x-ndjson"},
                timeout=timeout,
            ) as response:
                self._check_transport_response(response, "not_sent")
                if not response.is_success:
                    async with asyncio.timeout_at(deadline):
                        data = await _bounded_body(
                            response, configuration.max_response_bytes, "not_sent"
                        )
                    self._decode_response(data, response.status_code, "not_sent")
                    raise ProviderError("invalid_provider_response")
                media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if media_type != "application/x-ndjson":
                    raise ProviderError("invalid_provider_response")
                count = 0
                offer_bytes = 0
                async for frame_bytes, frame in _ndjson_frames(
                    response,
                    frame_limit=max_bytes + 4096,
                    wire_limit=max_bytes + 4096,
                    deadline=deadline,
                ):
                    frame_kind = frame.get("kind")
                    if frame_kind == "heartbeat":
                        continue
                    if frame_kind == "error" and isinstance(error := frame.get("error"), dict):
                        code = self._safe_code(error.get("code"))
                        raise ProviderError(code, retryable=error.get("retryable") is True)
                    offer = frame.get("offer")
                    if frame_kind != "offer" or not isinstance(offer, dict):
                        raise ProviderError("invalid_provider_response")
                    count += 1
                    offer_bytes += frame_bytes
                    if count > limit or offer_bytes > max_bytes:
                        raise ProviderError("provider_response_limit")
                    yield offer
        except (httpx.RequestError, TimeoutError):
            raise ProviderError("provider_unavailable", 503, True) from None
        except (ValueError, ValidationError, RecursionError):
            raise ProviderError("invalid_provider_response") from None

    async def call(
        self, operation: str, arguments: dict[str, JsonValue] | None = None
    ) -> dict[str, JsonValue]:
        """Invoke the same single-attempt RPC operation."""

        return await self.request(operation, arguments)

    @staticmethod
    def _check_transport_response(
        response: httpx.Response, outcome: Literal["not_sent", "unknown"]
    ) -> None:
        """Reject redirects and content transformations before body consumption."""

        if 300 <= response.status_code < 400:
            raise ProviderError("provider_redirect_refused", 503, False, outcome)
        if response.headers.get("content-encoding", "identity").lower() not in {"", "identity"}:
            raise ProviderError("invalid_provider_response", 503, False, outcome)

    @staticmethod
    def _safe_code(raw_code: JsonValue) -> str:
        """Return a contract error code without forwarding free-form provider text."""

        return (
            raw_code if isinstance(raw_code, str) and raw_code in _SAFE_CODES else "provider_error"
        )

    def _decode_response(
        self,
        data: bytes,
        status: int,
        uncertain_outcome: Literal["not_sent", "unknown"],
    ) -> dict[str, JsonValue]:
        """Validate the bounded envelope and sanitize any provider error."""

        try:
            decoded = _decode_object(data)
        except (ValueError, ValidationError, UnicodeDecodeError, RecursionError):
            code = "receiver_incompatible" if status in {404, 405} else "invalid_provider_response"
            raise ProviderError(code, 503, False, uncertain_outcome) from None
        if decoded.get("ok") is True and 200 <= status < 300:
            result = decoded.get("result")
            if isinstance(result, dict):
                return result
            raise ProviderError("invalid_provider_response", 503, False, uncertain_outcome)
        error = decoded.get("error")
        if isinstance(error, dict) and decoded.get("ok") is False and status >= 400:
            code = self._safe_code(error.get("code"))
            retryable = error.get("retryable") is True
            retry_after = error.get("retry_after_seconds")
            delay = (
                float(retry_after)
                if isinstance(retry_after, (float, int))
                and not isinstance(retry_after, bool)
                and math.isfinite(float(retry_after))
                and 0 <= float(retry_after) <= 300
                else None
            )
            safe_status = status if status in {401, 403, 404, 409, 413, 422, 429, 503} else 503
            reported_outcome = error.get("dispatch_outcome", error.get("outcome"))
            outcome: Literal["not_sent", "unknown"] = (
                "unknown"
                if reported_outcome == "unknown"
                or ((status >= 500 or status == 408) and uncertain_outcome == "unknown")
                else "not_sent"
            )
            raise ProviderError(code, safe_status, retryable, outcome, delay)
        code = "receiver_incompatible" if status in {404, 405} else "invalid_provider_response"
        raise ProviderError(code, 503, False, uncertain_outcome)
