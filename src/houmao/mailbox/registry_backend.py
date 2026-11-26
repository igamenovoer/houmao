"""Remote offline backend implementing the same shared mail operation protocol."""

from __future__ import annotations

from functools import wraps
from pathlib import Path
from typing import Callable, ParamSpec, Sequence, TypeVar

from pydantic import ValidationError

from houmao.agents.mailbox_runtime_models import RemoteRegistryMailboxResolvedConfig
from houmao.mailbox.models import (
    GatewayMailArchiveRequestV1,
    GatewayMailAttachmentUploadV1,
    GatewayMailboxMessageV1,
    GatewayMailListRequestV1,
    GatewayMailMarkRequestV1,
    GatewayMailMessageRequestV1,
    GatewayMailMoveRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    MailboxBackendStatusV1,
)
from houmao.mailbox.protocol import MailboxNotifyAuth, MailboxNotifyBlock, OperatorOriginReplyPolicy
from houmao.mailbox.policy import MailPolicyReceipt, SignedMailPolicyUpdate
from houmao.mailbox.registry import OfflineRegistryError
from houmao.mailbox.registry_client import OfflineRegistryClient
from houmao.mailbox.pagination import BackendMailPage
from houmao.mailbox.scope import MailScope, MailboxScopeError
from houmao.mailbox.services import GatewayMailboxError, GatewayMailboxUnsupportedError


_Parameters = ParamSpec("_Parameters")
_Result = TypeVar("_Result")


def _registry_operation(function: Callable[_Parameters, _Result]) -> Callable[_Parameters, _Result]:
    """Translate transport failures into the shared backend error contract."""

    @wraps(function)
    def translated(*args: _Parameters.args, **kwargs: _Parameters.kwargs) -> _Result:
        """Preserve binding conflicts while containing one channel's backend outage."""

        try:
            return function(*args, **kwargs)
        except OfflineRegistryError as exc:
            if exc.code in {"binding_conflict", "membership_conflict"}:
                raise MailboxScopeError("remote offline membership changed") from exc
            if exc.code == "unsupported_operation":
                raise GatewayMailboxUnsupportedError(
                    "offline registry operation is unsupported"
                ) from exc
            raise GatewayMailboxError(f"offline registry operation failed ({exc.code})") from exc
        except OSError as exc:
            raise GatewayMailboxError(
                "offline registry credential or attachment could not be read"
            ) from exc

    return translated


