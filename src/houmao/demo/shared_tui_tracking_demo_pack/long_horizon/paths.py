"""Owned filesystem layout for long-horizon qualification runs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


OWNERSHIP_FILE_NAME = "ownership.json"
OWNERSHIP_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class LongHorizonRunPaths:
    """Canonical paths contained by one repository-local temporary run root."""

    repo_root: Path
    run_root: Path
    ownership_path: Path
    suite_manifest_path: Path
    phase_state_path: Path
    catalog_snapshot_dir: Path
    preflight_dir: Path
    projects_dir: Path
    provider_homes_dir: Path
    sessions_dir: Path
    aggregate_dir: Path

    @classmethod
    def from_requested_root(
        cls,
        *,
        repo_root: Path,
        requested_root: Path,
    ) -> "LongHorizonRunPaths":
        """Resolve and validate one caller-selected `tmp/<subdir>` root."""

        resolved_repo = repo_root.resolve()
        tmp_root = (resolved_repo / "tmp").resolve()
        candidate = requested_root
        if not candidate.is_absolute():
            candidate = resolved_repo / candidate
        resolved_run = candidate.resolve()
        if resolved_run == tmp_root or not resolved_run.is_relative_to(tmp_root):
            raise ValueError(
                "Long-horizon run root must be a proper descendant of the repository tmp/ "
                f"directory: {resolved_run}"
            )
        return cls(
            repo_root=resolved_repo,
            run_root=resolved_run,
            ownership_path=resolved_run / OWNERSHIP_FILE_NAME,
            suite_manifest_path=resolved_run / "suite-manifest.json",
            phase_state_path=resolved_run / "phase-state.json",
            catalog_snapshot_dir=resolved_run / "catalog-snapshot",
            preflight_dir=resolved_run / "preflight",
            projects_dir=resolved_run / "projects",
            provider_homes_dir=resolved_run / "provider-homes",
            sessions_dir=resolved_run / "sessions",
            aggregate_dir=resolved_run / "aggregate",
        )

    def attempt_root(self, *, cell_id: str, attempt_number: int) -> Path:
        """Return the evidence root for one numbered cell attempt."""

        safe_cell_id = cell_id.replace(":", "-")
        return self.sessions_dir / safe_cell_id / "attempts" / f"a{attempt_number:03d}"

    def project_root(self, *, cell_id: str, attempt_number: int) -> Path:
        """Return the copied Boltons root for one numbered cell attempt."""

        safe_cell_id = cell_id.replace(":", "-")
        return self.projects_dir / f"{safe_cell_id}-a{attempt_number:03d}" / "boltons"

    def provider_home_root(self, *, cell_id: str, attempt_number: int) -> Path:
        """Return the temporary provider-home root for one numbered attempt."""

        safe_cell_id = cell_id.replace(":", "-")
        return self.provider_homes_dir / f"{safe_cell_id}-a{attempt_number:03d}"


def initialize_owned_run_root(*, paths: LongHorizonRunPaths, suite_id: str) -> None:
    """Create or validate one restrictive owned run root and its base layout."""

    if paths.run_root.exists():
        entries = tuple(paths.run_root.iterdir())
        if entries and not paths.ownership_path.is_file():
            raise ValueError(f"Refusing to reuse non-empty unowned run root: {paths.run_root}")
        if paths.ownership_path.is_file():
            ownership = load_json_object(paths.ownership_path)
            if ownership.get("suite_id") != suite_id:
                raise ValueError(f"Run root belongs to another suite: {paths.run_root}")
            if Path(str(ownership.get("run_root", ""))).resolve() != paths.run_root:
                raise ValueError(f"Run-root ownership path does not match: {paths.run_root}")
    else:
        paths.run_root.mkdir(parents=True, mode=0o700)
    os.chmod(paths.run_root, 0o700)
    for directory in (
        paths.catalog_snapshot_dir,
        paths.preflight_dir,
        paths.projects_dir,
        paths.provider_homes_dir,
        paths.sessions_dir,
        paths.aggregate_dir,
    ):
        _require_descendant(path=directory, parent=paths.run_root)
        directory.mkdir(parents=True, exist_ok=True)
    if not paths.ownership_path.exists():
        save_json_atomic(
            paths.ownership_path,
            {
                "schema_version": OWNERSHIP_SCHEMA_VERSION,
                "suite_id": suite_id,
                "run_root": str(paths.run_root),
            },
        )


def save_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Persist one JSON document through atomic replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_json_object(path: Path) -> dict[str, Any]:
    """Load one JSON object from disk."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"Expected a JSON object: {path}")
    return cast(dict[str, Any], value)


def require_owned_descendant(*, paths: LongHorizonRunPaths, target: Path) -> Path:
    """Resolve one output target and require current run ownership."""

    if not paths.ownership_path.is_file():
        raise ValueError(f"Run root has no ownership metadata: {paths.run_root}")
    resolved = target.resolve()
    _require_descendant(path=resolved, parent=paths.run_root)
    return resolved


def _require_descendant(*, path: Path, parent: Path) -> None:
    """Require a proper resolved descendant relationship."""

    resolved_path = path.resolve()
    resolved_parent = parent.resolve()
    if resolved_path == resolved_parent or not resolved_path.is_relative_to(resolved_parent):
        raise ValueError(f"Path escapes owned run root: {resolved_path}")
