from __future__ import annotations

import json
import os
from pathlib import Path
import shutil

from click.testing import CliRunner
import pytest
import yaml

from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.srv_ctrl.commands.main import cli


def _fixture_agents_dir() -> Path:
    """Return the tracked plain agent-definition-directory fixture."""

    return (Path(__file__).resolve().parents[2] / "fixtures" / "plain-agent-def").resolve()


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


def _write_fake_provider_bin(bin_dir: Path, *, name: str, body: str) -> Path:
    """Write one fake provider executable for credential login tests."""

    path = (bin_dir / name).resolve()
    path.write_text("#!/bin/sh\nset -eu\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _provider_env(*, bin_dir: Path, record_dir: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build one CLI runner env that prefers fake provider commands."""

    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "RECORD_DIR": str(record_dir),
    }
    if extra is not None:
        env.update(extra)
    return env


def _extract_preserved_temp_home(output: str, *, tool: str) -> Path:
    """Extract the preserved temp-home path from one Click error output."""

    marker = f"Temporary {tool} login home preserved: "
    assert marker in output
    return Path(output.split(marker, 1)[1].strip()).resolve()


def test_top_level_credentials_help_mentions_supported_tools() -> None:
    result = CliRunner().invoke(cli, ["credentials", "--help"])

    assert result.exit_code == 0
    assert "claude" in result.output
    assert "codex" in result.output
    assert "gemini" in result.output
    assert "credential-management" in result.output or "credential" in result.output.lower()

    tool_result = CliRunner().invoke(cli, ["credentials", "codex", "--help"])
    assert tool_result.exit_code == 0
    assert "login" in tool_result.output


