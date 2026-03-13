from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import subprocess
import sys

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

_REPO_ROOT = Path(__file__).resolve().parents[2].parent
_MANAGED_SCRIPT_DIR = _REPO_ROOT / "src" / "gig_agents" / "mailbox" / "assets" / "rules" / "scripts"


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
        sender=request.sender.to_mailbox_principal(),
        to=[principal.to_mailbox_principal() for principal in request.to],
        cc=[principal.to_mailbox_principal() for principal in request.cc],
        reply_to=[principal.to_mailbox_principal() for principal in request.reply_to],
        subject=request.subject,
        body_markdown=body_markdown,
        attachments=[attachment.to_mailbox_attachment() for attachment in request.attachments],
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


def _run_managed_script(
    script_name: str,
    *,
    mailbox_root: Path,
    payload_file: Path | None,
) -> subprocess.CompletedProcess[str]:
    """Execute one projected managed mailbox script for regression testing."""

    command = [
        sys.executable,
        str(_MANAGED_SCRIPT_DIR / script_name),
        "--mailbox-root",
        str(mailbox_root),
    ]
    if payload_file is not None:
        command.extend(["--payload-file", str(payload_file)])
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _parse_script_stdout(stdout: str) -> dict[str, object]:
    """Parse the one JSON result object emitted by a managed helper script."""

    output_lines = [line for line in stdout.splitlines() if line]
    assert len(output_lines) == 1
    payload = json.loads(output_lines[0])
    assert isinstance(payload, dict)
    return payload


def _delivery_payload(tmp_path: Path) -> dict[str, object]:
    """Return one valid managed delivery payload."""

    return {
        "staged_message_path": str(tmp_path / "staging" / "message.md"),
        "message_id": "msg-20260311T041500Z-a1b2c3d4e5f64798aabbccddeeff0011",
        "thread_id": "msg-20260311T041500Z-a1b2c3d4e5f64798aabbccddeeff0011",
        "in_reply_to": None,
        "references": [],
        "created_at_utc": "2026-03-11T04:15:00Z",
        "sender": {
            "principal_id": "AGENTSYS-sender",
            "address": "AGENTSYS-sender@agents.localhost",
        },
        "to": [
            {
                "principal_id": "AGENTSYS-recipient",
                "address": "AGENTSYS-recipient@agents.localhost",
            }
        ],
        "cc": [],
        "reply_to": [],
        "subject": "Investigate parser drift",
        "attachments": [
            {
                "attachment_id": "att-001",
                "kind": "path_ref",
                "path": str((tmp_path / "attachments" / "evidence.txt").resolve()),
                "media_type": "text/plain",
                "sha256": "a" * 64,
                "size_bytes": 7,
                "label": "Evidence",
            }
        ],
        "headers": {"tags": ["parser"]},
    }


def _state_update_payload() -> dict[str, object]:
    """Return one valid mailbox-state update payload."""

    return {
        "address": "AGENTSYS-recipient@agents.localhost",
        "message_id": "msg-20260311T041500Z-a1b2c3d4e5f64798aabbccddeeff0011",
        "read": True,
        "starred": False,
    }


def _repair_payload() -> dict[str, object]:
    """Return one valid repair payload."""

    return {
        "cleanup_staging": False,
        "quarantine_staging": True,
    }


def _register_payload(tmp_path: Path) -> dict[str, object]:
    """Return one valid mailbox registration payload."""

    return {
        "mode": "safe",
        "address": "AGENTSYS-register@agents.localhost",
        "owner_principal_id": "AGENTSYS-register",
        "mailbox_kind": "in_root",
        "mailbox_path": str(
            (tmp_path / "mailbox" / "mailboxes" / "AGENTSYS-register@agents.localhost").resolve()
        ),
        "display_name": "Register Agent",
    }


def _deregister_payload() -> dict[str, object]:
    """Return one valid mailbox deregistration payload."""

    return {
        "mode": "purge",
        "address": "AGENTSYS-register@agents.localhost",
    }


@pytest.mark.parametrize(
    ("request_cls", "payload_builder", "assertion"),
    [
        (
            DeliveryRequest,
            _delivery_payload,
            lambda request, tmp_path: (
                request.sender.address == "AGENTSYS-sender@agents.localhost"
                and request.attachments[0].size_bytes == 7
                and request.staged_message_path == (tmp_path / "staging" / "message.md").resolve()
            ),
        ),
        (
            StateUpdateRequest,
            lambda _tmp_path: _state_update_payload(),
            lambda request, _tmp_path: (
                request.read is True and request.starred is False and request.archived is None
            ),
        ),
        (
            RepairRequest,
            lambda _tmp_path: _repair_payload(),
            lambda request, _tmp_path: (
                request.cleanup_staging is False and request.quarantine_staging is True
            ),
        ),
        (
            RegisterMailboxRequest,
            _register_payload,
            lambda request, tmp_path: (
                request.mailbox_kind == "in_root"
                and request.mailbox_path
                == (
                    tmp_path / "mailbox" / "mailboxes" / "AGENTSYS-register@agents.localhost"
                ).resolve()
            ),
        ),
        (
            DeregisterMailboxRequest,
            lambda _tmp_path: _deregister_payload(),
            lambda request, _tmp_path: request.mode == "purge",
        ),
    ],
)
def test_managed_request_models_accept_valid_payloads(
    tmp_path: Path,
    request_cls: type[object],
    payload_builder,
    assertion,
) -> None:
    request = request_cls.from_payload(payload_builder(tmp_path))
    assert assertion(request, tmp_path)


