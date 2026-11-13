from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from houmao.demo.shared_tui_tracking_demo_pack.agent_assets import (
    default_recipe_path,
    materialize_generated_agent_tree,
)


_WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
_DEMO_INPUTS_SOURCE = _WORKSPACE_ROOT / "scripts/demo/shared-tui-tracking-demo-pack/inputs/agents"


def _seed_demo_repo(repo_root: Path) -> None:
    destination = repo_root / "scripts/demo/shared-tui-tracking-demo-pack/inputs/agents"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(_DEMO_INPUTS_SOURCE, destination)


def _seed_prepared_run(repo_root: Path, *, tool: str) -> Path:
    """Create synthetic external inputs using the shared preparation contract."""

    root = repo_root.parent / f"prepared-{tool}"
    target = root / "assets/tools" / tool
    source = _WORKSPACE_ROOT / "tests/fixtures/plain-agent-def/tools" / tool
    target.mkdir(parents=True)
    shutil.copyfile(source / "adapter.yaml", target / "adapter.yaml")
    (target / "setups/fixture").mkdir(parents=True)
    (target / "auth/default/env").mkdir(parents=True)
    (target / "auth/default/files").mkdir()
    (target / "auth/default/env/vars.env").write_text("FIXTURE_SYNTHETIC_KEY=test-key\n")
    (root / "private-env.json").write_text("{}")
    (root / "run.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_dir": str(root.resolve()),
                "assets_root": str(root / "assets"),
                "configuration": {"client": tool},
            }
        )
    )
    return root


@pytest.mark.parametrize("tool", ["claude", "codex", "kimi"])
def test_materialize_generated_agent_tree_projects_default_auth_alias(
    tmp_path: Path,
    tool: str,
) -> None:
    repo_root = tmp_path / "repo"
    _seed_demo_repo(repo_root)
    prepared_run = _seed_prepared_run(repo_root, tool=tool)
    workdir = tmp_path / "workdir"

    generated_agent_def_dir = materialize_generated_agent_tree(
        repo_root=repo_root,
        workdir=workdir,
        prepared_run=prepared_run,
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
    assert auth_default.is_dir() and not auth_default.is_symlink()
    assert (auth_default / "env/vars.env").read_text() == "FIXTURE_SYNTHETIC_KEY=test-key\n"
    (auth_default / "env/vars.env").write_text("changed")
    assert (
        "test-key"
        in (prepared_run / "assets/tools" / tool / "auth/default/env/vars.env").read_text()
    )


@pytest.mark.parametrize("tool", ["claude", "codex", "kimi"])
def test_materialize_generated_agent_tree_requires_host_local_auth_bundle(
    tmp_path: Path,
    tool: str,
) -> None:
    repo_root = tmp_path / "repo"
    _seed_demo_repo(repo_root)

    with pytest.raises(RuntimeError, match="explicit --prepared-run"):
        materialize_generated_agent_tree(
            repo_root=repo_root,
            workdir=tmp_path / "workdir",
            tool=tool,  # type: ignore[arg-type]
        )


def test_codex_demo_adapter_projects_proxy_environment() -> None:
    adapter_path = _DEMO_INPUTS_SOURCE / "tools/codex/adapter.yaml"
    payload = yaml.safe_load(adapter_path.read_text(encoding="utf-8"))

    allowlist = set(payload["auth_projection"]["env"]["allowlist"])

    assert {
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    }.issubset(allowlist)


@pytest.mark.parametrize("tool", ["claude", "codex", "kimi"])
def test_prepared_inputs_reject_wrong_tool_and_allow_credential_free_offline_validation(
    tmp_path: Path,
    tool: str,
) -> None:
    """Tool selection is explicit while offline asset projection needs no auth state."""

    repo = tmp_path / "repo"
    _seed_demo_repo(repo)
    selected = _seed_prepared_run(repo, tool="codex" if tool != "codex" else "kimi")
    with pytest.raises(RuntimeError, match="another tool"):
        materialize_generated_agent_tree(
            repo_root=repo, workdir=tmp_path / "live", tool=tool, prepared_run=selected
        )
    generated = materialize_generated_agent_tree(
        repo_root=repo, workdir=tmp_path / "offline", tool=tool, allow_missing_auth=True
    )
    assert generated.is_dir()
    assert not (generated / "tools" / tool / "auth/default").exists()
