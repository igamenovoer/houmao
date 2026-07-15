"""Prepare immutable-source Boltons projects for qualification attempts."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.models import (
    FixtureContract,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.paths import (
    LongHorizonRunPaths,
    require_owned_descendant,
    save_json_atomic,
)


_CACHE_DIRECTORY_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
_REVISION_PATTERN = re.compile(r"Imported revision:\s*`([0-9a-f]{40})`")
_COLLECTION_PATTERN = re.compile(r"(\d+) tests collected")


@dataclass(frozen=True)
class PreparedProject:
    """Manifest for one copied and baselined Boltons project."""

    schema_version: int
    cell_id: str
    attempt_id: str
    source_path: str
    source_sha256: str
    copied_project_path: str
    copied_sha256: str
    upstream_revision: str
    baseline_commit: str
    python_executable: str
    collection_count: int
    initial_status: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible project manifest."""

        return asdict(self)


def prepare_boltons_project(
    *,
    repo_root: Path,
    paths: LongHorizonRunPaths,
    fixture: FixtureContract,
    cell_id: str,
    attempt_number: int,
    python_executable: Path | None = None,
) -> PreparedProject:
    """Copy, baseline, and collection-check Boltons for one attempt."""

    source_path = (repo_root / fixture.path).resolve()
    if not source_path.is_dir():
        raise ValueError(f"Boltons fixture is missing: {source_path}")
    _validate_imported_revision(
        readme_path=source_path / "README.md",
        expected_revision=fixture.upstream_revision,
    )
    source_digest = tree_sha256(source_path)
    destination = paths.project_root(cell_id=cell_id, attempt_number=attempt_number)
    require_owned_descendant(paths=paths, target=destination)
    if destination.exists():
        raise ValueError(f"Attempt project already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_path, destination, ignore=_ignore_generated_paths)
    copied_digest = tree_sha256(destination)
    if copied_digest != source_digest:
        raise RuntimeError(
            "Copied Boltons tree differs from the immutable fixture: "
            f"source={source_digest}, copy={copied_digest}"
        )
    baseline_commit = _initialize_git_baseline(project_root=destination)
    initial_status = _run_git(project_root=destination, args=["status", "--short"]).stdout
    if initial_status:
        raise RuntimeError(f"Boltons baseline is not clean: {initial_status}")
    executable = (python_executable or Path(sys.executable)).resolve()
    collection_count = run_collection_preflight(
        project_root=destination,
        python_executable=executable,
        expected_count=fixture.expected_collection_count,
    )
    manifest = PreparedProject(
        schema_version=1,
        cell_id=cell_id,
        attempt_id=f"a{attempt_number:03d}",
        source_path=str(source_path),
        source_sha256=source_digest,
        copied_project_path=str(destination),
        copied_sha256=copied_digest,
        upstream_revision=fixture.upstream_revision,
        baseline_commit=baseline_commit,
        python_executable=str(executable),
        collection_count=collection_count,
        initial_status=initial_status,
    )
    attempt_root = paths.attempt_root(cell_id=cell_id, attempt_number=attempt_number)
    save_json_atomic(attempt_root / "engineering" / "project-manifest.json", manifest.to_payload())
    return manifest


def run_collection_preflight(
    *,
    project_root: Path,
    python_executable: Path,
    expected_count: int,
) -> int:
    """Run the pinned no-install pytest collection gate."""

    environment = dict(os.environ)
    for name in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        environment.pop(name, None)
    environment.update(
        {
            "PIP_NO_INDEX": "1",
            "UV_NO_INDEX": "1",
            "NO_PROXY": "*",
            "no_proxy": "*",
        }
    )
    completed = subprocess.run(
        [str(python_executable), "-m", "pytest", "--collect-only", "-q"],
        cwd=project_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    combined = f"{completed.stdout}\n{completed.stderr}"
    match = _COLLECTION_PATTERN.search(combined)
    observed_count = int(match.group(1)) if match is not None else -1
    if completed.returncode != 0 or observed_count != expected_count:
        raise RuntimeError(
            "Boltons collection preflight failed: "
            f"exit={completed.returncode}, expected={expected_count}, "
            f"observed={observed_count}\n{combined}"
        )
    return observed_count


def tree_sha256(root: Path) -> str:
    """Return a deterministic cache-excluding tree digest."""

    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if _is_generated_path(relative) or ".git" in relative.parts:
            continue
        encoded_path = relative.as_posix().encode("utf-8")
        digest.update(len(encoded_path).to_bytes(8, "big"))
        digest.update(encoded_path)
        if path.is_symlink():
            digest.update(b"L")
            digest.update(os.readlink(path).encode("utf-8"))
        elif path.is_dir():
            digest.update(b"D")
        elif path.is_file():
            digest.update(b"F")
            digest.update(stat.S_IMODE(path.stat().st_mode).to_bytes(4, "big"))
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
    return digest.hexdigest()


def recording_evidence_sha256(recording_root: Path) -> str:
    """Hash immutable finalized recorder evidence and exclude controller state/logs."""

    digest = hashlib.sha256()
    for name in (
        "manifest.json",
        "pane_snapshots.ndjson",
        "input_events.ndjson",
    ):
        path = recording_root / name
        if not path.is_file():
            raise ValueError(f"Finalized recording evidence is missing: {path}")
        encoded_name = name.encode("utf-8")
        digest.update(len(encoded_name).to_bytes(8, "big"))
        digest.update(encoded_name)
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def _validate_imported_revision(*, readme_path: Path, expected_revision: str) -> None:
    """Require the pinned imported revision from the fixture README."""

    match = _REVISION_PATTERN.search(readme_path.read_text(encoding="utf-8"))
    observed = match.group(1) if match is not None else None
    if observed != expected_revision:
        raise ValueError(
            "Boltons fixture imported revision differs: "
            f"expected {expected_revision}, observed {observed}"
        )


def _initialize_git_baseline(*, project_root: Path) -> str:
    """Create the fresh `houmao-baseline` Git commit."""

    _run_git(project_root=project_root, args=["init", "--quiet"])
    _run_git(project_root=project_root, args=["config", "user.name", "Houmao Test Harness"])
    _run_git(
        project_root=project_root,
        args=["config", "user.email", "houmao-test@example.invalid"],
    )
    _run_git(project_root=project_root, args=["add", "--all"])
    _run_git(
        project_root=project_root,
        args=["commit", "--quiet", "-m", "houmao-baseline"],
    )
    commit = _run_git(project_root=project_root, args=["rev-parse", "HEAD"]).stdout.strip()
    _run_git(project_root=project_root, args=["tag", "houmao-baseline", commit])
    return commit


def _run_git(*, project_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run one checked Git command in the copied project."""

    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )


def _ignore_generated_paths(_directory: str, names: list[str]) -> set[str]:
    """Return generated names excluded from a fresh fixture copy."""

    return {
        name
        for name in names
        if name in _CACHE_DIRECTORY_NAMES or name == ".git" or name.endswith(".pyc")
    }


def _is_generated_path(path: Path) -> bool:
    """Return whether a relative path belongs to generated caches."""

    return any(part in _CACHE_DIRECTORY_NAMES for part in path.parts) or path.name.endswith(".pyc")
