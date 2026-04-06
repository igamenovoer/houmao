from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from houmao.srv_ctrl.commands.main import cli


def test_system_skills_help_lists_commands() -> None:
    result = CliRunner().invoke(cli, ["system-skills", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "install" in result.output
    assert "status" in result.output


def test_system_skills_list_reports_sets_and_auto_install_defaults() -> None:
    result = CliRunner().invoke(cli, ["--print-json", "system-skills", "list"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert [record["name"] for record in payload["skills"]] == [
        "houmao-process-emails-via-gateway",
        "houmao-email-via-agent-gateway",
        "houmao-email-via-filesystem",
        "houmao-email-via-stalwart",
        "houmao-manage-specialist",
        "houmao-manage-credentials",
        "houmao-manage-agent-definition",
        "houmao-manage-agent-instance",
    ]
    assert [record["name"] for record in payload["sets"]] == [
        "mailbox-core",
        "mailbox-full",
        "user-control",
        "agent-instance",
    ]
    assert payload["auto_install"]["cli_default_sets"] == [
        "mailbox-full",
        "user-control",
        "agent-instance",
    ]
    assert payload["auto_install"]["managed_launch_sets"] == ["mailbox-full", "user-control"]
    assert payload["auto_install"]["managed_join_sets"] == ["mailbox-full", "user-control"]
    user_control_record = next(
        record for record in payload["sets"] if record["name"] == "user-control"
    )
    assert user_control_record["skills"] == [
        "houmao-manage-specialist",
        "houmao-manage-credentials",
        "houmao-manage-agent-definition",
    ]


def test_system_skills_status_reports_missing_state_for_untouched_home(tmp_path: Path) -> None:
    home_path = tmp_path / "codex-home"

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "status",
            "--tool",
            "codex",
            "--home",
            str(home_path),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["tool"] == "codex"
    assert payload["state_exists"] is False
    assert payload["installed_skills"] == []
    assert payload["installed_skill_records"] == []


def test_system_skills_install_supports_default_and_status(tmp_path: Path) -> None:
    home_path = (tmp_path / "codex-home").resolve()

    install_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "install",
            "--tool",
            "codex",
            "--home",
            str(home_path),
            "--default",
        ],
    )

    assert install_result.exit_code == 0, install_result.output
    install_payload = json.loads(install_result.output)
    assert install_payload["selected_sets"] == ["mailbox-full", "user-control", "agent-instance"]
    assert install_payload["projection_mode"] == "copy"
    assert install_payload["resolved_skills"] == [
        "houmao-process-emails-via-gateway",
        "houmao-email-via-agent-gateway",
        "houmao-email-via-filesystem",
        "houmao-email-via-stalwart",
        "houmao-manage-specialist",
        "houmao-manage-credentials",
        "houmao-manage-agent-definition",
        "houmao-manage-agent-instance",
    ]
    assert (home_path / "skills/houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-email-via-agent-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-manage-specialist/SKILL.md").is_file()
    assert (home_path / "skills/houmao-manage-credentials/SKILL.md").is_file()
    assert (home_path / "skills/houmao-manage-agent-definition/SKILL.md").is_file()
    assert (home_path / "skills/houmao-manage-agent-instance/SKILL.md").is_file()

    status_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "status",
            "--tool",
            "codex",
            "--home",
            str(home_path),
        ],
    )

    assert status_result.exit_code == 0, status_result.output
    status_payload = json.loads(status_result.output)
    assert status_payload["state_exists"] is True
    assert status_payload["installed_skills"] == install_payload["resolved_skills"]
    assert status_payload["installed_skill_records"] == [
        {
            "name": skill_name,
            "projected_relative_dir": relative_dir,
            "projection_mode": "copy",
        }
        for skill_name, relative_dir in zip(
            install_payload["resolved_skills"],
            install_payload["projected_relative_dirs"],
            strict=True,
        )
    ]


def test_system_skills_install_supports_symlink_mode_and_status_reports_it(tmp_path: Path) -> None:
    home_path = (tmp_path / "codex-home").resolve()

    install_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "install",
            "--tool",
            "codex",
            "--home",
            str(home_path),
            "--skill",
            "houmao-manage-specialist",
            "--symlink",
        ],
    )

    assert install_result.exit_code == 0, install_result.output
    install_payload = json.loads(install_result.output)
    assert install_payload["projection_mode"] == "symlink"
    assert install_payload["resolved_skills"] == ["houmao-manage-specialist"]
    assert (home_path / "skills/houmao-manage-specialist").is_symlink()

    status_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "status",
            "--tool",
            "codex",
            "--home",
            str(home_path),
        ],
    )

    assert status_result.exit_code == 0, status_result.output
    status_payload = json.loads(status_result.output)
    assert status_payload["installed_skills"] == ["houmao-manage-specialist"]
    assert status_payload["installed_skill_records"] == [
        {
            "name": "houmao-manage-specialist",
            "projected_relative_dir": "skills/houmao-manage-specialist",
            "projection_mode": "symlink",
        }
    ]


def test_system_skills_install_fails_when_selection_is_omitted(tmp_path: Path) -> None:
    home_path = tmp_path / "gemini-home"

    result = CliRunner().invoke(
        cli,
        [
            "system-skills",
            "install",
            "--tool",
            "gemini",
            "--home",
            str(home_path),
        ],
    )

    assert result.exit_code != 0
    assert "Select at least one system skill" in result.output
