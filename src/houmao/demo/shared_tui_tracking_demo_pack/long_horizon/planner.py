"""Create and resume long-horizon qualification run plans."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, cast

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.catalog import (
    default_catalog_path,
    expand_matrix,
    load_suite_catalog,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.models import SuitePlan
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.paths import (
    LongHorizonRunPaths,
    initialize_owned_run_root,
    load_json_object,
    save_json_atomic,
)


def create_or_resume_plan(
    *,
    repo_root: Path,
    requested_run_root: Path,
    selected_cells: tuple[str, ...] = (),
) -> tuple[LongHorizonRunPaths, SuitePlan]:
    """Create or idempotently resume one reviewed suite plan."""

    suite = load_suite_catalog(repo_root=repo_root)
    plan = expand_matrix(suite=suite, selected_cells=selected_cells)
    paths = LongHorizonRunPaths.from_requested_root(
        repo_root=repo_root,
        requested_root=requested_run_root,
    )
    initialize_owned_run_root(paths=paths, suite_id=suite.suite_id)
    manifest_payload = _json_compatible(_plan_manifest_payload(plan=plan))
    if paths.suite_manifest_path.is_file():
        existing = load_json_object(paths.suite_manifest_path)
        if existing != manifest_payload:
            raise ValueError(
                "Existing run plan differs from the requested catalog or cell selection: "
                f"{paths.suite_manifest_path}"
            )
    else:
        save_json_atomic(paths.suite_manifest_path, manifest_payload)
        save_json_atomic(
            paths.phase_state_path,
            {
                "schema_version": 1,
                "phase": "planned",
                "suite_manifest_sha256": _sha256_json_file(paths.suite_manifest_path),
            },
        )
        source_catalog = default_catalog_path(repo_root=repo_root)
        shutil.copy2(source_catalog, paths.catalog_snapshot_dir / source_catalog.name)
        source_document = (repo_root / suite.source_path).resolve()
        shutil.copy2(source_document, paths.catalog_snapshot_dir / source_document.name)
    return paths, plan


def _plan_manifest_payload(*, plan: SuitePlan) -> dict[str, Any]:
    """Return the stable persisted subset of one suite plan."""

    return {
        "schema_version": 1,
        "suite_id": plan.suite_id,
        "source_sha256": plan.source_sha256,
        "complete_matrix": plan.complete_matrix,
        "cell_count": len(plan.cells),
        "total_operations": plan.total_operations,
        "cells": [item.to_payload() for item in plan.cells],
    }


def _sha256_json_file(path: Path) -> str:
    """Return the SHA-256 digest of one persisted JSON file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_compatible(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize tuples and nested dataclasses through JSON semantics."""

    return cast(dict[str, Any], json.loads(json.dumps(payload)))
