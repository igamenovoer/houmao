from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from gig_agents.mailbox.filesystem import (
    bootstrap_filesystem_mailbox,
    load_active_mailbox_registration,
)
from gig_agents.mailbox.managed import (
    DeliveryRequest,
    DeregisterMailboxRequest,
    ManagedMailboxOperationError,
    RegisterMailboxRequest,
    RepairRequest,
    StateUpdateRequest,
    deliver_message,
    deregister_mailbox,
    register_mailbox,
    repair_mailbox_index,
    update_mailbox_state,
)
from gig_agents.mailbox.protocol import MailboxMessage, MailboxPrincipal, serialize_message_document


def _write_canonical_staged_message(
    staged_message: Path,
    request: DeliveryRequest,
    *,
    body_markdown: str = "Body\n",
) -> None:
    """Write a canonical staged mailbox document for delivery tests."""

    message = MailboxMessage(
        message_id=request.message_id,
        thread_id=request.thread_id,
        in_reply_to=request.in_reply_to,
        references=list(request.references),
        created_at_utc=request.created_at_utc,
        sender=MailboxPrincipal(
            principal_id=request.sender.principal_id,
            address=request.sender.address,
            display_name=request.sender.display_name,
            manifest_path_hint=request.sender.manifest_path_hint,
            role=request.sender.role,
        ),
        to=[principal.to_mailbox_principal() for principal in request.to],
        cc=[principal.to_mailbox_principal() for principal in request.cc],
        reply_to=[principal.to_mailbox_principal() for principal in request.reply_to],
        subject=request.subject,
        body_markdown=body_markdown,
        attachments=list(request.attachments),
        headers=dict(request.headers),
    )
    staged_message.write_text(serialize_message_document(message), encoding="utf-8")


def _mailbox_state_for_address(
    sqlite_path: Path,
    *,
    address: str,
    message_id: str,
) -> tuple[int, int, int, int] | None:
    with sqlite3.connect(sqlite_path) as connection:
        row = connection.execute(
            """
            SELECT state.is_read, state.is_starred, state.is_archived, state.is_deleted
            FROM mailbox_state AS state
            JOIN mailbox_registrations AS registration
              ON registration.registration_id = state.registration_id
            WHERE registration.address = ? AND state.message_id = ?
            """,
            (address, message_id),
        ).fetchone()
    return None if row is None else tuple(int(value) for value in row)


def test_register_mailbox_enforces_one_active_registration_per_address(tmp_path: Path) -> None:
    original = MailboxPrincipal(
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
    )
    replacement = RegisterMailboxRequest(
        mode="force",
        address=original.address,
        owner_principal_id="AGENTSYS-new-owner",
        mailbox_kind="in_root",
        mailbox_path=(tmp_path / "mailbox" / "mailboxes" / original.address).resolve(),
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=original)

    reused = register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="safe",
            address=original.address,
            owner_principal_id=original.principal_id,
            mailbox_kind="in_root",
            mailbox_path=paths.mailbox_entry_path(original.address),
        ),
    )
    assert reused["reused_existing"] is True

    with pytest.raises(ManagedMailboxOperationError, match="already has an active mailbox"):
        register_mailbox(
            paths.root,
            RegisterMailboxRequest(
                mode="safe",
                address=original.address,
                owner_principal_id="AGENTSYS-conflict",
                mailbox_kind="in_root",
                mailbox_path=paths.mailbox_entry_path(original.address),
            ),
        )

    forced = register_mailbox(paths.root, replacement)
    assert forced["ok"] is True
    assert forced["replaced_registration_id"]

    active_registration = load_active_mailbox_registration(paths.root, address=original.address)
    assert active_registration.owner_principal_id == "AGENTSYS-new-owner"

    with sqlite3.connect(paths.sqlite_path) as connection:
        rows = connection.execute(
            """
            SELECT owner_principal_id, status
            FROM mailbox_registrations
            WHERE address = ?
            ORDER BY created_at_utc ASC
            """,
            (original.address,),
        ).fetchall()

    assert rows[0] == ("AGENTSYS-research", "inactive")
    assert rows[1] == ("AGENTSYS-new-owner", "active")


