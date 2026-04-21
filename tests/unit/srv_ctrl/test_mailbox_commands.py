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
from houmao.owned_paths import HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR
from houmao.project.overlay import PROJECT_OVERLAY_DIR_ENV_VAR
from houmao.srv_ctrl.commands.main import cli, main


_AMBIGUOUS_MESSAGE_STATE_FIELDS = {"read", "starred", "archived", "deleted"}


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


def _deliver_cli_test_message(
    *,
    mailbox_root: Path,
    sender_address: str,
    sender_principal_id: str,
    recipient_address: str,
    recipient_principal_id: str,
) -> str:
    """Deliver one test message through the managed mailbox layer."""

    mailbox_paths = resolve_filesystem_mailbox_paths(mailbox_root)
    staged_message_path = (mailbox_paths.staging_dir / f"{generate_message_id()}.md").resolve()
    staged_message_path.parent.mkdir(parents=True, exist_ok=True)
    staged_message_path.write_text("Hello from a CLI test.\n", encoding="utf-8")
    message_id = generate_message_id()
    deliver_message(
        mailbox_root,
        DeliveryRequest(
            staged_message_path=staged_message_path,
            message_id=message_id,
            thread_id=message_id,
            created_at_utc="2026-03-28T12:00:00Z",
            sender=ManagedPrincipal(
                principal_id=sender_principal_id,
                address=sender_address,
            ),
            to=(
                ManagedPrincipal(
                    principal_id=recipient_principal_id,
                    address=recipient_address,
                ),
            ),
            subject="Hello recipient",
        ),
    )
    return message_id


