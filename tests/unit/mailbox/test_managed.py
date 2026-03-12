from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from gig_agents.mailbox.filesystem import bootstrap_filesystem_mailbox
from gig_agents.mailbox.managed import (
    DeliveryRequest,
    ManagedMailboxOperationError,
    RepairRequest,
    StateUpdateRequest,
    deliver_message,
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
        ),
        to=[
            MailboxPrincipal(principal_id=principal.principal_id, address=principal.address)
            for principal in request.to
        ],
        cc=[
            MailboxPrincipal(principal_id=principal.principal_id, address=principal.address)
            for principal in request.cc
        ],
        reply_to=[
            MailboxPrincipal(principal_id=principal.principal_id, address=principal.address)
            for principal in request.reply_to
        ],
        subject=request.subject,
        body_markdown=body_markdown,
        attachments=list(request.attachments),
        headers=dict(request.headers),
    )
    staged_message.write_text(serialize_message_document(message), encoding="utf-8")


def test_deliver_message_moves_staged_file_creates_symlinks_and_updates_sqlite(
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
    staged_message.write_text("---\nprotocol_version: 1\n---\n\nBody\n", encoding="utf-8")

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
        paths.principal_mailbox_dir(sender.principal_id) / "sent" / f"{request.message_id}.md"
    )
    recipient_projection = (
        paths.principal_mailbox_dir(recipient.principal_id) / "inbox" / f"{request.message_id}.md"
    )

    assert result["ok"] is True
    assert not staged_message.exists()
    assert canonical_path.is_file()
    assert sender_projection.is_symlink()
    assert recipient_projection.is_symlink()
    assert sender_projection.resolve() == canonical_path
    assert recipient_projection.resolve() == canonical_path

    with sqlite3.connect(paths.sqlite_path) as connection:
        message_row = connection.execute(
            "SELECT canonical_path, subject FROM messages WHERE message_id = ?",
            (request.message_id,),
        ).fetchone()
        sender_state = connection.execute(
            "SELECT is_read FROM mailbox_state WHERE principal_id = ? AND message_id = ?",
            (sender.principal_id, request.message_id),
        ).fetchone()
        recipient_state = connection.execute(
            "SELECT is_read FROM mailbox_state WHERE principal_id = ? AND message_id = ?",
            (recipient.principal_id, request.message_id),
        ).fetchone()
        summary_row = connection.execute(
            "SELECT unread_count FROM thread_summaries WHERE thread_id = ?",
            (request.thread_id,),
        ).fetchone()

    assert message_row == (str(canonical_path), "Investigate parser drift")
    assert sender_state == (1,)
    assert recipient_state == (0,)
    assert summary_row == (1,)


def test_deliver_message_fails_for_missing_principal_registration(tmp_path: Path) -> None:
    sender = MailboxPrincipal(
        principal_id="AGENTSYS-sender",
        address="AGENTSYS-sender@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    staged_message = paths.staging_dir / "pending-message.md"
    staged_message.write_text("---\nprotocol_version: 1\n---\n\nBody\n", encoding="utf-8")

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
                    "principal_id": "AGENTSYS-missing",
                    "address": "AGENTSYS-missing@agents.localhost",
                }
            ],
            "cc": [],
            "reply_to": [],
            "subject": "Investigate parser drift",
            "attachments": [],
            "headers": {},
        }
    )
    _write_canonical_staged_message(staged_message, request)

    with pytest.raises(ManagedMailboxOperationError, match="missing principal registration"):
        deliver_message(paths.root, request)

    assert staged_message.exists()


def test_update_mailbox_state_marks_message_read_and_updates_thread_summary(
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
    staged_message.write_text("---\nprotocol_version: 1\n---\n\nBody\n", encoding="utf-8")

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
            "headers": {},
        }
    )
    _write_canonical_staged_message(staged_message, request)
    deliver_message(paths.root, request)

    result = update_mailbox_state(
        paths.root,
        StateUpdateRequest.from_payload(
            {
                "principal_id": recipient.principal_id,
                "message_id": request.message_id,
                "read": True,
            }
        ),
    )

    assert result["ok"] is True
    assert result["read"] is True

    with sqlite3.connect(paths.sqlite_path) as connection:
        state_row = connection.execute(
            "SELECT is_read FROM mailbox_state WHERE principal_id = ? AND message_id = ?",
            (recipient.principal_id, request.message_id),
        ).fetchone()
        summary_row = connection.execute(
            "SELECT unread_count FROM thread_summaries WHERE thread_id = ?",
            (request.thread_id,),
        ).fetchone()

    assert state_row == (1,)
    assert summary_row == (0,)


