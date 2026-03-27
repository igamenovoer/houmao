from __future__ import annotations

from pathlib import Path

import pytest

from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
    StalwartMailboxResolvedConfig,
)
from houmao.agents.mailbox_runtime_support import (
    mailbox_env_bindings,
    publish_tmux_live_mailbox_projection,
    resolve_live_mailbox_binding,
)
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox


def test_resolve_live_mailbox_binding_uses_targeted_filesystem_projection(
    tmp_path: Path,
) -> None:
    mailbox_root = tmp_path / "mailbox"
    durable_mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
        filesystem_root=mailbox_root.resolve(),
        bindings_version="2026-03-26T18:10:00.000001Z",
    )
    bootstrap_filesystem_mailbox(
        mailbox_root,
        principal=MailboxPrincipal(
            principal_id=durable_mailbox.principal_id,
            address=durable_mailbox.address,
        ),
    )
    env_bindings = mailbox_env_bindings(durable_mailbox)

    resolution = resolve_live_mailbox_binding(
        durable_mailbox=durable_mailbox,
        env_reader=env_bindings.get,
    )

    assert resolution.source == "tmux_session_env"
    assert resolution.mailbox == durable_mailbox
    assert resolution.env_bindings["AGENTSYS_MAILBOX_FS_ROOT"] == str(mailbox_root.resolve())


def test_resolve_live_mailbox_binding_rejects_incomplete_projection(tmp_path: Path) -> None:
    mailbox_root = tmp_path / "mailbox"
    durable_mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
        filesystem_root=mailbox_root.resolve(),
        bindings_version="2026-03-26T18:10:00.000001Z",
    )
    bootstrap_filesystem_mailbox(
        mailbox_root,
        principal=MailboxPrincipal(
            principal_id=durable_mailbox.principal_id,
            address=durable_mailbox.address,
        ),
    )
    env_bindings = mailbox_env_bindings(durable_mailbox)
    env_bindings.pop("AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH")

    with pytest.raises(ValueError, match="missing required env vars"):
        resolve_live_mailbox_binding(
            durable_mailbox=durable_mailbox,
            env_reader=env_bindings.get,
        )


def test_publish_tmux_live_mailbox_projection_refreshes_current_bindings(tmp_path: Path) -> None:
    old_root = tmp_path / "mail-old"
    new_root = tmp_path / "mail-new"
    previous_mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
        filesystem_root=old_root.resolve(),
        bindings_version="2026-03-26T18:10:00.000001Z",
    )
    mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
        filesystem_root=new_root.resolve(),
        bindings_version="2026-03-26T18:20:00.000001Z",
    )
    bootstrap_filesystem_mailbox(
        new_root,
        principal=MailboxPrincipal(
            principal_id=mailbox.principal_id,
            address=mailbox.address,
        ),
    )
    set_calls: list[tuple[str, dict[str, str]]] = []
    unset_calls: list[tuple[str, list[str]]] = []

    publish_tmux_live_mailbox_projection(
        session_name="AGENTSYS-research",
        previous_mailbox=previous_mailbox,
        mailbox=mailbox,
        set_env=lambda session_name, env_vars: set_calls.append((session_name, dict(env_vars))),
        unset_env=lambda session_name, variable_names: unset_calls.append(
            (session_name, list(variable_names))
        ),
    )

    assert set_calls
    assert set_calls[-1][0] == "AGENTSYS-research"
    assert set_calls[-1][1]["AGENTSYS_MAILBOX_FS_ROOT"] == str(new_root.resolve())
    assert set_calls[-1][1]["AGENTSYS_MAILBOX_BINDINGS_VERSION"] == mailbox.bindings_version
    assert unset_calls == []


def test_publish_tmux_live_mailbox_projection_clears_stale_transport_vars(tmp_path: Path) -> None:
    credential_file = tmp_path / "mailbox-secret.json"
    credential_file.write_text('{"password":"secret"}\n', encoding="utf-8")
    previous_mailbox = StalwartMailboxResolvedConfig(
        transport="stalwart",
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
        jmap_url="http://stalwart.local/jmap",
        management_url="http://stalwart.local/api",
        login_identity="AGENTSYS-research@agents.localhost",
        credential_ref="cred-1",
        bindings_version="2026-03-26T18:10:00.000001Z",
        credential_file=credential_file,
    )
    set_calls: list[tuple[str, dict[str, str]]] = []
    unset_calls: list[tuple[str, list[str]]] = []

    publish_tmux_live_mailbox_projection(
        session_name="AGENTSYS-research",
        previous_mailbox=previous_mailbox,
        mailbox=None,
        set_env=lambda session_name, env_vars: set_calls.append((session_name, dict(env_vars))),
        unset_env=lambda session_name, variable_names: unset_calls.append(
            (session_name, list(variable_names))
        ),
    )

    assert set_calls == []
    assert unset_calls == [
        (
            "AGENTSYS-research",
            [
                "AGENTSYS_MAILBOX_ADDRESS",
                "AGENTSYS_MAILBOX_BINDINGS_VERSION",
                "AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_FILE",
                "AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_REF",
                "AGENTSYS_MAILBOX_EMAIL_JMAP_URL",
                "AGENTSYS_MAILBOX_EMAIL_LOGIN_IDENTITY",
                "AGENTSYS_MAILBOX_EMAIL_MANAGEMENT_URL",
                "AGENTSYS_MAILBOX_PRINCIPAL_ID",
                "AGENTSYS_MAILBOX_TRANSPORT",
            ],
        )
    ]
