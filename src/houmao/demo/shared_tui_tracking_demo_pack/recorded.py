"""Recorded capture and validation workflow for the tracked-TUI demo pack."""

from __future__ import annotations

import json
import re
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from houmao.agents.brain_builder import BuildRequest, build_brain_home, load_brain_recipe
from houmao.agents.realm_controller.backends.tmux_runtime import (
    ensure_tmux_available,
    parse_tmux_control_input,
    send_tmux_control_input,
)
from houmao.shared_tui_tracking.reducer import replay_timeline
from houmao.shared_tui_tracking.registry import DetectorProfileRegistry, app_id_from_tool
from houmao.terminal_record.models import TerminalRecordManifest, load_manifest
from houmao.terminal_record.runtime_bridge import append_managed_control_input_for_tmux_session
from houmao.terminal_record.service import start_terminal_record

from .comparison import TimelineComparison, compare_timelines
from .config import ResolvedDemoConfig
from .groundtruth import expand_labels_to_groundtruth_timeline, load_fixture_inputs
from .models import (
    DEMO_PACK_SCHEMA_VERSION,
    DemoOwnedResourceRole,
    RecordedFixtureManifest,
    RecordedValidationManifest,
    RecordedValidationPaths,
    ToolName,
    append_ndjson,
    ensure_directory_layout,
    load_input_events,
    overwrite_ndjson,
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
    build_recorded_run_issues,
    build_recorded_summary_report,
    write_issue_documents,
)
from .review_video import encode_review_video, render_review_frames
from .scenario import ScenarioDefinition
from .tooling import (
    build_session_name,
    capture_visible_pane_text,
    default_tool_runtime_metadata,
    detect_tool_version,
    kill_tmux_session_if_exists,
    kill_supported_process_for_pane,
    launch_tmux_session,
    now_utc_iso,
    resolve_active_pane_id,
    sample_runtime_observation,
)


_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_FIXTURE_MANIFEST_NAME = "fixture_manifest.json"
_SUBMIT_KEY_DELAY_SECONDS = 0.2
_INTERRUPT_SEQUENCE_BY_TOOL: dict[ToolName, tuple[str, ...]] = {
    "claude": ("<[Escape]>",),
    "codex": ("<[Escape]>",),
}
_CLOSE_SEQUENCE_BY_TOOL: dict[ToolName, tuple[str, ...]] = {
    "claude": ("<[C-c]>",),
    "codex": ("<[C-c]>",),
}
_GRACEFUL_CLOSE_TIMEOUT_SECONDS = 2.0
_GRACEFUL_CLOSE_POLL_SECONDS = 0.2
_INTERRUPTED_READY_STABLE_POLLS = 2


@dataclass(frozen=True)
class RecordedCaptureResult:
    """Summary of one completed recorded-capture run."""

    run_root: Path
    recording_root: Path
    scenario_id: str
    tool: ToolName
    observed_version: str | None


@dataclass(frozen=True)
class RecordedValidationResult:
    """Summary of one completed recorded-validation run."""

    run_root: Path
    manifest: RecordedValidationManifest
    comparison: TimelineComparison


@dataclass(frozen=True)
class _ResolvedScenarioLaunch:
    """Concrete launch settings after config and scenario overrides are merged."""

    settle_seconds: float
    sample_interval_seconds: float
    runtime_observer_interval_seconds: float
    ready_timeout_seconds: float
    recipe_path: Path


