"""Command-facing orchestration for long-horizon TUI qualification."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, cast

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.attempts import (
    create_attempt,
    load_attempt_state,
    transition_attempt,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.capture import capture_attempt
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.catalog import load_suite_catalog
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.labeling import (
    complete_manual_labels,
    prepare_blind_review,
    validate_label_completion,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.models import (
    PlannedCell,
    ProviderName,
    SuitePlan,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.paths import (
    LongHorizonRunPaths,
    load_json_object,
    save_json_atomic,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.planner import (
    create_or_resume_plan,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.preflight import (
    PreparedProviderHome,
    prepare_provider_home,
    remove_sensitive_provider_home,
    run_disposable_probe,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.projects import (
    PreparedProject,
    prepare_boltons_project,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.replay import replay_attempt
from houmao.demo.shared_tui_tracking_demo_pack.tooling import kill_tmux_session_if_exists


def plan_suite(*, repo_root: Path, run_root: Path) -> dict[str, Any]:
    """Create or resume the complete reviewed matrix."""

    paths, plan = create_or_resume_plan(
        repo_root=repo_root,
        requested_run_root=run_root,
    )
    return {
        "run_root": str(paths.run_root),
        "cell_count": len(plan.cells),
        "total_operations": plan.total_operations,
        "cells": [cell.to_payload() for cell in plan.cells],
    }


def preflight_cells(
    *, repo_root: Path, run_root: Path, selected_cells: tuple[str, ...]
) -> dict[str, Any]:
    """Prepare fresh projects and provider homes, then run raw native probes."""

    paths, plan = _load_full_plan(repo_root=repo_root, run_root=run_root)
    cells = _select_cells(plan=plan, selected_cells=selected_cells)
    suite = load_suite_catalog(repo_root=repo_root)
    results: list[dict[str, Any]] = []
    for cell in cells:
        attempt_root, state = create_attempt(paths=paths, cell_id=cell.cell_id)
        attempt_number = int(state.attempt_id[1:])
        prepared_home: PreparedProviderHome | None = None
        try:
            project = prepare_boltons_project(
                repo_root=repo_root,
                paths=paths,
                fixture=suite.fixture,
                cell_id=cell.cell_id,
                attempt_number=attempt_number,
            )
            prepared_home = prepare_provider_home(
                repo_root=repo_root,
                paths=paths,
                provider=cell.provider,
                cell_id=cell.cell_id,
                attempt_number=attempt_number,
            )
            probe = run_disposable_probe(
                paths=paths,
                prepared=prepared_home,
                project_root=Path(project.copied_project_path),
                require_steering=cell.procedure_id == "st-02",
                require_model_selector=cell.procedure_id == "st-04",
                require_empty_editor_exit=cell.procedure_id == "st-05",
            )
            if probe.status != "pass":
                transition_attempt(
                    attempt_root=attempt_root,
                    expected_phase="planned",
                    new_phase="failed",
                    failure_code=probe.code,
                )
                if prepared_home is not None:
                    remove_sensitive_provider_home(paths=paths, prepared=prepared_home)
                _remove_definition_workdir(attempt_root=attempt_root)
                results.append({"cell_id": cell.cell_id, **probe.to_payload()})
                continue
            remove_sensitive_provider_home(paths=paths, prepared=prepared_home)
            _remove_definition_workdir(attempt_root=attempt_root)
            prepared_home = prepare_provider_home(
                repo_root=repo_root,
                paths=paths,
                provider=cell.provider,
                cell_id=cell.cell_id,
                attempt_number=attempt_number,
            )
            transition_attempt(
                attempt_root=attempt_root,
                expected_phase="planned",
                new_phase="preflight_passed",
            )
            results.append(
                {
                    "cell_id": cell.cell_id,
                    "attempt_id": state.attempt_id,
                    **probe.to_payload(),
                }
            )
        except BaseException:
            current = load_attempt_state(attempt_root=attempt_root)
            if current.phase == "planned":
                transition_attempt(
                    attempt_root=attempt_root,
                    expected_phase="planned",
                    new_phase="failed",
                    failure_code="provider_preflight_failed",
                )
            if prepared_home is not None:
                remove_sensitive_provider_home(paths=paths, prepared=prepared_home)
            _remove_definition_workdir(attempt_root=attempt_root)
            raise
    return {"run_root": str(paths.run_root), "results": results}


def capture_cells(
    *, repo_root: Path, run_root: Path, selected_cells: tuple[str, ...]
) -> dict[str, Any]:
    """Capture the latest preflight-passed attempt for each selected cell serially."""

    paths, plan = _load_full_plan(repo_root=repo_root, run_root=run_root)
    suite = load_suite_catalog(repo_root=repo_root)
    results: list[dict[str, Any]] = []
    for cell in _select_cells(plan=plan, selected_cells=selected_cells):
        attempt_root = _latest_attempt(paths=paths, cell_id=cell.cell_id, phase="preflight_passed")
        state = load_attempt_state(attempt_root=attempt_root)
        attempt_number = int(state.attempt_id[1:])
        project = _load_project(attempt_root=attempt_root)
        provider_home = _load_provider_home(attempt_root=attempt_root, provider=cell.provider)
        result = capture_attempt(
            paths=paths,
            suite=suite,
            cell=cell,
            attempt_number=attempt_number,
            project=project,
            provider_home=provider_home,
        )
        prepare_blind_review(attempt_root=attempt_root, render_video=False)
        results.append(result.to_payload())
    return {"run_root": str(paths.run_root), "results": results}


def label_status(
    *,
    repo_root: Path,
    run_root: Path,
    cell_id: str,
    labels_path: Path | None,
) -> dict[str, Any]:
    """Complete supplied labels or report current completion state."""

    paths, _plan = _load_full_plan(repo_root=repo_root, run_root=run_root)
    attempt_root = _latest_attempt(paths=paths, cell_id=cell_id)
    state = load_attempt_state(attempt_root=attempt_root)
    if labels_path is not None:
        completion = complete_manual_labels(attempt_root=attempt_root, labels_path=labels_path)
    elif state.phase in {"labels_complete", "replaying", "reported"}:
        completion = validate_label_completion(attempt_root=attempt_root)
    else:
        completion = {
            "phase": state.phase,
            "template_path": str(attempt_root / "labels" / "label-template.json"),
            "review_video_path": str(attempt_root / "labels" / "blind-review.mp4"),
        }
    return {"run_root": str(paths.run_root), "cell_id": cell_id, **completion}


def replay_cells(
    *, repo_root: Path, run_root: Path, selected_cells: tuple[str, ...]
) -> dict[str, Any]:
    """Replay selected completed attempts under all schedules."""

    paths, plan = _load_full_plan(repo_root=repo_root, run_root=run_root)
    results: list[dict[str, Any]] = []
    for cell in _select_cells(plan=plan, selected_cells=selected_cells):
        attempt_root = _latest_attempt(paths=paths, cell_id=cell.cell_id, phase="labels_complete")
        result = replay_attempt(
            attempt_root=attempt_root,
            provider=cell.provider,
        )
        results.append({"cell_id": cell.cell_id, **result})
    return {"run_root": str(paths.run_root), "results": results}


def report_suite(*, repo_root: Path, run_root: Path) -> dict[str, Any]:
    """Aggregate all preserved attempts without treating missing work as pass."""

    paths, plan = _load_full_plan(repo_root=repo_root, run_root=run_root)
    cell_rows: list[dict[str, Any]] = []
    qualified_operations = 0
    for cell in plan.cells:
        attempt_dirs = _attempt_dirs(paths=paths, cell_id=cell.cell_id)
        attempts: list[dict[str, Any]] = []
        qualified = False
        for attempt_root in attempt_dirs:
            state = load_attempt_state(attempt_root=attempt_root)
            tracker_path = attempt_root / "replay" / "tracker-verdict.json"
            tracker = load_json_object(tracker_path) if tracker_path.is_file() else None
            engineering_path = attempt_root / "engineering" / "engineering-verdict.json"
            engineering = load_json_object(engineering_path) if engineering_path.is_file() else None
            attempt_qualified = (
                state.phase == "reported"
                and tracker is not None
                and tracker.get("status") == "pass"
                and engineering is not None
                and engineering.get("status") == "pass"
            )
            qualified = qualified or attempt_qualified
            attempts.append(
                {
                    "attempt_id": state.attempt_id,
                    "phase": state.phase,
                    "failure_code": state.failure_code,
                    "qualified": attempt_qualified,
                    "engineering": engineering,
                    "tracker": tracker,
                }
            )
        if qualified:
            qualified_operations += len(cell.operations)
        cell_rows.append(
            {
                "cell_id": cell.cell_id,
                "provider": cell.provider,
                "procedure_id": cell.procedure_id,
                "operation_count": len(cell.operations),
                "transition_families": list(cell.transition_families),
                "qualified": qualified,
                "attempts": attempts,
            }
        )
    qualified_cells = sum(1 for item in cell_rows if item["qualified"])
    status = (
        "pass"
        if qualified_cells == 12 and qualified_operations == 242 and len(plan.cells) == 12
        else "incomplete"
    )
    payload = {
        "schema_version": 1,
        "run_root": str(paths.run_root),
        "status": status,
        "cell_count": len(plan.cells),
        "qualified_cells": qualified_cells,
        "planned_operations": plan.total_operations,
        "qualified_operations": qualified_operations,
        "gemini_artifact_count": 0,
        "cells": cell_rows,
    }
    save_json_atomic(paths.aggregate_dir / "qualification-report.json", payload)
    (paths.aggregate_dir / "qualification-report.md").write_text(
        _report_markdown(payload=payload), encoding="utf-8"
    )
    return payload


def cleanup_suite(*, repo_root: Path, run_root: Path) -> dict[str, Any]:
    """Reap owned runtime resources and remove sensitive transient trees."""

    paths, _plan = _load_full_plan(repo_root=repo_root, run_root=run_root)
    killed_sessions: set[str] = set()
    removed_definition_workdirs = 0
    for attempt_root in paths.sessions_dir.glob("*/attempts/a*"):
        owned_path = attempt_root / "runtime" / "owned-resources.json"
        if owned_path.is_file():
            owned = load_json_object(owned_path)
            session_name = str(owned.get("tmux_session_name", ""))
            if session_name.startswith("shared-tui-"):
                kill_tmux_session_if_exists(session_name=session_name)
                killed_sessions.add(session_name)
        recorder_manifest = attempt_root / "recording" / "terminal-record" / "manifest.json"
        if recorder_manifest.is_file():
            manifest = load_json_object(recorder_manifest)
            recorder_name = str(manifest.get("recorder_session_name", ""))
            if recorder_name.startswith("HMREC-"):
                kill_tmux_session_if_exists(session_name=recorder_name)
                killed_sessions.add(recorder_name)
        definition_workdir = attempt_root / "runtime" / "definition-workdir"
        if definition_workdir.exists():
            shutil.rmtree(definition_workdir)
            removed_definition_workdirs += 1
    provider_homes_removed = paths.provider_homes_dir.exists()
    if provider_homes_removed:
        shutil.rmtree(paths.provider_homes_dir)
    payload = {
        "schema_version": 1,
        "run_root": str(paths.run_root),
        "killed_tmux_sessions": sorted(killed_sessions),
        "provider_homes_removed": provider_homes_removed,
        "definition_workdirs_removed": removed_definition_workdirs,
    }
    save_json_atomic(paths.aggregate_dir / "cleanup-report.json", payload)
    return payload


def _load_full_plan(*, repo_root: Path, run_root: Path) -> tuple[LongHorizonRunPaths, SuitePlan]:
    """Load the immutable complete plan."""

    return create_or_resume_plan(repo_root=repo_root, requested_run_root=run_root)


def _select_cells(*, plan: SuitePlan, selected_cells: tuple[str, ...]) -> tuple[PlannedCell, ...]:
    """Select action cells while preserving the complete suite plan."""

    if not selected_cells:
        return plan.cells
    selected = set(selected_cells)
    cells = tuple(item for item in plan.cells if item.cell_id in selected)
    unknown = selected.difference(item.cell_id for item in cells)
    if unknown:
        raise ValueError(f"Unknown cells: {', '.join(sorted(unknown))}")
    return cells


def _attempt_dirs(*, paths: LongHorizonRunPaths, cell_id: str) -> tuple[Path, ...]:
    """Return ordered preserved attempt roots."""

    root = paths.sessions_dir / cell_id.replace(":", "-") / "attempts"
    return tuple(sorted(item for item in root.glob("a[0-9][0-9][0-9]") if item.is_dir()))


def _latest_attempt(*, paths: LongHorizonRunPaths, cell_id: str, phase: str | None = None) -> Path:
    """Return the newest attempt, optionally requiring an exact phase."""

    candidates = [
        item
        for item in _attempt_dirs(paths=paths, cell_id=cell_id)
        if phase is None or load_attempt_state(attempt_root=item).phase == phase
    ]
    if not candidates:
        suffix = f" in phase {phase}" if phase else ""
        raise ValueError(f"No attempt exists for {cell_id}{suffix}")
    return candidates[-1]


def _load_project(*, attempt_root: Path) -> PreparedProject:
    """Restore a persisted project manifest."""

    payload = load_json_object(attempt_root / "engineering" / "project-manifest.json")
    return PreparedProject(**payload)


def _load_provider_home(*, attempt_root: Path, provider: ProviderName) -> PreparedProviderHome:
    """Restore runtime-only provider paths from sanitized metadata."""

    payload = load_json_object(attempt_root / "runtime" / "provider-launch-manifest.json")
    environment = (
        {
            name: "http://127.0.0.1:7990"
            for name in cast(list[str], payload.get("environment_names", []))
            if "proxy" in name.lower() and name.lower() != "no_proxy"
        }
        if provider == "codex"
        else {}
    )
    if provider == "codex":
        environment.update(
            {"NO_PROXY": "127.0.0.1,localhost,::1", "no_proxy": "127.0.0.1,localhost,::1"}
        )
    return PreparedProviderHome(
        provider=provider,
        home_path=Path(str(payload["home_path"])),
        manifest_path=Path(str(payload["manifest_path"])),
        launch_helper_path=Path(str(payload["launch_helper_path"])),
        observed_version=str(payload["observed_version"]),
        strategy_id=str(payload["strategy_id"]),
        launch_command_sha256=str(payload["launch_command_sha256"]),
        environment=environment,
    )


def _report_markdown(*, payload: dict[str, Any]) -> str:
    """Render the retained qualification report."""

    lines = [
        "# Long-Horizon TUI State-Tracking Qualification",
        "",
        f"- Status: `{payload['status']}`",
        f"- Qualified cells: `{payload['qualified_cells']}/{payload['cell_count']}`",
        f"- Qualified operations: `{payload['qualified_operations']}/{payload['planned_operations']}`",
        "- Gemini artifacts: `0`",
        "",
        "| Cell | Qualified | Attempts |",
        "| --- | --- | --- |",
    ]
    for cell in cast(list[dict[str, Any]], payload["cells"]):
        attempts = ", ".join(
            f"{item['attempt_id']}:{item['phase']}"
            for item in cast(list[dict[str, Any]], cell["attempts"])
        )
        lines.append(f"| {cell['cell_id']} | {cell['qualified']} | {attempts or 'missing'} |")
    return "\n".join(lines) + "\n"


def _remove_definition_workdir(*, attempt_root: Path) -> None:
    """Remove the credential-linked disposable agent definition."""

    import shutil

    shutil.rmtree(attempt_root / "runtime" / "definition-workdir", ignore_errors=True)
