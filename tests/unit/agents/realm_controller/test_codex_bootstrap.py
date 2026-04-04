from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from houmao.agents.realm_controller.backends.codex_bootstrap import (
    ensure_codex_home_bootstrap,
)
from houmao.agents.realm_controller.errors import BackendExecutionError


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
            'model_provider = "yunwu-openai"\n'
            "\n"
            "[model_providers.yunwu-openai]\n"
            'name = "Yunwu"\n'
            'base_url = "https://api.example.test/v1"\n'
            'env_key = "OPENAI_API_KEY"\n'
            "requires_openai_auth = false\n"
            'wire_api = "responses"\n'
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
    assert first_payload["model"] == "gpt-5.4"
    assert first_payload["approval_policy"] == "never"
    assert first_payload["sandbox_mode"] == "danger-full-access"
    assert first_payload["model_provider"] == "yunwu-openai"
    assert first_payload["notice"]["hide_full_access_warning"] is True
    assert first_payload["notice"]["model_migrations"]["gpt-5.3-codex"] == "gpt-5.4"
    assert first_payload["projects"][str(agent_def_dir.resolve())]["trust_level"] == "trusted"
    assert first_payload["features"]["unified_exec"] is True


def test_codex_bootstrap_falls_back_to_workdir_and_seeds_runtime_defaults(
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "workspace"
    workdir.mkdir()

    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"session_id": "abc"}\n', encoding="utf-8")

    ensure_codex_home_bootstrap(home_path=home, env={}, working_directory=workdir)
    _, payload = _read_config(home)

    assert payload["model"] == "gpt-5.4"
    assert payload["approval_policy"] == "never"
    assert payload["sandbox_mode"] == "danger-full-access"
    assert payload["notice"]["hide_full_access_warning"] is True
    assert payload["notice"]["model_migrations"]["gpt-5.3-codex"] == "gpt-5.4"
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

    assert payload["model"] == "gpt-5.4"
    assert payload["approval_policy"] == "never"
    assert payload["sandbox_mode"] == "danger-full-access"
    assert payload["notice"]["hide_full_access_warning"] is True


@pytest.mark.parametrize(
    ("auth_payload", "config_payload", "env"),
    [
        (None, None, {"OPENAI_API_KEY": "sk-test"}),
        (
            None,
            (
                'model_provider = "yunwu-openai"\n'
                "\n"
                "[model_providers.yunwu-openai]\n"
                'name = "Yunwu"\n'
                'base_url = "https://api.example.test/v1"\n'
                'env_key = "OPENAI_API_KEY"\n'
                "requires_openai_auth = false\n"
                'wire_api = "responses"\n'
            ),
            {},
        ),
        ("{}\n", None, {}),
    ],
)
def test_codex_bootstrap_requires_credential_readiness_contract(
    tmp_path: Path,
    auth_payload: str | None,
    config_payload: str | None,
    env: dict[str, str],
) -> None:
    workdir = tmp_path / "workspace"
    workdir.mkdir()

    home = tmp_path / "codex-home"
    home.mkdir()
    if auth_payload is not None:
        (home / "auth.json").write_text(auth_payload, encoding="utf-8")
    if config_payload is not None:
        (home / "config.toml").write_text(config_payload, encoding="utf-8")

    with pytest.raises(
        BackendExecutionError,
        match="Codex credential readiness requires|Codex env-only provider",
    ):
        ensure_codex_home_bootstrap(home_path=home, env=env, working_directory=workdir)
