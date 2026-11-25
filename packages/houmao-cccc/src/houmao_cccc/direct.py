"""Run common CCCC commands through an explicitly selected private Actor profile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, cast
from urllib.parse import unquote

import httpx
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from houmao.gateway.access import read_private_access_file
from houmao_cccc.client import MAX_BATCH_BYTES, MAX_BATCH_MESSAGES, ProviderClient, ProviderError
from houmao_cccc.configuration import (
    MAIL_DEFAULT_BYTES,
    MAIL_MAX_LIMIT,
    CcccConfiguration,
    validate_credentials,
)
from houmao_cccc.mail import (
    MailBatch,
    MailCursor,
    MailReadReceipt,
    mail_event_id,
    qualified_mail,
    validate_mail_read,
    validate_mail_receipt,
)
from houmao_cccc.models import JSON_OBJECT, ReceiverLease


class _DirectChatOffer(BaseModel):
    """Project one exact provider offer into an ordered direct-tool result."""

    model_config = ConfigDict(extra="ignore", strict=True)

    kind: Literal["chat"] = "chat"
    group_id: str
    actor_id: str
    actor_generation: str
    lease_generation: int
    sequence: int = Field(gt=0)
    sender: str = Field(min_length=1, max_length=256)
    timestamp: str = Field(min_length=1, max_length=128)
    message_mode: Literal["send", "request_reply"]
    text: str = Field(min_length=1, max_length=65536)
    event_ref: str = Field(min_length=1, max_length=16384)

    def message(self) -> dict[str, JsonValue]:
        """Expose display fields and the CCCC reference usable in a later invocation."""

        return {
            "sender": self.sender,
            "timestamp": self.timestamp,
            "mode": self.message_mode,
            "text": self.text,
            "event_ref": self.event_ref,
        }


def load_direct_profile(
    source: Path, *, agent_id: str, timeout_seconds: float
) -> tuple[CcccConfiguration, str]:
    """Read one owner-only profile and verify its local owner and fixed descriptors."""

    try:
        profile = JSON_OBJECT.validate_python(json.loads(read_private_access_file(source)))
        if type(profile.get("schema_version")) is not int or profile.get("schema_version") != 1:
            raise ValueError("Invalid profile schema")
        configuration = CcccConfiguration.model_validate(
            {
                **{
                    key: profile.get(key)
                    for key in ("endpoint", "group_id", "actor_id", "actor_generation")
                },
                "request_timeout_seconds": min(timeout_seconds, 60),
            }
        )
        return configuration, validate_credentials(configuration, agent_id, profile)
    except (OSError, ValueError, ValidationError):
        raise ValueError("The selected private CCCC profile is unavailable or invalid.") from None


def _require_operations(capabilities: dict[str, JsonValue], *operations: str) -> None:
    """Fail before a provider operation unless the Actor can use every required call."""

    advertised = capabilities.get("operations")
    if not isinstance(advertised, list) or any(
        operation not in advertised for operation in operations
    ):
        raise ProviderError("unsupported_operation", 422)


def _provider_limit(limits: JsonValue, key: str) -> int:
    """Read one positive negotiated bound without accepting a bool or coercion."""

    value = limits.get(key) if isinstance(limits, dict) else None
    if type(value) is not int or value <= 0:
        raise ProviderError("receiver_incompatible")
    return value


def _bounded_selection(requested: JsonValue, default: int, maximum: int) -> int:
    """Select a default within the negotiated limit and reject an excessive request."""

    if requested is None:
        return min(default, maximum)
    if type(requested) is not int or not 1 <= requested <= maximum:
        raise ProviderError("content_limit", 422)
    return requested


async def _pull(
    client: ProviderClient,
    configuration: CcccConfiguration,
    capabilities: dict[str, JsonValue],
    body: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    """Claim one bounded snapshot, then release intake while its receipt remains usable."""

    _require_operations(capabilities, "lease.acquire", "lease.next", "lease.release", "chat.ack")
    features = capabilities.get("features")
    if not isinstance(features, dict) or features.get("chat_direct_pull") is not True:
        raise ProviderError("receiver_incompatible")
    limits = capabilities.get("limits")
    maximum = min(MAX_BATCH_MESSAGES, _provider_limit(limits, "max_batch_messages"))
    max_bytes = min(
        MAX_BATCH_BYTES,
        configuration.max_response_bytes,
        _provider_limit(limits, "max_batch_bytes"),
    )
    count = _bounded_selection(body.get("limit"), maximum, maximum)
    budget = _bounded_selection(body.get("max_bytes"), max_bytes, max_bytes)
    try:
        lease = ReceiverLease.model_validate(
            await client.request("lease.acquire", {"transport": "pull", "receiver": "direct"})
        )
    except ValidationError:
        raise ProviderError("invalid_provider_response", outcome="unknown") from None
    scope: dict[str, JsonValue] = {
        "lease_id": lease.lease_id,
        "lease_generation": lease.lease_generation,
    }
    try:
        result = await client.request("lease.next", {**scope, "limit": count, "max_bytes": budget})
        return _pull_result(result, count, configuration, lease)
    finally:
        try:
            await client.request("lease.release", scope)
        except ProviderError:
            # The provider lease expires independently of its direct-read receipt.
            pass


def _pull_result(
    result: dict[str, JsonValue], count: int, configuration: CcccConfiguration, lease: ReceiverLease
) -> dict[str, JsonValue]:
    """Validate one exact receipt and preserve original sequence order in the result."""

    offers, receipt = result.get("offers"), result.get("receipt")
    if (
        not isinstance(offers, list)
        or len(offers) > count
        or (not offers and receipt is not None)
        or (offers and (not isinstance(receipt, str) or not 1 <= len(receipt) <= 16384))
    ):
        raise ProviderError("invalid_provider_response", outcome="unknown")
    try:
        messages: list[JsonValue] = []
        previous_sequence = 0
        for value in offers:
            offer = _DirectChatOffer.model_validate(value)
            if (
                offer.sequence <= previous_sequence
                or offer.group_id != configuration.group_id
                or offer.actor_id != configuration.actor_id
                or offer.actor_generation != configuration.actor_generation
                or offer.lease_generation != lease.lease_generation
            ):
                raise ValueError("Direct pull offers are out of sequence or scope")
            previous_sequence = offer.sequence
            messages.append(offer.message())
    except (ValueError, ValidationError):
        raise ProviderError("invalid_provider_response", outcome="unknown") from None
    return {"messages": messages, "receipt": receipt}


async def _mail(
    client: ProviderClient,
    configuration: CcccConfiguration,
    capabilities: dict[str, JsonValue],
    route: str,
    body: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    """Use the same qualified Mail contract with native Actor-scoped inputs."""

    qualified = qualified_mail(capabilities)
    if route == "status":
        return {
            "backend": "cccc-mail",
            "qualified": qualified,
            "available": qualified,
            "consumed": False,
        }
    if not qualified:
        raise ProviderError("mail_unsupported", 503)
    if route.startswith("reads/"):
        operation_id = unquote(route.removeprefix("reads/"))
        result = await client.request("mail.read-receipts", {"operation_id": operation_id})
        if type(result.get("found")) is not bool:
            raise ProviderError("invalid_provider_response")
        projection: dict[str, JsonValue] = {
            "operation_id": operation_id,
            "found": result["found"],
            "consumed": False,
            "outcome": "unknown",
        }
        if result["found"]:
            try:
                receipt = MailReadReceipt.model_validate(result.get("receipt"))
                validate_mail_receipt(receipt, operation_id, configuration.actor_generation)
            except (ValueError, ValidationError):
                raise ProviderError("invalid_provider_response") from None
            projection.update(receipt=receipt.model_dump(mode="json"), outcome=receipt.outcome)
        return projection
    if route in {"peek", "read"}:
        return await _mail_batch(client, configuration, capabilities, route, body)
    result = await client.request("mail." + route, body)
    try:
        if route == "cursor":
            MailCursor.model_validate(result.get("cursor"))
        else:
            event = result.get("event")
            if result.get("consumed") is not False or not isinstance(event, dict):
                raise ValueError("Invalid Mail mutation result")
            mail_event_id(event)
    except (ValueError, ValidationError):
        outcome: Literal["not_sent", "unknown"] = "not_sent" if route == "cursor" else "unknown"
        raise ProviderError("invalid_provider_response", outcome=outcome) from None
    return result


async def _mail_batch(
    client: ProviderClient,
    configuration: CcccConfiguration,
    capabilities: dict[str, JsonValue],
    route: str,
    body: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    """Read or inspect a bounded batch using native cursor and receipt semantics."""

    limits = capabilities.get("limits")
    count = _bounded_selection(
        body.get("limit"),
        configuration.mail_limit,
        min(MAIL_MAX_LIMIT, _provider_limit(limits, "max_mail_messages")),
    )
    budget = _bounded_selection(
        body.get("max_bytes"),
        MAIL_DEFAULT_BYTES,
        min(configuration.mail_max_bytes, _provider_limit(limits, "max_mail_response_bytes")),
    )
    result = await client.request("mail." + route, {**body, "limit": count, "max_bytes": budget})
    try:
        batch = MailBatch.model_validate(result)
        if route == "read":
            validate_mail_read(
                batch,
                operation_id=cast(str, body["operation_id"]),
                actor_generation=configuration.actor_generation,
                expected_cursor=cast(str, body["expected_cursor"]),
                count=count,
            )
        else:
            if (
                batch.consumed
                or batch.receipt is not None
                or len(batch.messages) > count
                or (batch.has_more and not batch.messages)
            ):
                raise ValueError("Malformed non-consuming inspection")
            for event in batch.messages:
                mail_event_id(event)
    except (ValueError, ValidationError):
        outcome: Literal["not_sent", "unknown"] = "unknown" if route == "read" else "not_sent"
        raise ProviderError("invalid_provider_response", outcome=outcome) from None
    return result


async def invoke_direct(
    configuration: CcccConfiguration,
    token: str,
    route: str,
    body: dict[str, JsonValue],
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, JsonValue]:
    """Verify the selected Actor then invoke exactly one common provider operation."""

    client = ProviderClient.from_config(configuration, token, transport=transport)
    try:
        binding = await client.verify_binding()
        if route == "/binding":
            return binding.model_dump(mode="json")
        capabilities = await client.capabilities()
        if route == "/capabilities":
            return capabilities
        if route == "/discovery":
            return {
                **binding.model_dump(mode="json"),
                "endpoint": configuration.endpoint,
                "operations": capabilities["operations"],
            }
        if route == "/chat/pull":
            return await _pull(client, configuration, capabilities, body)
        if route.startswith("/mail/"):
            return await _mail(
                client, configuration, capabilities, route.removeprefix("/mail/"), body
            )
        operation = route.lstrip("/").replace("/", ".")
        _require_operations(capabilities, operation)
        result = await client.request(operation, body)
        if operation == "chat.ack":
            identities = result.get("attempt_ids")
            if (
                result.get("receipt") != body.get("receipt")
                or result.get("acknowledged") is not True
                or not isinstance(identities, list)
                or not 1 <= len(identities) <= MAX_BATCH_MESSAGES
                or any(not isinstance(item, str) or not item for item in identities)
            ):
                raise ProviderError("invalid_provider_response", outcome="unknown")
        return result
    finally:
        await client.aclose()
