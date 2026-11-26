"""Shared headless CLI runner for JSON/JSONL streaming turns."""

from __future__ import annotations

import errno
import ctypes
from contextlib import contextmanager
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
import json
import os
import select
import shlex
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from houmao.execution.tmux import tmux_command as run_tmux_shared

from houmao.execution.tmux import TmuxServer

from houmao.agents.realm_controller.backends.dispatch_control import (
    HeadlessDispatchControl,
    _dispatch_origin_birth_token,
)
from houmao.agents.realm_controller.backends.dsh_acp_connection import signal_dsh_native_process
from houmao.agents.realm_controller.backends.dsh_diagnostics import (
    dsh_diagnostic_secrets,
    dsh_diagnostic_tail,
    sanitize_dsh_diagnostic,
)
from houmao.agents.realm_controller.backends.hermes_headless_protocol import (
    reconcile_hermes_headless_turn,
)
from houmao.agents.realm_controller.usage_support import (
    headless_artifact_process_alive,
    persist_terminal_evidence,
    write_usage_json,
)
from houmao.agents.realm_controller.usage_adapters.dsh import (
    DSH_MAX_JOURNAL_ROW_BYTES,
    inspect_dsh_journal,
    select_dsh_journal,
)

from ..errors import BackendExecutionError
from ..models import SessionControlResult, SessionEvent
from .headless_output import (
    CanonicalHeadlessEvent,
    canonical_headless_event_artifact_path,
    canonical_headless_events_from_provider_output,
    canonical_headless_events_to_session_events,
    load_preferred_canonical_headless_events,
)
from .headless_output import (
    HeadlessDisplayDetail,
    HeadlessDisplayStyle,
    HeadlessProvider,
)
from .tmux_runtime import (
    HEADLESS_AGENT_WINDOW_NAME,
    TmuxCommandError,
    resolve_primary_tmux_surface as resolve_primary_tmux_surface_shared,
    tmux_error_detail as tmux_error_detail_shared,
    wait_for_tmux_signal as wait_for_tmux_signal_shared,
)

_DEFAULT_COMPLETION_TIMEOUT_SECONDS = 300.0
_DEFAULT_COMPLETION_POLL_INTERVAL_SECONDS = 0.1


class HeadlessTurnWaitTimeout(BackendExecutionError):
    """Indicate controller wait expiry while owned execution may remain active."""


@dataclass(frozen=True)
class HeadlessProcessMetadata:
    """Durable process identity for one tmux-backed headless turn."""

    runner_pid: int | None = None
    child_pid: int | None = None
    launched_at_utc: str | None = None
    runner_birth_token: str | None = None
    child_birth_token: str | None = None
    child_isolated_group: bool = False


@dataclass(frozen=True)
class HeadlessRunResult:
    """Result for one headless CLI invocation."""

    events: list[SessionEvent]
    stderr: str
    returncode: int
    session_id: str | None
    stdout_path: Path | None = None
    stderr_path: Path | None = None
    status_path: Path | None = None
    process_path: Path | None = None
    canonical_path: Path | None = None
    process_metadata: HeadlessProcessMetadata | None = None
    completion_source: str = "direct_process"
    turn_id: str | None = None
    started_at_utc: str | None = None
    completed_at_utc: str | None = None
    wall_time_ms: float | None = None
    interrupted: bool = False


