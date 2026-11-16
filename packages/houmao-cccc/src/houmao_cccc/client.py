"""Bounded asynchronous CCCC receiver RPC transport with no mutation retries."""

from __future__ import annotations

import json
import math
from typing import Literal

import httpx
from pydantic import JsonValue, ValidationError

from houmao_cccc.configuration import CcccConfiguration
from houmao_cccc.models import JSON_OBJECT

_OPERATIONS = frozenset(
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
        "mail.peek",
        "mail.cursor",
        "mail.read-receipts",
    }
)
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
        if any(key in args for key in ("by", "owner", "agent_id", "group_id", "actor_id", "token")):
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
        if operation == "lease.next":
            timeout += configuration.poll_timeout_seconds
        try:
            async with http.stream(
                "POST",
                configuration.endpoint + "/api/v1/external-receiver/v1/rpc",
                content=payload,
                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                timeout=timeout,
            ) as response:
                if 300 <= response.status_code < 400:
                    raise ProviderError("provider_redirect_refused", 503, False, outcome)
                encoding = response.headers.get("content-encoding", "identity").lower()
                if encoding not in {"", "identity"}:
                    raise ProviderError("invalid_provider_response", 503, False, outcome)
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(data) + len(chunk) > max_response_bytes:
                        raise ProviderError("provider_response_limit", 503, False, outcome)
                    data.extend(chunk)
                return self._decode_response(bytes(data), response.status_code, outcome)
        except ProviderError:
            raise
        except httpx.RequestError:
            raise ProviderError("provider_unavailable", 503, True, outcome) from None

    async def call(
        self, operation: str, arguments: dict[str, JsonValue] | None = None
    ) -> dict[str, JsonValue]:
        """Invoke the same single-attempt RPC operation."""

        return await self.request(operation, arguments)

    def _decode_response(
        self,
        data: bytes,
        status: int,
        uncertain_outcome: Literal["not_sent", "unknown"],
    ) -> dict[str, JsonValue]:
        """Validate the bounded envelope and sanitize any provider error."""

        try:
            decoded = JSON_OBJECT.validate_python(
                json.loads(data, parse_constant=_reject_constant), strict=True
            )
        except (ValueError, ValidationError, UnicodeDecodeError):
            code = "receiver_incompatible" if status in {404, 405} else "invalid_provider_response"
            raise ProviderError(code, 503, False, uncertain_outcome) from None
        if decoded.get("ok") is True and 200 <= status < 300:
            result = decoded.get("result")
            if isinstance(result, dict):
                return result
            raise ProviderError("invalid_provider_response", 503, False, uncertain_outcome)
        error = decoded.get("error")
        if isinstance(error, dict) and decoded.get("ok") is False and status >= 400:
            raw_code = error.get("code")
            code = (
                raw_code
                if isinstance(raw_code, str) and raw_code in _SAFE_CODES
                else "provider_error"
            )
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
