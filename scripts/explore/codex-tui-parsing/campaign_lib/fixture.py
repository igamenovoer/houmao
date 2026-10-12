"""Prepare an isolated Boltons working copy for one campaign session.

Mirrors the semantics of
``houmao.demo.shared_tui_tracking_demo_pack.long_horizon.projects.prepare_boltons_project``
(copy with generated-path pruning, upstream revision check, git baseline tag,
pytest collection preflight) without the demo pack's run-path machinery.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
BOLTONS_FIXTURE = REPO_ROOT / "tests/fixtures/test-projects/boltons"

_CACHE_DIRECTORY_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git"}
_REVISION_PATTERN = re.compile(r"Imported revision:\s*`([0-9a-f]{40})`")
_COLLECTION_PATTERN = re.compile(r"(\d+) tests? collected")
BASELINE_TAG = "houmao-baseline"


def prepare_boltons_copy(*, workdir: Path, expected_collection: int = 437) -> dict[str, Any]:
    """Copy the vendored Boltons fixture into ``workdir`` and baseline it.

    Parameters
    ----------
    workdir:
        Fresh destination directory; must not already exist.
    expected_collection:
        Expected pytest collection count for the vendored suite.

    Returns
    -------
    dict
        Fixture manifest with digests, revision, baseline commit, and
        collection count, suitable for ``capture/fixture_manifest.json``.
    """

    if not BOLTONS_FIXTURE.is_dir():
        raise FileNotFoundError(f"Boltons fixture missing at `{BOLTONS_FIXTURE}`")
    if workdir.exists():
        raise FileExistsError(f"Workdir already exists: `{workdir}`")
    workdir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(BOLTONS_FIXTURE, workdir, ignore=_ignore_generated)

    readme = workdir / "README.md"
    revision = ""
    if readme.is_file():
        match = _REVISION_PATTERN.search(readme.read_text(encoding="utf-8"))
        revision = match.group(1) if match else ""

    _run_git(workdir, ["init", "-q"])
    _run_git(workdir, ["add", "-A"])
    _run_git(
        workdir,
        [
            "-c",
            "user.name=houmao-campaign",
            "-c",
            "user.email=houmao-campaign@localhost",
            "commit",
            "-q",
            "-m",
            "baseline",
        ],
    )
    _run_git(workdir, ["tag", BASELINE_TAG])
    baseline_commit = _run_git(workdir, ["rev-parse", "HEAD"]).stdout.strip()

    collection = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=300,
    )
    collected = 0
    for line in collection.stdout.splitlines():
        match = _COLLECTION_PATTERN.search(line)
        if match:
            collected = int(match.group(1))
    if collected != expected_collection:
        raise RuntimeError(
            f"Boltons collection preflight collected {collected}, expected {expected_collection}: "
            f"{collection.stdout[-500:]}"
        )

    return {
        "source_path": str(BOLTONS_FIXTURE),
        "copied_project_path": str(workdir),
        "source_sha256": _tree_digest(BOLTONS_FIXTURE),
        "copied_sha256": _tree_digest(workdir, exclude={".git"}),
        "upstream_revision": revision,
        "baseline_commit": baseline_commit,
        "baseline_tag": BASELINE_TAG,
        "python_executable": sys.executable,
        "collection_count": collected,
        "initial_status": _run_git(workdir, ["status", "--short"]).stdout.strip(),
    }


def _ignore_generated(_directory: str, names: list[str]) -> set[str]:
    """Prune generated caches and VCS metadata from the fixture copy."""

    return {name for name in names if name in _CACHE_DIRECTORY_NAMES}


def _run_git(workdir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run one git command inside the copied project."""

    result = subprocess.run(
        ["git", *args], cwd=workdir, capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {workdir}: {result.stderr.strip()}")
    return result


def _tree_digest(root: Path, *, exclude: set[str] | None = None) -> str:
    """Return one deterministic SHA-256 over file paths and contents."""

    excluded = exclude or set()
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name for name in dirnames if name not in excluded and name not in _CACHE_DIRECTORY_NAMES
        )
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            relative = path.relative_to(root)
            digest.update(str(relative).encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()
