"""Recorded capture and validation workflow for the tracked-TUI demo pack."""

from __future__ import annotations

import json
import re
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
from houmao.terminal_record.service import start_terminal_record, stop_terminal_record

from .comparison import TimelineComparison, compare_timelines
from .groundtruth import expand_labels_to_groundtruth_timeline, load_fixture_inputs
from .models import (
    DEMO_PACK_SCHEMA_VERSION,
    DEFAULT_RECORDED_RUN_ROOT_PARENT,
    DEFAULT_REVIEW_VIDEO_FPS,
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
from .reporting import (
    build_recorded_run_issues,
    build_recorded_summary_report,
    write_issue_documents,
)
from .review_video import encode_review_video, render_review_frames
from .scenario import ScenarioDefinition
from .tooling import (
    build_session_name,
    capture_pane_text,
    default_tool_runtime_metadata,
    detect_tool_version,
    kill_tmux_session_if_exists,
    launch_tmux_session,
    now_utc_iso,
    resolve_active_pane_id,
    sample_runtime_observation,
)


_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_FIXTURE_MANIFEST_NAME = "fixture_manifest.json"


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
    output_root: Path | None,
    cleanup_session: bool,
) -> RecordedCaptureResult:
    """Launch one real tmux session, record it, and persist replay-grade artifacts."""

    ensure_tmux_available()
    run_root = _resolve_recorded_run_root(
        repo_root=repo_root,
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

    tool_metadata = default_tool_runtime_metadata(repo_root=repo_root, tool=scenario.tool)
    selected_recipe_path = (
        Path(scenario.launch.recipe_path).expanduser().resolve()
        if scenario.launch.recipe_path is not None
        else tool_metadata.interactive_watch_recipe_path
    )
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
        )
    )
    observed_version = detect_tool_version(tool=scenario.tool)
    tool_session_name = build_session_name(
        prefix=f"shared-tui-{scenario.tool}", run_id=run_root.name
    )
    launch_tmux_session(
        session_name=tool_session_name,
        workdir=workdir,
        launch_script=build_result.launch_helper_path,
    )
    pane_id = resolve_active_pane_id(session_name=tool_session_name)
    recorder_payload = start_terminal_record(
        mode="active",
        target_session=tool_session_name,
        target_pane=pane_id,
        tool=scenario.tool,
        run_root=recording_root,
        sample_interval_seconds=scenario.launch.sample_interval_seconds,
    )
    recorder_manifest = load_manifest(recording_root / "manifest.json")
    observer = RuntimeObserver(
        tool=scenario.tool,
        session_name=tool_session_name,
        pane_id=pane_id,
        output_path=run_root / "runtime_observations.ndjson",
        recorder_started_at=datetime.fromisoformat(recorder_manifest.started_at_utc),
        poll_interval_seconds=scenario.launch.sample_interval_seconds,
    )
    observer.start()
    try:
        _execute_scenario(
            scenario=scenario,
            tool_session_name=tool_session_name,
            pane_id=pane_id,
            observed_version=observed_version,
            log_path=run_root / "drive_events.ndjson",
        )
    finally:
        observer.stop()
        stop_terminal_record(run_root=recording_root)
        if cleanup_session:
            kill_tmux_session_if_exists(session_name=tool_session_name)

    fixture_manifest = RecordedFixtureManifest(
        schema_version=DEMO_PACK_SCHEMA_VERSION,
        case_id=scenario.scenario_id,
        tool=scenario.tool,
        observed_version=observed_version,
        settle_seconds=scenario.launch.settle_seconds,
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
    fixture_root: Path,
    output_root: Path | None,
    tool: ToolName | None = None,
    observed_version: str | None = None,
    settle_seconds: float | None = None,
    labels_path: Path | None = None,
    render_review_video: bool = True,
    review_video_fps: int = DEFAULT_REVIEW_VIDEO_FPS,
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
        tool=effective_tool,
        case_id=case_id,
        output_root=output_root,
    )
    if run_root.exists():
        raise RuntimeError(f"Run root already exists: {run_root}")
    paths = RecordedValidationPaths.from_run_root(run_root=run_root)
    ensure_directory_layout(paths)

    recording_root = _resolve_recording_root(effective_fixture_root)
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
        observed_version=effective_observed_version,
        settle_seconds=effective_settle_seconds,
        review_video_fps=review_video_fps,
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
            fps=review_video_fps,
        )
        encode_review_video(
            frames_dir=paths.frames_dir,
            output_path=paths.review_video_path,
            fps=review_video_fps,
        )

    recorder_manifest = _load_recorder_manifest(recording_root)
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
    fixtures_root: Path,
    output_root: Path | None,
    render_review_video: bool,
    review_video_fps: int,
) -> list[RecordedValidationResult]:
    """Validate every fixture manifest found under one corpus root."""

    results: list[RecordedValidationResult] = []
    for manifest_path in sorted(fixtures_root.rglob(_FIXTURE_MANIFEST_NAME)):
        fixture_root = manifest_path.parent
        case_output_root = output_root / fixture_root.name if output_root is not None else None
        results.append(
            validate_recorded_fixture(
                repo_root=repo_root,
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
    tool: ToolName,
    case_id: str,
    output_root: Path | None,
) -> Path:
    """Return the run root for one recorded capture."""

    if output_root is not None:
        return output_root.expanduser().resolve()
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    return (repo_root / DEFAULT_RECORDED_RUN_ROOT_PARENT / tool / f"{case_id}-{stamp}").resolve()


def _resolve_recorded_validation_output_root(
    *,
    repo_root: Path,
    tool: ToolName,
    case_id: str,
    output_root: Path | None,
) -> Path:
    """Return the run root for one recorded validation."""

    if output_root is not None:
        return output_root.expanduser().resolve()
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    return (
        repo_root / DEFAULT_RECORDED_RUN_ROOT_PARENT / tool / case_id / f"validation-{stamp}"
    ).resolve()


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
                timeout_seconds=step.timeout_seconds or scenario.launch.ready_timeout_seconds,
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
            sequence = step.text or ""
            if step.submit:
                sequence += "<[Enter]>"
            _send_sequence(
                session_name=tool_session_name,
                pane_id=pane_id,
                sequence=sequence,
            )
        elif step.action == "send_key":
            key = step.key or "Enter"
            _send_sequence(
                session_name=tool_session_name,
                pane_id=pane_id,
                sequence=f"<[{key}]>",
            )
        elif step.action == "kill_session":
            kill_tmux_session_if_exists(session_name=tool_session_name)
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


def _wait_for_ready(*, pane_id: str, detector: Any, timeout_seconds: float) -> None:
    """Wait until the detector reports a ready posture."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        output = capture_pane_text(pane_id=pane_id)
        signals = detector.detect(output_text=output)
        if signals.ready_posture == "yes":
            return
        time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for ready posture in {pane_id}")


def _wait_for_pattern(*, pane_id: str, pattern: str, timeout_seconds: float) -> None:
    """Wait until a stripped pane surface matches a regex pattern."""

    compiled = re.compile(pattern)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        output = _ANSI_RE.sub("", capture_pane_text(pane_id=pane_id))
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