@pytest.mark.parametrize(
    ("request_cls", "payload_builder", "expected_fragments"),
    [
        (
            DeliveryRequest,
            lambda tmp_path: {
                **_delivery_payload(tmp_path),
                "to": [
                    {
                        "principal_id": "AGENTSYS-recipient",
                        "address": "invalid recipient",
                    }
                ],
            },
            ("delivery payload", "$.to[0].address", "mailbox addresses"),
        ),
        (
            StateUpdateRequest,
            lambda _tmp_path: {
                **_state_update_payload(),
                "read": "yes",
            },
            ("state update payload", "$.read", "Input should be a valid boolean"),
        ),
        (
            RepairRequest,
            lambda _tmp_path: {
                **_repair_payload(),
                "cleanup_staging": "yes",
            },
            ("repair payload", "$.cleanup_staging", "Input should be a valid boolean"),
        ),
        (
            RegisterMailboxRequest,
            lambda tmp_path: {
                **_register_payload(tmp_path),
                "owner_principal_id": "   ",
            },
            ("register payload", "$.owner_principal_id", "must not be empty"),
        ),
        (
            DeregisterMailboxRequest,
            lambda _tmp_path: {
                **_deregister_payload(),
                "mode": "archive",
            },
            ("deregister payload", "$.mode", "Input should be 'deactivate' or 'purge'"),
        ),
    ],
)
def test_managed_request_models_reject_invalid_payloads(
    tmp_path: Path,
    request_cls: type[object],
    payload_builder,
    expected_fragments: tuple[str, ...],
) -> None:
    with pytest.raises(ManagedMailboxOperationError) as excinfo:
        request_cls.from_payload(payload_builder(tmp_path))

    error_message = str(excinfo.value)
    for fragment in expected_fragments:
        assert fragment in error_message


def test_register_mailbox_script_validation_failure_emits_one_json_error_without_mutation(
    tmp_path: Path,
) -> None:
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox")
    payload_file = tmp_path / "register-invalid.json"
    payload_file.write_text(
        json.dumps(
            {
                **_register_payload(tmp_path),
                "owner_principal_id": "   ",
            }
        ),
        encoding="utf-8",
    )

    result = _run_managed_script(
        "register_mailbox.py",
        mailbox_root=paths.root,
        payload_file=payload_file,
    )

    parsed = _parse_script_stdout(result.stdout)
    assert result.returncode == 1
    assert result.stderr == ""
    assert parsed["ok"] is False
    assert "$.owner_principal_id" in str(parsed["error"])
    assert not paths.mailbox_entry_path("AGENTSYS-register@agents.localhost").exists()
    with sqlite3.connect(paths.sqlite_path) as connection:
        registration_count = connection.execute(
            "SELECT COUNT(*) FROM mailbox_registrations"
        ).fetchone()
    assert registration_count == (0,)


def test_deliver_message_script_validation_failure_emits_one_json_error_without_mutation(
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

    staged_message = paths.staging_dir / "invalid-delivery.md"
    staged_message.write_text("pending\n", encoding="utf-8")

    payload = _delivery_payload(tmp_path)
    payload["staged_message_path"] = str(staged_message)
    payload["to"] = [{"principal_id": recipient.principal_id, "address": "invalid recipient"}]
    payload_file = tmp_path / "deliver-invalid.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")

    result = _run_managed_script(
        "deliver_message.py",
        mailbox_root=paths.root,
        payload_file=payload_file,
    )

    parsed = _parse_script_stdout(result.stdout)
    assert result.returncode == 1
    assert result.stderr == ""
    assert parsed["ok"] is False
    assert "$.to[0].address" in str(parsed["error"])
    assert staged_message.read_text(encoding="utf-8") == "pending\n"
    assert list(paths.messages_dir.rglob("*.md")) == []
    with sqlite3.connect(paths.sqlite_path) as connection:
        message_count = connection.execute("SELECT COUNT(*) FROM messages").fetchone()
        projection_count = connection.execute("SELECT COUNT(*) FROM mailbox_projections").fetchone()
    assert message_count == (0,)
    assert projection_count == (0,)


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