class RuntimeObserver:
    """Background runtime liveness sampler for one tmux target."""

    def __init__(
        self,
        *,
        tool: ToolName,
        session_name: str,
        pane_id: str,
        output_path: Path,
        recorder_started_at: datetime,
        poll_interval_seconds: float,
    ) -> None:
        """Initialize one runtime observer."""

        self.m_tool = tool
        self.m_session_name = session_name
        self.m_pane_id = pane_id
        self.m_output_path = output_path
        self.m_recorder_started_at = recorder_started_at
        self.m_poll_interval_seconds = poll_interval_seconds
        self.m_stop_event = threading.Event()
        self.m_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start background observation."""

        self.m_thread = threading.Thread(
            target=self._run_loop,
            name=f"{self.m_tool}-tracked-tui-runtime-observer",
            daemon=True,
        )
        self.m_thread.start()

    def stop(self) -> None:
        """Stop background observation and join the thread."""

        self.m_stop_event.set()
        if self.m_thread is not None:
            self.m_thread.join(timeout=5.0)

    def _run_loop(self) -> None:
        """Run the sampling loop until stop is requested."""

        while not self.m_stop_event.is_set():
            append_ndjson(
                self.m_output_path,
                sample_runtime_observation(
                    tool=self.m_tool,
                    session_name=self.m_session_name,
                    pane_id=self.m_pane_id,
                    recorder_started_at=self.m_recorder_started_at,
                ).to_payload(),
            )
            time.sleep(self.m_poll_interval_seconds)


def run_recorded_capture(
    *,
    repo_root: Path,
    scenario: ScenarioDefinition,
    demo_config: ResolvedDemoConfig,
    output_root: Path | None,
    cleanup_session: bool,
) -> RecordedCaptureResult:
    """Launch one real tmux session, record it, and persist replay-grade artifacts."""

    ensure_tmux_available()
    run_root = _resolve_recorded_run_root(
        repo_root=repo_root,
        demo_config=demo_config,
        tool=scenario.tool,
        case_id=scenario.scenario_id,
        output_root=output_root,
    )
    if run_root.exists():
        raise RuntimeError(f"Run root already exists: {run_root}")
    run_root.mkdir(parents=True, exist_ok=False)
    recording_root = run_root / "recording"
    runtime_root = run_root / "runtime"
    workdir = run_root / "workdir"
    logs_dir = run_root / "logs"
    runtime_root.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    save_json(run_root / "resolved_demo_config.json", demo_config.to_payload())
    tool_session_name = build_session_name(
        prefix=f"shared-tui-{scenario.tool}", run_id=run_root.name
    )
    initialize_demo_session_ownership(
        demo_id=demo_config.demo_id,
        run_root=run_root,
        workflow_kind="recorded_capture",
        tool=scenario.tool,
    )
    launch: _ResolvedScenarioLaunch | None = None
    selected_recipe_path: Path | None = None
    build_result: Any | None = None
    observed_version: str | None = None
    pane_id: str | None = None
    recorder_payload: dict[str, Any] | None = None
    observer: RuntimeObserver | None = None
    execution_error: BaseException | None = None
    cleanup_error: BaseException | None = None
    try:
        launch = _resolve_scenario_launch(
            scenario=scenario,
            demo_config=demo_config,
        )
        tool_metadata = default_tool_runtime_metadata(
            repo_root=repo_root,
            tool=scenario.tool,
            demo_config=demo_config,
        )
        selected_recipe_path = launch.recipe_path
        recipe = load_brain_recipe(selected_recipe_path)
        if recipe.tool != scenario.tool:
            raise RuntimeError(
                f"Scenario `{scenario.scenario_id}` expects tool `{scenario.tool}`, "
                f"but recipe `{selected_recipe_path}` declares `{recipe.tool}`."
            )
        build_result = build_brain_home(
            BuildRequest(
                agent_def_dir=(repo_root / "tests" / "fixtures" / "agents").resolve(),
                tool=recipe.tool,
                skills=list(recipe.skills),
                config_profile=recipe.config_profile,
                credential_profile=recipe.credential_profile,
                runtime_root=runtime_root,
                mailbox=recipe.mailbox,
                agent_name=recipe.default_agent_name,
                launch_args_override=tool_metadata.launch_args_override,
                operator_prompt_mode=tool_metadata.operator_prompt_mode
                or recipe.operator_prompt_mode,
            )
        )
        observed_version = detect_tool_version(tool=scenario.tool)
        launch_tmux_session(
            session_name=tool_session_name,
            workdir=workdir,
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
        set_demo_session_recorder_run_root(run_root=run_root, recorder_run_root=recording_root)
        upsert_demo_owned_resource(run_root=run_root, role="recorder", session_name=None)
        recorder_payload = start_terminal_record(
            mode="active",
            target_session=tool_session_name,
            target_pane=pane_id,
            tool=scenario.tool,
            run_root=recording_root,
            sample_interval_seconds=launch.sample_interval_seconds,
        )
        recorder_manifest = load_manifest(recording_root / "manifest.json")
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
        observer = RuntimeObserver(
            tool=scenario.tool,
            session_name=tool_session_name,
            pane_id=pane_id,
            output_path=run_root / "runtime_observations.ndjson",
            recorder_started_at=datetime.fromisoformat(recorder_manifest.started_at_utc),
            poll_interval_seconds=launch.runtime_observer_interval_seconds,
        )
        observer.start()
        set_demo_session_ownership_status(run_root=run_root, status="running")
        _execute_scenario(
            scenario=scenario,
            launch=launch,
            tool_session_name=tool_session_name,
            pane_id=pane_id,
            observed_version=observed_version,
            log_path=run_root / "drive_events.ndjson",
        )
    except BaseException as exc:
        execution_error = exc
        try:
            set_demo_session_ownership_status(
                run_root=run_root,
                status="failed",
                last_error=_error_text(exc),
            )
        except FileNotFoundError:
            pass
        raise
    finally:
        if observer is not None:
            observer.stop()
        cleanup_roles: set[DemoOwnedResourceRole] = {"recorder"}
        if execution_error is not None or cleanup_session:
            cleanup_roles.add("tool")
        try:
            reap_demo_owned_resources(
                resolved_resources=resolve_demo_owned_resources(run_root=run_root),
                include_roles=cleanup_roles,
                stop_recorder=True,
                best_effort=execution_error is not None,
            )
        except Exception as exc:  # noqa: BLE001
            cleanup_error = exc
            if execution_error is None:
                try:
                    set_demo_session_ownership_status(
                        run_root=run_root,
                        status="failed",
                        last_error=_error_text(exc),
                    )
                except FileNotFoundError:
                    pass
                raise
        if execution_error is None and cleanup_error is None:
            set_demo_session_ownership_status(run_root=run_root, status="stopped")

    if launch is None or selected_recipe_path is None or build_result is None:
        raise RuntimeError("Recorded capture finished without resolved launch metadata.")
    if pane_id is None or recorder_payload is None:
        raise RuntimeError("Recorded capture finished without initialized runtime metadata.")

    fixture_manifest = RecordedFixtureManifest(
        schema_version=DEMO_PACK_SCHEMA_VERSION,
        case_id=scenario.scenario_id,
        tool=scenario.tool,
        observed_version=observed_version,
        settle_seconds=launch.settle_seconds,
        description=scenario.description,
    )
    save_json(run_root / _FIXTURE_MANIFEST_NAME, fixture_manifest.to_payload())
    save_json(
        run_root / "capture_manifest.json",
        {
            "tool_session_name": tool_session_name,
            "pane_id": pane_id,
            "recording_root": str(recording_root),
            "recorder": recorder_payload,
            "observed_version": observed_version,
            "recipe_path": str(selected_recipe_path),
            "brain_home_path": str(build_result.home_path),
            "brain_manifest_path": str(build_result.manifest_path),
            "resolved_demo_config_path": str(run_root / "resolved_demo_config.json"),
            "effective_launch": {
                "sample_interval_seconds": launch.sample_interval_seconds,
                "runtime_observer_interval_seconds": launch.runtime_observer_interval_seconds,
                "ready_timeout_seconds": launch.ready_timeout_seconds,
                "settle_seconds": launch.settle_seconds,
            },
        },
    )
    return RecordedCaptureResult(
        run_root=run_root,
        recording_root=recording_root,
        scenario_id=scenario.scenario_id,
        tool=scenario.tool,
        observed_version=observed_version,
    )


def validate_recorded_fixture(
    *,
    repo_root: Path,
    demo_config: ResolvedDemoConfig,
    fixture_root: Path,
    output_root: Path | None,
    tool: ToolName | None = None,
    observed_version: str | None = None,
    settle_seconds: float | None = None,
    labels_path: Path | None = None,
    render_review_video: bool = True,
    review_video_fps: float | None = None,
) -> RecordedValidationResult:
    """Validate one recorded fixture against human-authored ground truth."""

    effective_fixture_root = fixture_root.expanduser().resolve()
    fixture_manifest = _load_fixture_manifest(effective_fixture_root)
    effective_tool = tool or (fixture_manifest.tool if fixture_manifest is not None else None)
    if effective_tool is None:
        raise ValueError("tool must be provided when fixture_manifest.json is absent")
    effective_observed_version = (
        observed_version
        if observed_version is not None
        else (fixture_manifest.observed_version if fixture_manifest is not None else None)
    )
    effective_settle_seconds = (
        float(settle_seconds)
        if settle_seconds is not None
        else (fixture_manifest.settle_seconds if fixture_manifest is not None else None)
    )
    if effective_settle_seconds is None:
        raise ValueError("settle_seconds must be provided when fixture_manifest.json is absent")

    case_id = (
        fixture_manifest.case_id if fixture_manifest is not None else effective_fixture_root.name
    )
    run_root = _resolve_recorded_validation_output_root(
        repo_root=repo_root,
        demo_config=demo_config,
        tool=effective_tool,
        case_id=case_id,
        output_root=output_root,
    )
    if run_root.exists():
        raise RuntimeError(f"Run root already exists: {run_root}")
    paths = RecordedValidationPaths.from_run_root(run_root=run_root)
    ensure_directory_layout(paths)
    save_json(paths.resolved_config_path, demo_config.to_payload())

    recording_root = _resolve_recording_root(effective_fixture_root)
    recorder_manifest = _load_recorder_manifest(recording_root)
    capture_sample_interval_seconds = (
        recorder_manifest.sample_interval_seconds
        if recorder_manifest is not None
        else demo_config.evidence.sample_interval_seconds
    )
    effective_review_video_fps = (
        float(review_video_fps)
        if review_video_fps is not None
        else demo_config.presentation.review_video.effective_fps(
            capture_sample_interval_seconds=capture_sample_interval_seconds
        )
    )
    effective_labels_path = (
        labels_path.expanduser().resolve()
        if labels_path is not None
        else _default_labels_path(recording_root=recording_root)
    )
    manifest = RecordedValidationManifest(
        schema_version=DEMO_PACK_SCHEMA_VERSION,
        run_id=run_root.name,
        case_id=case_id,
        tool=effective_tool,
        repo_root=str(repo_root),
        run_root=str(run_root),
        fixture_root=str(effective_fixture_root),
        recording_root=str(recording_root),
        labels_path=str(effective_labels_path),
        resolved_config_path=str(paths.resolved_config_path),
        observed_version=effective_observed_version,
        settle_seconds=effective_settle_seconds,
        review_video_fps=effective_review_video_fps,
        capture_sample_interval_seconds=capture_sample_interval_seconds,
        started_at_utc=now_utc_iso(),
    )
    save_json(paths.manifest_path, manifest.to_payload())

    source_runtime_path = effective_fixture_root / "runtime_observations.ndjson"
    if source_runtime_path.is_file():
        overwrite_ndjson(
            paths.runtime_observations_path, _load_ndjson_payloads(source_runtime_path)
        )
    fixture_inputs = load_fixture_inputs(
        recording_root=recording_root,
        runtime_observations_path=paths.runtime_observations_path
        if paths.runtime_observations_path.is_file()
        else None,
    )
    groundtruth_timeline = expand_labels_to_groundtruth_timeline(
        recording_root=recording_root,
        labels_path=effective_labels_path,
    )
    replay_timeline_rows, replay_events = replay_timeline(
        observations=fixture_inputs.observations,
        tool=effective_tool,
        observed_version=effective_observed_version,
        settle_seconds=effective_settle_seconds,
        input_events=load_input_events(recording_root / "input_events.ndjson"),
    )
    overwrite_ndjson(
        paths.groundtruth_timeline_path,
        [item.to_payload() for item in groundtruth_timeline],
    )
    overwrite_ndjson(
        paths.replay_timeline_path,
        [item.to_payload() for item in replay_timeline_rows],
    )
    overwrite_ndjson(
        paths.replay_events_path,
        [item.to_payload() for item in replay_events],
    )
    comparison, comparison_markdown = compare_timelines(
        groundtruth=groundtruth_timeline,
        replay=replay_timeline_rows,
    )
    save_json(paths.comparison_json_path, comparison.to_payload())
    paths.comparison_markdown_path.write_text(comparison_markdown, encoding="utf-8")

    if render_review_video:
        render_review_frames(
            snapshots=fixture_inputs.snapshots,
            groundtruth_timeline=groundtruth_timeline,
            output_dir=paths.frames_dir,
            fps=effective_review_video_fps,
            width=demo_config.presentation.review_video.width,
            height=demo_config.presentation.review_video.height,
        )
        encode_review_video(
            frames_dir=paths.frames_dir,
            output_path=paths.review_video_path,
            fps=effective_review_video_fps,
            codec=demo_config.presentation.review_video.codec,
            pixel_format=demo_config.presentation.review_video.pixel_format,
        )
        if not demo_config.presentation.review_video.keep_frames:
            _cleanup_review_frames(paths.frames_dir)

    issues = build_recorded_run_issues(
        comparison=comparison,
        recorder_manifest=recorder_manifest,
    )
    issue_paths = write_issue_documents(issues_dir=paths.issues_dir, issues=issues)
    report = build_recorded_summary_report(
        manifest=manifest,
        comparison=comparison,
        recorder_manifest=recorder_manifest,
        issue_paths=issue_paths,
        artifact_paths={
            "resolved demo config": paths.resolved_config_path,
            "ground truth timeline": paths.groundtruth_timeline_path,
            "replay timeline": paths.replay_timeline_path,
            "comparison JSON": paths.comparison_json_path,
            "comparison Markdown": paths.comparison_markdown_path,
            "review video": paths.review_video_path if render_review_video else paths.review_dir,
        },
    )
    paths.report_path.write_text(report, encoding="utf-8")
    return RecordedValidationResult(run_root=run_root, manifest=manifest, comparison=comparison)


def validate_fixture_corpus(
    *,
    repo_root: Path,
    demo_config: ResolvedDemoConfig,
    fixtures_root: Path,
    output_root: Path | None,
    render_review_video: bool,
    review_video_fps: float | None,
) -> list[RecordedValidationResult]:
    """Validate every fixture manifest found under one corpus root."""

    results: list[RecordedValidationResult] = []
    for manifest_path in sorted(fixtures_root.rglob(_FIXTURE_MANIFEST_NAME)):
        fixture_root = manifest_path.parent
        case_output_root = output_root / fixture_root.name if output_root is not None else None
        results.append(
            validate_recorded_fixture(
                repo_root=repo_root,
                demo_config=demo_config,
                fixture_root=fixture_root,
                output_root=case_output_root,
                render_review_video=render_review_video,
                review_video_fps=review_video_fps,
            )
        )
    return results


def _resolve_recorded_run_root(
    *,
    repo_root: Path,
    demo_config: ResolvedDemoConfig,
    tool: ToolName,
    case_id: str,
    output_root: Path | None,
) -> Path:
    """Return the run root for one recorded capture."""

    if output_root is not None:
        return output_root.expanduser().resolve()
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    return (demo_config.recorded_root_path() / tool / f"{case_id}-{stamp}").resolve()


def _resolve_recorded_validation_output_root(
    *,
    repo_root: Path,
    demo_config: ResolvedDemoConfig,
    tool: ToolName,
    case_id: str,
    output_root: Path | None,
) -> Path:
    """Return the run root for one recorded validation."""

    if output_root is not None:
        return output_root.expanduser().resolve()
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    del repo_root
    return (demo_config.recorded_root_path() / tool / case_id / f"validation-{stamp}").resolve()


def _resolve_recording_root(fixture_root: Path) -> Path:
    """Return the recording root inside one fixture or run root."""

    recording_root = fixture_root / "recording"
    if recording_root.is_dir():
        return recording_root
    return fixture_root


def _default_labels_path(*, recording_root: Path) -> Path:
    """Return the default labels path for one recording root."""

    return recording_root / "labels.json"


def _load_fixture_manifest(fixture_root: Path) -> RecordedFixtureManifest | None:
    """Load fixture metadata when present."""

    path = fixture_root / _FIXTURE_MANIFEST_NAME
    if not path.is_file():
        return None
    return RecordedFixtureManifest.from_payload(json.loads(path.read_text(encoding="utf-8")))


def _execute_scenario(
    *,
    scenario: ScenarioDefinition,
    launch: _ResolvedScenarioLaunch,
    tool_session_name: str,
    pane_id: str,
    observed_version: str | None,
    log_path: Path,
) -> None:
    """Execute all scenario steps sequentially."""

    detector = (
        DetectorProfileRegistry.default()
        .resolve(
            app_id=app_id_from_tool(tool=scenario.tool),
            observed_version=observed_version,
        )
        .profile
    )
    for step in scenario.steps:
        append_ndjson(
            log_path,
            {
                "event": "step_started",
                "action": step.action,
                "name": step.name,
                "ts_utc": now_utc_iso(),
            },
        )
        if step.action == "wait_for_ready":
            _wait_for_ready(
                pane_id=pane_id,
                detector=detector,
                timeout_seconds=step.timeout_seconds or launch.ready_timeout_seconds,
            )
        elif step.action == "wait_for_interrupted_ready":
            _wait_for_interrupted_ready(
                pane_id=pane_id,
                detector=detector,
                timeout_seconds=step.timeout_seconds or launch.ready_timeout_seconds,
            )
        elif step.action == "wait_seconds":
            time.sleep(step.seconds or 0.0)
        elif step.action == "wait_for_pattern":
            _wait_for_pattern(
                pane_id=pane_id,
                pattern=step.pattern or "",
                timeout_seconds=step.timeout_seconds or 30.0,
            )
        elif step.action == "send_text":
            _send_text(
                session_name=tool_session_name,
                pane_id=pane_id,
                text=step.text or "",
                submit=step.submit,
            )
        elif step.action == "send_key":
            key = step.key or "Enter"
            _send_sequence(
                session_name=tool_session_name,
                pane_id=pane_id,
                sequence=f"<[{key}]>",
            )
        elif step.action == "interrupt_turn":
            _interrupt_turn(
                tool=scenario.tool,
                session_name=tool_session_name,
                pane_id=pane_id,
            )
        elif step.action == "close_tool":
            _close_tool(
                tool=scenario.tool,
                session_name=tool_session_name,
                pane_id=pane_id,
            )
        elif step.action == "kill_session":
            kill_tmux_session_if_exists(session_name=tool_session_name)
        elif step.action == "kill_supported_process":
            kill_supported_process_for_pane(
                tool=scenario.tool,
                session_name=tool_session_name,
                pane_id=pane_id,
            )
        else:  # pragma: no cover - parser guards valid actions
            raise ValueError(f"Unsupported scenario action: {step.action}")
        append_ndjson(
            log_path,
            {
                "event": "step_completed",
                "action": step.action,
                "name": step.name,
                "ts_utc": now_utc_iso(),
            },
        )


def _send_sequence(*, session_name: str, pane_id: str, sequence: str) -> None:
    """Deliver one authoritative managed-input sequence to the target pane."""

    segments = parse_tmux_control_input(sequence=sequence)
    send_tmux_control_input(target=pane_id, segments=segments)
    append_managed_control_input_for_tmux_session(
        session_name=session_name,
        sequence=sequence,
        escape_special_keys=False,
        tmux_target=pane_id,
    )


def _send_text(*, session_name: str, pane_id: str, text: str, submit: bool) -> None:
    """Deliver typed text, optionally followed by a slightly delayed submit key."""

    if text:
        _send_sequence(
            session_name=session_name,
            pane_id=pane_id,
            sequence=text,
        )
    if not submit:
        return
    time.sleep(_SUBMIT_KEY_DELAY_SECONDS)
    _send_sequence(
        session_name=session_name,
        pane_id=pane_id,
        sequence="<[Enter]>",
    )


def _interrupt_turn(*, tool: ToolName, session_name: str, pane_id: str) -> None:
    """Deliver one tool-owned interruption recipe to the target pane."""

    for sequence in _INTERRUPT_SEQUENCE_BY_TOOL[tool]:
        _send_sequence(
            session_name=session_name,
            pane_id=pane_id,
            sequence=sequence,
        )


def _close_tool(*, tool: ToolName, session_name: str, pane_id: str) -> None:
    """Request one best-effort graceful close before falling back to process kill."""

    for sequence in _CLOSE_SEQUENCE_BY_TOOL[tool]:
        _send_sequence(
            session_name=session_name,
            pane_id=pane_id,
            sequence=sequence,
        )
        if _wait_for_supported_process_exit(
            tool=tool,
            session_name=session_name,
            pane_id=pane_id,
            timeout_seconds=_GRACEFUL_CLOSE_TIMEOUT_SECONDS,
        ):
            return
    kill_supported_process_for_pane(
        tool=tool,
        session_name=session_name,
        pane_id=pane_id,
    )


def _wait_for_supported_process_exit(
    *,
    tool: ToolName,
    session_name: str,
    pane_id: str,
    timeout_seconds: float,
) -> bool:
    """Return whether the supported tool process exited within the timeout."""

    deadline = time.monotonic() + timeout_seconds
    started_at = datetime.now().astimezone()
    while time.monotonic() < deadline:
        observation = sample_runtime_observation(
            tool=tool,
            session_name=session_name,
            pane_id=pane_id,
            recorder_started_at=started_at,
        )
        if not observation.session_exists:
            return True
        if not observation.pane_exists or observation.pane_dead:
            return True
        if not observation.supported_process_alive:
            return True
        time.sleep(_GRACEFUL_CLOSE_POLL_SECONDS)
    return False


def _wait_for_ready(*, pane_id: str, detector: Any, timeout_seconds: float) -> None:
    """Wait until the detector reports a ready posture."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        output = capture_visible_pane_text(pane_id=pane_id)
        signals = detector.detect(output_text=output)
        if signals.ready_posture == "yes":
            return
        time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for ready posture in {pane_id}")