def test_credentials_codex_login_imports_auth_json_and_deletes_temp_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    agent_def_dir = _copy_agent_def_fixture(tmp_path)
    bin_dir = (tmp_path / "bin").resolve()
    record_dir = (tmp_path / "records").resolve()
    bin_dir.mkdir()
    record_dir.mkdir()
    _write_fake_provider_bin(
        bin_dir,
        name="codex",
        body="""
printf '%s\\n' "$@" > "$RECORD_DIR/codex.args"
printf '%s\\n' "$CODEX_HOME" > "$RECORD_DIR/codex.home"
if [ "${OPENAI_API_KEY+x}" = x ]; then printf present > "$RECORD_DIR/openai_api_key"; fi
if [ "${OPENAI_BASE_URL+x}" = x ]; then printf present > "$RECORD_DIR/openai_base_url"; fi
printf '{"logged_in": true}\\n' > "$CODEX_HOME/auth.json"
""",
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        cli,
        [
            "credentials",
            "codex",
            "login",
            "--agent-def-dir",
            str(agent_def_dir),
            "--name",
            "sandbox",
        ],
        env=_provider_env(
            bin_dir=bin_dir,
            record_dir=record_dir,
            extra={
                "OPENAI_API_KEY": "sk-existing",
                "OPENAI_BASE_URL": "https://old.example.test",
            },
        ),
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["operation"] == "add"
    assert payload["target_kind"] == "agent_def_dir"
    assert payload["login"]["provider_command"] == ["codex", "login", "--device-auth"]
    temp_home = Path(payload["login"]["temp_home"])
    assert payload["login"]["temp_home_deleted"] is True
    assert not temp_home.exists()
    assert (record_dir / "codex.args").read_text(encoding="utf-8").splitlines() == [
        "login",
        "--device-auth",
    ]
    assert not (record_dir / "openai_api_key").exists()
    assert not (record_dir / "openai_base_url").exists()
    assert json.loads(
        (
            _direct_auth_root(agent_def_dir, tool="codex", name="sandbox")
            / "files"
            / "auth.json"
        ).read_text(encoding="utf-8")
    ) == {"logged_in": True}


def test_credentials_codex_login_can_keep_temp_home_and_inherit_auth_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    agent_def_dir = _copy_agent_def_fixture(tmp_path)
    bin_dir = (tmp_path / "bin").resolve()
    record_dir = (tmp_path / "records").resolve()
    bin_dir.mkdir()
    record_dir.mkdir()
    _write_fake_provider_bin(
        bin_dir,
        name="codex",
        body="""
printf '%s\\n' "$@" > "$RECORD_DIR/codex.args"
if [ "${OPENAI_API_KEY+x}" = x ]; then printf present > "$RECORD_DIR/openai_api_key"; fi
printf '{"logged_in": true}\\n' > "$CODEX_HOME/auth.json"
""",
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        cli,
        [
            "credentials",
            "codex",
            "login",
            "--agent-def-dir",
            str(agent_def_dir),
            "--name",
            "browser-login",
            "--browser",
            "--keep-temp-home",
            "--inherit-auth-env",
        ],
        env=_provider_env(
            bin_dir=bin_dir,
            record_dir=record_dir,
            extra={"OPENAI_API_KEY": "sk-existing"},
        ),
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["login"]["provider_command"] == ["codex", "login"]
    assert payload["login"]["temp_home_deleted"] is False
    assert Path(payload["login"]["temp_home"]).is_dir()
    assert (record_dir / "codex.args").read_text(encoding="utf-8").splitlines() == ["login"]
    assert (record_dir / "openai_api_key").read_text(encoding="utf-8") == "present"


def test_project_credentials_claude_login_imports_vendor_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir()
    bin_dir = (tmp_path / "bin").resolve()
    record_dir = (tmp_path / "records").resolve()
    bin_dir.mkdir()
    record_dir.mkdir()
    _write_fake_provider_bin(
        bin_dir,
        name="claude",
        body="""
printf '%s\\n' "$@" > "$RECORD_DIR/claude.args"
if [ "${ANTHROPIC_AUTH_TOKEN+x}" = x ]; then printf present > "$RECORD_DIR/anthropic_auth_token"; fi
printf '{"claudeAiOauth": {"accessToken": "vendor-alpha"}}\\n' > "$CLAUDE_CONFIG_DIR/.credentials.json"
printf '{"hasCompletedOnboarding": true}\\n' > "$CLAUDE_CONFIG_DIR/.claude.json"
""",
    )
    monkeypatch.chdir(repo_root)
    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

    result = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "claude",
            "login",
            "--name",
            "vendor-login",
            "--claudeai",
            "--console",
            "--email",
            "user@example.test",
            "--sso",
        ],
        env=_provider_env(
            bin_dir=bin_dir,
            record_dir=record_dir,
            extra={"ANTHROPIC_AUTH_TOKEN": "old-token"},
        ),
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["target_kind"] == "project"
    assert payload["login"]["temp_home_deleted"] is True
    assert not Path(payload["login"]["temp_home"]).exists()
    assert (record_dir / "claude.args").read_text(encoding="utf-8").splitlines() == [
        "auth",
        "login",
        "--claudeai",
        "--console",
        "--email",
        "user@example.test",
        "--sso",
    ]
    assert not (record_dir / "anthropic_auth_token").exists()
    files_root = Path(payload["path"]) / "files"
    assert json.loads((files_root / ".credentials.json").read_text(encoding="utf-8")) == {
        "claudeAiOauth": {"accessToken": "vendor-alpha"}
    }
    assert json.loads((files_root / ".claude.json").read_text(encoding="utf-8")) == {
        "hasCompletedOnboarding": True
    }


def test_credentials_gemini_login_requires_update_for_existing_direct_credential(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    agent_def_dir = _copy_agent_def_fixture(tmp_path)
    bin_dir = (tmp_path / "bin").resolve()
    record_dir = (tmp_path / "records").resolve()
    bin_dir.mkdir()
    record_dir.mkdir()
    _write_fake_provider_bin(
        bin_dir,
        name="gemini",
        body="""
printf '%s\\n' "$GEMINI_CLI_HOME" > "$RECORD_DIR/gemini.home"
if [ -f "$GEMINI_CLI_HOME/.gemini/settings.json" ]; then printf present > "$RECORD_DIR/gemini_settings"; fi
if [ "${GEMINI_API_KEY+x}" = x ]; then printf present > "$RECORD_DIR/gemini_api_key"; fi
if [ "${NO_BROWSER:-}" = true ]; then printf true > "$RECORD_DIR/no_browser"; fi
printf '{"refresh_token": "gemini-token"}\\n' > "$GEMINI_CLI_HOME/.gemini/oauth_creds.json"
""",
    )
    monkeypatch.chdir(tmp_path)
    env = _provider_env(
        bin_dir=bin_dir,
        record_dir=record_dir,
        extra={"GEMINI_API_KEY": "old-key"},
    )

    add_result = runner.invoke(
        cli,
        [
            "credentials",
            "gemini",
            "login",
            "--agent-def-dir",
            str(agent_def_dir),
            "--name",
            "personal",
        ],
        env=env,
    )
    assert add_result.exit_code == 0, add_result.output
    assert not (record_dir / "gemini_api_key").exists()
    assert (record_dir / "gemini_settings").read_text(encoding="utf-8") == "present"

    duplicate_result = runner.invoke(
        cli,
        [
            "credentials",
            "gemini",
            "login",
            "--agent-def-dir",
            str(agent_def_dir),
            "--name",
            "personal",
        ],
        env=env,
    )
    assert duplicate_result.exit_code != 0
    assert "--update" in duplicate_result.output

    update_result = runner.invoke(
        cli,
        [
            "credentials",
            "gemini",
            "login",
            "--agent-def-dir",
            str(agent_def_dir),
            "--name",
            "personal",
            "--update",
            "--keep-temp-home",
            "--no-browser",
        ],
        env=env,
    )
    assert update_result.exit_code == 0, update_result.output
    update_payload = json.loads(update_result.output)
    assert update_payload["operation"] == "set"
    assert Path(update_payload["login"]["temp_home"]).is_dir()
    assert (record_dir / "no_browser").read_text(encoding="utf-8") == "true"


def test_credentials_login_failures_preserve_temp_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    agent_def_dir = _copy_agent_def_fixture(tmp_path)
    bin_dir = (tmp_path / "bin").resolve()
    record_dir = (tmp_path / "records").resolve()
    bin_dir.mkdir()
    record_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    _write_fake_provider_bin(
        bin_dir,
        name="codex",
        body="""
exit 9
""",
    )
    failed_provider = runner.invoke(
        cli,
        [
            "credentials",
            "codex",
            "login",
            "--agent-def-dir",
            str(agent_def_dir),
            "--name",
            "provider-fail",
        ],
        env=_provider_env(bin_dir=bin_dir, record_dir=record_dir),
    )
    assert failed_provider.exit_code != 0
    assert _extract_preserved_temp_home(failed_provider.output, tool="codex").is_dir()

    _write_fake_provider_bin(
        bin_dir,
        name="codex",
        body="""
printf ok > "$RECORD_DIR/missing_artifact_ran"
""",
    )
    missing_artifact = runner.invoke(
        cli,
        [
            "credentials",
            "codex",
            "login",
            "--agent-def-dir",
            str(agent_def_dir),
            "--name",
            "missing-artifact",
        ],
        env=_provider_env(bin_dir=bin_dir, record_dir=record_dir),
    )
    assert missing_artifact.exit_code != 0
    assert _extract_preserved_temp_home(missing_artifact.output, tool="codex").is_dir()

    (agent_def_dir / "tools" / "codex" / "adapter.yaml").unlink()
    _write_fake_provider_bin(
        bin_dir,
        name="codex",
        body="""
printf '{"logged_in": true}\\n' > "$CODEX_HOME/auth.json"
""",
    )
    import_failure = runner.invoke(
        cli,
        [
            "credentials",
            "codex",
            "login",
            "--agent-def-dir",
            str(agent_def_dir),
            "--name",
            "import-fail",
        ],
        env=_provider_env(bin_dir=bin_dir, record_dir=record_dir),
    )
    assert import_failure.exit_code != 0
    assert _extract_preserved_temp_home(import_failure.output, tool="codex").is_dir()


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


def test_credentials_direct_dir_remove_unlinks_symlinked_bundle_without_touching_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    agent_def_dir = _copy_agent_def_fixture(tmp_path)
    bundle_root = _direct_auth_root(agent_def_dir, tool="codex", name="sandbox")
    external_bundle = (tmp_path / "external-bundle").resolve()
    (external_bundle / "env").mkdir(parents=True, exist_ok=True)
    (external_bundle / "files").mkdir(parents=True, exist_ok=True)
    (external_bundle / "env" / "vars.env").write_text("OPENAI_API_KEY=sk-openai\n", encoding="utf-8")
    bundle_root.parent.mkdir(parents=True, exist_ok=True)
    bundle_root.symlink_to(external_bundle, target_is_directory=True)
    monkeypatch.chdir(tmp_path)

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
    assert not bundle_root.exists()
    assert (external_bundle / "env" / "vars.env").is_file()


def test_credentials_direct_dir_set_replaces_symlinked_auth_file_without_touching_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    agent_def_dir = _copy_agent_def_fixture(tmp_path)
    auth_json = (tmp_path / "auth.json").resolve()
    auth_json.write_text('{"logged_in": true}\n', encoding="utf-8")
    replacement_auth = (tmp_path / "replacement-auth.json").resolve()
    replacement_auth.write_text('{"logged_in": "replacement"}\n', encoding="utf-8")
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

    bundled_auth_json = _direct_auth_root(agent_def_dir, tool="codex", name="sandbox") / "files" / "auth.json"
    external_auth = (tmp_path / "external-auth.json").resolve()
    external_auth.write_text('{"logged_in": "external"}\n', encoding="utf-8")
    bundled_auth_json.unlink()
    bundled_auth_json.symlink_to(external_auth)

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
            "--auth-json",
            str(replacement_auth),
        ],
    )

    assert set_result.exit_code == 0, set_result.output
    assert bundled_auth_json.is_file()
    assert not bundled_auth_json.is_symlink()
    assert json.loads(bundled_auth_json.read_text(encoding="utf-8")) == {"logged_in": "replacement"}
    assert json.loads(external_auth.read_text(encoding="utf-8")) == {"logged_in": "external"}


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
