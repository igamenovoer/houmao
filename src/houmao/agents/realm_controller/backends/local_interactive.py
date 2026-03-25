"""Local interactive tmux-backed runtime backend."""

from __future__ import annotations

import shlex
import time
from pathlib import Path

from houmao.server.tui.process import PaneProcessInspector

from ..errors import BackendExecutionError
from ..models import LaunchPlan, SessionControlResult, SessionEvent
from .headless_base import HeadlessInteractiveSession, HeadlessSessionState
from .tmux_runtime import (
    HEADLESS_AGENT_WINDOW_NAME,
    TmuxCommandError,
    TmuxControlInputError,
    capture_tmux_pane as capture_tmux_pane_shared,
    headless_agent_pane_target as headless_agent_pane_target_shared,
    kill_tmux_session as kill_tmux_session_shared,
    list_tmux_panes as list_tmux_panes_shared,
    parse_tmux_control_input as parse_tmux_control_input_shared,
    prepare_headless_agent_window as prepare_headless_agent_window_shared,
    run_tmux as run_tmux_shared,
    send_tmux_control_input as send_tmux_control_input_shared,
    tmux_error_detail as tmux_error_detail_shared,
)

_SUPPORTED_TUI_PROCESSES: dict[str, tuple[str, ...]] = {
    "claude": ("claude", "claude-code"),
    "codex": ("codex",),
    "gemini": ("gemini",),
}