def _wait_for_interrupted_ready(*, pane_id: str, detector: Any, timeout_seconds: float) -> None:
    """Wait until the detector reports a stable interrupted-ready posture."""

    deadline = time.monotonic() + timeout_seconds
    consecutive_matches = 0
    while time.monotonic() < deadline:
        output = capture_visible_pane_text(pane_id=pane_id)
        signals = detector.detect(output_text=output)
        interrupted_ready = (
            signals.interrupted and signals.ready_posture == "yes" and not signals.active_evidence
        )
        if interrupted_ready:
            consecutive_matches += 1
            if consecutive_matches >= _INTERRUPTED_READY_STABLE_POLLS:
                return
        else:
            consecutive_matches = 0
        time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for interrupted ready posture in {pane_id}")


def _wait_for_pattern(*, pane_id: str, pattern: str, timeout_seconds: float) -> None:
    """Wait until a stripped pane surface matches a regex pattern."""

    compiled = re.compile(pattern)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        output = _ANSI_RE.sub("", capture_visible_pane_text(pane_id=pane_id))
        if compiled.search(output):
            return
        time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for pattern `{pattern}` in {pane_id}")


def _load_recorder_manifest(recording_root: Path) -> TerminalRecordManifest | None:
    """Load the recorder manifest when present."""

    path = recording_root / "manifest.json"
    if not path.is_file():
        return None
    return load_manifest(path)


