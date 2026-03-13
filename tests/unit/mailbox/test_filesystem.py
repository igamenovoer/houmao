from __future__ import annotations

import os
from pathlib import Path
import sqlite3

import pytest

from houmao.mailbox.errors import MailboxBootstrapError
from houmao.mailbox.filesystem import bootstrap_filesystem_mailbox, read_protocol_version
from houmao.mailbox.protocol import MAILBOX_PROTOCOL_VERSION, MailboxPrincipal


def test_bootstrap_creates_address_routed_schema_assets_and_placeholder_directories(
    tmp_path: Path,
) -> None:
    principal = MailboxPrincipal(
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
    )

    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=principal)
    mailbox_entry = paths.mailbox_entry_path(principal.address)

    assert read_protocol_version(paths.protocol_version_file) == MAILBOX_PROTOCOL_VERSION
    assert paths.sqlite_path.is_file()
    assert (paths.rules_dir / "README.md").is_file()
    assert (paths.rules_protocols_dir / "filesystem-mailbox-v1.md").is_file()
    assert (paths.rules_skills_dir / "README.md").is_file()
    assert paths.rules_scripts_dir.is_dir()
    assert (paths.rules_scripts_dir / "requirements.txt").is_file()
    assert (paths.rules_scripts_dir / "deliver_message.py").is_file()
    assert (paths.rules_scripts_dir / "register_mailbox.py").is_file()
    assert (paths.rules_scripts_dir / "deregister_mailbox.py").is_file()
    assert (paths.rules_scripts_dir / "update_mailbox_state.py").is_file()
    assert (paths.rules_scripts_dir / "repair_index.py").is_file()
    assert mailbox_entry.is_dir()
    assert (mailbox_entry / "archive").is_dir()
    assert (mailbox_entry / "drafts").is_dir()
    assert os.access(paths.rules_scripts_dir / "deliver_message.py", os.X_OK)
    assert "pydantic>=2.12" in (paths.rules_scripts_dir / "requirements.txt").read_text(
        encoding="utf-8"
    )

    with sqlite3.connect(paths.sqlite_path) as connection:
        row = connection.execute(
            """
            SELECT
                address,
                owner_principal_id,
                status,
                mailbox_kind,
                mailbox_path,
                mailbox_entry_path
            FROM mailbox_registrations
            WHERE address = ? AND status = 'active'
            """,
            (principal.address,),
        ).fetchone()

    assert row == (
        "AGENTSYS-research@agents.localhost",
        "AGENTSYS-research",
        "active",
        "in_root",
        str(mailbox_entry),
        str(mailbox_entry),
    )


def test_bootstrap_rejects_unsupported_protocol_version(tmp_path: Path) -> None:
    mailbox_root = tmp_path / "mailbox"
    mailbox_root.mkdir(parents=True)
    (mailbox_root / "protocol-version.txt").write_text("99\n", encoding="utf-8")

    with pytest.raises(MailboxBootstrapError, match="unsupported mailbox protocol version"):
        bootstrap_filesystem_mailbox(mailbox_root)


def test_bootstrap_rejects_stale_principal_scoped_mailbox_root(tmp_path: Path) -> None:
    mailbox_root = tmp_path / "mailbox"
    (mailbox_root / "locks" / "principals").mkdir(parents=True)
    with sqlite3.connect(mailbox_root / "index.sqlite") as connection:
        connection.execute("CREATE TABLE principals (principal_id TEXT PRIMARY KEY)")
        connection.commit()

    with pytest.raises(MailboxBootstrapError, match="Delete this mailbox root and re-bootstrap"):
        bootstrap_filesystem_mailbox(mailbox_root)


def test_bootstrap_is_idempotent_for_matching_address_registration(tmp_path: Path) -> None:
    principal = MailboxPrincipal(
        principal_id="AGENTSYS-orchestrator",
        address="AGENTSYS-orchestrator@agents.localhost",
    )

    first_paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=principal)
    second_paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=principal)

    assert first_paths.sqlite_path == second_paths.sqlite_path
    assert read_protocol_version(second_paths.protocol_version_file) == MAILBOX_PROTOCOL_VERSION
    assert second_paths.mailbox_entry_path(principal.address).is_dir()
