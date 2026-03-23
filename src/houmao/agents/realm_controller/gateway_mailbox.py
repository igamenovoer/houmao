"""Gateway mailbox adapter protocol and transport implementations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import mimetypes
from pathlib import Path
import sqlite3
from typing import Protocol, Sequence
from uuid import uuid4

from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
    MailboxResolvedConfig,
    StalwartMailboxResolvedConfig,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayMailAttachmentUploadV1,
    GatewayMailStateResponseV1,
    GatewayMailStatusV1,
    GatewayMailboxAttachmentV1,
    GatewayMailboxMessageV1,
    GatewayMailboxParticipantV1,
)
from houmao.mailbox.filesystem import resolve_active_mailbox_local_sqlite_path
from houmao.mailbox.managed import (
    DeliveryRequest,
    ManagedAttachment,
    ManagedMailboxOperationError,
    ManagedPrincipal,
    StateUpdateRequest,
    deliver_message,
    update_mailbox_state,
)
from houmao.mailbox.protocol import (
    MailboxAttachment,
    MailboxMessage,
    MailboxPrincipal,
    parse_message_document,
    serialize_message_document,
)
from houmao.mailbox.stalwart import StalwartError, StalwartJmapClient


class GatewayMailboxError(RuntimeError):
    """Raised when a gateway mailbox adapter cannot satisfy a mailbox request."""


class GatewayMailboxAdapter(Protocol):
    """Shared gateway mailbox adapter for one manifest-backed session binding."""

    def status(self) -> GatewayMailStatusV1:
        """Return mailbox availability and identity metadata."""

    def check(
        self,
        *,
        unread_only: bool,
        limit: int | None,
        since: str | None,
    ) -> list[GatewayMailboxMessageV1]:
        """Return normalized mailbox messages for one check request."""

    def send(
        self,
        *,
        to_addresses: Sequence[str],
        cc_addresses: Sequence[str],
        subject: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
    ) -> GatewayMailboxMessageV1:
        """Send one new mailbox message and return the normalized delivered record."""

    def reply(
        self,
        *,
        message_ref: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
    ) -> GatewayMailboxMessageV1:
        """Reply to one existing message and return the normalized delivered record."""

    def update_read_state(
        self,
        *,
        message_ref: str,
        read: bool,
    ) -> GatewayMailStateResponseV1:
        """Apply one single-message read-state update by opaque shared reference."""


def build_gateway_mailbox_adapter(mailbox: MailboxResolvedConfig) -> GatewayMailboxAdapter:
    """Build a transport-specific mailbox adapter for one resolved binding."""

    if isinstance(mailbox, FilesystemMailboxResolvedConfig):
        return FilesystemGatewayMailboxAdapter(mailbox)
    return StalwartGatewayMailboxAdapter(mailbox)


@dataclass
class FilesystemGatewayMailboxAdapter:
    """Gateway adapter that exposes the filesystem mailbox transport."""

    m_mailbox: FilesystemMailboxResolvedConfig

    def status(self) -> GatewayMailStatusV1:
        return GatewayMailStatusV1(
            transport="filesystem",
            principal_id=self.m_mailbox.principal_id,
            address=self.m_mailbox.address,
            bindings_version=self.m_mailbox.bindings_version,
        )

    def check(
        self,
        *,
        unread_only: bool,
        limit: int | None,
        since: str | None,
    ) -> list[GatewayMailboxMessageV1]:
        local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
            self.m_mailbox.filesystem_root,
            address=self.m_mailbox.address,
        )
        shared_sqlite_path = (self.m_mailbox.filesystem_root / "index.sqlite").resolve()
        since_filter = _parse_optional_timestamp(since)
        try:
            with sqlite3.connect(shared_sqlite_path) as connection:
                connection.execute("ATTACH DATABASE ? AS local_mailbox", (str(local_sqlite_path),))
                rows = connection.execute(
                    """
                    SELECT
                        message.message_id,
                        message.thread_id,
                        message.created_at_utc,
                        message.subject,
                        message.canonical_path,
                        local_mailbox.message_state.is_read
                    FROM local_mailbox.message_state
                    JOIN messages AS message
                      ON message.message_id = local_mailbox.message_state.message_id
                    ORDER BY message.created_at_utc DESC, message.message_id DESC
                    """
                ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise GatewayMailboxError(
                f"filesystem mailbox state is unreadable for `{self.m_mailbox.address}`"
            ) from exc

        messages: list[GatewayMailboxMessageV1] = []
        for row in rows:
            created_at_utc = str(row[2])
            if since_filter is not None and _parse_timestamp(created_at_utc) < since_filter:
                continue
            unread = not bool(row[5])
            if unread_only and not unread:
                continue
            message = self._load_message_document(
                message_id=str(row[0]),
                canonical_path=Path(str(row[4])),
            )
            messages.append(self._message_to_model(message=message, unread=unread))
            if limit is not None and len(messages) >= limit:
                break
        return messages

    def send(
        self,
        *,
        to_addresses: Sequence[str],
        cc_addresses: Sequence[str],
        subject: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
    ) -> GatewayMailboxMessageV1:
        now = datetime.now(UTC)
        message_id = _generate_filesystem_message_id(now)
        created_at_utc = now.isoformat(timespec="seconds").replace("+00:00", "Z")
        request = self._build_delivery_request(
            message_id=message_id,
            thread_id=message_id,
            in_reply_to=None,
            references=(),
            created_at_utc=created_at_utc,
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            subject=subject,
            body_content=body_content,
            attachments=attachments,
        )
        try:
            deliver_message(self.m_mailbox.filesystem_root, request)
        except ManagedMailboxOperationError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        return self._message_to_model(
            message=self._load_message_document(
                message_id=message_id,
                canonical_path=self._canonical_message_path(
                    message_id=message_id, created_at_utc=created_at_utc
                ),
            ),
            unread=False,
        )

    def reply(
        self,
        *,
        message_ref: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
    ) -> GatewayMailboxMessageV1:
        parent_message_id = _require_prefixed_ref(message_ref, prefix="filesystem")
        parent_message = self._load_message_by_id(parent_message_id)
        reply_targets = parent_message.reply_to or [parent_message.sender]
        now = datetime.now(UTC)
        message_id = _generate_filesystem_message_id(now)
        created_at_utc = now.isoformat(timespec="seconds").replace("+00:00", "Z")
        subject = parent_message.subject
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        request = self._build_delivery_request(
            message_id=message_id,
            thread_id=parent_message.thread_id,
            in_reply_to=parent_message.message_id,
            references=(*parent_message.references, parent_message.message_id),
            created_at_utc=created_at_utc,
            to_addresses=[principal.address for principal in reply_targets],
            cc_addresses=(),
            subject=subject,
            body_content=body_content,
            attachments=attachments,
        )
        try:
            deliver_message(self.m_mailbox.filesystem_root, request)
        except ManagedMailboxOperationError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        return self._message_to_model(
            message=self._load_message_document(
                message_id=message_id,
                canonical_path=self._canonical_message_path(
                    message_id=message_id, created_at_utc=created_at_utc
                ),
            ),
            unread=False,
        )

    def update_read_state(
        self,
        *,
        message_ref: str,
        read: bool,
    ) -> GatewayMailStateResponseV1:
        message_id = _require_prefixed_ref(message_ref, prefix="filesystem")
        try:
            update_mailbox_state(
                self.m_mailbox.filesystem_root,
                StateUpdateRequest(
                    address=self.m_mailbox.address,
                    message_id=message_id,
                    read=read,
                ),
            )
        except ManagedMailboxOperationError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        return GatewayMailStateResponseV1(
            transport="filesystem",
            principal_id=self.m_mailbox.principal_id,
            address=self.m_mailbox.address,
            message_ref=f"filesystem:{message_id}",
            read=read,
        )

    def _build_delivery_request(
        self,
        *,
        message_id: str,
        thread_id: str,
        in_reply_to: str | None,
        references: Sequence[str],
        created_at_utc: str,
        to_addresses: Sequence[str],
        cc_addresses: Sequence[str],
        subject: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
    ) -> DeliveryRequest:
        staged_message_path = (
            self.m_mailbox.filesystem_root / "staging" / f"gateway-{uuid4().hex[:12]}.md"
        ).resolve()
        with sqlite3.connect(
            (self.m_mailbox.filesystem_root / "index.sqlite").resolve()
        ) as connection:
            to_principals = [
                self._managed_principal_for_address(connection=connection, address=address)
                for address in to_addresses
            ]
            cc_principals = [
                self._managed_principal_for_address(connection=connection, address=address)
                for address in cc_addresses
            ]
        request = DeliveryRequest(
            staged_message_path=staged_message_path,
            message_id=message_id,
            thread_id=thread_id,
            in_reply_to=in_reply_to,
            references=tuple(references),
            created_at_utc=created_at_utc,
            sender=ManagedPrincipal(
                principal_id=self.m_mailbox.principal_id,
                address=self.m_mailbox.address,
            ),
            to=tuple(to_principals),
            cc=tuple(cc_principals),
            reply_to=(),
            subject=subject,
            attachments=tuple(_managed_attachment_from_upload(item) for item in attachments),
            headers={},
        )
        self._write_staged_message(
            staged_message_path=staged_message_path, request=request, body_content=body_content
        )
        return request

    def _write_staged_message(
        self,
        *,
        staged_message_path: Path,
        request: DeliveryRequest,
        body_content: str,
    ) -> None:
        message = MailboxMessage.model_validate(
            {
                "message_id": request.message_id,
                "thread_id": request.thread_id,
                "in_reply_to": request.in_reply_to,
                "references": list(request.references),
                "created_at_utc": request.created_at_utc,
                "from": request.sender.to_mailbox_principal(),
                "to": [principal.to_mailbox_principal() for principal in request.to],
                "cc": [principal.to_mailbox_principal() for principal in request.cc],
                "reply_to": [principal.to_mailbox_principal() for principal in request.reply_to],
                "subject": request.subject,
                "body_markdown": body_content,
                "attachments": [
                    attachment.to_mailbox_attachment() for attachment in request.attachments
                ],
                "headers": dict(request.headers),
            }
        )
        staged_message_path.parent.mkdir(parents=True, exist_ok=True)
        staged_message_path.write_text(
            serialize_message_document(message),
            encoding="utf-8",
        )

    def _canonical_message_path(self, *, message_id: str, created_at_utc: str) -> Path:
        return (
            self.m_mailbox.filesystem_root / "messages" / created_at_utc[:10] / f"{message_id}.md"
        ).resolve()

    def _managed_principal_for_address(
        self,
        *,
        connection: sqlite3.Connection,
        address: str,
    ) -> ManagedPrincipal:
        row = connection.execute(
            """
            SELECT owner_principal_id
            FROM mailbox_registrations
            WHERE address = ? AND status = 'active'
            LIMIT 1
            """,
            (address,),
        ).fetchone()
        if row is None:
            raise GatewayMailboxError(
                f"filesystem mailbox recipient `{address}` does not have an active mailbox registration"
            )
        return ManagedPrincipal(
            principal_id=str(row[0]),
            address=address,
        )

    def _load_message_by_id(self, message_id: str) -> MailboxMessage:
        with sqlite3.connect(
            (self.m_mailbox.filesystem_root / "index.sqlite").resolve()
        ) as connection:
            row = connection.execute(
                "SELECT canonical_path FROM messages WHERE message_id = ?",
                (message_id,),
            ).fetchone()
        if row is None:
            raise GatewayMailboxError(f"filesystem mailbox message `{message_id}` was not found")
        return self._load_message_document(message_id=message_id, canonical_path=Path(str(row[0])))

    def _load_message_document(self, *, message_id: str, canonical_path: Path) -> MailboxMessage:
        try:
            document = canonical_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise GatewayMailboxError(
                f"filesystem mailbox canonical message `{message_id}` is unreadable: {canonical_path}"
            ) from exc
        try:
            return parse_message_document(document)
        except Exception as exc:
            raise GatewayMailboxError(
                f"filesystem mailbox canonical message `{message_id}` is invalid: {canonical_path}"
            ) from exc

    def _message_to_model(
        self, *, message: MailboxMessage, unread: bool | None
    ) -> GatewayMailboxMessageV1:
        return GatewayMailboxMessageV1(
            message_ref=f"filesystem:{message.message_id}",
            thread_ref=f"filesystem:{message.thread_id}",
            created_at_utc=message.created_at_utc,
            subject=message.subject,
            unread=unread,
            body_preview=_body_preview(message.body_markdown),
            body_text=message.body_markdown,
            sender=_participant_from_mailbox_principal(message.sender),
            to=[_participant_from_mailbox_principal(item) for item in message.to],
            cc=[_participant_from_mailbox_principal(item) for item in message.cc],
            reply_to=[_participant_from_mailbox_principal(item) for item in message.reply_to],
            attachments=[_attachment_from_mailbox_attachment(item) for item in message.attachments],
        )


@dataclass
class StalwartGatewayMailboxAdapter:
    """Gateway adapter that exposes the Stalwart-backed mailbox transport."""

    m_mailbox: StalwartMailboxResolvedConfig

    def status(self) -> GatewayMailStatusV1:
        self._client().status()
        return GatewayMailStatusV1(
            transport="stalwart",
            principal_id=self.m_mailbox.principal_id,
            address=self.m_mailbox.address,
            bindings_version=self.m_mailbox.bindings_version,
        )

    def check(
        self,
        *,
        unread_only: bool,
        limit: int | None,
        since: str | None,
    ) -> list[GatewayMailboxMessageV1]:
        try:
            rows = self._client().check(unread_only=unread_only, limit=limit, since=since)
        except StalwartError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        return [_stalwart_message_to_model(row) for row in rows]

    def send(
        self,
        *,
        to_addresses: Sequence[str],
        cc_addresses: Sequence[str],
        subject: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
    ) -> GatewayMailboxMessageV1:
        try:
            row = self._client().send(
                sender_address=self.m_mailbox.address,
                to_addresses=to_addresses,
                cc_addresses=cc_addresses,
                subject=subject,
                body_content=body_content,
                attachments=[Path(item.path).resolve() for item in attachments],
            )
        except StalwartError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        return _stalwart_message_to_model(row)

    def reply(
        self,
        *,
        message_ref: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
    ) -> GatewayMailboxMessageV1:
        try:
            row = self._client().reply(
                message_ref=_require_prefixed_ref(message_ref, prefix="stalwart"),
                sender_address=self.m_mailbox.address,
                body_content=body_content,
                attachments=[Path(item.path).resolve() for item in attachments],
            )
        except StalwartError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        return _stalwart_message_to_model(row)

    def update_read_state(
        self,
        *,
        message_ref: str,
        read: bool,
    ) -> GatewayMailStateResponseV1:
        try:
            payload = self._client().update_read_state(
                message_ref=_require_prefixed_ref(message_ref, prefix="stalwart"),
                read=read,
            )
        except StalwartError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        message_id = _require_string(payload, "id")
        unread = _require_boolean(payload, "unread")
        return GatewayMailStateResponseV1(
            transport="stalwart",
            principal_id=self.m_mailbox.principal_id,
            address=self.m_mailbox.address,
            message_ref=f"stalwart:{message_id}",
            read=not unread,
        )

    def _client(self) -> StalwartJmapClient:
        credential_file = self.m_mailbox.credential_file
        if credential_file is None:
            raise GatewayMailboxError(
                "stalwart mailbox binding is missing the session credential file"
            )
        return StalwartJmapClient(
            jmap_url=self.m_mailbox.jmap_url,
            login_identity=self.m_mailbox.login_identity,
            credential_file=credential_file,
        )


def _participant_from_mailbox_principal(principal: MailboxPrincipal) -> GatewayMailboxParticipantV1:
    return GatewayMailboxParticipantV1(
        address=principal.address,
        display_name=principal.display_name,
        principal_id=principal.principal_id,
    )


def _attachment_from_mailbox_attachment(
    attachment: MailboxAttachment,
) -> GatewayMailboxAttachmentV1:
    return GatewayMailboxAttachmentV1(
        attachment_id=attachment.attachment_id,
        kind=attachment.kind,
        media_type=attachment.media_type,
        locator=attachment.path,
        size_bytes=attachment.size_bytes,
        sha256=attachment.sha256,
        label=attachment.label,
    )


def _managed_attachment_from_upload(item: GatewayMailAttachmentUploadV1) -> ManagedAttachment:
    path = Path(item.path).resolve()
    if not path.is_file():
        raise GatewayMailboxError(f"attachment path does not exist or is not a file: {path}")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return ManagedAttachment(
        attachment_id=f"att-{uuid4().hex[:12]}",
        kind="path_ref",
        path=str(path),
        media_type=media_type,
        sha256=_sha256_file(path),
        size_bytes=path.stat().st_size,
        label=item.label or path.name,
    )


def _stalwart_message_to_model(payload: dict[str, object]) -> GatewayMailboxMessageV1:
    unread_value = payload.get("unread")
    normalized_unread: bool | None = unread_value if isinstance(unread_value, bool) else None
    return GatewayMailboxMessageV1(
        message_ref=f"stalwart:{_require_string(payload, 'id')}",
        thread_ref=(
            f"stalwart-thread:{payload['threadId']}"
            if isinstance(payload.get("threadId"), str) and str(payload.get("threadId")).strip()
            else None
        ),
        created_at_utc=_require_string(payload, "receivedAt"),
        subject=_require_string(payload, "subject"),
        unread=normalized_unread,
        body_preview=_optional_string(payload.get("preview")),
        body_text=_optional_string(payload.get("body")),
        sender=_participant_from_address_list(payload.get("from")),
        to=_participants_from_address_list(payload.get("to")),
        cc=_participants_from_address_list(payload.get("cc")),
        reply_to=_participants_from_address_list(payload.get("replyTo")),
        attachments=_attachments_from_stalwart_list(payload.get("attachments")),
    )


def _participant_from_address_list(value: object) -> GatewayMailboxParticipantV1:
    participants = _participants_from_address_list(value)
    if not participants:
        return GatewayMailboxParticipantV1(address="unknown@invalid.local")
    return participants[0]


def _participants_from_address_list(value: object) -> list[GatewayMailboxParticipantV1]:
    if not isinstance(value, list):
        return []
    participants: list[GatewayMailboxParticipantV1] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        email = item.get("email")
        if not isinstance(email, str) or not email.strip():
            continue
        name = item.get("name") if isinstance(item.get("name"), str) else None
        participants.append(
            GatewayMailboxParticipantV1(
                address=email.strip(),
                display_name=name.strip() if isinstance(name, str) and name.strip() else None,
                principal_id=None,
            )
        )
    return participants


def _attachments_from_stalwart_list(value: object) -> list[GatewayMailboxAttachmentV1]:
    if not isinstance(value, list):
        return []
    attachments: list[GatewayMailboxAttachmentV1] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        blob_id = item.get("blobId")
        if not isinstance(blob_id, str) or not blob_id.strip():
            continue
        media_type = item.get("type")
        normalized_media_type = (
            media_type if isinstance(media_type, str) else "application/octet-stream"
        )
        attachments.append(
            GatewayMailboxAttachmentV1(
                attachment_id=blob_id,
                kind="transport_owned",
                media_type=normalized_media_type,
                locator=f"blob:{blob_id}",
                size_bytes=item.get("size") if isinstance(item.get("size"), int) else None,
                label=item.get("name") if isinstance(item.get("name"), str) else None,
            )
        )
    return attachments


def _body_preview(body_text: str) -> str:
    normalized = " ".join(body_text.split())
    if len(normalized) <= 240:
        return normalized
    return normalized[:237] + "..."


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_optional_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return _parse_timestamp(value)


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _require_prefixed_ref(value: str, *, prefix: str) -> str:
    if ":" not in value:
        return value
    ref_prefix, ref_value = value.split(":", 1)
    if ref_prefix != prefix or not ref_value.strip():
        raise GatewayMailboxError(
            f"message_ref `{value}` is not valid for the `{prefix}` mailbox transport"
        )
    return ref_value


def _require_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GatewayMailboxError(f"mailbox payload is missing `{key}`")
    return value


def _require_boolean(payload: dict[str, object], key: str) -> bool:
    """Return one required boolean mailbox payload field."""

    value = payload.get(key)
    if not isinstance(value, bool):
        raise GatewayMailboxError(f"mailbox payload is missing explicit boolean `{key}` state")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _generate_filesystem_message_id(now: datetime) -> str:
    timestamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"msg-{timestamp}-{uuid4().hex}"
