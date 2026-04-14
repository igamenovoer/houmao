"""Gateway mailbox adapter protocol and transport implementations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import mimetypes
from pathlib import Path
import sqlite3
from typing import Mapping, Protocol, Sequence
from uuid import uuid4

from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
    MailboxResolvedConfig,
    StalwartMailboxResolvedConfig,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayMailAttachmentUploadV1,
    GatewayMailStatusV1,
    GatewayMailboxAttachmentV1,
    GatewayMailboxMessageV1,
    GatewayMailboxParticipantV1,
)
from houmao.mailbox.errors import MailboxProtocolError
from houmao.mailbox.filesystem import resolve_active_mailbox_local_sqlite_path
from houmao.mailbox.managed import (
    DeliveryRequest,
    ManagedAttachment,
    ManagedMailboxOperationError,
    ManagedPrincipal,
    StateUpdateRequest,
    deliver_message,
    ensure_operator_mailbox_registration,
    update_mailbox_state,
)
from houmao.mailbox.protocol import (
    HOUMAO_NO_REPLY_POLICY_VALUE,
    HOUMAO_OPERATOR_ADDRESS,
    HOUMAO_OPERATOR_DISPLAY_NAME,
    HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
    HOUMAO_OPERATOR_PRINCIPAL_ID,
    HOUMAO_OPERATOR_ROLE,
    MailboxAttachment,
    MailboxMessage,
    MailboxPrincipal,
    is_operator_origin_headers,
    operator_origin_reply_policy,
    OperatorOriginReplyPolicy,
    operator_origin_headers,
    parse_message_document,
    serialize_message_document,
    validate_mailbox_address,
)
from houmao.mailbox.stalwart import StalwartError, StalwartJmapClient


class GatewayMailboxError(RuntimeError):
    """Raised when a gateway mailbox adapter cannot satisfy a mailbox request."""


class GatewayMailboxUnsupportedError(GatewayMailboxError):
    """Raised when one mailbox operation is unsupported for the active transport."""


class GatewayMailboxAdapter(Protocol):
    """Shared gateway mailbox adapter for one manifest-backed session binding."""

    def status(self) -> GatewayMailStatusV1:
        """Return mailbox availability and identity metadata."""

    def list_messages(
        self,
        *,
        box: str,
        read_state: str,
        answered_state: str,
        archived: bool | None,
        limit: int | None,
        since: str | None,
        include_body: bool,
    ) -> list[GatewayMailboxMessageV1]:
        """Return normalized mailbox messages for one list request."""

    def peek(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        """Return one normalized mailbox message without marking it read."""

    def read(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        """Return one normalized mailbox message and mark it read."""

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

    def post(
        self,
        *,
        subject: str,
        body_content: str,
        reply_policy: OperatorOriginReplyPolicy,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
    ) -> GatewayMailboxMessageV1:
        """Deliver one operator-origin mailbox note into the current mailbox."""

    def mark(
        self,
        *,
        message_refs: Sequence[str],
        read: bool | None,
        answered: bool | None,
        archived: bool | None,
    ) -> list[GatewayMailboxMessageV1]:
        """Apply mailbox state flags to selected messages."""

    def move(
        self,
        *,
        message_refs: Sequence[str],
        destination_box: str,
    ) -> list[GatewayMailboxMessageV1]:
        """Move selected messages into another mailbox box."""

    def archive(self, *, message_refs: Sequence[str]) -> list[GatewayMailboxMessageV1]:
        """Move selected messages into the archive box."""


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

    def list_messages(
        self,
        *,
        box: str,
        read_state: str,
        answered_state: str,
        archived: bool | None,
        limit: int | None,
        since: str | None,
        include_body: bool,
    ) -> list[GatewayMailboxMessageV1]:
        local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
            self.m_mailbox.filesystem_root,
            address=self.m_mailbox.address,
        )
        shared_sqlite_path = (self.m_mailbox.filesystem_root / "index.sqlite").resolve()
        normalized_box = _normalize_box_name(box)
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
                        local_mailbox.message_state.is_read,
                        local_mailbox.message_state.is_answered,
                        local_mailbox.message_state.is_archived,
                        local_mailbox.message_state.box_name
                    FROM local_mailbox.message_state
                    JOIN messages AS message
                      ON message.message_id = local_mailbox.message_state.message_id
                    WHERE local_mailbox.message_state.box_name = ?
                    ORDER BY message.created_at_utc DESC, message.message_id DESC
                    """,
                    (normalized_box,),
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
            read = bool(row[5])
            answered = bool(row[6])
            archived_state = bool(row[7])
            if read_state == "read" and not read:
                continue
            if read_state == "unread" and read:
                continue
            if answered_state == "answered" and not answered:
                continue
            if answered_state == "unanswered" and answered:
                continue
            if archived is not None and archived_state is not archived:
                continue
            message = self._load_message_document(
                message_id=str(row[0]),
                canonical_path=Path(str(row[4])),
            )
            messages.append(
                self._message_to_model(
                    message=message,
                    read=read,
                    answered=answered,
                    archived=archived_state,
                    box=str(row[8]),
                    include_body=include_body,
                )
            )
            if limit is not None and len(messages) >= limit:
                break
        return messages

    def peek(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        message_id = _require_prefixed_ref(message_ref, prefix="filesystem")
        return self._load_local_message_model(message_id=message_id, box=box, include_body=True)

    def read(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        message_id = _require_prefixed_ref(message_ref, prefix="filesystem")
        try:
            update_mailbox_state(
                self.m_mailbox.filesystem_root,
                StateUpdateRequest(
                    address=self.m_mailbox.address,
                    message_id=message_id,
                    read=True,
                ),
            )
        except ManagedMailboxOperationError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        return self._load_local_message_model(message_id=message_id, box=box, include_body=True)

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
        state = self._load_local_message_state(message_id=message_id)
        return self._message_to_model(
            message=self._load_message_document(
                message_id=message_id,
                canonical_path=self._canonical_message_path(
                    message_id=message_id, created_at_utc=created_at_utc
                ),
            ),
            read=bool(state["read"]),
            answered=bool(state["answered"]),
            archived=bool(state["archived"]),
            box=str(state["box"]),
            include_body=True,
        )

    def post(
        self,
        *,
        subject: str,
        body_content: str,
        reply_policy: OperatorOriginReplyPolicy,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
    ) -> GatewayMailboxMessageV1:
        self._ensure_operator_registration()
        now = datetime.now(UTC)
        message_id = _generate_filesystem_message_id(now)
        created_at_utc = now.isoformat(timespec="seconds").replace("+00:00", "Z")
        request = self._build_delivery_request(
            message_id=message_id,
            thread_id=message_id,
            in_reply_to=None,
            references=(),
            created_at_utc=created_at_utc,
            to_addresses=[self.m_mailbox.address],
            cc_addresses=(),
            subject=subject,
            body_content=body_content,
            attachments=attachments,
            sender=self._operator_sender(),
            reply_to=(
                (self._operator_sender(),)
                if reply_policy == HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE
                else ()
            ),
            headers=operator_origin_headers(reply_policy=reply_policy),
        )
        try:
            deliver_message(self.m_mailbox.filesystem_root, request)
        except ManagedMailboxOperationError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        state = self._load_local_message_state(message_id=message_id)
        return self._message_to_model(
            message=self._load_message_document(
                message_id=message_id,
                canonical_path=self._canonical_message_path(
                    message_id=message_id, created_at_utc=created_at_utc
                ),
            ),
            read=bool(state["read"]),
            answered=bool(state["answered"]),
            archived=bool(state["archived"]),
            box=str(state["box"]),
            include_body=True,
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
        if is_operator_origin_headers(parent_message.headers):
            if operator_origin_reply_policy(parent_message.headers) == HOUMAO_NO_REPLY_POLICY_VALUE:
                raise GatewayMailboxUnsupportedError(
                    "reply is unsupported for operator-origin mailbox messages"
                )
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
            update_mailbox_state(
                self.m_mailbox.filesystem_root,
                StateUpdateRequest(
                    address=self.m_mailbox.address,
                    message_id=parent_message_id,
                    read=True,
                    answered=True,
                ),
            )
        except ManagedMailboxOperationError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        state = self._load_local_message_state(message_id=message_id)
        return self._message_to_model(
            message=self._load_message_document(
                message_id=message_id,
                canonical_path=self._canonical_message_path(
                    message_id=message_id, created_at_utc=created_at_utc
                ),
            ),
            read=bool(state["read"]),
            answered=bool(state["answered"]),
            archived=bool(state["archived"]),
            box=str(state["box"]),
            include_body=True,
        )

    def mark(
        self,
        *,
        message_refs: Sequence[str],
        read: bool | None,
        answered: bool | None,
        archived: bool | None,
    ) -> list[GatewayMailboxMessageV1]:
        if archived is True and read is False:
            raise GatewayMailboxError("archived messages must be read")
        messages: list[GatewayMailboxMessageV1] = []
        for message_ref in message_refs:
            message_id = _require_prefixed_ref(message_ref, prefix="filesystem")
            if archived is not None:
                self._move_local_message(
                    message_id=message_id,
                    destination_box="archive" if archived else "inbox",
                    force_read=True if archived else None,
                )
            if read is not None or answered is not None:
                try:
                    update_mailbox_state(
                        self.m_mailbox.filesystem_root,
                        StateUpdateRequest(
                            address=self.m_mailbox.address,
                            message_id=message_id,
                            read=read,
                            answered=answered,
                        ),
                    )
                except ManagedMailboxOperationError as exc:
                    raise GatewayMailboxError(str(exc)) from exc
            messages.append(
                self._load_local_message_model(message_id=message_id, box=None, include_body=True)
            )
        return messages

    def move(
        self,
        *,
        message_refs: Sequence[str],
        destination_box: str,
    ) -> list[GatewayMailboxMessageV1]:
        messages: list[GatewayMailboxMessageV1] = []
        for message_ref in message_refs:
            message_id = _require_prefixed_ref(message_ref, prefix="filesystem")
            messages.append(
                self._move_local_message(
                    message_id=message_id,
                    destination_box=destination_box,
                    force_read=True if _normalize_box_name(destination_box) == "archive" else None,
                )
            )
        return messages

    def archive(self, *, message_refs: Sequence[str]) -> list[GatewayMailboxMessageV1]:
        return self.move(message_refs=message_refs, destination_box="archive")

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
        sender: ManagedPrincipal | None = None,
        reply_to: Sequence[ManagedPrincipal] = (),
        headers: Mapping[str, object] | None = None,
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
            sender=sender
            or ManagedPrincipal(
                principal_id=self.m_mailbox.principal_id,
                address=self.m_mailbox.address,
            ),
            to=tuple(to_principals),
            cc=tuple(cc_principals),
            reply_to=tuple(reply_to),
            subject=subject,
            attachments=tuple(_managed_attachment_from_upload(item) for item in attachments),
            headers=dict(headers or {}),
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
        normalized_address = self._normalize_recipient_address(
            connection=connection,
            address=address,
        )
        row = connection.execute(
            """
            SELECT owner_principal_id
            FROM mailbox_registrations
            WHERE address = ? AND status = 'active'
            LIMIT 1
            """,
            (normalized_address,),
        ).fetchone()
        if row is None:
            raise GatewayMailboxError(
                self._missing_recipient_registration_detail(
                    connection=connection,
                    address=normalized_address,
                )
            )
        return ManagedPrincipal(
            principal_id=str(row[0]),
            address=normalized_address,
        )

    def _normalize_recipient_address(
        self,
        *,
        connection: sqlite3.Connection,
        address: str,
    ) -> str:
        """Validate and normalize one recipient address for filesystem delivery."""

        try:
            return validate_mailbox_address(address)
        except MailboxProtocolError as exc:
            hint_address = self._active_address_hint_for_agent_name(
                connection=connection,
                agent_name=address,
            )
            raise GatewayMailboxError(
                _invalid_recipient_address_detail(address=address, hint_address=hint_address)
            ) from exc

    def _missing_recipient_registration_detail(
        self,
        *,
        connection: sqlite3.Connection,
        address: str,
    ) -> str:
        """Return an actionable error for a syntactically valid missing recipient."""

        rows = connection.execute(
            """
            SELECT DISTINCT status
            FROM mailbox_registrations
            WHERE address = ? AND status != 'active'
            ORDER BY status
            """,
            (address,),
        ).fetchall()
        if rows:
            statuses = ", ".join(f"`{str(row[0])}`" for row in rows)
            return (
                f"filesystem mailbox recipient `{address}` is registered with status "
                f"{statuses}, not `active`. `/v1/mail/send` can deliver only to active "
                "mailbox addresses."
            )
        return (
            f"filesystem mailbox recipient `{address}` is not an active registered mailbox "
            "address. `/v1/mail/send` expects a full mailbox address with an active "
            "registration."
        )

    def _active_address_hint_for_agent_name(
        self,
        *,
        connection: sqlite3.Connection,
        agent_name: str,
    ) -> str | None:
        """Return a unique active mailbox address matching one likely agent name."""

        normalized_agent_name = agent_name.strip()
        if not normalized_agent_name:
            return None
        candidate_principal_ids = {normalized_agent_name}
        if not normalized_agent_name.startswith("HOUMAO-"):
            candidate_principal_ids.add(f"HOUMAO-{normalized_agent_name}")
        rows = connection.execute(
            """
            SELECT address, owner_principal_id
            FROM mailbox_registrations
            WHERE status = 'active'
            """
        ).fetchall()
        matches = {
            str(row[0])
            for row in rows
            if _active_registration_matches_agent_name(
                address=str(row[0]),
                owner_principal_id=str(row[1]),
                agent_name=normalized_agent_name,
                candidate_principal_ids=candidate_principal_ids,
            )
        }
        if len(matches) != 1:
            return None
        return next(iter(matches))

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

    def _load_local_message_state(self, *, message_id: str) -> dict[str, object]:
        """Return actor-local lifecycle state for one delivered filesystem message."""

        local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
            self.m_mailbox.filesystem_root,
            address=self.m_mailbox.address,
        )
        try:
            with sqlite3.connect(local_sqlite_path) as connection:
                row = connection.execute(
                    """
                    SELECT is_read, is_answered, is_archived, box_name
                    FROM message_state
                    WHERE message_id = ?
                    """,
                    (message_id,),
                ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise GatewayMailboxError(
                f"filesystem mailbox state is unreadable for `{self.m_mailbox.address}`"
            ) from exc
        if row is None:
            raise GatewayMailboxError(
                f"filesystem mailbox state is missing for `{message_id}` in `{self.m_mailbox.address}`"
            )
        return {
            "read": bool(row[0]),
            "answered": bool(row[1]),
            "archived": bool(row[2]),
            "box": str(row[3]),
        }

    def _load_local_message_model(
        self,
        *,
        message_id: str,
        box: str | None,
        include_body: bool,
    ) -> GatewayMailboxMessageV1:
        """Return one local message model by id, optionally requiring its active box."""

        shared_sqlite_path = (self.m_mailbox.filesystem_root / "index.sqlite").resolve()
        local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
            self.m_mailbox.filesystem_root,
            address=self.m_mailbox.address,
        )
        try:
            with sqlite3.connect(shared_sqlite_path) as connection:
                connection.execute("ATTACH DATABASE ? AS local_mailbox", (str(local_sqlite_path),))
                row = connection.execute(
                    """
                    SELECT
                        message.canonical_path,
                        local_mailbox.message_state.is_read,
                        local_mailbox.message_state.is_answered,
                        local_mailbox.message_state.is_archived,
                        local_mailbox.message_state.box_name
                    FROM local_mailbox.message_state
                    JOIN messages AS message
                      ON message.message_id = local_mailbox.message_state.message_id
                    WHERE local_mailbox.message_state.message_id = ?
                    """,
                    (message_id,),
                ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise GatewayMailboxError(
                f"filesystem mailbox state is unreadable for `{self.m_mailbox.address}`"
            ) from exc
        if row is None:
            raise GatewayMailboxError(
                f"filesystem mailbox state is missing for `{message_id}` in `{self.m_mailbox.address}`"
            )
        message_box = str(row[4])
        if box is not None and message_box != _normalize_box_name(box):
            raise GatewayMailboxError(
                f"filesystem mailbox message `{message_id}` is in `{message_box}`, not `{box}`"
            )
        message = self._load_message_document(message_id=message_id, canonical_path=Path(str(row[0])))
        return self._message_to_model(
            message=message,
            read=bool(row[1]),
            answered=bool(row[2]),
            archived=bool(row[3]),
            box=message_box,
            include_body=include_body,
        )

    def _move_local_message(
        self,
        *,
        message_id: str,
        destination_box: str,
        force_read: bool | None,
    ) -> GatewayMailboxMessageV1:
        """Move one filesystem mailbox projection and mirror its local box state."""

        normalized_box = _normalize_box_name(destination_box)
        shared_sqlite_path = (self.m_mailbox.filesystem_root / "index.sqlite").resolve()
        local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
            self.m_mailbox.filesystem_root,
            address=self.m_mailbox.address,
        )
        try:
            with sqlite3.connect(shared_sqlite_path) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute("ATTACH DATABASE ? AS local_mailbox", (str(local_sqlite_path),))
                registration_row = connection.execute(
                    """
                    SELECT registration_id, mailbox_path
                    FROM mailbox_registrations
                    WHERE address = ? AND status = 'active'
                    LIMIT 1
                    """,
                    (self.m_mailbox.address,),
                ).fetchone()
                if registration_row is None:
                    raise GatewayMailboxError(
                        f"no active mailbox registration exists for `{self.m_mailbox.address}`"
                    )
                registration_id = str(registration_row[0])
                mailbox_path = Path(str(registration_row[1]))
                message_row = connection.execute(
                    "SELECT canonical_path, thread_id FROM messages WHERE message_id = ?",
                    (message_id,),
                ).fetchone()
                if message_row is None:
                    raise GatewayMailboxError(f"unknown filesystem mailbox message `{message_id}`")
                projection_rows = connection.execute(
                    """
                    SELECT folder_name, projection_path
                    FROM mailbox_projections
                    WHERE registration_id = ? AND message_id = ?
                    ORDER BY folder_name ASC
                    """,
                    (registration_id, message_id),
                ).fetchall()
                if not projection_rows:
                    raise GatewayMailboxError(
                        f"message `{message_id}` is not projected into `{self.m_mailbox.address}`"
                    )

                canonical_path = Path(str(message_row[0]))
                destination_path = mailbox_path / normalized_box / f"{message_id}.md"
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                if destination_path.is_symlink():
                    if destination_path.resolve() != canonical_path:
                        raise GatewayMailboxError(
                            f"projection target mismatch for `{destination_path}`"
                        )
                elif destination_path.exists():
                    raise GatewayMailboxError(
                        f"projection path exists but is not a symlink: {destination_path}"
                    )
                else:
                    destination_path.symlink_to(canonical_path)

                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO mailbox_projections (
                        registration_id,
                        message_id,
                        folder_name,
                        projection_path
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(registration_id, message_id, folder_name) DO UPDATE SET
                        projection_path = excluded.projection_path
                    """,
                    (registration_id, message_id, normalized_box, str(destination_path)),
                )
                for row in projection_rows:
                    folder_name = str(row[0])
                    projection_path = Path(str(row[1]))
                    if folder_name == normalized_box:
                        continue
                    connection.execute(
                        """
                        DELETE FROM mailbox_projections
                        WHERE registration_id = ? AND message_id = ? AND folder_name = ?
                        """,
                        (registration_id, message_id, folder_name),
                    )
                    if projection_path != destination_path:
                        projection_path.unlink(missing_ok=True)

                assignments = ["box_name = ?", "is_archived = ?"]
                parameters: list[object] = [normalized_box, int(normalized_box == "archive")]
                if force_read is not None:
                    assignments.append("is_read = ?")
                    parameters.append(int(force_read))
                parameters.append(message_id)
                connection.execute(
                    f"""
                    UPDATE local_mailbox.message_state
                    SET {", ".join(assignments)}
                    WHERE message_id = ?
                    """,
                    tuple(parameters),
                )
                connection.commit()
        except sqlite3.DatabaseError as exc:
            raise GatewayMailboxError(
                f"filesystem mailbox move failed for `{self.m_mailbox.address}`"
            ) from exc
        return self._load_local_message_model(message_id=message_id, box=None, include_body=True)

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

    def _ensure_operator_registration(self) -> None:
        try:
            ensure_operator_mailbox_registration(self.m_mailbox.filesystem_root)
        except ManagedMailboxOperationError as exc:
            raise GatewayMailboxError(str(exc)) from exc

    def _operator_sender(self) -> ManagedPrincipal:
        return ManagedPrincipal(
            principal_id=HOUMAO_OPERATOR_PRINCIPAL_ID,
            address=HOUMAO_OPERATOR_ADDRESS,
            display_name=HOUMAO_OPERATOR_DISPLAY_NAME,
            role=HOUMAO_OPERATOR_ROLE,
        )

    def _message_to_model(
        self,
        *,
        message: MailboxMessage,
        read: bool | None,
        answered: bool | None,
        archived: bool | None,
        box: str | None,
        include_body: bool,
    ) -> GatewayMailboxMessageV1:
        return GatewayMailboxMessageV1(
            message_ref=f"filesystem:{message.message_id}",
            thread_ref=f"filesystem:{message.thread_id}",
            created_at_utc=message.created_at_utc,
            subject=message.subject,
            read=read,
            answered=answered,
            archived=archived,
            box=box,
            unread=None if read is None else not read,
            body_preview=_body_preview(message.body_markdown),
            body_text=message.body_markdown if include_body else None,
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

    def list_messages(
        self,
        *,
        box: str,
        read_state: str,
        answered_state: str,
        archived: bool | None,
        limit: int | None,
        since: str | None,
        include_body: bool,
    ) -> list[GatewayMailboxMessageV1]:
        try:
            rows = self._client().list_messages(
                box=box,
                read_state=read_state,
                answered_state=answered_state,
                archived=archived,
                limit=limit,
                since=since,
            )
        except StalwartError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        return [_stalwart_message_to_model(row, include_body=include_body) for row in rows]

    def peek(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        del box
        try:
            row = self._client().get_email(
                email_id=_require_prefixed_ref(message_ref, prefix="stalwart")
            )
        except StalwartError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        return _stalwart_message_to_model(row, include_body=True)

    def read(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        del box
        try:
            row = self._client().mark(
                message_ref=_require_prefixed_ref(message_ref, prefix="stalwart"),
                read=True,
                answered=None,
                archived=None,
            )
        except StalwartError as exc:
            raise GatewayMailboxError(str(exc)) from exc
        return _stalwart_message_to_model(row, include_body=True)

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
        return _stalwart_message_to_model(row, include_body=True)

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
        return _stalwart_message_to_model(row, include_body=True)

    def post(
        self,
        *,
        subject: str,
        body_content: str,
        reply_policy: OperatorOriginReplyPolicy,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
    ) -> GatewayMailboxMessageV1:
        del subject, body_content, reply_policy, attachments
        raise GatewayMailboxUnsupportedError(
            "operator-origin mailbox post is unsupported for stalwart mailbox bindings"
        )

    def mark(
        self,
        *,
        message_refs: Sequence[str],
        read: bool | None,
        answered: bool | None,
        archived: bool | None,
    ) -> list[GatewayMailboxMessageV1]:
        messages: list[GatewayMailboxMessageV1] = []
        for message_ref in message_refs:
            try:
                row = self._client().mark(
                    message_ref=_require_prefixed_ref(message_ref, prefix="stalwart"),
                    read=read,
                    answered=answered,
                    archived=archived,
                )
            except StalwartError as exc:
                raise GatewayMailboxError(str(exc)) from exc
            messages.append(_stalwart_message_to_model(row, include_body=True))
        return messages

    def move(
        self,
        *,
        message_refs: Sequence[str],
        destination_box: str,
    ) -> list[GatewayMailboxMessageV1]:
        messages: list[GatewayMailboxMessageV1] = []
        for message_ref in message_refs:
            try:
                row = self._client().move(
                    message_ref=_require_prefixed_ref(message_ref, prefix="stalwart"),
                    destination_box=destination_box,
                )
            except StalwartError as exc:
                raise GatewayMailboxError(str(exc)) from exc
            messages.append(_stalwart_message_to_model(row, include_body=True))
        return messages

    def archive(self, *, message_refs: Sequence[str]) -> list[GatewayMailboxMessageV1]:
        return self.move(message_refs=message_refs, destination_box="archive")

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


def _invalid_recipient_address_detail(*, address: str, hint_address: str | None) -> str:
    """Return the filesystem send diagnostic for non-address recipient input."""

    detail = (
        f"filesystem mailbox recipient `{address}` is not a registered mailbox address. "
        "`/v1/mail/send` expects email-like mailbox addresses such as "
        "`daq-mgr@houmao.localhost`, not managed-agent names. Resolve the target "
        "mailbox address first or use the managed-agent mail helper."
    )
    if hint_address is not None:
        return f"{detail} Did you mean `{hint_address}`?"
    return detail


def _normalize_box_name(value: str) -> str:
    """Normalize one mailbox box name for filesystem/JMAP operations."""

    normalized = value.strip()
    if not normalized:
        raise GatewayMailboxError("mailbox box name must not be empty")
    if normalized in {".", ".."} or "/" in normalized or "\x00" in normalized:
        raise GatewayMailboxError(f"unsupported mailbox box name `{value}`")
    return normalized


def _active_registration_matches_agent_name(
    *,
    address: str,
    owner_principal_id: str,
    agent_name: str,
    candidate_principal_ids: set[str],
) -> bool:
    """Return whether one registration is a likely match for a bare agent name."""

    local_part = address.split("@", 1)[0]
    return local_part == agent_name or owner_principal_id in candidate_principal_ids


def _stalwart_message_to_model(
    payload: dict[str, object],
    *,
    include_body: bool,
) -> GatewayMailboxMessageV1:
    unread_value = payload.get("unread")
    normalized_unread: bool | None = unread_value if isinstance(unread_value, bool) else None
    read_value = payload.get("read")
    normalized_read = read_value if isinstance(read_value, bool) else None
    answered_value = payload.get("answered")
    normalized_answered = answered_value if isinstance(answered_value, bool) else None
    archived_value = payload.get("archived")
    normalized_archived = archived_value if isinstance(archived_value, bool) else None
    return GatewayMailboxMessageV1(
        message_ref=f"stalwart:{_require_string(payload, 'id')}",
        thread_ref=(
            f"stalwart-thread:{payload['threadId']}"
            if isinstance(payload.get("threadId"), str) and str(payload.get("threadId")).strip()
            else None
        ),
        created_at_utc=_require_string(payload, "receivedAt"),
        subject=_require_string(payload, "subject"),
        read=normalized_read,
        answered=normalized_answered,
        archived=normalized_archived,
        box=_optional_string(payload.get("box")),
        unread=normalized_unread,
        body_preview=_optional_string(payload.get("preview")),
        body_text=_optional_string(payload.get("body")) if include_body else None,
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