def _load_ndjson_payloads(path: Path) -> list[dict[str, Any]]:
    """Load raw NDJSON payloads from disk."""

    payloads: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        payloads.append(json.loads(stripped))
    return payloads


def _error_text(error: BaseException) -> str:
    """Return a stable error string for recorded-capture ownership state."""

    message = str(error).strip()
    if message:
        return message
    return error.__class__.__name__


def _resolve_scenario_launch(
    *,
    scenario: ScenarioDefinition,
    demo_config: ResolvedDemoConfig,
) -> _ResolvedScenarioLaunch:
    """Resolve effective launch settings for one capture scenario."""

    tool_config = demo_config.tool_config(tool=scenario.tool)
    recipe_path = (
        Path(scenario.launch.recipe_path).expanduser().resolve()
        if scenario.launch.recipe_path is not None
        else demo_config.resolve_repo_path(tool_config.recipe_path)
    )
    return _ResolvedScenarioLaunch(
        settle_seconds=(
            scenario.launch.settle_seconds
            if scenario.launch.settle_seconds is not None
            else demo_config.semantics.settle_seconds
        ),
        sample_interval_seconds=(
            scenario.launch.sample_interval_seconds
            if scenario.launch.sample_interval_seconds is not None
            else demo_config.evidence.sample_interval_seconds
        ),
        runtime_observer_interval_seconds=(
            scenario.launch.runtime_observer_interval_seconds
            if scenario.launch.runtime_observer_interval_seconds is not None
            else demo_config.evidence.runtime_observer_interval_seconds
        ),
        ready_timeout_seconds=(
            scenario.launch.ready_timeout_seconds
            if scenario.launch.ready_timeout_seconds is not None
            else demo_config.evidence.ready_timeout_seconds
        ),
        recipe_path=recipe_path,
    )


def _cleanup_review_frames(frames_dir: Path) -> None:
    """Remove staged review frames after encoding when configured."""

    if frames_dir.is_dir():
        shutil.rmtree(frames_dir)
