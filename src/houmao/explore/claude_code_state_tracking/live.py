"""Live tmux capture workflow for the Claude Code state-tracking explore harness."""

from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    ensure_tmux_available,
    kill_tmux_session,
    tmux_session_exists,
)
from houmao.explore.claude_code_state_tracking.detectors import select_claude_detector
from houmao.explore.claude_code_state_tracking.models import (
    HarnessPaths,
    RuntimeObservation,
    append_ndjson,
    save_json,
)
from houmao.explore.claude_code_state_tracking.runtime_support import (
    detect_claude_version,
    ensure_command_available,
    find_supported_process_pid,
    launch_tmux_session,
    now_utc_iso,
    process_is_alive,
    query_pane_state,
    resolve_active_pane_id,
    send_key,
    send_text,
    wait_for_pattern,
    wait_for_ready,
)
from houmao.explore.claude_code_state_tracking.scenario import (
    FaultInjectionSpec,
    ScenarioDefinition,
)
from houmao.terminal_record.service import (
    start_terminal_record,
    status_terminal_record,
    stop_terminal_record,
)


DEFAULT_RUN_ROOT_PARENT = Path("tmp/explore/claude-code-state-tracking")


@dataclass(frozen=True)
class LiveCaptureResult:
    """Summary of one completed live-capture run."""

    run_root: Path
    scenario_id: str
    tmux_session_name: str
    pane_id: str
    terminal_record_run_root: Path
    observed_version: str | None