def test_repair_mailbox_index_rebuilds_missing_index_recreates_projections_and_quarantines_staging(
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
    staged_message.write_text("---\nprotocol_version: 1\n---\n\nBody\n", encoding="utf-8")

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
            "headers": {},
        }
    )
    _write_canonical_staged_message(staged_message, request)
    deliver_message(paths.root, request)

    canonical_path = paths.messages_dir / "2026-03-11" / f"{request.message_id}.md"
    recipient_projection = (
        paths.principal_mailbox_dir(recipient.principal_id) / "inbox" / f"{request.message_id}.md"
    )
    recipient_projection.unlink()
    orphaned_staging_file = paths.staging_dir / "orphaned.md"
    orphaned_staging_file.write_text("orphan", encoding="utf-8")
    paths.sqlite_path.unlink()

    result = repair_mailbox_index(paths.root, RepairRequest.from_payload({}))

    assert result["ok"] is True
    assert result["message_count"] == 1
    assert result["projection_count"] == 2
    assert result["defaulted_state_count"] == 2
    assert result["restored_state_count"] == 0
    assert result["staging_action"] == "quarantine"
    assert result["staging_artifact_count"] == 1
    quarantined_path = Path(str(result["staging_artifact_paths"][0]))
    assert quarantined_path.is_file()
    assert quarantined_path.read_text(encoding="utf-8") == "orphan"
    assert recipient_projection.is_symlink()
    assert recipient_projection.resolve() == canonical_path

    with sqlite3.connect(paths.sqlite_path) as connection:
        message_row = connection.execute(
            "SELECT canonical_path, subject FROM messages WHERE message_id = ?",
            (request.message_id,),
        ).fetchone()
        sender_state = connection.execute(
            "SELECT is_read FROM mailbox_state WHERE principal_id = ? AND message_id = ?",
            (sender.principal_id, request.message_id),
        ).fetchone()
        recipient_state = connection.execute(
            "SELECT is_read FROM mailbox_state WHERE principal_id = ? AND message_id = ?",
            (recipient.principal_id, request.message_id),
        ).fetchone()
        summary_row = connection.execute(
            "SELECT unread_count FROM thread_summaries WHERE thread_id = ?",
            (request.thread_id,),
        ).fetchone()

    assert message_row == (str(canonical_path), "Investigate parser drift")
    assert sender_state == (1,)
    assert recipient_state == (0,)
    assert summary_row == (1,)


def test_repair_mailbox_index_preserves_existing_mailbox_state_when_index_is_usable(
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
    staged_message.write_text("---\nprotocol_version: 1\n---\n\nBody\n", encoding="utf-8")

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
            "headers": {},
        }
    )
    _write_canonical_staged_message(staged_message, request)
    deliver_message(paths.root, request)
    update_mailbox_state(
        paths.root,
        StateUpdateRequest.from_payload(
            {
                "principal_id": recipient.principal_id,
                "message_id": request.message_id,
                "read": True,
                "starred": True,
            }
        ),
    )

    result = repair_mailbox_index(paths.root, RepairRequest.from_payload({}))

    assert result["ok"] is True
    assert result["restored_state_count"] == 2
    assert result["defaulted_state_count"] == 0

    with sqlite3.connect(paths.sqlite_path) as connection:
        recipient_state = connection.execute(
            """
            SELECT is_read, is_starred, is_archived, is_deleted
            FROM mailbox_state
            WHERE principal_id = ? AND message_id = ?
            """,
            (recipient.principal_id, request.message_id),
        ).fetchone()
        summary_row = connection.execute(
            "SELECT unread_count FROM thread_summaries WHERE thread_id = ?",
            (request.thread_id,),
        ).fetchone()

    assert recipient_state == (1, 1, 0, 0)
    assert summary_row == (0,)
