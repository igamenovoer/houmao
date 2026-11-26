"""Mail scope rejection and durable registration isolation."""

from pathlib import Path
import sqlite3

import pytest

from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.mailbox import bootstrap_filesystem_mailbox
from houmao.mailbox.errors import GatewayMailboxError
from houmao.mailbox.filesystem import resolve_active_mailbox_local_sqlite_path
from houmao.mailbox.managed import (
    DeregisterMailboxRequest,
    RegisterMailboxRequest,
    StateUpdateRequest,
    deregister_mailbox,
    register_mailbox,
    update_mailbox_state,
)
from houmao.mailbox.scope import MailScope, MailboxScopeError
from houmao.mailbox.services import FilesystemGatewayMailboxAdapter, ScopedMailboxAdapter


def _adapter(root: Path, owner: str, address: str) -> ScopedMailboxAdapter:
    """Register a real owner and bind the service to that registration."""

    result = register_mailbox(
        root,
        RegisterMailboxRequest(
            mode="safe",
            address=address,
            owner_principal_id=owner,
            mailbox_kind="in_root",
            mailbox_path=root / "mailboxes" / address,
        ),
    )
    binding_id = str(result["active_registration_id"])
    config = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id=owner,
        agent_id=owner,
        binding_id=binding_id,
        address=address,
        filesystem_root=root,
        bindings_version="revision-one",
    )
    return ScopedMailboxAdapter.from_backend(
        FilesystemGatewayMailboxAdapter(config), MailScope(owner, "offline", binding_id)
    )


@pytest.mark.parametrize(
    "scope",
    [
        MailScope("another", "offline", "binding"),
        MailScope("owner", "online", "binding"),
        MailScope("owner", "offline", "replacement"),
    ],
)
def test_reference_cannot_cross_scope(scope: MailScope) -> None:
    reference = MailScope("owner", "offline", "binding").encode("filesystem:message")
    with pytest.raises(MailboxScopeError):
        scope.decode(reference)


def test_released_address_does_not_expose_replacement_to_old_service(tmp_path: Path) -> None:
    bootstrap_filesystem_mailbox(tmp_path)
    old = _adapter(tmp_path, "agent-old", "alice@example.test")
    old.send(
        to_addresses=["alice@example.test"],
        cc_addresses=[],
        subject="Private",
        body_content="old owner secret",
        attachments=[],
    )
    deregister_mailbox(
        tmp_path, DeregisterMailboxRequest(mode="deactivate", address="alice@example.test")
    )
    replacement = _adapter(tmp_path, "agent-new", "alice@example.test")
    assert (
        replacement.list_page(
            box="inbox", read_state="any", answered_state="any", archived=None, limit=10, since=None
        ).messages
        == []
    )
    with pytest.raises(MailboxScopeError):
        old.list_page(
            box="inbox", read_state="any", answered_state="any", archived=None, limit=10, since=None
        )


def test_wrong_reference_is_rejected_before_read_mutation(tmp_path: Path) -> None:
    bootstrap_filesystem_mailbox(tmp_path)
    sender = _adapter(tmp_path, "agent-a", "alice@example.test")
    recipient = _adapter(tmp_path, "agent-b", "bob@example.test")
    sent = sender.send(
        to_addresses=["bob@example.test"],
        cc_addresses=[],
        subject="Hello",
        body_content="body",
        attachments=[],
    )
    with pytest.raises(MailboxScopeError):
        recipient.read(message_ref=sent.message_ref, box=None)
    messages = recipient.list_page(
        box="inbox", read_state="unread", answered_state="any", archived=False, limit=10, since=None
    ).messages
    assert len(messages) == 1
    assert messages[0].unread is True


