"""Mail scope rejection and durable registration isolation."""

from pathlib import Path

import pytest

from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.mailbox import bootstrap_filesystem_mailbox
from houmao.mailbox.managed import (
    DeregisterMailboxRequest,
    RegisterMailboxRequest,
    deregister_mailbox,
    register_mailbox,
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
