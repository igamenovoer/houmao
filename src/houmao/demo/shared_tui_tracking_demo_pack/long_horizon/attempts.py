"""Persist resumable numbered attempts for long-horizon matrix cells."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.models import (
    AttemptPhase,
    AttemptState,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.paths import (
    LongHorizonRunPaths,
    load_json_object,
    require_owned_descendant,
    save_json_atomic,
)


_ALLOWED_TRANSITIONS: dict[AttemptPhase, tuple[AttemptPhase, ...]] = {
    "planned": ("preflight_passed", "failed"),
    "preflight_passed": ("capturing", "failed"),
    "capturing": ("awaiting_manual_labels", "failed"),
    "awaiting_manual_labels": ("labels_complete", "failed"),
    "labels_complete": ("replaying", "failed"),
    "replaying": ("reported", "failed"),
    "reported": (),
    "failed": (),
}


def create_attempt(*, paths: LongHorizonRunPaths, cell_id: str) -> tuple[Path, AttemptState]:
    """Create the next immutable numbered attempt for one planned cell."""

    _require_planned_cell(paths=paths, cell_id=cell_id)
    cell_root = require_owned_descendant(
        paths=paths,
        target=paths.sessions_dir / cell_id.replace(":", "-"),
    )
    attempts_root = cell_root / "attempts"
    attempts_root.mkdir(parents=True, exist_ok=True)
    existing_numbers = tuple(
        int(item.name[1:])
        for item in attempts_root.iterdir()
        if item.is_dir() and item.name.startswith("a") and item.name[1:].isdigit()
    )
    attempt_number = max(existing_numbers, default=0) + 1
    attempt_root = paths.attempt_root(cell_id=cell_id, attempt_number=attempt_number)
    require_owned_descendant(paths=paths, target=attempt_root)
    attempt_root.mkdir(parents=True, exist_ok=False)
    for name in ("runtime", "recording", "labels", "engineering", "replay", "logs", "issues"):
        (attempt_root / name).mkdir()
    state = AttemptState(
        schema_version=1,
        cell_id=cell_id,
        attempt_id=f"a{attempt_number:03d}",
        phase="planned",
        input_digests={},
        selected_for_aggregate=False,
        failure_code=None,
    )
    save_json_atomic(attempt_root / "attempt-state.json", state.to_payload())
    return attempt_root, state


def load_attempt_state(*, attempt_root: Path) -> AttemptState:
    """Load one persisted attempt state."""

    payload = load_json_object(attempt_root / "attempt-state.json")
    return AttemptState(
        schema_version=int(payload["schema_version"]),
        cell_id=str(payload["cell_id"]),
        attempt_id=str(payload["attempt_id"]),
        phase=cast(AttemptPhase, str(payload["phase"])),
        input_digests={
            str(key): str(value)
            for key, value in _require_mapping(payload.get("input_digests")).items()
        },
        selected_for_aggregate=bool(payload["selected_for_aggregate"]),
        failure_code=(
            str(payload["failure_code"]) if payload.get("failure_code") is not None else None
        ),
    )


def transition_attempt(
    *,
    attempt_root: Path,
    expected_phase: AttemptPhase,
    new_phase: AttemptPhase,
    input_digests: dict[str, str] | None = None,
    failure_code: str | None = None,
) -> AttemptState:
    """Atomically advance one attempt through an allowed phase edge."""

    current = load_attempt_state(attempt_root=attempt_root)
    if current.phase != expected_phase:
        raise ValueError(
            f"Attempt phase differs: expected {expected_phase}, observed {current.phase}"
        )
    if new_phase not in _ALLOWED_TRANSITIONS[current.phase]:
        raise ValueError(f"Invalid attempt transition: {current.phase} -> {new_phase}")
    if new_phase == "failed" and not failure_code:
        raise ValueError("failed attempts require failure_code")
    merged_digests = dict(current.input_digests)
    if input_digests:
        for name, digest in input_digests.items():
            prior = merged_digests.get(name)
            if prior is not None and prior != digest:
                raise ValueError(f"Input artifact digest changed for {name}")
            merged_digests[name] = digest
    updated = AttemptState(
        schema_version=current.schema_version,
        cell_id=current.cell_id,
        attempt_id=current.attempt_id,
        phase=new_phase,
        input_digests=merged_digests,
        selected_for_aggregate=current.selected_for_aggregate,
        failure_code=failure_code,
    )
    save_json_atomic(attempt_root / "attempt-state.json", updated.to_payload())
    return updated


def select_attempt_for_aggregate(
    *,
    paths: LongHorizonRunPaths,
    cell_id: str,
    attempt_root: Path,
) -> AttemptState:
    """Select one reported attempt without deleting prior cell attempts."""

    require_owned_descendant(paths=paths, target=attempt_root)
    current = load_attempt_state(attempt_root=attempt_root)
    if current.cell_id != cell_id:
        raise ValueError("Attempt cell does not match aggregate selection")
    if current.phase != "reported":
        raise ValueError("Only reported attempts can be selected for aggregation")
    updated = AttemptState(
        schema_version=current.schema_version,
        cell_id=current.cell_id,
        attempt_id=current.attempt_id,
        phase=current.phase,
        input_digests=current.input_digests,
        selected_for_aggregate=True,
        failure_code=current.failure_code,
    )
    save_json_atomic(attempt_root / "attempt-state.json", updated.to_payload())
    cell_root = paths.sessions_dir / cell_id.replace(":", "-")
    save_json_atomic(
        cell_root / "cell-manifest.json",
        {
            "schema_version": 1,
            "cell_id": cell_id,
            "selected_attempt_id": updated.attempt_id,
            "selected_attempt_root": str(attempt_root.resolve()),
        },
    )
    return updated


def _require_planned_cell(*, paths: LongHorizonRunPaths, cell_id: str) -> None:
    """Require one cell id from the persisted suite plan."""

    manifest = load_json_object(paths.suite_manifest_path)
    cells = manifest.get("cells")
    if not isinstance(cells, list):
        raise ValueError("Suite manifest cells must be a list")
    known = {
        str(item.get("cell_id"))
        for item in cells
        if isinstance(item, dict) and item.get("cell_id") is not None
    }
    if cell_id not in known:
        raise ValueError(f"Cell is not part of the persisted suite plan: {cell_id}")


def _require_mapping(value: object) -> dict[str, Any]:
    """Return one validated mapping."""

    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return cast(dict[str, Any], value)
