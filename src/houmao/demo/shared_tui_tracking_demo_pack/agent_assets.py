"""Demo-local agent asset helpers for the shared tracked-TUI demo pack."""

from __future__ import annotations

import shutil
from pathlib import Path

from .models import ToolName


_TRACKED_AGENT_INPUTS_RELATIVE = Path("scripts/demo/shared-tui-tracking-demo-pack/inputs/agents")
_GENERATED_AGENT_DEF_RELATIVE = Path(".agentsys/agents")
_FIXTURE_AUTH_SOURCE_BY_TOOL: dict[ToolName, Path] = {
    "claude": Path("tests/fixtures/agents/tools/claude/auth/kimi-coding"),
    "codex": Path("tests/fixtures/agents/tools/codex/auth/yunwu-openai"),
}


def tracked_agent_inputs_dir(*, repo_root: Path) -> Path:
    """Return the tracked demo-local agent asset root."""

    return (repo_root / _TRACKED_AGENT_INPUTS_RELATIVE).resolve()


def default_recipe_path(*, repo_root: Path, tool: ToolName) -> Path:
    """Return the default demo-local recipe path for one tool."""

    return (
        tracked_agent_inputs_dir(repo_root=repo_root)
        / "roles"
        / "interactive-watch"
        / "presets"
        / tool
        / "default.yaml"
    ).resolve()


def materialize_generated_agent_tree(*, repo_root: Path, workdir: Path, tool: ToolName) -> Path:
    """Create the run-local generated agent-definition tree for one demo run."""

    tracked_inputs_dir = tracked_agent_inputs_dir(repo_root=repo_root)
    if not tracked_inputs_dir.is_dir():
        raise RuntimeError(f"Tracked demo agent-definition tree is missing: {tracked_inputs_dir}")

    generated_agent_def_dir = (workdir / _GENERATED_AGENT_DEF_RELATIVE).resolve()
    if generated_agent_def_dir.exists():
        shutil.rmtree(generated_agent_def_dir)
    generated_agent_def_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(tracked_inputs_dir, generated_agent_def_dir, symlinks=True)

    fixture_auth_source = (repo_root / _FIXTURE_AUTH_SOURCE_BY_TOOL[tool]).resolve()
    if not fixture_auth_source.is_dir():
        raise RuntimeError(
            "Fixture auth bundle missing for "
            f"`{tool}`: expected {fixture_auth_source}. "
            "Restore the local fixture auth bundle before running this demo."
        )

    auth_dir = generated_agent_def_dir / "tools" / tool / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    default_auth_path = auth_dir / "default"
    if default_auth_path.exists() or default_auth_path.is_symlink():
        if default_auth_path.is_dir() and not default_auth_path.is_symlink():
            shutil.rmtree(default_auth_path)
        else:
            default_auth_path.unlink()
    default_auth_path.symlink_to(fixture_auth_source)
    return generated_agent_def_dir
