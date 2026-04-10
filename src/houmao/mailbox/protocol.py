"""Canonical mailbox protocol models and serialization helpers.

This module defines the transport-neutral mailbox envelope used by the
filesystem mailbox transport. It also provides helpers for canonical
message-id generation plus YAML-front-matter serialization for Markdown
message documents.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import re
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import yaml

from houmao.mailbox.errors import MailboxProtocolError

MAILBOX_PROTOCOL_VERSION = 1
HOUMAO_MAILBOX_DOMAIN = "houmao.localhost"
HOUMAO_RESERVED_LOCAL_PART_PREFIX = "HOUMAO-"
HOUMAO_OPERATOR_PRINCIPAL_ID = "HOUMAO-operator"
HOUMAO_OPERATOR_ADDRESS = f"{HOUMAO_OPERATOR_PRINCIPAL_ID}@{HOUMAO_MAILBOX_DOMAIN}"
HOUMAO_OPERATOR_ROLE = "system_operator"
HOUMAO_OPERATOR_DISPLAY_NAME = "Houmao Operator"
HOUMAO_ORIGIN_HEADER_NAME = "x-houmao-origin"
HOUMAO_REPLY_POLICY_HEADER_NAME = "x-houmao-reply-policy"
HOUMAO_OPERATOR_ORIGIN_VALUE = "operator"
HOUMAO_NO_REPLY_POLICY_VALUE = "none"
HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE = "operator_mailbox"
OperatorOriginReplyPolicy = Literal["none", "operator_mailbox"]
MESSAGE_ID_PATTERN = re.compile(r"^msg-\d{8}T\d{6}Z-[0-9a-f]{32}$")
_RFC3339_UTC_SUFFIX = "Z"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAILBOX_ADDRESS_RE = re.compile(
    r"^(?P<local>[A-Za-z0-9][A-Za-z0-9._+-]*)@"
    r"(?P<domain>[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)$"
)
_FORBIDDEN_PATH_SEGMENT_CHARS = frozenset('/\\\x00:*?"<>|')


class _StrictMailboxModel(BaseModel):
    """Base model for strict mailbox protocol parsing."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, strict=True)


class MailboxPrincipal(_StrictMailboxModel):
    """Mailbox principal metadata."""

    principal_id: str
    address: str
    display_name: str | None = None
    manifest_path_hint: str | None = None
    role: str | None = None

    @field_validator("principal_id", "address")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("display_name", "manifest_path_hint", "role")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("address")
    @classmethod
    def _validate_address(cls, value: str) -> str:
        return validate_mailbox_address(value)