class HeadlessCliRunner:
    """Run one headless turn and stream parsed events."""

    def __init__(self) -> None:
        self._active_process: subprocess.Popen[str] | None = None
        self._active_tmux_session_name: str | None = None
        self._active_tmux_pane_target: str | None = None
        self._active_tmux_wait_signal: str | None = None
        self._active_process_path: Path | None = None
        self._active_process_metadata: HeadlessProcessMetadata | None = None
        self.m_interrupt_requested: bool = False
        self.m_active_turn_dir: Path | None = None
        self.m_dispatch_control: HeadlessDispatchControl | None = None
        self.m_active_provider: HeadlessProvider | None = None

    def set_dispatch_control(self, control: HeadlessDispatchControl | None) -> None:
        """Set a request-scoped launch guard without changing ordinary turns."""

        self.m_dispatch_control = control

    def restore_dsh_attempt(self, *, turn_dir: Path, tmux_session_name: str | None) -> None:
        """Recover a caller-validated native attempt's exact live driver identity.

        Parameters
        ----------
        turn_dir:
            Managed artifact directory whose native binding and execution
            generation the DSH session has already verified.
        tmux_session_name:
            Existing managed envelope identity. No pane or process is created.
        """

        self.m_active_provider = "dsh"
        if (turn_dir / "exitcode").exists():
            raise BackendExecutionError("DSH attempt already has terminal evidence")
        try:
            metadata = load_headless_process_metadata(process_path=turn_dir / "process.json")
        except (OSError, ValueError) as exc:
            raise BackendExecutionError("DSH owned driver identity is unavailable") from exc
        if (
            metadata.child_pid is None
            or not metadata.child_birth_token
            or _dispatch_origin_birth_token(metadata.child_pid) != metadata.child_birth_token
        ):
            raise BackendExecutionError("DSH owned driver identity is unavailable")
        self.m_active_turn_dir = turn_dir
        self._active_process_path = turn_dir / "process.json"
        self._active_process_metadata = metadata
        self._active_tmux_session_name = tmux_session_name
        # Supervisory panes never substitute for native cancellation authority.
        self._active_tmux_pane_target = None
        self._active_tmux_wait_signal = None

    def _require_dispatch_allowed(self) -> None:
        """Check permission immediately before changing or launching execution."""

        if self.m_dispatch_control is not None:
            self.m_dispatch_control.require_allowed()

    def run(
        self,
        *,
        command: list[str],
        env: dict[str, str],
        cwd: Path,
        turn_index: int,
        output_format: str,
        provider: HeadlessProvider | None = None,
        display_style: HeadlessDisplayStyle = "plain",
        display_detail: HeadlessDisplayDetail = "concise",
        tmux_session_name: str | None = None,
        tmux_pane_target: str | None = None,
        turn_artifacts_root: Path | None = None,
        turn_artifact_dir_name: str | None = None,
        completion_timeout_seconds: float = _DEFAULT_COMPLETION_TIMEOUT_SECONDS,
        completion_poll_interval_seconds: float = (_DEFAULT_COMPLETION_POLL_INTERVAL_SECONDS),
        replace_environment: bool = False,
    ) -> HeadlessRunResult:
        """Execute a headless command and parse events."""

        if output_format not in {"json", "stream-json", "dsh-cli"}:
            raise BackendExecutionError(f"Unsupported headless output format: {output_format}")
        if output_format == "dsh-cli" and (provider != "dsh" or tmux_session_name is None):
            raise BackendExecutionError("Native DSH requires its managed headless bridge")

        self._require_dispatch_allowed()

        turn_id = turn_artifact_dir_name or f"turn-{uuid.uuid4().hex[:12]}"
        if not turn_id or Path(turn_id).name != turn_id or turn_id in {".", ".."}:
            raise BackendExecutionError("Headless turn ID must be one directory name")
        self.m_interrupt_requested = False
        self.m_active_provider = provider
        self.m_active_turn_dir = (
            (turn_artifacts_root / turn_id).resolve() if turn_artifacts_root is not None else None
        )
        if self.m_active_turn_dir is not None and any(
            (self.m_active_turn_dir / name).exists()
            for name in ("stdout.jsonl", "exitcode", "usage-final.json")
        ):
            raise BackendExecutionError("Headless turn artifact ID has already been used")
        started_at_utc = datetime.now(UTC).isoformat()
        started_monotonic = time.monotonic()
        if tmux_session_name is None:
            result = self._run_direct_subprocess(
                command=command,
                env=env,
                cwd=cwd,
                turn_index=turn_index,
                output_format=output_format,
                provider=provider,
            )

        elif provider is None:
            result = self._run_in_tmux_legacy(
                command=command,
                cwd=cwd,
                turn_index=turn_index,
                output_format=output_format,
                tmux_session_name=tmux_session_name,
                tmux_pane_target=tmux_pane_target,
                turn_artifacts_root=turn_artifacts_root
                if turn_artifacts_root is not None
                else cwd / ".houmao" / "headless-turns",
                turn_artifact_dir_name=turn_id,
                completion_timeout_seconds=completion_timeout_seconds,
                completion_poll_interval_seconds=completion_poll_interval_seconds,
            )

        else:
            result = self._run_in_tmux_bridge(
                command=command,
                env=env,
                cwd=cwd,
                turn_index=turn_index,
                output_format=output_format,
                provider=provider,
                display_style=display_style,
                display_detail=display_detail,
                tmux_session_name=tmux_session_name,
                tmux_pane_target=tmux_pane_target,
                turn_artifacts_root=turn_artifacts_root
                if turn_artifacts_root is not None
                else cwd / ".houmao" / "headless-turns",
                turn_artifact_dir_name=turn_id,
                completion_timeout_seconds=completion_timeout_seconds,
                completion_poll_interval_seconds=completion_poll_interval_seconds,
                replace_environment=replace_environment,
            )
        completed_at_utc = datetime.now(UTC).isoformat()
        elapsed_ms = (time.monotonic() - started_monotonic) * 1000
        if provider == "dsh" and result.returncode == 130:
            self.m_interrupt_requested = True
        if self.m_active_turn_dir is not None and provider != "hermes":
            persist_terminal_evidence(
                self.m_active_turn_dir,
                returncode=result.returncode,
                completed_at_utc=completed_at_utc,
                wall_time_ms=elapsed_ms,
                interrupted=self.m_interrupt_requested
                or (self.m_active_turn_dir / "usage-interrupt.json").is_file(),
            )
        return replace(
            result,
            turn_id=turn_id,
            started_at_utc=started_at_utc,
            completed_at_utc=(
                completed_at_utc
                if provider != "hermes" or result.completion_source != "native_unresolved"
                else None
            ),
            wall_time_ms=elapsed_ms,
            interrupted=self.m_interrupt_requested,
        )

    @property
    def active_process_running(self) -> bool:
        """Return whether durable process identity still identifies live execution."""

        if self._active_process is not None:
            return self._active_process.poll() is None
        if self.m_active_turn_dir is not None and (self.m_active_turn_dir / "exitcode").exists():
            return False
        if self.m_active_turn_dir is not None and (
            self._active_process_path is not None or self.m_active_provider == "dsh"
        ):
            return headless_artifact_process_alive(self.m_active_turn_dir)
        metadata = self._active_process_metadata
        if metadata is None or metadata.child_pid is None:
            return False
        try:
            os.kill(metadata.child_pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _note_interruption(self) -> None:
        """Persist interruption intent so recovery uses the original terminal outcome."""

        self.m_interrupt_requested = True
        if self.m_active_turn_dir is not None:
            write_usage_json(
                self.m_active_turn_dir / "usage-interrupt.json",
                {"requested_at_utc": datetime.now(UTC).isoformat()},
            )

    def cancel_request_dispatch(self, control: HeadlessDispatchControl) -> None:
        """Stop only this request's captured process, without targeting a replacement pane."""

        control.cancel()
        # Hermes cannot attribute native cancellation to the finite viewer's PID.
        if self.m_dispatch_control is not control or self.m_active_provider == "hermes":
            return
        process = self._active_process
        if process is not None and process.poll() is None:
            self._note_interruption()
            process.terminate()
            return
        metadata = self._active_process_metadata
        if metadata is None and self._active_process_path is not None:
            metadata = self._read_process_metadata_best_effort(
                process_path=self._active_process_path
            )
            self._active_process_metadata = metadata
        if metadata is not None and metadata.child_pid is not None and self.active_process_running:
            if metadata.child_isolated_group and self.m_active_turn_dir is not None:
                outcome = interrupt_owned_headless_attempt(self.m_active_turn_dir)
                self.m_interrupt_requested = outcome.status == "ok"
                return
            self._note_interruption()
            self._signal_active_tmux_process(signal.SIGTERM)

    def interrupt(self) -> SessionControlResult:
        """Interrupt an in-flight process with best-effort termination."""

        process = self._active_process
        if process is not None and process.poll() is None:
            self._note_interruption()
            process.terminate()
            return SessionControlResult(
                status="ok",
                action="interrupt",
                detail="Sent terminate signal to headless process",
            )

        if self._active_tmux_pane_target is not None or self._active_process_metadata is not None:
            self._note_interruption()
        if self._signal_active_tmux_process(signal.SIGTERM):
            return SessionControlResult(
                status="ok",
                action="interrupt",
                detail="Sent terminate signal to active tmux-backed headless process",
            )

        if self.m_active_provider == "dsh":
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail="DSH attempt process identity is unavailable; no replacement surface was signalled",
            )

        pane_target = self._active_tmux_pane_target
        if pane_target is None:
            return SessionControlResult(
                status="ok",
                action="interrupt",
                detail="No in-flight headless process",
            )

        try:
            self._note_interruption()
            result = run_tmux_shared(["send-keys", "-t", pane_target, "C-c"])
        except TmuxCommandError as exc:
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail=f"Failed to interrupt tmux {HEADLESS_AGENT_WINDOW_NAME} surface: {exc}",
            )
        if result.returncode != 0:
            detail = tmux_error_detail_shared(result) or "unknown tmux error"
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail=f"Failed to interrupt tmux {HEADLESS_AGENT_WINDOW_NAME} surface: {detail}",
            )
        return SessionControlResult(
            status="ok",
            action="interrupt",
            detail="Sent control input to active tmux-backed headless agent surface",
        )

    def terminate(self) -> SessionControlResult:
        """Force kill an in-flight process."""

        process = self._active_process
        if process is not None and process.poll() is None:
            self._note_interruption()
            process.kill()
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="Killed headless process",
            )

        if self._active_tmux_pane_target is not None or self._active_process_metadata is not None:
            self._note_interruption()
        if self._signal_active_tmux_process(signal.SIGKILL):
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="Killed active tmux-backed headless process",
            )

        if self.m_active_provider == "dsh":
            return SessionControlResult(
                status="ok" if not self.active_process_running else "error",
                action="terminate",
                detail="DSH attempt ended or its exact process identity is unavailable",
            )

        pane_target = self._active_tmux_pane_target
        if pane_target is None:
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="No active headless process",
            )

        try:
            result = run_tmux_shared(["send-keys", "-t", pane_target, "C-c"])
        except TmuxCommandError as exc:
            return SessionControlResult(
                status="error",
                action="terminate",
                detail=f"Failed to terminate tmux {HEADLESS_AGENT_WINDOW_NAME} surface: {exc}",
            )
        if result.returncode != 0:
            detail = tmux_error_detail_shared(result) or "unknown tmux error"
            return SessionControlResult(
                status="error",
                action="terminate",
                detail=f"Failed to terminate tmux {HEADLESS_AGENT_WINDOW_NAME} surface: {detail}",
            )
        return SessionControlResult(
            status="ok",
            action="terminate",
            detail="Sent control input to active tmux-backed headless agent surface",
        )

    def _run_direct_subprocess(
        self,
        *,
        command: list[str],
        env: dict[str, str],
        cwd: Path,
        turn_index: int,
        output_format: str,
        provider: HeadlessProvider | None,
    ) -> HeadlessRunResult:
        self._require_dispatch_allowed()
        if provider == "dsh":
            raise BackendExecutionError("Managed DSH ACP execution requires its tmux turn envelope")
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._active_process = process
        try:
            if self.m_dispatch_control is not None and process.poll() is None:
                self.m_dispatch_control.m_handoff_alive = lambda: process.poll() in {None, 0}
                self.m_dispatch_control.confirm_handoff()

            raw_stdout_chunks: list[str] = []

            assert process.stdout is not None
            for raw_line in process.stdout:
                raw_stdout_chunks.append(raw_line)

            returncode = process.wait()

            stderr_text = ""
            if process.stderr is not None:
                stderr_text = process.stderr.read()

            stdout_text = "".join(raw_stdout_chunks)
            if provider is None:
                events = parse_headless_output_text(
                    output_format=output_format,
                    stdout_text=stdout_text,
                    turn_index=turn_index,
                )
            else:
                canonical_events = canonical_headless_events_from_provider_output(
                    provider=provider,
                    output_format=output_format,
                    stdout_text=stdout_text,
                    turn_index=turn_index,
                )
                events = canonical_headless_events_to_session_events(canonical_events)

            session_id = extract_session_id(events)
            self._active_process = None

            if returncode != 0:
                message = stderr_text.strip() or f"command exited with code {returncode}"
                events.append(
                    SessionEvent(
                        kind="error",
                        message=message,
                        turn_index=turn_index,
                        payload={"returncode": returncode},
                    )
                )

            return HeadlessRunResult(
                events=events,
                stderr=stderr_text,
                returncode=returncode,
                session_id=session_id,
            )
        except BaseException:
            if self.m_dispatch_control is not None:
                self.m_dispatch_control.cancel()
            _stop_unconfirmed_native_process(process)
            raise
        finally:
            self._active_process = None
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()

    def _run_in_tmux_bridge(
        self,
        *,
        command: list[str],
        env: dict[str, str],
        cwd: Path,
        turn_index: int,
        output_format: str,
        provider: HeadlessProvider,
        display_style: HeadlessDisplayStyle,
        display_detail: HeadlessDisplayDetail,
        tmux_session_name: str,
        tmux_pane_target: str | None,
        turn_artifacts_root: Path,
        turn_artifact_dir_name: str | None,
        completion_timeout_seconds: float,
        completion_poll_interval_seconds: float,
        replace_environment: bool = False,
    ) -> HeadlessRunResult:
        turn_dir_name = turn_artifact_dir_name or f"turn-{uuid.uuid4().hex[:12]}"
        turn_dir = (turn_artifacts_root / turn_dir_name).resolve()
        turn_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = turn_dir / "stdout.jsonl"
        stderr_path = turn_dir / "stderr.log"
        status_path = turn_dir / "exitcode"
        process_path = turn_dir / "process.json"
        canonical_path = canonical_headless_event_artifact_path(turn_dir=turn_dir)
        wait_signal = f"houmao-headless-turn-{turn_index}-{uuid.uuid4().hex[:10]}".lower()
        pane_target = tmux_pane_target
        launched_at_utc = datetime.now(UTC).isoformat(timespec="seconds")
        environment_path = turn_dir / f".provider-env-{uuid.uuid4().hex}.json"
        try:
            permission_path = (
                self.m_dispatch_control.prepare_bridge_permission(turn_dir)
                if self.m_dispatch_control is not None
                else None
            )
            if provider == "dsh" and permission_path is not None:
                env = {**env, "HOUMAO_DSH_DISPATCH_GUARD": str(permission_path)}
            bridge_args = [
                sys.executable,
                "-m",
                "houmao.agents.realm_controller.backends.headless_bridge",
                "--provider",
                provider,
                "--output-format",
                output_format,
                "--turn-index",
                str(turn_index),
                "--turn-dir",
                str(turn_dir),
                "--cwd",
                str(cwd),
                "--style",
                display_style,
                "--detail",
                display_detail,
                "--launched-at-utc",
                launched_at_utc,
                "--env-file",
                str(environment_path),
                *(["--replace-environment"] if replace_environment else []),
                *(["--dispatch-guard-file", str(permission_path)] if permission_path else []),
                "--",
                *command,
            ]
            bridge_command_text = shlex.join(bridge_args)
            script = "\n".join(
                [
                    "set +e",
                    f"cd {shlex.quote(str(cwd))}",
                    bridge_command_text,
                    f"{shlex.join(TmuxServer().signal_invocation(wait_signal))} >/dev/null 2>&1 || true",
                    'idle_shell="${SHELL:-/bin/sh}"',
                    'exec "$idle_shell" -l',
                ]
            )
            pane_command = f"bash -lc {shlex.quote(script)}"

            if pane_target is None:
                try:
                    self._require_dispatch_allowed()
                    pane_target = resolve_primary_tmux_surface_shared(
                        session_name=tmux_session_name,
                    ).pane_id
                except TmuxCommandError as exc:
                    raise BackendExecutionError(
                        f"Failed to prepare tmux headless agent surface in `{tmux_session_name}`: {exc}"
                    ) from exc

            try:
                self._require_dispatch_allowed()
                descriptor = os.open(environment_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    json.dump(env, handle, sort_keys=True)
                    handle.flush()
                    os.fsync(handle.fileno())
                self._require_dispatch_allowed()
                launch = run_tmux_shared(
                    [
                        "respawn-pane",
                        "-k",
                        "-t",
                        pane_target,
                        pane_command,
                    ]
                )
            except (TmuxCommandError, BackendExecutionError) as exc:
                environment_path.unlink(missing_ok=True)
                raise BackendExecutionError(f"Failed to launch tmux headless turn: {exc}") from exc

            if launch.returncode != 0:
                environment_path.unlink(missing_ok=True)
                detail = tmux_error_detail_shared(launch) or "unknown tmux error"
                raise BackendExecutionError(
                    f"Failed to launch tmux headless turn in `{tmux_session_name}` on the "
                    f"stable {HEADLESS_AGENT_WINDOW_NAME} surface: {detail}"
                )

            self._active_tmux_session_name = tmux_session_name
            self._active_tmux_pane_target = pane_target
            self._active_tmux_wait_signal = wait_signal
            self._active_process_path = process_path
            self._active_process_metadata = self._wait_for_process_metadata(
                process_path=process_path,
                timeout_seconds=(
                    max(0.0, self.m_dispatch_control.m_deadline - time.monotonic())
                    if self.m_dispatch_control is not None
                    else 1.0
                ),
            )
            if self.m_dispatch_control is not None and provider != "hermes":
                if provider == "dsh":
                    handoff_path = turn_dir / "dsh-native-handoff.json"
                    while not handoff_path.is_file() and not status_path.is_file():
                        self._require_dispatch_allowed()
                        time.sleep(0.01)
                    if not handoff_path.is_file():
                        if output_format == "dsh-cli":
                            detail = _native_dsh_stderr(stderr_path, env)
                            if detail:
                                raise BackendExecutionError(
                                    f"DSH native handoff was not confirmed: {detail}"
                                )
                        raise BackendExecutionError("DSH native handoff was not confirmed")
                    try:
                        receipt = json.loads(handoff_path.read_text(encoding="utf-8"))
                        if (
                            receipt.get("version") != 1
                            or receipt.get("attempt_id") != turn_dir.name
                            or not receipt.get("native_session_id")
                            or (
                                output_format == "dsh-cli"
                                and not _matching_dsh_process(
                                    receipt, self._active_process_metadata
                                )
                            )
                        ):
                            raise ValueError("Invalid DSH native receipt")
                    except (OSError, ValueError) as exc:
                        raise BackendExecutionError(
                            "DSH native handoff evidence is invalid"
                        ) from exc
                has_native_handoff = (
                    output_format == "dsh-cli"
                    or (
                        self._active_process_metadata is not None
                        and self._active_process_metadata.child_pid is not None
                        and self.active_process_running
                    )
                    or (
                        status_path.is_file()
                        and read_headless_turn_return_code(status_path=status_path) == 0
                    )
                )
                if not has_native_handoff:
                    raise BackendExecutionError("Immediate native handoff was not confirmed")
                self.m_dispatch_control.m_handoff_alive = lambda: (
                    output_format == "dsh-cli"
                    or self.active_process_running
                    or (
                        status_path.is_file()
                        and read_headless_turn_return_code(status_path=status_path) == 0
                    )
                )
                self.m_dispatch_control.confirm_handoff()

            deadline = time.monotonic() + max(completion_timeout_seconds, 0.0)
            try:
                wait_for_tmux_signal_shared(
                    signal_name=wait_signal,
                    timeout_seconds=completion_timeout_seconds,
                )
            except TmuxCommandError:
                pass

            while True:
                if status_path.is_file():
                    break
                if time.monotonic() >= deadline:
                    raise HeadlessTurnWaitTimeout(
                        "Timed out waiting for tmux headless turn completion marker."
                    )
                time.sleep(max(completion_poll_interval_seconds, 0.01))

            if provider == "hermes":
                stderr_text = (
                    "Hermes client diagnostics are available in the private turn artifacts."
                )
            elif output_format == "dsh-cli":
                stderr_text = _native_dsh_stderr(stderr_path, env)
            else:
                stderr_text = (
                    stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
                )
            returncode = read_headless_turn_return_code(status_path=status_path)
            canonical_events = load_preferred_canonical_headless_events(
                turn_dir=turn_dir,
                provider=provider,
                output_format=output_format,
                turn_index=turn_index,
            )
            events = canonical_headless_events_to_session_events(canonical_events)
            session_id = extract_session_id(events)
            process_metadata = self._read_process_metadata_best_effort(process_path=process_path)
            completion_source = "process_exit"
            if provider == "hermes":
                settlement = reconcile_hermes_headless_turn(turn_dir)
                completion_source = settlement.completion_source or "native_unresolved"
                if settlement.status == "completed" and self.m_dispatch_control is not None:
                    self.m_dispatch_control.confirm_durable_handoff()
            if output_format == "dsh-cli" and returncode != 0:
                stderr_text = _native_dsh_failure(stderr_text, canonical_events)
            if returncode != 0:
                message = stderr_text.strip() or f"command exited with code {returncode}"
                events.append(
                    SessionEvent(
                        kind="error",
                        message=message,
                        turn_index=turn_index,
                        payload={"returncode": returncode},
                    )
                )
            return HeadlessRunResult(
                events=events,
                stderr=stderr_text,
                returncode=returncode,
                session_id=session_id,
                stdout_path=turn_dir / "provider-stdout.jsonl"
                if provider == "dsh" and output_format != "dsh-cli"
                else stdout_path,
                stderr_path=stderr_path,
                status_path=status_path,
                process_path=process_path,
                canonical_path=canonical_path if canonical_path.exists() else None,
                process_metadata=process_metadata,
                completion_source=completion_source,
            )
        except BaseException as exc:
            control = self.m_dispatch_control
            if control is not None and not (
                provider == "dsh"
                and isinstance(exc, HeadlessTurnWaitTimeout)
                and control.m_handoff_confirmed.is_set()
                and self.active_process_running
            ):
                self.cancel_request_dispatch(control)
            raise
        finally:
            environment_path.unlink(missing_ok=True)
            if provider != "dsh" or not headless_artifact_process_alive(turn_dir):
                self._active_tmux_session_name = None
                self._active_tmux_pane_target = None
                self._active_tmux_wait_signal = None
                self._active_process_path = None
                self._active_process_metadata = None

    def _run_in_tmux_legacy(
        self,
        *,
        command: list[str],
        cwd: Path,
        turn_index: int,
        output_format: str,
        tmux_session_name: str,
        tmux_pane_target: str | None,
        turn_artifacts_root: Path,
        turn_artifact_dir_name: str | None,
        completion_timeout_seconds: float,
        completion_poll_interval_seconds: float,
    ) -> HeadlessRunResult:
        """Run the pre-canonical tmux path for legacy callers and tests."""

        turn_dir_name = turn_artifact_dir_name or f"turn-{uuid.uuid4().hex[:12]}"
        turn_dir = (turn_artifacts_root / turn_dir_name).resolve()
        turn_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = turn_dir / "stdout.jsonl"
        stderr_path = turn_dir / "stderr.log"
        status_path = turn_dir / "exitcode"
        process_path = turn_dir / "process.json"
        process_tmp_path = turn_dir / f".process-{uuid.uuid4().hex}.tmp"
        status_tmp_path = turn_dir / f".exitcode-{uuid.uuid4().hex}.tmp"
        stdout_pipe_path = turn_dir / f".stdout-{uuid.uuid4().hex}.pipe"
        stderr_pipe_path = turn_dir / f".stderr-{uuid.uuid4().hex}.pipe"
        wait_signal = f"houmao-headless-turn-{turn_index}-{uuid.uuid4().hex[:10]}".lower()
        pane_target = tmux_pane_target

        command_text = shlex.join(command)
        script = "\n".join(
            [
                "set +e",
                f"cd {shlex.quote(str(cwd))}",
                'started_at_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"',
                f"rm -f {shlex.quote(str(stdout_pipe_path))} {shlex.quote(str(stderr_pipe_path))}",
                f"mkfifo {shlex.quote(str(stdout_pipe_path))} {shlex.quote(str(stderr_pipe_path))}",
                (
                    "trap "
                    f"'rm -f {shlex.quote(str(stdout_pipe_path))} "
                    f"{shlex.quote(str(stderr_pipe_path))}' EXIT HUP INT TERM"
                ),
                f": > {shlex.quote(str(stdout_path))}",
                f": > {shlex.quote(str(stderr_path))}",
                (
                    f"tee -a {shlex.quote(str(stdout_path))} "
                    f"< {shlex.quote(str(stdout_pipe_path))} &"
                ),
                "stdout_tee_pid=$!",
                (
                    f"tee -a {shlex.quote(str(stderr_path))} "
                    f"< {shlex.quote(str(stderr_pipe_path))} >&2 &"
                ),
                "stderr_tee_pid=$!",
                (
                    f"( exec {command_text} > {shlex.quote(str(stdout_pipe_path))} "
                    f"2> {shlex.quote(str(stderr_pipe_path))} ) &"
                ),
                "child_pid=$!",
                (
                    "printf "
                    '\'{"runner_pid":%s,"child_pid":%s,"launched_at_utc":"%s"}\\n\' '
                    f'"$$" "$child_pid" "$started_at_utc" > {shlex.quote(str(process_tmp_path))}'
                ),
                (f"mv {shlex.quote(str(process_tmp_path))} {shlex.quote(str(process_path))}"),
                'wait "$child_pid"',
                "status=$?",
                'wait "$stdout_tee_pid" || true',
                'wait "$stderr_tee_pid" || true',
                f"printf '%s\\n' \"$status\" > {shlex.quote(str(status_tmp_path))}",
                (f"mv {shlex.quote(str(status_tmp_path))} {shlex.quote(str(status_path))}"),
                f"{shlex.join(TmuxServer().signal_invocation(wait_signal))} >/dev/null 2>&1 || true",
                'idle_shell="${SHELL:-/bin/sh}"',
                'exec "$idle_shell" -l',
            ]
        )
        pane_command = f"bash -lc {shlex.quote(script)}"

        if pane_target is None:
            try:
                pane_target = resolve_primary_tmux_surface_shared(
                    session_name=tmux_session_name,
                ).pane_id
            except TmuxCommandError as exc:
                raise BackendExecutionError(
                    f"Failed to prepare tmux headless agent surface in `{tmux_session_name}`: {exc}"
                ) from exc

        try:
            launch = run_tmux_shared(
                [
                    "respawn-pane",
                    "-k",
                    "-t",
                    pane_target,
                    pane_command,
                ]
            )
        except TmuxCommandError as exc:
            raise BackendExecutionError(f"Failed to launch tmux headless turn: {exc}") from exc

        if launch.returncode != 0:
            detail = tmux_error_detail_shared(launch) or "unknown tmux error"
            raise BackendExecutionError(
                f"Failed to launch tmux headless turn in `{tmux_session_name}` on the "
                f"stable {HEADLESS_AGENT_WINDOW_NAME} surface: {detail}"
            )

        self._active_tmux_session_name = tmux_session_name
        self._active_tmux_pane_target = pane_target
        self._active_tmux_wait_signal = wait_signal
        self._active_process_path = process_path
        self._active_process_metadata = self._wait_for_process_metadata(
            process_path=process_path,
            timeout_seconds=1.0,
        )

        try:
            wait_for_tmux_signal_shared(
                signal_name=wait_signal,
                timeout_seconds=completion_timeout_seconds,
            )
        except TmuxCommandError:
            pass

        deadline = time.monotonic() + max(completion_timeout_seconds, 0.0)
        while True:
            if status_path.is_file():
                break
            if time.monotonic() >= deadline:
                raise BackendExecutionError(
                    "Timed out waiting for tmux headless turn completion marker."
                )
            time.sleep(max(completion_poll_interval_seconds, 0.01))

        stderr_text = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
        stdout_text = stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else ""
        returncode = read_headless_turn_return_code(status_path=status_path)
        events = parse_headless_output_text(
            output_format=output_format,
            stdout_text=stdout_text,
            turn_index=turn_index,
        )
        session_id = extract_session_id(events)
        process_metadata = self._read_process_metadata_best_effort(process_path=process_path)

        if returncode != 0:
            message = stderr_text.strip() or f"command exited with code {returncode}"
            events.append(
                SessionEvent(
                    kind="error",
                    message=message,
                    turn_index=turn_index,
                    payload={"returncode": returncode},
                )
            )
        try:
            return HeadlessRunResult(
                events=events,
                stderr=stderr_text,
                returncode=returncode,
                session_id=session_id,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                status_path=status_path,
                process_path=process_path,
                process_metadata=process_metadata,
                completion_source="process_exit",
            )
        finally:
            self._active_tmux_session_name = None
            self._active_tmux_pane_target = None
            self._active_tmux_wait_signal = None
            self._active_process_path = None
            self._active_process_metadata = None

    def _signal_active_tmux_process(self, sig: int) -> bool:
        """Signal the active tmux-backed process identity when available."""

        metadata = self._active_process_metadata
        if metadata is None and self._active_process_path is not None:
            metadata = self._read_process_metadata_best_effort(
                process_path=self._active_process_path
            )
            if metadata is not None:
                self._active_process_metadata = metadata
        if metadata is None:
            return False
        if self.m_active_provider == "dsh":
            if metadata.child_isolated_group and metadata.child_pid is not None:
                try:
                    with _pinned_worker(metadata) as descriptor:
                        _signal_worker(descriptor, sig)
                    return True
                except (OSError, ValueError, AttributeError):
                    return False
            if sig == signal.SIGKILL and self.m_active_turn_dir is not None:
                signal_dsh_native_process(self.m_active_turn_dir, sig)
            if metadata.child_pid is None or metadata.child_birth_token is None:
                return False
            if _dispatch_origin_birth_token(metadata.child_pid) != metadata.child_birth_token:
                return False
            return _signal_pid(metadata.child_pid, sig)
        if _signal_pid(metadata.child_pid, sig):
            return True
        return _signal_pid(metadata.runner_pid, sig)

    def _wait_for_process_metadata(
        self,
        *,
        process_path: Path,
        timeout_seconds: float,
    ) -> HeadlessProcessMetadata | None:
        """Wait briefly for launch-time process metadata to be published."""

        deadline = time.monotonic() + max(timeout_seconds, 0.0)
        while time.monotonic() < deadline:
            self._require_dispatch_allowed()
            metadata = self._read_process_metadata_best_effort(process_path=process_path)
            if metadata is not None:
                return metadata
            if process_path.with_name("exitcode").is_file():
                return None
            time.sleep(0.05)
        return self._read_process_metadata_best_effort(process_path=process_path)

    def _read_process_metadata_best_effort(
        self,
        *,
        process_path: Path,
    ) -> HeadlessProcessMetadata | None:
        """Read durable process metadata without surfacing parse failures."""

        try:
            return load_headless_process_metadata(process_path=process_path)
        except (FileNotFoundError, ValueError, json.JSONDecodeError):
            return None


def _stop_unconfirmed_native_process(process: subprocess.Popen[str]) -> None:
    """Reap a child when a failed handoff can no longer leave execution running."""

    if process.poll() is not None:
        return
    try:
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1.0)
    except (OSError, subprocess.TimeoutExpired):
        pass