def test_generic_mailbox_init_bootstraps_project_overlay_root_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(cli, ["--print-json", "mailbox", "init"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mailbox_root"] == str((repo_root / ".houmao" / "mailbox").resolve())
    assert (
        payload["mailbox_root_detail"]
        == "Selected the active project mailbox root from the current project overlay."
    )
    assert (repo_root / ".houmao" / "houmao-config.toml").exists()


def test_mailbox_help_describes_project_aware_mailbox_default() -> None:
    result = CliRunner().invoke(cli, ["mailbox", "status", "--help"])

    assert result.exit_code == 0
    assert "active project mailbox root" in result.output
    assert "shared mailbox-root override" in result.output


def test_main_renders_generic_mailbox_accounts_list_missing_index_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mailbox_root = (tmp_path / "shared-mail").resolve()
    mailbox_root.mkdir(parents=True, exist_ok=True)

    exit_code = main(["mailbox", "accounts", "list", "--mailbox-root", str(mailbox_root)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert f"Mailbox index is missing under `{mailbox_root}`." in captured.err
    assert "Run `houmao-mgr mailbox init` first." in captured.err
    assert "Traceback" not in captured.err


def test_main_renders_generic_mailbox_cleanup_unbootstrapped_root_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mailbox_root = (tmp_path / "shared-mail").resolve()
    mailbox_root.mkdir(parents=True, exist_ok=True)

    exit_code = main(["mailbox", "cleanup", "--mailbox-root", str(mailbox_root)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert f"missing protocol version file: {mailbox_root / 'protocol-version.txt'}" in captured.err
    assert "Run `houmao-mgr mailbox init` first." in captured.err
    assert "Traceback" not in captured.err


def test_main_renders_project_mailbox_accounts_list_missing_index_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

    exit_code = main(["project", "mailbox", "accounts", "list"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Selected overlay mailbox root" in captured.err
    assert "Run `houmao-mgr project mailbox init` first." in captured.err
    assert "Traceback" not in captured.err


def test_main_renders_project_mailbox_cleanup_unbootstrapped_root_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

    exit_code = main(["project", "mailbox", "cleanup"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Selected overlay mailbox root" in captured.err
    assert "Run `houmao-mgr project mailbox init` first." in captured.err
    assert "Traceback" not in captured.err


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
                "HOUMAO-alice@agents.localhost",
                "--principal-id",
                "HOUMAO-alice",
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
                "HOUMAO-bob@agents.localhost",
                "--principal-id",
                "HOUMAO-bob",
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
                "HOUMAO-bob@agents.localhost",
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
    project_payload = json.loads(project_list_result.output)
    project_accounts = project_payload["accounts"]
    assert [(item["address"], item["status"]) for item in generic_accounts] == [
        (item["address"], item["status"]) for item in project_accounts
    ]
    assert project_payload["selected_overlay_root"] == str((repo_root / ".houmao").resolve())
    assert (
        project_payload["selected_overlay_detail"]
        == "Selected overlay root from nearest-ancestor project discovery."
    )
    assert (
        project_payload["mailbox_root_detail"]
        == "Selected `mailbox/` under the selected project overlay."
    )
    assert project_payload["project_overlay_bootstrapped"] is False

    generic_get_result = runner.invoke(
        cli,
        [
            "mailbox",
            "accounts",
            "get",
            "--mailbox-root",
            str(mailbox_root),
            "--address",
            "HOUMAO-alice@agents.localhost",
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
            "HOUMAO-alice@agents.localhost",
        ],
    )

    assert generic_get_result.exit_code == 0, generic_get_result.output
    assert project_get_result.exit_code == 0, project_get_result.output
    assert (
        json.loads(generic_get_result.output)["account"]["address"]
        == "HOUMAO-alice@agents.localhost"
    )
    assert (
        json.loads(project_get_result.output)["account"]["address"]
        == "HOUMAO-alice@agents.localhost"
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
                "HOUMAO-alice@agents.localhost",
                "--principal-id",
                "HOUMAO-alice",
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
                "HOUMAO-bob@agents.localhost",
                "--principal-id",
                "HOUMAO-bob",
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
                principal_id="HOUMAO-bob",
                address="HOUMAO-bob@agents.localhost",
            ),
            to=(
                ManagedPrincipal(
                    principal_id="HOUMAO-alice",
                    address="HOUMAO-alice@agents.localhost",
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
            "HOUMAO-alice@agents.localhost",
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
            "HOUMAO-alice@agents.localhost",
        ],
    )

    assert generic_list_result.exit_code == 0, generic_list_result.output
    assert project_list_result.exit_code == 0, project_list_result.output
    generic_messages = json.loads(generic_list_result.output)["messages"]
    project_messages = json.loads(project_list_result.output)["messages"]
    assert [item["message_id"] for item in generic_messages] == [message_id]
    assert [item["message_id"] for item in project_messages] == [message_id]
    assert _AMBIGUOUS_MESSAGE_STATE_FIELDS.isdisjoint(generic_messages[0])
    assert _AMBIGUOUS_MESSAGE_STATE_FIELDS.isdisjoint(project_messages[0])

    generic_get_result = runner.invoke(
        cli,
        [
            "mailbox",
            "messages",
            "get",
            "--mailbox-root",
            str(mailbox_root),
            "--address",
            "HOUMAO-alice@agents.localhost",
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
            "HOUMAO-alice@agents.localhost",
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
    assert _AMBIGUOUS_MESSAGE_STATE_FIELDS.isdisjoint(generic_message)
    assert _AMBIGUOUS_MESSAGE_STATE_FIELDS.isdisjoint(project_message)


def test_mailbox_clear_messages_preserves_accounts_and_requires_yes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    mailbox_root = (tmp_path / "mailbox").resolve()
    sender_address = "HOUMAO-bob@agents.localhost"
    recipient_address = "HOUMAO-alice@agents.localhost"

    assert (
        runner.invoke(cli, ["mailbox", "init", "--mailbox-root", str(mailbox_root)]).exit_code == 0
    )
    for address, principal_id in (
        (sender_address, "HOUMAO-bob"),
        (recipient_address, "HOUMAO-alice"),
    ):
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
                    principal_id,
                ],
            ).exit_code
            == 0
        )
    message_id = _deliver_cli_test_message(
        mailbox_root=mailbox_root,
        sender_address=sender_address,
        sender_principal_id="HOUMAO-bob",
        recipient_address=recipient_address,
        recipient_principal_id="HOUMAO-alice",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.common.has_interactive_terminal",
        lambda *streams: False,
    )

    help_result = runner.invoke(cli, ["mailbox", "--help"])
    apply_without_yes_result = runner.invoke(
        cli,
        [
            "mailbox",
            "clear-messages",
            "--mailbox-root",
            str(mailbox_root),
        ],
    )
    dry_run_result = runner.invoke(
        cli,
        [
            "--print-json",
            "mailbox",
            "clear-messages",
            "--mailbox-root",
            str(mailbox_root),
            "--dry-run",
        ],
    )
    apply_result = runner.invoke(
        cli,
        [
            "--print-json",
            "mailbox",
            "clear-messages",
            "--mailbox-root",
            str(mailbox_root),
            "--yes",
        ],
    )

    assert help_result.exit_code == 0, help_result.output
    assert "clear-messages" in help_result.output
    assert apply_without_yes_result.exit_code != 0
    assert "Rerun with `--yes`" in apply_without_yes_result.output
    assert dry_run_result.exit_code == 0, dry_run_result.output
    dry_run_payload = json.loads(dry_run_result.output)
    assert dry_run_payload["dry_run"] is True
    assert any(
        action["artifact_kind"] == "canonical_message"
        for action in dry_run_payload["planned_actions"]
    )
    assert apply_result.exit_code == 0, apply_result.output
    apply_payload = json.loads(apply_result.output)
    assert apply_payload["scope"]["kind"] == "mailbox_message_clear"
    assert any(
        action["artifact_kind"] == "canonical_message"
        for action in apply_payload["applied_actions"]
    )
    assert load_active_mailbox_registration(mailbox_root, address=recipient_address).address == (
        recipient_address
    )

    messages_result = runner.invoke(
        cli,
        [
            "mailbox",
            "messages",
            "list",
            "--mailbox-root",
            str(mailbox_root),
            "--address",
            recipient_address,
        ],
    )

    assert messages_result.exit_code == 0, messages_result.output
    assert json.loads(messages_result.output)["messages"] == []
    assert message_id not in messages_result.output


def test_mailbox_export_command_validates_scope_and_writes_archive(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    mailbox_root = (tmp_path / "mailbox").resolve()
    sender_address = "HOUMAO-bob@agents.localhost"
    recipient_address = "HOUMAO-alice@agents.localhost"

    assert (
        runner.invoke(cli, ["mailbox", "init", "--mailbox-root", str(mailbox_root)]).exit_code == 0
    )
    for address, principal_id in (
        (sender_address, "HOUMAO-bob"),
        (recipient_address, "HOUMAO-alice"),
    ):
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
                    principal_id,
                ],
            ).exit_code
            == 0
        )
    message_id = _deliver_cli_test_message(
        mailbox_root=mailbox_root,
        sender_address=sender_address,
        sender_principal_id="HOUMAO-bob",
        recipient_address=recipient_address,
        recipient_principal_id="HOUMAO-alice",
    )

    help_result = runner.invoke(cli, ["mailbox", "--help"])
    missing_scope_result = runner.invoke(
        cli,
        [
            "mailbox",
            "export",
            "--mailbox-root",
            str(mailbox_root),
            "--output-dir",
            str(tmp_path / "missing-scope-archive"),
        ],
    )
    conflicting_scope_result = runner.invoke(
        cli,
        [
            "mailbox",
            "export",
            "--mailbox-root",
            str(mailbox_root),
            "--output-dir",
            str(tmp_path / "conflict-archive"),
            "--all-accounts",
            "--address",
            recipient_address,
        ],
    )
    existing_output = tmp_path / "existing-archive"
    existing_output.mkdir()
    existing_output_result = runner.invoke(
        cli,
        [
            "mailbox",
            "export",
            "--mailbox-root",
            str(mailbox_root),
            "--output-dir",
            str(existing_output),
            "--all-accounts",
        ],
    )
    selected_output = tmp_path / "selected-archive"
    selected_result = runner.invoke(
        cli,
        [
            "--print-json",
            "mailbox",
            "export",
            "--mailbox-root",
            str(mailbox_root),
            "--output-dir",
            str(selected_output),
            "--address",
            recipient_address,
        ],
    )
    preserve_output = tmp_path / "preserve-archive"
    preserve_result = runner.invoke(
        cli,
        [
            "--print-json",
            "mailbox",
            "export",
            "--mailbox-root",
            str(mailbox_root),
            "--output-dir",
            str(preserve_output),
            "--all-accounts",
            "--symlink-mode",
            "preserve",
        ],
    )

    assert help_result.exit_code == 0, help_result.output
    assert "export" in help_result.output
    assert missing_scope_result.exit_code != 0
    assert "Choose `--all-accounts`" in missing_scope_result.output
    assert conflicting_scope_result.exit_code != 0
    assert "not both" in conflicting_scope_result.output
    assert existing_output_result.exit_code != 0
    assert "already exists" in existing_output_result.output
    assert selected_result.exit_code == 0, selected_result.output
    selected_payload = json.loads(selected_result.output)
    assert selected_payload["mailbox_root"] == str(mailbox_root)
    assert selected_payload["output_dir"] == str(selected_output.resolve())
    assert selected_payload["symlink_mode"] == "materialize"
    assert selected_payload["selected_addresses"] == [recipient_address]
    assert selected_payload["all_accounts"] is False
    assert selected_payload["account_count"] == 1
    assert selected_payload["message_count"] == 1
    assert Path(selected_payload["manifest_path"]).is_file()
    assert any(
        action["artifact_kind"] == "mailbox_projection"
        for action in selected_payload["materialized_artifacts"]
    )
    assert not any(path.is_symlink() for path in selected_output.rglob("*"))
    assert message_id in (selected_output / "manifest.json").read_text(encoding="utf-8")
    assert preserve_result.exit_code == 0, preserve_result.output
    preserve_payload = json.loads(preserve_result.output)
    assert preserve_payload["symlink_mode"] == "preserve"
    assert preserve_payload["all_accounts"] is True
    assert preserve_payload["preserved_symlinks"]


def test_mailbox_register_prompts_before_overwriting_active_registration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    mailbox_root = (tmp_path / "mailbox").resolve()
    address = "HOUMAO-alice@agents.localhost"

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
                "HOUMAO-alice",
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
            "HOUMAO-bob",
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    registration = load_active_mailbox_registration(mailbox_root, address=address)
    assert registration.owner_principal_id == "HOUMAO-bob"


def test_mailbox_register_decline_keeps_existing_registration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    mailbox_root = (tmp_path / "mailbox").resolve()
    address = "HOUMAO-alice@agents.localhost"

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
                "HOUMAO-alice",
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
            "HOUMAO-bob",
        ],
        input="n\n",
    )

    assert result.exit_code != 0
    assert "Mailbox registration cancelled" in result.output
    registration = load_active_mailbox_registration(mailbox_root, address=address)
    assert registration.owner_principal_id == "HOUMAO-alice"


def test_mailbox_register_noninteractive_conflict_requires_yes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    mailbox_root = (tmp_path / "mailbox").resolve()
    address = "HOUMAO-alice@agents.localhost"

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
                "HOUMAO-alice",
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
            "HOUMAO-bob",
        ],
    )

    assert result.exit_code != 0
    assert "Rerun with `--yes`" in result.output
    registration = load_active_mailbox_registration(mailbox_root, address=address)
    assert registration.owner_principal_id == "HOUMAO-alice"


def test_mailbox_register_yes_overwrites_without_tty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    mailbox_root = (tmp_path / "mailbox").resolve()
    address = "HOUMAO-alice@agents.localhost"

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
                "HOUMAO-alice",
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
            "HOUMAO-bob",
            "--yes",
        ],
    )

    assert result.exit_code == 0, result.output
    registration = load_active_mailbox_registration(mailbox_root, address=address)
    assert registration.owner_principal_id == "HOUMAO-bob"


def test_project_mailbox_register_prompts_before_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, _repo_root, mailbox_root = _init_project_mailbox_repo(monkeypatch, tmp_path)
    address = "HOUMAO-alice@agents.localhost"

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
                "HOUMAO-alice",
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
            "HOUMAO-bob",
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    registration = load_active_mailbox_registration(mailbox_root, address=address)
    assert registration.owner_principal_id == "HOUMAO-bob"


def test_project_mailbox_uses_env_selected_overlay_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    overlay_root = (tmp_path / "ci-overlay").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)
    env = {PROJECT_OVERLAY_DIR_ENV_VAR: str(overlay_root)}

    assert runner.invoke(cli, ["project", "init"], env=env).exit_code == 0
    assert runner.invoke(cli, ["project", "mailbox", "init"], env=env).exit_code == 0
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "mailbox",
                "register",
                "--address",
                "HOUMAO-alice@agents.localhost",
                "--principal-id",
                "HOUMAO-alice",
            ],
            env=env,
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
            str(overlay_root / "mailbox"),
        ],
    )
    project_list_result = runner.invoke(cli, ["project", "mailbox", "accounts", "list"], env=env)

    assert generic_list_result.exit_code == 0, generic_list_result.output
    assert project_list_result.exit_code == 0, project_list_result.output
    generic_accounts = json.loads(generic_list_result.output)["accounts"]
    project_accounts = json.loads(project_list_result.output)["accounts"]
    assert [(item["address"], item["status"]) for item in generic_accounts] == [
        (item["address"], item["status"]) for item in project_accounts
    ]


