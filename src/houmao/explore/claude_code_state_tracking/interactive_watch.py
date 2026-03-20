"""Interactive watch workflow for live Claude Code state observation."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reactivex.scheduler import TimeoutScheduler
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from houmao.agents.brain_builder import BuildRequest, build_brain_home, load_brain_recipe
from houmao.agents.realm_controller.backends.tmux_runtime import (
    cleanup_tmux_session,
    ensure_tmux_available,
    tmux_session_exists,
)
from houmao.explore.claude_code_state_tracking.models import (
    InteractiveWatchLiveState,
    InteractiveWatchManifest,
    InteractiveWatchPaths,
    LiveStateSample,
    RecordedObservation,
    RuntimeObservation,
    append_ndjson,
    load_json,
    load_ndjson,
    save_json,
)
from houmao.explore.claude_code_state_tracking.runtime_support import (
    detect_claude_version,
    find_supported_process_pid,
    launch_tmux_session,
    now_utc_iso,
    process_is_alive,
    query_pane_state,
    resolve_active_pane_id,
)
from houmao.explore.claude_code_state_tracking.state_reducer import StreamStateReducer
from houmao.terminal_record.models import TerminalRecordPaths, load_manifest
from houmao.terminal_record.service import (
    start_terminal_record,
    status_terminal_record,
    stop_terminal_record,
)


INTERACTIVE_WATCH_SCHEMA_VERSION = 1
DEFAULT_INTERACTIVE_RUN_ROOT_PARENT = Path("tmp/explore/claude-code-state-tracking/interactive-watch")
DEFAULT_INTERACTIVE_RECIPE = Path(
    "tests/fixtures/agents/brains/brain-recipes/claude/interactive-watch-default.yaml"
)
DEFAULT_SAMPLE_INTERVAL_SECONDS = 0.25
DEFAULT_SETTLE_SECONDS = 1.0
DEFAULT_DASHBOARD_REFRESH_PER_SECOND = 4.0
CLAUDE_INTERACTIVE_LAUNCH_ARGS: list[str] = ["--dangerously-skip-permissions"]


@dataclass(frozen=True)
class InteractiveWatchStartResult:
    """Summary of one started interactive watch run."""

    run_root: Path
    manifest: InteractiveWatchManifest


@dataclass
class _InteractiveWatchStartupResources:
    """Track workflow-owned resources created during startup."""

    claude_session_name: str | None = None
    dashboard_session_name: str | None = None
    terminal_record_run_root: Path | None = None
    metadata_written: bool = False


def start_interactive_watch(
    *,
    repo_root: Path,
    output_root: Path | None,
    recipe_path: Path | None,
    sample_interval_seconds: float,
    settle_seconds: float,
    trace_enabled: bool,
) -> InteractiveWatchStartResult:
    """Start one interactive Claude watch run."""

    ensure_tmux_available()
    run_root = _resolve_interactive_run_root(repo_root=repo_root, output_root=output_root)
    if run_root.exists():
        raise RuntimeError(f"Run root already exists: {run_root}")
    paths = InteractiveWatchPaths.from_run_root(run_root=run_root)
    _ensure_run_directories(paths=paths)

    selected_recipe_path = _resolve_recipe_path(repo_root=repo_root, recipe_path=recipe_path)
    recipe = load_brain_recipe(selected_recipe_path)
    if recipe.tool != "claude":
        raise RuntimeError(
            f"Interactive Claude watch requires a Claude recipe, got {recipe.tool!r} from "
            f"{selected_recipe_path}"
        )

    build_result = build_brain_home(
        BuildRequest(
            agent_def_dir=(repo_root / "tests" / "fixtures" / "agents").resolve(),
            tool=recipe.tool,
            skills=list(recipe.skills),
            config_profile=recipe.config_profile,
            credential_profile=recipe.credential_profile,
            runtime_root=paths.runtime_root,
            mailbox=recipe.mailbox,
            agent_name=recipe.default_agent_name,
            launch_args_override=list(CLAUDE_INTERACTIVE_LAUNCH_ARGS),
        )
    )
    observed_version = detect_claude_version()
    claude_session_name = _session_name(prefix="cc-track-watch", run_id=run_root.name)
    dashboard_session_name = _session_name(prefix="cc-track-dashboard", run_id=run_root.name)
    resources = _InteractiveWatchStartupResources()
    try:
        launch_tmux_session(
            session_name=claude_session_name,
            workdir=paths.workdir,
            launch_script=build_result.launch_helper_path,
        )
        resources.claude_session_name = claude_session_name
        pane_id = resolve_active_pane_id(session_name=claude_session_name)
        resources.terminal_record_run_root = paths.terminal_record_run_root
        terminal_record_payload = start_terminal_record(
            mode="passive",
            target_session=claude_session_name,
            target_pane=pane_id,
            tool="claude",
            run_root=paths.terminal_record_run_root,
            sample_interval_seconds=sample_interval_seconds,
        )

        dashboard_command = (
            f"cd {repo_root} && "
            f"pixi run python scripts/explore/claude-code-state-tracking/run.py dashboard "
            f"--run-root {run_root}"
        )
        dashboard_script = _write_command_script(
            script_path=paths.logs_dir / "dashboard_launch.sh",
            command=dashboard_command,
        )
        manifest = InteractiveWatchManifest(
            schema_version=INTERACTIVE_WATCH_SCHEMA_VERSION,
            run_id=run_root.name,
            repo_root=str(repo_root),
            run_root=str(paths.run_root),
            runtime_root=str(paths.runtime_root),
            recipe_path=str(selected_recipe_path),
            brain_home_path=str(build_result.home_path),
            brain_manifest_path=str(build_result.manifest_path),
            launch_helper_path=str(build_result.launch_helper_path),
            workdir=str(paths.workdir),
            claude_session_name=claude_session_name,
            claude_attach_command=f"tmux attach-session -t {claude_session_name}",
            dashboard_session_name=dashboard_session_name,
            dashboard_attach_command=f"tmux attach-session -t {dashboard_session_name}",
            dashboard_command=dashboard_command,
            terminal_record_run_root=str(paths.terminal_record_run_root),
            sample_interval_seconds=sample_interval_seconds,
            settle_seconds=settle_seconds,
            observed_version=observed_version,
            trace_enabled=trace_enabled,
            started_at_utc=now_utc_iso(),
            stopped_at_utc=None,
            stop_reason=None,
        )
        live_state = InteractiveWatchLiveState(
            schema_version=INTERACTIVE_WATCH_SCHEMA_VERSION,
            run_id=manifest.run_id,
            run_root=manifest.run_root,
            status="starting",
            latest_state_path=str(paths.latest_state_path),
            stop_requested_at_utc=None,
            last_error=None,
            updated_at_utc=now_utc_iso(),
        )
        _save_watch_manifest(paths.watch_manifest_path, manifest)
        _save_watch_live_state(paths.live_state_path, live_state)
        save_json(paths.artifacts_dir / "start_payload.json", terminal_record_payload)
        resources.metadata_written = True

        launch_tmux_session(
            session_name=dashboard_session_name,
            workdir=repo_root,
            launch_script=dashboard_script,
        )
        resources.dashboard_session_name = dashboard_session_name
        _wait_for_dashboard_running(paths=paths)
        return InteractiveWatchStartResult(run_root=run_root, manifest=manifest)
    except KeyboardInterrupt as exc:
        _cleanup_failed_start(paths=paths, resources=resources, last_error=_error_text(exc))
        raise
    except Exception as exc:
        _cleanup_failed_start(paths=paths, resources=resources, last_error=_error_text(exc))
        raise


def inspect_interactive_watch(*, repo_root: Path, run_root: Path | None) -> dict[str, Any]:
    """Return a stable machine-readable payload for one interactive run."""

    selected_run_root = _resolve_existing_run_root(repo_root=repo_root, run_root=run_root)
    paths = InteractiveWatchPaths.from_run_root(run_root=selected_run_root)
    manifest = _load_watch_manifest(paths.watch_manifest_path)
    live_state = _load_watch_live_state(paths.live_state_path)
    latest_state = load_json(paths.latest_state_path)
    state_samples = str(paths.state_samples_path)
    transitions = str(paths.transitions_path)
    return {
        "run_root": manifest.run_root,
        "runtime_root": manifest.runtime_root,
        "brain_home_path": manifest.brain_home_path,
        "brain_manifest_path": manifest.brain_manifest_path,
        "claude_attach_command": manifest.claude_attach_command,
        "dashboard_attach_command": manifest.dashboard_attach_command,
        "recorder_root": manifest.terminal_record_run_root,
        "claude_session_running": tmux_session_exists(session_name=manifest.claude_session_name),
        "dashboard_session_running": tmux_session_exists(
            session_name=manifest.dashboard_session_name
        ),
        "recorder_status": status_terminal_record(
            run_root=Path(manifest.terminal_record_run_root)
        ),
        "live_status": live_state.to_payload(),
        "latest_state": latest_state,
        "artifact_paths": {
            "latest_state": str(paths.latest_state_path),
            "state_samples": state_samples,
            "transitions": transitions,
            "runtime_observations": str(paths.runtime_observations_path),
            "report": str(paths.report_path),
        },
    }


def stop_interactive_watch(
    *,
    repo_root: Path,
    run_root: Path | None,
    stop_reason: str,
) -> dict[str, Any]:
    """Stop one interactive watch run and finalize analysis artifacts."""

    selected_run_root = _resolve_existing_run_root(repo_root=repo_root, run_root=run_root)
    paths = InteractiveWatchPaths.from_run_root(run_root=selected_run_root)
    manifest = _load_watch_manifest(paths.watch_manifest_path)
    live_state = _load_watch_live_state(paths.live_state_path)
    stop_requested_at = now_utc_iso()
    _save_watch_live_state(
        paths.live_state_path,
        InteractiveWatchLiveState(
            schema_version=live_state.schema_version,
            run_id=live_state.run_id,
            run_root=live_state.run_root,
            status="stopping",
            latest_state_path=live_state.latest_state_path,
            stop_requested_at_utc=stop_requested_at,
            last_error=live_state.last_error,
            updated_at_utc=stop_requested_at,
        ),
    )
    recorder_stop = stop_terminal_record(run_root=Path(manifest.terminal_record_run_root))
    _wait_for_dashboard_stop(paths=paths)
    _kill_tmux_session_if_exists(session_name=manifest.dashboard_session_name)
    _kill_tmux_session_if_exists(session_name=manifest.claude_session_name)

    from houmao.explore.claude_code_state_tracking.cli import _run_replay_workflow

    _run_replay_workflow(
        recording_root=Path(manifest.terminal_record_run_root),
        run_root=paths.run_root,
        observed_version=manifest.observed_version,
        settle_seconds=manifest.settle_seconds,
    )
    comparison_payload = load_json(paths.analysis_dir / "comparison.json") or {}
    report_markdown = _render_interactive_report(
        manifest=manifest,
        comparison_payload=comparison_payload,
        paths=paths,
    )
    paths.report_path.write_text(report_markdown, encoding="utf-8")
    stopped_at_utc = now_utc_iso()
    _save_watch_manifest(
        paths.watch_manifest_path,
        InteractiveWatchManifest(
            schema_version=manifest.schema_version,
            run_id=manifest.run_id,
            repo_root=manifest.repo_root,
            run_root=manifest.run_root,
            runtime_root=manifest.runtime_root,
            recipe_path=manifest.recipe_path,
            brain_home_path=manifest.brain_home_path,
            brain_manifest_path=manifest.brain_manifest_path,
            launch_helper_path=manifest.launch_helper_path,
            workdir=manifest.workdir,
            claude_session_name=manifest.claude_session_name,
            claude_attach_command=manifest.claude_attach_command,
            dashboard_session_name=manifest.dashboard_session_name,
            dashboard_attach_command=manifest.dashboard_attach_command,
            dashboard_command=manifest.dashboard_command,
            terminal_record_run_root=manifest.terminal_record_run_root,
            sample_interval_seconds=manifest.sample_interval_seconds,
            settle_seconds=manifest.settle_seconds,
            observed_version=manifest.observed_version,
            trace_enabled=manifest.trace_enabled,
            started_at_utc=manifest.started_at_utc,
            stopped_at_utc=stopped_at_utc,
            stop_reason=stop_reason,
        ),
    )
    _save_watch_live_state(
        paths.live_state_path,
        InteractiveWatchLiveState(
            schema_version=live_state.schema_version,
            run_id=live_state.run_id,
            run_root=live_state.run_root,
            status="stopped",
            latest_state_path=live_state.latest_state_path,
            stop_requested_at_utc=stop_requested_at,
            last_error=live_state.last_error,
            updated_at_utc=stopped_at_utc,
        ),
    )
    return {
        "run_root": str(paths.run_root),
        "report_path": str(paths.report_path),
        "comparison_path": str(paths.analysis_dir / "comparison.json"),
        "recorder_stop": recorder_stop,
    }


def run_dashboard(*, run_root: Path) -> int:
    """Run the live dashboard loop for one interactive watch run."""

    paths = InteractiveWatchPaths.from_run_root(run_root=run_root)
    manifest = _load_watch_manifest(paths.watch_manifest_path)
    live_state = _load_watch_live_state(paths.live_state_path)
    _save_watch_live_state(
        paths.live_state_path,
        InteractiveWatchLiveState(
            schema_version=live_state.schema_version,
            run_id=live_state.run_id,
            run_root=live_state.run_root,
            status="running",
            latest_state_path=live_state.latest_state_path,
            stop_requested_at_utc=live_state.stop_requested_at_utc,
            last_error=None,
            updated_at_utc=now_utc_iso(),
        ),
    )

    reducer = StreamStateReducer(
        observed_version=manifest.observed_version,
        settle_seconds=manifest.settle_seconds,
        scheduler=TimeoutScheduler.singleton(),
        trace_writer=_trace_writer(paths=paths) if manifest.trace_enabled else None,
    )
    console = Console()
    terminal_record_paths = TerminalRecordPaths.from_run_root(
        run_root=Path(manifest.terminal_record_run_root)
    )
    recorder_manifest = load_manifest(terminal_record_paths.manifest_path)
    recorder_started = datetime.fromisoformat(recorder_manifest.started_at_utc)
    processed_snapshot_count = 0
    latest_state_payload: dict[str, Any] | None = None
    last_render_signature: str | None = None
    try:
        with Live(console=console, refresh_per_second=DEFAULT_DASHBOARD_REFRESH_PER_SECOND) as live:
            while True:
                runtime_observation = _sample_runtime_observation(
                    manifest=manifest,
                    recorder_started=recorder_started,
                )
                append_ndjson(paths.runtime_observations_path, runtime_observation.to_payload())

                snapshot_payloads = load_ndjson(terminal_record_paths.pane_snapshots_path)
                runtime_payloads = load_ndjson(paths.runtime_observations_path)
                runtime_rows = [RuntimeObservation.from_payload(item) for item in runtime_payloads]
                while processed_snapshot_count < len(snapshot_payloads):
                    snapshot_payload = snapshot_payloads[processed_snapshot_count]
                    processed_snapshot_count += 1
                    observation = _recorded_observation_from_snapshot(
                        snapshot_payload=snapshot_payload,
                        runtime_rows=runtime_rows,
                    )
                    observation_state = reducer.process_observation(observation)
                    observation_sample = LiveStateSample(
                        source="observation",
                        sample_id=observation.sample_id,
                        elapsed_seconds=observation.elapsed_seconds,
                        ts_utc=observation.ts_utc,
                        diagnostics_availability=observation_state.diagnostics_availability,
                        surface_accepting_input=observation_state.surface_accepting_input,
                        surface_editing_input=observation_state.surface_editing_input,
                        surface_ready_posture=observation_state.surface_ready_posture,
                        turn_phase=observation_state.turn_phase,
                        last_turn_result=observation_state.last_turn_result,
                        detector_name=observation_state.detector_name,
                        detector_version=observation_state.detector_version,
                        active_reasons=observation_state.active_reasons,
                        notes=observation_state.notes,
                        transition_note="observation_sample",
                    )
                    append_ndjson(paths.state_samples_path, observation_sample.to_payload())
                    latest_state_payload = observation_sample.to_payload()
                    save_json(paths.latest_state_path, latest_state_payload)
                    _append_transition_events(
                        reducer=reducer,
                        paths=paths,
                        latest_state_payload_ref=lambda payload=latest_state_payload: payload,
                        latest_state_setter=lambda payload: _set_latest_state(
                            paths=paths, payload=payload
                        ),
                    )

                _append_transition_events(
                    reducer=reducer,
                    paths=paths,
                    latest_state_payload_ref=lambda payload=latest_state_payload: payload,
                    latest_state_setter=lambda payload: _set_latest_state(paths=paths, payload=payload),
                )
                latest_state_payload = load_json(paths.latest_state_path)
                render_signature = json.dumps(latest_state_payload or {}, sort_keys=True)
                if render_signature != last_render_signature:
                    last_render_signature = render_signature
                    _trace_dashboard_render(paths=paths, payload=latest_state_payload, enabled=manifest.trace_enabled)
                live.update(_render_dashboard(manifest=manifest, latest_state_payload=latest_state_payload))

                current_live_state = _load_watch_live_state(paths.live_state_path)
                recorder_status = status_terminal_record(run_root=Path(manifest.terminal_record_run_root))
                if current_live_state.stop_requested_at_utc is not None and recorder_status["status"] != "running":
                    break
                time.sleep(manifest.sample_interval_seconds)
    except Exception as exc:
        _save_watch_live_state(
            paths.live_state_path,
            InteractiveWatchLiveState(
                schema_version=live_state.schema_version,
                run_id=live_state.run_id,
                run_root=live_state.run_root,
                status="failed",
                latest_state_path=live_state.latest_state_path,
                stop_requested_at_utc=live_state.stop_requested_at_utc,
                last_error=str(exc),
                updated_at_utc=now_utc_iso(),
            ),
        )
        raise

    final_live_state = _load_watch_live_state(paths.live_state_path)
    _save_watch_live_state(
        paths.live_state_path,
        InteractiveWatchLiveState(
            schema_version=final_live_state.schema_version,
            run_id=final_live_state.run_id,
            run_root=final_live_state.run_root,
            status="stopped" if final_live_state.stop_requested_at_utc is not None else "running",
            latest_state_path=final_live_state.latest_state_path,
            stop_requested_at_utc=final_live_state.stop_requested_at_utc,
            last_error=final_live_state.last_error,
            updated_at_utc=now_utc_iso(),
        ),
    )
    return 0


def _ensure_run_directories(*, paths: InteractiveWatchPaths) -> None:
    """Create the canonical directory tree for one run."""

    for directory in (
        paths.run_root,
        paths.runtime_root,
        paths.workdir,
        paths.artifacts_dir,
        paths.logs_dir,
        paths.analysis_dir,
        paths.traces_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def _resolve_interactive_run_root(*, repo_root: Path, output_root: Path | None) -> Path:
    """Return the run root for one interactive watch run."""

    if output_root is not None:
        return output_root.expanduser().resolve()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return (repo_root / DEFAULT_INTERACTIVE_RUN_ROOT_PARENT / stamp).resolve()


def _resolve_existing_run_root(*, repo_root: Path, run_root: Path | None) -> Path:
    """Resolve an existing interactive watch run root."""

    if run_root is not None:
        return run_root.expanduser().resolve()
    parent = (repo_root / DEFAULT_INTERACTIVE_RUN_ROOT_PARENT).resolve()
    candidates = [path for path in parent.iterdir() if path.is_dir()] if parent.is_dir() else []
    if not candidates:
        raise RuntimeError("No interactive watch run roots found")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _resolve_recipe_path(*, repo_root: Path, recipe_path: Path | None) -> Path:
    """Resolve the interactive watch recipe path."""

    selected = recipe_path or (repo_root / DEFAULT_INTERACTIVE_RECIPE)
    return selected.expanduser().resolve()


def _session_name(*, prefix: str, run_id: str) -> str:
    """Build one bounded tmux session name."""

    return f"{prefix}-{run_id}"[:60]


def _write_command_script(*, script_path: Path, command: str) -> Path:
    """Write one shell script that runs a fixed command."""

    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"exec bash -lc {json.dumps(command)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return script_path


def _save_watch_manifest(path: Path, manifest: InteractiveWatchManifest) -> None:
    """Persist one interactive watch manifest."""

    save_json(path, manifest.to_payload())


def _load_watch_manifest(path: Path) -> InteractiveWatchManifest:
    """Load one interactive watch manifest."""

    payload = load_json(path)
    if payload is None:
        raise FileNotFoundError(f"Interactive watch manifest not found: {path}")
    return InteractiveWatchManifest.from_payload(payload)


def _save_watch_live_state(path: Path, live_state: InteractiveWatchLiveState) -> None:
    """Persist one interactive watch live-state payload."""

    save_json(path, live_state.to_payload())


def _load_watch_live_state(path: Path) -> InteractiveWatchLiveState:
    """Load one interactive watch live-state payload."""

    payload = load_json(path)
    if payload is None:
        raise FileNotFoundError(f"Interactive watch live state not found: {path}")
    return InteractiveWatchLiveState.from_payload(payload)


def _cleanup_failed_start(
    *, paths: InteractiveWatchPaths, resources: _InteractiveWatchStartupResources, last_error: str
) -> None:
    """Best-effort cleanup for one failed or interrupted startup."""

    if resources.metadata_written:
        _mark_start_failed(paths=paths, last_error=last_error)
    if resources.terminal_record_run_root is not None:
        _cleanup_terminal_record_start(run_root=resources.terminal_record_run_root)
    if resources.dashboard_session_name is not None:
        _kill_tmux_session_if_exists(session_name=resources.dashboard_session_name)
    if resources.claude_session_name is not None:
        _kill_tmux_session_if_exists(session_name=resources.claude_session_name)


def _mark_start_failed(*, paths: InteractiveWatchPaths, last_error: str) -> None:
    """Persist failed startup state when watch metadata exists."""

    try:
        live_state = _load_watch_live_state(paths.live_state_path)
    except (FileNotFoundError, KeyError, TypeError, ValueError):
        return
    _save_watch_live_state(
        paths.live_state_path,
        InteractiveWatchLiveState(
            schema_version=live_state.schema_version,
            run_id=live_state.run_id,
            run_root=live_state.run_root,
            status="failed",
            latest_state_path=live_state.latest_state_path,
            stop_requested_at_utc=live_state.stop_requested_at_utc,
            last_error=last_error,
            updated_at_utc=now_utc_iso(),
        ),
    )


def _cleanup_terminal_record_start(*, run_root: Path) -> None:
    """Best-effort cleanup for one partially started terminal-record run."""

    recorder_paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    if recorder_paths.live_state_path.is_file():
        try:
            stop_terminal_record(run_root=run_root)
        except (FileNotFoundError, KeyError, TypeError, ValueError, RuntimeError):
            pass
    _kill_tmux_session_if_exists(session_name=_terminal_record_session_name(run_root=run_root))


def _terminal_record_session_name(*, run_root: Path) -> str:
    """Return the recorder tmux session name for one run root."""

    recorder_paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    if recorder_paths.manifest_path.is_file():
        try:
            return load_manifest(recorder_paths.manifest_path).recorder_session_name
        except (FileNotFoundError, KeyError, TypeError, ValueError):
            pass
    normalized = run_root.name.replace(":", "-").replace(".", "-")
    return f"HMREC-{normalized}"


def _error_text(error: BaseException) -> str:
    """Return a stable error string for live-state persistence."""

    message = str(error).strip()
    if message:
        return message
    return error.__class__.__name__


def _wait_for_dashboard_running(*, paths: InteractiveWatchPaths) -> None:
    """Wait until the dashboard updates live state to running."""

    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        payload = load_json(paths.live_state_path)
        if payload is not None:
            live_state = InteractiveWatchLiveState.from_payload(payload)
            if live_state.status == "running":
                return
            if live_state.status == "failed":
                raise RuntimeError(live_state.last_error or "interactive dashboard failed to start")
        time.sleep(0.2)
    raise TimeoutError("Timed out waiting for interactive dashboard to start")


def _wait_for_dashboard_stop(*, paths: InteractiveWatchPaths) -> None:
    """Wait until the dashboard leaves running/starting state."""

    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        payload = load_json(paths.live_state_path)
        if payload is not None:
            live_state = InteractiveWatchLiveState.from_payload(payload)
            if live_state.status in {"stopped", "failed"}:
                return
        time.sleep(0.2)


def _kill_tmux_session_if_exists(*, session_name: str) -> None:
    """Kill one tmux session when it still exists."""

    if not tmux_session_exists(session_name=session_name):
        return
    cleanup_tmux_session(session_name=session_name)


def _sample_runtime_observation(
    *, manifest: InteractiveWatchManifest, recorder_started: datetime
) -> RuntimeObservation:
    """Capture one runtime liveness observation aligned to recorder time."""

    session_exists = tmux_session_exists(session_name=manifest.claude_session_name)
    pane_exists = False
    pane_dead = False
    pane_pid: int | None = None
    pane_pid_alive = False
    supported_process_pid: int | None = None
    supported_process_alive = False
    if session_exists:
        pane_state = query_pane_state(
            session_name=manifest.claude_session_name,
            pane_id=resolve_active_pane_id(session_name=manifest.claude_session_name),
        )
        if pane_state is not None:
            pane_exists = True
            pane_dead = pane_state["pane_dead"]
            pane_pid = pane_state["pane_pid"]
            if pane_pid is not None:
                pane_pid_alive = process_is_alive(pane_pid)
                supported_process_pid = find_supported_process_pid(root_pid=pane_pid)
                if supported_process_pid is not None:
                    supported_process_alive = process_is_alive(supported_process_pid)
    return RuntimeObservation(
        ts_utc=now_utc_iso(),
        elapsed_seconds=max(
            0.0, (datetime.now(UTC) - recorder_started.astimezone(UTC)).total_seconds()
        ),
        session_exists=session_exists,
        pane_exists=pane_exists,
        pane_dead=pane_dead,
        pane_pid=pane_pid,
        pane_pid_alive=pane_pid_alive,
        supported_process_pid=supported_process_pid,
        supported_process_alive=supported_process_alive,
    )


def _recorded_observation_from_snapshot(
    *, snapshot_payload: dict[str, Any], runtime_rows: list[RuntimeObservation]
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


def _append_transition_events(
    *,
    reducer: StreamStateReducer,
    paths: InteractiveWatchPaths,
    latest_state_payload_ref: Any,
    latest_state_setter: Any,
) -> None:
    """Persist pending reducer transition events and any timer-origin state samples."""

    latest_observation = reducer.latest_observation
    latest_signals = reducer.latest_signals
    if latest_signals is None:
        reducer.drain_events()
        return
    for event in reducer.drain_events():
        append_ndjson(paths.transitions_path, event.to_payload())
        if event.source == "timer":
            ts_utc = now_utc_iso()
            timer_sample = LiveStateSample(
                source="timer",
                sample_id=event.sample_id,
                elapsed_seconds=event.at_seconds,
                ts_utc=ts_utc,
                diagnostics_availability=event.diagnostics_availability,
                surface_accepting_input=latest_signals.accepting_input,
                surface_editing_input=latest_signals.editing_input,
                surface_ready_posture=latest_signals.ready_posture,
                turn_phase=event.turn_phase,
                last_turn_result=event.last_turn_result,
                detector_name=latest_signals.detector_name,
                detector_version=latest_signals.detector_version,
                active_reasons=latest_signals.active_reasons,
                notes=latest_signals.notes,
                transition_note=event.note,
            )
            append_ndjson(paths.state_samples_path, timer_sample.to_payload())
            latest_state_setter(timer_sample.to_payload())
        elif latest_observation is not None:
            latest_payload = latest_state_payload_ref()
            if latest_payload is not None:
                latest_payload["transition_note"] = event.note
                latest_state_setter(latest_payload)


def _set_latest_state(*, paths: InteractiveWatchPaths, payload: dict[str, Any]) -> None:
    """Persist the latest-state payload."""

    save_json(paths.latest_state_path, payload)


def _render_dashboard(
    *, manifest: InteractiveWatchManifest, latest_state_payload: dict[str, Any] | None
) -> Panel:
    """Render the interactive Rich dashboard panel."""

    lines: list[Text] = [
        Text(f"run: {manifest.run_id}"),
        Text(f"recipe: {Path(manifest.recipe_path).name}"),
        Text(f"detector: claude_code / {manifest.observed_version or 'unknown'}"),
    ]
    if latest_state_payload is None:
        lines.append(Text("state: waiting for recorded observations...", style="yellow"))
    else:
        lines.extend(
            [
                _styled_state_line(
                    "availability", str(latest_state_payload["diagnostics_availability"])
                ),
                _styled_state_line("turn", str(latest_state_payload["turn_phase"])),
                _styled_state_line("last", str(latest_state_payload["last_turn_result"])),
                _styled_state_line(
                    "input", str(latest_state_payload["surface_accepting_input"])
                ),
                _styled_state_line(
                    "editing", str(latest_state_payload["surface_editing_input"])
                ),
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
    return Panel(Group(*lines), title="Claude Code Interactive Watch", border_style="cyan")


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


def _trace_writer(*, paths: InteractiveWatchPaths):
    """Return one dense-trace writer closure."""

    def _write(category: str, payload: dict[str, Any]) -> None:
        """Append one trace record into the category-specific NDJSON file."""

        append_ndjson(paths.traces_dir / f"{category}.ndjson", payload)

    return _write


def _trace_dashboard_render(
    *, paths: InteractiveWatchPaths, payload: dict[str, Any] | None, enabled: bool
) -> None:
    """Persist one optional dashboard render trace."""

    if not enabled:
        return
    append_ndjson(
        paths.traces_dir / "dashboard_render_events.ndjson",
        {
            "ts_utc": now_utc_iso(),
            "latest_state": payload,
        },
    )


def _render_interactive_report(
    *,
    manifest: InteractiveWatchManifest,
    comparison_payload: dict[str, Any],
    paths: InteractiveWatchPaths,
) -> str:
    """Render the final interactive watch report."""

    mismatch_count = int(comparison_payload.get("mismatch_count", 0))
    verdict = "passed" if mismatch_count == 0 else "failed"
    lines = [
        "# Interactive Claude Code State Tracking Report",
        "",
        f"- Verdict: `{verdict}`",
        f"- Run root: `{paths.run_root}`",
        f"- Recipe: `{manifest.recipe_path}`",
        f"- Brain home: `{manifest.brain_home_path}`",
        f"- Brain manifest: `{manifest.brain_manifest_path}`",
        f"- Recorder root: `{manifest.terminal_record_run_root}`",
        f"- Latest state: `{paths.latest_state_path}`",
        f"- State samples: `{paths.state_samples_path}`",
        f"- Transitions: `{paths.transitions_path}`",
        f"- Runtime observations: `{paths.runtime_observations_path}`",
        f"- Comparison JSON: `{paths.analysis_dir / 'comparison.json'}`",
        f"- Comparison Markdown: `{paths.analysis_dir / 'comparison.md'}`",
        "",
        "## Summary",
        "",
        f"- Replay mismatch count: `{mismatch_count}`",
        f"- First divergence sample: `{comparison_payload.get('first_divergence_sample_id')}`",
        f"- Transition order matches: `{comparison_payload.get('transition_order_matches')}`",
    ]
    return "\n".join(lines) + "\n"