def test_register_mailbox_stash_preserves_previous_mailbox_artifact(tmp_path: Path) -> None:
    original = MailboxPrincipal(
        principal_id="AGENTSYS-bob",
        address="AGENTSYS-bob@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=original)
    preserved_note = paths.mailbox_entry_path(original.address) / "archive" / "keep.md"
    preserved_note.write_text("keep me\n", encoding="utf-8")

    result = register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="stash",
            address=original.address,
            owner_principal_id="AGENTSYS-carol",
            mailbox_kind="in_root",
            mailbox_path=paths.mailbox_entry_path(original.address),
        ),
    )

    assert result["ok"] is True
    stashed_path = Path(str(result["stashed_mailbox_path"]))
    assert stashed_path.is_dir()
    assert (stashed_path / "archive" / "keep.md").read_text(encoding="utf-8") == "keep me\n"
    assert paths.mailbox_entry_path(original.address).is_dir()

    with sqlite3.connect(paths.sqlite_path) as connection:
        rows = connection.execute(
            """
            SELECT owner_principal_id, status, mailbox_entry_path
            FROM mailbox_registrations
            WHERE address = ?
            ORDER BY created_at_utc ASC
            """,
            (original.address,),
        ).fetchall()

    assert rows[0] == ("AGENTSYS-bob", "stashed", str(stashed_path))
    assert rows[1] == ("AGENTSYS-carol", "active", str(paths.mailbox_entry_path(original.address)))


def test_deliver_message_routes_by_address_and_state_updates_use_active_registration(
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="AGENTSYS-sender",
        address="AGENTSYS-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="AGENTSYS-recipient",
        address="AGENTSYS-recipient@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    bootstrap_filesystem_mailbox(paths.root, principal=recipient)

    staged_message = paths.staging_dir / "pending-message.md"
    request = DeliveryRequest.from_payload(
        {
            "staged_message_path": str(staged_message),
            "message_id": "msg-20260311T041500Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "thread_id": "msg-20260311T041500Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "in_reply_to": None,
            "references": [],
            "created_at_utc": "2026-03-11T04:15:00Z",
            "sender": {
                "principal_id": sender.principal_id,
                "address": sender.address,
            },
            "to": [
                {
                    "principal_id": recipient.principal_id,
                    "address": recipient.address,
                }
            ],
            "cc": [],
            "reply_to": [],
            "subject": "Investigate parser drift",
            "attachments": [],
            "headers": {"tags": ["parser"]},
        }
    )
    _write_canonical_staged_message(staged_message, request)

    result = deliver_message(paths.root, request)

    canonical_path = paths.messages_dir / "2026-03-11" / f"{request.message_id}.md"
    sender_projection = (
        paths.mailbox_entry_path(sender.address) / "sent" / f"{request.message_id}.md"
    )
    recipient_projection = (
        paths.mailbox_entry_path(recipient.address) / "inbox" / f"{request.message_id}.md"
    )

    assert result["ok"] is True
    assert canonical_path.is_file()
    assert sender_projection.is_symlink()
    assert recipient_projection.is_symlink()
    assert sender_projection.resolve() == canonical_path
    assert recipient_projection.resolve() == canonical_path
    assert _mailbox_state_for_address(
        paths.sqlite_path,
        address=sender.address,
        message_id=request.message_id,
    ) == (1, 0, 0, 0)
    assert _mailbox_state_for_address(
        paths.sqlite_path,
        address=recipient.address,
        message_id=request.message_id,
    ) == (0, 0, 0, 0)

    state_result = update_mailbox_state(
        paths.root,
        StateUpdateRequest.from_payload(
            {
                "address": recipient.address,
                "message_id": request.message_id,
                "read": True,
                "starred": True,
            }
        ),
    )

    assert state_result["ok"] is True
    assert state_result["read"] is True
    assert _mailbox_state_for_address(
        paths.sqlite_path,
        address=recipient.address,
        message_id=request.message_id,
    ) == (1, 1, 0, 0)


def test_deregister_mailbox_purge_preserves_canonical_history_and_symlink_targets(
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="AGENTSYS-sender",
        address="AGENTSYS-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="AGENTSYS-private",
        address="AGENTSYS-private@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    private_mailbox = tmp_path / "private-mailboxes" / recipient.address

    register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="safe",
            address=recipient.address,
            owner_principal_id=recipient.principal_id,
            mailbox_kind="symlink",
            mailbox_path=private_mailbox.resolve(),
        ),
    )

    staged_message = paths.staging_dir / "pending-message.md"
    request = DeliveryRequest.from_payload(
        {
            "staged_message_path": str(staged_message),
            "message_id": "msg-20260311T051500Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "thread_id": "msg-20260311T051500Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "in_reply_to": None,
            "references": [],
            "created_at_utc": "2026-03-11T05:15:00Z",
            "sender": {
                "principal_id": sender.principal_id,
                "address": sender.address,
            },
            "to": [
                {
                    "principal_id": recipient.principal_id,
                    "address": recipient.address,
                }
            ],
            "cc": [],
            "reply_to": [],
            "subject": "Private mailbox test",
            "attachments": [],
            "headers": {},
        }
    )
    _write_canonical_staged_message(staged_message, request)
    deliver_message(paths.root, request)

    recipient_registration = load_active_mailbox_registration(paths.root, address=recipient.address)
    result = deregister_mailbox(
        paths.root,
        DeregisterMailboxRequest(mode="purge", address=recipient.address),
    )

    assert result["ok"] is True
    assert private_mailbox.is_dir()
    assert not paths.mailbox_entry_path(recipient.address).exists()

    with sqlite3.connect(paths.sqlite_path) as connection:
        message_row = connection.execute(
            "SELECT canonical_path, sender_address FROM messages WHERE message_id = ?",
            (request.message_id,),
        ).fetchone()
        recipient_row = connection.execute(
            """
            SELECT address, owner_principal_id, delivered_registration_id
            FROM message_recipients
            WHERE message_id = ? AND recipient_kind = 'to'
            """,
            (request.message_id,),
        ).fetchone()
        projection_row = connection.execute(
            "SELECT 1 FROM mailbox_projections WHERE registration_id = ?",
            (recipient_registration.registration_id,),
        ).fetchone()
        state_row = connection.execute(
            "SELECT 1 FROM mailbox_state WHERE registration_id = ?",
            (recipient_registration.registration_id,),
        ).fetchone()

    assert message_row == (
        str(paths.messages_dir / "2026-03-11" / f"{request.message_id}.md"),
        sender.address,
    )
    assert recipient_row == (
        recipient.address,
        recipient.principal_id,
        recipient_registration.registration_id,
    )
    assert projection_row is None
    assert state_row is None


