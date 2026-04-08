from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from houmao.srv_ctrl.commands.main import cli

_DEFAULT_SET_NAMES = [
    "mailbox-full",
    "advanced-usage",
    "user-control",
    "agent-instance",
    "agent-messaging",
    "agent-gateway",
]
_CATALOG_SKILLS = [
    "houmao-process-emails-via-gateway",
    "houmao-agent-email-comms",
    "houmao-adv-usage-pattern",
    "houmao-mailbox-mgr",
    "houmao-project-mgr",
    "houmao-specialist-mgr",
    "houmao-credential-mgr",
    "houmao-agent-definition",
    "houmao-agent-instance",
    "houmao-agent-messaging",
    "houmao-agent-gateway",
]
_DEFAULT_RESOLVED_SKILLS = [
    "houmao-process-emails-via-gateway",
    "houmao-agent-email-comms",
    "houmao-mailbox-mgr",
    "houmao-adv-usage-pattern",
    "houmao-project-mgr",
    "houmao-specialist-mgr",
    "houmao-credential-mgr",
    "houmao-agent-definition",
    "houmao-agent-instance",
    "houmao-agent-messaging",
    "houmao-agent-gateway",
]


def test_system_skills_help_lists_commands() -> None:
    result = CliRunner().invoke(cli, ["system-skills", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "install" in result.output
    assert "status" in result.output


def test_system_skills_install_help_omits_removed_default_flag() -> None:
    result = CliRunner().invoke(cli, ["system-skills", "install", "--help"])

    assert result.exit_code == 0
    assert "--default" not in result.output


def test_system_skills_list_reports_sets_and_auto_install_defaults() -> None:
    result = CliRunner().invoke(cli, ["--print-json", "system-skills", "list"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert [record["name"] for record in payload["skills"]] == _CATALOG_SKILLS
    assert [record["name"] for record in payload["sets"]] == [
        "mailbox-core",
        "mailbox-full",
        "advanced-usage",
        "user-control",
        "agent-instance",
        "agent-messaging",
        "agent-gateway",
    ]
    assert payload["auto_install"]["cli_default_sets"] == _DEFAULT_SET_NAMES
    assert payload["auto_install"]["managed_launch_sets"] == [
        "mailbox-full",
        "advanced-usage",
        "user-control",
        "agent-messaging",
        "agent-gateway",
    ]
    assert payload["auto_install"]["managed_join_sets"] == [
        "mailbox-full",
        "advanced-usage",
        "user-control",
        "agent-messaging",
        "agent-gateway",
    ]
    mailbox_core_record = next(
        record for record in payload["sets"] if record["name"] == "mailbox-core"
    )
    assert mailbox_core_record["skills"] == [
        "houmao-process-emails-via-gateway",
        "houmao-agent-email-comms",
    ]
    mailbox_full_record = next(
        record for record in payload["sets"] if record["name"] == "mailbox-full"
    )
    assert mailbox_full_record["skills"] == [
        "houmao-process-emails-via-gateway",
        "houmao-agent-email-comms",
        "houmao-mailbox-mgr",
    ]
    advanced_usage_record = next(
        record for record in payload["sets"] if record["name"] == "advanced-usage"
    )
    assert advanced_usage_record["skills"] == ["houmao-adv-usage-pattern"]
    user_control_record = next(
        record for record in payload["sets"] if record["name"] == "user-control"
    )
    assert user_control_record["skills"] == [
        "houmao-project-mgr",
        "houmao-specialist-mgr",
        "houmao-credential-mgr",
        "houmao-agent-definition",
    ]
    agent_messaging_record = next(
        record for record in payload["sets"] if record["name"] == "agent-messaging"
    )
    assert agent_messaging_record["skills"] == ["houmao-agent-messaging"]
    agent_gateway_record = next(
        record for record in payload["sets"] if record["name"] == "agent-gateway"
    )
    assert agent_gateway_record["skills"] == ["houmao-agent-gateway"]


def test_system_skills_install_uses_cli_default_selection_when_selection_is_omitted(
    tmp_path: Path,
) -> None:
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
        ],
    )

    assert install_result.exit_code == 0, install_result.output
    install_payload = json.loads(install_result.output)
    assert install_payload["home_path"] == str(home_path)
    assert install_payload["selected_sets"] == _DEFAULT_SET_NAMES
    assert install_payload["projection_mode"] == "copy"
    assert install_payload["resolved_skills"] == _DEFAULT_RESOLVED_SKILLS
    assert (home_path / "skills/houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-email-comms/SKILL.md").is_file()
    assert (home_path / "skills/houmao-mailbox-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-adv-usage-pattern/SKILL.md").is_file()
    assert (home_path / "skills/houmao-project-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-specialist-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-credential-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-definition/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-instance/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-messaging/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-gateway/SKILL.md").is_file()

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
    assert status_payload["home_path"] == str(home_path)
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


def test_system_skills_install_uses_explicit_home_over_env_redirect(tmp_path: Path) -> None:
    env_home = (tmp_path / "env-codex-home").resolve()
    explicit_home = (tmp_path / "explicit-codex-home").resolve()

    install_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "install",
            "--tool",
            "codex",
            "--home",
            str(explicit_home),
            "--skill",
            "houmao-specialist-mgr",
        ],
        env={"CODEX_HOME": str(env_home)},
    )

    assert install_result.exit_code == 0, install_result.output
    install_payload = json.loads(install_result.output)
    assert install_payload["home_path"] == str(explicit_home)
    assert (explicit_home / "skills/houmao-specialist-mgr/SKILL.md").is_file()
    assert not (env_home / "skills/houmao-specialist-mgr").exists()


