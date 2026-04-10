from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from houmao.demo.shared_tui_tracking_demo_pack.agent_assets import (
    default_recipe_path,
    materialize_generated_agent_tree,
)


_WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
_DEMO_INPUTS_SOURCE = _WORKSPACE_ROOT / "scripts/demo/shared-tui-tracking-demo-pack/inputs/agents"
_FIXTURE_AUTH_RELATIVE_BY_TOOL = {
    "claude": Path("tests/fixtures/auth-bundles/claude/kimi-coding"),
    "codex": Path("tests/fixtures/auth-bundles/codex/yunwu-openai"),
}


def _seed_demo_repo(repo_root: Path) -> None:
    destination = repo_root / "scripts/demo/shared-tui-tracking-demo-pack/inputs/agents"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(_DEMO_INPUTS_SOURCE, destination)


def _seed_fixture_auth_bundle(repo_root: Path, *, tool: str) -> Path:
    fixture_root = repo_root / _FIXTURE_AUTH_RELATIVE_BY_TOOL[tool]
    env_dir = fixture_root / "env"
    env_dir.mkdir(parents=True, exist_ok=True)
    env_path = env_dir / "vars.env"
    if tool == "claude":
        env_path.write_text("ANTHROPIC_API_KEY=test-key\n", encoding="utf-8")
    else:
        env_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")
    return fixture_root


@pytest.mark.parametrize("tool", ["claude", "codex"])
def test_materialize_generated_agent_tree_projects_default_auth_alias(
    tmp_path: Path,
    tool: str,
) -> None:
    repo_root = tmp_path / "repo"
    _seed_demo_repo(repo_root)
    fixture_auth_root = _seed_fixture_auth_bundle(repo_root, tool=tool)
    workdir = tmp_path / "workdir"

    generated_agent_def_dir = materialize_generated_agent_tree(
        repo_root=repo_root,
        workdir=workdir,
        tool=tool,  # type: ignore[arg-type]
    )

    assert generated_agent_def_dir == (workdir / ".houmao/agents").resolve()
    assert default_recipe_path(repo_root=repo_root, tool=tool) == (
        repo_root
        / "scripts/demo/shared-tui-tracking-demo-pack/inputs/agents/presets"
        / f"interactive-watch-{tool}-default.yaml"
    )
    assert (
        generated_agent_def_dir / "presets" / f"interactive-watch-{tool}-default.yaml"
    ).is_file()
    auth_default = generated_agent_def_dir / "tools" / tool / "auth" / "default"
    assert auth_default.is_symlink()
    assert auth_default.resolve() == fixture_auth_root.resolve()


@pytest.mark.parametrize("tool", ["claude", "codex"])
def test_materialize_generated_agent_tree_requires_host_local_auth_bundle(
    tmp_path: Path,
    tool: str,
) -> None:
    repo_root = tmp_path / "repo"
    _seed_demo_repo(repo_root)

    with pytest.raises(RuntimeError, match="Fixture auth bundle missing"):
        materialize_generated_agent_tree(
            repo_root=repo_root,
            workdir=tmp_path / "workdir",
            tool=tool,  # type: ignore[arg-type]
        )