class RemoteRegistryMailboxAdapter:
    """Translate raw backend handles and host-local attachment content for one member."""

    def __init__(self) -> None:
        """Initialize an unbound adapter; use ``from_config``."""

        self.m_mailbox: RemoteRegistryMailboxResolvedConfig
        self.m_client: OfflineRegistryClient
        self.m_scope: MailScope

    @classmethod
    def from_config(
        cls, config: RemoteRegistryMailboxResolvedConfig
    ) -> RemoteRegistryMailboxAdapter:
        """Select the explicit member credential and immutable registry registration."""

        if config.credential_file is None:
            raise ValueError("remote offline mail requires a resolved private credential file")
        instance = cls()
        instance.m_mailbox = config
        instance.m_client = OfflineRegistryClient.from_url(
            config.registry_url, config.credential_file
        )
        instance.m_scope = MailScope(config.agent_id, "offline", config.binding_id)
        return instance

    @_registry_operation
    def status(self) -> MailboxBackendStatusV1:
        """Check durable registration separately from body or gateway presence."""

        member = self.m_client.self_status()
        if (
            member.status != "active"
            or member.agent_id != self.m_mailbox.agent_id
            or member.registration_id != self.m_mailbox.binding_id
        ):
            raise MailboxScopeError("remote offline membership changed")
        return MailboxBackendStatusV1(
            transport="registry",
            principal_id=member.agent_id,
            address=member.address,
            bindings_version=self.m_mailbox.bindings_version,
            placement_writable=member.placement_writable,
        )

    def apply_policy(self, request: SignedMailPolicyUpdate) -> MailPolicyReceipt:
        """Relay exact owner authority and preserve the transport's evidence."""

        update = request.update
        if update.binding_id != self.m_mailbox.binding_id:
            return MailPolicyReceipt(
                status="refused", operation_id=update.operation_id, detail="binding_conflict"
            )
        try:
            receipt = self.m_client.apply_policy(request)
        except OfflineRegistryError as exc:
            if exc.status in {401, 403, 409, 422}:
                return MailPolicyReceipt(
                    status="refused", operation_id=update.operation_id, detail=exc.code
                )
            if exc.status == 404:
                return MailPolicyReceipt(
                    status="unsupported", operation_id=update.operation_id, detail=exc.code
                )
        except (OSError, ValidationError):
            pass
        else:
            if receipt.operation_id == update.operation_id:
                return receipt
        return MailPolicyReceipt(
            status="uncertain", operation_id=update.operation_id, detail="registry_unavailable"
        )

    def _raw(self, message: GatewayMailboxMessageV1) -> GatewayMailboxMessageV1:
        """Expose raw handles to the common outer scope wrapper, validating server ownership."""

        return message.model_copy(
            update={
                "message_ref": self.m_scope.decode(message.message_ref),
                "thread_ref": self.m_scope.decode(message.thread_ref, kind="thread")
                if message.thread_ref
                else None,
            }
        )

    @_registry_operation
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
        """Page remote metadata and preserve server-issued scope and continuation."""

        request = GatewayMailListRequestV1.model_validate(
            {
                "expected_binding_id": self.m_mailbox.binding_id,
                "box": box,
                "read_state": read_state,
                "answered_state": answered_state,
                "archived": archived,
                "limit": limit,
                "since": since,
                "cursor": self.m_scope.encode(cursor, kind="cursor") if cursor else None,
            }
        )
        page = self.m_client.list_page(request)
        return BackendMailPage(
            messages=[self._raw(message) for message in page.messages],
            next_cursor=self.m_scope.decode(page.next_cursor, kind="cursor")
            if page.next_cursor
            else None,
            has_more=page.has_more,
            complete=page.complete,
            total_count=page.total_count,
        )

    @_registry_operation
    def peek(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        """Fetch one message without changing its read flag."""

        request = GatewayMailMessageRequestV1(
            expected_binding_id=self.m_mailbox.binding_id,
            message_ref=self.m_scope.encode(message_ref),
            box=box,
        )
        return self._raw(self.m_client.mail("peek", request)[0])

    @_registry_operation
    def read(self, *, message_ref: str, box: str | None) -> GatewayMailboxMessageV1:
        """Fetch one message and persist its read flag on the registry host."""

        request = GatewayMailMessageRequestV1(
            expected_binding_id=self.m_mailbox.binding_id,
            message_ref=self.m_scope.encode(message_ref),
            box=box,
        )
        return self._raw(self.m_client.mail("read", request)[0])

    @_registry_operation
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
        """Upload local content and send within this registry's offline address space."""

        request = GatewayMailSendRequestV1(
            expected_binding_id=self.m_mailbox.binding_id,
            to=list(to_addresses),
            cc=list(cc_addresses),
            subject=subject,
            body_content=body_content,
            attachments=self._uploads(attachments),
            notify_block=notify_block,
            notify_auth=notify_auth,
        )
        return self._raw(self.m_client.mail("send", request)[0])

    @_registry_operation
    def reply(
        self,
        *,
        message_ref: str,
        body_content: str,
        attachments: Sequence[GatewayMailAttachmentUploadV1],
        notify_block: MailboxNotifyBlock | None = None,
        notify_auth: MailboxNotifyAuth | None = None,
    ) -> GatewayMailboxMessageV1:
        """Reply in the originating offline registration and preserve read/answered semantics."""

        request = GatewayMailReplyRequestV1(
            expected_binding_id=self.m_mailbox.binding_id,
            message_ref=self.m_scope.encode(message_ref),
            body_content=body_content,
            attachments=self._uploads(attachments),
            notify_block=notify_block,
            notify_auth=notify_auth,
        )
        return self._raw(self.m_client.mail("reply", request)[0])

    @_registry_operation
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
        """Reject operator impersonation through ordinary member credentials."""

        raise GatewayMailboxUnsupportedError(
            "remote member credentials cannot post as the operator"
        )

    @_registry_operation
    def mark(
        self,
        *,
        message_refs: Sequence[str],
        read: bool | None,
        answered: bool | None,
        archived: bool | None,
    ) -> list[GatewayMailboxMessageV1]:
        """Update selected lifecycle flags on the authoritative remote mailbox."""

        request = GatewayMailMarkRequestV1(
            expected_binding_id=self.m_mailbox.binding_id,
            message_refs=[self.m_scope.encode(ref) for ref in message_refs],
            read=read,
            answered=answered,
            archived=archived,
        )
        return [self._raw(message) for message in self.m_client.mail("mark", request)]

    @_registry_operation
    def move(
        self, *, message_refs: Sequence[str], destination_box: str
    ) -> list[GatewayMailboxMessageV1]:
        """Move selected messages without selecting another channel."""

        request = GatewayMailMoveRequestV1(
            expected_binding_id=self.m_mailbox.binding_id,
            message_refs=[self.m_scope.encode(ref) for ref in message_refs],
            destination_box=destination_box,
        )
        return [self._raw(message) for message in self.m_client.mail("move", request)]

    @_registry_operation
    def archive(self, *, message_refs: Sequence[str]) -> list[GatewayMailboxMessageV1]:
        """Archive selected work as the explicit completion action."""

        request = GatewayMailArchiveRequestV1(
            expected_binding_id=self.m_mailbox.binding_id,
            message_refs=[self.m_scope.encode(ref) for ref in message_refs],
        )
        return [self._raw(message) for message in self.m_client.mail("archive", request)]

    def _uploads(
        self, attachments: Sequence[GatewayMailAttachmentUploadV1]
    ) -> list[GatewayMailAttachmentUploadV1]:
        """Read only this host's explicit files and transfer bounded managed content."""

        uploads = []
        for attachment in attachments:
            path = Path(attachment.path).expanduser().resolve()
            with path.open("rb") as handle:
                content = handle.read(10 * 1024 * 1024 + 1)
            uploaded = self.m_client.upload(content, label=attachment.label or path.name)
            uploads.append(
                GatewayMailAttachmentUploadV1(path=uploaded.locator, label=uploaded.label)
            )
        return uploads