def extract_session_id(events: list[SessionEvent]) -> str | None:
    """Extract a backend `session_id` from parsed events."""

    for event in events:
        payload = event.payload
        if not isinstance(payload, dict):
            continue
        candidate = _extract_session_id_from_payload(payload)
        if candidate:
            return candidate
    return None


def parse_headless_output_text(
    *,
    output_format: str,
    stdout_text: str,
    turn_index: int,
) -> list[SessionEvent]:
    """Parse one persisted headless stdout payload into structured events."""

    events: list[SessionEvent] = []
    if output_format == "stream-json":
        for raw_line in stdout_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            events.append(_parse_stream_json_line(line=line, turn_index=turn_index))
        return events
    return _parse_json_payload(text=stdout_text, turn_index=turn_index)


def load_headless_turn_events(
    *,
    turn_dir: Path,
    provider: HeadlessProvider | None,
    output_format: str,
    turn_index: int,
) -> list[SessionEvent]:
    """Read one persisted headless stdout artifact and parse it."""

    stdout_path = (turn_dir / "stdout.jsonl").resolve()
    if provider is not None:
        canonical_path = canonical_headless_event_artifact_path(turn_dir=turn_dir)
        if canonical_path.exists():
            canonical_events = load_preferred_canonical_headless_events(
                turn_dir=turn_dir,
                provider=provider,
                output_format=output_format,
                turn_index=turn_index,
            )
            return canonical_headless_events_to_session_events(canonical_events)
        if provider == "hermes":
            return []

    stdout_text = stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else ""
    return parse_headless_output_text(
        output_format=output_format,
        stdout_text=stdout_text,
        turn_index=turn_index,
    )