def test_system_skills_install_uses_env_redirect_when_home_is_omitted(tmp_path: Path) -> None:
    home_path = (tmp_path / "claude-home").resolve()

    install_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "install",
            "--tool",
            "claude",
        ],
        env={"CLAUDE_CONFIG_DIR": str(home_path)},
    )

    assert install_result.exit_code == 0, install_result.output
    install_payload = json.loads(install_result.output)
    assert install_payload["home_path"] == str(home_path)
    assert install_payload["selected_sets"] == _DEFAULT_SET_NAMES
    assert (home_path / "skills/houmao-specialist-mgr/SKILL.md").is_file()


def test_system_skills_install_uses_project_scoped_codex_default_home(
    tmp_path: Path, monkeypatch
) -> None:
    expected_home = (tmp_path / ".codex").resolve()
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.chdir(tmp_path)

    install_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "install",
            "--tool",
            "codex",
        ],
    )

    assert install_result.exit_code == 0, install_result.output
    install_payload = json.loads(install_result.output)
    assert install_payload["home_path"] == str(expected_home)
    assert install_payload["selected_sets"] == _DEFAULT_SET_NAMES
    assert (expected_home / "skills/houmao-agent-instance/SKILL.md").is_file()
    assert (expected_home / "skills/houmao-agent-messaging/SKILL.md").is_file()
    assert (expected_home / "skills/houmao-agent-gateway/SKILL.md").is_file()


def test_system_skills_install_uses_project_root_for_gemini_default_home(
    tmp_path: Path, monkeypatch
) -> None:
    workspace = tmp_path.resolve()
    monkeypatch.delenv("GEMINI_CLI_HOME", raising=False)
    monkeypatch.chdir(workspace)

    install_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "install",
            "--tool",
            "gemini",
            "--set",
            "user-control",
        ],
    )

    assert install_result.exit_code == 0, install_result.output
    install_payload = json.loads(install_result.output)
    assert install_payload["home_path"] == str(workspace)
    assert (workspace / ".gemini/skills/houmao-project-mgr/SKILL.md").is_file()
    assert (workspace / ".gemini/skills/houmao-specialist-mgr/SKILL.md").is_file()
    assert (workspace / ".gemini/skills/houmao-credential-mgr/SKILL.md").is_file()
    assert (workspace / ".gemini/skills/houmao-agent-definition/SKILL.md").is_file()
    assert not (workspace / ".agents/skills").exists()


def test_system_skills_status_reports_missing_state_for_project_default_home(
    tmp_path: Path, monkeypatch
) -> None:
    expected_home = (tmp_path / ".codex").resolve()
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "status",
            "--tool",
            "codex",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["tool"] == "codex"
    assert payload["home_path"] == str(expected_home)
    assert payload["state_exists"] is False
    assert payload["installed_skills"] == []
    assert payload["installed_skill_records"] == []


def test_system_skills_status_reports_env_redirect_home_when_omitted(tmp_path: Path) -> None:
    home_path = (tmp_path / "claude-home").resolve()

    install_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "install",
            "--tool",
            "claude",
            "--skill",
            "houmao-specialist-mgr",
        ],
        env={"CLAUDE_CONFIG_DIR": str(home_path)},
    )
    assert install_result.exit_code == 0, install_result.output

    status_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "status",
            "--tool",
            "claude",
        ],
        env={"CLAUDE_CONFIG_DIR": str(home_path)},
    )

    assert status_result.exit_code == 0, status_result.output
    status_payload = json.loads(status_result.output)
    assert status_payload["home_path"] == str(home_path)
    assert status_payload["state_exists"] is True
    assert status_payload["installed_skills"] == ["houmao-specialist-mgr"]


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
            "houmao-specialist-mgr",
            "--symlink",
        ],
    )

    assert install_result.exit_code == 0, install_result.output
    install_payload = json.loads(install_result.output)
    assert install_payload["projection_mode"] == "symlink"
    assert install_payload["resolved_skills"] == ["houmao-specialist-mgr"]
    assert (home_path / "skills/houmao-specialist-mgr").is_symlink()

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
    assert status_payload["installed_skills"] == ["houmao-specialist-mgr"]
    assert status_payload["installed_skill_records"] == [
        {
            "name": "houmao-specialist-mgr",
            "projected_relative_dir": "skills/houmao-specialist-mgr",
            "projection_mode": "symlink",
        }
    ]


def test_system_skills_install_rejects_removed_default_flag() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "system-skills",
            "install",
            "--tool",
            "gemini",
            "--default",
        ],
    )

    assert result.exit_code != 0
    assert "No such option: --default" in result.output


def test_system_skills_install_rejects_superseded_current_skill_names(tmp_path: Path) -> None:
    home_path = (tmp_path / "codex-home").resolve()

    for legacy_name in (
        "houmao-manage-specialist",
        "houmao-manage-credentials",
        "houmao-manage-agent-definition",
        "houmao-manage-agent-instance",
    ):
        result = CliRunner().invoke(
            cli,
            [
                "system-skills",
                "install",
                "--tool",
                "codex",
                "--home",
                str(home_path),
                "--skill",
                legacy_name,
            ],
        )

        assert result.exit_code != 0
        assert f"Unknown system skill `{legacy_name}`" in result.output
