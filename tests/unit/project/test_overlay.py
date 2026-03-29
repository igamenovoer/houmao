from __future__ import annotations

from pathlib import Path

import pytest

from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.project.overlay import (
    bootstrap_project_overlay,
    discover_project_overlay,
    resolve_project_aware_agent_def_dir,
)


def test_resolve_project_aware_agent_def_dir_prefers_cli_over_env_and_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = (tmp_path / "repo").resolve()
    nested_dir = project_root / "nested" / "deeper"
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(project_root)
    monkeypatch.setenv(AGENT_DEF_DIR_ENV_VAR, str(tmp_path / "env-agent-def"))

    resolution = resolve_project_aware_agent_def_dir(
        cwd=nested_dir,
        cli_value="../cli-agent-def",
    )

    assert resolution.source == "cli"
    assert resolution.agent_def_dir == (nested_dir / "../cli-agent-def").resolve()


def test_resolve_project_aware_agent_def_dir_uses_env_when_cli_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = (tmp_path / "repo").resolve()
    nested_dir = project_root / "nested"
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(project_root)
    env_agent_def_dir = (tmp_path / "env-agent-def").resolve()
    monkeypatch.setenv(AGENT_DEF_DIR_ENV_VAR, str(env_agent_def_dir))

    resolution = resolve_project_aware_agent_def_dir(cwd=nested_dir)

    assert resolution.source == "env"
    assert resolution.agent_def_dir == env_agent_def_dir
    assert resolution.project_overlay is None


def test_resolve_project_aware_agent_def_dir_discovers_nearest_project_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(AGENT_DEF_DIR_ENV_VAR, raising=False)
    project_root = (tmp_path / "repo").resolve()
    nested_dir = project_root / "a" / "b" / "c"
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(project_root)

    resolution = resolve_project_aware_agent_def_dir(cwd=nested_dir)

    assert resolution.source == "project_config"
    assert resolution.project_overlay is not None
    assert resolution.project_overlay.project_root == project_root
    assert resolution.agent_def_dir == (project_root / ".houmao" / "agents").resolve()


def test_resolve_project_aware_agent_def_dir_falls_back_to_legacy_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(AGENT_DEF_DIR_ENV_VAR, raising=False)
    workdir = (tmp_path / "workspace").resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    resolution = resolve_project_aware_agent_def_dir(cwd=workdir)

    assert resolution.source == "legacy_default"
    assert resolution.agent_def_dir == (workdir / ".agentsys" / "agents").resolve()


def test_bootstrap_project_overlay_discovers_created_overlay(tmp_path: Path) -> None:
    project_root = (tmp_path / "repo").resolve()
    nested_dir = project_root / "src"
    nested_dir.mkdir(parents=True, exist_ok=True)

    result = bootstrap_project_overlay(project_root)
    discovered = discover_project_overlay(nested_dir)

    assert result.project_overlay.project_root == project_root
    assert discovered is not None
    assert discovered.project_root == project_root
    assert (project_root / ".houmao" / ".gitignore").read_text(encoding="utf-8") == "*\n"
    assert not (project_root / ".houmao" / "agents" / "compatibility-profiles").exists()


def test_bootstrap_project_overlay_can_include_compatibility_profiles(tmp_path: Path) -> None:
    project_root = (tmp_path / "repo").resolve()
    project_root.mkdir(parents=True, exist_ok=True)

    bootstrap_project_overlay(project_root, include_compatibility_profiles=True)

    assert (project_root / ".houmao" / "agents" / "compatibility-profiles").is_dir()
