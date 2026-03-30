from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from houmao.mailbox import (
    generate_message_id,
    load_active_mailbox_registration,
    resolve_filesystem_mailbox_paths,
)
from houmao.mailbox.managed import DeliveryRequest, ManagedPrincipal, deliver_message
from houmao.srv_ctrl.commands.main import cli


def _init_project_mailbox_repo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[CliRunner, Path, Path]:
    """Create one project repo with an initialized project mailbox root."""

    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)
    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    assert runner.invoke(cli, ["project", "mailbox", "init"]).exit_code == 0
    return runner, repo_root, repo_root / ".houmao" / "mailbox"


def test_mailbox_accounts_commands_and_project_wrapper_have_root_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    mailbox_root = repo_root / ".houmao" / "mailbox"
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    assert runner.invoke(cli, ["project", "mailbox", "init"]).exit_code == 0
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "mailbox",
                "register",
                "--address",
                "AGENTSYS-alice@agents.localhost",
                "--principal-id",
                "AGENTSYS-alice",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "mailbox",
                "register",
                "--address",
                "AGENTSYS-bob@agents.localhost",
                "--principal-id",
                "AGENTSYS-bob",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "mailbox",
                "unregister",
                "--address",
                "AGENTSYS-bob@agents.localhost",
            ],
        ).exit_code
        == 0
    )

    generic_list_result = runner.invoke(
        cli,
        [
            "mailbox",
            "accounts",
            "list",
            "--mailbox-root",
            str(mailbox_root),
        ],
    )
    project_list_result = runner.invoke(cli, ["project", "mailbox", "accounts", "list"])

    assert generic_list_result.exit_code == 0, generic_list_result.output
    assert project_list_result.exit_code == 0, project_list_result.output
    generic_accounts = json.loads(generic_list_result.output)["accounts"]
    project_accounts = json.loads(project_list_result.output)["accounts"]
    assert [(item["address"], item["status"]) for item in generic_accounts] == [
        (item["address"], item["status"]) for item in project_accounts
    ]

    generic_get_result = runner.invoke(
        cli,
        [
            "mailbox",
            "accounts",
            "get",
            "--mailbox-root",
            str(mailbox_root),
            "--address",
            "AGENTSYS-alice@agents.localhost",
        ],
    )
    project_get_result = runner.invoke(
        cli,
        [
            "project",
            "mailbox",
            "accounts",
            "get",
            "--address",
            "AGENTSYS-alice@agents.localhost",
        ],
    )

    assert generic_get_result.exit_code == 0, generic_get_result.output
    assert project_get_result.exit_code == 0, project_get_result.output
    assert (
        json.loads(generic_get_result.output)["account"]["address"]
        == "AGENTSYS-alice@agents.localhost"
    )
    assert (
        json.loads(project_get_result.output)["account"]["address"]
        == "AGENTSYS-alice@agents.localhost"
    )


