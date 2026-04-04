"""Live interactive watch workflow for the tracked-TUI demo pack."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from reactivex.scheduler import TimeoutScheduler
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from houmao.agents.brain_builder import BuildRequest, build_brain_home, load_brain_recipe
from houmao.agents.realm_controller.backends.tmux_runtime import (
    ensure_tmux_available,
    tmux_session_exists,
)
from houmao.shared_tui_tracking.models import RecordedObservation, RuntimeObservation
from houmao.shared_tui_tracking.reducer import StreamStateReducer, replay_timeline
from houmao.terminal_record.models import (
    TerminalRecordPaths,
    load_manifest as load_terminal_record_manifest,
)
from houmao.terminal_record.service import (
    start_terminal_record,
    status_terminal_record,
    stop_terminal_record,
)

from .agent_assets import materialize_generated_agent_tree
from .comparison import TimelineComparison, compare_timelines
from .config import ResolvedDemoConfig
from .groundtruth import expand_labels_to_groundtruth_timeline, load_fixture_inputs
from .models import (
    DEMO_PACK_SCHEMA_VERSION,
    LiveWatchLiveState,
    LiveWatchManifest,
    LiveWatchPaths,
    LiveWatchStartResult,
    ToolName,
    append_ndjson,
    ensure_directory_layout,
    load_input_events,
    load_json,
    load_ndjson,
    save_json,
)
from .ownership import (
    initialize_demo_session_ownership,
    publish_demo_session_recovery_pointers,
    reap_demo_owned_resources,
    resolve_demo_owned_resources,
    set_demo_session_ownership_status,
    set_demo_session_recorder_run_root,
    upsert_demo_owned_resource,
)
from .reporting import (
    build_live_run_issues,
    build_live_summary_report,
    write_issue_documents,
)
from .tooling import (
    build_dashboard_session_name,
    build_tool_session_name,
    capture_visible_pane_text,
    default_tool_runtime_metadata,
    detect_tool_version,
    launch_tmux_session,
    now_utc_iso,
    resolve_active_pane_id,
    sample_runtime_observation,
    write_command_script,
)


DEFAULT_DASHBOARD_REFRESH_PER_SECOND = 4.0


def start_live_watch(
    *,
    repo_root: Path,
    demo_config: ResolvedDemoConfig,
    tool: ToolName,
    output_root: Path | None,
    recipe_path: Path | None,
    sample_interval_seconds: float,
    runtime_observer_interval_seconds: float,
    settle_seconds: float,
    trace_enabled: bool,
) -> LiveWatchStartResult:
    """Start one live watch run for Claude or Codex."""

    ensure_tmux_available()
    run_root = _resolve_live_run_root(
        repo_root=repo_root,
        demo_config=demo_config,
        tool=tool,
        output_root=output_root,
    )
    if run_root.exists():
        raise RuntimeError(f"Run root already exists: {run_root}")
    paths = LiveWatchPaths.from_run_root(run_root=run_root)
    ensure_directory_layout(paths)
    initialize_demo_session_ownership(
        demo_id=demo_config.demo_id,
        run_root=run_root,
        workflow_kind="live_watch",
        tool=tool,
    )
    try:
        tool_metadata = default_tool_runtime_metadata(
            repo_root=repo_root,
            tool=tool,
            demo_config=demo_config,
        )
        selected_recipe_path = (
            recipe_path.expanduser().resolve()
            if recipe_path is not None
            else tool_metadata.interactive_watch_recipe_path
        )
        generated_agent_def_dir = materialize_generated_agent_tree(
            repo_root=repo_root,
            workdir=paths.workdir,
            tool=tool,
        )
        recipe = load_brain_recipe(selected_recipe_path)
        if recipe.tool != tool:
            raise RuntimeError(
                f"Interactive watch requested `{tool}`, but recipe `{selected_recipe_path}` declares `{recipe.tool}`."
            )
        build_result = build_brain_home(
            BuildRequest(
                agent_def_dir=generated_agent_def_dir,
                tool=recipe.tool,
                skills=list(recipe.skills),
                config_profile=recipe.config_profile,
                credential_profile=recipe.credential_profile,
                recipe_path=selected_recipe_path,
                recipe_launch_overrides=getattr(recipe, "launch_overrides", None),
                runtime_root=paths.runtime_root,
                mailbox=recipe.mailbox,
                agent_name=recipe.default_agent_name,
                launch_overrides=tool_metadata.launch_overrides,
                operator_prompt_mode=tool_metadata.operator_prompt_mode
                or recipe.operator_prompt_mode,
                persistent_env_records=recipe.launch_env_records,
            )
        )
        observed_version = detect_tool_version(tool=tool)
        tool_session_name = build_tool_session_name(tool=tool, run_id=run_root.name)
        dashboard_session_name = build_dashboard_session_name(
            tool=tool,
            run_id=run_root.name,
        )
        recorder_enabled = demo_config.evidence.live_watch_recorder_enabled
        save_json(paths.resolved_config_path, demo_config.to_payload())
        launch_tmux_session(
            session_name=tool_session_name,
            workdir=paths.workdir,
            launch_script=build_result.launch_helper_path,
        )
        upsert_demo_owned_resource(run_root=run_root, role="tool", session_name=tool_session_name)
        publish_demo_session_recovery_pointers(
            demo_id=demo_config.demo_id,
            run_root=run_root,
            session_name=tool_session_name,
            role="tool",
        )
        pane_id = resolve_active_pane_id(session_name=tool_session_name)
        if recorder_enabled:
            set_demo_session_recorder_run_root(
                run_root=run_root,
                recorder_run_root=paths.terminal_record_run_root,
            )
            upsert_demo_owned_resource(run_root=run_root, role="recorder", session_name=None)
            start_terminal_record(
                mode="passive",
                target_session=tool_session_name,
                target_pane=pane_id,
                tool=tool,
                run_root=paths.terminal_record_run_root,
                sample_interval_seconds=sample_interval_seconds,
            )
            recorder_manifest = load_terminal_record_manifest(
                paths.terminal_record_run_root / "manifest.json"
            )
            upsert_demo_owned_resource(
                run_root=run_root,
                role="recorder",
                session_name=recorder_manifest.recorder_session_name,
            )
            publish_demo_session_recovery_pointers(
                demo_id=demo_config.demo_id,
                run_root=run_root,
                session_name=recorder_manifest.recorder_session_name,
                role="recorder",
            )
        dashboard_command = (
            f"cd {repo_root} && pixi run python "
            f"scripts/demo/shared-tui-tracking-demo-pack/scripts/demo_driver.py "
            f"dashboard --run-root {run_root}"
        )
        dashboard_script = write_command_script(
            script_path=paths.logs_dir / "dashboard_launch.sh",
            command=dashboard_command,
        )
        manifest = LiveWatchManifest(
            schema_version=DEMO_PACK_SCHEMA_VERSION,
            run_id=run_root.name,
            tool=tool,
            repo_root=str(repo_root),
            run_root=str(paths.run_root),
            runtime_root=str(paths.runtime_root),
            recipe_path=str(selected_recipe_path),
            brain_home_path=str(build_result.home_path),
            brain_manifest_path=str(build_result.manifest_path),
            launch_helper_path=str(build_result.launch_helper_path),
            workdir=str(paths.workdir),
            tool_session_name=tool_session_name,
            tool_attach_command=f"tmux attach-session -t {tool_session_name}",
            dashboard_session_name=dashboard_session_name,
            dashboard_attach_command=f"tmux attach-session -t {dashboard_session_name}",
            dashboard_command=dashboard_command,
            recorder_enabled=recorder_enabled,
            terminal_record_run_root=(
                str(paths.terminal_record_run_root) if recorder_enabled else None
            ),
            resolved_config_path=str(paths.resolved_config_path),
            sample_interval_seconds=sample_interval_seconds,
            runtime_observer_interval_seconds=runtime_observer_interval_seconds,
            settle_seconds=settle_seconds,
            observed_version=observed_version,
            trace_enabled=trace_enabled,
            started_at_utc=now_utc_iso(),
            stopped_at_utc=None,
            stop_reason=None,
        )
        live_state = LiveWatchLiveState(
            schema_version=DEMO_PACK_SCHEMA_VERSION,
            run_id=manifest.run_id,
            run_root=manifest.run_root,
            status="starting",
            latest_state_path=str(paths.latest_state_path),
            stop_requested_at_utc=None,
            last_error=None,
            updated_at_utc=now_utc_iso(),
        )
        save_json(paths.watch_manifest_path, manifest.to_payload())
        save_json(paths.live_state_path, live_state.to_payload())

        launch_tmux_session(
            session_name=dashboard_session_name,
            workdir=repo_root,
            launch_script=dashboard_script,
        )
        upsert_demo_owned_resource(
            run_root=run_root,
            role="dashboard",
            session_name=dashboard_session_name,
        )
        publish_demo_session_recovery_pointers(
            demo_id=demo_config.demo_id,
            run_root=run_root,
            session_name=dashboard_session_name,
            role="dashboard",
        )
        _wait_for_dashboard_running(paths=paths)
        set_demo_session_ownership_status(run_root=run_root, status="running")
        return LiveWatchStartResult(run_root=run_root, manifest=manifest)
    except KeyboardInterrupt as exc:
        _cleanup_failed_start(paths=paths, last_error=_error_text(exc))
        raise
    except Exception as exc:
        _cleanup_failed_start(paths=paths, last_error=_error_text(exc))
        raise


def inspect_live_watch(
    *,
    repo_root: Path,
    demo_config: ResolvedDemoConfig,
    run_root: Path | None,
) -> dict[str, Any]:
    """Return a stable machine-readable payload for one live watch run."""

    selected_run_root = _resolve_existing_run_root(
        repo_root=repo_root,
        demo_config=demo_config,
        run_root=run_root,
    )
    paths = LiveWatchPaths.from_run_root(run_root=selected_run_root)
    manifest = _load_manifest(paths.watch_manifest_path)
    live_state = _load_live_state(paths.live_state_path)
    resolved_resources = resolve_demo_owned_resources(run_root=selected_run_root)
    latest_state = load_json(paths.latest_state_path)
    tool_session_name = (
        resolved_resources.known_session_name(role="tool") or manifest.tool_session_name
    )
    dashboard_session_name = (
        resolved_resources.known_session_name(role="dashboard") or manifest.dashboard_session_name
    )
    return {
        "run_root": manifest.run_root,
        "runtime_root": manifest.runtime_root,
        "brain_home_path": manifest.brain_home_path,
        "brain_manifest_path": manifest.brain_manifest_path,
        "tool_attach_command": manifest.tool_attach_command,
        "dashboard_attach_command": manifest.dashboard_attach_command,
        "recorder_enabled": manifest.recorder_enabled,
        "recorder_root": (
            str(resolved_resources.recorder_run_root)
            if resolved_resources.recorder_run_root is not None
            else manifest.terminal_record_run_root
        ),
        "tool_session_running": resolved_resources.live_session_name(role="tool") is not None
        or tmux_session_exists(session_name=tool_session_name),
        "dashboard_session_running": resolved_resources.live_session_name(role="dashboard")
        is not None
        or tmux_session_exists(session_name=dashboard_session_name),
        "recorder_status": _recorder_status_payload(manifest=manifest),
        "live_status": live_state.to_payload(),
        "latest_state": latest_state,
        "ownership_path": str(paths.session_ownership_path),
        "owned_resources": [item.to_payload() for item in resolved_resources.owned_resources],
        "artifact_paths": {
            "latest_state": str(paths.latest_state_path),
            "state_samples": str(paths.state_samples_path),
            "transitions": str(paths.transitions_path),
            "runtime_observations": str(paths.runtime_observations_path),
            "resolved_demo_config": str(paths.resolved_config_path),
            "report": str(paths.report_path),
        },
    }


def stop_live_watch(
    *,
    repo_root: Path,
    demo_config: ResolvedDemoConfig,
    run_root: Path | None,
    stop_reason: str,
) -> dict[str, Any]:
    """Stop one live watch run and finalize replay/comparison/report artifacts."""

    selected_run_root = _resolve_existing_run_root(
        repo_root=repo_root,
        demo_config=demo_config,
        run_root=run_root,
    )
    paths = LiveWatchPaths.from_run_root(run_root=selected_run_root)
    manifest = _load_manifest(paths.watch_manifest_path)
    live_state = _load_live_state(paths.live_state_path)
    resolved_resources = resolve_demo_owned_resources(run_root=selected_run_root)
    stop_requested_at = now_utc_iso()
    save_json(
        paths.live_state_path,
        LiveWatchLiveState(
            schema_version=live_state.schema_version,
            run_id=live_state.run_id,
            run_root=live_state.run_root,
            status="stopping",
            latest_state_path=live_state.latest_state_path,
            stop_requested_at_utc=stop_requested_at,
            last_error=live_state.last_error,
            updated_at_utc=stop_requested_at,
        ).to_payload(),
    )
    try:
        set_demo_session_ownership_status(
            run_root=selected_run_root,
            status="cleanup_pending",
            last_error="graceful_stop_requested",
        )
    except FileNotFoundError:
        pass
    recorder_stop = (
        stop_terminal_record(run_root=resolved_resources.recorder_run_root)
        if manifest.recorder_enabled and resolved_resources.recorder_run_root is not None
        else None
    )
    _wait_for_dashboard_stop(paths=paths)
    cleanup_payload = reap_demo_owned_resources(
        resolved_resources=resolve_demo_owned_resources(run_root=selected_run_root),
        include_roles={"tool", "dashboard", "recorder"},
        stop_recorder=False,
        best_effort=False,
    )

    comparison = _finalize_live_replay(paths=paths, manifest=manifest)
    labels_present = bool(
        resolved_resources.recorder_run_root is not None
        and (resolved_resources.recorder_run_root / "labels.json").is_file()
    )
    issues = build_live_run_issues(
        comparison=comparison,
        labels_present=labels_present,
        recorder_enabled=manifest.recorder_enabled,
    )
    issue_paths = write_issue_documents(issues_dir=paths.issues_dir, issues=issues)
    artifact_paths: dict[str, Path] = {
        "latest state": paths.latest_state_path,
        "state samples": paths.state_samples_path,
        "transitions": paths.transitions_path,
        "runtime observations": paths.runtime_observations_path,
        "resolved demo config": paths.resolved_config_path,
    }
    if manifest.recorder_enabled:
        artifact_paths["replay timeline"] = paths.replay_timeline_path
        artifact_paths["comparison JSON"] = paths.comparison_json_path
    report = build_live_summary_report(
        manifest=manifest,
        comparison=comparison,
        labels_present=labels_present,
        recorder_enabled=manifest.recorder_enabled,
        issue_paths=issue_paths,
        artifact_paths=artifact_paths,
    )
    paths.report_path.write_text(report, encoding="utf-8")

    stopped_at_utc = now_utc_iso()
    save_json(
        paths.watch_manifest_path,
        LiveWatchManifest(
            schema_version=manifest.schema_version,
            run_id=manifest.run_id,
            tool=manifest.tool,
            repo_root=manifest.repo_root,
            run_root=manifest.run_root,
            runtime_root=manifest.runtime_root,
            recipe_path=manifest.recipe_path,
            brain_home_path=manifest.brain_home_path,
            brain_manifest_path=manifest.brain_manifest_path,
            launch_helper_path=manifest.launch_helper_path,
            workdir=manifest.workdir,
            tool_session_name=manifest.tool_session_name,
            tool_attach_command=manifest.tool_attach_command,
            dashboard_session_name=manifest.dashboard_session_name,
            dashboard_attach_command=manifest.dashboard_attach_command,
            dashboard_command=manifest.dashboard_command,
            recorder_enabled=manifest.recorder_enabled,
            terminal_record_run_root=manifest.terminal_record_run_root,
            resolved_config_path=manifest.resolved_config_path,
            sample_interval_seconds=manifest.sample_interval_seconds,
            runtime_observer_interval_seconds=manifest.runtime_observer_interval_seconds,
            settle_seconds=manifest.settle_seconds,
            observed_version=manifest.observed_version,
            trace_enabled=manifest.trace_enabled,
            started_at_utc=manifest.started_at_utc,
            stopped_at_utc=stopped_at_utc,
            stop_reason=stop_reason,
        ).to_payload(),
    )
    save_json(
        paths.live_state_path,
        LiveWatchLiveState(
            schema_version=live_state.schema_version,
            run_id=live_state.run_id,
            run_root=live_state.run_root,
            status="stopped",
            latest_state_path=live_state.latest_state_path,
            stop_requested_at_utc=stop_requested_at,
            last_error=live_state.last_error,
            updated_at_utc=stopped_at_utc,
        ).to_payload(),
    )
    try:
        set_demo_session_ownership_status(
            run_root=selected_run_root,
            status="stopped",
            last_error="graceful_stop_completed",
        )
    except FileNotFoundError:
        pass
    return {
        "run_root": str(paths.run_root),
        "report_path": str(paths.report_path),
        "comparison_path": str(paths.comparison_json_path) if manifest.recorder_enabled else None,
        "recorder_stop": recorder_stop,
        "recorder_enabled": manifest.recorder_enabled,
        "cleaned_sessions": cleanup_payload["cleaned_sessions"],
    }


def run_dashboard(*, run_root: Path) -> int:
    """Run the live watch dashboard loop for one run."""

    paths = LiveWatchPaths.from_run_root(run_root=run_root)
    manifest = _load_manifest(paths.watch_manifest_path)
    live_state = _load_live_state(paths.live_state_path)
    save_json(
        paths.live_state_path,
        LiveWatchLiveState(
            schema_version=live_state.schema_version,
            run_id=live_state.run_id,
            run_root=live_state.run_root,
            status="running",
            latest_state_path=live_state.latest_state_path,
            stop_requested_at_utc=live_state.stop_requested_at_utc,
            last_error=None,
            updated_at_utc=now_utc_iso(),
        ).to_payload(),
    )

    reducer = StreamStateReducer(
        tool=manifest.tool,
        observed_version=manifest.observed_version,
        settle_seconds=manifest.settle_seconds,
        scheduler=TimeoutScheduler.singleton(),
    )
    console = Console()
    terminal_record_paths: TerminalRecordPaths | None = None
    pane_id = resolve_active_pane_id(session_name=manifest.tool_session_name)
    observation_started_at = datetime.fromisoformat(manifest.started_at_utc)
    if manifest.recorder_enabled:
        if manifest.terminal_record_run_root is None:
            raise RuntimeError("Recorder-enabled live watch manifest is missing recorder root.")
        terminal_record_paths = TerminalRecordPaths.from_run_root(
            run_root=Path(manifest.terminal_record_run_root)
        )
        recorder_manifest = load_terminal_record_manifest(terminal_record_paths.manifest_path)
        observation_started_at = datetime.fromisoformat(recorder_manifest.started_at_utc)
        pane_id = recorder_manifest.target.pane_id
    processed_snapshot_count = 0
    latest_state_payload: dict[str, Any] | None = None
    runtime_rows: list[RuntimeObservation] = []
    try:
        with Live(console=console, refresh_per_second=DEFAULT_DASHBOARD_REFRESH_PER_SECOND) as live:
            while True:
                runtime_observation = sample_runtime_observation(
                    tool=manifest.tool,
                    session_name=manifest.tool_session_name,
                    pane_id=pane_id,
                    recorder_started_at=observation_started_at,
                )
                append_ndjson(paths.runtime_observations_path, runtime_observation.to_payload())
                runtime_rows.append(runtime_observation)
                if manifest.recorder_enabled:
                    assert terminal_record_paths is not None
                    snapshot_payloads = load_ndjson(terminal_record_paths.pane_snapshots_path)
                    while processed_snapshot_count < len(snapshot_payloads):
                        snapshot_payload = snapshot_payloads[processed_snapshot_count]
                        processed_snapshot_count += 1
                        observation = _recorded_observation_from_snapshot(
                            snapshot_payload=snapshot_payload,
                            runtime_rows=runtime_rows,
                        )
                        latest_state_payload = _persist_live_observation(
                            observation=observation,
                            reducer=reducer,
                            paths=paths,
                        )
                        _append_transition_events(
                            reducer=reducer,
                            paths=paths,
                            latest_state_payload_ref=lambda payload=latest_state_payload: payload,
                        )
                else:
                    processed_snapshot_count += 1
                    observation = _recorded_observation_from_visible_pane(
                        pane_id=pane_id,
                        runtime_observation=runtime_observation,
                        sample_index=processed_snapshot_count,
                    )
                    latest_state_payload = _persist_live_observation(
                        observation=observation,
                        reducer=reducer,
                        paths=paths,
                    )
                    _append_transition_events(
                        reducer=reducer,
                        paths=paths,
                        latest_state_payload_ref=lambda payload=latest_state_payload: payload,
                    )

                _append_transition_events(
                    reducer=reducer,
                    paths=paths,
                    latest_state_payload_ref=lambda payload=latest_state_payload: payload,
                )
                latest_state_payload = load_json(paths.latest_state_path)
                live.update(
                    _render_dashboard(manifest=manifest, latest_state_payload=latest_state_payload)
                )
                current_live_state = _load_live_state(paths.live_state_path)
                if current_live_state.stop_requested_at_utc is None:
                    time.sleep(manifest.runtime_observer_interval_seconds)
                    continue
                if not manifest.recorder_enabled:
                    break
                recorder_status = _recorder_status_payload(manifest=manifest)
                if recorder_status is None or recorder_status.get("status") != "running":
                    break
                time.sleep(manifest.runtime_observer_interval_seconds)
    except Exception as exc:
        save_json(
            paths.live_state_path,
            LiveWatchLiveState(
                schema_version=live_state.schema_version,
                run_id=live_state.run_id,
                run_root=live_state.run_root,
                status="failed",
                latest_state_path=live_state.latest_state_path,
                stop_requested_at_utc=live_state.stop_requested_at_utc,
                last_error=str(exc),
                updated_at_utc=now_utc_iso(),
            ).to_payload(),
        )
        raise

    final_live_state = _load_live_state(paths.live_state_path)
    save_json(
        paths.live_state_path,
        LiveWatchLiveState(
            schema_version=final_live_state.schema_version,
            run_id=final_live_state.run_id,
            run_root=final_live_state.run_root,
            status="stopped" if final_live_state.stop_requested_at_utc is not None else "running",
            latest_state_path=final_live_state.latest_state_path,
            stop_requested_at_utc=final_live_state.stop_requested_at_utc,
            last_error=final_live_state.last_error,
            updated_at_utc=now_utc_iso(),
        ).to_payload(),
    )
    return 0


def _resolve_live_run_root(
    *,
    repo_root: Path,
    demo_config: ResolvedDemoConfig,
    tool: ToolName,
    output_root: Path | None,
) -> Path:
    """Return the run root for one live watch run."""

    if output_root is not None:
        return output_root.expanduser().resolve()
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    del repo_root
    return (demo_config.live_root_path() / tool / stamp).resolve()


def _resolve_existing_run_root(
    *,
    repo_root: Path,
    demo_config: ResolvedDemoConfig,
    run_root: Path | None,
) -> Path:
    """Resolve an existing live-watch run root."""

    if run_root is not None:
        return run_root.expanduser().resolve()
    del repo_root
    parent = demo_config.live_root_path()
    candidates = [
        path for path in parent.rglob("*") if path.is_dir() and (path / "artifacts").is_dir()
    ]
    if not candidates:
        raise RuntimeError("No live watch run roots found")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _wait_for_dashboard_running(*, paths: LiveWatchPaths) -> None:
    """Wait until the dashboard updates live state to running."""

    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        payload = load_json(paths.live_state_path)
        if payload is not None:
            live_state = LiveWatchLiveState.from_payload(payload)
            if live_state.status == "running":
                return
            if live_state.status == "failed":
                raise RuntimeError(live_state.last_error or "interactive dashboard failed to start")
        time.sleep(0.2)
    raise TimeoutError("Timed out waiting for interactive dashboard to start")


def _wait_for_dashboard_stop(*, paths: LiveWatchPaths) -> None:
    """Wait until the dashboard leaves running/starting state."""

    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        payload = load_json(paths.live_state_path)
        if payload is not None:
            live_state = LiveWatchLiveState.from_payload(payload)
            if live_state.status in {"stopped", "failed"}:
                return
        time.sleep(0.2)


def _load_manifest(path: Path) -> LiveWatchManifest:
    """Load one live-watch manifest."""

    payload = load_json(path)
    if payload is None:
        raise FileNotFoundError(f"Live watch manifest not found: {path}")
    return LiveWatchManifest.from_payload(payload)


def _load_live_state(path: Path) -> LiveWatchLiveState:
    """Load one live-watch live-state payload."""

    payload = load_json(path)
    if payload is None:
        raise FileNotFoundError(f"Live watch live state not found: {path}")
    return LiveWatchLiveState.from_payload(payload)


def _cleanup_failed_start(*, paths: LiveWatchPaths, last_error: str) -> None:
    """Best-effort cleanup for one failed or interrupted startup."""

    _mark_start_failed(paths=paths, last_error=last_error)
    try:
        set_demo_session_ownership_status(
            run_root=paths.run_root, status="failed", last_error=last_error
        )
    except FileNotFoundError:
        pass
    try:
        reap_demo_owned_resources(
            resolved_resources=resolve_demo_owned_resources(run_root=paths.run_root),
            include_roles={"tool", "dashboard", "recorder"},
            stop_recorder=True,
            best_effort=True,
        )
    except Exception:
        pass


def _mark_start_failed(*, paths: LiveWatchPaths, last_error: str) -> None:
    """Persist failed startup state when run metadata exists."""

    try:
        live_state = _load_live_state(paths.live_state_path)
    except Exception:
        return
    save_json(
        paths.live_state_path,
        LiveWatchLiveState(
            schema_version=live_state.schema_version,
            run_id=live_state.run_id,
            run_root=live_state.run_root,
            status="failed",
            latest_state_path=live_state.latest_state_path,
            stop_requested_at_utc=live_state.stop_requested_at_utc,
            last_error=last_error,
            updated_at_utc=now_utc_iso(),
        ).to_payload(),
    )


def _error_text(error: BaseException) -> str:
    """Return a stable error string for live-state persistence."""

    message = str(error).strip()
    if message:
        return message
    return error.__class__.__name__


def _append_transition_events(
    *,
    reducer: StreamStateReducer,
    paths: LiveWatchPaths,
    latest_state_payload_ref: Any,
) -> None:
    """Persist pending reducer transition events and timer-origin samples."""

    latest_observation = reducer.latest_observation
    latest_signals = reducer.latest_signals
    if latest_signals is None:
        reducer.drain_events()
        return
    for event in reducer.drain_events():
        append_ndjson(paths.transitions_path, event.to_payload())
        if event.source == "timer":
            timer_sample = {
                "source": "timer",
                "sample_id": event.sample_id,
                "elapsed_seconds": event.at_seconds,
                "ts_utc": now_utc_iso(),
                "diagnostics_availability": event.diagnostics_availability,
                "surface_accepting_input": latest_signals.accepting_input,
                "surface_editing_input": latest_signals.editing_input,
                "surface_ready_posture": latest_signals.ready_posture,
                "turn_phase": event.turn_phase,
                "last_turn_result": event.last_turn_result,
                "last_turn_source": event.last_turn_source,
                "detector_name": latest_signals.detector_name,
                "detector_version": latest_signals.detector_version,
                "active_reasons": list(latest_signals.active_reasons),
                "notes": list(latest_signals.notes),
                "transition_note": event.note,
            }
            append_ndjson(paths.state_samples_path, timer_sample)
            save_json(paths.latest_state_path, timer_sample)
        elif latest_observation is not None:
            latest_payload = latest_state_payload_ref()
            if latest_payload is not None:
                latest_payload["transition_note"] = event.note
                save_json(paths.latest_state_path, latest_payload)


def _render_dashboard(
    *,
    manifest: LiveWatchManifest,
    latest_state_payload: dict[str, Any] | None,
) -> Panel:
    """Render the Rich dashboard panel."""

    lines: list[Text] = [
        Text(f"run: {manifest.run_id}"),
        Text(f"tool: {manifest.tool}"),
        Text(f"recipe: {Path(manifest.recipe_path).name}"),
        Text(f"detector version input: {manifest.observed_version or 'unknown'}"),
        Text(f"recorder: {'enabled' if manifest.recorder_enabled else 'disabled'}"),
    ]
    if latest_state_payload is None:
        lines.append(Text("state: waiting for observations...", style="yellow"))
    else:
        lines.extend(
            [
                _styled_state_line(
                    "availability", str(latest_state_payload["diagnostics_availability"])
                ),
                _styled_state_line("turn", str(latest_state_payload["turn_phase"])),
                _styled_state_line("last", str(latest_state_payload["last_turn_result"])),
                _styled_state_line("source", str(latest_state_payload["last_turn_source"])),
                _styled_state_line("input", str(latest_state_payload["surface_accepting_input"])),
                _styled_state_line("editing", str(latest_state_payload["surface_editing_input"])),
                _styled_state_line(
                    "ready_posture", str(latest_state_payload["surface_ready_posture"])
                ),
                Text(
                    "sample: "
                    f"{latest_state_payload.get('sample_id') or '<timer>'} @ "
                    f"{latest_state_payload['elapsed_seconds']:.2f}s"
                ),
                Text(
                    "reasons: "
                    + (", ".join(latest_state_payload.get("active_reasons", [])) or "none")
                ),
                Text("notes: " + (", ".join(latest_state_payload.get("notes", [])) or "none")),
                Text(f"transition: {latest_state_payload.get('transition_note', 'none')}"),
            ]
        )
    return Panel(Group(*lines), title="Shared TUI Tracking Live Watch", border_style="cyan")


def _styled_state_line(label: str, value: str) -> Text:
    """Render one labeled state token line."""

    line = Text(f"{label}: ")
    line.append(value, style=_state_style(label=label, value=value))
    return line


def _state_style(*, label: str, value: str) -> str:
    """Return the Rich style for one state token."""

    mapping = {
        ("availability", "available"): "green",
        ("availability", "tui_down"): "red",
        ("availability", "unavailable"): "red",
        ("turn", "ready"): "cyan",
        ("turn", "active"): "yellow",
        ("turn", "unknown"): "magenta",
        ("last", "success"): "green",
        ("last", "interrupted"): "bright_red",
        ("last", "known_failure"): "red bold",
        ("last", "none"): "white",
    }
    tristate_styles = {"yes": "green", "no": "red", "unknown": "magenta"}
    if (label, value) in mapping:
        return mapping[(label, value)]
    if value in tristate_styles:
        return tristate_styles[value]
    return "white"


def _recorded_observation_from_snapshot(
    *,
    snapshot_payload: dict[str, Any],
    runtime_rows: list[RuntimeObservation],
) -> RecordedObservation:
    """Build one recorded observation aligned with the latest runtime sample."""

    elapsed_seconds = float(snapshot_payload["elapsed_seconds"])
    matched_runtime: RuntimeObservation | None = None
    for runtime in runtime_rows:
        if runtime.elapsed_seconds <= elapsed_seconds:
            matched_runtime = runtime
        else:
            break
    return RecordedObservation(
        sample_id=str(snapshot_payload["sample_id"]),
        elapsed_seconds=elapsed_seconds,
        ts_utc=str(snapshot_payload["ts_utc"]),
        output_text=str(snapshot_payload["output_text"]),
        runtime=matched_runtime,
    )


def _recorded_observation_from_visible_pane(
    *,
    pane_id: str,
    runtime_observation: RuntimeObservation,
    sample_index: int,
) -> RecordedObservation:
    """Build one synthetic observation from the current visible tmux pane."""

    try:
        output_text = capture_visible_pane_text(pane_id=pane_id)
    except Exception:
        output_text = ""
    return RecordedObservation(
        sample_id=f"s{sample_index:06d}",
        elapsed_seconds=runtime_observation.elapsed_seconds,
        ts_utc=runtime_observation.ts_utc,
        output_text=output_text,
        runtime=runtime_observation,
    )


def _persist_live_observation(
    *,
    observation: RecordedObservation,
    reducer: StreamStateReducer,
    paths: LiveWatchPaths,
) -> dict[str, Any]:
    """Reduce and persist one live observation row."""

    state = reducer.process_observation(observation)
    payload = {
        "source": "observation",
        "sample_id": observation.sample_id,
        "elapsed_seconds": observation.elapsed_seconds,
        "ts_utc": observation.ts_utc,
        "diagnostics_availability": state.diagnostics_availability,
        "surface_accepting_input": state.surface_accepting_input,
        "surface_editing_input": state.surface_editing_input,
        "surface_ready_posture": state.surface_ready_posture,
        "turn_phase": state.turn_phase,
        "last_turn_result": state.last_turn_result,
        "last_turn_source": state.last_turn_source,
        "detector_name": state.detector_name,
        "detector_version": state.detector_version,
        "active_reasons": list(state.active_reasons),
        "notes": list(state.notes),
        "transition_note": "observation_sample",
    }
    append_ndjson(paths.state_samples_path, payload)
    save_json(paths.latest_state_path, payload)
    return payload


def _finalize_live_replay(
    *,
    paths: LiveWatchPaths,
    manifest: LiveWatchManifest,
) -> TimelineComparison | None:
    """Replay retained live evidence and compare when labels are available."""

    if not manifest.recorder_enabled or manifest.terminal_record_run_root is None:
        return None

    fixture_inputs = load_fixture_inputs(
        recording_root=Path(manifest.terminal_record_run_root),
        runtime_observations_path=paths.runtime_observations_path
        if paths.runtime_observations_path.is_file()
        else None,
    )
    replay_timeline_rows, replay_events = replay_timeline(
        observations=fixture_inputs.observations,
        tool=manifest.tool,
        observed_version=manifest.observed_version,
        settle_seconds=manifest.settle_seconds,
        input_events=load_input_events(
            Path(manifest.terminal_record_run_root) / "input_events.ndjson"
        ),
    )
    from .models import overwrite_ndjson

    overwrite_ndjson(
        paths.replay_timeline_path, [item.to_payload() for item in replay_timeline_rows]
    )
    overwrite_ndjson(paths.replay_events_path, [item.to_payload() for item in replay_events])

    labels_path = Path(manifest.terminal_record_run_root) / "labels.json"
    if not labels_path.is_file():
        return None
    groundtruth = expand_labels_to_groundtruth_timeline(
        recording_root=Path(manifest.terminal_record_run_root),
        labels_path=labels_path,
    )
    overwrite_ndjson(paths.groundtruth_timeline_path, [item.to_payload() for item in groundtruth])
    comparison, comparison_markdown = compare_timelines(
        groundtruth=groundtruth,
        replay=replay_timeline_rows,
    )
    save_json(paths.comparison_json_path, comparison.to_payload())
    paths.comparison_markdown_path.write_text(comparison_markdown, encoding="utf-8")
    return comparison


def _recorder_status_payload(manifest: LiveWatchManifest) -> dict[str, Any] | None:
    """Return recorder status when the run retained recorder artifacts."""

    if not manifest.recorder_enabled or manifest.terminal_record_run_root is None:
        return None
    return status_terminal_record(run_root=Path(manifest.terminal_record_run_root))
