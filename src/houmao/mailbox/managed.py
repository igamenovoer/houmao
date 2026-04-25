"""Helpers for managed mailbox scripts and lifecycle operations."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import time
from typing import (
    Callable,
    ClassVar,
    Iterator,
    Literal,
    Sequence,
    TextIO,
    TypedDict,
    TypeVar,
)
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from houmao.mailbox.filesystem import (
    FilesystemMailboxPaths,
    MailboxRegistration,
    initialize_mailbox_local_sqlite_schema,
    initialize_sqlite_schema,
    resolve_filesystem_mailbox_paths,
    unsupported_mailbox_root_reason,
)
from houmao.mailbox.protocol import (
    HOUMAO_MAILBOX_DOMAIN,
    HOUMAO_OPERATOR_ADDRESS,
    HOUMAO_OPERATOR_DISPLAY_NAME,
    HOUMAO_OPERATOR_PRINCIPAL_ID,
    HOUMAO_OPERATOR_ROLE,
    MAILBOX_PROTOCOL_VERSION,
    MailboxAttachment,
    MailboxMessage,
    MailboxPrincipal,
    is_houmao_reserved_mailbox_local_part,
    mailbox_address_domain_part,
    mailbox_address_local_part,
    mailbox_address_path_segment,
    normalize_utc_timestamp,
    parse_message_document,
    validate_message_id,
)

_MAILBOX_PLACEHOLDER_DIRS = ("inbox", "sent", "archive", "drafts")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_STASHED_ENTRY_RE = re.compile(r"^(?P<address>.+)--(?P<suffix>[0-9a-f]{32})$")

_ManagedRequestT = TypeVar("_ManagedRequestT", bound="_ManagedRequestModel")


class _LocalMessageStateRow(TypedDict):
    """Typed mailbox-local state row materialized from SQLite projections."""

    message_id: str
    thread_id: str
    created_at_utc: str
    subject: str
    is_read: bool
    is_answered: bool
    is_starred: bool
    is_archived: bool
    is_deleted: bool
    box_name: str


class ManagedMailboxOperationError(RuntimeError):
    """Raised when a managed mailbox script cannot complete safely."""


class _ManagedMailboxModel(BaseModel):
    """Base model for strict managed mailbox payload parsing."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class _ManagedRequestModel(_ManagedMailboxModel):
    """Base class for managed mailbox helper request models."""

    PAYLOAD_NAME: ClassVar[str] = "payload"

    @classmethod
    def from_payload(
        cls: type[_ManagedRequestT],
        payload: object,
    ) -> _ManagedRequestT:
        """Validate one request payload and convert validation errors."""

        return _parse_managed_request(cls, payload)


class ManagedPrincipal(_ManagedMailboxModel):
    """Principal metadata used by managed mailbox scripts."""

    principal_id: str
    address: str
    display_name: str | None = None
    manifest_path_hint: str | None = None
    role: str | None = None

    @field_validator("principal_id")
    @classmethod
    def _validate_principal_id(cls, value: str) -> str:
        """Normalize required principal identifiers."""

        return _normalize_non_blank_string(value)

    @field_validator("address")
    @classmethod
    def _validate_address(cls, value: str) -> str:
        """Validate literal mailbox path-segment addresses."""

        return _validate_managed_address(value)

    @field_validator("display_name", "manifest_path_hint", "role")
    @classmethod
    def _validate_optional_text(cls, value: str | None) -> str | None:
        """Normalize optional non-blank string metadata."""

        return _normalize_optional_non_blank_string(value)

    def to_mailbox_principal(self) -> MailboxPrincipal:
        """Return the canonical mailbox principal model."""

        return MailboxPrincipal(
            principal_id=self.principal_id,
            address=self.address,
            display_name=self.display_name,
            manifest_path_hint=self.manifest_path_hint,
            role=self.role,
        )


class ManagedAttachment(_ManagedMailboxModel):
    """Structured attachment metadata used by managed mailbox delivery."""

    attachment_id: str
    kind: Literal["path_ref", "managed_copy"]
    path: str
    media_type: str
    sha256: str | None = None
    size_bytes: int | None = None
    label: str | None = None

    @field_validator("attachment_id", "path", "media_type")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        """Normalize required attachment string fields."""

        return _normalize_non_blank_string(value)

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, value: str | None) -> str | None:
        """Validate optional SHA-256 digests."""

        if value is None:
            return None
        normalized = _normalize_non_blank_string(value).lower()
        if not _SHA256_PATTERN.fullmatch(normalized):
            raise ValueError("must be a 64-character lowercase hex SHA-256 digest")
        return normalized

    @field_validator("size_bytes")
    @classmethod
    def _validate_size_bytes(cls, value: int | None) -> int | None:
        """Ensure attachment sizes are non-negative."""

        if value is None:
            return None
        if value < 0:
            raise ValueError("must be greater than or equal to zero")
        return value

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value: str | None) -> str | None:
        """Normalize optional attachment labels."""

        return _normalize_optional_non_blank_string(value)

    @model_validator(mode="after")
    def _validate_kind_specific_path(self) -> "ManagedAttachment":
        """Apply attachment-kind-specific path rules."""

        if self.kind == "path_ref" and not self.path.startswith("/"):
            raise ValueError("path_ref attachments must use an absolute path")
        return self

    def to_mailbox_attachment(self) -> MailboxAttachment:
        """Return the canonical mailbox attachment model."""

        return MailboxAttachment(
            attachment_id=self.attachment_id,
            kind=self.kind,
            path=self.path,
            media_type=self.media_type,
            sha256=self.sha256,
            size_bytes=self.size_bytes,
            label=self.label,
        )