def test_mailbox_messages_commands_and_project_wrapper_share_visibility(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    mailbox_root = repo_root / ".houmao" / "mailbox"
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    assert runner.invoke(cli, ["project", "mailbox", "init"]).exit_code == 0
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "mailbox",
                "register",
                "--address",
                "AGENTSYS-alice@agents.localhost",
                "--principal-id",
                "AGENTSYS-alice",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "mailbox",
                "register",
                "--address",
                "AGENTSYS-bob@agents.localhost",
                "--principal-id",
                "AGENTSYS-bob",
            ],
        ).exit_code
        == 0
    )

    mailbox_paths = resolve_filesystem_mailbox_paths(mailbox_root)
    staged_message_path = (mailbox_paths.staging_dir / "draft-message.md").resolve()
    staged_message_path.parent.mkdir(parents=True, exist_ok=True)
    staged_message_path.write_text("Hello from Bob.\n", encoding="utf-8")
    message_id = generate_message_id()
    deliver_message(
        mailbox_root,
        DeliveryRequest(
            staged_message_path=staged_message_path,
            message_id=message_id,
            thread_id=message_id,
            created_at_utc="2026-03-28T12:00:00Z",
            sender=ManagedPrincipal(
                principal_id="AGENTSYS-bob",
                address="AGENTSYS-bob@agents.localhost",
            ),
            to=(
                ManagedPrincipal(
                    principal_id="AGENTSYS-alice",
                    address="AGENTSYS-alice@agents.localhost",
                ),
            ),
            subject="Hello Alice",
        ),
    )

    generic_list_result = runner.invoke(
        cli,
        [
            "mailbox",
            "messages",
            "list",
            "--mailbox-root",
            str(mailbox_root),
            "--address",
            "AGENTSYS-alice@agents.localhost",
        ],
    )
    project_list_result = runner.invoke(
        cli,
        [
            "project",
            "mailbox",
            "messages",
            "list",
            "--address",
            "AGENTSYS-alice@agents.localhost",
        ],
    )

    assert generic_list_result.exit_code == 0, generic_list_result.output
    assert project_list_result.exit_code == 0, project_list_result.output
    generic_messages = json.loads(generic_list_result.output)["messages"]
    project_messages = json.loads(project_list_result.output)["messages"]
    assert [item["message_id"] for item in generic_messages] == [message_id]
    assert [item["message_id"] for item in project_messages] == [message_id]

    generic_get_result = runner.invoke(
        cli,
        [
            "mailbox",
            "messages",
            "get",
            "--mailbox-root",
            str(mailbox_root),
            "--address",
            "AGENTSYS-alice@agents.localhost",
            "--message-id",
            message_id,
        ],
    )
    project_get_result = runner.invoke(
        cli,
        [
            "project",
            "mailbox",
            "messages",
            "get",
            "--address",
            "AGENTSYS-alice@agents.localhost",
            "--message-id",
            message_id,
        ],
    )

    assert generic_get_result.exit_code == 0, generic_get_result.output
    assert project_get_result.exit_code == 0, project_get_result.output
    generic_message = json.loads(generic_get_result.output)["message"]
    project_message = json.loads(project_get_result.output)["message"]
    assert generic_message["message_id"] == message_id
    assert project_message["message_id"] == message_id
    assert generic_message["subject"] == "Hello Alice"


def test_mailbox_register_prompts_before_overwriting_active_registration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    mailbox_root = (tmp_path / "mailbox").resolve()
    address = "AGENTSYS-alice@agents.localhost"

    assert (
        runner.invoke(cli, ["mailbox", "init", "--mailbox-root", str(mailbox_root)]).exit_code == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "mailbox",
                "register",
                "--mailbox-root",
                str(mailbox_root),
                "--address",
                address,
                "--principal-id",
                "AGENTSYS-alice",
            ],
        ).exit_code
        == 0
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.common.has_interactive_terminal",
        lambda *streams: True,
    )

    result = runner.invoke(
        cli,
        [
            "mailbox",
            "register",
            "--mailbox-root",
            str(mailbox_root),
            "--address",
            address,
            "--principal-id",
            "AGENTSYS-bob",
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    registration = load_active_mailbox_registration(mailbox_root, address=address)
    assert registration.owner_principal_id == "AGENTSYS-bob"


def test_mailbox_register_decline_keeps_existing_registration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    mailbox_root = (tmp_path / "mailbox").resolve()
    address = "AGENTSYS-alice@agents.localhost"

    assert (
        runner.invoke(cli, ["mailbox", "init", "--mailbox-root", str(mailbox_root)]).exit_code == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "mailbox",
                "register",
                "--mailbox-root",
                str(mailbox_root),
                "--address",
                address,
                "--principal-id",
                "AGENTSYS-alice",
            ],
        ).exit_code
        == 0
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.common.has_interactive_terminal",
        lambda *streams: True,
    )

    result = runner.invoke(
        cli,
        [
            "mailbox",
            "register",
            "--mailbox-root",
            str(mailbox_root),
            "--address",
            address,
            "--principal-id",
            "AGENTSYS-bob",
        ],
        input="n\n",
    )

    assert result.exit_code != 0
    assert "Mailbox registration cancelled" in result.output
    registration = load_active_mailbox_registration(mailbox_root, address=address)
    assert registration.owner_principal_id == "AGENTSYS-alice"


