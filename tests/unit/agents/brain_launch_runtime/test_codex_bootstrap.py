from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from gig_agents.agents.brain_launch_runtime.backends.codex_bootstrap import (
    ensure_codex_home_bootstrap,
)
from gig_agents.agents.brain_launch_runtime.errors import BackendExecutionError


def _read_config(home_path: Path) -> tuple[str, dict[str, object]]:
    raw = (home_path / "config.toml").read_text(encoding="utf-8")
    return raw, tomllib.loads(raw)


def test_codex_bootstrap_patches_config_idempotently_and_seeds_repo_trust(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir()
    (agent_def_dir / ".git").mkdir()
    workdir = agent_def_dir / "src"
    workdir.mkdir()

    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "config.toml").write_text(
        (
            'model = "gpt-5.3-codex"\n'
            'approval_policy = "on-request"\n'
            'sandbox_mode = "workspace-write"\n'
            "\n"
            "[features]\n"
            "unified_exec = true\n"
        ),
        encoding="utf-8",
    )

    ensure_codex_home_bootstrap(
        home_path=home,
        env={"OPENAI_API_KEY": "sk-test"},
        working_directory=workdir,
    )
    first_raw, first_payload = _read_config(home)
    ensure_codex_home_bootstrap(
        home_path=home,
        env={"OPENAI_API_KEY": "sk-test"},
        working_directory=workdir,
    )
    second_raw, second_payload = _read_config(home)

    assert first_raw == second_raw
    assert first_payload == second_payload
    assert first_payload["model"] == "gpt-5.3-codex"
    assert first_payload["approval_policy"] == "on-request"
    assert first_payload["sandbox_mode"] == "workspace-write"
    assert first_payload["notice"]["hide_full_access_warning"] is True
    assert first_payload["projects"][str(agent_def_dir.resolve())]["trust_level"] == "trusted"
    assert first_payload["features"]["unified_exec"] is True


def test_codex_bootstrap_falls_back_to_workdir_and_does_not_add_policy_defaults(
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "workspace"
    workdir.mkdir()

    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "config.toml").write_text(
        'model = "gpt-5.3-codex"\n',
        encoding="utf-8",
    )

    ensure_codex_home_bootstrap(
        home_path=home,
        env={"OPENAI_API_KEY": "sk-test"},
        working_directory=workdir,
    )
    _, payload = _read_config(home)

    assert payload["model"] == "gpt-5.3-codex"
    assert "approval_policy" not in payload
    assert "sandbox_mode" not in payload
    assert payload["notice"]["hide_full_access_warning"] is True
    assert payload["projects"][str(workdir.resolve())]["trust_level"] == "trusted"


def test_codex_bootstrap_accepts_non_empty_auth_json_without_api_key(
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "workspace"
    workdir.mkdir()

    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"session_id": "abc"}\n', encoding="utf-8")
    (home / "config.toml").write_text('model = "gpt-5.3-codex"\n', encoding="utf-8")

    ensure_codex_home_bootstrap(home_path=home, env={}, working_directory=workdir)
    _, payload = _read_config(home)

    assert payload["model"] == "gpt-5.3-codex"
    assert payload["notice"]["hide_full_access_warning"] is True


@pytest.mark.parametrize("auth_payload", [None, "{}\n"])
def test_codex_bootstrap_requires_openai_api_key_or_usable_auth_json(
    tmp_path: Path,
    auth_payload: str | None,
) -> None:
    workdir = tmp_path / "workspace"
    workdir.mkdir()

    home = tmp_path / "codex-home"
    home.mkdir()
    if auth_payload is not None:
        (home / "auth.json").write_text(auth_payload, encoding="utf-8")

    with pytest.raises(
        BackendExecutionError,
        match="requires either valid `auth.json` or `OPENAI_API_KEY`",
    ):
        ensure_codex_home_bootstrap(home_path=home, env={}, working_directory=workdir)
