from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from click.testing import CliRunner

from houmao.agents.system_skills import system_skill_state_path_for_home
from houmao.srv_ctrl.commands.main import cli
from houmao.version import get_version

_DEFAULT_SET_NAMES = [
    "mailbox-full",
    "agent-memory",
    "advanced-usage",
    "touring",
    "user-control",
    "agent-instance",
    "agent-inspect",
    "agent-messaging",
    "agent-gateway",
]
_CATALOG_SKILLS = [
    "houmao-process-emails-via-gateway",
    "houmao-agent-email-comms",
    "houmao-adv-usage-pattern",
    "houmao-touring",
    "houmao-mailbox-mgr",
    "houmao-memory-mgr",
    "houmao-project-mgr",
    "houmao-specialist-mgr",
    "houmao-credential-mgr",
    "houmao-agent-definition",
    "houmao-agent-loop-pairwise",
    "houmao-agent-loop-pairwise-v2",
    "houmao-agent-loop-generic",
    "houmao-agent-instance",
    "houmao-agent-inspect",
    "houmao-agent-messaging",
    "houmao-agent-gateway",
]
_DEFAULT_RESOLVED_SKILLS = [
    "houmao-process-emails-via-gateway",
    "houmao-agent-email-comms",
    "houmao-mailbox-mgr",
    "houmao-memory-mgr",
    "houmao-adv-usage-pattern",
    "houmao-touring",
    "houmao-project-mgr",
    "houmao-specialist-mgr",
    "houmao-credential-mgr",
    "houmao-agent-definition",
    "houmao-agent-loop-pairwise",
    "houmao-agent-loop-pairwise-v2",
    "houmao-agent-loop-generic",
    "houmao-agent-instance",
    "houmao-agent-inspect",
    "houmao-agent-messaging",
    "houmao-agent-gateway",
]


