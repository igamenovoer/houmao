from __future__ import annotations

import os
from pathlib import Path
import sqlite3

import pytest

from gig_agents.mailbox.errors import MailboxBootstrapError
from gig_agents.mailbox.filesystem import bootstrap_filesystem_mailbox, read_protocol_version
from gig_agents.mailbox.protocol import MAILBOX_PROTOCOL_VERSION, MailboxPrincipal


def test_bootstrap_creates_protocol_version_schema_and_placeholder_directories(
    tmp_path: Path,
) -> None:
    principal = MailboxPrincipal(
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
    )

    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=principal)

    assert read_protocol_version(paths.protocol_version_file) == MAILBOX_PROTOCOL_VERSION
    assert paths.sqlite_path.is_file()
    assert (paths.rules_dir / "README.md").is_file()
    assert (paths.rules_protocols_dir / "filesystem-mailbox-v1.md").is_file()
    assert (paths.rules_skills_dir / "README.md").is_file()
    assert paths.rules_scripts_dir.is_dir()
    assert (paths.rules_scripts_dir / "requirements.txt").is_file()
    assert (paths.rules_scripts_dir / "deliver_message.py").is_file()
    assert (paths.rules_scripts_dir / "insert_standard_headers.py").is_file()
    assert (paths.rules_scripts_dir / "update_mailbox_state.py").is_file()
    assert (paths.rules_scripts_dir / "repair_index.py").is_file()
    assert paths.principal_mailbox_dir(principal.principal_id).is_dir()
    assert (paths.principal_mailbox_dir(principal.principal_id) / "archive").is_dir()
    assert (paths.principal_mailbox_dir(principal.principal_id) / "drafts").is_dir()
    assert os.access(paths.rules_scripts_dir / "deliver_message.py", os.X_OK)
    assert "pydantic>=2.12,<3" in (paths.rules_scripts_dir / "requirements.txt").read_text(
        encoding="utf-8"
    )

    with sqlite3.connect(paths.sqlite_path) as connection:
        row = connection.execute(
            "SELECT address, mailbox_kind, mailbox_path FROM principals WHERE principal_id = ?",
            (principal.principal_id,),
        ).fetchone()

    assert row == (
        "AGENTSYS-research@agents.localhost",
        "in_root",
        str(paths.principal_mailbox_dir(principal.principal_id)),
    )


def test_bootstrap_rejects_unsupported_protocol_version(tmp_path: Path) -> None:
    mailbox_root = tmp_path / "mailbox"
    mailbox_root.mkdir(parents=True)
    (mailbox_root / "protocol-version.txt").write_text("99\n", encoding="utf-8")

    with pytest.raises(MailboxBootstrapError, match="unsupported mailbox protocol version"):
        bootstrap_filesystem_mailbox(mailbox_root)


def test_bootstrap_is_idempotent_for_matching_principal_registration(tmp_path: Path) -> None:
    principal = MailboxPrincipal(
        principal_id="AGENTSYS-orchestrator",
        address="AGENTSYS-orchestrator@agents.localhost",
    )

    first_paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=principal)
    second_paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox", principal=principal)

    assert first_paths.sqlite_path == second_paths.sqlite_path
    assert read_protocol_version(second_paths.protocol_version_file) == MAILBOX_PROTOCOL_VERSION