class LocalInteractiveSession(HeadlessInteractiveSession):
    """Tmux-backed runtime that keeps one provider TUI alive."""

    def __init__(
        self,
        *,
        launch_plan: LaunchPlan,
        role_name: str,
        session_manifest_path: Path,
        agent_def_dir: Path | None = None,
        state: HeadlessSessionState | None = None,
        tmux_session_name: str | None = None,
    ) -> None:
        self._process_inspector = PaneProcessInspector(supported_processes=_SUPPORTED_TUI_PROCESSES)
        resumed = state is not None
        super().__init__(
            backend="local_interactive",
            launch_plan=launch_plan,
            role_name=role_name,
            session_manifest_path=session_manifest_path,
            agent_def_dir=agent_def_dir,
            state=state,
            tmux_session_name=tmux_session_name,
        )
        if resumed:
            return
        try:
            self._launch_provider_surface()
            self._apply_startup_bootstrap()
        except Exception:
            self._cleanup_failed_startup()
            raise

    def send_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str | None = None,
    ) -> list[SessionEvent]:
        """Send one prompt into the live provider TUI."""

        del turn_artifact_dir_name
        if not prompt.strip():
            raise BackendExecutionError("Prompt must not be empty")
        if (
            not self._state.role_bootstrap_applied
            and self._plan.role_injection.method == "bootstrap_message"
            and self._plan.role_injection.bootstrap_message
        ):
            self._send_literal_with_enter(self._plan.role_injection.bootstrap_message)
            self._state.role_bootstrap_applied = True
        self._send_literal_with_enter(prompt)
        self._state.turn_index += 1
        return [
            SessionEvent(
                kind="submitted",
                message="prompt submitted",
                turn_index=self._state.turn_index,
                payload={"tmux_session_name": self._require_tmux_session_name()},
            )
        ]

    def interrupt(self) -> SessionControlResult:
        """Send one best-effort interrupt signal to the live TUI pane."""

        try:
            send_tmux_control_input_shared(
                target=headless_agent_pane_target_shared(
                    session_name=self._require_tmux_session_name()
                ),
                segments=parse_tmux_control_input_shared(sequence="<[C-c]>"),
            )
        except (BackendExecutionError, TmuxCommandError, TmuxControlInputError) as exc:
            return SessionControlResult(
                status="error",
                action="interrupt",
                detail=f"Failed to interrupt local interactive session: {exc}",
            )
        return SessionControlResult(
            status="ok",
            action="interrupt",
            detail="Sent interrupt to the local interactive session.",
        )

    def send_input_ex(
        self, sequence: str, *, escape_special_keys: bool = False
    ) -> SessionControlResult:
        """Send raw mixed control input to the provider TUI."""

        try:
            send_tmux_control_input_shared(
                target=headless_agent_pane_target_shared(
                    session_name=self._require_tmux_session_name()
                ),
                segments=parse_tmux_control_input_shared(
                    sequence=sequence,
                    escape_special_keys=escape_special_keys,
                ),
            )
        except (BackendExecutionError, TmuxCommandError, TmuxControlInputError) as exc:
            return SessionControlResult(
                status="error",
                action="control_input",
                detail=f"Failed to send local interactive control input: {exc}",
            )
        return SessionControlResult(
            status="ok",
            action="control_input",
            detail="Delivered control input to the local interactive session.",
        )

    def terminate(self) -> SessionControlResult:
        """Stop runtime control and optionally delete the tmux session."""

        session_name = self._state.tmux_session_name
        if not self._force_cleanup_on_terminate:
            detail = (
                "Stopped local interactive runtime control; preserved tmux session "
                f"`{session_name}` for inspection."
                if session_name
                else "Stopped local interactive runtime control."
            )
            return SessionControlResult(status="ok", action="terminate", detail=detail)

        session_name = self._require_tmux_session_name()
        try:
            kill_tmux_session_shared(session_name=session_name)
        except TmuxCommandError as exc:
            return SessionControlResult(
                status="error",
                action="terminate",
                detail=f"Failed to cleanup tmux session `{session_name}`: {exc}",
            )
        self._state.tmux_session_name = None
        return SessionControlResult(
            status="ok",
            action="terminate",
            detail=f"Stopped local interactive runtime and deleted tmux session `{session_name}`.",
        )

    def close(self) -> None:
        """Release backend resources."""

        self.terminate()

    def _launch_provider_surface(self) -> None:
        session_name = self._require_tmux_session_name()
        pane_target = headless_agent_pane_target_shared(session_name=session_name)
        command_text = shlex.join(self._build_launch_command())
        script = "\n".join(
            [
                "set +e",
                f"cd {shlex.quote(str(self._plan.working_directory))}",
                f"{command_text}",
                "status=$?",
                'printf "\\n[houmao local interactive exited with code %s]\\n" "$status"',
                'idle_shell="${SHELL:-/bin/sh}"',
                'exec "$idle_shell" -l',
            ]
        )
        pane_command = f"sh -lc {shlex.quote(script)}"

        try:
            prepare_headless_agent_window_shared(session_name=session_name)
        except TmuxCommandError as exc:
            raise BackendExecutionError(
                f"Failed to prepare tmux interactive agent surface in `{session_name}`: {exc}"
            ) from exc

        try:
            result = run_tmux_shared(["respawn-pane", "-k", "-t", pane_target, pane_command])
        except TmuxCommandError as exc:
            raise BackendExecutionError(
                f"Failed to launch tmux interactive runtime in `{session_name}`: {exc}"
            ) from exc
        if result.returncode != 0:
            detail = tmux_error_detail_shared(result) or "unknown tmux error"
            raise BackendExecutionError(
                f"Failed to launch tmux interactive runtime in `{session_name}` on the stable "
                f"{HEADLESS_AGENT_WINDOW_NAME} surface: {detail}"
            )

        self._wait_for_provider_tui(timeout_seconds=10.0, poll_interval_seconds=0.2)

    def _build_launch_command(self) -> list[str]:
        command = [self._plan.executable, *self._plan.args]
        if self._plan.role_injection.method == "native_developer_instructions":
            command.extend(["-c", f"developer_instructions={self._plan.role_injection.prompt}"])
        elif self._plan.role_injection.method == "native_append_system_prompt":
            command.extend(["--append-system-prompt", self._plan.role_injection.prompt])
        return command

    def _apply_startup_bootstrap(self) -> None:
        bootstrap = self._plan.role_injection.bootstrap_message
        if self._plan.role_injection.method != "bootstrap_message" or not bootstrap:
            return
        time.sleep(0.2)
        self._send_literal_with_enter(bootstrap)
        self._state.role_bootstrap_applied = True

    def _send_literal_with_enter(self, text: str) -> None:
        try:
            send_tmux_control_input_shared(
                target=headless_agent_pane_target_shared(
                    session_name=self._require_tmux_session_name()
                ),
                segments=(
                    *parse_tmux_control_input_shared(
                        sequence=text,
                        escape_special_keys=True,
                    ),
                    *parse_tmux_control_input_shared(sequence="<[Enter]>"),
                ),
            )
        except (TmuxCommandError, TmuxControlInputError) as exc:
            raise BackendExecutionError(
                f"Failed to send input to local interactive session: {exc}"
            ) from exc

    def _wait_for_provider_tui(
        self,
        *,
        timeout_seconds: float,
        poll_interval_seconds: float,
    ) -> None:
        session_name = self._require_tmux_session_name()
        pane_target = headless_agent_pane_target_shared(session_name=session_name)
        deadline = time.monotonic() + max(timeout_seconds, 0.1)
        last_capture = ""
        while time.monotonic() < deadline:
            try:
                panes = list_tmux_panes_shared(session_name=session_name)
            except TmuxCommandError as exc:
                raise BackendExecutionError(
                    f"Failed to inspect tmux panes for `{session_name}`: {exc}"
                ) from exc
            pane = next(
                (
                    candidate
                    for candidate in panes
                    if candidate.window_index == "0" and candidate.pane_index == "0"
                ),
                None,
            )
            if pane is None:
                raise BackendExecutionError(
                    f"tmux session `{session_name}` is missing the stable agent pane."
                )
            try:
                last_capture = capture_tmux_pane_shared(target=pane_target)
            except TmuxCommandError:
                last_capture = ""
            inspection = self._process_inspector.inspect(
                tool=self._plan.tool, pane_pid=pane.pane_pid
            )
            if inspection.process_state == "tui_up":
                return
            if pane.pane_dead:
                break
            time.sleep(max(poll_interval_seconds, 0.05))

        excerpt = last_capture.strip()
        detail = "provider TUI did not stay live after launch"
        if excerpt:
            detail = f"{detail}; pane output:\n{excerpt[-1200:]}"
        raise BackendExecutionError(
            f"Local interactive launch failed because the {self._plan.tool} TUI was not ready: "
            f"{detail}"
        )

    def _cleanup_failed_startup(self) -> None:
        session_name = (self._state.tmux_session_name or "").strip()
        if not session_name:
            return
        try:
            kill_tmux_session_shared(session_name=session_name)
        except TmuxCommandError:
            return
        self._state.tmux_session_name = None