def test_project_mailbox_env_selected_overlay_without_config_fails_non_creating(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    overlay_root = (tmp_path / "ci-overlay").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(
        cli,
        ["--print-json", "project", "mailbox", "status"],
        env={PROJECT_OVERLAY_DIR_ENV_VAR: str(overlay_root)},
    )

    assert result.exit_code != 0
    assert str(overlay_root) in result.output
    assert "uses non-creating resolution and did not bootstrap it" in result.output
    assert "did not fall back to the shared mailbox root" in result.output
    assert not (overlay_root / "houmao-config.toml").exists()


def test_project_mailbox_clear_messages_uses_selected_overlay_and_preserves_accounts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner, repo_root, mailbox_root = _init_project_mailbox_repo(monkeypatch, tmp_path)
    sender_address = "HOUMAO-bob@agents.localhost"
    recipient_address = "HOUMAO-alice@agents.localhost"

    for address, principal_id in (
        (sender_address, "HOUMAO-bob"),
        (recipient_address, "HOUMAO-alice"),
    ):
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
                    principal_id,
                ],
            ).exit_code
            == 0
        )
    _deliver_cli_test_message(
        mailbox_root=mailbox_root,
        sender_address=sender_address,
        sender_principal_id="HOUMAO-bob",
        recipient_address=recipient_address,
        recipient_principal_id="HOUMAO-alice",
    )

    help_result = runner.invoke(cli, ["project", "mailbox", "--help"])
    dry_run_result = runner.invoke(
        cli,
        ["--print-json", "project", "mailbox", "clear-messages", "--dry-run"],
    )
    apply_result = runner.invoke(
        cli,
        ["--print-json", "project", "mailbox", "clear-messages", "--yes"],
    )

    assert help_result.exit_code == 0, help_result.output
    assert "clear-messages" in help_result.output
    assert dry_run_result.exit_code == 0, dry_run_result.output
    dry_run_payload = json.loads(dry_run_result.output)
    assert dry_run_payload["scope"]["mailbox_root"] == str(mailbox_root.resolve())
    assert dry_run_payload["selected_overlay_root"] == str((repo_root / ".houmao").resolve())
    assert dry_run_payload["dry_run"] is True
    assert any(
        action["artifact_kind"] == "canonical_message"
        for action in dry_run_payload["planned_actions"]
    )
    assert apply_result.exit_code == 0, apply_result.output
    apply_payload = json.loads(apply_result.output)
    assert apply_payload["scope"]["mailbox_root"] == str(mailbox_root.resolve())
    assert load_active_mailbox_registration(mailbox_root, address=recipient_address).address == (
        recipient_address
    )

    messages_result = runner.invoke(
        cli,
        ["project", "mailbox", "messages", "list", "--address", recipient_address],
    )

    assert messages_result.exit_code == 0, messages_result.output
    assert json.loads(messages_result.output)["messages"] == []


