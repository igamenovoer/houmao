"""Reusable filesystem and online mail backend services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import mimetypes
from pathlib import Path
import sqlite3
from typing import (
    Callable,
    Concatenate,
    Mapping,
    ParamSpec,
    Protocol,
    Sequence,
    TypeVar,
    TYPE_CHECKING,
)
from functools import wraps
from uuid import uuid4

from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
    MailboxResolvedConfig,
    RemoteRegistryMailboxResolvedConfig,
    StalwartMailboxResolvedConfig,
)
from houmao.mailbox.models import (
    GatewayMailAttachmentUploadV1,
    MailChannel,
    MailboxBackendStatusV1,
    GatewayMailboxAttachmentV1,
    GatewayMailboxMessageV1,
    MailMutationReceipt,
    GatewayMailboxParticipantV1,
)
from houmao.mailbox.scope import MailScope, MailboxScopeError
from houmao.mailbox.content import CanonicalContent, read_canonical_content
from houmao.mailbox.pagination import (
    BackendMailPage,
    MailboxCursorError,
    validate_page_size,
    query_fingerprint,
    decode_backend_cursor,
    encode_backend_cursor,
)

if TYPE_CHECKING:
    from houmao.mailbox.online_models import OnlineAuthorityContext
from houmao.mailbox.authority_lock import offline_authority_lock
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
    MailboxNotifyAuth,
    MailboxNotifyBlock,
    MailboxPrincipal,
    is_operator_origin_headers,
    operator_origin_reply_policy,
    OperatorOriginReplyPolicy,
    operator_origin_headers,
    parse_message_document,
    serialize_message_document,
    validate_mailbox_address,
)
from houmao.mailbox.errors import (
    GatewayMailboxError as GatewayMailboxError,
    GatewayMailboxUnsupportedError as GatewayMailboxUnsupportedError,
)
from houmao.mailbox.stalwart import StalwartError, StalwartJmapClient, StalwartMutationError
from houmao.mailbox.errors import GatewayMailboxMutationError


class GatewayMailboxAdapter(Protocol):
    """Shared gateway mailbox adapter for one manifest-backed session binding."""

    def status(self) -> MailboxBackendStatusV1:
        """Return mailbox availability and identity metadata."""

    def list_page(
        self,
        *,
        box: str,
        read_state: str,
        answered_state: str,
        archived: bool | None,
        limit: int = 50,
        since: str | None = None,
        cursor: str | None = None,
    ) -> BackendMailPage:
        """Return a bounded metadata page with explicit continuation."""

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
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
    ) -> GatewayMailboxMessageV1:
        """Send one new mailbox message and return the normalized delivered record."""

    def reply(
        self,
        *,
        message_ref: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
    ) -> GatewayMailboxMessageV1:
        """Reply to one existing message and return the normalized delivered record."""

    def post(
        self,
        *,
        subject: str,
        body_content: str,
        reply_policy: OperatorOriginReplyPolicy,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
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
    if isinstance(mailbox, RemoteRegistryMailboxResolvedConfig):
        from houmao.mailbox.registry_backend import RemoteRegistryMailboxAdapter

        return RemoteRegistryMailboxAdapter.from_config(mailbox)
    return StalwartGatewayMailboxAdapter(mailbox)


_OperationParams = ParamSpec("_OperationParams")
_OperationResult = TypeVar("_OperationResult")


def _filesystem_operation(
    function: Callable[
        Concatenate["FilesystemGatewayMailboxAdapter", _OperationParams], _OperationResult
    ],
) -> Callable[Concatenate["FilesystemGatewayMailboxAdapter", _OperationParams], _OperationResult]:
    """Hold registry ownership stable for an entire filesystem operation."""

    @wraps(function)
    def guarded(
        self: FilesystemGatewayMailboxAdapter,
        /,
        *args: _OperationParams.args,
        **kwargs: _OperationParams.kwargs,
    ) -> _OperationResult:
        """Reject a released or reassigned registration before reading private state."""

        with offline_authority_lock(self.m_mailbox.filesystem_root):
            with sqlite3.connect(self.m_mailbox.filesystem_root / "index.sqlite") as connection:
                row = connection.execute(
                    "SELECT registration_id, owner_principal_id FROM mailbox_registrations WHERE address = ? AND status = 'active'",
                    (self.m_mailbox.address,),
                ).fetchone()
            if row is None or row != (self.m_mailbox.binding_id, self.m_mailbox.agent_id):
                raise MailboxScopeError("Offline registration was released or replaced")
            return function(self, *args, **kwargs)

    return guarded


@dataclass
class FilesystemGatewayMailboxAdapter:
    """Gateway adapter that exposes the filesystem mailbox transport."""

    m_mailbox: FilesystemMailboxResolvedConfig

    @_filesystem_operation
    def status(self) -> MailboxBackendStatusV1:
        return MailboxBackendStatusV1(
            transport="filesystem",
            principal_id=self.m_mailbox.principal_id,
            address=self.m_mailbox.address,
            bindings_version=self.m_mailbox.bindings_version,
        )

    @_filesystem_operation
    def list_page(
        self,
        *,
        box: str,
        read_state: str,
        answered_state: str,
        archived: bool | None,
        limit: int = 50,
        since: str | None = None,
        cursor: str | None = None,
    ) -> BackendMailPage:
        """Page authoritative metadata without loading full canonical bodies."""

        validate_page_size(limit)
        box = _normalize_box_name(box)
        if read_state not in {"any", "read", "unread"} or answered_state not in {
            "any",
            "answered",
            "unanswered",
        }:
            raise GatewayMailboxUnsupportedError("unsupported filesystem metadata filter")
        since_time = _parse_optional_timestamp(since)
        normalized_since = (
            since_time.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if since_time else None
        )
        fingerprint = query_fingerprint(
            {
                "box": box,
                "read_state": read_state,
                "answered_state": answered_state,
                "archived": archived,
                "since": normalized_since,
                "sort": "created-desc,message-id-desc",
            }
        )
        local_path = resolve_active_mailbox_local_sqlite_path(
            self.m_mailbox.filesystem_root, address=self.m_mailbox.address
        )
        clauses = ["box_name = ?"]
        parameters: list[object] = [box]
        if read_state != "any":
            clauses.append("is_read = ?")
            parameters.append(int(read_state == "read"))
        if answered_state != "any":
            clauses.append("is_answered = ?")
            parameters.append(int(answered_state == "answered"))
        if archived is not None:
            clauses.append("is_archived = ?")
            parameters.append(int(archived))
        if normalized_since is not None:
            clauses.append("created_at_utc > ?")
            parameters.append(normalized_since)
        try:
            with sqlite3.connect(local_path) as connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS mail_page_version (singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL)"
                )
                connection.execute("INSERT OR IGNORE INTO mail_page_version VALUES (1, 0)")
                for operation in ("INSERT", "UPDATE", "DELETE"):
                    connection.execute(
                        f"CREATE TRIGGER IF NOT EXISTS mail_page_{operation.lower()} AFTER {operation} ON message_state BEGIN UPDATE mail_page_version SET version=version+1 WHERE singleton=1; END"
                    )
                state = str(
                    connection.execute(
                        "SELECT version FROM mail_page_version WHERE singleton=1"
                    ).fetchone()[0]
                )
                position = 0
                if cursor is not None:
                    prior, position = decode_backend_cursor(
                        cursor, fingerprint=fingerprint, account=self.m_mailbox.binding_id
                    )
                    if prior != state:
                        raise MailboxCursorError(
                            "Mailbox changed between pages; start a fresh page", stale=True
                        )
                rows = connection.execute(
                    "SELECT message_id,is_read,is_answered,is_archived,box_name FROM message_state WHERE "
                    + " AND ".join(clauses)
                    + " ORDER BY created_at_utc DESC,message_id DESC LIMIT ? OFFSET ?",
                    (*parameters, limit + 1, position),
                ).fetchall()
                connection.commit()
        except sqlite3.DatabaseError as exc:
            raise GatewayMailboxError("filesystem mailbox metadata index is unavailable") from exc
        has_more = len(rows) > limit
        messages = []
        for row in rows[:limit]:
            message = self._load_message_by_id(str(row[0]))
            messages.append(
                self._message_to_model(
                    message=message,
                    read=bool(row[1]),
                    answered=bool(row[2]),
                    archived=bool(row[3]),
                    box=str(row[4]),
                    include_body=False,
                )
            )
        continuation = (
            encode_backend_cursor(
                fingerprint=fingerprint,
                state=state,
                position=position + len(messages),
                account=self.m_mailbox.binding_id,
            )
            if has_more
            else None
        )
        return BackendMailPage(
            messages=messages, next_cursor=continuation, has_more=has_more, complete=not has_more
        )

    @_filesystem_operation
    def peek(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        message_id = _require_prefixed_ref(message_ref, prefix="filesystem")
        return self._load_local_message_model(message_id=message_id, box=box, include_body=True)

    @_filesystem_operation
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

    @_filesystem_operation
    def send(
        self,
        *,
        to_addresses: Sequence[str],
        cc_addresses: Sequence[str],
        subject: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
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
            notify_block=notify_block,
            notify_auth=notify_auth,
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
            include_body=False,
        )

    @_filesystem_operation
    def post(
        self,
        *,
        subject: str,
        body_content: str,
        reply_policy: OperatorOriginReplyPolicy,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
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
            notify_block=notify_block,
            notify_auth=notify_auth,
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
            include_body=False,
        )

    @_filesystem_operation
    def reply(
        self,
        *,
        message_ref: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
    ) -> GatewayMailboxMessageV1:
        parent_message_id = _require_prefixed_ref(message_ref, prefix="filesystem")
        self._load_local_message_state(message_id=parent_message_id)
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
            notify_block=notify_block,
            notify_auth=notify_auth,
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
            include_body=False,
        )

    @_filesystem_operation
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
        message_ids = self._owned_message_ids(message_refs)
        messages: list[GatewayMailboxMessageV1] = []
        for message_id in message_ids:
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
                self._load_local_message_model(message_id=message_id, box=None, include_body=False)
            )
        return messages

    @_filesystem_operation
    def move(
        self,
        *,
        message_refs: Sequence[str],
        destination_box: str,
    ) -> list[GatewayMailboxMessageV1]:
        message_ids = self._owned_message_ids(message_refs)
        messages: list[GatewayMailboxMessageV1] = []
        for message_id in message_ids:
            messages.append(
                self._move_local_message(
                    message_id=message_id,
                    destination_box=destination_box,
                    force_read=True if _normalize_box_name(destination_box) == "archive" else None,
                )
            )
        return messages

    @_filesystem_operation
    def archive(self, *, message_refs: Sequence[str]) -> list[GatewayMailboxMessageV1]:
        return self.move(message_refs=message_refs, destination_box="archive")

    def _owned_message_ids(self, message_refs: Sequence[str]) -> list[str]:
        """Check an entire batch's actor-local membership before any mutation."""

        message_ids = [
            _require_prefixed_ref(reference, prefix="filesystem") for reference in message_refs
        ]
        for message_id in message_ids:
            self._load_local_message_state(message_id=message_id)
        return message_ids

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
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
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
            staged_message_path=staged_message_path,
            request=request,
            body_content=body_content,
            notify_block=notify_block,
            notify_auth=notify_auth,
        )
        return request

    def _write_staged_message(
        self,
        *,
        staged_message_path: Path,
        request: DeliveryRequest,
        body_content: str,
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
    ) -> None:
        payload: dict[str, object] = {
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
        if notify_block is not None:
            payload["notify_block"] = notify_block
        if notify_auth is not None:
            payload["notify_auth"] = notify_auth
        message = MailboxMessage.compose(payload)
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
                f"{statuses}, not `active`. `/v1/mail/offline/send` can deliver only to active "
                "mailbox addresses."
            )
        return (
            f"filesystem mailbox recipient `{address}` is not an active registered mailbox "
            "address. `/v1/mail/offline/send` expects a full mailbox address with an active "
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

    def _canonical_content(self, message_id: str, *, metadata_only: bool) -> CanonicalContent:
        """Read authorized canonical front matter and bounded content."""

        with sqlite3.connect(self.m_mailbox.filesystem_root / "index.sqlite") as connection:
            row = connection.execute(
                "SELECT canonical_path FROM messages WHERE message_id = ?", (message_id,)
            ).fetchone()
        if row is None:
            raise GatewayMailboxError("filesystem mailbox message was not found")
        try:
            return read_canonical_content(Path(str(row[0])), metadata_only=metadata_only)
        except (OSError, MailboxProtocolError) as exc:
            raise GatewayMailboxUnsupportedError(
                "Canonical metadata/content is unavailable or exceeds the supported limit"
            ) from exc

    def _load_message_by_id(self, message_id: str) -> MailboxMessage:
        """Return metadata without fetching a full message body."""

        return self._canonical_content(message_id, metadata_only=True).message

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

        local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
            self.m_mailbox.filesystem_root,
            address=self.m_mailbox.address,
        )
        try:
            with sqlite3.connect(local_sqlite_path) as connection:
                row = connection.execute(
                    """
                    SELECT
                        is_read,
                        is_answered,
                        is_archived,
                        box_name
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
        message_box = str(row[3])
        if box is not None and message_box != _normalize_box_name(box):
            raise GatewayMailboxError(
                f"filesystem mailbox message `{message_id}` is in `{message_box}`, not `{box}`"
            )
        content = self._canonical_content(message_id, metadata_only=not include_body)
        message = content.message
        result = self._message_to_model(
            message=message,
            read=bool(row[0]),
            answered=bool(row[1]),
            archived=bool(row[2]),
            box=message_box,
            include_body=include_body,
        )
        return result.model_copy(
            update={
                "content_complete": content.complete if include_body else None,
                "content_limit_bytes": content.limit_bytes if include_body else None,
                "content_limit_reason": "body_exceeds_supported_limit"
                if include_body and not content.complete
                else None,
            }
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
                connection.commit()
        except sqlite3.DatabaseError as exc:
            raise GatewayMailboxError(
                f"filesystem mailbox move failed for `{self.m_mailbox.address}`"
            ) from exc
        try:
            with sqlite3.connect(local_sqlite_path) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    f"""
                    UPDATE message_state
                    SET {", ".join(assignments)}
                    WHERE message_id = ?
                    """,
                    tuple(parameters),
                )
                connection.commit()
        except sqlite3.DatabaseError as exc:
            raise GatewayMailboxError(
                "filesystem mailbox local state update failed after moving "
                f"`{message_id}` for `{self.m_mailbox.address}`; run mailbox repair to rebuild "
                "local state"
            ) from exc
        return self._load_local_message_model(message_id=message_id, box=None, include_body=False)

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
            has_attachments=bool(message.attachments),
            notify_block=message.notify_block,
            notify_auth=message.notify_auth,
        )


@dataclass
class StalwartGatewayMailboxAdapter:
    """Gateway adapter that exposes the Stalwart-backed mailbox transport."""

    m_mailbox: StalwartMailboxResolvedConfig
    m_client: StalwartJmapClient | None = None

    def status(self) -> MailboxBackendStatusV1:
        self._client().status()
        return MailboxBackendStatusV1(
            transport="stalwart",
            principal_id=self.m_mailbox.principal_id,
            address=self.m_mailbox.address,
            bindings_version=self.m_mailbox.bindings_version,
        )

    def list_page(
        self,
        *,
        box: str,
        read_state: str,
        answered_state: str,
        archived: bool | None,
        limit: int = 50,
        since: str | None = None,
        cursor: str | None = None,
    ) -> BackendMailPage:
        """Use server-filtered metadata and a provider-state-validated page."""

        from houmao.mailbox.stalwart_models import JmapMetadataQuery

        validate_page_size(limit)
        try:
            client = self._client()
            client.validate_binding(sender_address=self.m_mailbox.address)
            query = JmapMetadataQuery(
                box=box,
                read_state=read_state,
                answered_state=answered_state,
                archived=archived,
                since=since,
            )
            fingerprint = client.query_fingerprint(query)
            account = self.m_mailbox.account_id or client.primary_account_id()
            state = None
            position = 0
            if cursor is not None:
                state, position = decode_backend_cursor(
                    cursor, fingerprint=fingerprint, account=account
                )
            page = client.query_metadata_page(
                query=query, limit=limit, position=position, expected_query_state=state
            )
        except StalwartError as exc:
            if getattr(exc, "error_type", "") == "staleCursor":
                raise MailboxCursorError(
                    "Provider query changed; start a fresh page", stale=True
                ) from exc
            raise _stalwart_backend_error(exc, self.m_mailbox) from exc
        messages = [stalwart_message_to_model(row, include_body=False) for row in page.messages]
        continuation = (
            encode_backend_cursor(
                fingerprint=fingerprint,
                state=page.query_state,
                position=page.next_position,
                account=account,
            )
            if page.has_more and page.next_position is not None
            else None
        )
        return BackendMailPage(
            messages=messages,
            next_cursor=continuation,
            has_more=page.has_more,
            complete=page.complete,
            total_count=page.total_count,
        )

    def peek(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        del box
        try:
            row = self._client().get_email(
                email_id=_require_prefixed_ref(message_ref, prefix="stalwart")
            )
        except StalwartError as exc:
            raise _stalwart_backend_error(exc, self.m_mailbox) from exc
        return stalwart_message_to_model(row, include_body=True)

    def read(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        """Read selected bounded content before committing its seen flag."""

        message = self.peek(message_ref=message_ref, box=box)
        try:
            self._client().mark(
                message_ref=_require_prefixed_ref(message_ref, prefix="stalwart"),
                read=True,
                answered=None,
                archived=None,
            )
        except StalwartError as exc:
            raise _stalwart_backend_error(exc, self.m_mailbox) from exc
        return message.model_copy(update={"read": True, "unread": False})

    def send(
        self,
        *,
        to_addresses: Sequence[str],
        cc_addresses: Sequence[str],
        subject: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
    ) -> GatewayMailboxMessageV1:
        _reject_stalwart_notify_fields(notify_block=notify_block, notify_auth=notify_auth)
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
            raise _stalwart_backend_error(exc, self.m_mailbox) from exc
        return self._mutation_message(row)

    def reply(
        self,
        *,
        message_ref: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
    ) -> GatewayMailboxMessageV1:
        _reject_stalwart_notify_fields(notify_block=notify_block, notify_auth=notify_auth)
        try:
            row = self._client().reply(
                message_ref=_require_prefixed_ref(message_ref, prefix="stalwart"),
                sender_address=self.m_mailbox.address,
                body_content=body_content,
                attachments=[Path(item.path).resolve() for item in attachments],
            )
        except StalwartError as exc:
            raise _stalwart_backend_error(exc, self.m_mailbox) from exc
        return self._mutation_message(row)

    def post(
        self,
        *,
        subject: str,
        body_content: str,
        reply_policy: OperatorOriginReplyPolicy,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
    ) -> GatewayMailboxMessageV1:
        del subject, body_content, reply_policy, attachments, notify_block, notify_auth
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
                raise _stalwart_backend_error(exc, self.m_mailbox) from exc
            messages.append(stalwart_message_to_model(row, include_body=False))
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
                raise _stalwart_backend_error(exc, self.m_mailbox) from exc
            messages.append(stalwart_message_to_model(row, include_body=False))
        return messages

    def archive(self, *, message_refs: Sequence[str]) -> list[GatewayMailboxMessageV1]:
        return self.move(message_refs=message_refs, destination_box="archive")

    def _client(self) -> StalwartJmapClient:
        """Reuse discovery and role state for one immutable connection scope."""

        if self.m_client is None:
            if self.m_mailbox.credential_file is None:
                raise GatewayMailboxError("online credential snapshot is unavailable")
            self.m_client = StalwartJmapClient(
                jmap_url=self.m_mailbox.jmap_url,
                login_identity=self.m_mailbox.login_identity,
                credential_file=self.m_mailbox.credential_file,
                sender_address=self.m_mailbox.address,
                account_id=self.m_mailbox.account_id,
                identity_id=self.m_mailbox.identity_id,
            )
        return self.m_client

    def _mutation_message(self, row: dict[str, object]) -> GatewayMailboxMessageV1:
        """Attach the exact admitted binding to a provider acknowledgement."""

        message = stalwart_message_to_model(row, include_body=False)
        if message.mutation_receipt is not None:
            return message.model_copy(
                update={
                    "mutation_receipt": message.mutation_receipt.model_copy(
                        update={
                            "agent_id": self.m_mailbox.agent_id,
                            "binding_id": self.m_mailbox.binding_id,
                            "revision": self.m_mailbox.bindings_version,
                        }
                    )
                }
            )
        return message


def _stalwart_backend_error(
    error: StalwartError, binding: StalwartMailboxResolvedConfig
) -> GatewayMailboxError:
    """Preserve typed mutation acknowledgement in its admitted account scope."""

    if isinstance(error, StalwartMutationError):
        return GatewayMailboxMutationError(
            operation=error.operation,
            outcome=error.outcome,
            email_id=error.email_id,
            submission_id=error.submission_id,
            agent_id=binding.agent_id,
            binding_id=binding.binding_id,
            revision=binding.bindings_version,
        )
    return GatewayMailboxError(str(error))


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
        "`/v1/mail/offline/send` expects email-like mailbox addresses such as "
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


def stalwart_message_to_model(
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
    content_complete = payload.get("content_complete")
    content_limit = payload.get("content_limit_bytes")
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
        has_attachments=payload.get("hasAttachment") is True,
        content_complete=content_complete if isinstance(content_complete, bool) else None,
        content_limit_bytes=content_limit if isinstance(content_limit, int) else None,
        content_limit_reason=_optional_string(payload.get("content_limit_reason")),
        mutation_receipt=(
            MailMutationReceipt.model_validate(payload["mutation_receipt"])
            if isinstance(payload.get("mutation_receipt"), dict)
            else None
        ),
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
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise GatewayMailboxUnsupportedError(
            "since must be an RFC3339 timestamp with a timezone"
        ) from exc
    if parsed.tzinfo is None:
        raise GatewayMailboxUnsupportedError("since must include an RFC3339 timezone")
    return parsed.astimezone(UTC)


def _reject_stalwart_notify_fields(
    *,
    notify_block: MailboxNotifyBlock | None,
    notify_auth: MailboxNotifyAuth | None,
) -> None:
    """Reject notify-block and notify-auth on Stalwart-bound sends in this version.

    The Stalwart adapter does not yet project canonical envelope fields into
    JMAP-native headers. Until that projection ships, callers that supply
    these fields against a Stalwart binding receive an explicit unsupported
    error rather than a silent drop of sender intent.
    """

    if notify_block is not None or notify_auth is not None:
        raise GatewayMailboxUnsupportedError(
            "notify_block and notify_auth are unsupported for stalwart mailbox bindings "
            "in this protocol version"
        )


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


class ScopedMailboxAdapter:
    """Validate binding handles before delegating to a single backend."""

    def __init__(self) -> None:
        """Initialize an unbound service; use ``from_backend``."""

        self.m_backend: GatewayMailboxAdapter
        self.m_scope: MailScope
        self.m_identity: MailboxBackendStatusV1 | None = None

    @classmethod
    def from_backend(
        cls,
        backend: GatewayMailboxAdapter,
        scope: MailScope,
        *,
        identity: MailboxBackendStatusV1 | None = None,
    ) -> ScopedMailboxAdapter:
        """Wrap one configured backend in its immutable owner scope."""

        instance = cls()
        instance.m_backend = backend
        instance.m_scope = scope
        instance.m_identity = identity
        return instance

    @property
    def scope(self) -> MailScope:
        """Return the immutable targeting scope."""

        return self.m_scope

    def _wrap_message(self, message: GatewayMailboxMessageV1) -> GatewayMailboxMessageV1:
        """Scope both message and thread handles without changing snapshots."""

        return message.model_copy(
            update={
                "message_ref": self.m_scope.encode(message.message_ref),
                "thread_ref": self.m_scope.encode(message.thread_ref, kind="thread")
                if message.thread_ref
                else None,
            }
        )

    def status(self) -> MailboxBackendStatusV1:
        """Run the selected operation with validated scope."""

        return self.m_identity if self.m_identity is not None else self.m_backend.status()

    def list_page(
        self,
        *,
        box: str,
        read_state: str,
        answered_state: str,
        archived: bool | None,
        limit: int = 50,
        since: str | None = None,
        cursor: str | None = None,
    ) -> BackendMailPage:
        """Preserve owner/channel/binding scope across every metadata page."""

        raw_cursor = self.m_scope.decode(cursor, kind="cursor") if cursor is not None else None
        page = self.m_backend.list_page(
            box=box,
            read_state=read_state,
            answered_state=answered_state,
            archived=archived,
            limit=limit,
            since=since,
            cursor=raw_cursor,
        )
        return BackendMailPage(
            messages=[self._wrap_message(message) for message in page.messages],
            next_cursor=self.m_scope.encode(page.next_cursor, kind="cursor")
            if page.next_cursor
            else None,
            has_more=page.has_more,
            complete=page.complete,
            total_count=page.total_count,
        )

    def peek(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        """Run the selected operation with validated scope."""

        return self._wrap_message(
            self.m_backend.peek(message_ref=self.m_scope.decode(message_ref), box=box)
        )

    def read(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        """Run the selected operation with validated scope."""

        return self._wrap_message(
            self.m_backend.read(message_ref=self.m_scope.decode(message_ref), box=box)
        )

    def send(
        self,
        *,
        to_addresses: Sequence[str],
        cc_addresses: Sequence[str],
        subject: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
    ) -> GatewayMailboxMessageV1:
        """Run the selected operation with validated scope."""

        try:
            normalized_to = [validate_mailbox_address(address) for address in to_addresses]
            normalized_cc = [validate_mailbox_address(address) for address in cc_addresses]
        except MailboxProtocolError as exc:
            if isinstance(self.m_backend, FilesystemGatewayMailboxAdapter):
                # Preserve the local address-resolution hint without staging or dispatch.
                with sqlite3.connect(
                    self.m_backend.m_mailbox.filesystem_root / "index.sqlite"
                ) as connection:
                    for address in (*to_addresses, *cc_addresses):
                        self.m_backend._managed_principal_for_address(
                            connection=connection, address=address
                        )
            raise GatewayMailboxError(
                "Recipients must be full mailbox addresses in the selected channel; "
                "scoped mail handles cannot select another channel."
            ) from exc
        return self._wrap_message(
            self.m_backend.send(
                to_addresses=normalized_to,
                cc_addresses=normalized_cc,
                subject=subject,
                body_content=body_content,
                attachments=attachments,
                notify_block=notify_block,
                notify_auth=notify_auth,
            )
        )

    def reply(
        self,
        *,
        message_ref: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
    ) -> GatewayMailboxMessageV1:
        """Run the selected operation with validated scope."""

        return self._wrap_message(
            self.m_backend.reply(
                message_ref=self.m_scope.decode(message_ref),
                body_content=body_content,
                attachments=attachments,
                notify_block=notify_block,
                notify_auth=notify_auth,
            )
        )

    def post(
        self,
        *,
        subject: str,
        body_content: str,
        reply_policy: OperatorOriginReplyPolicy,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
    ) -> GatewayMailboxMessageV1:
        """Run the selected operation with validated scope."""

        return self._wrap_message(
            self.m_backend.post(
                subject=subject,
                body_content=body_content,
                reply_policy=reply_policy,
                attachments=attachments,
                notify_block=notify_block,
                notify_auth=notify_auth,
            )
        )

    def mark(
        self,
        *,
        message_refs: Sequence[str],
        read: bool | None,
        answered: bool | None,
        archived: bool | None,
    ) -> list[GatewayMailboxMessageV1]:
        """Run the selected operation with validated scope."""

        return [
            self._wrap_message(message)
            for message in self.m_backend.mark(
                message_refs=[self.m_scope.decode(ref) for ref in message_refs],
                read=read,
                answered=answered,
                archived=archived,
            )
        ]

    def move(
        self,
        *,
        message_refs: Sequence[str],
        destination_box: str,
    ) -> list[GatewayMailboxMessageV1]:
        """Run the selected operation with validated scope."""

        return [
            self._wrap_message(message)
            for message in self.m_backend.move(
                message_refs=[self.m_scope.decode(ref) for ref in message_refs],
                destination_box=destination_box,
            )
        ]

    def archive(self, *, message_refs: Sequence[str]) -> list[GatewayMailboxMessageV1]:
        """Run the selected operation with validated scope."""

        return [
            self._wrap_message(message)
            for message in self.m_backend.archive(
                message_refs=[self.m_scope.decode(ref) for ref in message_refs]
            )
        ]


def build_scoped_mailbox_adapter(
    mailbox: MailboxResolvedConfig, *, authority: OnlineAuthorityContext | None = None
) -> ScopedMailboxAdapter:
    """Pin operation identity without a second health request after backend effects."""

    channel: MailChannel = "online" if mailbox.transport == "stalwart" else "offline"
    identity = MailboxBackendStatusV1(
        transport=mailbox.transport,
        principal_id=mailbox.principal_id,
        address=mailbox.address,
        bindings_version=mailbox.bindings_version,
    )
    backend = build_gateway_mailbox_adapter(mailbox)
    if isinstance(mailbox, StalwartMailboxResolvedConfig) and authority is not None:
        from houmao.mailbox.online_backend import ManagedOnlineBackend

        backend = ManagedOnlineBackend.from_context(
            mailbox,
            authority,
            backend_factory=lambda config, client: StalwartGatewayMailboxAdapter(config, client),
        )
    return ScopedMailboxAdapter.from_backend(
        backend,
        MailScope(mailbox.agent_id, channel, mailbox.binding_id),
        identity=identity,
    )
