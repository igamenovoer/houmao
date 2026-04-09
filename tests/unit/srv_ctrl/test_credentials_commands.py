from __future__ import annotations

import json
from pathlib import Path
import shutil

from click.testing import CliRunner
import pytest
import yaml

from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.srv_ctrl.commands.main import cli


def _fixture_agents_dir() -> Path:
    """Return the tracked plain agent-definition-directory fixture."""

    return (Path(__file__).resolve().parents[2] / "fixtures" / "agents").resolve()


def _copy_agent_def_fixture(tmp_path: Path) -> Path:
    """Copy the tracked agent-definition fixture into one temporary workspace."""

    destination = (tmp_path / "agents").resolve()
    shutil.copytree(_fixture_agents_dir(), destination)
    return destination


def _direct_auth_root(agent_def_dir: Path, *, tool: str, name: str) -> Path:
    """Return one direct-dir auth bundle root."""

    return (agent_def_dir / "tools" / tool / "auth" / name).resolve()


def _direct_env_file(agent_def_dir: Path, *, tool: str, name: str) -> Path:
    """Return one direct-dir auth env file."""

    return (_direct_auth_root(agent_def_dir, tool=tool, name=name) / "env" / "vars.env").resolve()


def test_top_level_credentials_help_mentions_supported_tools() -> None:
    result = CliRunner().invoke(cli, ["credentials", "--help"])

    assert result.exit_code == 0
    assert "claude" in result.output
    assert "codex" in result.output
    assert "gemini" in result.output
    assert "credential-management" in result.output or "credential" in result.output.lower()


def test_credentials_fail_clearly_without_resolvable_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(cli, ["credentials", "gemini", "list"])

    assert result.exit_code != 0
    assert "--project" in result.output
    assert "--agent-def-dir" in result.output


def test_credentials_direct_dir_crud_and_env_target_resolution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    agent_def_dir = _copy_agent_def_fixture(tmp_path)
    auth_json = (tmp_path / "auth.json").resolve()
    auth_json.write_text('{"logged_in": true}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    add_result = runner.invoke(
        cli,
        [
            "credentials",
            "codex",
            "add",
            "--agent-def-dir",
            str(agent_def_dir),
            "--name",
            "sandbox",
            "--api-key",
            "sk-test",
            "--auth-json",
            str(auth_json),
        ],
    )
    assert add_result.exit_code == 0, add_result.output
    add_payload = json.loads(add_result.output)
    assert add_payload["target_kind"] == "agent_def_dir"
    assert Path(add_payload["path"]).is_dir()

    list_result = runner.invoke(
        cli,
        ["credentials", "codex", "list", "--agent-def-dir", str(agent_def_dir)],
    )
    assert list_result.exit_code == 0, list_result.output
    list_payload = json.loads(list_result.output)
    assert list_payload["target_kind"] == "agent_def_dir"
    assert "sandbox" in list_payload["credentials"]

    env_list_result = runner.invoke(
        cli,
        ["credentials", "codex", "list"],
        env={AGENT_DEF_DIR_ENV_VAR: str(agent_def_dir)},
    )
    assert env_list_result.exit_code == 0, env_list_result.output
    assert "sandbox" in json.loads(env_list_result.output)["credentials"]

    get_result = runner.invoke(
        cli,
        ["credentials", "codex", "get", "--agent-def-dir", str(agent_def_dir), "--name", "sandbox"],
    )
    assert get_result.exit_code == 0, get_result.output
    get_payload = json.loads(get_result.output)
    assert get_payload["env"]["OPENAI_API_KEY"] == {"present": True, "redacted": True}
    assert get_payload["files"]["auth.json"]["present"] is True

    set_result = runner.invoke(
        cli,
        [
            "credentials",
            "codex",
            "set",
            "--agent-def-dir",
            str(agent_def_dir),
            "--name",
            "sandbox",
            "--base-url",
            "https://proxy.example.test",
        ],
    )
    assert set_result.exit_code == 0, set_result.output
    assert _direct_env_file(agent_def_dir, tool="codex", name="sandbox").read_text(
        encoding="utf-8"
    ).splitlines() == [
        "OPENAI_API_KEY=sk-test",
        "OPENAI_BASE_URL=https://proxy.example.test",
    ]

    remove_result = runner.invoke(
        cli,
        [
            "credentials",
            "codex",
            "remove",
            "--agent-def-dir",
            str(agent_def_dir),
            "--name",
            "sandbox",
        ],
    )
    assert remove_result.exit_code == 0, remove_result.output
    assert not _direct_auth_root(agent_def_dir, tool="codex", name="sandbox").exists()


def test_credentials_direct_dir_rename_rewrites_managed_yaml_references(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    agent_def_dir = _copy_agent_def_fixture(tmp_path)
    auth_json = (tmp_path / "auth.json").resolve()
    auth_json.write_text('{"logged_in": true}\n', encoding="utf-8")
    (agent_def_dir / "launch-profiles").mkdir(parents=True, exist_ok=True)
    (agent_def_dir / "presets" / "reviewer.yaml").write_text(
        yaml.safe_dump(
            {
                "role": "reviewer",
                "tool": "codex",
                "setup": "default",
                "skills": [],
                "auth": "work",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (agent_def_dir / "launch-profiles" / "reviewer.yaml").write_text(
        yaml.safe_dump(
            {
                "source": {"kind": "recipe", "name": "reviewer"},
                "tool": "codex",
                "auth": "work",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert (
        runner.invoke(
            cli,
            [
                "credentials",
                "codex",
                "add",
                "--agent-def-dir",
                str(agent_def_dir),
                "--name",
                "work",
                "--api-key",
                "sk-test",
                "--auth-json",
                str(auth_json),
            ],
        ).exit_code
        == 0
    )

    rename_result = runner.invoke(
        cli,
        [
            "credentials",
            "codex",
            "rename",
            "--agent-def-dir",
            str(agent_def_dir),
            "--name",
            "work",
            "--to",
            "breakglass",
        ],
    )
    assert rename_result.exit_code == 0, rename_result.output
    rename_payload = json.loads(rename_result.output)
    assert rename_payload["target_kind"] == "agent_def_dir"
    assert len(rename_payload["rewritten_files"]) == 2
    assert _direct_auth_root(agent_def_dir, tool="codex", name="breakglass").is_dir()
    assert not _direct_auth_root(agent_def_dir, tool="codex", name="work").exists()
    assert yaml.safe_load((agent_def_dir / "presets" / "reviewer.yaml").read_text(encoding="utf-8"))[
        "auth"
    ] == "breakglass"
    assert yaml.safe_load(
        (agent_def_dir / "launch-profiles" / "reviewer.yaml").read_text(encoding="utf-8")
    )["auth"] == "breakglass"


def test_credentials_explicit_agent_def_dir_promotes_overlay_managed_projection_to_project_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json = (tmp_path / "auth.json").resolve()
    auth_json.write_text('{"logged_in": true}\n', encoding="utf-8")
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    add_result = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "codex",
            "add",
            "--name",
            "work",
            "--api-key",
            "sk-openai",
            "--auth-json",
            str(auth_json),
        ],
    )
    assert add_result.exit_code == 0, add_result.output

    list_result = runner.invoke(
        cli,
        [
            "credentials",
            "codex",
            "list",
            "--agent-def-dir",
            str((repo_root / ".houmao" / "agents").resolve()),
        ],
    )
    assert list_result.exit_code == 0, list_result.output
    list_payload = json.loads(list_result.output)
    assert list_payload["target_kind"] == "project"
    assert list_payload["project_root"] == str(repo_root)
    assert list_payload["credentials"] == ["work"]