class MailboxAttachment(_StrictMailboxModel):
    """Structured attachment metadata."""

    attachment_id: str
    kind: Literal["path_ref", "managed_copy"]
    path: str
    media_type: str
    sha256: str | None = None
    size_bytes: int | None = None
    label: str | None = None

    @field_validator("attachment_id", "path", "media_type")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not _SHA256_PATTERN.fullmatch(normalized):
            raise ValueError("must be a 64-character lowercase hex SHA-256 digest")
        return normalized

    @field_validator("size_bytes")
    @classmethod
    def _validate_size_bytes(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("must be greater than or equal to zero")
        return value

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_kind_specific_path(self) -> "MailboxAttachment":
        if self.kind == "path_ref" and not self.path.startswith("/"):
            raise MailboxProtocolError("path_ref attachments must use an absolute path")
        return self


class MailboxMessage(_StrictMailboxModel):
    """Canonical mailbox message envelope plus Markdown body."""

    protocol_version: int = MAILBOX_PROTOCOL_VERSION
    message_id: str
    thread_id: str
    in_reply_to: str | None = None
    references: list[str] = Field(default_factory=list)
    created_at_utc: str
    sender: MailboxPrincipal = Field(alias="from")
    to: list[MailboxPrincipal]
    cc: list[MailboxPrincipal] = Field(default_factory=list)
    reply_to: list[MailboxPrincipal] = Field(default_factory=list)
    subject: str
    body_markdown: str
    attachments: list[MailboxAttachment] = Field(default_factory=list)
    headers: dict[str, object] = Field(default_factory=dict)

    @field_validator("protocol_version")
    @classmethod
    def _validate_protocol_version(cls, value: int) -> int:
        if value != MAILBOX_PROTOCOL_VERSION:
            raise ValueError(f"must be {MAILBOX_PROTOCOL_VERSION}")
        return value

    @field_validator("message_id", "thread_id", "in_reply_to")
    @classmethod
    def _validate_optional_message_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_message_id(value)

    @field_validator("references")
    @classmethod
    def _validate_references(cls, value: list[str]) -> list[str]:
        return [validate_message_id(item) for item in value]

    @field_validator("created_at_utc")
    @classmethod
    def _validate_created_at_utc(cls, value: str) -> str:
        return normalize_utc_timestamp(value)

    @field_validator("subject")
    @classmethod
    def _validate_subject(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("body_markdown")
    @classmethod
    def _validate_body_markdown(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("must not contain NUL bytes")
        return value

    @field_validator("to")
    @classmethod
    def _validate_to(cls, value: list[MailboxPrincipal]) -> list[MailboxPrincipal]:
        if not value:
            raise ValueError("must include at least one recipient")
        return value

    @field_validator("headers")
    @classmethod
    def _validate_headers(cls, value: dict[str, object]) -> dict[str, object]:
        for key in value:
            if not key.strip():
                raise ValueError("header keys must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_threading(self) -> "MailboxMessage":
        if self.in_reply_to is None:
            if self.thread_id != self.message_id:
                raise MailboxProtocolError("root messages must use message_id as thread_id")
            if self.references:
                raise MailboxProtocolError("root messages must not include references")
            return self

        if not self.references:
            raise MailboxProtocolError("reply messages must include references")
        if self.references[-1] != self.in_reply_to:
            raise MailboxProtocolError("references must end with in_reply_to")
        return self


def generate_message_id(now: datetime | None = None) -> str:
    """Return a canonical mailbox message id.

    Parameters
    ----------
    now:
        Optional UTC timestamp override used for deterministic tests.

    Returns
    -------
    str
        Message identifier formatted as
        ``msg-{YYYYMMDDTHHMMSSZ}-{uuid4-no-dashes}``.
    """

    timestamp = normalize_utc_datetime(now or datetime.now(UTC))
    return f"msg-{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex}"


def validate_mailbox_address(value: str) -> str:
    """Validate and normalize one mailbox address string."""

    match, normalized = _parse_mailbox_address_match(value)
    local_part = match.group("local")
    domain_part = match.group("domain")
    if ".." in local_part or ".." in domain_part:
        raise MailboxProtocolError("mailbox addresses must not contain empty dot segments")
    if domain_part.startswith("-") or domain_part.endswith("-"):
        raise MailboxProtocolError("mailbox address domains must not start or end with `-`")
    return normalized


def mailbox_address_local_part(value: str) -> str:
    """Return the normalized local part for one mailbox address."""

    match, _ = _parse_mailbox_address_match(value)
    return match.group("local")


def mailbox_address_domain_part(value: str) -> str:
    """Return the normalized domain part for one mailbox address."""

    match, _ = _parse_mailbox_address_match(value)
    return match.group("domain")


def is_houmao_reserved_mailbox_local_part(value: str) -> bool:
    """Return whether one mailbox local part is reserved for Houmao system use."""

    return value.strip().startswith(HOUMAO_RESERVED_LOCAL_PART_PREFIX)


def is_houmao_reserved_mailbox_address(value: str) -> bool:
    """Return whether one full mailbox address uses the reserved Houmao namespace."""

    return is_houmao_reserved_mailbox_local_part(mailbox_address_local_part(value))


def is_operator_origin_headers(headers: Mapping[str, object]) -> bool:
    """Return whether mailbox headers indicate one operator-origin message."""

    origin = headers.get(HOUMAO_ORIGIN_HEADER_NAME)
    if not isinstance(origin, str):
        return False
    return origin.strip().lower() == HOUMAO_OPERATOR_ORIGIN_VALUE


def operator_origin_reply_policy(headers: Mapping[str, object]) -> OperatorOriginReplyPolicy:
    """Return the normalized operator-origin reply policy for one message."""

    value = headers.get(HOUMAO_REPLY_POLICY_HEADER_NAME)
    if not isinstance(value, str):
        return HOUMAO_NO_REPLY_POLICY_VALUE
    normalized = value.strip().lower()
    if normalized == HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE:
        return HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE
    return HOUMAO_NO_REPLY_POLICY_VALUE


def operator_origin_headers(
    *,
    reply_policy: OperatorOriginReplyPolicy = HOUMAO_NO_REPLY_POLICY_VALUE,
) -> dict[str, str]:
    """Return canonical provenance headers for operator-origin mailbox delivery."""

    if reply_policy not in {
        HOUMAO_NO_REPLY_POLICY_VALUE,
        HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
    }:
        raise ValueError(f"unsupported operator-origin reply policy: {reply_policy!r}")
    return {
        HOUMAO_ORIGIN_HEADER_NAME: HOUMAO_OPERATOR_ORIGIN_VALUE,
        HOUMAO_REPLY_POLICY_HEADER_NAME: reply_policy,
    }


def _parse_mailbox_address_match(value: str) -> tuple[re.Match[str], str]:
    """Return the normalized address and parsed local/domain match."""

    normalized = value.strip()
    if not normalized:
        raise MailboxProtocolError("mailbox addresses must not be empty")
    if any(character.isspace() for character in normalized):
        raise MailboxProtocolError("mailbox addresses must not contain whitespace")

    match = _MAILBOX_ADDRESS_RE.fullmatch(normalized)
    if match is None:
        raise MailboxProtocolError(
            "mailbox addresses must be full-form email-like values such as "
            "`research@houmao.localhost`"
        )
    return match, normalized


def mailbox_address_path_segment(address: str) -> str:
    """Validate a mailbox address for literal filesystem-segment usage."""

    normalized = validate_mailbox_address(address)
    if normalized in {".", ".."}:
        raise MailboxProtocolError("mailbox addresses must not be `.` or `..`")
    if any(character in _FORBIDDEN_PATH_SEGMENT_CHARS for character in normalized):
        raise MailboxProtocolError(
            "mailbox addresses must be safe literal filesystem path segments"
        )
    if any(ord(character) < 32 for character in normalized):
        raise MailboxProtocolError("mailbox addresses must not contain control characters")
    return normalized


def validate_message_id(value: str) -> str:
    """Validate and normalize a canonical mailbox message id.

    Parameters
    ----------
    value:
        Candidate mailbox message identifier.

    Returns
    -------
    str
        The normalized message identifier.

    Raises
    ------
    MailboxProtocolError
        Raised when the value does not match the canonical mailbox format.
    """

    normalized = value.strip()
    if not MESSAGE_ID_PATTERN.fullmatch(normalized):
        raise MailboxProtocolError("message_id must match msg-{YYYYMMDDTHHMMSSZ}-{uuid4-no-dashes}")
    suffix = normalized.rsplit("-", 1)[-1]
    UUID(hex=suffix)
    return normalized


def normalize_utc_timestamp(value: str) -> str:
    """Return a canonical UTC RFC3339 timestamp string."""

    candidate = value.strip()
    if not candidate.endswith(_RFC3339_UTC_SUFFIX):
        raise MailboxProtocolError("created_at_utc must be an RFC3339 UTC timestamp ending in Z")

    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MailboxProtocolError("created_at_utc must be a valid RFC3339 UTC timestamp") from exc

    return normalize_utc_datetime(parsed).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_utc_datetime(value: datetime) -> datetime:
    """Normalize a datetime to UTC without sub-second precision."""

    if value.tzinfo is None:
        raise MailboxProtocolError("datetime values must be timezone-aware")
    return value.astimezone(UTC).replace(microsecond=0)


def serialize_message_document(message: MailboxMessage) -> str:
    """Serialize a canonical mailbox message to Markdown with YAML front matter.

    Parameters
    ----------
    message:
        Canonical mailbox message to serialize.

    Returns
    -------
    str
        Markdown document containing YAML front matter plus the body.
    """

    payload = message.model_dump(
        by_alias=True,
        exclude={"body_markdown"},
        mode="python",
    )
    front_matter = yaml.safe_dump(payload, sort_keys=False)
    body = message.body_markdown
    if body:
        return f"---\n{front_matter}---\n\n{body}"
    return f"---\n{front_matter}---\n"


def parse_message_document(document: str) -> MailboxMessage:
    """Parse a Markdown mailbox document into a canonical message model.

    Parameters
    ----------
    document:
        Markdown document containing YAML front matter.

    Returns
    -------
    MailboxMessage
        Parsed canonical mailbox message.
    """

    if not document.startswith("---\n"):
        raise MailboxProtocolError("mailbox documents must start with YAML front matter")

    delimiter = "\n---\n"
    remainder = document[4:]
    if delimiter not in remainder:
        raise MailboxProtocolError("mailbox documents must terminate YAML front matter with ---")

    front_matter_text, body = remainder.split(delimiter, maxsplit=1)
    if body.startswith("\n"):
        body = body[1:]

    payload = yaml.safe_load(front_matter_text)
    if not isinstance(payload, dict):
        raise MailboxProtocolError("mailbox front matter must parse to a mapping")

    payload["body_markdown"] = body
    try:
        return MailboxMessage.model_validate(payload)
    except Exception as exc:  # pragma: no cover - pydantic type is not RuntimeError-specific.
        if isinstance(exc, MailboxProtocolError):
            raise
        raise MailboxProtocolError(f"invalid mailbox message document: {exc}") from exc
