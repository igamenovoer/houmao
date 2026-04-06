from __future__ import annotations

from pathlib import Path

import pytest

from houmao.agents.native_launch_resolver import (
    resolve_effective_agent_def_dir,
    resolve_native_launch_target,
    tool_for_provider,
)
from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.project.overlay import (
    PROJECT_OVERLAY_DIR_ENV_VAR,
    bootstrap_project_overlay,
    bootstrap_project_overlay_at_root,
)


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

    assert resolved == (workdir / ".houmao" / "agents").resolve()


def test_resolve_effective_agent_def_dir_uses_discovered_project_overlay_when_present(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(AGENT_DEF_DIR_ENV_VAR, raising=False)
    project_root = (tmp_path / "repo").resolve()
    nested_dir = project_root / "nested"
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(project_root)

    resolved = resolve_effective_agent_def_dir(working_directory=nested_dir)

    assert resolved == (project_root / ".houmao" / "agents").resolve()
    assert resolved.is_dir()


def test_resolve_effective_agent_def_dir_uses_overlay_env_before_discovery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(AGENT_DEF_DIR_ENV_VAR, raising=False)
    project_root = (tmp_path / "repo").resolve()
    overlay_root = (tmp_path / "ci-overlay").resolve()
    nested_dir = project_root / "nested"
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(project_root)
    bootstrap_project_overlay_at_root(overlay_root)
    monkeypatch.setenv(PROJECT_OVERLAY_DIR_ENV_VAR, str(overlay_root))

    resolved = resolve_effective_agent_def_dir(working_directory=nested_dir)

    assert resolved == (overlay_root / "agents").resolve()
    assert resolved.is_dir()


def test_resolve_native_launch_target_resolves_tool_lane_default_recipe_and_role(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = (tmp_path / "agents").resolve()
    preset_path = agent_def_dir / "presets" / "gpu-kernel-coder-claude-default.yaml"
    preset_path.parent.mkdir(parents=True, exist_ok=True)
    preset_path.write_text(
        "\n".join(
            [
                "role: gpu-kernel-coder",
                "tool: claude",
                "setup: default",
                "skills: []",
                "auth: demo-default",
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
    assert target.recipe_path == preset_path.resolve()
    assert target.role_name == "gpu-kernel-coder"
    assert target.role_prompt == "Demo role prompt"
    assert target.role_prompt_path == role_prompt_path.resolve()


def test_resolve_native_launch_target_requires_role_prompt_for_preset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = (tmp_path / "agents").resolve()
    preset_path = agent_def_dir / "presets" / "gpu-kernel-coder-codex-default.yaml"
    preset_path.parent.mkdir(parents=True, exist_ok=True)
    preset_path.write_text(
        "\n".join(
            [
                "role: gpu-kernel-coder",
                "tool: codex",
                "setup: default",
                "skills: []",
                "auth: demo-default",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(AGENT_DEF_DIR_ENV_VAR, str(agent_def_dir))

    with pytest.raises(FileNotFoundError, match="Missing role prompt"):
        resolve_native_launch_target(
            selector="gpu-kernel-coder",
            provider="codex",
            working_directory=(tmp_path / "workdir").resolve(),
        )