class DeliveryRequest(_ManagedRequestModel):
    """Structured delivery request for `deliver_message.py`."""

    PAYLOAD_NAME: ClassVar[str] = "delivery payload"

    staged_message_path: Path
    message_id: str
    thread_id: str
    in_reply_to: str | None = None
    references: tuple[str, ...] = Field(default_factory=tuple)
    created_at_utc: str
    sender: ManagedPrincipal
    to: tuple[ManagedPrincipal, ...]
    cc: tuple[ManagedPrincipal, ...] = Field(default_factory=tuple)
    reply_to: tuple[ManagedPrincipal, ...] = Field(default_factory=tuple)
    subject: str
    attachments: tuple[ManagedAttachment, ...] = Field(default_factory=tuple)
    headers: dict[str, object] = Field(default_factory=dict)

    @field_validator("staged_message_path", mode="before")
    @classmethod
    def _coerce_staged_message_path(cls, value: object) -> object:
        """Accept string payload paths and resolve them eagerly."""

        return _coerce_path_value(value)

    @field_validator("message_id", "thread_id")
    @classmethod
    def _validate_message_ids(cls, value: str) -> str:
        """Validate canonical message identifiers."""

        return _validate_managed_message_id(value)

    @field_validator("in_reply_to")
    @classmethod
    def _validate_in_reply_to(cls, value: str | None) -> str | None:
        """Validate optional reply threading identifiers."""

        if value is None:
            return None
        return _validate_managed_message_id(value)

    @field_validator("references", "to", "cc", "reply_to", "attachments", mode="before")
    @classmethod
    def _coerce_sequence_fields(cls, value: object) -> object:
        """Accept JSON arrays for tuple-backed fields."""

        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("references")
    @classmethod
    def _validate_references(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Validate each referenced message identifier."""

        return tuple(_validate_managed_message_id(item) for item in value)

    @field_validator("created_at_utc")
    @classmethod
    def _validate_created_at_utc(cls, value: str) -> str:
        """Normalize managed delivery timestamps."""

        return _normalize_managed_timestamp(value)

    @field_validator("subject")
    @classmethod
    def _validate_subject(cls, value: str) -> str:
        """Normalize required delivery subject text."""

        return _normalize_non_blank_string(value)

    @field_validator("headers")
    @classmethod
    def _validate_headers(cls, value: dict[str, object]) -> dict[str, object]:
        """Reject blank header keys while preserving payload values."""

        normalized_headers: dict[str, object] = {}
        for key, item in value.items():
            normalized_headers[_normalize_non_blank_string(key)] = item
        return normalized_headers

    @model_validator(mode="after")
    def _validate_threading(self) -> "DeliveryRequest":
        """Validate cross-field delivery threading rules."""

        if not self.to:
            raise ValueError("delivery payload must include at least one recipient")
        if self.in_reply_to is None:
            if self.thread_id != self.message_id:
                raise ValueError("root deliveries must use message_id as thread_id")
            if self.references:
                raise ValueError("root deliveries must not include references")
            return self

        if not self.references:
            raise ValueError("reply deliveries must include references")
        if self.references[-1] != self.in_reply_to:
            raise ValueError("references must end with in_reply_to")
        return self


class StateUpdateRequest(_ManagedRequestModel):
    """Structured mailbox-state mutation request."""

    PAYLOAD_NAME: ClassVar[str] = "state update payload"

    address: str
    message_id: str
    read: bool | None = None
    answered: bool | None = None
    starred: bool | None = None
    archived: bool | None = None
    deleted: bool | None = None

    @field_validator("address")
    @classmethod
    def _validate_address(cls, value: str) -> str:
        """Validate managed mailbox addresses."""

        return _validate_managed_address(value)

    @field_validator("message_id")
    @classmethod
    def _validate_message_id(cls, value: str) -> str:
        """Validate canonical message identifiers."""

        return _validate_managed_message_id(value)

    @model_validator(mode="after")
    def _validate_mutation_request(self) -> "StateUpdateRequest":
        """Require at least one mailbox-state flag to be present."""

        if self.read is self.answered is self.starred is self.archived is self.deleted is None:
            raise ValueError("state update payload must set at least one field")
        return self


class RepairRequest(_ManagedRequestModel):
    """Structured mailbox repair or reindex request."""

    PAYLOAD_NAME: ClassVar[str] = "repair payload"

    cleanup_staging: bool = True
    quarantine_staging: bool = True

    @classmethod
    def from_payload(cls, payload: object) -> "RepairRequest":
        """Validate one repair payload, defaulting null to the empty payload."""

        if payload is None:
            return cls()
        return _parse_managed_request(cls, payload)


class MailboxExportRequest(_ManagedRequestModel):
    """Structured filesystem mailbox export request."""

    PAYLOAD_NAME: ClassVar[str] = "mailbox export payload"

    output_dir: Path
    all_accounts: bool = False
    addresses: tuple[str, ...] = Field(default_factory=tuple)
    symlink_mode: Literal["materialize", "preserve"] = "materialize"

    @field_validator("output_dir", mode="before")
    @classmethod
    def _coerce_output_dir(cls, value: object) -> object:
        """Accept string payload paths and resolve them eagerly."""

        return _coerce_path_value(value)

    @field_validator("addresses", mode="before")
    @classmethod
    def _coerce_addresses(cls, value: object) -> object:
        """Accept JSON arrays for tuple-backed address selection."""

        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("addresses")
    @classmethod
    def _validate_addresses(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Validate selected mailbox addresses and reject duplicates."""

        normalized = tuple(_validate_managed_address(item) for item in value)
        if len(set(normalized)) != len(normalized):
            raise ValueError("mailbox export addresses must not contain duplicates")
        return normalized

    @model_validator(mode="after")
    def _validate_selection(self) -> "MailboxExportRequest":
        """Require exactly one account-selection mode."""

        if self.all_accounts and self.addresses:
            raise ValueError("mailbox export accepts either all_accounts or addresses, not both")
        if not self.all_accounts and not self.addresses:
            raise ValueError("mailbox export requires all_accounts or at least one address")
        return self


class RegisterMailboxRequest(_ManagedRequestModel):
    """Structured mailbox registration request."""

    PAYLOAD_NAME: ClassVar[str] = "register payload"

    mode: Literal["safe", "force", "stash"]
    address: str
    owner_principal_id: str
    mailbox_kind: Literal["in_root", "symlink"]
    mailbox_path: Path
    display_name: str | None = None
    manifest_path_hint: str | None = None
    role: str | None = None

    @field_validator("address")
    @classmethod
    def _validate_address(cls, value: str) -> str:
        """Validate managed mailbox addresses."""

        return _validate_managed_address(value)

    @field_validator("owner_principal_id")
    @classmethod
    def _validate_owner_principal_id(cls, value: str) -> str:
        """Normalize required owner identifiers."""

        return _normalize_non_blank_string(value)

    @field_validator("mailbox_path", mode="before")
    @classmethod
    def _coerce_mailbox_path(cls, value: object) -> object:
        """Accept string payload paths and resolve them eagerly."""

        return _coerce_path_value(value)

    @field_validator("display_name", "manifest_path_hint", "role")
    @classmethod
    def _validate_optional_text(cls, value: str | None) -> str | None:
        """Normalize optional registration metadata."""

        return _normalize_optional_non_blank_string(value)

    @model_validator(mode="after")
    def _validate_reserved_address_policy(self) -> "RegisterMailboxRequest":
        """Protect reserved Houmao mailbox locals from ordinary registrations."""

        if (
            mailbox_address_domain_part(self.address) == HOUMAO_MAILBOX_DOMAIN
            and is_houmao_reserved_mailbox_local_part(mailbox_address_local_part(self.address))
            and not (
                self.address == HOUMAO_OPERATOR_ADDRESS
                and self.owner_principal_id == HOUMAO_OPERATOR_PRINCIPAL_ID
                and self.role == HOUMAO_OPERATOR_ROLE
            )
        ):
            raise ValueError(
                "mailbox local parts beginning with `HOUMAO-` under `houmao.localhost` "
                "are reserved for Houmao-owned system principals"
            )
        return self


class DeregisterMailboxRequest(_ManagedRequestModel):
    """Structured mailbox deregistration request."""

    PAYLOAD_NAME: ClassVar[str] = "deregister payload"

    mode: Literal["deactivate", "purge"]
    address: str

    @field_validator("address")
    @classmethod
    def _validate_address(cls, value: str) -> str:
        """Validate managed mailbox addresses."""

        return _validate_managed_address(value)


@dataclass(frozen=True)
class _RecoveredMessageDocument:
    """Canonical mailbox message plus its on-disk document text."""

    canonical_path: Path
    document_text: str
    message: MailboxMessage


@dataclass(frozen=True)
class _DiscoveredMailboxArtifact:
    """Recovered mailbox artifact metadata from `mailboxes/`."""

    address: str
    status: str
    mailbox_kind: str
    mailbox_path: Path
    mailbox_entry_path: Path


@dataclass(frozen=True)
class _IndexSnapshot:
    """Existing mailbox index data preserved across reindex."""

    registrations: dict[str, MailboxRegistration]
    sender_registration_ids: dict[str, str | None]
    recipient_registration_ids: dict[tuple[str, str, int], str | None]
    backup_path: Path | None


@dataclass(frozen=True)
class MailboxCleanupRecord:
    """One mailbox cleanup decision or mutation outcome."""

    outcome: Literal["planned", "removed", "preserved", "blocked"]
    artifact_kind: str
    path: Path
    reason: str
    address: str | None = None
    registration_id: str | None = None
    registration_status: str | None = None
    message_id: str | None = None
    attachment_id: str | None = None

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-compatible cleanup record payload."""

        payload: dict[str, object] = {
            "outcome": self.outcome,
            "artifact_kind": self.artifact_kind,
            "path": str(self.path),
            "reason": self.reason,
        }
        if self.address is not None:
            payload["address"] = self.address
        if self.registration_id is not None:
            payload["registration_id"] = self.registration_id
        if self.registration_status is not None:
            payload["registration_status"] = self.registration_status
        if self.message_id is not None:
            payload["message_id"] = self.message_id
        if self.attachment_id is not None:
            payload["attachment_id"] = self.attachment_id
        return payload


@dataclass(frozen=True)
class MailboxCleanupResult:
    """Structured mailbox cleanup result."""

    mailbox_root: Path
    dry_run: bool
    planned: tuple[MailboxCleanupRecord, ...]
    removed: tuple[MailboxCleanupRecord, ...]
    preserved: tuple[MailboxCleanupRecord, ...]
    blocked: tuple[MailboxCleanupRecord, ...]


@dataclass(frozen=True)
class MailboxMessageClearResult:
    """Structured delivered-message clearing result."""

    mailbox_root: Path
    dry_run: bool
    planned: tuple[MailboxCleanupRecord, ...]
    removed: tuple[MailboxCleanupRecord, ...]
    preserved: tuple[MailboxCleanupRecord, ...]
    blocked: tuple[MailboxCleanupRecord, ...]


@dataclass(frozen=True)
class MailboxExportAction:
    """One mailbox export copy, materialization, skip, or blocked outcome."""

    outcome: Literal["copied", "materialized", "preserved_symlink", "skipped", "blocked"]
    artifact_kind: str
    source_path: Path | None
    archive_path: Path | None
    reason: str
    address: str | None = None
    registration_id: str | None = None
    registration_status: str | None = None
    message_id: str | None = None
    attachment_id: str | None = None
    symlink_target: Path | None = None
    details: dict[str, object] | None = None

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-compatible export action payload."""

        payload: dict[str, object] = {
            "outcome": self.outcome,
            "artifact_kind": self.artifact_kind,
            "reason": self.reason,
        }
        if self.source_path is not None:
            payload["source_path"] = str(self.source_path)
        if self.archive_path is not None:
            payload["archive_path"] = str(self.archive_path)
        if self.address is not None:
            payload["address"] = self.address
        if self.registration_id is not None:
            payload["registration_id"] = self.registration_id
        if self.registration_status is not None:
            payload["registration_status"] = self.registration_status
        if self.message_id is not None:
            payload["message_id"] = self.message_id
        if self.attachment_id is not None:
            payload["attachment_id"] = self.attachment_id
        if self.symlink_target is not None:
            payload["symlink_target"] = str(self.symlink_target)
        if self.details:
            payload["details"] = dict(self.details)
        return payload


@dataclass(frozen=True)
class MailboxExportResult:
    """Structured filesystem mailbox export result."""

    mailbox_root: Path
    output_dir: Path
    manifest_path: Path
    symlink_mode: Literal["materialize", "preserve"]
    all_accounts: bool
    selected_addresses: tuple[str, ...]
    account_count: int
    message_count: int
    attachment_count: int
    copied: tuple[MailboxExportAction, ...]
    materialized: tuple[MailboxExportAction, ...]
    preserved_symlinks: tuple[MailboxExportAction, ...]
    skipped: tuple[MailboxExportAction, ...]
    blocked: tuple[MailboxExportAction, ...]


@dataclass(frozen=True)
class _MailboxExportMessage:
    """Message row selected for one mailbox export snapshot."""

    message_id: str
    thread_id: str
    in_reply_to: str | None
    created_at_utc: str
    canonical_path: Path
    subject: str
    sender_address: str
    sender_principal_id: str
    sender_registration_id: str | None


@dataclass(frozen=True)
class _MailboxExportProjection:
    """Mailbox projection row selected for one mailbox export snapshot."""

    registration_id: str
    message_id: str
    folder_name: str
    projection_path: Path


@dataclass(frozen=True)
class _MailboxExportAttachment:
    """Message attachment row selected for one mailbox export snapshot."""

    message_id: str
    attachment_id: str
    kind: str
    locator: str
    media_type: str
    sha256: str | None
    size_bytes: int | None
    label: str | None
    ordinal: int


@dataclass(frozen=True)
class _MailboxExportSnapshot:
    """Index state selected under the mailbox export lock boundary."""

    registrations: tuple[MailboxRegistration, ...]
    messages: tuple[_MailboxExportMessage, ...]
    projections: tuple[_MailboxExportProjection, ...]
    attachments: tuple[_MailboxExportAttachment, ...]


def ensure_operator_mailbox_registration(mailbox_root: Path) -> dict[str, object]:
    """Provision or confirm the reserved filesystem mailbox operator account."""

    resolved_root = mailbox_root.resolve()
    paths = resolve_filesystem_mailbox_paths(resolved_root)
    return register_mailbox(
        resolved_root,
        RegisterMailboxRequest(
            mode="safe",
            address=HOUMAO_OPERATOR_ADDRESS,
            owner_principal_id=HOUMAO_OPERATOR_PRINCIPAL_ID,
            mailbox_kind="in_root",
            mailbox_path=paths.mailbox_entry_path(HOUMAO_OPERATOR_ADDRESS),
            display_name=HOUMAO_OPERATOR_DISPLAY_NAME,
            role=HOUMAO_OPERATOR_ROLE,
        ),
    )


def load_json_payload(path: Path) -> object:
    """Load a JSON payload file for a managed mailbox script."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManagedMailboxOperationError(f"payload file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManagedMailboxOperationError(f"payload file is not valid JSON: {path}") from exc


def run_managed_mailbox_script(
    *,
    description: str | None,
    request_model: type[_ManagedRequestT],
    handler: Callable[[Path, _ManagedRequestT], dict[str, object]],
    payload_required: bool = True,
    default_payload: object | None = None,
) -> int:
    """Run one managed mailbox wrapper script with shared validation and output handling."""

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--mailbox-root", required=True)
    parser.add_argument("--payload-file", required=payload_required)
    args = parser.parse_args()

    try:
        payload = default_payload
        if args.payload_file is not None:
            payload = load_json_payload(Path(args.payload_file))
        request = request_model.from_payload(payload)
        result = handler(Path(args.mailbox_root), request)
    except ManagedMailboxOperationError as exc:
        _emit_json_result({"ok": False, "error": str(exc)}, stream=sys.stdout)
        return 1

    _emit_json_result(result, stream=sys.stdout)
    return 0


def _emit_json_result(result: dict[str, object], *, stream: TextIO) -> None:
    """Emit one JSON result object plus a terminating newline."""

    json.dump(result, stream)
    stream.write("\n")


def _parse_managed_request(
    model_cls: type[_ManagedRequestT],
    payload: object,
) -> _ManagedRequestT:
    """Validate one managed request payload and normalize validation failures."""

    try:
        return model_cls.model_validate(payload)
    except ValidationError as exc:
        raise ManagedMailboxOperationError(
            _format_validation_error(model_cls.PAYLOAD_NAME, exc)
        ) from exc


def _format_validation_error(prefix: str, exc: ValidationError) -> str:
    """Return an actionable pydantic validation error message."""

    details: list[str] = []
    for issue in exc.errors(include_url=False):
        location = _format_error_location(issue.get("loc", ()))
        message = str(issue.get("msg", "validation failed"))
        details.append(f"{location}: {message}")
        if len(details) >= 5:
            break
    joined = "; ".join(details) if details else "validation failed"
    return f"{prefix}: {joined}"


def _format_error_location(location: object) -> str:
    """Render one pydantic error location as a JSONPath-like string."""

    if not isinstance(location, tuple) or not location:
        return "$"

    path = "$"
    for item in location:
        if isinstance(item, int):
            path += f"[{item}]"
            continue
        path += f".{item}"
    return path


def _normalize_non_blank_string(value: str) -> str:
    """Strip required strings and reject blank values."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("must not be empty")
    return normalized


def _normalize_optional_non_blank_string(value: str | None) -> str | None:
    """Strip optional strings and reject blank values when present."""

    if value is None:
        return None
    return _normalize_non_blank_string(value)


def _coerce_path_value(value: object) -> object:
    """Accept string payload paths while preserving strict path validation."""

    if isinstance(value, Path):
        return value.resolve()
    if isinstance(value, str):
        normalized = _normalize_non_blank_string(value)
        return Path(normalized).resolve()
    return value


def _validate_managed_address(value: str) -> str:
    """Validate one mailbox address for managed filesystem usage."""

    try:
        return mailbox_address_path_segment(_normalize_non_blank_string(value))
    except Exception as exc:
        raise ValueError(str(exc)) from exc


def _validate_managed_message_id(value: str) -> str:
    """Validate one canonical mailbox message identifier."""

    try:
        return validate_message_id(_normalize_non_blank_string(value))
    except Exception as exc:
        raise ValueError(str(exc)) from exc


def _normalize_managed_timestamp(value: str) -> str:
    """Normalize one managed mailbox timestamp."""

    try:
        return normalize_utc_timestamp(_normalize_non_blank_string(value))
    except Exception as exc:
        raise ValueError(str(exc)) from exc


def _coerce_cleanup_now(now: datetime | None) -> datetime:
    """Return one timezone-aware UTC cleanup timestamp."""

    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _registration_old_enough(
    registration: MailboxRegistration,
    *,
    older_than_seconds: int,
    now: datetime,
) -> bool:
    """Return whether one inactive or stashed registration is old enough for cleanup."""

    if older_than_seconds <= 0:
        return True
    timestamp_value = registration.deactivated_at_utc or registration.created_at_utc
    try:
        observed = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
    except ValueError:
        return True
    if observed.tzinfo is None or observed.utcoffset() is None:
        observed = observed.replace(tzinfo=UTC)
    return (now.astimezone(UTC) - observed.astimezone(UTC)).total_seconds() >= older_than_seconds


def ensure_mailbox_local_state(
    mailbox_root: Path,
    *,
    addresses: Sequence[str] | None = None,
) -> None:
    """Ensure active mailbox registrations have initialized local mailbox SQLite state."""

    paths = _resolve_paths(mailbox_root)
    _ensure_supported_mailbox_root(paths)
    if not paths.sqlite_path.is_file():
        return

    with sqlite3.connect(paths.sqlite_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        registrations = (
            _load_active_registrations(connection, addresses)
            if addresses is not None
            else _load_all_active_registrations(connection)
        )
        for registration in sorted(
            registrations.values(),
            key=lambda item: (item.address, item.registration_id),
        ):
            with _open_local_mailbox_connection(registration) as local_connection:
                _seed_or_rebuild_local_mailbox_state(
                    shared_connection=connection,
                    local_connection=local_connection,
                    registration=registration,
                    overwrite=False,
                )


@contextmanager
def _open_local_mailbox_connection(
    registration: MailboxRegistration,
    *,
    replace_unreadable: bool = False,
) -> Iterator[sqlite3.Connection]:
    """Open one prepared mailbox-local SQLite database."""

    _prepare_local_mailbox_sqlite_path(
        registration,
        replace_unreadable=replace_unreadable,
    )
    connection = sqlite3.connect(registration.local_sqlite_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _prepare_local_mailbox_sqlite_path(
    registration: MailboxRegistration,
    *,
    replace_unreadable: bool,
) -> None:
    """Create or repair one mailbox-local SQLite database before direct use."""

    try:
        initialize_mailbox_local_sqlite_schema(registration.local_sqlite_path)
    except sqlite3.DatabaseError:
        if not replace_unreadable:
            raise
        if registration.local_sqlite_path.exists():
            _backup_replaced_index(registration.local_sqlite_path, suffix="local-unusable")
        initialize_mailbox_local_sqlite_schema(registration.local_sqlite_path)


def _load_all_active_registrations(
    connection: sqlite3.Connection,
) -> dict[str, MailboxRegistration]:
    """Load every active registration keyed by address."""

    rows = connection.execute(
        """
        SELECT
            registration_id,
            address,
            owner_principal_id,
            status,
            mailbox_kind,
            mailbox_path,
            mailbox_entry_path,
            display_name,
            manifest_path_hint,
            role,
            created_at_utc,
            deactivated_at_utc,
            replaced_by_registration_id
        FROM mailbox_registrations
        WHERE status = 'active'
        """
    ).fetchall()
    return {registration.address: registration for registration in _rows_to_registrations(rows)}


def _load_all_registrations(connection: sqlite3.Connection) -> list[MailboxRegistration]:
    """Load every mailbox registration ordered for deterministic mutation/reporting."""

    rows = connection.execute(
        """
        SELECT
            registration_id,
            address,
            owner_principal_id,
            status,
            mailbox_kind,
            mailbox_path,
            mailbox_entry_path,
            display_name,
            manifest_path_hint,
            role,
            created_at_utc,
            deactivated_at_utc,
            replaced_by_registration_id
        FROM mailbox_registrations
        ORDER BY address, registration_id
        """
    ).fetchall()
    return _rows_to_registrations(rows)


def _load_cleanup_candidate_registrations(
    connection: sqlite3.Connection,
) -> list[MailboxRegistration]:
    """Load inactive and stashed registrations ordered for cleanup."""

    rows = connection.execute(
        """
        SELECT
            registration_id,
            address,
            owner_principal_id,
            status,
            mailbox_kind,
            mailbox_path,
            mailbox_entry_path,
            display_name,
            manifest_path_hint,
            role,
            created_at_utc,
            deactivated_at_utc,
            replaced_by_registration_id
        FROM mailbox_registrations
        WHERE status IN ('inactive', 'stashed')
        ORDER BY address, registration_id
        """
    ).fetchall()
    return _rows_to_registrations(rows)


def _seed_or_rebuild_local_mailbox_state(
    *,
    shared_connection: sqlite3.Connection,
    local_connection: sqlite3.Connection,
    registration: MailboxRegistration,
    overwrite: bool,
) -> int:
    """Seed or rebuild one mailbox-local SQLite database from shared structural state."""

    existing_row_count = int(
        local_connection.execute("SELECT COUNT(*) FROM message_state").fetchone()[0]
    )
    if existing_row_count > 0 and not overwrite:
        _rebuild_local_thread_summaries(connection=local_connection)
        return 0

    if overwrite or existing_row_count > 0:
        _clear_local_mailbox_state(connection=local_connection)

    rows = _registration_local_state_rows(
        connection=shared_connection,
        registration_id=registration.registration_id,
    )
    for row in rows:
        _insert_local_message_state_row(
            connection=local_connection,
            message_id=row["message_id"],
            thread_id=row["thread_id"],
            created_at_utc=row["created_at_utc"],
            subject=row["subject"],
            is_read=row["is_read"],
            is_answered=row["is_answered"],
            is_starred=row["is_starred"],
            is_archived=row["is_archived"],
            is_deleted=row["is_deleted"],
            box_name=row["box_name"],
        )
    _rebuild_local_thread_summaries(connection=local_connection)
    return len(rows)


def _registration_local_state_rows(
    *,
    connection: sqlite3.Connection,
    registration_id: str,
) -> list[_LocalMessageStateRow]:
    """Build mailbox-local state rows from shared structural projections."""

    rows = connection.execute(
        """
        SELECT
            projection.message_id,
            message.thread_id,
            message.created_at_utc,
            message.subject,
            projection.folder_name
        FROM mailbox_projections AS projection
        JOIN messages AS message ON message.message_id = projection.message_id
        WHERE projection.registration_id = ?
        ORDER BY message.created_at_utc ASC, projection.message_id ASC
        """,
        (registration_id,),
    ).fetchall()

    materialized_rows: list[_LocalMessageStateRow] = []
    current_message_id: str | None = None
    current_thread_id = ""
    current_created_at_utc = ""
    current_subject = ""
    current_folder_names: set[str] = set()

    def _flush_current_row() -> None:
        nonlocal current_message_id
        if current_message_id is None:
            return
        materialized_rows.append(
            {
                "message_id": current_message_id,
                "thread_id": current_thread_id,
                "created_at_utc": current_created_at_utc,
                "subject": current_subject,
                "is_read": _default_read_for_projection_folders(current_folder_names),
                "is_answered": False,
                "is_starred": False,
                "is_archived": _default_archived_for_projection_folders(current_folder_names),
                "is_deleted": False,
                "box_name": _default_box_for_projection_folders(current_folder_names),
            }
        )

    for row in rows:
        message_id = str(row[0])
        if current_message_id is not None and message_id != current_message_id:
            _flush_current_row()
            current_folder_names = set()
        if message_id != current_message_id:
            current_message_id = message_id
            current_thread_id = str(row[1])
            current_created_at_utc = str(row[2])
            current_subject = str(row[3])
        current_folder_names.add(str(row[4]))

    _flush_current_row()
    return materialized_rows


def _default_read_for_projection_folders(folder_names: set[str]) -> bool:
    """Return the deterministic default read state for one mailbox-local projection set."""

    return "inbox" not in folder_names


def _default_archived_for_projection_folders(folder_names: set[str]) -> bool:
    """Return the deterministic default archived state for one projection set."""

    return "archive" in folder_names and "inbox" not in folder_names


def _default_box_for_projection_folders(folder_names: set[str]) -> str:
    """Return the deterministic active box for one mailbox-local projection set."""

    for box_name in ("inbox", "sent", "archive"):
        if box_name in folder_names:
            return box_name
    return sorted(folder_names)[0] if folder_names else "inbox"


def _has_interactive_terminal(*streams: TextIO | None) -> bool:
    """Return whether all provided streams represent one interactive terminal."""

    effective_streams = streams or (sys.stdin, sys.stdout, sys.stderr)
    return all(stream is not None and stream.isatty() for stream in effective_streams)


def _confirm_managed_file_replacement(
    *,
    sqlite_path: Path,
    confirm_replace_managed_file: Callable[[str], bool] | None,
) -> None:
    """Confirm one destructive mailbox-local SQLite replacement."""

    prompt = (
        "Replace unreadable managed file "
        f"`{sqlite_path}` before adopting the private mailbox directory?"
    )
    if confirm_replace_managed_file is not None:
        confirmed = confirm_replace_managed_file(prompt)
    else:
        if not _has_interactive_terminal():
            raise ManagedMailboxOperationError(
                "safe registration failed: unreadable managed file "
                f"`{sqlite_path}` would need replacement, but no interactive TTY is available"
            )
        response = input(f"{prompt} [y/N]: ")
        confirmed = response.strip().lower() in {"y", "yes"}
    if not confirmed:
        raise ManagedMailboxOperationError(
            "safe registration cancelled: operator declined to replace unreadable managed file "
            f"`{sqlite_path}`"
        )


def _confirm_destructive_registration_replacement(
    *,
    prompt: str,
    cancelled_message: str,
    confirm_destructive_replace: Callable[[str], bool] | None,
) -> bool:
    """Confirm one destructive mailbox-registration replacement path when supported."""

    if confirm_destructive_replace is None:
        return False
    if not confirm_destructive_replace(prompt):
        raise ManagedMailboxOperationError(cancelled_message)
    return True


def _resolve_registration_conflict_prompt(
    *,
    request: RegisterMailboxRequest,
    active_registration: MailboxRegistration | None,
    occupying_registration: MailboxRegistration | None,
    desired_entry_path: Path,
) -> tuple[str, str]:
    """Describe one replaceable tracked-registration conflict."""

    if active_registration is not None:
        return (
            f"Replace the active mailbox registration for `{request.address}`?",
            f"safe registration failed: `{request.address}` already has an active mailbox",
        )
    assert occupying_registration is not None
    return (
        f"Replace the preserved mailbox artifact for `{request.address}` at `{desired_entry_path}`?",
        f"safe registration failed: `{request.address}` still has a preserved mailbox artifact",
    )


def _resolve_untracked_artifact_conflict_prompt(
    *,
    request: RegisterMailboxRequest,
    desired_mailbox_path: Path,
    desired_entry_path: Path,
) -> tuple[str, str] | None:
    """Describe one replaceable untracked mailbox-entry conflict when applicable."""

    if not (desired_entry_path.exists() or desired_entry_path.is_symlink()):
        return None
    if request.mailbox_kind == "symlink":
        if desired_entry_path.is_symlink() and desired_entry_path.resolve() == desired_mailbox_path:
            return None
        if desired_entry_path.is_symlink():
            return (
                "Replace the existing mailbox symlink at "
                f"`{desired_entry_path}` with one targeting `{desired_mailbox_path}`?",
                "safe registration failed: mailbox symlink points to a different target: "
                f"{desired_entry_path}",
            )
        return (
            f"Replace the existing mailbox entry at `{desired_entry_path}` with a symlink?",
            "safe registration failed: mailbox entry already exists and is not a symlink: "
            f"{desired_entry_path}",
        )
    return (
        f"Replace the existing mailbox entry artifact at `{desired_entry_path}`?",
        f"safe registration failed: mailbox entry already exists: {desired_entry_path}",
    )


def _resolve_effective_registration_mode(
    *,
    request: RegisterMailboxRequest,
    prompt: str | None,
    safe_error_message: str | None,
    confirm_destructive_replace: Callable[[str], bool] | None,
) -> Literal["safe", "force", "stash"]:
    """Resolve the effective registration mode after one optional confirmation."""

    if prompt is None or request.mode == "stash":
        return request.mode
    if request.mode == "safe":
        if _confirm_destructive_registration_replacement(
            prompt=prompt,
            cancelled_message=(
                "Mailbox registration cancelled: operator declined destructive replacement."
            ),
            confirm_destructive_replace=confirm_destructive_replace,
        ):
            return "force"
        assert safe_error_message is not None
        raise ManagedMailboxOperationError(safe_error_message)
    if request.mode == "force":
        _confirm_destructive_registration_replacement(
            prompt=prompt,
            cancelled_message=(
                "Mailbox registration cancelled: operator declined destructive replacement."
            ),
            confirm_destructive_replace=confirm_destructive_replace,
        )
    return request.mode


def _prepare_private_mailbox_local_sqlite_for_safe_registration(
    *,
    mailbox_path: Path,
    confirm_replace_managed_file: Callable[[str], bool] | None,
) -> None:
    """Prepare one private mailbox directory for safe symlink-backed registration."""

    resolved_mailbox_path = mailbox_path.resolve()
    resolved_mailbox_path.mkdir(parents=True, exist_ok=True)
    _ensure_mailbox_placeholder_dirs(resolved_mailbox_path)
    sqlite_path = resolved_mailbox_path / "mailbox.sqlite"
    try:
        initialize_mailbox_local_sqlite_schema(sqlite_path)
    except sqlite3.DatabaseError:
        _confirm_managed_file_replacement(
            sqlite_path=sqlite_path,
            confirm_replace_managed_file=confirm_replace_managed_file,
        )
        if sqlite_path.exists():
            _backup_replaced_index(sqlite_path, suffix="local-unusable")
        initialize_mailbox_local_sqlite_schema(sqlite_path)


def _clear_local_mailbox_state(
    *,
    connection: sqlite3.Connection,
) -> None:
    """Delete mailbox-local state rows from one mailbox-local database."""

    connection.execute("DELETE FROM thread_summaries")
    connection.execute("DELETE FROM message_state")


def _reset_local_mailbox_database(mailbox_path: Path) -> None:
    """Initialize and clear one mailbox-local SQLite database."""

    sqlite_path = mailbox_path.resolve() / "mailbox.sqlite"
    initialize_mailbox_local_sqlite_schema(sqlite_path)
    with sqlite3.connect(sqlite_path) as connection:
        connection.execute("DELETE FROM thread_summaries")
        connection.execute("DELETE FROM message_state")
        connection.commit()


def _insert_local_message_state_row(
    *,
    connection: sqlite3.Connection,
    message_id: str,
    thread_id: str,
    created_at_utc: str,
    subject: str,
    is_read: bool,
    is_answered: bool,
    is_starred: bool,
    is_archived: bool,
    is_deleted: bool,
    box_name: str,
) -> None:
    """Insert or replace one mailbox-local message-state row."""

    connection.execute(
        """
        INSERT INTO message_state (
            message_id,
            thread_id,
            created_at_utc,
            subject,
            is_read,
            is_answered,
            is_starred,
            is_archived,
            is_deleted,
            box_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(message_id) DO UPDATE SET
            thread_id = excluded.thread_id,
            created_at_utc = excluded.created_at_utc,
            subject = excluded.subject,
            is_read = excluded.is_read,
            is_answered = excluded.is_answered,
            is_starred = excluded.is_starred,
            is_archived = excluded.is_archived,
            is_deleted = excluded.is_deleted,
            box_name = excluded.box_name
        """,
        (
            message_id,
            thread_id,
            created_at_utc,
            subject,
            int(is_read),
            int(is_answered),
            int(is_starred),
            int(is_archived),
            int(is_deleted),
            box_name,
        ),
    )


def _rebuild_local_thread_summaries(
    *,
    connection: sqlite3.Connection,
) -> None:
    """Rebuild all mailbox-local thread summaries from local message-state rows."""

    thread_rows = connection.execute(
        "SELECT DISTINCT thread_id FROM message_state ORDER BY thread_id ASC"
    ).fetchall()
    connection.execute("DELETE FROM thread_summaries")
    for row in thread_rows:
        _recompute_local_thread_summary(
            connection=connection,
            thread_id=str(row[0]),
        )


def _recompute_local_thread_summary(
    *,
    connection: sqlite3.Connection,
    thread_id: str,
) -> None:
    """Recompute one mailbox-local thread summary from local message-state rows."""

    latest_row = connection.execute(
        """
        SELECT message_id, created_at_utc, subject
        FROM message_state
        WHERE thread_id = ?
        ORDER BY created_at_utc DESC, message_id DESC
        LIMIT 1
        """,
        (thread_id,),
    ).fetchone()
    if latest_row is None:
        connection.execute(
            "DELETE FROM thread_summaries WHERE thread_id = ?",
            (thread_id,),
        )
        return

    unread_count = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM message_state
            WHERE thread_id = ? AND is_read = 0
            """,
            (thread_id,),
        ).fetchone()[0]
    )
    connection.execute(
        """
        INSERT INTO thread_summaries (
            thread_id,
            normalized_subject,
            latest_message_id,
            latest_message_created_at_utc,
            unread_count
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(thread_id) DO UPDATE SET
            normalized_subject = excluded.normalized_subject,
            latest_message_id = excluded.latest_message_id,
            latest_message_created_at_utc = excluded.latest_message_created_at_utc,
            unread_count = excluded.unread_count
        """,
        (
            thread_id,
            str(latest_row[2]).strip().lower(),
            str(latest_row[0]),
            str(latest_row[1]),
            unread_count,
        ),
    )


def register_mailbox(
    mailbox_root: Path,
    request: RegisterMailboxRequest,
    *,
    lock_timeout_seconds: float = 5.0,
    confirm_replace_managed_file: Callable[[str], bool] | None = None,
    confirm_destructive_replace: Callable[[str], bool] | None = None,
) -> dict[str, object]:
    """Register or replace one mailbox address under the shared mailbox root."""

    paths = _resolve_paths(mailbox_root)
    _ensure_supported_mailbox_root(paths)
    initialize_sqlite_schema(paths.sqlite_path)

    desired_entry_path = paths.mailbox_entry_path(request.address)
    desired_mailbox_path = _desired_mailbox_path(
        paths=paths,
        mailbox_kind=request.mailbox_kind,
        address=request.address,
        requested_path=request.mailbox_path,
    )

    with _acquired_lock_set(paths, (request.address,), timeout_seconds=lock_timeout_seconds):
        with sqlite3.connect(paths.sqlite_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")

            if request.mailbox_kind == "symlink":
                _reject_private_mailbox_path_inside_root(
                    mailbox_root=paths.root,
                    mailbox_path=desired_mailbox_path,
                )

            active_registration = _load_active_registration(connection, address=request.address)
            occupying_registration = active_registration or _load_occupying_registration(
                connection,
                mailbox_entry_path=desired_entry_path,
            )
            path_registration = _load_active_registration_by_mailbox_path(
                connection,
                mailbox_path=desired_mailbox_path,
            )
            if (
                request.mailbox_kind == "symlink"
                and path_registration is not None
                and path_registration.address != request.address
            ):
                raise ManagedMailboxOperationError(
                    "safe registration failed: concrete mailbox path "
                    f"`{desired_mailbox_path}` is already active for `{path_registration.address}`"
                )
            if request.mailbox_kind == "symlink" and request.mode == "safe":
                _prepare_private_mailbox_local_sqlite_for_safe_registration(
                    mailbox_path=desired_mailbox_path,
                    confirm_replace_managed_file=(
                        confirm_destructive_replace or confirm_replace_managed_file
                    ),
                )

            if active_registration is not None and _registration_matches_request(
                active_registration,
                request=request,
                desired_mailbox_path=desired_mailbox_path,
                desired_entry_path=desired_entry_path,
            ):
                _ensure_artifact_for_registration(active_registration)
                _update_registration_metadata(
                    connection, active_registration.registration_id, request
                )
                connection.commit()
                initialize_mailbox_local_sqlite_schema(active_registration.local_sqlite_path)
                return {
                    "ok": True,
                    "mode": request.mode,
                    "address": request.address,
                    "active_registration_id": active_registration.registration_id,
                    "owner_principal_id": active_registration.owner_principal_id,
                    "status": "active",
                    "reused_existing": True,
                }

            if (
                active_registration is None
                and occupying_registration is not None
                and occupying_registration.status == "inactive"
                and _registration_matches_request(
                    occupying_registration,
                    request=request,
                    desired_mailbox_path=desired_mailbox_path,
                    desired_entry_path=desired_entry_path,
                )
            ):
                _restore_registration_artifact(
                    registration=occupying_registration,
                    desired_mailbox_path=desired_mailbox_path,
                    desired_entry_path=desired_entry_path,
                )
                _reactivate_registration(
                    connection, occupying_registration.registration_id, request
                )
                connection.commit()
                initialize_mailbox_local_sqlite_schema(occupying_registration.local_sqlite_path)
                return {
                    "ok": True,
                    "mode": request.mode,
                    "address": request.address,
                    "active_registration_id": occupying_registration.registration_id,
                    "owner_principal_id": request.owner_principal_id,
                    "status": "active",
                    "reused_existing": True,
                }

            tracked_conflict_prompt: str | None = None
            tracked_conflict_error: str | None = None
            if active_registration is not None or (
                active_registration is None and occupying_registration is not None
            ):
                tracked_conflict_prompt, tracked_conflict_error = (
                    _resolve_registration_conflict_prompt(
                        request=request,
                        active_registration=active_registration,
                        occupying_registration=occupying_registration,
                        desired_entry_path=desired_entry_path,
                    )
                )

            untracked_conflict: tuple[str, str] | None = None
            if confirm_destructive_replace is not None or request.mailbox_kind == "symlink":
                untracked_conflict = _resolve_untracked_artifact_conflict_prompt(
                    request=request,
                    desired_mailbox_path=desired_mailbox_path,
                    desired_entry_path=desired_entry_path,
                )
            effective_mode = request.mode
            if tracked_conflict_prompt is not None:
                effective_mode = _resolve_effective_registration_mode(
                    request=request,
                    prompt=tracked_conflict_prompt,
                    safe_error_message=tracked_conflict_error,
                    confirm_destructive_replace=confirm_destructive_replace,
                )
            elif untracked_conflict is not None:
                effective_mode = _resolve_effective_registration_mode(
                    request=request,
                    prompt=untracked_conflict[0],
                    safe_error_message=untracked_conflict[1],
                    confirm_destructive_replace=confirm_destructive_replace,
                )

            replacement_registration_id = _generate_registration_id()
            result: dict[str, object] = {
                "ok": True,
                "mode": effective_mode,
                "address": request.address,
                "active_registration_id": replacement_registration_id,
                "owner_principal_id": request.owner_principal_id,
                "status": "active",
            }

            if occupying_registration is not None:
                if effective_mode == "stash":
                    stashed_entry_path, stashed_mailbox_path = _stash_registration_artifact(
                        paths=paths,
                        registration=occupying_registration,
                    )
                    _mark_registration_stashed(
                        connection,
                        registration=occupying_registration,
                        stashed_entry_path=stashed_entry_path,
                        stashed_mailbox_path=stashed_mailbox_path,
                    )
                    result["stashed_registration_id"] = occupying_registration.registration_id
                    result["stashed_mailbox_path"] = str(stashed_entry_path)
                else:
                    _purge_registration_state(connection, occupying_registration.registration_id)
                    _mark_registration_replaced(
                        connection,
                        registration=occupying_registration,
                    )
                    _remove_registration_artifact(occupying_registration)
                    result["replaced_registration_id"] = occupying_registration.registration_id
            elif desired_entry_path.exists() or desired_entry_path.is_symlink():
                if effective_mode == "safe" and request.mailbox_kind == "symlink":
                    if desired_entry_path.is_symlink():
                        if desired_entry_path.resolve() != desired_mailbox_path:
                            raise ManagedMailboxOperationError(
                                "safe registration failed: mailbox symlink points to a different "
                                f"target: {desired_entry_path}"
                            )
                    else:
                        raise ManagedMailboxOperationError(
                            "safe registration failed: mailbox entry already exists and is not a "
                            f"symlink: {desired_entry_path}"
                        )
                elif effective_mode == "stash":
                    stashed_path = _stash_untracked_artifact(
                        paths, desired_entry_path, request.address
                    )
                    result["stashed_mailbox_path"] = str(stashed_path)
                else:
                    _remove_untracked_artifact(desired_entry_path)

            _create_requested_artifact(
                mailbox_kind=request.mailbox_kind,
                desired_mailbox_path=desired_mailbox_path,
                desired_entry_path=desired_entry_path,
            )
            _insert_registration(
                connection,
                registration_id=replacement_registration_id,
                request=request,
                mailbox_path=desired_mailbox_path,
                mailbox_entry_path=desired_entry_path,
                status="active",
                deactivated_at_utc=None,
                replaced_by_registration_id=None,
            )
            if occupying_registration is not None:
                _set_replaced_by_registration_id(
                    connection,
                    registration_id=occupying_registration.registration_id,
                    replacement_registration_id=replacement_registration_id,
                )
            connection.commit()
            if request.mailbox_kind == "symlink":
                ensure_mailbox_local_state(paths.root, addresses=(request.address,))
            else:
                _reset_local_mailbox_database(desired_mailbox_path)
            return result


def deregister_mailbox(
    mailbox_root: Path,
    request: DeregisterMailboxRequest,
    *,
    lock_timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Deactivate or purge the active registration for one mailbox address."""

    paths = _resolve_paths(mailbox_root)
    _ensure_supported_mailbox_root(paths)

    with _acquired_lock_set(paths, (request.address,), timeout_seconds=lock_timeout_seconds):
        with sqlite3.connect(paths.sqlite_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            registration = _load_active_registration(connection, address=request.address)
            if registration is None:
                raise ManagedMailboxOperationError(
                    f"no active mailbox registration exists for `{request.address}`"
                )
            if registration.address == HOUMAO_OPERATOR_ADDRESS:
                raise ManagedMailboxOperationError(
                    "generic mailbox unregister does not allow removing the reserved "
                    f"operator registration `{HOUMAO_OPERATOR_ADDRESS}`"
                )

            if request.mode == "deactivate":
                _mark_registration_inactive(connection, registration.registration_id)
                connection.commit()
                return {
                    "ok": True,
                    "mode": request.mode,
                    "address": request.address,
                    "target_registration_id": registration.registration_id,
                    "resulting_status": "inactive",
                    "deactivated_registration_id": registration.registration_id,
                }

            _purge_registration_state(connection, registration.registration_id)
            connection.execute(
                "DELETE FROM mailbox_registrations WHERE registration_id = ?",
                (registration.registration_id,),
            )
            connection.commit()

        _remove_registration_artifact(registration)
        return {
            "ok": True,
            "mode": request.mode,
            "address": request.address,
            "target_registration_id": registration.registration_id,
            "resulting_status": "purged",
            "purged_registration_id": registration.registration_id,
        }


def deliver_message(
    mailbox_root: Path,
    request: DeliveryRequest,
    *,
    lock_timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Commit a staged mailbox message into the filesystem transport."""

    paths = _resolve_paths(mailbox_root)
    _ensure_supported_mailbox_root(paths)
    _ensure_staged_message_path(paths.staging_dir, request.staged_message_path)

    recipient_principals = _unique_principals((*request.to, *request.cc))
    affected_addresses = tuple(
        sorted({request.sender.address, *(principal.address for principal in recipient_principals)})
    )
    staged_message_path = request.staged_message_path.resolve()

    with _acquired_lock_set(paths, affected_addresses, timeout_seconds=lock_timeout_seconds):
        with sqlite3.connect(paths.sqlite_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            registrations = _load_active_registrations(connection, affected_addresses)

            sender_registration = registrations.get(request.sender.address)
            if sender_registration is None:
                raise ManagedMailboxOperationError(
                    f"missing active mailbox registration for sender `{request.sender.address}`"
                )
            _validate_active_registration(sender_registration)
            if sender_registration.owner_principal_id != request.sender.principal_id:
                raise ManagedMailboxOperationError(
                    f"registered owner mismatch for sender `{request.sender.address}`"
                )

            recipient_registrations: dict[str, MailboxRegistration] = {}
            for principal in recipient_principals:
                registration = registrations.get(principal.address)
                if registration is None:
                    raise ManagedMailboxOperationError(
                        f"no active mailbox registration exists for `{principal.address}`"
                    )
                _validate_active_registration(registration)
                if registration.owner_principal_id != principal.principal_id:
                    raise ManagedMailboxOperationError(
                        f"registered owner mismatch for recipient `{principal.address}`"
                    )
                recipient_registrations[principal.address] = registration

            canonical_dir = paths.messages_dir / request.created_at_utc[:10]
            canonical_path = canonical_dir / f"{request.message_id}.md"
            projection_paths = _build_projection_targets(
                sender_registration=sender_registration,
                recipient_principals=recipient_principals,
                recipient_registrations=recipient_registrations,
                message_id=request.message_id,
            )

            created_projection_paths: list[Path] = []
            moved_to_canonical = False

            try:
                if canonical_path.exists():
                    raise ManagedMailboxOperationError(
                        f"canonical message already exists: {canonical_path}"
                    )

                canonical_dir.mkdir(parents=True, exist_ok=True)
                staged_message_path.replace(canonical_path)
                moved_to_canonical = True

                for projection_path in projection_paths:
                    _create_projection_symlink(projection_path, canonical_path)
                    created_projection_paths.append(projection_path)

                connection.execute("BEGIN IMMEDIATE")
                _insert_message_record(
                    connection=connection,
                    request=request,
                    canonical_path=canonical_path,
                    sender_registration_id=sender_registration.registration_id,
                )
                _insert_recipient_records(
                    connection=connection,
                    request=request,
                    recipient_registrations=recipient_registrations,
                )
                _insert_attachment_records(connection, request)
                _insert_projection_records(
                    connection=connection,
                    sender_registration=sender_registration,
                    recipient_principals=recipient_principals,
                    recipient_registrations=recipient_registrations,
                    projection_paths=projection_paths,
                    message_id=request.message_id,
                )
                _recompute_thread_summary(connection, request.thread_id)
                connection.commit()
            except Exception:
                connection.rollback()
                for projection_path in reversed(created_projection_paths):
                    if projection_path.is_symlink() or projection_path.exists():
                        projection_path.unlink(missing_ok=True)
                if (
                    moved_to_canonical
                    and canonical_path.exists()
                    and not staged_message_path.exists()
                ):
                    canonical_path.replace(staged_message_path)
                raise

            try:
                _insert_mailbox_state_records(
                    sender_registration=sender_registration,
                    recipient_principals=recipient_principals,
                    recipient_registrations=recipient_registrations,
                    message_id=request.message_id,
                    thread_id=request.thread_id,
                    created_at_utc=request.created_at_utc,
                    subject=request.subject,
                )
            except Exception as exc:
                raise ManagedMailboxOperationError(
                    "mailbox-local state update failed after delivery committed for "
                    f"`{request.message_id}`; run mailbox repair for `{paths.root}` to rebuild "
                    f"local state: {exc}"
                ) from exc

    return {
        "ok": True,
        "message_id": request.message_id,
        "canonical_path": str(canonical_path),
        "recipient_count": len(recipient_principals),
    }


def update_mailbox_state(
    mailbox_root: Path,
    request: StateUpdateRequest,
    *,
    lock_timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Apply a mailbox-state mutation for one active registration and message."""

    paths = _resolve_paths(mailbox_root)
    _ensure_supported_mailbox_root(paths)

    with _acquired_lock_set(paths, (request.address,), timeout_seconds=lock_timeout_seconds):
        with sqlite3.connect(paths.sqlite_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            registration = _load_active_registration(connection, address=request.address)
            if registration is None:
                raise ManagedMailboxOperationError(
                    f"no active mailbox registration exists for `{request.address}`"
                )
            _validate_active_registration(registration)

            message_row = connection.execute(
                "SELECT thread_id FROM messages WHERE message_id = ?",
                (request.message_id,),
            ).fetchone()
            if message_row is None:
                raise ManagedMailboxOperationError(f"unknown message id `{request.message_id}`")
            thread_id = str(message_row[0])
            with _open_local_mailbox_connection(registration) as local_connection:
                local_connection.execute("BEGIN IMMEDIATE")
                existing_state = local_connection.execute(
                    """
                    SELECT 1
                    FROM message_state
                    WHERE message_id = ?
                    """,
                    (request.message_id,),
                ).fetchone()
                if existing_state is None:
                    projection_rows = connection.execute(
                        """
                        SELECT projection.folder_name, message.thread_id, message.created_at_utc, message.subject
                        FROM mailbox_projections AS projection
                        JOIN messages AS message ON message.message_id = projection.message_id
                        WHERE projection.registration_id = ? AND projection.message_id = ?
                        ORDER BY projection.folder_name ASC
                        """,
                        (registration.registration_id, request.message_id),
                    ).fetchall()
                    if not projection_rows:
                        raise ManagedMailboxOperationError(
                            f"message `{request.message_id}` is not projected into `{request.address}`"
                        )
                    folder_names = {str(row[0]) for row in projection_rows}
                    projection_row = projection_rows[0]
                    _insert_local_message_state_row(
                        connection=local_connection,
                        message_id=request.message_id,
                        thread_id=str(projection_row[1]),
                        created_at_utc=str(projection_row[2]),
                        subject=str(projection_row[3]),
                        is_read=_default_read_for_projection_folders(folder_names),
                        is_answered=False,
                        is_starred=False,
                        is_archived=_default_archived_for_projection_folders(folder_names),
                        is_deleted=False,
                        box_name=_default_box_for_projection_folders(folder_names),
                    )

                assignments: list[str] = []
                parameters: list[object] = []
                if request.read is not None:
                    assignments.append("is_read = ?")
                    parameters.append(int(request.read))
                if request.answered is not None:
                    assignments.append("is_answered = ?")
                    parameters.append(int(request.answered))
                if request.starred is not None:
                    assignments.append("is_starred = ?")
                    parameters.append(int(request.starred))
                if request.archived is not None:
                    assignments.append("is_archived = ?")
                    parameters.append(int(request.archived))
                if request.deleted is not None:
                    assignments.append("is_deleted = ?")
                    parameters.append(int(request.deleted))
                parameters.append(request.message_id)
                local_connection.execute(
                    f"""
                    UPDATE message_state
                    SET {", ".join(assignments)}
                    WHERE message_id = ?
                    """,
                    tuple(parameters),
                )
                _recompute_local_thread_summary(
                    connection=local_connection,
                    thread_id=thread_id,
                )
                state_row = local_connection.execute(
                    """
                    SELECT is_read, is_answered, is_starred, is_archived, is_deleted, box_name
                    FROM message_state
                    WHERE message_id = ?
                    """,
                    (request.message_id,),
                ).fetchone()

    assert state_row is not None
    return {
        "ok": True,
        "address": request.address,
        "owner_principal_id": registration.owner_principal_id,
        "registration_id": registration.registration_id,
        "message_id": request.message_id,
        "read": bool(state_row[0]),
        "answered": bool(state_row[1]),
        "starred": bool(state_row[2]),
        "archived": bool(state_row[3]),
        "deleted": bool(state_row[4]),
        "box": str(state_row[5]),
    }


def repair_mailbox_index(
    mailbox_root: Path,
    request: RepairRequest,
    *,
    lock_timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Rebuild mailbox indexes from canonical messages and clean staging artifacts."""

    paths = _resolve_paths(mailbox_root)
    _ensure_supported_mailbox_root(paths)
    discovered_mailboxes = _discover_mailbox_paths(paths.mailboxes_dir)
    affected_addresses = tuple(sorted({artifact.address for artifact in discovered_mailboxes}))

    with _acquired_lock_set(paths, affected_addresses, timeout_seconds=lock_timeout_seconds):
        recovered_messages = _load_recovery_messages(paths.messages_dir)
        snapshot = _snapshot_existing_index(paths.sqlite_path)
        initialize_sqlite_schema(paths.sqlite_path)
        staging_results = (
            _cleanup_staging_artifacts(
                paths.staging_dir,
                quarantine=request.quarantine_staging,
            )
            if request.cleanup_staging
            else []
        )

        with sqlite3.connect(paths.sqlite_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            recovered_registrations = _recover_registrations(
                connection=connection,
                discovered_mailboxes=discovered_mailboxes,
                snapshot=snapshot,
                recovered_messages=recovered_messages,
            )
            projection_count = 0
            restored_state_count = 0
            defaulted_state_count = 0
            thread_ids: set[str] = set()
            local_state_plans: list[tuple[MailboxMessage, str | None, tuple[str | None, ...]]] = []
            try:
                for recovered_message in recovered_messages:
                    thread_ids.add(recovered_message.message.thread_id)
                    sender_registration_id = snapshot.sender_registration_ids.get(
                        recovered_message.message.message_id
                    )
                    if sender_registration_id is None:
                        sender_registration_id = _best_effort_registration_id(
                            registrations=recovered_registrations,
                            address=recovered_message.message.sender.address,
                            owner_principal_id=recovered_message.message.sender.principal_id,
                        )
                    _insert_recovered_message_record(
                        connection=connection,
                        recovered_message=recovered_message,
                        sender_registration_id=sender_registration_id,
                    )
                    recipient_registration_ids = _insert_recovered_recipient_records(
                        connection=connection,
                        message=recovered_message.message,
                        snapshot=snapshot,
                        registrations=recovered_registrations,
                    )
                    local_state_plans.append(
                        (
                            recovered_message.message,
                            sender_registration_id,
                            tuple(recipient_registration_ids),
                        )
                    )
                    _insert_recovered_attachment_records(connection, recovered_message.message)
                    projection_count += _repair_projection_records(
                        connection=connection,
                        registrations=recovered_registrations,
                        recovered_message=recovered_message,
                        sender_registration_id=sender_registration_id,
                        recipient_registration_ids=recipient_registration_ids,
                    )

                for thread_id in sorted(thread_ids):
                    _recompute_thread_summary(connection, thread_id)
                connection.commit()
            except Exception:
                connection.rollback()
                raise

            try:
                for registration in recovered_registrations.values():
                    if registration.mailbox_path.exists() and registration.mailbox_path.is_dir():
                        with _open_local_mailbox_connection(
                            registration,
                            replace_unreadable=True,
                        ) as local_connection:
                            _clear_local_mailbox_state(connection=local_connection)

                for (
                    message,
                    sender_registration_id,
                    recovered_recipient_registration_ids,
                ) in local_state_plans:
                    restored_count, defaulted_count = _insert_recovered_mailbox_state_records(
                        registrations=recovered_registrations,
                        message=message,
                        sender_registration_id=sender_registration_id,
                        recipient_registration_ids=recovered_recipient_registration_ids,
                    )
                    restored_state_count += restored_count
                    defaulted_state_count += defaulted_count

                for registration in recovered_registrations.values():
                    if registration.mailbox_path.exists() and registration.mailbox_path.is_dir():
                        with _open_local_mailbox_connection(registration) as local_connection:
                            _rebuild_local_thread_summaries(connection=local_connection)
            except Exception as exc:
                raise ManagedMailboxOperationError(
                    "mailbox-local state repair failed after shared mailbox index was rebuilt; "
                    f"rerun mailbox repair for `{paths.root}` to rebuild local state: {exc}"
                ) from exc

    return {
        "ok": True,
        "message_count": len(recovered_messages),
        "projection_count": projection_count,
        "registration_count": len(recovered_registrations),
        "restored_state_count": restored_state_count,
        "defaulted_state_count": defaulted_state_count,
        "staging_action": "quarantine" if request.quarantine_staging else "remove",
        "staging_artifact_count": len(staging_results),
        "staging_artifact_paths": [str(path) for path in staging_results],
        "backed_up_index_path": None if snapshot.backup_path is None else str(snapshot.backup_path),
    }


def cleanup_mailbox_registrations(
    mailbox_root: Path,
    *,
    inactive_older_than_seconds: int = 0,
    stashed_older_than_seconds: int = 0,
    dry_run: bool = False,
    now: datetime | None = None,
    lock_timeout_seconds: float = 5.0,
) -> MailboxCleanupResult:
    """Clean inactive or stashed mailbox registrations without touching canonical messages."""

    paths = _resolve_paths(mailbox_root)
    _ensure_supported_mailbox_root(paths)
    if not paths.sqlite_path.is_file():
        raise ManagedMailboxOperationError(
            f"mailbox root needs repair before cleanup: missing index `{paths.sqlite_path}`"
        )

    current_time = _coerce_cleanup_now(now)
    try:
        with sqlite3.connect(paths.sqlite_path) as seed_connection:
            seed_connection.execute("PRAGMA foreign_keys = ON")
            seed_candidates = _load_cleanup_candidate_registrations(seed_connection)
    except sqlite3.DatabaseError as exc:
        raise ManagedMailboxOperationError(
            f"mailbox root needs repair before cleanup: {exc}"
        ) from exc

    affected_addresses = tuple(sorted({registration.address for registration in seed_candidates}))
    planned: list[MailboxCleanupRecord] = []
    removed: list[MailboxCleanupRecord] = []
    preserved: list[MailboxCleanupRecord] = []
    blocked: list[MailboxCleanupRecord] = []

    with _acquired_lock_set(paths, affected_addresses, timeout_seconds=lock_timeout_seconds):
        try:
            with sqlite3.connect(paths.sqlite_path) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute("BEGIN IMMEDIATE")

                active_registrations = _load_all_active_registrations(connection)
                for registration in sorted(
                    active_registrations.values(),
                    key=lambda item: (item.address, item.registration_id),
                ):
                    preserved.append(
                        MailboxCleanupRecord(
                            outcome="preserved",
                            artifact_kind="active_registration",
                            path=registration.mailbox_entry_path,
                            reason="active mailbox registrations are intentionally outside cleanup scope",
                            address=registration.address,
                            registration_id=registration.registration_id,
                            registration_status=registration.status,
                        )
                    )

                candidates = _load_cleanup_candidate_registrations(connection)
                for registration in candidates:
                    if registration.address == HOUMAO_OPERATOR_ADDRESS:
                        preserved.append(
                            MailboxCleanupRecord(
                                outcome="preserved",
                                artifact_kind="mailbox_registration",
                                path=registration.mailbox_entry_path,
                                reason=(
                                    "reserved operator registration is part of the filesystem "
                                    "mailbox root contract and is outside cleanup scope"
                                ),
                                address=registration.address,
                                registration_id=registration.registration_id,
                                registration_status=registration.status,
                            )
                        )
                        continue
                    threshold_seconds = (
                        inactive_older_than_seconds
                        if registration.status == "inactive"
                        else stashed_older_than_seconds
                    )
                    if not _registration_old_enough(
                        registration,
                        older_than_seconds=threshold_seconds,
                        now=current_time,
                    ):
                        preserved.append(
                            MailboxCleanupRecord(
                                outcome="preserved",
                                artifact_kind="mailbox_registration",
                                path=registration.mailbox_entry_path,
                                reason=(
                                    f"{registration.status} registration is newer than its cleanup threshold"
                                ),
                                address=registration.address,
                                registration_id=registration.registration_id,
                                registration_status=registration.status,
                            )
                        )
                        continue

                    cleanup_record = MailboxCleanupRecord(
                        outcome="planned" if dry_run else "removed",
                        artifact_kind="mailbox_registration",
                        path=registration.mailbox_entry_path,
                        reason=(
                            f"{registration.status} mailbox registration is no longer active and is"
                            " eligible for cleanup"
                        ),
                        address=registration.address,
                        registration_id=registration.registration_id,
                        registration_status=registration.status,
                    )
                    if dry_run:
                        planned.append(cleanup_record)
                        continue

                    try:
                        _remove_registration_artifact(registration)
                        _purge_registration_state(connection, registration.registration_id)
                        connection.execute(
                            "DELETE FROM mailbox_registrations WHERE registration_id = ?",
                            (registration.registration_id,),
                        )
                    except (OSError, sqlite3.DatabaseError) as exc:
                        blocked.append(
                            MailboxCleanupRecord(
                                outcome="blocked",
                                artifact_kind="mailbox_registration",
                                path=registration.mailbox_entry_path,
                                reason=f"{cleanup_record.reason}; cleanup failed: {exc}",
                                address=registration.address,
                                registration_id=registration.registration_id,
                                registration_status=registration.status,
                            )
                        )
                    else:
                        removed.append(cleanup_record)

                connection.commit()
        except sqlite3.DatabaseError as exc:
            raise ManagedMailboxOperationError(
                f"mailbox root needs repair before cleanup: {exc}"
            ) from exc

    if paths.messages_dir.exists():
        preserved.append(
            MailboxCleanupRecord(
                outcome="preserved",
                artifact_kind="canonical_messages",
                path=paths.messages_dir,
                reason="canonical mailbox message history is intentionally preserved during cleanup",
            )
        )

    return MailboxCleanupResult(
        mailbox_root=paths.root,
        dry_run=dry_run,
        planned=tuple(planned),
        removed=tuple(removed),
        preserved=tuple(preserved),
        blocked=tuple(blocked),
    )


def clear_mailbox_messages(
    mailbox_root: Path,
    *,
    dry_run: bool = False,
    lock_timeout_seconds: float = 5.0,
) -> MailboxMessageClearResult:
    """Clear delivered messages and derived state without unregistering mailbox accounts."""

    paths = _resolve_paths(mailbox_root)
    _ensure_supported_mailbox_root(paths)
    if not paths.sqlite_path.is_file():
        raise ManagedMailboxOperationError(
            f"mailbox root needs repair before clearing messages: missing index `{paths.sqlite_path}`"
        )

    try:
        with sqlite3.connect(paths.sqlite_path) as seed_connection:
            seed_connection.execute("PRAGMA foreign_keys = ON")
            seed_registrations = _load_all_registrations(seed_connection)
    except sqlite3.DatabaseError as exc:
        raise ManagedMailboxOperationError(
            f"mailbox root needs repair before clearing messages: {exc}"
        ) from exc

    affected_addresses = tuple(
        sorted({registration.address for registration in seed_registrations})
    )
    planned: list[MailboxCleanupRecord] = []
    removed: list[MailboxCleanupRecord] = []
    preserved: list[MailboxCleanupRecord] = []
    blocked: list[MailboxCleanupRecord] = []

    with _acquired_lock_set(paths, affected_addresses, timeout_seconds=lock_timeout_seconds):
        try:
            with sqlite3.connect(paths.sqlite_path) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                registrations = _load_all_registrations(connection)
                targets = _message_clear_targets(
                    paths=paths,
                    connection=connection,
                    registrations=registrations,
                )
                blocked_targets = tuple(target for target in targets if target.outcome == "blocked")
                removal_targets = tuple(target for target in targets if target.outcome != "blocked")

                for registration in sorted(
                    registrations,
                    key=lambda item: (item.address, item.registration_id),
                ):
                    preserved.append(
                        MailboxCleanupRecord(
                            outcome="preserved",
                            artifact_kind="mailbox_registration",
                            path=registration.mailbox_entry_path,
                            reason=(
                                "mailbox registrations are intentionally preserved during "
                                "message clearing"
                            ),
                            address=registration.address,
                            registration_id=registration.registration_id,
                            registration_status=registration.status,
                        )
                    )

                if dry_run:
                    planned.extend(removal_targets)
                    blocked.extend(blocked_targets)
                    return MailboxMessageClearResult(
                        mailbox_root=paths.root,
                        dry_run=True,
                        planned=tuple(planned),
                        removed=(),
                        preserved=tuple(preserved),
                        blocked=tuple(blocked),
                    )

                connection.execute("BEGIN IMMEDIATE")
                _delete_shared_message_index_rows(connection)
                connection.commit()
        except sqlite3.DatabaseError as exc:
            raise ManagedMailboxOperationError(
                f"mailbox root needs repair before clearing messages: {exc}"
            ) from exc

        blocked.extend(blocked_targets)
        for target in removal_targets:
            try:
                if target.artifact_kind == "mailbox_local_state":
                    _clear_existing_local_mailbox_database(target.path)
                else:
                    _remove_message_clear_artifact(target.path)
                    if target.artifact_kind == "canonical_message":
                        _remove_empty_descendant_dirs(paths.messages_dir)
                    elif target.artifact_kind == "managed_attachment":
                        _remove_empty_descendant_dirs(paths.attachments_managed_dir)
            except (OSError, sqlite3.DatabaseError) as exc:
                blocked.append(
                    MailboxCleanupRecord(
                        outcome="blocked",
                        artifact_kind=target.artifact_kind,
                        path=target.path,
                        reason=f"{target.reason}; clear failed: {exc}",
                        address=target.address,
                        registration_id=target.registration_id,
                        registration_status=target.registration_status,
                        message_id=target.message_id,
                        attachment_id=target.attachment_id,
                    )
                )
            else:
                removed.append(
                    MailboxCleanupRecord(
                        outcome="removed",
                        artifact_kind=target.artifact_kind,
                        path=target.path,
                        reason=target.reason,
                        address=target.address,
                        registration_id=target.registration_id,
                        registration_status=target.registration_status,
                        message_id=target.message_id,
                        attachment_id=target.attachment_id,
                    )
                )

    return MailboxMessageClearResult(
        mailbox_root=paths.root,
        dry_run=False,
        planned=(),
        removed=tuple(removed),
        preserved=tuple(preserved),
        blocked=tuple(blocked),
    )


def export_mailbox_archive(
    mailbox_root: Path,
    request: MailboxExportRequest,
    *,
    lock_timeout_seconds: float = 5.0,
) -> MailboxExportResult:
    """Export selected filesystem mailbox state into a portable archive directory."""

    paths = _resolve_paths(mailbox_root)
    _ensure_supported_mailbox_root(paths)
    if not paths.sqlite_path.is_file():
        raise ManagedMailboxOperationError(
            f"mailbox root needs repair before export: missing index `{paths.sqlite_path}`"
        )
    _ensure_export_output_available(request.output_dir)

    try:
        with sqlite3.connect(paths.sqlite_path) as seed_connection:
            seed_connection.execute("PRAGMA foreign_keys = ON")
            seed_registrations = _select_export_registrations(
                seed_connection,
                request=request,
            )
    except sqlite3.DatabaseError as exc:
        raise ManagedMailboxOperationError(
            f"mailbox root needs repair before export: {exc}"
        ) from exc

    locked_addresses = tuple(sorted({registration.address for registration in seed_registrations}))

    with _acquired_lock_set(paths, locked_addresses, timeout_seconds=lock_timeout_seconds):
        _ensure_export_output_available(request.output_dir)
        try:
            with sqlite3.connect(paths.sqlite_path) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                snapshot = _load_export_snapshot(connection, request=request)
        except sqlite3.DatabaseError as exc:
            raise ManagedMailboxOperationError(
                f"mailbox root needs repair before export: {exc}"
            ) from exc

        _validate_export_registration_artifacts(snapshot.registrations)
        return _write_mailbox_export_archive(paths=paths, request=request, snapshot=snapshot)


def _select_export_registrations(
    connection: sqlite3.Connection,
    *,
    request: MailboxExportRequest,
) -> tuple[MailboxRegistration, ...]:
    """Return registrations selected by one export request."""

    registrations = tuple(_load_all_registrations(connection))
    if request.all_accounts:
        return registrations

    requested_addresses = set(request.addresses)
    selected = tuple(
        registration
        for registration in registrations
        if registration.address in requested_addresses
    )
    found_addresses = {registration.address for registration in selected}
    missing_addresses = tuple(sorted(requested_addresses - found_addresses))
    if missing_addresses:
        raise ManagedMailboxOperationError(
            "mailbox export selected address not found: " + ", ".join(missing_addresses)
        )
    return selected


def _load_export_snapshot(
    connection: sqlite3.Connection,
    *,
    request: MailboxExportRequest,
) -> _MailboxExportSnapshot:
    """Load export-selected mailbox index state."""

    registrations = _select_export_registrations(connection, request=request)
    registration_ids = tuple(registration.registration_id for registration in registrations)
    messages = _load_export_messages(
        connection,
        all_accounts=request.all_accounts,
        registration_ids=registration_ids,
    )
    message_ids = tuple(message.message_id for message in messages)
    projections = _load_export_projections(
        connection,
        registration_ids=registration_ids,
    )
    attachments = _load_export_attachments(connection, message_ids=message_ids)
    return _MailboxExportSnapshot(
        registrations=registrations,
        messages=messages,
        projections=projections,
        attachments=attachments,
    )


def _load_export_messages(
    connection: sqlite3.Connection,
    *,
    all_accounts: bool,
    registration_ids: Sequence[str],
) -> tuple[_MailboxExportMessage, ...]:
    """Load canonical message rows selected for export."""

    if all_accounts:
        rows = connection.execute(
            """
            SELECT
                message_id,
                thread_id,
                in_reply_to,
                created_at_utc,
                canonical_path,
                subject,
                sender_address,
                sender_principal_id,
                sender_registration_id
            FROM messages
            ORDER BY created_at_utc, message_id
            """
        ).fetchall()
    elif registration_ids:
        placeholders = _sql_placeholders(len(registration_ids))
        rows = connection.execute(
            f"""
            SELECT DISTINCT
                message.message_id,
                message.thread_id,
                message.in_reply_to,
                message.created_at_utc,
                message.canonical_path,
                message.subject,
                message.sender_address,
                message.sender_principal_id,
                message.sender_registration_id
            FROM messages AS message
            JOIN mailbox_projections AS projection
              ON projection.message_id = message.message_id
            WHERE projection.registration_id IN ({placeholders})
            ORDER BY message.created_at_utc, message.message_id
            """,
            registration_ids,
        ).fetchall()
    else:
        rows = []

    return tuple(
        _MailboxExportMessage(
            message_id=str(row[0]),
            thread_id=str(row[1]),
            in_reply_to=None if row[2] is None else str(row[2]),
            created_at_utc=str(row[3]),
            canonical_path=_artifact_path(str(row[4])),
            subject=str(row[5]),
            sender_address=str(row[6]),
            sender_principal_id=str(row[7]),
            sender_registration_id=None if row[8] is None else str(row[8]),
        )
        for row in rows
    )


def _load_export_projections(
    connection: sqlite3.Connection,
    *,
    registration_ids: Sequence[str],
) -> tuple[_MailboxExportProjection, ...]:
    """Load projection rows selected for export."""

    if not registration_ids:
        return ()
    placeholders = _sql_placeholders(len(registration_ids))
    rows = connection.execute(
        f"""
        SELECT registration_id, message_id, folder_name, projection_path
        FROM mailbox_projections
        WHERE registration_id IN ({placeholders})
        ORDER BY registration_id, folder_name, message_id, projection_path
        """,
        tuple(registration_ids),
    ).fetchall()
    return tuple(
        _MailboxExportProjection(
            registration_id=str(row[0]),
            message_id=str(row[1]),
            folder_name=str(row[2]),
            projection_path=_artifact_path(str(row[3])),
        )
        for row in rows
    )


def _load_export_attachments(
    connection: sqlite3.Connection,
    *,
    message_ids: Sequence[str],
) -> tuple[_MailboxExportAttachment, ...]:
    """Load attachment rows linked to selected messages."""

    if not message_ids:
        return ()
    placeholders = _sql_placeholders(len(message_ids))
    rows = connection.execute(
        f"""
        SELECT
            link.message_id,
            attachment.attachment_id,
            attachment.kind,
            attachment.locator,
            attachment.media_type,
            attachment.sha256,
            attachment.size_bytes,
            attachment.label,
            link.ordinal
        FROM message_attachments AS link
        JOIN attachments AS attachment
          ON attachment.attachment_id = link.attachment_id
        WHERE link.message_id IN ({placeholders})
        ORDER BY link.message_id, link.ordinal, attachment.attachment_id
        """,
        tuple(message_ids),
    ).fetchall()
    return tuple(
        _MailboxExportAttachment(
            message_id=str(row[0]),
            attachment_id=str(row[1]),
            kind=str(row[2]),
            locator=str(row[3]),
            media_type=str(row[4]),
            sha256=None if row[5] is None else str(row[5]),
            size_bytes=None if row[6] is None else int(row[6]),
            label=None if row[7] is None else str(row[7]),
            ordinal=int(row[8]),
        )
        for row in rows
    )


def _validate_export_registration_artifacts(
    registrations: Sequence[MailboxRegistration],
) -> None:
    """Reject active registration artifacts that indicate a repair-needed root."""

    for registration in registrations:
        if registration.status != "active":
            continue
        if registration.mailbox_kind == "symlink":
            if not registration.mailbox_entry_path.is_symlink():
                raise ManagedMailboxOperationError(
                    f"mailbox root needs repair before export: missing symlink registration for "
                    f"`{registration.address}`"
                )
        elif registration.mailbox_kind == "in_root":
            if registration.mailbox_entry_path.is_symlink():
                raise ManagedMailboxOperationError(
                    f"mailbox root needs repair before export: in-root registration "
                    f"`{registration.address}` is a symlink"
                )
        else:
            raise ManagedMailboxOperationError(
                f"mailbox root needs repair before export: unsupported mailbox kind "
                f"`{registration.mailbox_kind}`"
            )

        if not registration.mailbox_path.is_dir():
            raise ManagedMailboxOperationError(
                f"mailbox root needs repair before export: invalid mailbox path for "
                f"`{registration.address}`: {registration.mailbox_path}"
            )
        for directory_name in _MAILBOX_PLACEHOLDER_DIRS:
            if not (registration.mailbox_path / directory_name).is_dir():
                raise ManagedMailboxOperationError(
                    f"mailbox root needs repair before export: `{registration.address}` is "
                    f"missing `{directory_name}/`"
                )


def _write_mailbox_export_archive(
    *,
    paths: FilesystemMailboxPaths,
    request: MailboxExportRequest,
    snapshot: _MailboxExportSnapshot,
) -> MailboxExportResult:
    """Write one selected mailbox snapshot through a temporary archive directory."""

    output_dir = request.output_dir
    output_parent = output_dir.parent
    output_parent.mkdir(parents=True, exist_ok=True)
    temp_dir = _mailbox_export_temp_dir(output_dir)

    copied: list[MailboxExportAction] = []
    materialized: list[MailboxExportAction] = []
    preserved_symlinks: list[MailboxExportAction] = []
    skipped: list[MailboxExportAction] = []
    blocked: list[MailboxExportAction] = []
    manifest: dict[str, object] = {
        "schema_version": 1,
        "source_mailbox_root": str(paths.root),
        "source_protocol_version": MAILBOX_PROTOCOL_VERSION,
        "exported_at_utc": _timestamp_utc(),
        "selection": {
            "all_accounts": request.all_accounts,
            "addresses": list(request.addresses),
        },
        "symlink_mode": request.symlink_mode,
        "accounts": [],
        "messages": [],
        "projections": [],
        "attachments": [],
    }

    try:
        temp_dir.mkdir()
        message_archive_paths = _export_canonical_messages(
            paths=paths,
            snapshot=snapshot,
            output_dir=output_dir,
            temp_dir=temp_dir,
            manifest=manifest,
            copied=copied,
            blocked=blocked,
        )
        _export_accounts(
            snapshot=snapshot,
            output_dir=output_dir,
            temp_dir=temp_dir,
            manifest=manifest,
            copied=copied,
            skipped=skipped,
        )
        _export_projections(
            snapshot=snapshot,
            output_dir=output_dir,
            temp_dir=temp_dir,
            symlink_mode=request.symlink_mode,
            message_archive_paths=message_archive_paths,
            manifest=manifest,
            materialized=materialized,
            preserved_symlinks=preserved_symlinks,
            blocked=blocked,
        )
        _export_attachments(
            paths=paths,
            snapshot=snapshot,
            output_dir=output_dir,
            temp_dir=temp_dir,
            manifest=manifest,
            copied=copied,
            skipped=skipped,
            blocked=blocked,
        )
        manifest["copied_artifacts"] = [action.to_payload() for action in copied]
        manifest["materialized_artifacts"] = [action.to_payload() for action in materialized]
        manifest["preserved_symlinks"] = [action.to_payload() for action in preserved_symlinks]
        manifest["skipped_artifacts"] = [action.to_payload() for action in skipped]
        manifest["blocked_artifacts"] = [action.to_payload() for action in blocked]
        _write_json_file(temp_dir / "manifest.json", manifest)
        if request.symlink_mode == "materialize":
            _ensure_export_tree_has_no_symlinks(temp_dir)
        _ensure_export_output_available(output_dir)
        temp_dir.rename(output_dir)
    except Exception:
        if temp_dir.exists() or temp_dir.is_symlink():
            _remove_export_temp_dir(temp_dir)
        raise

    return MailboxExportResult(
        mailbox_root=paths.root,
        output_dir=output_dir,
        manifest_path=output_dir / "manifest.json",
        symlink_mode=request.symlink_mode,
        all_accounts=request.all_accounts,
        selected_addresses=request.addresses,
        account_count=len(snapshot.registrations),
        message_count=len(snapshot.messages),
        attachment_count=len(snapshot.attachments),
        copied=tuple(copied),
        materialized=tuple(materialized),
        preserved_symlinks=tuple(preserved_symlinks),
        skipped=tuple(skipped),
        blocked=tuple(blocked),
    )


def _export_canonical_messages(
    *,
    paths: FilesystemMailboxPaths,
    snapshot: _MailboxExportSnapshot,
    output_dir: Path,
    temp_dir: Path,
    manifest: dict[str, object],
    copied: list[MailboxExportAction],
    blocked: list[MailboxExportAction],
) -> dict[str, Path]:
    """Copy exported canonical messages and update manifest state."""

    archive_paths: dict[str, Path] = {}
    message_manifest = _manifest_list(manifest, "messages")
    for message in snapshot.messages:
        archive_path: Path | None = None
        if not _path_is_relative_to(message.canonical_path, paths.messages_dir):
            blocked.append(
                MailboxExportAction(
                    outcome="blocked",
                    artifact_kind="canonical_message",
                    source_path=message.canonical_path,
                    archive_path=None,
                    reason="canonical message path is outside the mailbox messages directory",
                    message_id=message.message_id,
                )
            )
        elif not message.canonical_path.is_file():
            blocked.append(
                MailboxExportAction(
                    outcome="blocked",
                    artifact_kind="canonical_message",
                    source_path=message.canonical_path,
                    archive_path=None,
                    reason="canonical message file is missing",
                    message_id=message.message_id,
                )
            )
        else:
            relative_source = message.canonical_path.relative_to(paths.messages_dir)
            archive_path = temp_dir / "messages" / relative_source
            _copy_export_artifact(message.canonical_path, archive_path)
            archive_paths[message.message_id] = archive_path
            copied.append(
                MailboxExportAction(
                    outcome="copied",
                    artifact_kind="canonical_message",
                    source_path=message.canonical_path,
                    archive_path=_final_archive_path(
                        output_dir=output_dir,
                        temp_dir=temp_dir,
                        temp_path=archive_path,
                    ),
                    reason="canonical mailbox message copied into export archive",
                    message_id=message.message_id,
                )
            )

        message_manifest.append(
            {
                "message_id": message.message_id,
                "thread_id": message.thread_id,
                "in_reply_to": message.in_reply_to,
                "created_at_utc": message.created_at_utc,
                "subject": message.subject,
                "sender_address": message.sender_address,
                "sender_principal_id": message.sender_principal_id,
                "sender_registration_id": message.sender_registration_id,
                "source_path": str(message.canonical_path),
                "archive_path": None
                if archive_path is None
                else _archive_relative_path(temp_dir, archive_path),
            }
        )
    return archive_paths


def _export_accounts(
    *,
    snapshot: _MailboxExportSnapshot,
    output_dir: Path,
    temp_dir: Path,
    manifest: dict[str, object],
    copied: list[MailboxExportAction],
    skipped: list[MailboxExportAction],
) -> None:
    """Materialize selected account directories and metadata."""

    account_manifest = _manifest_list(manifest, "accounts")
    for registration in snapshot.registrations:
        account_dir = _export_account_dir(temp_dir, registration)
        account_dir.mkdir(parents=True, exist_ok=True)
        for folder_name in _MAILBOX_PLACEHOLDER_DIRS:
            (account_dir / folder_name).mkdir(parents=True, exist_ok=True)

        account_json_path = account_dir / "account.json"
        account_payload = _export_account_manifest(
            registration=registration,
            temp_dir=temp_dir,
            account_dir=account_dir,
        )
        _write_json_file(account_json_path, account_payload)
        copied.append(
            MailboxExportAction(
                outcome="copied",
                artifact_kind="account_metadata",
                source_path=None,
                archive_path=_final_archive_path(
                    output_dir=output_dir,
                    temp_dir=temp_dir,
                    temp_path=account_json_path,
                ),
                reason="registration metadata written into export archive",
                address=registration.address,
                registration_id=registration.registration_id,
                registration_status=registration.status,
            )
        )

        local_sqlite_archive_path: Path | None = None
        local_sqlite_path = registration.local_sqlite_path
        if local_sqlite_path.is_file():
            local_sqlite_archive_path = account_dir / "mailbox.sqlite"
            _copy_export_artifact(local_sqlite_path, local_sqlite_archive_path)
            copied.append(
                MailboxExportAction(
                    outcome="copied",
                    artifact_kind="mailbox_local_sqlite",
                    source_path=local_sqlite_path,
                    archive_path=_final_archive_path(
                        output_dir=output_dir,
                        temp_dir=temp_dir,
                        temp_path=local_sqlite_archive_path,
                    ),
                    reason="mailbox-local SQLite state copied into export archive",
                    address=registration.address,
                    registration_id=registration.registration_id,
                    registration_status=registration.status,
                )
            )
        else:
            skipped.append(
                MailboxExportAction(
                    outcome="skipped",
                    artifact_kind="mailbox_local_sqlite",
                    source_path=local_sqlite_path,
                    archive_path=None,
                    reason="mailbox-local SQLite state file was not present",
                    address=registration.address,
                    registration_id=registration.registration_id,
                    registration_status=registration.status,
                )
            )

        account_payload["archive_local_sqlite_path"] = (
            None
            if local_sqlite_archive_path is None
            else _archive_relative_path(temp_dir, local_sqlite_archive_path)
        )
        _write_json_file(account_json_path, account_payload)
        account_manifest.append(account_payload)


def _export_projections(
    *,
    snapshot: _MailboxExportSnapshot,
    output_dir: Path,
    temp_dir: Path,
    symlink_mode: Literal["materialize", "preserve"],
    message_archive_paths: dict[str, Path],
    manifest: dict[str, object],
    materialized: list[MailboxExportAction],
    preserved_symlinks: list[MailboxExportAction],
    blocked: list[MailboxExportAction],
) -> None:
    """Copy or preserve archive-internal message projection links."""

    projection_manifest = _manifest_list(manifest, "projections")
    registrations_by_id = {
        registration.registration_id: registration for registration in snapshot.registrations
    }
    messages_by_id = {message.message_id: message for message in snapshot.messages}
    for projection in snapshot.projections:
        registration = registrations_by_id.get(projection.registration_id)
        message = messages_by_id.get(projection.message_id)
        account_dir = None if registration is None else _export_account_dir(temp_dir, registration)
        projection_archive_path = None
        projection_action = "blocked"
        projection_reason = "projection was not exported"

        if registration is None:
            blocked.append(
                MailboxExportAction(
                    outcome="blocked",
                    artifact_kind="mailbox_projection",
                    source_path=projection.projection_path,
                    archive_path=None,
                    reason="projection registration was not selected for export",
                    registration_id=projection.registration_id,
                    message_id=projection.message_id,
                )
            )
        elif message is None or projection.message_id not in message_archive_paths:
            blocked.append(
                MailboxExportAction(
                    outcome="blocked",
                    artifact_kind="mailbox_projection",
                    source_path=projection.projection_path,
                    archive_path=None,
                    reason="projection canonical message was not available in the export",
                    address=registration.address,
                    registration_id=registration.registration_id,
                    registration_status=registration.status,
                    message_id=projection.message_id,
                )
            )
        elif not _path_is_relative_to(projection.projection_path, registration.mailbox_path):
            blocked.append(
                MailboxExportAction(
                    outcome="blocked",
                    artifact_kind="mailbox_projection",
                    source_path=projection.projection_path,
                    archive_path=None,
                    reason="projection path is outside the registered mailbox path",
                    address=registration.address,
                    registration_id=registration.registration_id,
                    registration_status=registration.status,
                    message_id=projection.message_id,
                )
            )
        else:
            assert account_dir is not None
            projection_archive_path = (
                account_dir / projection.folder_name / f"{projection.message_id}.md"
            )
            canonical_archive_path = message_archive_paths[projection.message_id]
            projection_archive_path.parent.mkdir(parents=True, exist_ok=True)
            if symlink_mode == "preserve":
                relative_target = Path(
                    os.path.relpath(canonical_archive_path, start=projection_archive_path.parent)
                )
                try:
                    projection_archive_path.symlink_to(relative_target)
                except OSError as exc:
                    raise ManagedMailboxOperationError(
                        "mailbox export could not create a projection symlink in preserve "
                        f"mode at `{projection_archive_path}`: {exc}"
                    ) from exc
                preserved_symlinks.append(
                    MailboxExportAction(
                        outcome="preserved_symlink",
                        artifact_kind="mailbox_projection",
                        source_path=projection.projection_path,
                        archive_path=_final_archive_path(
                            output_dir=output_dir,
                            temp_dir=temp_dir,
                            temp_path=projection_archive_path,
                        ),
                        reason="projection preserved as archive-internal relative symlink",
                        address=registration.address,
                        registration_id=registration.registration_id,
                        registration_status=registration.status,
                        message_id=projection.message_id,
                        symlink_target=relative_target,
                    )
                )
                projection_action = "preserved_symlink"
                projection_reason = "projection preserved as relative archive symlink"
            else:
                _copy_export_artifact(canonical_archive_path, projection_archive_path)
                materialized.append(
                    MailboxExportAction(
                        outcome="materialized",
                        artifact_kind="mailbox_projection",
                        source_path=projection.projection_path,
                        archive_path=_final_archive_path(
                            output_dir=output_dir,
                            temp_dir=temp_dir,
                            temp_path=projection_archive_path,
                        ),
                        reason="projection symlink materialized as a regular archive file",
                        address=registration.address,
                        registration_id=registration.registration_id,
                        registration_status=registration.status,
                        message_id=projection.message_id,
                    )
                )
                projection_action = "materialized"
                projection_reason = "projection materialized as regular file"

        projection_manifest.append(
            {
                "registration_id": projection.registration_id,
                "address": None if registration is None else registration.address,
                "message_id": projection.message_id,
                "folder_name": projection.folder_name,
                "source_path": str(projection.projection_path),
                "archive_path": None
                if projection_archive_path is None
                else _archive_relative_path(temp_dir, projection_archive_path),
                "action": projection_action,
                "reason": projection_reason,
            }
        )


def _export_attachments(
    *,
    paths: FilesystemMailboxPaths,
    snapshot: _MailboxExportSnapshot,
    output_dir: Path,
    temp_dir: Path,
    manifest: dict[str, object],
    copied: list[MailboxExportAction],
    skipped: list[MailboxExportAction],
    blocked: list[MailboxExportAction],
) -> None:
    """Copy mailbox-owned managed attachments and record external path refs."""

    attachment_manifest = _manifest_list(manifest, "attachments")
    copied_archive_paths: dict[str, Path] = {}
    terminal_actions: dict[str, str] = {}

    for attachment in snapshot.attachments:
        source_path = _artifact_path(attachment.locator)
        archive_path = copied_archive_paths.get(attachment.attachment_id)
        action = terminal_actions.get(attachment.attachment_id)
        reason = "attachment action reused from an earlier selected message"

        if action is None:
            if attachment.kind == "path_ref":
                exists = source_path.exists()
                skipped.append(
                    MailboxExportAction(
                        outcome="skipped",
                        artifact_kind="path_ref_attachment",
                        source_path=source_path,
                        archive_path=None,
                        reason="external path_ref attachment recorded in manifest only",
                        attachment_id=attachment.attachment_id,
                        message_id=attachment.message_id,
                        details={"target_exists": exists},
                    )
                )
                action = "skipped"
                reason = "external path_ref attachment recorded in manifest only"
            elif attachment.kind != "managed_copy":
                blocked.append(
                    MailboxExportAction(
                        outcome="blocked",
                        artifact_kind="attachment",
                        source_path=source_path,
                        archive_path=None,
                        reason=f"unsupported attachment kind `{attachment.kind}`",
                        attachment_id=attachment.attachment_id,
                        message_id=attachment.message_id,
                    )
                )
                action = "blocked"
                reason = f"unsupported attachment kind `{attachment.kind}`"
            elif not _path_resolves_relative_to(source_path, paths.attachments_managed_dir):
                blocked.append(
                    MailboxExportAction(
                        outcome="blocked",
                        artifact_kind="managed_attachment",
                        source_path=source_path,
                        archive_path=None,
                        reason=(
                            "managed-copy attachment path is outside the mailbox managed "
                            "attachment directory"
                        ),
                        attachment_id=attachment.attachment_id,
                        message_id=attachment.message_id,
                    )
                )
                action = "blocked"
                reason = "managed-copy attachment path is outside the managed attachment directory"
            elif not source_path.exists():
                blocked.append(
                    MailboxExportAction(
                        outcome="blocked",
                        artifact_kind="managed_attachment",
                        source_path=source_path,
                        archive_path=None,
                        reason="managed-copy attachment file is missing",
                        attachment_id=attachment.attachment_id,
                        message_id=attachment.message_id,
                    )
                )
                action = "blocked"
                reason = "managed-copy attachment file is missing"
            else:
                archive_path = (
                    temp_dir
                    / "attachments"
                    / "managed"
                    / attachment.attachment_id
                    / (source_path.name or "attachment")
                )
                _copy_export_artifact(source_path, archive_path)
                copied_archive_paths[attachment.attachment_id] = archive_path
                copied.append(
                    MailboxExportAction(
                        outcome="copied",
                        artifact_kind="managed_attachment",
                        source_path=source_path,
                        archive_path=_final_archive_path(
                            output_dir=output_dir,
                            temp_dir=temp_dir,
                            temp_path=archive_path,
                        ),
                        reason="mailbox-owned managed-copy attachment copied into export archive",
                        attachment_id=attachment.attachment_id,
                        message_id=attachment.message_id,
                    )
                )
                action = "copied"
                reason = "managed-copy attachment copied into export archive"

            terminal_actions[attachment.attachment_id] = action

        attachment_manifest.append(
            {
                "message_id": attachment.message_id,
                "attachment_id": attachment.attachment_id,
                "kind": attachment.kind,
                "source_path": str(source_path),
                "media_type": attachment.media_type,
                "sha256": attachment.sha256,
                "size_bytes": attachment.size_bytes,
                "label": attachment.label,
                "ordinal": attachment.ordinal,
                "target_exists": source_path.exists(),
                "archive_path": None
                if archive_path is None
                else _archive_relative_path(temp_dir, archive_path),
                "action": action,
                "reason": reason,
            }
        )


def _export_account_dir(temp_dir: Path, registration: MailboxRegistration) -> Path:
    """Return the archive account directory for one registration."""

    return (
        temp_dir
        / "accounts"
        / mailbox_address_path_segment(registration.address)
        / registration.registration_id
    )


def _export_account_manifest(
    *,
    registration: MailboxRegistration,
    temp_dir: Path,
    account_dir: Path,
) -> dict[str, object]:
    """Return manifest metadata for one exported account registration."""

    source_entry_target = (
        str(registration.mailbox_entry_path.resolve())
        if registration.mailbox_entry_path.is_symlink()
        else None
    )
    return {
        "registration_id": registration.registration_id,
        "address": registration.address,
        "owner_principal_id": registration.owner_principal_id,
        "status": registration.status,
        "mailbox_kind": registration.mailbox_kind,
        "source_mailbox_path": str(registration.mailbox_path),
        "source_mailbox_entry_path": str(registration.mailbox_entry_path),
        "source_mailbox_entry_is_symlink": registration.mailbox_entry_path.is_symlink(),
        "source_mailbox_entry_target": source_entry_target,
        "archive_account_path": _archive_relative_path(temp_dir, account_dir),
        "display_name": registration.display_name,
        "manifest_path_hint": registration.manifest_path_hint,
        "role": registration.role,
        "created_at_utc": registration.created_at_utc,
        "deactivated_at_utc": registration.deactivated_at_utc,
        "replaced_by_registration_id": registration.replaced_by_registration_id,
    }


def _ensure_export_output_available(output_dir: Path) -> None:
    """Require that the final export output path does not already exist."""

    if output_dir.exists() or output_dir.is_symlink():
        raise ManagedMailboxOperationError(
            f"mailbox export output directory already exists: {output_dir}"
        )


def _mailbox_export_temp_dir(output_dir: Path) -> Path:
    """Return a unique sibling temporary export directory."""

    name = output_dir.name or "mailbox-export"
    while True:
        candidate = output_dir.parent / f".{name}.tmp-{os.getpid()}-{uuid4().hex}"
        if not candidate.exists() and not candidate.is_symlink():
            return candidate


def _copy_export_artifact(source_path: Path, archive_path: Path) -> None:
    """Copy one source artifact while materializing symlink content."""

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.is_dir():
        shutil.copytree(source_path, archive_path, symlinks=False)
        return
    if source_path.is_file():
        shutil.copy2(source_path, archive_path, follow_symlinks=True)
        return
    raise ManagedMailboxOperationError(f"mailbox export source artifact is missing: {source_path}")


def _archive_relative_path(archive_root: Path, archive_path: Path) -> str:
    """Return one POSIX archive-relative manifest path."""

    return archive_path.relative_to(archive_root).as_posix()


def _final_archive_path(*, output_dir: Path, temp_dir: Path, temp_path: Path) -> Path:
    """Return the final archive path corresponding to a temporary archive path."""

    return output_dir / temp_path.relative_to(temp_dir)


def _manifest_list(manifest: dict[str, object], key: str) -> list[dict[str, object]]:
    """Return a typed list from an export manifest draft."""

    value = manifest[key]
    if not isinstance(value, list):
        raise AssertionError(f"manifest key `{key}` is not a list")
    return value


def _write_json_file(path: Path, payload: object) -> None:
    """Write one stable UTF-8 JSON payload."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _ensure_export_tree_has_no_symlinks(root: Path) -> None:
    """Verify that a materialized export tree contains no symlink artifacts."""

    if root.is_symlink():
        raise ManagedMailboxOperationError(
            f"mailbox export materialize mode produced a symlink: {root}"
        )
    for candidate in root.rglob("*"):
        if candidate.is_symlink():
            raise ManagedMailboxOperationError(
                f"mailbox export materialize mode produced a symlink: {candidate}"
            )


def _remove_export_temp_dir(temp_dir: Path) -> None:
    """Remove one temporary export directory after a failed export."""

    if temp_dir.is_symlink() or temp_dir.is_file():
        temp_dir.unlink(missing_ok=True)
        return
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


def _path_resolves_relative_to(path: Path, root: Path) -> bool:
    """Return whether one path resolves under a root path."""

    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _sql_placeholders(count: int) -> str:
    """Return a positional SQL placeholder list for one non-empty sequence."""

    if count <= 0:
        raise ValueError("SQL placeholder count must be positive")
    return ", ".join("?" for _ in range(count))


def _message_clear_targets(
    *,
    paths: FilesystemMailboxPaths,
    connection: sqlite3.Connection,
    registrations: Sequence[MailboxRegistration],
) -> tuple[MailboxCleanupRecord, ...]:
    """Return deterministic filesystem/local-state targets for message clearing."""

    targets: list[MailboxCleanupRecord] = []
    seen_paths: set[Path] = set()

    for message_id, canonical_path in _message_clear_canonical_paths(
        paths=paths,
        connection=connection,
    ):
        _append_unique_clear_target(
            targets=targets,
            seen_paths=seen_paths,
            target=MailboxCleanupRecord(
                outcome="planned",
                artifact_kind="canonical_message",
                path=canonical_path,
                reason="canonical delivered mailbox message is in clear-messages scope",
                message_id=message_id,
            ),
        )

    registration_by_id = {
        registration.registration_id: registration for registration in registrations
    }
    for row in connection.execute(
        """
        SELECT registration_id, message_id, projection_path
        FROM mailbox_projections
        ORDER BY registration_id, message_id, folder_name, projection_path
        """
    ).fetchall():
        registration = registration_by_id.get(str(row[0]))
        projection_path = _artifact_path(str(row[2]))
        if registration is not None and not _path_is_relative_to(
            projection_path, registration.mailbox_path
        ):
            targets.append(
                MailboxCleanupRecord(
                    outcome="blocked",
                    artifact_kind="mailbox_projection",
                    path=projection_path,
                    reason=(
                        "recorded mailbox projection is outside the registered mailbox path "
                        "and will not be deleted automatically"
                    ),
                    address=registration.address,
                    registration_id=registration.registration_id,
                    registration_status=registration.status,
                    message_id=str(row[1]),
                )
            )
            continue
        if projection_path.exists() or projection_path.is_symlink():
            _append_unique_clear_target(
                targets=targets,
                seen_paths=seen_paths,
                target=MailboxCleanupRecord(
                    outcome="planned",
                    artifact_kind="mailbox_projection",
                    path=projection_path,
                    reason="mailbox projection for delivered message is in clear-messages scope",
                    address=None if registration is None else registration.address,
                    registration_id=None if registration is None else registration.registration_id,
                    registration_status=None if registration is None else registration.status,
                    message_id=str(row[1]),
                ),
            )

    for record in _stale_projection_targets(
        registrations=registrations,
        already_seen_paths=seen_paths,
    ):
        _append_unique_clear_target(targets=targets, seen_paths=seen_paths, target=record)

    for record in _managed_attachment_clear_targets(paths=paths, connection=connection):
        _append_unique_clear_target(targets=targets, seen_paths=seen_paths, target=record)

    for record in _stale_managed_attachment_targets(paths=paths, already_seen_paths=seen_paths):
        _append_unique_clear_target(targets=targets, seen_paths=seen_paths, target=record)

    for registration in registrations:
        local_sqlite_path = registration.local_sqlite_path
        if not local_sqlite_path.is_file():
            continue
        try:
            if _local_mailbox_state_row_count(local_sqlite_path) == 0:
                continue
        except sqlite3.DatabaseError:
            pass
        _append_unique_clear_target(
            targets=targets,
            seen_paths=seen_paths,
            target=MailboxCleanupRecord(
                outcome="planned",
                artifact_kind="mailbox_local_state",
                path=local_sqlite_path,
                reason="mailbox-local message and thread state is in clear-messages scope",
                address=registration.address,
                registration_id=registration.registration_id,
                registration_status=registration.status,
            ),
        )

    return tuple(targets)


def _message_clear_canonical_paths(
    *,
    paths: FilesystemMailboxPaths,
    connection: sqlite3.Connection,
) -> list[tuple[str | None, Path]]:
    """Return canonical message files known from the index plus stale canonical files."""

    rows = connection.execute(
        """
        SELECT message_id, canonical_path
        FROM messages
        ORDER BY created_at_utc, message_id
        """
    ).fetchall()
    canonical_paths: list[tuple[str | None, Path]] = []
    for message_id, path_value in rows:
        canonical_path = _artifact_path(str(path_value))
        if canonical_path.exists() or canonical_path.is_symlink():
            canonical_paths.append((str(message_id), canonical_path))
    known_paths = {path for _message_id, path in canonical_paths}
    if paths.messages_dir.exists():
        for stale_path in sorted(paths.messages_dir.rglob("*.md")):
            resolved_stale_path = _artifact_path(stale_path)
            if resolved_stale_path not in known_paths:
                canonical_paths.append((stale_path.stem, resolved_stale_path))
                known_paths.add(resolved_stale_path)
    return canonical_paths


def _stale_projection_targets(
    *,
    registrations: Sequence[MailboxRegistration],
    already_seen_paths: set[Path],
) -> list[MailboxCleanupRecord]:
    """Return mailbox projection symlinks not currently present in the shared index."""

    targets: list[MailboxCleanupRecord] = []
    for registration in registrations:
        if not registration.mailbox_path.is_dir():
            continue
        for directory_name in _MAILBOX_PLACEHOLDER_DIRS:
            folder_path = registration.mailbox_path / directory_name
            if not folder_path.is_dir():
                continue
            for projection_path in sorted(folder_path.glob("*.md")):
                resolved_projection_path = _artifact_path(projection_path)
                if resolved_projection_path in already_seen_paths:
                    continue
                if not projection_path.is_symlink():
                    continue
                targets.append(
                    MailboxCleanupRecord(
                        outcome="planned",
                        artifact_kind="mailbox_projection",
                        path=resolved_projection_path,
                        reason="stale mailbox projection symlink is in clear-messages scope",
                        address=registration.address,
                        registration_id=registration.registration_id,
                        registration_status=registration.status,
                        message_id=projection_path.stem,
                    )
                )
    return targets


def _managed_attachment_clear_targets(
    *,
    paths: FilesystemMailboxPaths,
    connection: sqlite3.Connection,
) -> list[MailboxCleanupRecord]:
    """Return managed-copy attachment artifacts referenced by delivered messages."""

    targets: list[MailboxCleanupRecord] = []
    rows = connection.execute(
        """
        SELECT DISTINCT attachment.attachment_id, attachment.locator
        FROM attachments AS attachment
        JOIN message_attachments AS link
          ON link.attachment_id = attachment.attachment_id
        WHERE attachment.kind = 'managed_copy'
        ORDER BY attachment.attachment_id
        """
    ).fetchall()
    for attachment_id, locator in rows:
        attachment_path = _artifact_path(str(locator))
        if not _path_is_relative_to(attachment_path, paths.attachments_managed_dir):
            targets.append(
                MailboxCleanupRecord(
                    outcome="blocked",
                    artifact_kind="managed_attachment",
                    path=attachment_path,
                    reason=(
                        "managed-copy attachment path is outside the mailbox managed "
                        "attachment directory and will not be deleted automatically"
                    ),
                    attachment_id=str(attachment_id),
                )
            )
            continue
        if attachment_path.exists() or attachment_path.is_symlink():
            targets.append(
                MailboxCleanupRecord(
                    outcome="planned",
                    artifact_kind="managed_attachment",
                    path=attachment_path,
                    reason="mailbox-owned managed-copy attachment is in clear-messages scope",
                    attachment_id=str(attachment_id),
                )
            )
    return targets


def _stale_managed_attachment_targets(
    *,
    paths: FilesystemMailboxPaths,
    already_seen_paths: set[Path],
) -> list[MailboxCleanupRecord]:
    """Return stale mailbox-owned managed attachment artifacts."""

    if not paths.attachments_managed_dir.exists():
        return []
    targets: list[MailboxCleanupRecord] = []
    for attachment_path in sorted(paths.attachments_managed_dir.rglob("*"), reverse=True):
        if attachment_path.is_dir():
            continue
        resolved_attachment_path = _artifact_path(attachment_path)
        if resolved_attachment_path in already_seen_paths:
            continue
        targets.append(
            MailboxCleanupRecord(
                outcome="planned",
                artifact_kind="managed_attachment",
                path=resolved_attachment_path,
                reason="stale mailbox-owned managed attachment is in clear-messages scope",
            )
        )
    return targets


def _append_unique_clear_target(
    *,
    targets: list[MailboxCleanupRecord],
    seen_paths: set[Path],
    target: MailboxCleanupRecord,
) -> None:
    """Append one clear target once per filesystem path."""

    if target.path in seen_paths:
        return
    seen_paths.add(target.path)
    targets.append(target)


def _delete_shared_message_index_rows(connection: sqlite3.Connection) -> None:
    """Delete shared index rows that are derived from delivered messages."""

    connection.execute("DELETE FROM messages")
    connection.execute("DELETE FROM attachments")
    connection.execute("DELETE FROM thread_summaries")


def _clear_existing_local_mailbox_database(sqlite_path: Path) -> None:
    """Clear message and thread state from one existing mailbox-local SQLite database."""

    initialize_mailbox_local_sqlite_schema(sqlite_path)
    with sqlite3.connect(sqlite_path) as connection:
        connection.execute("DELETE FROM thread_summaries")
        connection.execute("DELETE FROM message_state")
        connection.commit()


def _local_mailbox_state_row_count(sqlite_path: Path) -> int:
    """Return the count of mailbox-local rows that message clearing would reset."""

    with sqlite3.connect(sqlite_path) as connection:
        message_count = int(connection.execute("SELECT COUNT(*) FROM message_state").fetchone()[0])
        thread_count = int(
            connection.execute("SELECT COUNT(*) FROM thread_summaries").fetchone()[0]
        )
    return message_count + thread_count


def _remove_message_clear_artifact(path: Path) -> None:
    """Remove one filesystem artifact owned by delivered-message clear."""

    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    if path.exists():
        shutil.rmtree(path)


def _remove_empty_descendant_dirs(root: Path) -> None:
    """Remove empty descendant directories while preserving the root itself."""

    if not root.is_dir():
        return
    for candidate in sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            candidate.rmdir()
        except OSError:
            pass


def _path_is_relative_to(path: Path, root: Path) -> bool:
    """Return whether one path resolves under a root path."""

    candidate = _artifact_path(path)
    root_path = _artifact_path(root)
    try:
        candidate.relative_to(root_path)
    except ValueError:
        return False
    return True


def _artifact_path(path: str | Path) -> Path:
    """Return one absolute path without dereferencing a symlink artifact."""

    return Path(os.path.abspath(Path(path).expanduser()))


def _resolve_paths(mailbox_root: Path) -> FilesystemMailboxPaths:
    """Resolve the filesystem paths used by managed mailbox scripts."""

    return resolve_filesystem_mailbox_paths(mailbox_root)


def _ensure_supported_mailbox_root(paths: FilesystemMailboxPaths) -> None:
    """Validate one mailbox root before managed mutations proceed."""

    reason = unsupported_mailbox_root_reason(paths.root)
    if reason is not None:
        raise ManagedMailboxOperationError(reason)

    try:
        raw_value = paths.protocol_version_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ManagedMailboxOperationError(
            f"missing protocol version file: {paths.protocol_version_file}"
        ) from exc
    if raw_value != str(MAILBOX_PROTOCOL_VERSION):
        raise ManagedMailboxOperationError(
            f"unsupported mailbox protocol version: expected {MAILBOX_PROTOCOL_VERSION}, found {raw_value or '<empty>'}"
        )


def _ensure_staged_message_path(staging_dir: Path, staged_message_path: Path) -> None:
    """Require staged messages to live under the mailbox staging directory."""

    try:
        staged_message_path.relative_to(staging_dir.resolve())
    except ValueError as exc:
        raise ManagedMailboxOperationError(
            "staged message must live under the mailbox staging directory"
        ) from exc
    if not staged_message_path.is_file():
        raise ManagedMailboxOperationError(f"staged message not found: {staged_message_path}")


def _desired_mailbox_path(
    *,
    paths: FilesystemMailboxPaths,
    mailbox_kind: str,
    address: str,
    requested_path: Path,
) -> Path:
    """Resolve the concrete mailbox directory path for a registration request."""

    if mailbox_kind == "in_root":
        expected_path = paths.mailbox_entry_path(address)
        if requested_path != expected_path:
            raise ManagedMailboxOperationError(
                f"in_root mailbox registrations must use the shared mailbox path `{expected_path}`"
            )
        return expected_path
    return requested_path.resolve()


def _reject_private_mailbox_path_inside_root(*, mailbox_root: Path, mailbox_path: Path) -> None:
    """Reject symlink-backed mailbox paths that resolve inside the shared root."""

    try:
        mailbox_path.resolve().relative_to(mailbox_root.resolve())
    except ValueError:
        return
    raise ManagedMailboxOperationError(
        "symlink-backed mailbox registrations require a concrete mailbox directory "
        "outside the shared mailbox root"
    )


def _registration_matches_request(
    registration: MailboxRegistration,
    *,
    request: RegisterMailboxRequest,
    desired_mailbox_path: Path,
    desired_entry_path: Path,
) -> bool:
    """Return whether a registration matches a join request semantically."""

    return (
        registration.address == request.address
        and registration.owner_principal_id == request.owner_principal_id
        and registration.mailbox_kind == request.mailbox_kind
        and registration.mailbox_path == desired_mailbox_path
        and registration.mailbox_entry_path == desired_entry_path
    )


def _restore_registration_artifact(
    *,
    registration: MailboxRegistration,
    desired_mailbox_path: Path,
    desired_entry_path: Path,
) -> None:
    """Ensure the filesystem artifact for a reactivated registration exists."""

    _create_requested_artifact(
        mailbox_kind=registration.mailbox_kind,
        desired_mailbox_path=desired_mailbox_path,
        desired_entry_path=desired_entry_path,
    )


def _create_requested_artifact(
    *,
    mailbox_kind: str,
    desired_mailbox_path: Path,
    desired_entry_path: Path,
) -> None:
    """Create or validate the filesystem artifact for a new active registration."""

    if mailbox_kind == "in_root":
        if desired_entry_path.exists() and not desired_entry_path.is_dir():
            raise ManagedMailboxOperationError(
                f"mailbox entry already exists and is not a directory: {desired_entry_path}"
            )
        if desired_entry_path.is_symlink():
            raise ManagedMailboxOperationError(
                f"mailbox entry already exists as a symlink: {desired_entry_path}"
            )
        _ensure_mailbox_placeholder_dirs(desired_entry_path)
        return

    desired_mailbox_path.mkdir(parents=True, exist_ok=True)
    _ensure_mailbox_placeholder_dirs(desired_mailbox_path)
    if desired_entry_path.is_symlink():
        if desired_entry_path.resolve() != desired_mailbox_path:
            raise ManagedMailboxOperationError(
                f"mailbox symlink points to a different target: {desired_entry_path}"
            )
        return
    if desired_entry_path.exists():
        raise ManagedMailboxOperationError(
            f"mailbox entry already exists and is not a symlink: {desired_entry_path}"
        )
    desired_entry_path.parent.mkdir(parents=True, exist_ok=True)
    desired_entry_path.symlink_to(desired_mailbox_path)


def _remove_registration_artifact(registration: MailboxRegistration) -> None:
    """Remove one shared-root mailbox artifact without touching canonical messages."""

    if registration.mailbox_kind == "symlink":
        registration.mailbox_entry_path.unlink(missing_ok=True)
        return
    if registration.mailbox_entry_path.exists():
        shutil.rmtree(registration.mailbox_entry_path)


def _remove_untracked_artifact(entry_path: Path) -> None:
    """Remove one untracked mailbox artifact occupying an address slot."""

    if entry_path.is_symlink() or entry_path.is_file():
        entry_path.unlink(missing_ok=True)
        return
    if entry_path.exists():
        shutil.rmtree(entry_path)


def _stash_registration_artifact(
    *,
    paths: FilesystemMailboxPaths,
    registration: MailboxRegistration,
) -> tuple[Path, Path]:
    """Rename one mailbox artifact into a stashed historical entry."""

    suffix = uuid4().hex
    stashed_entry_path = paths.stashed_mailbox_entry_path(registration.address, suffix)
    while stashed_entry_path.exists() or stashed_entry_path.is_symlink():
        suffix = uuid4().hex
        stashed_entry_path = paths.stashed_mailbox_entry_path(registration.address, suffix)

    registration.mailbox_entry_path.replace(stashed_entry_path)
    stashed_mailbox_path = (
        stashed_entry_path if registration.mailbox_kind == "in_root" else registration.mailbox_path
    )
    return stashed_entry_path, stashed_mailbox_path


def _stash_untracked_artifact(
    paths: FilesystemMailboxPaths,
    entry_path: Path,
    address: str,
) -> Path:
    """Rename one untracked mailbox artifact aside to free the active address slot."""

    suffix = uuid4().hex
    stashed_entry_path = paths.stashed_mailbox_entry_path(address, suffix)
    while stashed_entry_path.exists() or stashed_entry_path.is_symlink():
        suffix = uuid4().hex
        stashed_entry_path = paths.stashed_mailbox_entry_path(address, suffix)
    entry_path.replace(stashed_entry_path)
    return stashed_entry_path


def _insert_registration(
    connection: sqlite3.Connection,
    *,
    registration_id: str,
    request: RegisterMailboxRequest,
    mailbox_path: Path,
    mailbox_entry_path: Path,
    status: str,
    deactivated_at_utc: str | None,
    replaced_by_registration_id: str | None,
) -> None:
    """Insert one registration row."""

    connection.execute(
        """
        INSERT INTO mailbox_registrations (
            registration_id,
            address,
            owner_principal_id,
            status,
            mailbox_kind,
            mailbox_path,
            mailbox_entry_path,
            display_name,
            manifest_path_hint,
            role,
            created_at_utc,
            deactivated_at_utc,
            replaced_by_registration_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            registration_id,
            request.address,
            request.owner_principal_id,
            status,
            request.mailbox_kind,
            str(mailbox_path),
            str(mailbox_entry_path),
            request.display_name,
            request.manifest_path_hint,
            request.role,
            _timestamp_utc(),
            deactivated_at_utc,
            replaced_by_registration_id,
        ),
    )


def _update_registration_metadata(
    connection: sqlite3.Connection,
    registration_id: str,
    request: RegisterMailboxRequest,
) -> None:
    """Refresh mutable metadata for a matching registration."""

    connection.execute(
        """
        UPDATE mailbox_registrations
        SET
            display_name = ?,
            manifest_path_hint = ?,
            role = ?
        WHERE registration_id = ?
        """,
        (
            request.display_name,
            request.manifest_path_hint,
            request.role,
            registration_id,
        ),
    )


def _reactivate_registration(
    connection: sqlite3.Connection,
    registration_id: str,
    request: RegisterMailboxRequest,
) -> None:
    """Reactivate an inactive registration."""

    connection.execute(
        """
        UPDATE mailbox_registrations
        SET
            status = 'active',
            display_name = ?,
            manifest_path_hint = ?,
            role = ?,
            deactivated_at_utc = NULL,
            replaced_by_registration_id = NULL
        WHERE registration_id = ?
        """,
        (
            request.display_name,
            request.manifest_path_hint,
            request.role,
            registration_id,
        ),
    )


def _mark_registration_stashed(
    connection: sqlite3.Connection,
    *,
    registration: MailboxRegistration,
    stashed_entry_path: Path,
    stashed_mailbox_path: Path,
) -> None:
    """Persist stashed replacement state for one prior registration."""

    connection.execute(
        """
        UPDATE mailbox_registrations
        SET
            status = 'stashed',
            mailbox_path = ?,
            mailbox_entry_path = ?,
            deactivated_at_utc = COALESCE(deactivated_at_utc, ?)
        WHERE registration_id = ?
        """,
        (
            str(stashed_mailbox_path),
            str(stashed_entry_path),
            _timestamp_utc(),
            registration.registration_id,
        ),
    )


def _mark_registration_replaced(
    connection: sqlite3.Connection,
    *,
    registration: MailboxRegistration,
) -> None:
    """Persist replacement metadata for a force-removed registration."""

    connection.execute(
        """
        UPDATE mailbox_registrations
        SET
            status = 'inactive',
            deactivated_at_utc = COALESCE(deactivated_at_utc, ?)
        WHERE registration_id = ?
        """,
        (
            _timestamp_utc(),
            registration.registration_id,
        ),
    )


def _set_replaced_by_registration_id(
    connection: sqlite3.Connection,
    *,
    registration_id: str,
    replacement_registration_id: str,
) -> None:
    """Record which later registration replaced one historical row."""

    connection.execute(
        """
        UPDATE mailbox_registrations
        SET replaced_by_registration_id = ?
        WHERE registration_id = ?
        """,
        (replacement_registration_id, registration_id),
    )


def _mark_registration_inactive(connection: sqlite3.Connection, registration_id: str) -> None:
    """Deactivate one active registration while preserving its mailbox artifacts."""

    connection.execute(
        """
        UPDATE mailbox_registrations
        SET
            status = 'inactive',
            deactivated_at_utc = COALESCE(deactivated_at_utc, ?)
        WHERE registration_id = ?
        """,
        (_timestamp_utc(), registration_id),
    )


def _purge_registration_state(connection: sqlite3.Connection, registration_id: str) -> None:
    """Delete registration-scoped projections and mutable state."""

    connection.execute(
        "DELETE FROM mailbox_projections WHERE registration_id = ?",
        (registration_id,),
    )
    connection.execute(
        "DELETE FROM mailbox_state WHERE registration_id = ?",
        (registration_id,),
    )


def _load_active_registrations(
    connection: sqlite3.Connection,
    addresses: Sequence[str],
) -> dict[str, MailboxRegistration]:
    """Load active registrations keyed by address."""

    if not addresses:
        return {}
    placeholders = ", ".join("?" for _ in addresses)
    rows = connection.execute(
        f"""
        SELECT
            registration_id,
            address,
            owner_principal_id,
            status,
            mailbox_kind,
            mailbox_path,
            mailbox_entry_path,
            display_name,
            manifest_path_hint,
            role,
            created_at_utc,
            deactivated_at_utc,
            replaced_by_registration_id
        FROM mailbox_registrations
        WHERE address IN ({placeholders}) AND status = 'active'
        """,
        tuple(addresses),
    ).fetchall()
    return {registration.address: registration for registration in _rows_to_registrations(rows)}


def _load_active_registration(
    connection: sqlite3.Connection,
    *,
    address: str,
) -> MailboxRegistration | None:
    """Load the active registration for one address."""

    rows = connection.execute(
        """
        SELECT
            registration_id,
            address,
            owner_principal_id,
            status,
            mailbox_kind,
            mailbox_path,
            mailbox_entry_path,
            display_name,
            manifest_path_hint,
            role,
            created_at_utc,
            deactivated_at_utc,
            replaced_by_registration_id
        FROM mailbox_registrations
        WHERE address = ? AND status = 'active'
        """,
        (address,),
    ).fetchall()
    if not rows:
        return None
    return _rows_to_registrations(rows)[0]


def _load_active_registration_by_mailbox_path(
    connection: sqlite3.Connection,
    *,
    mailbox_path: Path,
) -> MailboxRegistration | None:
    """Load the active registration that currently owns one concrete mailbox path."""

    rows = connection.execute(
        """
        SELECT
            registration_id,
            address,
            owner_principal_id,
            status,
            mailbox_kind,
            mailbox_path,
            mailbox_entry_path,
            display_name,
            manifest_path_hint,
            role,
            created_at_utc,
            deactivated_at_utc,
            replaced_by_registration_id
        FROM mailbox_registrations
        WHERE mailbox_path = ? AND status = 'active'
        ORDER BY created_at_utc DESC, registration_id DESC
        LIMIT 1
        """,
        (str(mailbox_path),),
    ).fetchall()
    if not rows:
        return None
    return _rows_to_registrations(rows)[0]


def _load_occupying_registration(
    connection: sqlite3.Connection,
    *,
    mailbox_entry_path: Path,
) -> MailboxRegistration | None:
    """Load the newest registration that still claims one mailbox entry path."""

    rows = connection.execute(
        """
        SELECT
            registration_id,
            address,
            owner_principal_id,
            status,
            mailbox_kind,
            mailbox_path,
            mailbox_entry_path,
            display_name,
            manifest_path_hint,
            role,
            created_at_utc,
            deactivated_at_utc,
            replaced_by_registration_id
        FROM mailbox_registrations
        WHERE mailbox_entry_path = ?
        ORDER BY created_at_utc DESC, registration_id DESC
        LIMIT 1
        """,
        (str(mailbox_entry_path),),
    ).fetchall()
    if not rows:
        return None
    return _rows_to_registrations(rows)[0]


def _rows_to_registrations(rows: Sequence[tuple[object, ...]]) -> list[MailboxRegistration]:
    """Convert SQLite rows into registration records."""

    return [
        MailboxRegistration(
            registration_id=str(row[0]),
            address=str(row[1]),
            owner_principal_id=str(row[2]),
            status=str(row[3]),
            mailbox_kind=str(row[4]),
            mailbox_path=Path(str(row[5])),
            mailbox_entry_path=Path(str(row[6])),
            display_name=None if row[7] is None else str(row[7]),
            manifest_path_hint=None if row[8] is None else str(row[8]),
            role=None if row[9] is None else str(row[9]),
            created_at_utc=str(row[10]),
            deactivated_at_utc=None if row[11] is None else str(row[11]),
            replaced_by_registration_id=None if row[12] is None else str(row[12]),
        )
        for row in rows
    ]


def _validate_active_registration(registration: MailboxRegistration) -> None:
    """Validate the filesystem artifact for an active registration."""

    if registration.status != "active":
        raise ManagedMailboxOperationError(
            f"registration `{registration.registration_id}` is not active"
        )
    _ensure_artifact_for_registration(registration)


def _ensure_artifact_for_registration(registration: MailboxRegistration) -> None:
    """Validate the concrete path for one registration."""

    if registration.mailbox_kind == "symlink":
        if not registration.mailbox_entry_path.is_symlink():
            raise ManagedMailboxOperationError(
                f"symlink registration missing for `{registration.address}`"
            )
    elif registration.mailbox_kind != "in_root":
        raise ManagedMailboxOperationError(
            f"unsupported mailbox kind `{registration.mailbox_kind}`"
        )

    if not registration.mailbox_path.exists() or not registration.mailbox_path.is_dir():
        raise ManagedMailboxOperationError(
            f"invalid mailbox registration for `{registration.address}`: {registration.mailbox_path}"
        )
    for directory_name in _MAILBOX_PLACEHOLDER_DIRS:
        if not (registration.mailbox_path / directory_name).is_dir():
            raise ManagedMailboxOperationError(
                f"mailbox registration for `{registration.address}` is missing `{directory_name}/`"
            )
    initialize_mailbox_local_sqlite_schema(registration.local_sqlite_path)


def _build_projection_targets(
    *,
    sender_registration: MailboxRegistration,
    recipient_principals: Sequence[ManagedPrincipal],
    recipient_registrations: dict[str, MailboxRegistration],
    message_id: str,
) -> list[Path]:
    """Compute inbox and sent projection targets for a delivery."""

    targets: list[Path] = []
    targets.append(sender_registration.mailbox_path / "sent" / f"{message_id}.md")
    for principal in recipient_principals:
        registration = recipient_registrations[principal.address]
        targets.append(registration.mailbox_path / "inbox" / f"{message_id}.md")
    return targets


def _create_projection_symlink(projection_path: Path, canonical_path: Path) -> None:
    """Create one mailbox projection symlink."""

    if projection_path.exists() or projection_path.is_symlink():
        raise ManagedMailboxOperationError(f"projection already exists: {projection_path}")
    projection_path.symlink_to(canonical_path)


def _insert_message_record(
    *,
    connection: sqlite3.Connection,
    request: DeliveryRequest,
    canonical_path: Path,
    sender_registration_id: str | None,
) -> None:
    """Insert the canonical message row."""

    connection.execute(
        """
        INSERT INTO messages (
            message_id,
            thread_id,
            in_reply_to,
            created_at_utc,
            canonical_path,
            subject,
            body_markdown,
            headers_json,
            sender_principal_id,
            sender_address,
            sender_display_name,
            sender_manifest_path_hint,
            sender_role,
            sender_registration_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request.message_id,
            request.thread_id,
            request.in_reply_to,
            request.created_at_utc,
            str(canonical_path),
            request.subject,
            canonical_path.read_text(encoding="utf-8"),
            json.dumps(request.headers, sort_keys=True),
            request.sender.principal_id,
            request.sender.address,
            request.sender.display_name,
            request.sender.manifest_path_hint,
            request.sender.role,
            sender_registration_id,
        ),
    )


def _insert_recipient_records(
    *,
    connection: sqlite3.Connection,
    request: DeliveryRequest,
    recipient_registrations: dict[str, MailboxRegistration],
) -> None:
    """Insert canonical recipient snapshot rows."""

    ordinal = 0
    for recipient_kind, principals in (("to", request.to), ("cc", request.cc)):
        for principal in principals:
            registration = recipient_registrations.get(principal.address)
            connection.execute(
                """
                INSERT INTO message_recipients (
                    message_id,
                    recipient_kind,
                    ordinal,
                    address,
                    owner_principal_id,
                    display_name,
                    manifest_path_hint,
                    role,
                    delivered_registration_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.message_id,
                    recipient_kind,
                    ordinal,
                    principal.address,
                    principal.principal_id,
                    principal.display_name,
                    principal.manifest_path_hint,
                    principal.role,
                    None if registration is None else registration.registration_id,
                ),
            )
            ordinal += 1


def _insert_attachment_records(connection: sqlite3.Connection, request: DeliveryRequest) -> None:
    """Insert attachment metadata rows."""

    for ordinal, attachment in enumerate(request.attachments):
        connection.execute(
            """
            INSERT INTO attachments (
                attachment_id,
                kind,
                locator,
                media_type,
                sha256,
                size_bytes,
                label
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attachment.attachment_id,
                attachment.kind,
                attachment.path,
                attachment.media_type,
                attachment.sha256,
                attachment.size_bytes,
                attachment.label,
            ),
        )
        connection.execute(
            """
            INSERT INTO message_attachments (
                message_id,
                attachment_id,
                ordinal
            )
            VALUES (?, ?, ?)
            """,
            (request.message_id, attachment.attachment_id, ordinal),
        )


def _insert_projection_records(
    *,
    connection: sqlite3.Connection,
    sender_registration: MailboxRegistration,
    recipient_principals: Sequence[ManagedPrincipal],
    recipient_registrations: dict[str, MailboxRegistration],
    projection_paths: Sequence[Path],
    message_id: str,
) -> None:
    """Insert projection catalog rows."""

    connection.execute(
        """
        INSERT INTO mailbox_projections (
            registration_id,
            message_id,
            folder_name,
            projection_path
        )
        VALUES (?, ?, ?, ?)
        """,
        (sender_registration.registration_id, message_id, "sent", str(projection_paths[0])),
    )
    for principal, projection_path in zip(recipient_principals, projection_paths[1:], strict=True):
        registration = recipient_registrations[principal.address]
        connection.execute(
            """
            INSERT INTO mailbox_projections (
                registration_id,
                message_id,
                folder_name,
                projection_path
            )
            VALUES (?, ?, ?, ?)
            """,
            (registration.registration_id, message_id, "inbox", str(projection_path)),
        )


def _insert_mailbox_state_records(
    *,
    sender_registration: MailboxRegistration,
    recipient_principals: Sequence[ManagedPrincipal],
    recipient_registrations: dict[str, MailboxRegistration],
    message_id: str,
    thread_id: str,
    created_at_utc: str,
    subject: str,
) -> None:
    """Insert deterministic default mailbox-local state rows."""

    recipient_registration_ids = {
        recipient_registrations[principal.address].registration_id
        for principal in recipient_principals
    }
    affected_registration_ids = {
        sender_registration.registration_id,
        *(
            recipient_registrations[principal.address].registration_id
            for principal in recipient_principals
        ),
    }
    registrations_by_id = {
        sender_registration.registration_id: sender_registration,
        **{
            registration.registration_id: registration
            for registration in recipient_registrations.values()
        },
    }
    for registration_id in sorted(affected_registration_ids):
        is_recipient = registration_id in recipient_registration_ids
        registration = registrations_by_id[registration_id]
        with _open_local_mailbox_connection(registration) as local_connection:
            _insert_local_message_state_row(
                connection=local_connection,
                message_id=message_id,
                thread_id=thread_id,
                created_at_utc=created_at_utc,
                subject=subject,
                is_read=not is_recipient,
                is_answered=False,
                is_starred=False,
                is_archived=False,
                is_deleted=False,
                box_name="inbox" if is_recipient else "sent",
            )
            _recompute_local_thread_summary(
                connection=local_connection,
                thread_id=thread_id,
            )


def _recompute_thread_summary(connection: sqlite3.Connection, thread_id: str) -> None:
    """Recompute shared structural thread-summary state."""

    latest_row = connection.execute(
        """
        SELECT message_id, created_at_utc, subject
        FROM messages
        WHERE thread_id = ?
        ORDER BY created_at_utc DESC, message_id DESC
        LIMIT 1
        """,
        (thread_id,),
    ).fetchone()
    if latest_row is None:
        return

    connection.execute(
        """
        INSERT INTO thread_summaries (
            thread_id,
            normalized_subject,
            latest_message_id,
            latest_message_created_at_utc,
            unread_count
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(thread_id) DO UPDATE SET
            normalized_subject = excluded.normalized_subject,
            latest_message_id = excluded.latest_message_id,
            latest_message_created_at_utc = excluded.latest_message_created_at_utc,
            unread_count = excluded.unread_count
        """,
        (
            thread_id,
            str(latest_row[2]).strip().lower(),
            str(latest_row[0]),
            str(latest_row[1]),
            0,
        ),
    )


@contextmanager
def _acquired_lock_set(
    paths: FilesystemMailboxPaths,
    addresses: Sequence[str],
    *,
    timeout_seconds: float,
) -> Iterator[None]:
    """Acquire address locks in lexicographic order, then the shared index lock."""

    lock_paths = [paths.address_lock_path(address) for address in sorted(set(addresses))]
    lock_paths.append(paths.locks_dir / "index.lock")
    acquired_paths: list[Path] = []
    try:
        for lock_path in lock_paths:
            _acquire_lock_file(lock_path, timeout_seconds=timeout_seconds)
            acquired_paths.append(lock_path)
        yield
    finally:
        for lock_path in reversed(acquired_paths):
            lock_path.unlink(missing_ok=True)


def _acquire_lock_file(lock_path: Path, *, timeout_seconds: float) -> None:
    """Acquire one lock file with bounded waiting."""

    deadline = time.monotonic() + timeout_seconds
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            with lock_path.open("x", encoding="utf-8") as handle:
                handle.write(f"pid={os.getpid()} acquired_at_utc={datetime.now(UTC).isoformat()}\n")
            return
        except FileExistsError as exc:
            if time.monotonic() >= deadline:
                raise ManagedMailboxOperationError(
                    f"timed out acquiring lock: {lock_path}"
                ) from exc
            time.sleep(0.05)


def _unique_principals(principals: Sequence[ManagedPrincipal]) -> tuple[ManagedPrincipal, ...]:
    """Deduplicate principals by address while preserving the first-seen metadata."""

    ordered: dict[str, ManagedPrincipal] = {}
    for principal in principals:
        existing = ordered.get(principal.address)
        if existing is not None and existing.principal_id != principal.principal_id:
            raise ManagedMailboxOperationError(
                f"conflicting owners for address `{principal.address}`"
            )
        ordered.setdefault(principal.address, principal)
    return tuple(ordered.values())


def _discover_mailbox_paths(mailboxes_dir: Path) -> list[_DiscoveredMailboxArtifact]:
    """Discover mailbox registration paths from the mailboxes directory."""

    discovered: list[_DiscoveredMailboxArtifact] = []
    if not mailboxes_dir.exists():
        return discovered

    for entry in sorted(mailboxes_dir.iterdir(), key=lambda path: path.name):
        parsed = _parse_mailbox_entry_name(entry.name)
        if parsed is None:
            raise ManagedMailboxOperationError(
                f"unsupported mailbox entry `{entry.name}`; delete and re-bootstrap the mailbox root"
            )
        address, status = parsed
        mailbox_kind = "symlink" if entry.is_symlink() else "in_root"
        mailbox_path = entry.resolve() if entry.is_symlink() else entry
        if mailbox_path.exists() and mailbox_path.is_dir():
            _ensure_mailbox_placeholder_dirs(mailbox_path)
        discovered.append(
            _DiscoveredMailboxArtifact(
                address=address,
                status=status,
                mailbox_kind=mailbox_kind,
                mailbox_path=mailbox_path,
                mailbox_entry_path=entry,
            )
        )
    return discovered


def _load_recovery_messages(messages_dir: Path) -> list[_RecoveredMessageDocument]:
    """Load and validate canonical message documents for repair."""

    if not messages_dir.exists():
        return []

    recovered_messages: list[_RecoveredMessageDocument] = []
    for canonical_path in sorted(messages_dir.rglob("*.md")):
        document_text = canonical_path.read_text(encoding="utf-8")
        try:
            message = parse_message_document(document_text)
        except Exception as exc:
            raise ManagedMailboxOperationError(
                f"invalid canonical mailbox message `{canonical_path}`: {exc}"
            ) from exc
        expected_filename = f"{message.message_id}.md"
        if canonical_path.name != expected_filename:
            raise ManagedMailboxOperationError(
                f"canonical mailbox message filename does not match message_id: {canonical_path}"
            )
        expected_date_dir = message.created_at_utc[:10]
        if canonical_path.parent.name != expected_date_dir:
            raise ManagedMailboxOperationError(
                f"canonical mailbox message date directory does not match created_at_utc: {canonical_path}"
            )
        recovered_messages.append(
            _RecoveredMessageDocument(
                canonical_path=canonical_path,
                document_text=document_text,
                message=message,
            )
        )

    recovered_messages.sort(
        key=lambda item: (item.message.created_at_utc, item.message.message_id),
    )
    return recovered_messages


def _snapshot_existing_index(sqlite_path: Path) -> _IndexSnapshot:
    """Snapshot recoverable registration and structural routing rows from an existing index."""

    if not sqlite_path.exists():
        return _IndexSnapshot(
            registrations={},
            sender_registration_ids={},
            recipient_registration_ids={},
            backup_path=None,
        )

    try:
        with sqlite3.connect(sqlite_path) as connection:
            registration_rows = connection.execute(
                """
                SELECT
                    registration_id,
                    address,
                    owner_principal_id,
                    status,
                    mailbox_kind,
                    mailbox_path,
                    mailbox_entry_path,
                    display_name,
                    manifest_path_hint,
                    role,
                    created_at_utc,
                    deactivated_at_utc,
                    replaced_by_registration_id
                FROM mailbox_registrations
                """
            ).fetchall()
            sender_rows = connection.execute(
                "SELECT message_id, sender_registration_id FROM messages"
            ).fetchall()
            recipient_rows = connection.execute(
                """
                SELECT
                    message_id,
                    recipient_kind,
                    ordinal,
                    delivered_registration_id
                FROM message_recipients
                """
            ).fetchall()
    except sqlite3.DatabaseError:
        backup_path = _backup_replaced_index(sqlite_path, suffix="unusable")
        return _IndexSnapshot(
            registrations={},
            sender_registration_ids={},
            recipient_registration_ids={},
            backup_path=backup_path,
        )

    registrations = {
        registration.registration_id: registration
        for registration in _rows_to_registrations(registration_rows)
    }
    sender_registration_ids = {
        str(row[0]): None if row[1] is None else str(row[1]) for row in sender_rows
    }
    recipient_registration_ids = {
        (str(row[0]), str(row[1]), int(row[2])): None if row[3] is None else str(row[3])
        for row in recipient_rows
    }
    sqlite_path.unlink(missing_ok=True)
    return _IndexSnapshot(
        registrations=registrations,
        sender_registration_ids=sender_registration_ids,
        recipient_registration_ids=recipient_registration_ids,
        backup_path=None,
    )


def _recover_registrations(
    *,
    connection: sqlite3.Connection,
    discovered_mailboxes: Sequence[_DiscoveredMailboxArtifact],
    snapshot: _IndexSnapshot,
    recovered_messages: Sequence[_RecoveredMessageDocument],
) -> dict[str, MailboxRegistration]:
    """Recover registration rows from current mailbox artifacts plus snapshot state."""

    address_hints = _address_hints_from_history(snapshot.registrations, recovered_messages)
    recovered: dict[str, MailboxRegistration] = {}
    matched_snapshot_ids: set[str] = set()
    discovered_active_addresses = {
        artifact.address for artifact in discovered_mailboxes if artifact.status == "active"
    }

    for artifact in discovered_mailboxes:
        matching_snapshot = _find_matching_snapshot_registration(
            artifact=artifact,
            snapshot=snapshot,
            matched_snapshot_ids=matched_snapshot_ids,
        )
        if matching_snapshot is not None:
            matched_snapshot_ids.add(matching_snapshot.registration_id)
            registration = MailboxRegistration(
                registration_id=matching_snapshot.registration_id,
                address=artifact.address,
                owner_principal_id=matching_snapshot.owner_principal_id,
                status=artifact.status,
                mailbox_kind=artifact.mailbox_kind,
                mailbox_path=artifact.mailbox_path,
                mailbox_entry_path=artifact.mailbox_entry_path,
                display_name=matching_snapshot.display_name,
                manifest_path_hint=matching_snapshot.manifest_path_hint,
                role=matching_snapshot.role,
                created_at_utc=matching_snapshot.created_at_utc,
                deactivated_at_utc=(
                    None if artifact.status == "active" else matching_snapshot.deactivated_at_utc
                ),
                replaced_by_registration_id=matching_snapshot.replaced_by_registration_id,
            )
        else:
            hint = address_hints.get(artifact.address)
            registration = MailboxRegistration(
                registration_id=_generate_registration_id(),
                address=artifact.address,
                owner_principal_id=(
                    hint.principal_id if hint is not None else artifact.address.split("@", 1)[0]
                ),
                status=artifact.status,
                mailbox_kind=artifact.mailbox_kind,
                mailbox_path=artifact.mailbox_path,
                mailbox_entry_path=artifact.mailbox_entry_path,
                display_name=None if hint is None else hint.display_name,
                manifest_path_hint=None if hint is None else hint.manifest_path_hint,
                role=None if hint is None else hint.role,
                created_at_utc=_timestamp_utc(),
                deactivated_at_utc=None if artifact.status == "active" else _timestamp_utc(),
                replaced_by_registration_id=None,
            )
        recovered[registration.registration_id] = registration

    for registration_id, snapshot_registration in sorted(snapshot.registrations.items()):
        if registration_id in matched_snapshot_ids:
            continue
        status = snapshot_registration.status
        deactivated_at_utc = snapshot_registration.deactivated_at_utc
        if status == "active" and snapshot_registration.address not in discovered_active_addresses:
            status = "inactive"
            if deactivated_at_utc is None:
                deactivated_at_utc = _timestamp_utc()
        recovered[registration_id] = MailboxRegistration(
            registration_id=snapshot_registration.registration_id,
            address=snapshot_registration.address,
            owner_principal_id=snapshot_registration.owner_principal_id,
            status=status,
            mailbox_kind=snapshot_registration.mailbox_kind,
            mailbox_path=snapshot_registration.mailbox_path,
            mailbox_entry_path=snapshot_registration.mailbox_entry_path,
            display_name=snapshot_registration.display_name,
            manifest_path_hint=snapshot_registration.manifest_path_hint,
            role=snapshot_registration.role,
            created_at_utc=snapshot_registration.created_at_utc,
            deactivated_at_utc=deactivated_at_utc,
            replaced_by_registration_id=snapshot_registration.replaced_by_registration_id,
        )

    for registration in sorted(
        recovered.values(), key=lambda item: (item.created_at_utc, item.registration_id)
    ):
        connection.execute(
            """
            INSERT INTO mailbox_registrations (
                registration_id,
                address,
                owner_principal_id,
                status,
                mailbox_kind,
                mailbox_path,
                mailbox_entry_path,
                display_name,
                manifest_path_hint,
                role,
                created_at_utc,
                deactivated_at_utc,
                replaced_by_registration_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                registration.registration_id,
                registration.address,
                registration.owner_principal_id,
                registration.status,
                registration.mailbox_kind,
                str(registration.mailbox_path),
                str(registration.mailbox_entry_path),
                registration.display_name,
                registration.manifest_path_hint,
                registration.role,
                registration.created_at_utc,
                registration.deactivated_at_utc,
                registration.replaced_by_registration_id,
            ),
        )
    return recovered


def _address_hints_from_history(
    registrations: dict[str, MailboxRegistration],
    recovered_messages: Sequence[_RecoveredMessageDocument],
) -> dict[str, ManagedPrincipal]:
    """Collect best-effort owner metadata by address from prior history."""

    hints: dict[str, ManagedPrincipal] = {}
    for registration in registrations.values():
        hints.setdefault(
            registration.address,
            ManagedPrincipal(
                principal_id=registration.owner_principal_id,
                address=registration.address,
                display_name=registration.display_name,
                manifest_path_hint=registration.manifest_path_hint,
                role=registration.role,
            ),
        )
    for recovered_message in recovered_messages:
        message = recovered_message.message
        for principal in (message.sender, *message.to, *message.cc):
            hints.setdefault(
                principal.address,
                ManagedPrincipal(
                    principal_id=principal.principal_id,
                    address=principal.address,
                    display_name=principal.display_name,
                    manifest_path_hint=principal.manifest_path_hint,
                    role=principal.role,
                ),
            )
    return hints


def _find_matching_snapshot_registration(
    *,
    artifact: _DiscoveredMailboxArtifact,
    snapshot: _IndexSnapshot,
    matched_snapshot_ids: set[str],
) -> MailboxRegistration | None:
    """Select the best snapshot registration for one discovered artifact."""

    candidates = [
        registration
        for registration in snapshot.registrations.values()
        if registration.registration_id not in matched_snapshot_ids
        and registration.address == artifact.address
        and registration.mailbox_kind == artifact.mailbox_kind
    ]
    for candidate in candidates:
        if candidate.mailbox_entry_path == artifact.mailbox_entry_path:
            return candidate
    for candidate in candidates:
        if candidate.status == artifact.status and candidate.mailbox_path == artifact.mailbox_path:
            return candidate
    return None


def _insert_recovered_message_record(
    *,
    connection: sqlite3.Connection,
    recovered_message: _RecoveredMessageDocument,
    sender_registration_id: str | None,
) -> None:
    """Insert one recovered canonical message row."""

    message = recovered_message.message
    connection.execute(
        """
        INSERT INTO messages (
            message_id,
            thread_id,
            in_reply_to,
            created_at_utc,
            canonical_path,
            subject,
            body_markdown,
            headers_json,
            sender_principal_id,
            sender_address,
            sender_display_name,
            sender_manifest_path_hint,
            sender_role,
            sender_registration_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            message.message_id,
            message.thread_id,
            message.in_reply_to,
            message.created_at_utc,
            str(recovered_message.canonical_path),
            message.subject,
            recovered_message.document_text,
            json.dumps(message.headers, sort_keys=True),
            message.sender.principal_id,
            message.sender.address,
            message.sender.display_name,
            message.sender.manifest_path_hint,
            message.sender.role,
            sender_registration_id,
        ),
    )


def _insert_recovered_recipient_records(
    *,
    connection: sqlite3.Connection,
    message: MailboxMessage,
    snapshot: _IndexSnapshot,
    registrations: dict[str, MailboxRegistration],
) -> list[str | None]:
    """Insert recovered recipient associations for one message."""

    ordinal = 0
    registration_ids: list[str | None] = []
    for recipient_kind, principals in (("to", message.to), ("cc", message.cc)):
        for principal in principals:
            binding_key = (message.message_id, recipient_kind, ordinal)
            delivered_registration_id = snapshot.recipient_registration_ids.get(binding_key)
            if delivered_registration_id is None:
                delivered_registration_id = _best_effort_registration_id(
                    registrations=registrations,
                    address=principal.address,
                    owner_principal_id=principal.principal_id,
                )
            connection.execute(
                """
                INSERT INTO message_recipients (
                    message_id,
                    recipient_kind,
                    ordinal,
                    address,
                    owner_principal_id,
                    display_name,
                    manifest_path_hint,
                    role,
                    delivered_registration_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    recipient_kind,
                    ordinal,
                    principal.address,
                    principal.principal_id,
                    principal.display_name,
                    principal.manifest_path_hint,
                    principal.role,
                    delivered_registration_id,
                ),
            )
            registration_ids.append(delivered_registration_id)
            ordinal += 1
    return registration_ids


def _insert_recovered_attachment_records(
    connection: sqlite3.Connection,
    message: MailboxMessage,
) -> None:
    """Insert recovered attachment metadata rows for one message."""

    for ordinal, attachment in enumerate(message.attachments):
        connection.execute(
            """
            INSERT INTO attachments (
                attachment_id,
                kind,
                locator,
                media_type,
                sha256,
                size_bytes,
                label
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attachment.attachment_id,
                attachment.kind,
                attachment.path,
                attachment.media_type,
                attachment.sha256,
                attachment.size_bytes,
                attachment.label,
            ),
        )
        connection.execute(
            """
            INSERT INTO message_attachments (
                message_id,
                attachment_id,
                ordinal
            )
            VALUES (?, ?, ?)
            """,
            (message.message_id, attachment.attachment_id, ordinal),
        )


def _repair_projection_records(
    *,
    connection: sqlite3.Connection,
    registrations: dict[str, MailboxRegistration],
    recovered_message: _RecoveredMessageDocument,
    sender_registration_id: str | None,
    recipient_registration_ids: Sequence[str | None],
) -> int:
    """Repair projection symlinks and rebuild the projection catalog for one message."""

    message = recovered_message.message
    projection_count = 0
    projection_specs: list[tuple[str | None, str]] = [(sender_registration_id, "sent")]
    projection_specs.extend(
        (registration_id, "inbox") for registration_id in recipient_registration_ids
    )

    for registration_id, folder_name in projection_specs:
        if registration_id is None:
            continue
        registration = registrations.get(registration_id)
        if registration is None or not registration.mailbox_path.exists():
            continue
        if not registration.mailbox_path.is_dir():
            raise ManagedMailboxOperationError(
                f"invalid recovered mailbox path for `{registration.address}`: {registration.mailbox_path}"
            )

        _ensure_mailbox_placeholder_dirs(registration.mailbox_path)
        projection_path = registration.mailbox_path / folder_name / f"{message.message_id}.md"
        if projection_path.is_symlink():
            if projection_path.resolve() != recovered_message.canonical_path:
                raise ManagedMailboxOperationError(
                    f"projection target mismatch for `{projection_path}`"
                )
        elif projection_path.exists():
            raise ManagedMailboxOperationError(
                f"projection path exists but is not a symlink: {projection_path}"
            )
        else:
            projection_path.symlink_to(recovered_message.canonical_path)

        connection.execute(
            """
            INSERT INTO mailbox_projections (
                registration_id,
                message_id,
                folder_name,
                projection_path
            )
            VALUES (?, ?, ?, ?)
            """,
            (registration_id, message.message_id, folder_name, str(projection_path)),
        )
        projection_count += 1

    return projection_count


def _insert_recovered_mailbox_state_records(
    *,
    registrations: dict[str, MailboxRegistration],
    message: MailboxMessage,
    sender_registration_id: str | None,
    recipient_registration_ids: Sequence[str | None],
) -> tuple[int, int]:
    """Insert deterministic default mailbox-local state rows for one recovered message."""

    restored_state_count = 0
    defaulted_state_count = 0
    delivered_recipient_ids = {
        registration_id
        for registration_id in recipient_registration_ids
        if registration_id is not None
    }
    affected_registration_ids = {
        registration_id for registration_id in recipient_registration_ids if registration_id
    }
    if sender_registration_id is not None:
        affected_registration_ids.add(sender_registration_id)
    for registration_id in sorted(affected_registration_ids):
        if registration_id not in registrations:
            continue
        is_recipient = registration_id in delivered_recipient_ids
        state_values = (
            not is_recipient,
            False,
            False,
            False,
            False,
            "inbox" if is_recipient else "sent",
        )
        defaulted_state_count += 1

        with _open_local_mailbox_connection(registrations[registration_id]) as local_connection:
            _insert_local_message_state_row(
                connection=local_connection,
                message_id=message.message_id,
                thread_id=message.thread_id,
                created_at_utc=message.created_at_utc,
                subject=message.subject,
                is_read=bool(state_values[0]),
                is_answered=bool(state_values[1]),
                is_starred=bool(state_values[2]),
                is_archived=bool(state_values[3]),
                is_deleted=bool(state_values[4]),
                box_name=str(state_values[5]),
            )

    return restored_state_count, defaulted_state_count


def _best_effort_registration_id(
    *,
    registrations: dict[str, MailboxRegistration],
    address: str,
    owner_principal_id: str,
) -> str | None:
    """Choose the best available registration id for historical repair."""

    candidates = [
        registration
        for registration in registrations.values()
        if registration.address == address and registration.owner_principal_id == owner_principal_id
    ]
    if not candidates:
        return None

    status_rank = {"active": 0, "inactive": 1, "stashed": 2}
    candidates.sort(
        key=lambda registration: (
            status_rank.get(registration.status, 99),
            registration.created_at_utc,
            registration.registration_id,
        ),
    )
    return candidates[0].registration_id


def _cleanup_staging_artifacts(staging_dir: Path, *, quarantine: bool) -> list[Path]:
    """Remove or quarantine orphaned staging artifacts."""

    if not staging_dir.exists():
        return []

    cleanup_results: list[Path] = []
    quarantine_root = staging_dir / "quarantine" / _timestamp_label()
    for staging_path in sorted(staging_dir.iterdir(), key=lambda path: path.name):
        if staging_path.name == "quarantine":
            continue
        if quarantine:
            quarantine_root.mkdir(parents=True, exist_ok=True)
            destination_path = _unique_destination_path(quarantine_root / staging_path.name)
            staging_path.replace(destination_path)
            cleanup_results.append(destination_path)
            continue

        if staging_path.is_dir():
            shutil.rmtree(staging_path)
        else:
            staging_path.unlink(missing_ok=True)
        cleanup_results.append(staging_path)
    return cleanup_results


def _backup_replaced_index(sqlite_path: Path, *, suffix: str) -> Path:
    """Move a replaced SQLite index aside using a timestamped suffix."""

    backup_path = sqlite_path.with_name(f"{sqlite_path.name}.{suffix}-{_timestamp_label()}.bak")
    sqlite_path.replace(backup_path)
    return backup_path


def _unique_destination_path(destination_path: Path) -> Path:
    """Return a unique destination path for staging quarantine artifacts."""

    if not destination_path.exists():
        return destination_path
    stem = destination_path.stem
    suffix = destination_path.suffix
    counter = 1
    while True:
        candidate = destination_path.with_name(f"{stem}-{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _timestamp_label() -> str:
    """Return a filesystem-friendly UTC timestamp label."""

    return datetime.now(UTC).replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")


def _timestamp_utc() -> str:
    """Return an RFC3339 UTC timestamp string with second precision."""

    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_registration_id() -> str:
    """Return a stable registration identifier."""

    return f"reg-{uuid4().hex}"


def _ensure_mailbox_placeholder_dirs(mailbox_path: Path) -> None:
    """Ensure the standard mailbox placeholder directories exist."""

    for directory_name in _MAILBOX_PLACEHOLDER_DIRS:
        (mailbox_path / directory_name).mkdir(parents=True, exist_ok=True)


def _parse_mailbox_entry_name(entry_name: str) -> tuple[str, str] | None:
    """Parse a mailbox directory entry name into `(address, status)`."""

    try:
        return (mailbox_address_path_segment(entry_name), "active")
    except Exception:
        match = _STASHED_ENTRY_RE.fullmatch(entry_name)
        if match is None:
            return None
        try:
            return (mailbox_address_path_segment(match.group("address")), "stashed")
        except Exception:
            return None