def test_project_mailbox_export_uses_selected_overlay_and_ignores_global_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner, repo_root, mailbox_root = _init_project_mailbox_repo(monkeypatch, tmp_path)
    sender_address = "HOUMAO-bob@agents.localhost"
    recipient_address = "HOUMAO-alice@agents.localhost"
    global_mailbox_root = (tmp_path / "global-mailbox").resolve()
    assert (
        runner.invoke(
            cli,
            ["mailbox", "init", "--mailbox-root", str(global_mailbox_root)],
        ).exit_code
        == 0
    )
    monkeypatch.setenv(HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR, str(global_mailbox_root))

    for address, principal_id in (
        (sender_address, "HOUMAO-bob"),
        (recipient_address, "HOUMAO-alice"),
    ):
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
                    principal_id,
                ],
            ).exit_code
            == 0
        )
    message_id = _deliver_cli_test_message(
        mailbox_root=mailbox_root,
        sender_address=sender_address,
        sender_principal_id="HOUMAO-bob",
        recipient_address=recipient_address,
        recipient_principal_id="HOUMAO-alice",
    )

    help_result = runner.invoke(cli, ["project", "mailbox", "--help"])
    selected_result = runner.invoke(
        cli,
        [
            "--print-json",
            "project",
            "mailbox",
            "export",
            "--output-dir",
            str(tmp_path / "project-selected-archive"),
            "--address",
            recipient_address,
        ],
    )
    all_accounts_result = runner.invoke(
        cli,
        [
            "--print-json",
            "project",
            "mailbox",
            "export",
            "--output-dir",
            str(tmp_path / "project-all-archive"),
            "--all-accounts",
        ],
    )

    assert help_result.exit_code == 0, help_result.output
    assert "export" in help_result.output
    assert selected_result.exit_code == 0, selected_result.output
    selected_payload = json.loads(selected_result.output)
    assert selected_payload["mailbox_root"] == str(mailbox_root.resolve())
    assert selected_payload["selected_overlay_root"] == str((repo_root / ".houmao").resolve())
    assert selected_payload["selected_addresses"] == [recipient_address]
    assert selected_payload["account_count"] == 1
    assert selected_payload["message_count"] == 1
    assert selected_payload["mailbox_root"] != str(global_mailbox_root)
    assert Path(selected_payload["manifest_path"]).is_file()
    assert message_id in Path(selected_payload["manifest_path"]).read_text(encoding="utf-8")
    assert all_accounts_result.exit_code == 0, all_accounts_result.output
    all_accounts_payload = json.loads(all_accounts_result.output)
    assert all_accounts_payload["mailbox_root"] == str(mailbox_root.resolve())
    assert all_accounts_payload["all_accounts"] is True
    assert all_accounts_payload["account_count"] >= 2


def test_project_mailbox_register_yes_overwrites_without_tty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, _repo_root, mailbox_root = _init_project_mailbox_repo(monkeypatch, tmp_path)
    address = "HOUMAO-alice@agents.localhost"

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
                "HOUMAO-alice",
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
            "HOUMAO-bob",
            "--yes",
        ],
    )

    assert result.exit_code == 0, result.output
    registration = load_active_mailbox_registration(mailbox_root, address=address)
    assert registration.owner_principal_id == "HOUMAO-bob"