def load_headless_process_metadata(*, process_path: Path) -> HeadlessProcessMetadata:
    """Read one persisted headless process metadata artifact."""

    payload = json.loads(process_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("headless process metadata must be a JSON object")
    return HeadlessProcessMetadata(
        runner_pid=_coerce_optional_pid(payload.get("runner_pid")),
        child_pid=_coerce_optional_pid(payload.get("child_pid")),
        launched_at_utc=_coerce_optional_string(payload.get("launched_at_utc")),
        runner_birth_token=_coerce_optional_string(payload.get("runner_birth_token")),
        child_birth_token=_coerce_optional_string(payload.get("child_birth_token")),
        child_isolated_group=payload.get("child_isolated_group") is True,
    )


def interrupt_owned_headless_attempt(turn_dir: Path) -> SessionControlResult:
    """Interrupt the captured process for an already verified owner request."""

    if (turn_dir / "exitcode").is_file():
        return SessionControlResult(
            status="ok", action="interrupt", detail="Headless turn has settled."
        )

    try:
        metadata = load_headless_process_metadata(process_path=turn_dir / "process.json")
        with _pinned_worker(metadata) as descriptor:
            if not (turn_dir / "exitcode").is_file():
                path = turn_dir / "usage-interrupt.json"
                request = {"requested_at_utc": datetime.now(UTC).isoformat()}
                write_usage_json(path, request)
                _signal_worker(descriptor, signal.SIGTERM)
                if metadata.child_isolated_group:
                    write_usage_json(
                        path,
                        {
                            **request,
                            "signal_delivered": True,
                            "process_id": metadata.child_pid,
                            "process_birth_token": metadata.child_birth_token,
                        },
                    )
                    poll = select.poll()
                    poll.register(descriptor, select.POLLIN)
                    if not poll.poll(1500):
                        _signal_worker(descriptor, signal.SIGKILL)
                        if not poll.poll(1000):
                            raise ValueError("Owned DSH worker did not exit")
                    deadline = time.monotonic() + 2.0
                    while not (turn_dir / "exitcode").is_file():
                        if time.monotonic() >= deadline:
                            raise ValueError("Native process closure remains unverified")
                        time.sleep(0.02)
    except (OSError, ValueError, AttributeError):
        return SessionControlResult(
            status="error",
            action="interrupt",
            detail="The native process for this headless request could not be verified.",
        )
    return SessionControlResult(
        status="ok", action="interrupt", detail="Interrupt sent to the captured headless worker."
    )


@contextmanager
def _pinned_worker(metadata: HeadlessProcessMetadata) -> Iterator[int]:
    """Pin the PID before comparing birth and isolated process-session identity."""

    pid = metadata.child_pid
    if pid is None or metadata.child_birth_token is None:
        raise ValueError("Missing process identity")
    descriptor = (
        os.pidfd_open(pid) if hasattr(os, "pidfd_open") else _libc_pidfd_call("pidfd_open", pid, 0)
    )
    try:
        if _dispatch_origin_birth_token(pid) != metadata.child_birth_token or (
            metadata.child_isolated_group and os.getsid(pid) != pid
        ):
            raise ValueError("Process identity changed")
        yield descriptor
    finally:
        os.close(descriptor)


def _signal_worker(descriptor: int, sig: int) -> None:
    """Send a signal through the pinned process handle."""

    if hasattr(signal, "pidfd_send_signal"):
        signal.pidfd_send_signal(descriptor, sig)
    else:
        _libc_pidfd_call("pidfd_send_signal", descriptor, sig, None, 0)


def _matching_dsh_process(
    binding: dict[str, Any], metadata: HeadlessProcessMetadata | None
) -> bool:
    """Match a native receipt to the exact worker launched by the bridge."""

    return bool(
        metadata is not None
        and metadata.child_isolated_group
        and metadata.child_pid is not None
        and metadata.child_birth_token
        and binding.get("process_id") == metadata.child_pid
        and binding.get("process_birth_token") == metadata.child_birth_token
    )


def _native_dsh_stderr(path: Path, environment: dict[str, str]) -> str:
    """Only surface bounded, redacted native diagnostic text."""

    secrets = dsh_diagnostic_secrets(
        environment, key_name=environment.get("HOUMAO_DSH_DIAGNOSTIC_KEY_NAME")
    )
    return sanitize_dsh_diagnostic(dsh_diagnostic_tail(path), secret_values=secrets, max_length=640)


def _native_dsh_failure(stderr: str, events: Sequence[CanonicalHeadlessEvent]) -> str:
    """Retain a qualified non-completion reason even when stderr is empty."""

    for event in reversed(events):
        if event.provider_event_type == "final":
            reason = (event.data or {}).get("stop_reason")
            if isinstance(reason, str):
                return f"Native final reason: {reason}. {stderr}".strip()
        elif event.provider_event_type == "error" and not stderr:
            return event.message
    return stderr


def _dsh_unverified_settlement(
    turn_dir: Path,
    session_id: str | None,
    events: Sequence[CanonicalHeadlessEvent],
    metadata: HeadlessProcessMetadata | None,
) -> str | None:
    """Require one complete native final and its exact persisted journal interval."""

    finals = [event for event in events if event.provider_event_type == "final"]
    if (
        session_id is None
        or len(finals) != 1
        or finals[0].session_id != session_id
        or (finals[0].data or {}).get("stop_reason") != "completed"
        or any(
            event.provider_event_type
            in {
                "raw_text",
                "non_mapping",
                "dsh_cli_invalid_record",
                "dsh_cli_incomplete_record",
                "dsh_cli_session_mismatch",
            }
            for event in events
        )
    ):
        return "DSH native stdout did not provide a verified completed final event."
    try:
        binding = json.loads((turn_dir / "dsh-native-binding.json").read_text())
        handoff = json.loads((turn_dir / "dsh-native-handoff.json").read_text())
        if (
            not isinstance(binding, dict)
            or binding != handoff
            or binding.get("native_session_id") != session_id
            or binding.get("attempt_id") != turn_dir.name
            or not _matching_dsh_process(binding, metadata)
        ):
            raise ValueError("Unverified DSH handoff")
        expected = {
            key: binding[key]
            for key in (
                "version",
                "attempt_id",
                "runtime_session_id",
                "generation",
                "process_id",
                "native_session_id",
            )
        }
        rows: list[dict[str, Any]] = []
        with (turn_dir / "dsh-native-evidence.jsonl").open("rb") as stream:
            while line := stream.readline(DSH_MAX_JOURNAL_ROW_BYTES + 1):
                if len(line) > DSH_MAX_JOURNAL_ROW_BYTES or not line.endswith(b"\n"):
                    raise ValueError("Incomplete DSH native evidence")
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("Malformed DSH native evidence")
                if row.get("event") in {"admitted", "claimed", "turn/start", "turn/end"}:
                    if any(row.get(key) != value for key, value in expected.items()):
                        raise ValueError("Mismatched DSH native evidence")
                    rows.append(row)
        admitted = [row.get("message_id") for row in rows if row.get("event") == "admitted"]
        claimed = [
            row
            for row in rows
            if row.get("event") == "claimed" and row.get("message_id") in admitted
        ]
        last_turn = next(row for row in reversed(rows) if row.get("event") == "turn/end")
        wanted = last_turn["native_sequence"]
        if (
            len(admitted) != 1
            or not isinstance(admitted[0], str)
            or len(claimed) != 1
            or type(wanted) is not int
            or last_turn.get("reason") != {"kind": "completed"}
            or not any(
                row.get("event") == "turn/start" and row.get("turn") == claimed[0].get("turn")
                for row in rows
            )
        ):
            raise ValueError("Incomplete DSH native turn interval")
        source = select_dsh_journal(Path(binding["persistence_root"]), session_id)
        if (
            source is None
            or inspect_dsh_journal(source, session_id).cwd != binding["working_directory"]
        ):
            raise ValueError("Unverified DSH native workspace")
        persisted = None
        with source.open("rb") as stream:
            stream.readline(DSH_MAX_JOURNAL_ROW_BYTES + 1)
            sequence = 0
            while line := stream.readline(DSH_MAX_JOURNAL_ROW_BYTES + 1):
                if len(line) > DSH_MAX_JOURNAL_ROW_BYTES or not line.endswith(b"\n"):
                    raise ValueError("Incomplete DSH native journal")
                row = json.loads(line)
                if not isinstance(row, dict) or row.get("seq") != sequence:
                    raise ValueError("Discontinuous DSH native journal")
                if sequence == wanted:
                    persisted = row
                sequence += 1
        if (
            persisted is None
            or persisted.get("type") != "turn/end"
            or persisted.get("data", {}).get("turn") != last_turn.get("turn")
            or persisted.get("data", {}).get("reason") != {"kind": "completed"}
        ):
            raise ValueError("Unverified DSH native terminal journal record")
    except (OSError, AttributeError, KeyError, StopIteration, TypeError, ValueError):
        return "DSH native completion could not be verified against its owned journal."
    return None


def _libc_pidfd_call(symbol: str, *arguments: int | None) -> int:
    """Use the Linux libc binding when this Python build omits pidfd functions."""

    call = getattr(ctypes.CDLL(None, use_errno=True), symbol)
    result = int(call(*arguments))
    if result < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return result


def read_headless_turn_return_code(*, status_path: Path) -> int:
    """Read one persisted headless exit-code marker."""

    raw = status_path.read_text(encoding="utf-8").strip()
    if not raw:
        raise BackendExecutionError(
            f"Invalid headless turn status marker `{status_path}`: blank content."
        )
    try:
        return int(raw)
    except ValueError as exc:
        raise BackendExecutionError(
            f"Invalid headless turn status marker `{status_path}`: {raw!r}."
        ) from exc


def _parse_stream_json_line(*, line: str, turn_index: int) -> SessionEvent:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return SessionEvent(
            kind="diagnostic",
            message=line,
            turn_index=turn_index,
            payload={"raw": line},
        )

    kind = str(payload.get("type", "event"))
    message = _extract_text(payload) or kind
    return SessionEvent(kind=kind, message=message, turn_index=turn_index, payload=payload)


def _parse_json_payload(*, text: str, turn_index: int) -> list[SessionEvent]:
    stripped = text.strip()
    if not stripped:
        return []

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise BackendExecutionError(f"Could not parse JSON headless payload: {exc}") from exc

    if isinstance(payload, list):
        events: list[SessionEvent] = []
        for item in payload:
            if isinstance(item, dict):
                events.append(
                    SessionEvent(
                        kind=str(item.get("type", "event")),
                        message=_extract_text(item) or "event",
                        turn_index=turn_index,
                        payload=item,
                    )
                )
        return events

    if isinstance(payload, dict):
        return [
            SessionEvent(
                kind=str(payload.get("type", "result")),
                message=_extract_text(payload) or "result",
                turn_index=turn_index,
                payload=payload,
            )
        ]

    return [
        SessionEvent(
            kind="result",
            message=str(payload),
            turn_index=turn_index,
            payload={"value": payload},
        )
    ]


def _extract_text(payload: dict[str, Any]) -> str:
    for key in ("text", "message", "content", "output", "result"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    if isinstance(payload.get("delta"), str):
        return str(payload["delta"])
    return ""


def _extract_session_id_from_payload(payload: dict[str, Any]) -> str | None:
    for key in ("session_id", "sessionId", "thread_id", "threadId"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    session = payload.get("session")
    if isinstance(session, dict):
        nested = session.get("id")
        if isinstance(nested, str) and nested.strip():
            return nested

    thread = payload.get("thread")
    if isinstance(thread, dict):
        thread_id = thread.get("id")
        if isinstance(thread_id, str) and thread_id.strip():
            return thread_id

    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("session_id", "sessionId", "thread_id", "threadId"):
            nested_data = data.get(key)
            if isinstance(nested_data, str) and nested_data.strip():
                return nested_data

    return None


def _coerce_optional_pid(value: object) -> int | None:
    """Normalize one optional persisted pid field."""

    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("pid must not be boolean")
    if isinstance(value, int):
        if value <= 0:
            raise ValueError("pid must be > 0")
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        if parsed <= 0:
            raise ValueError("pid must be > 0")
        return parsed
    raise ValueError("pid must be an integer")


def _coerce_optional_string(value: object) -> str | None:
    """Normalize one optional persisted string field."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("value must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValueError("value must not be empty")
    return stripped


def _signal_pid(pid: int | None, sig: int) -> bool:
    """Deliver one POSIX signal when the pid is live."""

    if pid is None:
        return False
    try:
        os.kill(pid, sig)
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        raise
    return True