def test_repair_mailbox_index_rebuilds_address_based_projections_and_state(tmp_path: Path) -> None:
    sender = MailboxPrincipal(
        principal_id="AGENTSYS-sender",
        address="AGENTSYS-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="AGENTSYS-recipient",
        address="AGENTSYS-recipient@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    bootstrap_filesystem_mailbox(paths.root, principal=recipient)

    staged_message = paths.staging_dir / "pending-message.md"
    request = DeliveryRequest.from_payload(
        {
            "staged_message_path": str(staged_message),
            "message_id": "msg-20260311T061500Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "thread_id": "msg-20260311T061500Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "in_reply_to": None,
            "references": [],
            "created_at_utc": "2026-03-11T06:15:00Z",
            "sender": {
                "principal_id": sender.principal_id,
                "address": sender.address,
            },
            "to": [
                {
                    "principal_id": recipient.principal_id,
                    "address": recipient.address,
                }
            ],
            "cc": [],
            "reply_to": [],
            "subject": "Repair mailbox index",
            "attachments": [],
            "headers": {},
        }
    )
    _write_canonical_staged_message(staged_message, request)
    deliver_message(paths.root, request)

    canonical_path = paths.messages_dir / "2026-03-11" / f"{request.message_id}.md"
    recipient_projection = (
        paths.mailbox_entry_path(recipient.address) / "inbox" / f"{request.message_id}.md"
    )
    recipient_projection.unlink()
    orphaned_staging_file = paths.staging_dir / "orphaned.md"
    orphaned_staging_file.write_text("orphan", encoding="utf-8")
    paths.sqlite_path.unlink()

    result = repair_mailbox_index(paths.root, RepairRequest.from_payload({}))

    assert result["ok"] is True
    assert result["message_count"] == 1
    assert result["projection_count"] == 2
    assert result["registration_count"] == 2
    assert result["defaulted_state_count"] == 2
    assert result["restored_state_count"] == 0
    assert result["staging_action"] == "quarantine"
    assert result["staging_artifact_count"] == 1
    assert recipient_projection.is_symlink()
    assert recipient_projection.resolve() == canonical_path
    assert _mailbox_state_for_address(
        paths.sqlite_path,
        address=sender.address,
        message_id=request.message_id,
    ) == (1, 0, 0, 0)
    assert _mailbox_state_for_address(
        paths.sqlite_path,
        address=recipient.address,
        message_id=request.message_id,
    ) == (0, 0, 0, 0)
