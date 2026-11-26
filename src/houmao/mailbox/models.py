"""Shared typed mail operation contracts, independent of HTTP handlers."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator
from houmao.agents.mailbox_runtime_models import MailboxTransport
from houmao.mailbox.protocol import (
    HOUMAO_NO_REPLY_POLICY_VALUE,
    HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
    MailboxNotifyAuth,
    MailboxNotifyBlock,
)

MailChannel = Literal["offline", "online"]
GatewayMailPostReplyPolicy = Literal["none", "operator_mailbox"]
GatewayMailReadFilter = Literal["any", "read", "unread"]
GatewayMailAnsweredFilter = Literal["any", "answered", "unanswered"]
GatewayMailLifecycleOperation = Literal["mark", "move", "archive"]
GATEWAY_MAIL_SCHEMA_VERSION = 3


class _StrictGatewayModel(BaseModel):
    """Reject unknown fields and implicit boundary coercion."""

    model_config = ConfigDict(extra="forbid", strict=True)


class GatewayMailboxParticipantV1(_StrictGatewayModel):
    """Normalized mailbox participant identity."""

    address: str
    display_name: str | None = None
    principal_id: str | None = None

    @field_validator("address", "display_name", "principal_id")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayMailboxAttachmentV1(_StrictGatewayModel):
    """Normalized delivered attachment metadata."""

    attachment_id: str
    kind: str
    media_type: str
    locator: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    label: str | None = None

    @field_validator("attachment_id", "kind", "media_type", "locator", "sha256", "label")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("size_bytes")
    @classmethod
    def _non_negative_size(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("must be >= 0")
        return value


class MailMutationReceipt(_StrictGatewayModel):
    """Provider acknowledgement and immutable account binding for reconciliation."""

    operation: str
    outcome: Literal["confirmed", "uncertain", "rejected"]
    email_id: str | None = None
    submission_id: str | None = None
    agent_id: str | None = None
    binding_id: str | None = None
    revision: str | None = None


class GatewayMailboxMessageV1(_StrictGatewayModel):
    """Normalized mailbox message metadata shared across mailbox routes."""

    message_ref: str
    thread_ref: str | None = None
    created_at_utc: str
    subject: str
    read: bool | None = None
    answered: bool | None = None
    archived: bool | None = None
    box: str | None = None
    unread: bool | None = None
    body_preview: str | None = None
    body_text: str | None = None
    has_attachments: bool = False
    content_complete: bool | None = None
    content_limit_bytes: int | None = None
    content_limit_reason: str | None = None
    mutation_receipt: MailMutationReceipt | None = None
    sender: GatewayMailboxParticipantV1
    to: list[GatewayMailboxParticipantV1]
    cc: list[GatewayMailboxParticipantV1] = Field(default_factory=list)
    reply_to: list[GatewayMailboxParticipantV1] = Field(default_factory=list)
    attachments: list[GatewayMailboxAttachmentV1] = Field(default_factory=list)
    notify_block: MailboxNotifyBlock | None = None
    notify_auth: MailboxNotifyAuth | None = None

    @field_validator("message_ref", "thread_ref", "created_at_utc", "subject", "box")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("body_preview", "body_text")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if "\x00" in value:
            raise ValueError("must not contain NUL bytes")
        return value


class MailboxBackendStatusV1(_StrictGatewayModel):
    """`GET /v1/mail/status` response body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    transport: MailboxTransport
    principal_id: str
    address: str
    bindings_version: str
    placement_writable: bool = True

    def supported_operations(self) -> list[str]:
        """Describe lifecycle operations supported by this backend binding."""

        operations = ["list", "peek", "read", "send", "reply", "mark"]
        if self.placement_writable:
            operations.extend(("move", "archive"))
        if self.transport == "filesystem":
            operations.append("post")
        return operations

    @field_validator("principal_id", "address", "bindings_version")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "MailboxBackendStatusV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailListRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/list` request body."""

    expected_binding_id: str = Field(min_length=1)
    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    box: str = "inbox"
    read_state: GatewayMailReadFilter = "any"
    answered_state: GatewayMailAnsweredFilter = "any"
    archived: bool | None = None
    limit: int = Field(default=50, ge=1, le=200)
    since: str | None = None
    cursor: str | None = Field(default=None, min_length=1, max_length=16384)

    @model_validator(mode="before")
    @classmethod
    def _reject_body_listing(cls, value: object) -> object:
        """Direct removed list-body inputs to explicit content operations."""

        if isinstance(value, dict) and "include_body" in value:
            raise ValueError("include_body was removed; use peek/read for selected content")
        return value

    @field_validator("box", "since")
    @classmethod
    def _optional_not_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailListRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailListResponseV1(_StrictGatewayModel):
    """`POST /v1/mail/list` response body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    transport: MailboxTransport
    principal_id: str
    address: str
    box: str
    message_count: int
    open_count: int
    unread_count: int
    messages: list[GatewayMailboxMessageV1] = Field(max_length=200)
    counts_scope: Literal["page"] = "page"
    next_cursor: str | None
    has_more: bool
    complete: bool
    total_count: int | None = Field(default=None, ge=0)

    @field_validator("principal_id", "address", "box")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @field_validator("message_count", "open_count", "unread_count")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @model_validator(mode="after")
    def _validate_response(self) -> "GatewayMailListResponseV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        if self.unread_count > self.message_count:
            raise ValueError("unread_count must be <= message_count")
        if self.open_count > self.message_count:
            raise ValueError("open_count must be <= message_count")
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("has_more requires exactly one continuation")
        if self.complete == self.has_more:
            raise ValueError("complete describes whether this page exhausts the query")
        if self.message_count != len(self.messages):
            raise ValueError("message_count must describe the returned page")
        if any(message.body_text is not None for message in self.messages):
            raise ValueError("metadata pages cannot contain message bodies; use peek/read")
        return self


class GatewayMailMessageRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/peek|read` request body."""

    expected_binding_id: str = Field(min_length=1)
    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    message_ref: str
    box: str | None = None

    @field_validator("message_ref", "box")
    @classmethod
    def _optional_not_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailMessageRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailMessageResponseV1(_StrictGatewayModel):
    """`POST /v1/mail/peek|read` response body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    operation: Literal["peek", "read"]
    transport: MailboxTransport
    principal_id: str
    address: str
    message: GatewayMailboxMessageV1

    @field_validator("principal_id", "address")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailMessageResponseV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailMarkRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/mark` request body."""

    expected_binding_id: str = Field(min_length=1)
    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    message_refs: list[str]
    read: bool | None = None
    answered: bool | None = None
    archived: bool | None = None

    @field_validator("message_refs")
    @classmethod
    def _message_refs_not_blank(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if len(normalized) != len(value):
            raise ValueError("must contain only non-empty strings")
        if not normalized:
            raise ValueError("must include at least one message reference")
        if len(set(normalized)) != len(normalized):
            raise ValueError("must not contain duplicate message references")
        return normalized

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailMarkRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        if self.read is self.answered is self.archived is None:
            raise ValueError("mark request must set at least one state field")
        return self


class GatewayMailMoveRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/move` request body."""

    expected_binding_id: str = Field(min_length=1)
    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    message_refs: list[str]
    destination_box: str

    @field_validator("message_refs")
    @classmethod
    def _message_refs_not_blank(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if len(normalized) != len(value):
            raise ValueError("must contain only non-empty strings")
        if not normalized:
            raise ValueError("must include at least one message reference")
        if len(set(normalized)) != len(normalized):
            raise ValueError("must not contain duplicate message references")
        return normalized

    @field_validator("destination_box")
    @classmethod
    def _destination_box_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailMoveRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailArchiveRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/archive` request body."""

    expected_binding_id: str = Field(min_length=1)
    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    message_refs: list[str]

    @field_validator("message_refs")
    @classmethod
    def _message_refs_not_blank(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if len(normalized) != len(value):
            raise ValueError("must contain only non-empty strings")
        if not normalized:
            raise ValueError("must include at least one message reference")
        if len(set(normalized)) != len(normalized):
            raise ValueError("must not contain duplicate message references")
        return normalized

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailArchiveRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailAttachmentUploadV1(_StrictGatewayModel):
    """Local attachment input accepted by shared mailbox send/reply routes."""

    path: str
    label: str | None = None

    @field_validator("path", "label")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayMailSendRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/send` request body."""

    expected_binding_id: str = Field(min_length=1)
    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    to: list[str]
    cc: list[str] = Field(default_factory=list)
    subject: str
    body_content: str
    attachments: list[GatewayMailAttachmentUploadV1] = Field(default_factory=list)
    notify_block: MailboxNotifyBlock | None = None
    notify_auth: MailboxNotifyAuth | None = None

    @field_validator("to", "cc")
    @classmethod
    def _validate_recipients(cls, value: list[str], info: ValidationInfo) -> list[str]:
        normalized = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if info.field_name == "to" and not normalized:
            raise ValueError("must include at least one recipient")
        if len(normalized) != len(value):
            raise ValueError("must contain only non-empty strings")
        return normalized

    @field_validator("subject")
    @classmethod
    def _subject_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("body_content")
    @classmethod
    def _body_no_nul(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("must not contain NUL bytes")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailSendRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailPostRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/post` request body."""

    expected_binding_id: str = Field(min_length=1)
    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    subject: str
    body_content: str
    reply_policy: GatewayMailPostReplyPolicy = Field(
        default=HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE
    )
    attachments: list[GatewayMailAttachmentUploadV1] = Field(default_factory=list)
    notify_block: MailboxNotifyBlock | None = None
    notify_auth: MailboxNotifyAuth | None = None

    @field_validator("subject")
    @classmethod
    def _subject_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("body_content")
    @classmethod
    def _body_no_nul(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("must not contain NUL bytes")
        return value

    @field_validator("reply_policy")
    @classmethod
    def _reply_policy_known(cls, value: GatewayMailPostReplyPolicy) -> GatewayMailPostReplyPolicy:
        if value not in {
            HOUMAO_NO_REPLY_POLICY_VALUE,
            HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
        }:
            raise ValueError("unsupported reply policy")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailPostRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailReplyRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/reply` request body."""

    expected_binding_id: str = Field(min_length=1)
    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    message_ref: str
    body_content: str
    attachments: list[GatewayMailAttachmentUploadV1] = Field(default_factory=list)
    notify_block: MailboxNotifyBlock | None = None
    notify_auth: MailboxNotifyAuth | None = None

    @field_validator("message_ref")
    @classmethod
    def _message_ref_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("body_content")
    @classmethod
    def _body_no_nul(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("must not contain NUL bytes")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailReplyRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailActionResponseV1(_StrictGatewayModel):
    """`POST /v1/mail/send|post|reply` response body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    operation: Literal["send", "post", "reply"]
    transport: MailboxTransport
    principal_id: str
    address: str
    message: GatewayMailboxMessageV1
    transport_evidence: Literal["offline_deposit", "provider_submission"] | None = None

    @field_validator("principal_id", "address")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailActionResponseV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        expected: Literal["offline_deposit", "provider_submission"] = (
            "provider_submission" if self.transport == "stalwart" else "offline_deposit"
        )
        if self.transport_evidence is None:
            self.transport_evidence = expected
        elif self.transport_evidence != expected:
            raise ValueError("transport_evidence must match the selected transport")
        return self


class GatewayMailLifecycleResponseV1(_StrictGatewayModel):
    """`POST /v1/mail/mark|move|archive` response body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    operation: GatewayMailLifecycleOperation
    transport: MailboxTransport
    principal_id: str
    address: str
    message_count: int
    messages: list[GatewayMailboxMessageV1]

    @field_validator("principal_id", "address")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @field_validator("message_count")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailLifecycleResponseV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        if self.message_count != len(self.messages):
            raise ValueError("message_count must match messages length")
        return self


class MailboxChannelStatusV1(_StrictGatewayModel):
    """Secret-free configured binding and independent availability."""

    agent_id: str
    channel: MailChannel
    binding_id: str
    revision: str
    address: str
    transport: MailboxTransport
    available: bool
    error: str | None = None
    supported_operations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class GatewayMailStatusV1(_StrictGatewayModel):
    """Summary of both slots from one manifest snapshot."""

    schema_version: int = GATEWAY_MAIL_SCHEMA_VERSION
    agent_id: str
    offline: MailboxChannelStatusV1 | None = None
    online: MailboxChannelStatusV1 | None = None
    canonical_mail_identity: dict[str, str] | None = None


class GatewayMailSyncViewV1(_StrictGatewayModel):
    """Secret-free progress of one durable bounded observation view."""

    phase: Literal["idle", "catching_up", "rebasing", "degraded", "unsupported"]
    complete: bool
    has_more: bool
    incremental_supported: bool | None
    last_success_utc: str | None
    error_code: str | None
    retry_after_utc: float | None
    view_fingerprint: str
    cached_count: int = Field(ge=0, le=200)


class GatewayMailSyncStatusV1(_StrictGatewayModel):
    """Safe persisted sync overview without credentials or cached message bodies."""

    phase: Literal["idle", "catching_up", "rebasing", "degraded", "unsupported"]
    available: bool
    views: list[GatewayMailSyncViewV1] = Field(default_factory=list, max_length=16)