class RuntimeObserver:
    """Background runtime liveness sampler for one tmux target."""

    def __init__(
        self, *, session_name: str, pane_id: str, output_path: Path, poll_interval_seconds: float
    ) -> None:
        """Initialize one runtime observer."""

        self.m_session_name = session_name
        self.m_pane_id = pane_id
        self.m_output_path = output_path
        self.m_poll_interval_seconds = poll_interval_seconds
        self.m_started_at = time.monotonic()
        self.m_stop_event = threading.Event()
        self.m_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start background observation."""

        self.m_thread = threading.Thread(
            target=self._run_loop, name="claude-runtime-observer", daemon=True
        )
        self.m_thread.start()

    def stop(self) -> None:
        """Stop background observation and join the thread."""

        self.m_stop_event.set()
        if self.m_thread is not None:
            self.m_thread.join(timeout=5.0)

    def _run_loop(self) -> None:
        """Run the observation loop until stop is requested."""

        while not self.m_stop_event.is_set():
            append_ndjson(self.m_output_path, self._sample().to_payload())
            time.sleep(self.m_poll_interval_seconds)

    def _sample(self) -> RuntimeObservation:
        """Capture one runtime liveness observation."""

        session_exists = tmux_session_exists(session_name=self.m_session_name)
        pane_exists = False
        pane_dead = False
        pane_pid: int | None = None
        pane_pid_alive = False
        supported_process_pid: int | None = None
        supported_process_alive = False
        if session_exists:
            pane_state = query_pane_state(session_name=self.m_session_name, pane_id=self.m_pane_id)
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
            elapsed_seconds=time.monotonic() - self.m_started_at,
            session_exists=session_exists,
            pane_exists=pane_exists,
            pane_dead=pane_dead,
            pane_pid=pane_pid,
            pane_pid_alive=pane_pid_alive,
            supported_process_pid=supported_process_pid,
            supported_process_alive=supported_process_alive,
        )


def run_live_capture(
    *,
    repo_root: Path,
    scenario: ScenarioDefinition,
    output_root: Path | None,
    cleanup_session: bool,
) -> LiveCaptureResult:
    """Run one live scenario capture end to end."""

    ensure_tmux_available()
    ensure_command_available("claude-yunwu")
    if scenario.launch.fault_injection is not None:
        ensure_command_available("strace")

    run_root = _resolve_run_root(
        repo_root=repo_root,
        scenario_id=scenario.scenario_id,
        output_root=output_root,
    )
    if run_root.exists():
        shutil.rmtree(run_root)
    paths = HarnessPaths.from_run_root(run_root=run_root)
    for directory in (
        run_root,
        paths.artifacts_dir,
        paths.logs_dir,
        paths.analysis_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    workdir = run_root / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)

    observed_version = detect_claude_version()
    save_json(
        paths.artifacts_dir / "observed_version.json",
        {
            "claude_version": observed_version,
            "scenario": scenario.to_payload(),
        },
    )

    session_name = f"cc-track-{run_root.name}"[:60]
    launch_script = _write_launch_script(
        run_root=run_root,
        workdir=workdir,
        fault_injection=scenario.launch.fault_injection,
    )
    launch_tmux_session(session_name=session_name, workdir=workdir, launch_script=launch_script)
    pane_id = resolve_active_pane_id(session_name=session_name)

    terminal_record_payload = start_terminal_record(
        mode="passive",
        target_session=session_name,
        target_pane=pane_id,
        tool="claude",
        run_root=paths.terminal_record_run_root,
        sample_interval_seconds=scenario.launch.sample_interval_seconds,
    )
    observer = RuntimeObserver(
        session_name=session_name,
        pane_id=pane_id,
        output_path=paths.runtime_observations_path,
        poll_interval_seconds=scenario.launch.sample_interval_seconds,
    )
    observer.start()
    drive_context = _DriveContext(
        repo_root=repo_root,
        run_root=run_root,
        session_name=session_name,
        pane_id=pane_id,
        drive_events_path=paths.drive_events_path,
        observed_version=observed_version,
    )
    try:
        _execute_scenario(scenario=scenario, drive_context=drive_context)
    finally:
        observer.stop()
        stop_terminal_record(run_root=paths.terminal_record_run_root)
        if cleanup_session and tmux_session_exists(session_name=session_name):
            try:
                kill_tmux_session(session_name=session_name)
            except TmuxCommandError:
                pass

    save_json(
        paths.capture_manifest_path,
        {
            "scenario": scenario.to_payload(),
            "run_root": str(run_root),
            "workdir": str(workdir),
            "tmux_session_name": session_name,
            "target_pane_id": pane_id,
            "terminal_record": terminal_record_payload,
            "terminal_record_status": status_terminal_record(
                run_root=paths.terminal_record_run_root
            ),
            "observed_version": observed_version,
        },
    )
    return LiveCaptureResult(
        run_root=run_root,
        scenario_id=scenario.scenario_id,
        tmux_session_name=session_name,
        pane_id=pane_id,
        terminal_record_run_root=paths.terminal_record_run_root,
        observed_version=observed_version,
    )


@dataclass
class _DriveContext:
    """Mutable driver context for one live scenario run."""

    repo_root: Path
    run_root: Path
    session_name: str
    pane_id: str
    drive_events_path: Path
    observed_version: str | None


def _execute_scenario(*, scenario: ScenarioDefinition, drive_context: _DriveContext) -> None:
    """Execute all scenario steps sequentially."""

    detector = select_claude_detector(observed_version=drive_context.observed_version)
    for step in scenario.steps:
        append_ndjson(
            drive_context.drive_events_path,
            {
                "event": "step_started",
                "name": step.name,
                "action": step.action,
                "ts_utc": now_utc_iso(),
            },
        )
        if step.action == "wait_for_ready":
            wait_for_ready(
                pane_id=drive_context.pane_id,
                detector=detector,
                timeout_seconds=step.timeout_seconds or scenario.launch.ready_timeout_seconds,
            )
        elif step.action == "wait_seconds":
            time.sleep(step.seconds or 0.0)
        elif step.action == "wait_for_pattern":
            wait_for_pattern(
                pane_id=drive_context.pane_id,
                pattern=step.pattern or "",
                timeout_seconds=step.timeout_seconds or 30.0,
            )
        elif step.action == "send_text":
            send_text(
                pane_id=drive_context.pane_id,
                text=step.text or "",
                submit=step.submit,
            )
        elif step.action == "send_key":
            send_key(pane_id=drive_context.pane_id, key=step.key or "Enter")
        elif step.action == "attach_fault_injection":
            if step.fault_injection is None:
                raise ValueError("attach_fault_injection step requires fault_injection")
            _attach_fault_injection(
                drive_context=drive_context,
                spec=step.fault_injection,
            )
        elif step.action == "kill_launch_process":
            _kill_launch_process(drive_context=drive_context)
        elif step.action == "kill_session":
            kill_tmux_session(session_name=drive_context.session_name)
        else:  # pragma: no cover - safeguarded by scenario parser
            raise ValueError(f"Unsupported action: {step.action}")
        append_ndjson(
            drive_context.drive_events_path,
            {
                "event": "step_completed",
                "name": step.name,
                "action": step.action,
                "ts_utc": now_utc_iso(),
            },
        )


def _resolve_run_root(*, repo_root: Path, scenario_id: str, output_root: Path | None) -> Path:
    """Return the resolved run root for one live scenario."""

    if output_root is not None:
        return output_root.expanduser().resolve()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return (repo_root / DEFAULT_RUN_ROOT_PARENT / f"{stamp}-{scenario_id}").resolve()


def _write_launch_script(
    *,
    run_root: Path,
    workdir: Path,
    fault_injection: FaultInjectionSpec | None,
) -> Path:
    """Write one tmux launch script for the Claude session."""

    launch_dir = run_root / "launch"
    launch_dir.mkdir(parents=True, exist_ok=True)
    strace_log = run_root / "logs" / "launch-strace.log"
    command = "claude-yunwu"
    if fault_injection is not None and fault_injection.mode == "launch_strace_inject":
        command = (
            "strace -f "
            f"-o {shlex.quote(str(strace_log))} "
            f"-e inject={shlex.quote(f'{fault_injection.syscall}:error={fault_injection.error}:when={fault_injection.when}')}"
            " claude-yunwu"
        )
    script = launch_dir / "launch_claude.sh"
    script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"cd {shlex.quote(str(workdir))}",
                f"exec {command}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def _attach_fault_injection(*, drive_context: _DriveContext, spec: FaultInjectionSpec) -> None:
    """Attach one `strace --inject` fault to the running Claude process."""

    target_pid = _resolve_fault_target_pid(
        session_name=drive_context.session_name, pane_id=drive_context.pane_id
    )
    if target_pid is None:
        raise RuntimeError("failed to resolve target pid for fault injection")
    fault_log = drive_context.run_root / "logs" / f"attach-{spec.syscall}-{spec.error}.log"
    process = subprocess.Popen(
        [
            "strace",
            "-f",
            "-o",
            str(fault_log),
            "-p",
            str(target_pid),
            "-e",
            f"inject={spec.syscall}:error={spec.error}:when={spec.when}",
        ],
        cwd=drive_context.repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        text=True,
    )
    append_ndjson(
        drive_context.drive_events_path,
        {
            "event": "fault_injection_attached",
            "target_pid": target_pid,
            "controller_pid": process.pid,
            "spec": spec.to_payload(),
            "ts_utc": now_utc_iso(),
        },
    )


def _kill_launch_process(*, drive_context: _DriveContext) -> None:
    """Kill the launch or supported Claude process for diagnostics testing."""

    target_pid = _resolve_fault_target_pid(
        session_name=drive_context.session_name, pane_id=drive_context.pane_id
    )
    if target_pid is None:
        raise RuntimeError("failed to resolve launch process pid")
    os.kill(target_pid, signal.SIGKILL)
    append_ndjson(
        drive_context.drive_events_path,
        {
            "event": "process_killed",
            "target_pid": target_pid,
            "signal": "SIGKILL",
            "ts_utc": now_utc_iso(),
        },
    )


def _resolve_fault_target_pid(*, session_name: str, pane_id: str) -> int | None:
    """Return the supported Claude pid when available, otherwise the pane pid."""

    pane_state = query_pane_state(session_name=session_name, pane_id=pane_id)
    if pane_state is None:
        return None
    pane_pid = pane_state["pane_pid"]
    if pane_pid is None:
        return None
    supported_pid = find_supported_process_pid(root_pid=pane_pid)
    return supported_pid or pane_pid
