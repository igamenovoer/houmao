from __future__ import annotations

from pathlib import Path

import pytest

from houmao.agents.native_launch_resolver import (
    resolve_effective_agent_def_dir,
    resolve_native_launch_target,
    tool_for_provider,
)
from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR


def test_tool_for_provider_maps_supported_provider_ids() -> None:
    assert tool_for_provider("claude_code") == "claude"
    assert tool_for_provider("codex") == "codex"
    assert tool_for_provider("q_cli") == "q_cli"


def test_resolve_effective_agent_def_dir_uses_workdir_default_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(AGENT_DEF_DIR_ENV_VAR, raising=False)
    workdir = (tmp_path / "workspace").resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    resolved = resolve_effective_agent_def_dir(working_directory=workdir)

    assert resolved == (workdir / ".agentsys" / "agents").resolve()


def test_resolve_native_launch_target_resolves_tool_lane_default_recipe_and_role(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = (tmp_path / "agents").resolve()
    recipe_path = (
        agent_def_dir
        / "brains"
        / "brain-recipes"
        / "claude"
        / "gpu-kernel-coder-default.yaml"
    )
    recipe_path.parent.mkdir(parents=True, exist_ok=True)
    recipe_path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "name: gpu-kernel-coder-default",
                "tool: claude",
                "skills: []",
                "config_profile: default",
                "credential_profile: demo-default",
                "",
            ]
        ),
        encoding="utf-8",
    )
    role_prompt_path = agent_def_dir / "roles" / "gpu-kernel-coder" / "system-prompt.md"
    role_prompt_path.parent.mkdir(parents=True, exist_ok=True)
    role_prompt_path.write_text("Demo role prompt\n", encoding="utf-8")
    monkeypatch.setenv(AGENT_DEF_DIR_ENV_VAR, str(agent_def_dir))

    target = resolve_native_launch_target(
        selector="gpu-kernel-coder",
        provider="claude_code",
        working_directory=(tmp_path / "workdir").resolve(),
    )

    assert target.tool == "claude"
    assert target.recipe_path == recipe_path.resolve()
    assert target.role_name == "gpu-kernel-coder"
    assert target.role_prompt == "Demo role prompt"
    assert target.role_prompt_path == role_prompt_path.resolve()


def test_resolve_native_launch_target_treats_missing_role_as_brain_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = (tmp_path / "agents").resolve()
    recipe_path = (
        agent_def_dir
        / "brains"
        / "brain-recipes"
        / "codex"
        / "gpu-kernel-coder-default.yaml"
    )
    recipe_path.parent.mkdir(parents=True, exist_ok=True)
    recipe_path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "name: gpu-kernel-coder-default",
                "tool: codex",
                "skills: []",
                "config_profile: default",
                "credential_profile: demo-default",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(AGENT_DEF_DIR_ENV_VAR, str(agent_def_dir))

    target = resolve_native_launch_target(
        selector="gpu-kernel-coder",
        provider="codex",
        working_directory=(tmp_path / "workdir").resolve(),
    )

    assert target.recipe_path == recipe_path.resolve()
    assert target.role_name is None
    assert target.role_prompt == ""
    assert target.role_prompt_path is None
