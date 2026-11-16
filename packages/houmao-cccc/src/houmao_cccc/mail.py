"""Explicit deferred Mail routes, scoped read handles, and precommit wire budgets."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
import json
import re
import time
from typing import TYPE_CHECKING, Literal, cast

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError, field_validator

from houmao_cccc.client import ProviderError
from houmao_cccc.references import ReferenceError

if TYPE_CHECKING:
    from houmao_cccc.plugin import CcccPlugin

MAIL_OPERATIONS = frozenset(
    {"mail.send", "mail.reply", "mail.peek", "mail.cursor", "mail.read", "mail.read-receipts"}
)
MAIL_FEATURES = frozenset(
    {
        "mail_expected_cursor",
        "mail_read_receipts",
        "mail_read_crash_recovery",
        "mail_precommit_response_budget",
    }
)
_OPERATION = r"^[A-Za-z0-9_.:-]{1,128}$"
_IDENTIFIER = re.compile(r"[A-Za-z0-9_.:-]{0,512}\Z")


class MailRequest(BaseModel):
    """Select the persisted binding and retain the caller's mutation identity."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_binding_id: str = Field(min_length=1, max_length=256)
    operation_id: str = Field(pattern=_OPERATION)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        """Keep caller identities addressable as literal receipt-path segments."""

        if value in {".", ".."}:
            raise ValueError("Operation identity must not be a navigation path")
        return value


class MailSendRequest(MailRequest):
    """Store deferred correspondence for explicit same-Group Actor recipients."""

    to: list[str] = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=1048576)

    @field_validator("text")
    @classmethod
    def _text(cls, value: str) -> str:
        """Reject blank content without rewriting correspondence."""

        if not value.strip():
            raise ValueError("Mail text must not be blank")
        return value


class MailReplyRequest(MailRequest):
    """Reply through a verifiable native event handle without reading the inbox."""

    event_ref: str = Field(min_length=1, max_length=16384)
    text: str = Field(min_length=1, max_length=1048576)

    @field_validator("text")
    @classmethod
    def _text(cls, value: str) -> str:
        """Reject blank reply content without changing its text."""

        return MailSendRequest._text(value)


class MailReadRequest(MailRequest):
    """Consume one bounded ordered batch under an authenticated cursor precondition."""

    expected_cursor: str = Field(min_length=1, max_length=16384)
    limit: int | None = Field(default=None, ge=1, le=200)
    max_bytes: int | None = Field(default=None, ge=1024, le=1048576)


def _identifier(value: str, *, empty: bool = False) -> str:
    """Bound native targeting identifiers before creating expandable reference handles."""

    if not _IDENTIFIER.fullmatch(value) or (not value and not empty):
        raise ValueError("Invalid native Mail identifier")
    return value


class MailCursor(BaseModel):
    """Validate the finite native boundary without deriving another read authority."""

    model_config = ConfigDict(extra="ignore", strict=True)
    event_id: str = Field(max_length=512)
    ts: str = Field(default="", max_length=128)
    updated_at: str = Field(default="", max_length=128)

    @field_validator("event_id")
    @classmethod
    def _event_id(cls, value: str) -> str:
        """Accept the empty initial boundary and finite native event identifiers."""

        return _identifier(value, empty=True)


class MailReadReceipt(BaseModel):
    """Describe an authoritative provider decision with bounded event provenance."""

    model_config = ConfigDict(extra="ignore", strict=True)
    operation_id: str = Field(pattern=_OPERATION)
    actor_generation: str = Field(min_length=1, max_length=256)
    before_cursor: str = Field(max_length=512)
    after_cursor: str = Field(max_length=512)
    event_ids: list[str] = Field(max_length=200)
    outcome: Literal["consumed", "empty"]
    read_event_id: str = Field(max_length=512)

    @field_validator("operation_id")
    @classmethod
    def _operation_id(cls, value: str) -> str:
        """Keep stored decision identities safely addressable through the receipt API."""

        return MailRequest._operation_id(value)

    @field_validator("before_cursor", "after_cursor", "read_event_id")
    @classmethod
    def _cursor_id(cls, value: str) -> str:
        """Keep all receipt boundaries within the qualified reference-size contract."""

        return _identifier(value, empty=True)

    @field_validator("event_ids")
    @classmethod
    def _event_ids(cls, values: list[str]) -> list[str]:
        """Reject duplicate or oversized receipt provenance."""

        if len(set(values)) != len(values):
            raise ValueError("Receipt event identifiers repeat")
        return [_identifier(value) for value in values]