def test_filesystem_archive_and_mark_refresh_local_thread_summary(tmp_path: Path) -> None:
    """Archive and ordinary mark update counts from the same retained message rows."""

    bootstrap_filesystem_mailbox(tmp_path)
    sender = _adapter(tmp_path, "agent-a", "alice@example.test")
    address = "bob@example.test"
    recipient = _adapter(tmp_path, "agent-b", address)
    sender.send(
        to_addresses=[address],
        cc_addresses=[],
        subject="State update",
        body_content="canonical body",
        attachments=[],
    )
    message = recipient.list_page(
        box="inbox", read_state="any", answered_state="any", archived=None, limit=10, since=None
    ).messages[0]
    local_path = resolve_active_mailbox_local_sqlite_path(tmp_path, address=address)
    with sqlite3.connect(local_path) as connection:
        (message_id,) = connection.execute("SELECT message_id FROM message_state").fetchone()

    def local_state() -> tuple[object, ...]:
        """Read flags and the corresponding count from the recipient's database."""

        with sqlite3.connect(local_path) as connection:
            return tuple(
                connection.execute(
                    """
                    SELECT is_read, is_answered, is_starred, is_archived, box_name, unread_count
                    FROM message_state JOIN thread_summaries USING (thread_id)
                    WHERE message_id = ?
                    """,
                    (message_id,),
                ).fetchone()
            )

    update_mailbox_state(
        tmp_path,
        StateUpdateRequest(address=address, message_id=message_id, starred=True, answered=True),
    )
    assert local_state() == (0, 1, 1, 0, "inbox", 1)
    refs = [message.message_ref]
    (archived,) = recipient.archive(message_refs=refs)
    assert archived.archived and not archived.unread
    assert local_state() == (1, 1, 1, 1, "archive", 0)

    with sqlite3.connect(local_path) as connection:
        connection.execute("UPDATE thread_summaries SET unread_count = 99")
    recipient.move(message_refs=refs, destination_box="archive")
    assert local_state() == (1, 1, 1, 1, "archive", 0)
    recipient.move(message_refs=refs, destination_box="inbox")
    recipient.mark(message_refs=refs, read=False, answered=None, archived=None)
    assert local_state() == (0, 1, 1, 0, "inbox", 1)
    recipient.mark(message_refs=refs, read=True, answered=None, archived=None)
    assert local_state() == (1, 1, 1, 0, "inbox", 0)

    sent = sender.list_page(
        box="sent", read_state="any", answered_state="any", archived=None, limit=10, since=None
    ).messages[0]
    assert sent.subject == message.subject and not sent.archived


def test_filesystem_archive_retries_after_local_summary_update_failure(tmp_path: Path) -> None:
    """Keep local flags and the summary together when a shared move needs a retry."""

    bootstrap_filesystem_mailbox(tmp_path)
    sender = _adapter(tmp_path, "agent-a", "alice@example.test")
    address = "bob@example.test"
    recipient = _adapter(tmp_path, "agent-b", address)
    sender.send(
        to_addresses=[address],
        cc_addresses=[],
        subject="Retry state update",
        body_content="canonical body",
        attachments=[],
    )
    message = recipient.list_page(
        box="inbox", read_state="any", answered_state="any", archived=None, limit=10, since=None
    ).messages[0]
    local_path = resolve_active_mailbox_local_sqlite_path(tmp_path, address=address)
    with sqlite3.connect(local_path) as connection:
        (message_id,) = connection.execute("SELECT message_id FROM message_state").fetchone()
        connection.execute(
            """
            CREATE TRIGGER reject_summary_update BEFORE UPDATE ON thread_summaries
            BEGIN SELECT RAISE(ABORT, 'injected summary write failure'); END
            """
        )
    with pytest.raises(GatewayMailboxError, match="retry the move"):
        recipient.archive(message_refs=[message.message_ref])

    with sqlite3.connect(local_path) as connection:
        assert connection.execute(
            "SELECT is_archived, is_read, box_name FROM message_state"
        ).fetchone() == (0, 0, "inbox")
        assert connection.execute("SELECT unread_count FROM thread_summaries").fetchone() == (1,)
        connection.execute("DROP TRIGGER reject_summary_update")
    mailbox = tmp_path / "mailboxes" / address
    assert (mailbox / "archive" / f"{message_id}.md").is_symlink()
    assert not (mailbox / "inbox" / f"{message_id}.md").exists()
    (archived,) = recipient.archive(message_refs=[message.message_ref])
    assert archived.archived and not archived.unread
    with sqlite3.connect(local_path) as connection:
        assert connection.execute("SELECT unread_count FROM thread_summaries").fetchone() == (0,)