def _run_houmao_mgr_module(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the package module entrypoint through a fresh Python subprocess."""

    repo_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    pythonpath_entries = [str(repo_root / "src")]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return subprocess.run(
        [sys.executable, "-m", "houmao.srv_ctrl", *args],
        cwd=(repo_root if cwd is None else cwd.resolve()),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def test_system_skills_help_lists_commands() -> None:
    result = CliRunner().invoke(cli, ["system-skills", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "install" in result.output
    assert "status" in result.output


def test_houmao_mgr_module_version_starts_successfully() -> None:
    result = _run_houmao_mgr_module("--version")

    assert result.returncode == 0, result.stderr
    assert get_version() in result.stdout


def test_houmao_mgr_module_system_skills_help_starts_successfully() -> None:
    result = _run_houmao_mgr_module("system-skills", "--help")

    assert result.returncode == 0, result.stderr
    assert "install" in result.stdout
    assert "status" in result.stdout


def test_houmao_mgr_module_system_skills_install_starts_successfully(tmp_path: Path) -> None:
    home_path = (tmp_path / "codex-home").resolve()

    result = _run_houmao_mgr_module(
        "--print-json",
        "system-skills",
        "install",
        "--tool",
        "codex",
        "--home",
        str(home_path),
        "--skill",
        "houmao-specialist-mgr",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["resolved_skills"] == ["houmao-specialist-mgr"]
    assert (home_path / "skills/houmao-specialist-mgr/SKILL.md").is_file()


def test_system_skills_install_help_omits_removed_default_flag() -> None:
    result = CliRunner().invoke(cli, ["system-skills", "install", "--help"])

    assert result.exit_code == 0
    assert "--default" not in result.output
    assert "--skill-set" in result.output
    assert "--set " not in result.output


def test_system_skills_list_reports_sets_and_auto_install_defaults() -> None:
    result = CliRunner().invoke(cli, ["--print-json", "system-skills", "list"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert [record["name"] for record in payload["skills"]] == _CATALOG_SKILLS
    assert [record["name"] for record in payload["sets"]] == [
        "mailbox-core",
        "mailbox-full",
        "agent-memory",
        "advanced-usage",
        "touring",
        "user-control",
        "agent-instance",
        "agent-inspect",
        "agent-messaging",
        "agent-gateway",
    ]
    assert payload["auto_install"]["cli_default_sets"] == _DEFAULT_SET_NAMES
    assert payload["auto_install"]["managed_launch_sets"] == [
        "mailbox-full",
        "agent-memory",
        "advanced-usage",
        "touring",
        "user-control",
        "agent-inspect",
        "agent-messaging",
        "agent-gateway",
    ]
    assert payload["auto_install"]["managed_join_sets"] == [
        "mailbox-full",
        "agent-memory",
        "advanced-usage",
        "touring",
        "user-control",
        "agent-inspect",
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
    agent_memory_record = next(
        record for record in payload["sets"] if record["name"] == "agent-memory"
    )
    assert agent_memory_record["skills"] == ["houmao-memory-mgr"]
    advanced_usage_record = next(
        record for record in payload["sets"] if record["name"] == "advanced-usage"
    )
    assert advanced_usage_record["skills"] == ["houmao-adv-usage-pattern"]
    touring_record = next(record for record in payload["sets"] if record["name"] == "touring")
    assert touring_record["skills"] == ["houmao-touring"]
    user_control_record = next(
        record for record in payload["sets"] if record["name"] == "user-control"
    )
    assert user_control_record["skills"] == [
        "houmao-project-mgr",
        "houmao-specialist-mgr",
        "houmao-credential-mgr",
        "houmao-agent-definition",
        "houmao-agent-loop-pairwise",
        "houmao-agent-loop-pairwise-v2",
        "houmao-agent-loop-generic",
    ]
    agent_inspect_record = next(
        record for record in payload["sets"] if record["name"] == "agent-inspect"
    )
    assert agent_inspect_record["skills"] == ["houmao-agent-inspect"]
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
    assert (home_path / "skills/houmao-memory-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-adv-usage-pattern/SKILL.md").is_file()
    assert (home_path / "skills/houmao-touring/SKILL.md").is_file()
    assert (home_path / "skills/houmao-project-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-specialist-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-credential-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-definition/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-loop-pairwise/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-loop-pairwise-v2/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-loop-generic/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-instance/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-inspect/SKILL.md").is_file()
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
    assert status_payload["installed_skills"] == _CATALOG_SKILLS
    assert status_payload["installed_skill_records"] == [
        {
            "name": skill_name,
            "projected_relative_dir": f"skills/{skill_name}",
            "projection_mode": "copy",
        }
        for skill_name in _CATALOG_SKILLS
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
    assert (expected_home / "skills/houmao-agent-inspect/SKILL.md").is_file()
    assert (expected_home / "skills/houmao-agent-messaging/SKILL.md").is_file()
    assert (expected_home / "skills/houmao-agent-gateway/SKILL.md").is_file()
    assert (expected_home / "skills/houmao-memory-mgr/SKILL.md").is_file()


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
            "--skill-set",
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
    assert (workspace / ".gemini/skills/houmao-agent-loop-pairwise/SKILL.md").is_file()
    assert (workspace / ".gemini/skills/houmao-agent-loop-pairwise-v2/SKILL.md").is_file()
    assert (workspace / ".gemini/skills/houmao-agent-loop-generic/SKILL.md").is_file()
    assert not (workspace / ".agents/skills").exists()


def test_system_skills_install_uses_project_scoped_copilot_default_home(
    tmp_path: Path, monkeypatch
) -> None:
    workspace = tmp_path.resolve()
    expected_home = workspace / ".github"
    monkeypatch.delenv("COPILOT_HOME", raising=False)
    monkeypatch.chdir(workspace)

    install_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "install",
            "--tool",
            "copilot",
            "--skill-set",
            "user-control",
        ],
    )

    assert install_result.exit_code == 0, install_result.output
    install_payload = json.loads(install_result.output)
    assert install_payload["home_path"] == str(expected_home)
    assert (expected_home / "skills/houmao-project-mgr/SKILL.md").is_file()
    assert (expected_home / "skills/houmao-specialist-mgr/SKILL.md").is_file()
    assert (expected_home / "skills/houmao-credential-mgr/SKILL.md").is_file()
    assert (expected_home / "skills/houmao-agent-definition/SKILL.md").is_file()
    assert (expected_home / "skills/houmao-agent-loop-pairwise/SKILL.md").is_file()
    assert (expected_home / "skills/houmao-agent-loop-pairwise-v2/SKILL.md").is_file()
    assert (expected_home / "skills/houmao-agent-loop-generic/SKILL.md").is_file()


def test_system_skills_install_supports_comma_separated_tools_with_project_defaults(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path.resolve()
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("COPILOT_HOME", raising=False)
    monkeypatch.delenv("GEMINI_CLI_HOME", raising=False)
    monkeypatch.chdir(workspace)

    install_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "install",
            "--tool",
            "claude, codex,copilot,gemini",
            "--skill-set",
            "user-control",
        ],
    )

    assert install_result.exit_code == 0, install_result.output
    payload = json.loads(install_result.output)
    assert payload["tools"] == ["claude", "codex", "copilot", "gemini"]
    installations = {record["tool"]: record for record in payload["installations"]}
    assert installations["claude"]["home_path"] == str(workspace / ".claude")
    assert installations["codex"]["home_path"] == str(workspace / ".codex")
    assert installations["copilot"]["home_path"] == str(workspace / ".github")
    assert installations["gemini"]["home_path"] == str(workspace)
    for record in installations.values():
        assert record["selected_sets"] == ["user-control"]
        assert record["explicit_skills"] == []
        assert record["projection_mode"] == "copy"
        assert record["resolved_skills"] == [
            "houmao-project-mgr",
            "houmao-specialist-mgr",
            "houmao-credential-mgr",
            "houmao-agent-definition",
            "houmao-agent-loop-pairwise",
            "houmao-agent-loop-pairwise-v2",
            "houmao-agent-loop-generic",
        ]
    assert (workspace / ".claude/skills/houmao-project-mgr/SKILL.md").is_file()
    assert (workspace / ".codex/skills/houmao-project-mgr/SKILL.md").is_file()
    assert (workspace / ".github/skills/houmao-project-mgr/SKILL.md").is_file()
    assert (workspace / ".gemini/skills/houmao-project-mgr/SKILL.md").is_file()


def test_system_skills_install_rejects_multi_tool_home_before_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path.resolve()
    explicit_home = workspace / "explicit-home"
    monkeypatch.chdir(workspace)

    result = CliRunner().invoke(
        cli,
        [
            "system-skills",
            "install",
            "--tool",
            "codex,claude",
            "--home",
            str(explicit_home),
            "--skill-set",
            "user-control",
        ],
    )

    assert result.exit_code != 0
    assert "--home can only be used when --tool names exactly one tool" in result.output
    assert not explicit_home.exists()
    assert not (workspace / ".codex").exists()
    assert not (workspace / ".claude").exists()


def test_system_skills_install_rejects_malformed_multi_tool_list_before_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path.resolve()
    monkeypatch.chdir(workspace)

    result = CliRunner().invoke(
        cli,
        [
            "system-skills",
            "install",
            "--tool",
            "codex,,gemini",
            "--skill",
            "houmao-specialist-mgr",
        ],
    )

    assert result.exit_code != 0
    assert "comma-separated tool lists cannot contain empty entries" in result.output
    assert not (workspace / ".codex").exists()
    assert not (workspace / ".gemini").exists()


def test_system_skills_install_rejects_duplicate_multi_tool_entries_before_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path.resolve()
    monkeypatch.chdir(workspace)

    result = CliRunner().invoke(
        cli,
        [
            "system-skills",
            "install",
            "--tool",
            "codex,codex",
            "--skill",
            "houmao-specialist-mgr",
        ],
    )

    assert result.exit_code != 0
    assert "Duplicate tool `codex`" in result.output
    assert not (workspace / ".codex").exists()


def test_system_skills_install_rejects_unknown_skill_set_before_multi_tool_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path.resolve()
    monkeypatch.chdir(workspace)

    result = CliRunner().invoke(
        cli,
        [
            "system-skills",
            "install",
            "--tool",
            "codex,gemini",
            "--skill-set",
            "unknown-set",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown system-skill set `unknown-set`" in result.output
    assert not (workspace / ".codex").exists()
    assert not (workspace / ".gemini").exists()


def test_system_skills_install_uses_copilot_env_redirect_when_home_is_omitted(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "copilot-home").resolve()

    install_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "install",
            "--tool",
            "copilot",
            "--skill",
            "houmao-specialist-mgr",
        ],
        env={"COPILOT_HOME": str(home_path)},
    )

    assert install_result.exit_code == 0, install_result.output
    install_payload = json.loads(install_result.output)
    assert install_payload["home_path"] == str(home_path)
    assert (home_path / "skills/houmao-specialist-mgr/SKILL.md").is_file()


def test_system_skills_install_uses_explicit_copilot_home_over_env_redirect(
    tmp_path: Path,
) -> None:
    env_home = (tmp_path / "env-copilot-home").resolve()
    user_home = (tmp_path / "user-home").resolve()
    explicit_home = user_home / ".copilot"

    install_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "install",
            "--tool",
            "copilot",
            "--home",
            "~/.copilot",
            "--skill",
            "houmao-agent-messaging",
        ],
        env={"COPILOT_HOME": str(env_home), "HOME": str(user_home)},
    )

    assert install_result.exit_code == 0, install_result.output
    install_payload = json.loads(install_result.output)
    assert install_payload["home_path"] == str(explicit_home)
    assert (explicit_home / "skills/houmao-agent-messaging/SKILL.md").is_file()
    assert not (env_home / "skills/houmao-agent-messaging").exists()


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
    assert payload["installed_skills"] == []
    assert payload["installed_skill_records"] == []


def test_system_skills_status_reports_project_scoped_copilot_default_home(
    tmp_path: Path, monkeypatch
) -> None:
    expected_home = (tmp_path / ".github").resolve()
    monkeypatch.delenv("COPILOT_HOME", raising=False)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "status",
            "--tool",
            "copilot",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["tool"] == "copilot"
    assert payload["home_path"] == str(expected_home)
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


def test_system_skills_status_ignores_stale_legacy_state_without_current_paths(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    state_path = system_skill_state_path_for_home(home_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "tool": "codex",
                "installed_at": "2026-04-09T00:00:00Z",
                "installed_skills": [
                    {
                        "name": "houmao-specialist-mgr",
                        "asset_subpath": "houmao-specialist-mgr",
                        "projected_relative_dir": "skills/houmao-specialist-mgr",
                        "projection_mode": "copy",
                        "content_digest": "stale",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

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
    assert status_payload["installed_skills"] == []
    assert status_payload["installed_skill_records"] == []


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


def test_system_skills_install_rejects_removed_set_flag() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "system-skills",
            "install",
            "--tool",
            "gemini",
            "--set",
            "user-control",
        ],
    )

    assert result.exit_code != 0
    assert "No such option: --set" in result.output


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