class MailBatch(BaseModel):
    """Validate complete peek/read batches without omitting native message content."""

    model_config = ConfigDict(extra="ignore", strict=True)
    messages: list[dict[str, JsonValue]] = Field(max_length=200)
    cursor: MailCursor
    has_more: bool
    consumed: bool = False
    count_accuracy: Literal["unknown", "bounded", "capped", "exact"] = "bounded"
    outcome: Literal["consumed", "empty", "already_completed"] | None = None
    receipt: MailReadReceipt | None = None


def _size(value: JsonValue) -> int:
    """Measure the same compact UTF-8 JSON representation used by HTTP responses."""

    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode())


class MailService:
    """Expose deferred operations through the existing immutable plugin binding."""

    def __init__(self) -> None:
        """Keep only bounded metadata; never retain Mail bodies or deferred jobs."""

        self.m_plugin: CcccPlugin | None = None
        self.m_router: APIRouter = APIRouter()
        self.m_observed_at: str | None = None
        self.m_observed_monotonic: float | None = None
        self.m_pending_count: int | None = None
        self.m_count_accuracy: str = "unknown"
        self.m_unavailable: bool = False

    @classmethod
    def from_plugin(cls, plugin: CcccPlugin) -> MailService:
        """Stage Mail routes without reading credentials, state, or provider resources."""

        service = cls()
        service.m_plugin = plugin
        for path, endpoint, methods in (
            ("/mail/status", service.status, ["GET"]),
            ("/mail/peek", service.peek, ["GET"]),
            ("/mail/cursor", service.cursor, ["GET"]),
            ("/mail/send", service.send, ["POST"]),
            ("/mail/reply", service.reply, ["POST"]),
            ("/mail/read", service.read, ["POST"]),
            ("/mail/reads/{operation_id}", service.receipt, ["GET"]),
        ):
            service.m_router.add_api_route(path, endpoint, methods=methods)
        for operation in ("archive", "move", "mark", "attachments", "submission", "mark-unread"):
            service.m_router.add_api_route(
                "/mail/" + operation,
                service._unsupported_handler(operation),
                methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            )
        return service

    def _unsupported_handler(self, operation: str) -> Callable[[], Awaitable[dict[str, JsonValue]]]:
        """Stage a concrete unsupported path without shadowing valid Mail routes."""

        async def endpoint() -> dict[str, JsonValue]:
            """Return a structured refusal for this unsupported email-style operation."""

            return await self.unsupported(operation)

        return endpoint

    @property
    def router(self) -> APIRouter:
        """Return the complete namespace-relative Mail route inventory."""

        return self.m_router

    def _plugin(self) -> CcccPlugin:
        """Require factory-bound immutable connection authority."""

        assert self.m_plugin is not None
        return self.m_plugin

    def qualified(self) -> bool:
        """Require the complete negotiated consuming-read and recovery contract."""

        capabilities = self._plugin().m_provider_capabilities
        operations, features, limits = (
            capabilities.get("operations"),
            capabilities.get("features"),
            capabilities.get("limits"),
        )
        return (
            capabilities.get("mail") is True
            and isinstance(operations, list)
            and MAIL_OPERATIONS.issubset({op for op in operations if isinstance(op, str)})
            and isinstance(features, dict)
            and all(features.get(feature) is True for feature in MAIL_FEATURES)
            and isinstance(limits, dict)
            and type(limits.get("max_mail_messages")) is int
            and cast(int, limits["max_mail_messages"]) > 0
            and type(limits.get("max_mail_response_bytes")) is int
            and cast(int, limits["max_mail_response_bytes"]) >= 1024
        )

    def capabilities(self) -> dict[str, JsonValue]:
        """Project effective Mail limits separately from chat and email channels."""

        qualified = self.qualified()
        config = self._plugin()._config()
        limits = self._plugin().m_provider_capabilities.get("limits")
        source = limits if isinstance(limits, dict) else {}
        max_messages = min(200, cast(int, source["max_mail_messages"])) if qualified else 200
        max_bytes = (
            min(config.mail_max_bytes, cast(int, source["max_mail_response_bytes"]))
            if qualified
            else config.mail_max_bytes
        )
        return {
            "available": qualified and self._plugin().m_phase == "connected",
            "qualified": qualified,
            "backend": "cccc-mail",
            "operations": cast(list[JsonValue], sorted(MAIL_OPERATIONS)) if qualified else [],
            "limits": {
                "default_messages": min(config.mail_limit, max_messages),
                "max_messages": max_messages,
                "default_response_bytes": min(262144, max_bytes),
                "max_response_bytes": max_bytes,
                "request_timeout_seconds": config.request_timeout_seconds,
            },
            "recipient_scope": "bound-group-actors",
            "modes": ["mail"],
            "read_semantics": "explicit_ordered_batch_consumption",
            "unsupported": ["archive", "move", "mark-unread", "attachments", "submission"],
        }

    def _require(self) -> None:
        """Refuse Mail without weakening a compatible chat-only connection."""

        if not self.qualified():
            raise HTTPException(501, detail={"error_code": "mail_unsupported", "retryable": False})

    def _identity(self) -> dict[str, JsonValue]:
        """Identify CCCC provenance without occupying an email identity slot."""

        plugin = self._plugin()
        return {
            "backend": "cccc-mail",
            "binding_id": plugin._context().binding_id,
            "group_id": plugin._config().group_id,
            "actor_id": plugin._config().actor_id,
        }

    def _ref(self, kind: str, value: str) -> str:
        """Encode finite cursor or operation provenance using existing owner scope."""

        return self._plugin()._references().encode(kind, {"value": value})

    def _decode(self, kind: str, reference: str) -> str:
        """Reject foreign or malformed handles before provider retrieval or mutation."""

        try:
            value = self._plugin()._references().decode(reference, kind)
            if not isinstance(value, dict) or not isinstance(value.get("value"), str):
                raise ValueError
            identifier = cast(str, value["value"])
            return _identifier(identifier, empty=kind == "mail-cursor")
        except (ValueError, ReferenceError):
            raise HTTPException(422, detail={"error_code": "reference_scope_error"}) from None

    def _budgets(self, limit: int | None, max_bytes: int | None) -> tuple[int, int]:
        """Apply local and provider bounds before issuing a consuming request."""

        self._require()
        limits = cast(dict[str, JsonValue], self.capabilities()["limits"])
        count = cast(int, limits["default_messages"]) if limit is None else limit
        budget = cast(int, limits["default_response_bytes"]) if max_bytes is None else max_bytes
        if count > cast(int, limits["max_messages"]) or budget > cast(
            int, limits["max_response_bytes"]
        ):
            raise HTTPException(422, detail={"error_code": "content_limit", "retryable": False})
        return count, budget

    def _reserves(self, operation_id: str = "") -> tuple[int, int]:
        """Reserve complete reference expansion before the provider commits consumption."""

        plugin = self._plugin()
        cursor_ref = self._ref("mail-cursor", "x" * 512)
        read_ref = self._ref("mail-read", operation_id or "x" * 128)
        event_ref = plugin._references().encode("event", {"event_id": "x" * 512})
        fixed = (
            _size(
                {
                    **self._identity(),
                    "cursor_ref": cursor_ref,
                    "operation_id": operation_id,
                    "read_ref": read_ref,
                    "consumed": True,
                    "receipt": {
                        "before_cursor_ref": cursor_ref,
                        "after_cursor_ref": cursor_ref,
                        "read_ref": read_ref,
                        "event_refs": [],
                    },
                }
            )
            + 1024
        )
        per_event = _size({"event_id": "x" * 512, "event_ref": event_ref}) + _size(event_ref) + 32
        return fixed, per_event

    def _observe(self, count: int, has_more: bool, accuracy: str = "bounded") -> None:
        """Retain only bounded pending metadata after an explicit provider observation."""

        self.m_observed_at = datetime.now(timezone.utc).isoformat()
        self.m_observed_monotonic = time.monotonic()
        self.m_pending_count = count
        self.m_count_accuracy = "capped" if has_more else accuracy
        self.m_unavailable = False

    def observe_notice(self, count: int) -> None:
        """Record content-free notice metadata without fetching or consuming a batch."""

        self._observe(count, False, "bounded")

    def _cursor_result(self, cursor: MailCursor) -> dict[str, JsonValue]:
        """Expose native provenance together with a binding-authenticated cursor."""

        return {
            "cursor": cursor.model_dump(mode="json"),
            "cursor_ref": self._ref("mail-cursor", cursor.event_id),
        }

    def _receipt_result(self, receipt: MailReadReceipt, operation_id: str) -> dict[str, JsonValue]:
        """Decorate authoritative receipts without fetching or caching message bodies."""

        if (
            receipt.operation_id != operation_id
            or receipt.actor_generation != self._plugin()._config().actor_generation
            or (receipt.outcome == "consumed" and not receipt.event_ids)
            or (receipt.outcome == "empty" and receipt.event_ids)
            or receipt.after_cursor
            != (receipt.event_ids[-1] if receipt.event_ids else receipt.before_cursor)
        ):
            raise ValueError("Receipt scope differs")
        return {
            **receipt.model_dump(mode="json"),
            "before_cursor_ref": self._ref("mail-cursor", receipt.before_cursor),
            "after_cursor_ref": self._ref("mail-cursor", receipt.after_cursor),
            "read_ref": self._ref("mail-read", operation_id),
            "event_refs": [
                self._plugin()._references().encode("event", {"event_id": identifier})
                for identifier in receipt.event_ids
            ],
        }

    def _error(
        self,
        error: ProviderError,
        operation_id: str | None = None,
        *,
        read_operation: bool = False,
    ) -> HTTPException:
        """Preserve safe caller reconciliation identity without retrying a mutation."""

        detail = error.to_detail()
        detail.update(self._identity())
        if error.status_code >= 500:
            self.m_unavailable = True
        if operation_id is not None:
            detail["operation_id"] = operation_id
            if read_operation:
                detail["read_ref"] = self._ref("mail-read", operation_id)
        return HTTPException(error.status_code, detail=detail)

    async def status(self, request: Request) -> dict[str, JsonValue]:
        """Read maintained metadata without making a provider call or claiming empty Mail."""

        plugin = self._plugin()
        plugin._queries(request, set())
        age = (
            time.monotonic() - self.m_observed_monotonic
            if self.m_observed_monotonic is not None
            else None
        )
        stale = age is None or age > 60 or plugin.m_phase != "connected" or self.m_unavailable
        return {
            **self._identity(),
            "connection": plugin.m_phase,
            "qualified": self.qualified(),
            "available": self.qualified() and plugin.m_phase == "connected",
            "observed_at": self.m_observed_at,
            "observation_age_seconds": age,
            "stale": stale,
            "current_truth": "unknown" if stale else "sampled",
            "pending_count": self.m_pending_count,
            "count_accuracy": self.m_count_accuracy,
            "consumed": False,
        }

    async def cursor(self, request: Request) -> dict[str, JsonValue]:
        """Inspect the current authoritative boundary without initiating a new read."""

        plugin = self._plugin()
        plugin._queries(request, set())
        self._require()
        try:
            result = await plugin._call("mail.cursor", {})
            cursor = MailCursor.model_validate(result.get("cursor"))
            self.m_unavailable = False
            return {**self._identity(), **self._cursor_result(cursor), "consumed": False}
        except (ValidationError, ValueError, ReferenceError):
            raise self._error(ProviderError("invalid_provider_response")) from None
        except ProviderError as error:
            raise self._error(error) from None

    async def peek(
        self,
        request: Request,
        limit: int | None = Query(default=None, ge=1, le=200),
        max_bytes: int | None = Query(default=None, ge=1024, le=1048576),
    ) -> dict[str, JsonValue]:
        """Explicitly inspect a bounded next batch without consuming its native cursor."""

        plugin = self._plugin()
        plugin._queries(request, {"limit", "max_bytes"})
        count, budget = self._budgets(limit, max_bytes)
        fixed, per_event = self._reserves()
        try:
            result = await plugin._call(
                "mail.peek",
                {
                    "limit": count,
                    "max_bytes": budget,
                    "response_overhead_bytes": fixed,
                    "per_event_overhead_bytes": per_event,
                },
            )
            batch = MailBatch.model_validate(result)
            if (
                batch.consumed
                or batch.receipt is not None
                or len(batch.messages) > count
                or (batch.has_more and not batch.messages)
            ):
                raise ValueError("Malformed non-consuming inspection")
            messages = self._messages(batch.messages)
            response: dict[str, JsonValue] = {
                **self._identity(),
                **self._cursor_result(batch.cursor),
                "messages": messages,
                "has_more": batch.has_more,
                "count_accuracy": "capped" if batch.has_more else batch.count_accuracy,
                "consumed": False,
            }
            if _size(response) > budget:
                raise ProviderError("content_limit", 422)
            self._observe(len(messages), batch.has_more, batch.count_accuracy)
            return response
        except (ValidationError, ValueError, ReferenceError):
            raise self._error(ProviderError("invalid_provider_response")) from None
        except ProviderError as error:
            raise self._error(error) from None

    def _messages(self, messages: list[dict[str, JsonValue]]) -> list[JsonValue]:
        """Preserve complete Mail bodies and native IDs with the shared event authority."""

        projected: list[JsonValue] = []
        for event in messages:
            identifier = event.get("id")
            data = event.get("data")
            if not isinstance(identifier, str) or not isinstance(data, dict):
                raise ValueError("Malformed Mail event")
            _identifier(identifier)
            if event.get("kind") != "chat.message" or data.get("message_mode") != "mail":
                raise ValueError("Non-Mail event returned")
            projected.append(self._plugin()._decorate_event(event))
        return projected

    async def send(self, body: MailSendRequest) -> dict[str, JsonValue]:
        """Create deferred correspondence with fixed Actor authority and no direct dispatch."""

        plugin = self._plugin()
        plugin._expect_binding(body.expected_binding_id)
        self._require()
        if len({value.lstrip("@") for value in body.to}) != len(body.to) or any(
            re.fullmatch(r"@?[A-Za-z0-9][A-Za-z0-9_-]{0,127}", value) is None
            or value.lstrip("@") == "user"
            for value in body.to
        ):
            raise HTTPException(422, detail={"error_code": "unsupported_recipient"})
        return await self._store(
            "mail.send", body.operation_id, {"to": list(body.to), "text": body.text}
        )

    async def reply(self, body: MailReplyRequest) -> dict[str, JsonValue]:
        """Preserve native reply ancestry while leaving pending consumption unchanged."""

        plugin = self._plugin()
        plugin._expect_binding(body.expected_binding_id)
        self._require()
        event_id = plugin._event_id(body.event_ref)
        return await self._store(
            "mail.reply", body.operation_id, {"event_id": event_id, "text": body.text}
        )

    async def _store(
        self, operation: str, operation_id: str, arguments: dict[str, JsonValue]
    ) -> dict[str, JsonValue]:
        """Make one native deferred mutation and expose ambiguous storage honestly."""

        try:
            result = await self._plugin()._call(
                operation, {"operation_id": operation_id, **arguments}, mutation=True
            )
            event = result.get("event")
            data = event.get("data") if isinstance(event, dict) else None
            if (
                result.get("consumed") is not False
                or not isinstance(data, dict)
                or data.get("message_mode") != "mail"
            ):
                raise ProviderError("invalid_provider_response", outcome="unknown")
            identifier = event.get("id") if isinstance(event, dict) else None
            if not isinstance(identifier, str):
                raise ValueError("Missing native Mail event identity")
            _identifier(identifier)
            projected = self._plugin()._stored_result(result, operation_id)
            projected.update(self._identity())
            return projected
        except (ValueError, ReferenceError):
            raise self._error(
                ProviderError("invalid_provider_response", outcome="unknown"), operation_id
            ) from None
        except ProviderError as error:
            raise self._error(error, operation_id) from None

    async def read(self, body: MailReadRequest) -> dict[str, JsonValue]:
        """Make one consuming call whose provider reserves the complete returned envelope."""

        plugin = self._plugin()
        plugin._expect_binding(body.expected_binding_id)
        expected_cursor = self._decode("mail-cursor", body.expected_cursor)
        count, budget = self._budgets(body.limit, body.max_bytes)
        fixed, per_event = self._reserves(body.operation_id)
        try:
            result = await plugin._call(
                "mail.read",
                {
                    "operation_id": body.operation_id,
                    "expected_cursor": expected_cursor,
                    "limit": count,
                    "max_bytes": budget,
                    "response_overhead_bytes": fixed,
                    "per_event_overhead_bytes": per_event,
                },
                mutation=True,
            )
            batch = MailBatch.model_validate(result)
            if batch.receipt is None or batch.outcome is None or len(batch.messages) > count:
                raise ValueError("Missing read decision")
            if batch.receipt.before_cursor != expected_cursor:
                raise ValueError("Receipt does not describe the requested precondition")
            messages = self._messages(batch.messages)
            ids = [cast(dict[str, JsonValue], event)["event_id"] for event in messages]
            if batch.outcome == "already_completed":
                if messages:
                    raise ValueError("Repeated read returned another batch")
            elif batch.receipt.event_ids != ids or batch.outcome != batch.receipt.outcome:
                raise ValueError("Receipt does not describe the returned batch")
            elif batch.cursor.event_id != batch.receipt.after_cursor:
                raise ValueError("Returned cursor differs from the committed boundary")
            receipt = self._receipt_result(batch.receipt, body.operation_id)
            response: dict[str, JsonValue] = {
                **self._identity(),
                **self._cursor_result(batch.cursor),
                "operation_id": body.operation_id,
                "read_ref": self._ref("mail-read", body.operation_id),
                "outcome": batch.outcome,
                "consumed": batch.outcome == "consumed",
                "messages": messages,
                "receipt": receipt,
                "has_more": batch.has_more,
            }
            if _size(response) > budget:
                raise ValueError("Provider violated its precommit response budget")
            # Consumption can race a later arrival, so this is bounded metadata only.
            if batch.outcome != "already_completed":
                self._observe(1 if batch.has_more else 0, batch.has_more)
            return response
        except (ValidationError, ValueError, ReferenceError):
            raise self._error(
                ProviderError("invalid_provider_response", outcome="unknown"),
                body.operation_id,
                read_operation=True,
            ) from None
        except ProviderError as error:
            raise self._error(error, body.operation_id, read_operation=True) from None

    async def receipt(
        self,
        request: Request,
        operation_id: str,
        read_ref: str | None = Query(default=None, max_length=16384),
    ) -> dict[str, JsonValue]:
        """Resolve only this Actor's operation without consuming a following batch."""

        plugin = self._plugin()
        plugin._queries(request, {"read_ref"})
        if re.fullmatch(_OPERATION, operation_id) is None or operation_id in {".", ".."}:
            raise HTTPException(422, detail={"error_code": "invalid_operation_id"})
        if read_ref is not None and self._decode("mail-read", read_ref) != operation_id:
            raise HTTPException(422, detail={"error_code": "reference_scope_error"})
        self._require()
        try:
            result = await plugin._call("mail.read-receipts", {"operation_id": operation_id})
            if type(result.get("found")) is not bool:
                raise ValueError("Missing receipt lookup outcome")
            response: dict[str, JsonValue] = {
                **self._identity(),
                "operation_id": operation_id,
                "read_ref": self._ref("mail-read", operation_id),
                "found": result["found"],
                "consumed": False,
                "outcome": "unknown",
            }
            if result["found"] is True:
                receipt = MailReadReceipt.model_validate(result.get("receipt"))
                response["receipt"] = self._receipt_result(receipt, operation_id)
                response["outcome"] = receipt.outcome
            return response
        except (ValidationError, ValueError, ReferenceError):
            raise self._error(
                ProviderError("invalid_provider_response"), operation_id, read_operation=True
            ) from None
        except ProviderError as error:
            raise self._error(error, operation_id, read_operation=True) from None

    async def unsupported(self, operation: str) -> dict[str, JsonValue]:
        """Refuse email lifecycle emulation with an explicit machine-readable result."""

        raise HTTPException(
            501,
            detail={
                **self._identity(),
                "error_code": "unsupported_operation",
                "operation": operation
                if operation
                in {"archive", "move", "mark", "attachments", "submission", "mark-unread"}
                else "unsupported",
                "retryable": False,
                "consumed": False,
            },
        )