def test_mailbox_register_noninteractive_conflict_requires_yes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    mailbox_root = (tmp_path / "mailbox").resolve()
    address = "AGENTSYS-alice@agents.localhost"

    assert (
        runner.invoke(cli, ["mailbox", "init", "--mailbox-root", str(mailbox_root)]).exit_code == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "mailbox",
                "register",
                "--mailbox-root",
                str(mailbox_root),
                "--address",
                address,
                "--principal-id",
                "AGENTSYS-alice",
            ],
        ).exit_code
        == 0
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.common.has_interactive_terminal",
        lambda *streams: False,
    )

    result = runner.invoke(
        cli,
        [
            "mailbox",
            "register",
            "--mailbox-root",
            str(mailbox_root),
            "--address",
            address,
            "--principal-id",
            "AGENTSYS-bob",
        ],
    )

    assert result.exit_code != 0
    assert "Rerun with `--yes`" in result.output
    registration = load_active_mailbox_registration(mailbox_root, address=address)
    assert registration.owner_principal_id == "AGENTSYS-alice"


def test_mailbox_register_yes_overwrites_without_tty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    mailbox_root = (tmp_path / "mailbox").resolve()
    address = "AGENTSYS-alice@agents.localhost"

    assert (
        runner.invoke(cli, ["mailbox", "init", "--mailbox-root", str(mailbox_root)]).exit_code == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "mailbox",
                "register",
                "--mailbox-root",
                str(mailbox_root),
                "--address",
                address,
                "--principal-id",
                "AGENTSYS-alice",
            ],
        ).exit_code
        == 0
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.common.has_interactive_terminal",
        lambda *streams: False,
    )

    result = runner.invoke(
        cli,
        [
            "mailbox",
            "register",
            "--mailbox-root",
            str(mailbox_root),
            "--address",
            address,
            "--principal-id",
            "AGENTSYS-bob",
            "--yes",
        ],
    )

    assert result.exit_code == 0, result.output
    registration = load_active_mailbox_registration(mailbox_root, address=address)
    assert registration.owner_principal_id == "AGENTSYS-bob"


def test_project_mailbox_register_prompts_before_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, _repo_root, mailbox_root = _init_project_mailbox_repo(monkeypatch, tmp_path)
    address = "AGENTSYS-alice@agents.localhost"

    assert (
        runner.invoke(
            cli,
            [
                "project",
                "mailbox",
                "register",
                "--address",
                address,
                "--principal-id",
                "AGENTSYS-alice",
            ],
        ).exit_code
        == 0
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.common.has_interactive_terminal",
        lambda *streams: True,
    )

    result = runner.invoke(
        cli,
        [
            "project",
            "mailbox",
            "register",
            "--address",
            address,
            "--principal-id",
            "AGENTSYS-bob",
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    registration = load_active_mailbox_registration(mailbox_root, address=address)
    assert registration.owner_principal_id == "AGENTSYS-bob"


def test_project_mailbox_register_yes_overwrites_without_tty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, _repo_root, mailbox_root = _init_project_mailbox_repo(monkeypatch, tmp_path)
    address = "AGENTSYS-alice@agents.localhost"

    assert (
        runner.invoke(
            cli,
            [
                "project",
                "mailbox",
                "register",
                "--address",
                address,
                "--principal-id",
                "AGENTSYS-alice",
            ],
        ).exit_code
        == 0
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.common.has_interactive_terminal",
        lambda *streams: False,
    )

    result = runner.invoke(
        cli,
        [
            "project",
            "mailbox",
            "register",
            "--address",
            address,
            "--principal-id",
            "AGENTSYS-bob",
            "--yes",
        ],
    )

    assert result.exit_code == 0, result.output
    registration = load_active_mailbox_registration(mailbox_root, address=address)
    assert registration.owner_principal_id == "AGENTSYS-bob"
