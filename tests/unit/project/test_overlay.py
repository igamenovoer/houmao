from __future__ import annotations

from pathlib import Path

import pytest

from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.project.overlay import (
    ProjectAwareLocalRoots,
    bootstrap_project_overlay,
    bootstrap_project_overlay_at_root,
    discover_project_overlay,
    PROJECT_OVERLAY_DIR_ENV_VAR,
    resolve_project_aware_local_roots,
    ensure_project_aware_local_roots,
    resolve_project_overlay,
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
    monkeypatch.delenv(PROJECT_OVERLAY_DIR_ENV_VAR, raising=False)
    project_root = (tmp_path / "repo").resolve()
    nested_dir = project_root / "a" / "b" / "c"
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(project_root)

    resolution = resolve_project_aware_agent_def_dir(cwd=nested_dir)

    assert resolution.source == "project_config"
    assert resolution.project_overlay is not None
    assert resolution.project_overlay.project_root == project_root
    assert resolution.agent_def_dir == (project_root / ".houmao" / "agents").resolve()


def test_resolve_project_aware_agent_def_dir_falls_back_to_houmao_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(AGENT_DEF_DIR_ENV_VAR, raising=False)
    monkeypatch.delenv(PROJECT_OVERLAY_DIR_ENV_VAR, raising=False)
    workdir = (tmp_path / "workspace").resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    resolution = resolve_project_aware_agent_def_dir(cwd=workdir)

    assert resolution.source == "default"
    assert resolution.agent_def_dir == (workdir / ".houmao" / "agents").resolve()


def test_resolve_project_aware_agent_def_dir_uses_overlay_env_before_ancestor_discovery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(AGENT_DEF_DIR_ENV_VAR, raising=False)
    repo_root = (tmp_path / "repo").resolve()
    nested_dir = repo_root / "nested"
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(repo_root)
    overlay_root = (tmp_path / "ci-overlay").resolve()
    bootstrap_project_overlay_at_root(overlay_root)
    monkeypatch.setenv(PROJECT_OVERLAY_DIR_ENV_VAR, str(overlay_root))

    resolution = resolve_project_aware_agent_def_dir(cwd=nested_dir)

    assert resolution.source == "project_config"
    assert resolution.project_overlay is not None
    assert resolution.project_overlay.overlay_root == overlay_root
    assert resolution.agent_def_dir == (overlay_root / "agents").resolve()


def test_resolve_project_aware_agent_def_dir_uses_overlay_env_agents_root_without_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(AGENT_DEF_DIR_ENV_VAR, raising=False)
    workdir = (tmp_path / "workspace").resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    overlay_root = (tmp_path / "ci-overlay").resolve()
    monkeypatch.setenv(PROJECT_OVERLAY_DIR_ENV_VAR, str(overlay_root))

    resolution = resolve_project_aware_agent_def_dir(cwd=workdir)

    assert resolution.source == "project_overlay_env"
    assert resolution.project_overlay is None
    assert resolution.agent_def_dir == (overlay_root / "agents").resolve()


def test_resolve_project_overlay_env_override_blocks_ancestor_discovery_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    nested_dir = repo_root / "nested"
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(repo_root)
    overlay_root = (tmp_path / "ci-overlay").resolve()
    monkeypatch.setenv(PROJECT_OVERLAY_DIR_ENV_VAR, str(overlay_root))

    resolution = resolve_project_overlay(cwd=nested_dir)

    assert resolution.source == "env"
    assert resolution.overlay_root == overlay_root
    assert resolution.project_overlay is None


def test_resolve_project_aware_agent_def_dir_rejects_relative_overlay_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(AGENT_DEF_DIR_ENV_VAR, raising=False)
    workdir = (tmp_path / "workspace").resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(PROJECT_OVERLAY_DIR_ENV_VAR, "relative/overlay")

    with pytest.raises(ValueError, match="HOUMAO_PROJECT_OVERLAY_DIR"):
        resolve_project_aware_agent_def_dir(cwd=workdir)


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
    assert not (project_root / ".houmao" / "agents").exists()
    assert not (project_root / ".houmao" / "agents" / "compatibility-profiles").exists()


def test_bootstrap_project_overlay_can_include_compatibility_profiles_for_custom_root(
    tmp_path: Path,
) -> None:
    project_root = (tmp_path / "repo").resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    overlay_root = project_root / ".houmao"
    overlay_root.mkdir(parents=True, exist_ok=True)
    (overlay_root / "houmao-config.toml").write_text(
        'schema_version = 1\n\n[paths]\nagent_def_dir = "custom-agents"\n',
        encoding="utf-8",
    )

    bootstrap_project_overlay(project_root, include_compatibility_profiles=True)

    assert (project_root / ".houmao" / "custom-agents" / "compatibility-profiles").is_dir()
    assert (project_root / ".houmao" / "custom-agents" / "tools").is_dir()
    assert not (project_root / ".houmao" / "agents").exists()


def test_resolve_project_overlay_does_not_cross_nearest_git_boundary(tmp_path: Path) -> None:
    parent_root = (tmp_path / "parent").resolve()
    nested_repo_root = (parent_root / "nested-repo").resolve()
    nested_dir = (nested_repo_root / "app").resolve()
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(parent_root)
    (nested_repo_root / ".git").write_text("gitdir: /tmp/fake-worktree\n", encoding="utf-8")

    resolution = resolve_project_overlay(cwd=nested_dir)

    assert resolution.project_overlay is None
    assert resolution.source == "default"
    assert resolution.overlay_root == (nested_dir / ".houmao").resolve()


def test_resolve_project_aware_local_roots_reports_overlay_local_defaults(tmp_path: Path) -> None:
    repo_root = (tmp_path / "repo").resolve()
    nested_dir = (repo_root / "nested" / "child").resolve()
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(repo_root)

    roots = resolve_project_aware_local_roots(cwd=nested_dir)

    assert isinstance(roots, ProjectAwareLocalRoots)
    assert roots.overlay_root == (repo_root / ".houmao").resolve()
    assert roots.runtime_root == (repo_root / ".houmao" / "runtime").resolve()
    assert roots.jobs_root == (repo_root / ".houmao" / "jobs").resolve()
    assert roots.mailbox_root == (repo_root / ".houmao" / "mailbox").resolve()
    assert roots.easy_root == (repo_root / ".houmao" / "easy").resolve()
    assert roots.created_overlay is False


def test_ensure_project_aware_local_roots_bootstraps_missing_overlay(tmp_path: Path) -> None:
    workdir = (tmp_path / "workspace").resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    roots = ensure_project_aware_local_roots(cwd=workdir)

    assert roots.project_overlay is not None
    assert roots.created_overlay is True
    assert roots.overlay_root == (workdir / ".houmao").resolve()
    assert (workdir / ".houmao" / "houmao-config.toml").is_file()
    assert roots.runtime_root == (workdir / ".houmao" / "runtime").resolve()
