"""Integration smoke coverage for standard Skills CLI installation."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
PUBLIC_SOURCE = REPO_ROOT / "src/houmao/agents/assets/system_skills/public"
PUBLIC_NAMES = {
    "houmao-admin-welcome",
    "houmao-admin-entrypoint",
    "houmao-agent-entrypoint",
    "houmao-shared-routines",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
}
AGENT_MEMBERS = {
    "houmao-agent-entrypoint",
    "houmao-shared-routines",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
}


def _run_skills_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the standard Skills CLI against the local static source."""

    if shutil.which("npx") is None:
        pytest.skip("npx is unavailable")
    return subprocess.run(
        ["npx", "--yes", "skills", "add", str(PUBLIC_SOURCE), *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_local_public_collection_lists_and_installs_explicit_agent_members(tmp_path: Path) -> None:
    """Skills CLI discovers six roots and copies the selected complete agent surface."""

    listing = _run_skills_cli("--list", cwd=tmp_path)
    assert listing.returncode == 0, listing.stderr
    assert "Found 6 skills" in listing.stdout
    for name in PUBLIC_NAMES:
        assert name in listing.stdout

    install = _run_skills_cli(
        "--agent",
        "codex",
        *(argument for name in sorted(AGENT_MEMBERS) for argument in ("--skill", name)),
        "--yes",
        cwd=tmp_path,
    )
    assert install.returncode == 0, install.stderr

    installed_root = tmp_path / ".agents/skills"
    assert {
        path.parent.name for path in installed_root.glob("*/SKILL.md") if path.is_file()
    } == AGENT_MEMBERS
    shared_children = installed_root.glob("houmao-shared-routines/subskills/*/SKILL-MAIN.md")
    assert len([path for path in shared_children if path.is_file()]) == 16
