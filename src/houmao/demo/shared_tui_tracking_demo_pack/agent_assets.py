"""Demo-local agent asset helpers for the shared tracked-TUI demo pack."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from houmao.demo.fixture_inputs import private_demo_root, read_prepared_run

from .models import ToolName


_TRACKED_AGENT_INPUTS_RELATIVE = Path("scripts/demo/shared-tui-tracking-demo-pack/inputs/agents")
_GENERATED_AGENT_DEF_RELATIVE = Path(".houmao/agents")


def tracked_agent_inputs_dir(*, repo_root: Path) -> Path:
    """Return the tracked demo-local agent asset root."""

    return (repo_root / _TRACKED_AGENT_INPUTS_RELATIVE).resolve()


def default_recipe_path(*, repo_root: Path, tool: ToolName) -> Path:
    """Return the default demo-local recipe path for one tool."""

    return (
        tracked_agent_inputs_dir(repo_root=repo_root)
        / "presets"
        / f"interactive-watch-{tool}-default.yaml"
    ).resolve()


def materialize_generated_agent_tree(
    *,
    repo_root: Path,
    workdir: Path,
    tool: ToolName,
    allow_missing_auth: bool = False,
    prepared_run: Path | None = None,
) -> Path:
    """Create the run-local generated agent-definition tree for one demo run."""

    selected = None
    if prepared_run is not None:
        selected = read_prepared_run(prepared_run=prepared_run, repo_root=repo_root, tool=tool)
        private_demo_root(path=workdir, repo_root=repo_root)
    elif not allow_missing_auth:
        raise RuntimeError(
            "Live launch requires explicit --prepared-run; use the test-fixture helper"
        )
    tracked_inputs_dir = tracked_agent_inputs_dir(repo_root=repo_root)
    if not tracked_inputs_dir.is_dir():
        raise RuntimeError(f"Tracked demo agent-definition tree is missing: {tracked_inputs_dir}")

    generated_agent_def_dir = (workdir / _GENERATED_AGENT_DEF_RELATIVE).resolve()
    if generated_agent_def_dir.exists():
        shutil.rmtree(generated_agent_def_dir)
    generated_agent_def_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(tracked_inputs_dir, generated_agent_def_dir, symlinks=True)

    if selected is not None:
        source_tool = Path(str(selected["assets_root"])) / "tools" / tool
        if not source_tool.resolve().is_relative_to(Path(str(selected["assets_root"])).resolve()):
            raise RuntimeError("Prepared tool inputs escape their private assets")
        target_tool = generated_agent_def_dir / "tools" / tool
        for source, destination in (
            (source_tool / "adapter.yaml", target_tool / "adapter.yaml"),
            (source_tool / "setups/fixture", target_tool / "setups/default"),
            (source_tool / "auth/default", target_tool / "auth/default"),
        ):
            if source.is_symlink() or any(p.is_symlink() for p in source.rglob("*")):
                raise RuntimeError("Prepared inputs contain symlinked state")
            if destination.is_dir():
                shutil.rmtree(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copyfile(source, destination)
        for path in (workdir, *generated_agent_def_dir.rglob("*")):
            if not path.is_symlink():
                os.chmod(path, 0o700 if path.is_dir() else 0o600)
    return generated_agent_def_dir
