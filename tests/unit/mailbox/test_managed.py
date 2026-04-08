from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from houmao.mailbox.filesystem import (
    MailboxBootstrapError,
    bootstrap_filesystem_mailbox,
    initialize_mailbox_local_sqlite_schema,
    load_active_mailbox_registration,
)
from houmao.mailbox.managed import (
    DeliveryRequest,
    DeregisterMailboxRequest,
    ManagedMailboxOperationError,
    RegisterMailboxRequest,
    RepairRequest,
    StateUpdateRequest,
    cleanup_mailbox_registrations,
    deliver_message,
    deregister_mailbox,
    register_mailbox,
    repair_mailbox_index,
    update_mailbox_state,
)
from houmao.mailbox.protocol import (
    HOUMAO_OPERATOR_ADDRESS,
    HOUMAO_OPERATOR_PRINCIPAL_ID,
    HOUMAO_OPERATOR_ROLE,
    MailboxMessage,
    MailboxPrincipal,
    serialize_message_document,
)

_REPO_ROOT = Path(__file__).resolve().parents[2].parent
_MANAGED_SCRIPT_DIR = _REPO_ROOT / "src" / "houmao" / "mailbox" / "assets" / "rules" / "scripts"


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
    registration = load_active_mailbox_registration(sqlite_path.parent, address=address)
    with sqlite3.connect(registration.local_sqlite_path) as connection:
        row = connection.execute(
            """
            SELECT is_read, is_starred, is_archived, is_deleted
            FROM message_state
            WHERE message_id = ?
            """,
            (message_id,),
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
            "principal_id": "HOUMAO-sender",
            "address": "HOUMAO-sender@agents.localhost",
        },
        "to": [
            {
                "principal_id": "HOUMAO-recipient",
                "address": "HOUMAO-recipient@agents.localhost",
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
        "address": "HOUMAO-recipient@agents.localhost",
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
        "address": "HOUMAO-register@agents.localhost",
        "owner_principal_id": "HOUMAO-register",
        "mailbox_kind": "in_root",
        "mailbox_path": str(
            (tmp_path / "mailbox" / "mailboxes" / "HOUMAO-register@agents.localhost").resolve()
        ),
        "display_name": "Register Agent",
    }


def _deregister_payload() -> dict[str, object]:
    """Return one valid mailbox deregistration payload."""

    return {
        "mode": "purge",
        "address": "HOUMAO-register@agents.localhost",
    }


@pytest.mark.parametrize(
    ("request_cls", "payload_builder", "assertion"),
    [
        (
            DeliveryRequest,
            _delivery_payload,
            lambda request, tmp_path: (
                request.sender.address == "HOUMAO-sender@agents.localhost"
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
                    tmp_path / "mailbox" / "mailboxes" / "HOUMAO-register@agents.localhost"
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
                        "principal_id": "HOUMAO-recipient",
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
    assert not paths.mailbox_entry_path("HOUMAO-register@agents.localhost").exists()
    with sqlite3.connect(paths.sqlite_path) as connection:
        registration_count = connection.execute(
            "SELECT COUNT(*) FROM mailbox_registrations"
        ).fetchone()
    assert registration_count == (1,)


def test_bootstrap_filesystem_mailbox_provisions_reserved_operator_account(tmp_path: Path) -> None:
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox")

    registration = load_active_mailbox_registration(paths.root, address=HOUMAO_OPERATOR_ADDRESS)

    assert registration is not None
    assert registration.address == HOUMAO_OPERATOR_ADDRESS
    assert registration.owner_principal_id == HOUMAO_OPERATOR_PRINCIPAL_ID
    assert registration.role == HOUMAO_OPERATOR_ROLE


def test_deregister_mailbox_rejects_reserved_operator_account(tmp_path: Path) -> None:
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox")

    with pytest.raises(ManagedMailboxOperationError, match="reserved operator registration"):
        deregister_mailbox(
            paths.root,
            DeregisterMailboxRequest(mode="purge", address=HOUMAO_OPERATOR_ADDRESS),
        )


def test_cleanup_mailbox_registrations_preserves_reserved_operator_account(tmp_path: Path) -> None:
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox")

    result = cleanup_mailbox_registrations(paths.root, dry_run=True)

    assert result.removed == ()
    assert any(
        record.address == HOUMAO_OPERATOR_ADDRESS and record.outcome == "preserved"
        for record in result.preserved
    )


def test_register_mailbox_request_rejects_reserved_houmao_local_part_for_ordinary_account() -> None:
    with pytest.raises(
        ValueError,
        match="reserved for Houmao-owned system principals",
    ):
        RegisterMailboxRequest(
            mode="safe",
            address="HOUMAO-alpha@houmao.localhost",
            owner_principal_id="HOUMAO-alpha",
            mailbox_kind="in_root",
            mailbox_path=Path("/tmp/mailboxes/HOUMAO-alpha@houmao.localhost"),
            role="researcher",
        )


def test_deliver_message_script_validation_failure_emits_one_json_error_without_mutation(
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-recipient",
        address="HOUMAO-recipient@agents.localhost",
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
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
    )
    replacement = RegisterMailboxRequest(
        mode="force",
        address=original.address,
        owner_principal_id="HOUMAO-new-owner",
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
                owner_principal_id="HOUMAO-conflict",
                mailbox_kind="in_root",
                mailbox_path=paths.mailbox_entry_path(original.address),
            ),
        )

    forced = register_mailbox(paths.root, replacement)
    assert forced["ok"] is True
    assert forced["replaced_registration_id"]

    active_registration = load_active_mailbox_registration(paths.root, address=original.address)
    assert active_registration.owner_principal_id == "HOUMAO-new-owner"

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

    assert rows[0] == ("HOUMAO-research", "inactive")
    assert rows[1] == ("HOUMAO-new-owner", "active")


def test_register_mailbox_stash_preserves_previous_mailbox_artifact(tmp_path: Path) -> None:
    original = MailboxPrincipal(
        principal_id="HOUMAO-bob",
        address="HOUMAO-bob@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=original)
    preserved_note = paths.mailbox_entry_path(original.address) / "archive" / "keep.md"
    preserved_note.write_text("keep me\n", encoding="utf-8")

    result = register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="stash",
            address=original.address,
            owner_principal_id="HOUMAO-carol",
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

    assert rows[0] == ("HOUMAO-bob", "stashed", str(stashed_path))
    assert rows[1] == ("HOUMAO-carol", "active", str(paths.mailbox_entry_path(original.address)))


def test_register_mailbox_safe_symlink_reuses_same_target_registration(tmp_path: Path) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-private",
        address="HOUMAO-private@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    private_mailbox = (tmp_path / "private-mailboxes" / recipient.address).resolve()

    created = register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="safe",
            address=recipient.address,
            owner_principal_id=recipient.principal_id,
            mailbox_kind="symlink",
            mailbox_path=private_mailbox,
        ),
    )
    reused = register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="safe",
            address=recipient.address,
            owner_principal_id=recipient.principal_id,
            mailbox_kind="symlink",
            mailbox_path=private_mailbox,
        ),
    )

    assert created["ok"] is True
    assert reused["reused_existing"] is True
    assert paths.mailbox_entry_path(recipient.address).is_symlink()
    assert paths.mailbox_entry_path(recipient.address).resolve() == private_mailbox


def test_register_mailbox_safe_symlink_rejects_real_directory_at_address_slot(
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-private",
        address="HOUMAO-private@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    paths.mailbox_entry_path(recipient.address).mkdir(parents=True, exist_ok=True)

    with pytest.raises(
        ManagedMailboxOperationError,
        match="mailbox entry already exists and is not a symlink",
    ):
        register_mailbox(
            paths.root,
            RegisterMailboxRequest(
                mode="safe",
                address=recipient.address,
                owner_principal_id=recipient.principal_id,
                mailbox_kind="symlink",
                mailbox_path=(tmp_path / "private-mailboxes" / recipient.address).resolve(),
            ),
        )


def test_register_mailbox_safe_symlink_rejects_different_existing_symlink_target(
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-private",
        address="HOUMAO-private@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    competing_target = (tmp_path / "competing-private-mailboxes" / recipient.address).resolve()
    competing_target.mkdir(parents=True, exist_ok=True)
    paths.mailbox_entry_path(recipient.address).parent.mkdir(parents=True, exist_ok=True)
    paths.mailbox_entry_path(recipient.address).symlink_to(competing_target)

    with pytest.raises(
        ManagedMailboxOperationError,
        match="mailbox symlink points to a different target",
    ):
        register_mailbox(
            paths.root,
            RegisterMailboxRequest(
                mode="safe",
                address=recipient.address,
                owner_principal_id=recipient.principal_id,
                mailbox_kind="symlink",
                mailbox_path=(tmp_path / "private-mailboxes" / recipient.address).resolve(),
            ),
        )


def test_register_mailbox_safe_symlink_rejects_private_mailbox_inside_shared_root(
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-private",
        address="HOUMAO-private@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)

    with pytest.raises(
        ManagedMailboxOperationError,
        match="outside the shared mailbox root",
    ):
        register_mailbox(
            paths.root,
            RegisterMailboxRequest(
                mode="safe",
                address=recipient.address,
                owner_principal_id=recipient.principal_id,
                mailbox_kind="symlink",
                mailbox_path=(paths.root / "private" / recipient.address).resolve(),
            ),
        )


def test_register_mailbox_rejects_duplicate_private_mailbox_path_across_addresses(
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    first = MailboxPrincipal(
        principal_id="HOUMAO-private-1",
        address="HOUMAO-private-1@agents.localhost",
    )
    second = MailboxPrincipal(
        principal_id="HOUMAO-private-2",
        address="HOUMAO-private-2@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    shared_private_mailbox = (tmp_path / "private-mailboxes" / "shared").resolve()

    register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="safe",
            address=first.address,
            owner_principal_id=first.principal_id,
            mailbox_kind="symlink",
            mailbox_path=shared_private_mailbox,
        ),
    )

    with pytest.raises(
        ManagedMailboxOperationError,
        match="already active for",
    ):
        register_mailbox(
            paths.root,
            RegisterMailboxRequest(
                mode="safe",
                address=second.address,
                owner_principal_id=second.principal_id,
                mailbox_kind="symlink",
                mailbox_path=shared_private_mailbox,
            ),
        )


def test_register_mailbox_safe_symlink_preserves_existing_private_mailbox_state(
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-private",
        address="HOUMAO-private@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    private_mailbox = (tmp_path / "private-mailboxes" / recipient.address).resolve()
    (private_mailbox / "archive").mkdir(parents=True, exist_ok=True)
    (private_mailbox / "archive" / "keep.md").write_text("keep me\n", encoding="utf-8")
    initialize_mailbox_local_sqlite_schema(private_mailbox / "mailbox.sqlite")
    with sqlite3.connect(private_mailbox / "mailbox.sqlite") as connection:
        connection.execute(
            """
            INSERT INTO message_state (
                message_id,
                thread_id,
                created_at_utc,
                subject,
                is_read,
                is_starred,
                is_archived,
                is_deleted
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "msg-1",
                "thread-1",
                "2026-03-29T12:00:00Z",
                "Preserve local state",
                1,
                0,
                0,
                0,
            ),
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
            """,
            ("thread-1", "preserve local state", "msg-1", "2026-03-29T12:00:00Z", 0),
        )
        connection.commit()

    result = register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="safe",
            address=recipient.address,
            owner_principal_id=recipient.principal_id,
            mailbox_kind="symlink",
            mailbox_path=private_mailbox,
        ),
    )
    registration = load_active_mailbox_registration(paths.root, address=recipient.address)

    assert result["ok"] is True
    assert registration.mailbox_kind == "symlink"
    assert registration.mailbox_path == private_mailbox
    assert paths.mailbox_entry_path(recipient.address).is_symlink()
    assert (private_mailbox / "archive" / "keep.md").read_text(encoding="utf-8") == "keep me\n"
    with sqlite3.connect(private_mailbox / "mailbox.sqlite") as connection:
        row = connection.execute(
            "SELECT message_id, thread_id FROM message_state WHERE message_id = ?",
            ("msg-1",),
        ).fetchone()
    assert row == ("msg-1", "thread-1")


def test_register_mailbox_safe_symlink_unreadable_local_state_fails_without_tty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-private",
        address="HOUMAO-private@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    private_mailbox = (tmp_path / "private-mailboxes" / recipient.address).resolve()
    private_mailbox.mkdir(parents=True, exist_ok=True)
    (private_mailbox / "mailbox.sqlite").write_text("not a sqlite database", encoding="utf-8")
    monkeypatch.setattr("houmao.mailbox.managed._has_interactive_terminal", lambda *streams: False)

    with pytest.raises(
        ManagedMailboxOperationError,
        match="would need replacement, but no interactive TTY is available",
    ):
        register_mailbox(
            paths.root,
            RegisterMailboxRequest(
                mode="safe",
                address=recipient.address,
                owner_principal_id=recipient.principal_id,
                mailbox_kind="symlink",
                mailbox_path=private_mailbox,
            ),
        )

    with pytest.raises(MailboxBootstrapError, match="no active mailbox registration exists"):
        load_active_mailbox_registration(paths.root, address=recipient.address)
    assert not paths.mailbox_entry_path(recipient.address).exists()


def test_register_mailbox_safe_symlink_prompts_before_replacing_unreadable_local_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-private",
        address="HOUMAO-private@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    private_mailbox = (tmp_path / "private-mailboxes" / recipient.address).resolve()
    private_mailbox.mkdir(parents=True, exist_ok=True)
    (private_mailbox / "mailbox.sqlite").write_text("not a sqlite database", encoding="utf-8")
    monkeypatch.setattr("houmao.mailbox.managed._has_interactive_terminal", lambda *streams: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")

    result = register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="safe",
            address=recipient.address,
            owner_principal_id=recipient.principal_id,
            mailbox_kind="symlink",
            mailbox_path=private_mailbox,
        ),
    )

    assert result["ok"] is True
    assert list(private_mailbox.glob("mailbox.sqlite.local-unusable-*.bak"))
    with sqlite3.connect(private_mailbox / "mailbox.sqlite") as connection:
        connection.execute("SELECT COUNT(*) FROM message_state").fetchone()


def test_deliver_message_routes_by_address_and_state_updates_use_active_registration(
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-recipient",
        address="HOUMAO-recipient@agents.localhost",
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


def test_deliver_message_self_addressed_mail_starts_unread(tmp_path: Path) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-self",
        address="HOUMAO-self@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)

    staged_message = paths.staging_dir / "self-message.md"
    request = DeliveryRequest.from_payload(
        {
            "staged_message_path": str(staged_message),
            "message_id": "msg-20260311T041600Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "thread_id": "msg-20260311T041600Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "in_reply_to": None,
            "references": [],
            "created_at_utc": "2026-03-11T04:16:00Z",
            "sender": {
                "principal_id": sender.principal_id,
                "address": sender.address,
            },
            "to": [
                {
                    "principal_id": sender.principal_id,
                    "address": sender.address,
                }
            ],
            "cc": [],
            "reply_to": [],
            "subject": "Self-addressed reminder",
            "attachments": [],
            "headers": {},
        }
    )
    _write_canonical_staged_message(staged_message, request)

    result = deliver_message(paths.root, request)

    sender_sent_projection = (
        paths.mailbox_entry_path(sender.address) / "sent" / f"{request.message_id}.md"
    )
    sender_inbox_projection = (
        paths.mailbox_entry_path(sender.address) / "inbox" / f"{request.message_id}.md"
    )

    assert result["ok"] is True
    assert sender_sent_projection.is_symlink()
    assert sender_inbox_projection.is_symlink()
    assert _mailbox_state_for_address(
        paths.sqlite_path,
        address=sender.address,
        message_id=request.message_id,
    ) == (0, 0, 0, 0)


def test_update_mailbox_state_lazy_insert_keeps_self_addressed_mail_unread(
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-self",
        address="HOUMAO-self@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)

    staged_message = paths.staging_dir / "lazy-self-message.md"
    request = DeliveryRequest.from_payload(
        {
            "staged_message_path": str(staged_message),
            "message_id": "msg-20260311T041700Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "thread_id": "msg-20260311T041700Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "in_reply_to": None,
            "references": [],
            "created_at_utc": "2026-03-11T04:17:00Z",
            "sender": {
                "principal_id": sender.principal_id,
                "address": sender.address,
            },
            "to": [
                {
                    "principal_id": sender.principal_id,
                    "address": sender.address,
                }
            ],
            "cc": [],
            "reply_to": [],
            "subject": "Lazy self-addressed reminder",
            "attachments": [],
            "headers": {},
        }
    )
    _write_canonical_staged_message(staged_message, request)
    deliver_message(paths.root, request)

    registration = load_active_mailbox_registration(paths.root, address=sender.address)
    with sqlite3.connect(registration.local_sqlite_path) as connection:
        connection.execute("DELETE FROM message_state WHERE message_id = ?", (request.message_id,))
        connection.commit()

    state_result = update_mailbox_state(
        paths.root,
        StateUpdateRequest.from_payload(
            {
                "address": sender.address,
                "message_id": request.message_id,
                "starred": True,
            }
        ),
    )

    assert state_result["ok"] is True
    assert state_result["read"] is False
    assert _mailbox_state_for_address(
        paths.sqlite_path,
        address=sender.address,
        message_id=request.message_id,
    ) == (0, 1, 0, 0)


def test_repair_mailbox_index_rebuilds_self_addressed_mail_as_unread(tmp_path: Path) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-self",
        address="HOUMAO-self@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)

    staged_message = paths.staging_dir / "repair-self-message.md"
    request = DeliveryRequest.from_payload(
        {
            "staged_message_path": str(staged_message),
            "message_id": "msg-20260311T041800Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "thread_id": "msg-20260311T041800Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "in_reply_to": None,
            "references": [],
            "created_at_utc": "2026-03-11T04:18:00Z",
            "sender": {
                "principal_id": sender.principal_id,
                "address": sender.address,
            },
            "to": [
                {
                    "principal_id": sender.principal_id,
                    "address": sender.address,
                }
            ],
            "cc": [],
            "reply_to": [],
            "subject": "Repair self-addressed reminder",
            "attachments": [],
            "headers": {},
        }
    )
    _write_canonical_staged_message(staged_message, request)
    deliver_message(paths.root, request)
    paths.sqlite_path.unlink()

    result = repair_mailbox_index(paths.root, RepairRequest.from_payload({}))

    assert result["ok"] is True
    assert result["message_count"] == 1
    assert result["projection_count"] == 2
    assert result["defaulted_state_count"] == 1
    assert _mailbox_state_for_address(
        paths.sqlite_path,
        address=sender.address,
        message_id=request.message_id,
    ) == (0, 0, 0, 0)


def test_deregister_mailbox_purge_preserves_canonical_history_and_symlink_targets(
    tmp_path: Path,
) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-private",
        address="HOUMAO-private@agents.localhost",
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
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-recipient",
        address="HOUMAO-recipient@agents.localhost",
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
    assert result["registration_count"] == 3
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


def test_bootstrap_migrates_legacy_shared_mailbox_state_into_local_sqlite(tmp_path: Path) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-recipient",
        address="HOUMAO-recipient@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    bootstrap_filesystem_mailbox(paths.root, principal=recipient)

    staged_message = paths.staging_dir / "legacy-migration.md"
    request = DeliveryRequest.from_payload(
        {
            "staged_message_path": str(staged_message),
            "message_id": "msg-20260311T071500Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "thread_id": "msg-20260311T071500Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "in_reply_to": None,
            "references": [],
            "created_at_utc": "2026-03-11T07:15:00Z",
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
            "subject": "Legacy state migration",
            "attachments": [],
            "headers": {},
        }
    )
    _write_canonical_staged_message(staged_message, request)
    deliver_message(paths.root, request)

    sender_registration = load_active_mailbox_registration(paths.root, address=sender.address)
    recipient_registration = load_active_mailbox_registration(paths.root, address=recipient.address)
    sender_registration.local_sqlite_path.unlink()
    recipient_registration.local_sqlite_path.unlink()

    with sqlite3.connect(paths.sqlite_path) as connection:
        connection.execute("DELETE FROM mailbox_state")
        connection.execute(
            """
            INSERT INTO mailbox_state (
                registration_id,
                message_id,
                is_read,
                is_starred,
                is_archived,
                is_deleted
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                sender_registration.registration_id,
                request.message_id,
                1,
                0,
                0,
                0,
            ),
        )
        connection.execute(
            """
            INSERT INTO mailbox_state (
                registration_id,
                message_id,
                is_read,
                is_starred,
                is_archived,
                is_deleted
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                recipient_registration.registration_id,
                request.message_id,
                1,
                1,
                0,
                0,
            ),
        )
        connection.commit()

    bootstrap_filesystem_mailbox(paths.root)

    assert _mailbox_state_for_address(
        paths.sqlite_path,
        address=sender.address,
        message_id=request.message_id,
    ) == (1, 0, 0, 0)
    assert _mailbox_state_for_address(
        paths.sqlite_path,
        address=recipient.address,
        message_id=request.message_id,
    ) == (1, 1, 0, 0)


def test_repair_mailbox_index_rebuilds_unreadable_local_mailbox_state(tmp_path: Path) -> None:
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="HOUMAO-recipient",
        address="HOUMAO-recipient@agents.localhost",
    )
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=sender)
    bootstrap_filesystem_mailbox(paths.root, principal=recipient)

    staged_message = paths.staging_dir / "repair-local-state.md"
    request = DeliveryRequest.from_payload(
        {
            "staged_message_path": str(staged_message),
            "message_id": "msg-20260311T081500Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "thread_id": "msg-20260311T081500Z-a1b2c3d4e5f64798aabbccddeeff0011",
            "in_reply_to": None,
            "references": [],
            "created_at_utc": "2026-03-11T08:15:00Z",
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
            "subject": "Unreadable local mailbox state",
            "attachments": [],
            "headers": {},
        }
    )
    _write_canonical_staged_message(staged_message, request)
    deliver_message(paths.root, request)

    recipient_registration = load_active_mailbox_registration(paths.root, address=recipient.address)
    recipient_registration.local_sqlite_path.write_text("not a sqlite database", encoding="utf-8")

    result = repair_mailbox_index(paths.root, RepairRequest.from_payload({}))

    assert result["ok"] is True
    assert _mailbox_state_for_address(
        paths.sqlite_path,
        address=recipient.address,
        message_id=request.message_id,
    ) == (0, 0, 0, 0)
    assert list(
        recipient_registration.local_sqlite_path.parent.glob("mailbox.sqlite.local-unusable-*.bak")
    )
