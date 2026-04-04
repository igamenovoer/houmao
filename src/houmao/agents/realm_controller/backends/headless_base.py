"""Shared tmux-backed resumable headless backend implementation."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from houmao.cao.no_proxy import inject_loopback_no_proxy_env

from ..agent_identity import AGENT_DEF_DIR_ENV_VAR, AGENT_MANIFEST_PATH_ENV_VAR
from ..errors import BackendExecutionError
from ..models import (
    BackendKind,
    HeadlessResumeSelectionKind,
    HeadlessTurnSessionSelection,
    LaunchPlan,
    SessionControlResult,
    SessionEvent,
)
from .claude_bootstrap import ensure_claude_home_bootstrap as _ensure_claude_home_bootstrap_legacy
from .codex_bootstrap import ensure_codex_home_bootstrap as _ensure_codex_home_bootstrap_legacy
from .headless_output import (
    resolve_headless_display_detail,
    resolve_headless_display_style,
    resolve_headless_provider,
)
from .headless_runner import HeadlessCliRunner
from .tmux_runtime import (
    TmuxCommandError,
    create_tmux_session as create_tmux_session_shared,
    ensure_tmux_available as ensure_tmux_available_shared,
    generate_tmux_session_name as generate_tmux_session_name_shared,
    has_tmux_session as has_tmux_session_shared,
    kill_tmux_session as kill_tmux_session_shared,
    prepare_headless_agent_window as prepare_headless_agent_window_shared,
    set_tmux_session_environment as set_tmux_session_environment_shared,
    tmux_error_detail as tmux_error_detail_shared,
)

# Legacy module aliases kept for tests and external monkeypatch hooks. Runtime launch
# policy is resolved before backend execution and no longer invokes these directly.
ensure_claude_home_bootstrap = _ensure_claude_home_bootstrap_legacy
ensure_codex_home_bootstrap = _ensure_codex_home_bootstrap_legacy


@dataclass
class HeadlessSessionState:
    """Persisted resumable state for headless backends."""

    session_id: str | None = None
    turn_index: int = 0
    role_bootstrap_applied: bool = False
    working_directory: str = ""
    tmux_session_name: str | None = None
    tmux_window_name: str | None = None
    resume_selection_kind: HeadlessResumeSelectionKind = "none"
    resume_selection_value: str | None = None
    joined_session: bool = False


class HeadlessInteractiveSession:
    """Base class for resumable tmux-backed headless tool backends."""

    def __init__(
        self,
        *,
        backend: BackendKind,
        launch_plan: LaunchPlan,
        role_name: str,
        session_manifest_path: Path,
        agent_def_dir: Path | None = None,
        state: HeadlessSessionState | None = None,
        tmux_session_name: str | None = None,
        output_format: str = "stream-json",
    ) -> None:
        if backend not in {
            "local_interactive",
            "codex_headless",
            "claude_headless",
            "gemini_headless",
        }:
            raise BackendExecutionError(f"Invalid tmux-backed backend: {backend}")

        self.backend: BackendKind = backend
        self._plan = launch_plan
        self._role_name = role_name
        self._state = state or HeadlessSessionState(
            working_directory=str(launch_plan.working_directory)
        )
        self._runner = HeadlessCliRunner()
        self._output_format = output_format
        self._provider = resolve_headless_provider(
            tool=launch_plan.tool,
            backend=backend,
        )
        self._display_style = resolve_headless_display_style(
            launch_plan.metadata.get("headless_display_style")
        )
        self._display_detail = resolve_headless_display_detail(
            launch_plan.metadata.get("headless_display_detail")
        )
        self._session_manifest_path = session_manifest_path.resolve()
        self._agent_def_dir = agent_def_dir.resolve() if agent_def_dir is not None else None
        self._turn_artifacts_root = (
            self._session_manifest_path.parent
            / f"{self._session_manifest_path.stem}.turn-artifacts"
        ).resolve()
        self._force_cleanup_on_terminate = False

        _ensure_required_executable(
            executable=self._plan.executable,
            flow=f"{self.backend} runtime execution",
        )
        self._ensure_tmux_container(requested_tmux_session_name=tmux_session_name)

    @property
    def state(self) -> HeadlessSessionState:
        """Return current headless backend state."""

        return self._state

    def configure_stop_force_cleanup(self, *, force_cleanup: bool) -> None:
        """Configure whether terminate() should kill the tmux session."""

        self._force_cleanup_on_terminate = force_cleanup

    def send_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
    ) -> list[SessionEvent]:
        """Send one prompt turn to the headless backend."""

        if not prompt.strip():
            raise BackendExecutionError("Prompt must not be empty")

        session_name = self._require_tmux_session_name()
        turn_index = self._state.turn_index + 1
        command, input_prompt = self._build_command(
            prompt=prompt,
            session_selection=session_selection,
        )
        env = os.environ.copy()
        env.update(self._plan.env)
        env[self._plan.home_env_var] = str(self._plan.home_path)
        inject_loopback_no_proxy_env(env)

        run_kwargs: dict[str, Any] = {
            "command": command,
            "env": env,
            "cwd": self._plan.working_directory,
            "turn_index": turn_index,
            "output_format": self._output_format,
            "provider": self._provider,
            "display_style": self._display_style,
            "display_detail": self._display_detail,
            "tmux_session_name": session_name,
            "turn_artifacts_root": self._turn_artifacts_root,
        }
        if turn_artifact_dir_name is not None:
            run_kwargs["turn_artifact_dir_name"] = turn_artifact_dir_name

        run_result = self._runner.run(
            **run_kwargs,
        )

        if run_result.returncode != 0:
            message = run_result.stderr.strip() or "headless command failed"
            raise BackendExecutionError(f"{self.backend}: {message}")

        self._state.turn_index = turn_index
        if not self._state.role_bootstrap_applied and input_prompt != prompt:
            self._state.role_bootstrap_applied = True

        if run_result.session_id:
            self._state.session_id = run_result.session_id
            self._publish_tmux_session_environment()

        events = list(run_result.events)
        if self._state.session_id is None:
            raise BackendExecutionError(f"{self.backend}: missing session_id in bootstrap output")

        events.append(
            SessionEvent(
                kind="done",
                message="turn completed",
                turn_index=turn_index,
                payload={
                    "session_id": self._state.session_id,
                    "tmux_session_name": session_name,
                    "stdout_path": str(run_result.stdout_path)
                    if run_result.stdout_path is not None
                    else None,
                    "stderr_path": str(run_result.stderr_path)
                    if run_result.stderr_path is not None
                    else None,
                    "canonical_path": str(run_result.canonical_path)
                    if run_result.canonical_path is not None
                    else None,
                    "completion_source": run_result.completion_source,
                },
            )
        )

        return events

    def interrupt(self) -> SessionControlResult:
        """Interrupt in-flight headless turn execution."""

        return self._runner.interrupt()

    def terminate(self) -> SessionControlResult:
        """Terminate in-flight work and optionally cleanup tmux session."""

        runner_result = self._runner.terminate()
        if runner_result.status == "error":
            return runner_result

        if not self._force_cleanup_on_terminate:
            session_name = self._state.tmux_session_name
            detail = (
                "Stopped headless runtime control; preserved tmux session "
                f"`{session_name}` for inspection."
                if session_name
                else "Stopped headless runtime control."
            )
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail=detail,
            )

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
            detail=f"Stopped runtime control and deleted tmux session `{session_name}`.",
        )

    def close(self) -> None:
        """Close backend process resources."""

        self.terminate()

    def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
        """Replace the launch plan and republish tmux session environment."""

        self._plan = launch_plan
        self._provider = resolve_headless_provider(
            tool=launch_plan.tool,
            backend=self.backend,
        )
        self._display_style = resolve_headless_display_style(
            launch_plan.metadata.get("headless_display_style")
        )
        self._display_detail = resolve_headless_display_detail(
            launch_plan.metadata.get("headless_display_detail")
        )
        self._publish_tmux_session_environment()

    def relaunch(self) -> SessionControlResult:
        """Refresh the stable tmux-backed headless surface on window `0`."""

        session_name = self._require_tmux_session_name()
        has = has_tmux_session_shared(session_name=session_name)
        if has.returncode != 0:
            detail = tmux_error_detail_shared(has) or "unknown tmux error"
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail=(
                    "Headless relaunch requires the existing tmux session "
                    f"`{session_name}`, but it is unavailable: {detail}"
                ),
            )

        try:
            if not self._uses_joined_surface():
                prepare_headless_agent_window_shared(session_name=session_name)
            self._publish_tmux_session_environment()
        except TmuxCommandError as exc:
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail=f"Failed to prepare headless relaunch surface in `{session_name}`: {exc}",
            )

        return SessionControlResult(
            status="ok",
            action="relaunch",
            detail=(
                "Headless relaunch authority refreshed on tmux window `0`; the session remains "
                "ready for the next turn without rebuilding the agent home."
            ),
        )

    def _build_command(
        self,
        *,
        prompt: str,
        session_selection: HeadlessTurnSessionSelection | None = None,
    ) -> tuple[list[str], str]:
        command = [self._plan.executable, *self._plan.args]
        if not self._uses_joined_operator_launch_args():
            command.extend(self._base_command_args())
        effective_prompt = prompt

        if session_selection is not None:
            if session_selection.mode == "exact":
                assert session_selection.session_id is not None
                command.extend(self._resume_args(session_selection.session_id))
            elif session_selection.mode == "tool_last_or_new":
                latest_resume_args = self._latest_resume_args()
                if latest_resume_args:
                    command.extend(latest_resume_args)
                else:
                    command.extend(self._bootstrap_args())
                    effective_prompt = self._bootstrap_prompt(prompt)
            else:
                command.extend(self._bootstrap_args())
                effective_prompt = self._bootstrap_prompt(prompt)
        elif self._state.session_id:
            command.extend(self._resume_args(self._state.session_id))
        else:
            resume_selector_args = self._initial_resume_selector_args()
            if resume_selector_args:
                command.extend(resume_selector_args)
            else:
                command.extend(self._bootstrap_args())
                effective_prompt = self._bootstrap_prompt(prompt)

        command.append(effective_prompt)
        if not self._uses_joined_operator_launch_args() or "--output-format" not in self._plan.args:
            command.extend(["--output-format", self._output_format])
        return command, effective_prompt

    def _bootstrap_prompt(self, prompt: str) -> str:
        method = self._plan.role_injection.method
        bootstrap = self._plan.role_injection.bootstrap_message

        if method == "bootstrap_message" and bootstrap:
            return f"{bootstrap}\n\n{prompt}"
        return prompt

    def _bootstrap_args(self) -> list[str]:
        return []

    def _base_command_args(self) -> list[str]:
        return []

    def _resume_args(self, session_id: str) -> list[str]:
        return ["--resume", session_id]

    def _latest_resume_args(self) -> list[str]:
        return []

    def _ensure_tmux_container(self, *, requested_tmux_session_name: str | None) -> None:
        try:
            ensure_tmux_available_shared()
        except TmuxCommandError as exc:
            raise BackendExecutionError(
                "tmux-backed runtimes require `tmux` on PATH. "
                "Install tmux and verify with `command -v tmux`."
            ) from exc

        persisted = (self._state.tmux_session_name or "").strip()
        if persisted:
            has = has_tmux_session_shared(session_name=persisted)
            if has.returncode != 0:
                detail = tmux_error_detail_shared(has) or "unknown tmux error"
                raise BackendExecutionError(
                    "Tmux-backed resume requires existing tmux session "
                    f"`{persisted}` but it is unavailable: {detail}"
                )
            if not self._uses_joined_surface():
                try:
                    prepare_headless_agent_window_shared(session_name=persisted)
                except TmuxCommandError as exc:
                    raise BackendExecutionError(
                        f"Failed to prepare tmux agent surface in `{persisted}`: {exc}"
                    ) from exc
            self._state.tmux_session_name = persisted
            self._publish_tmux_session_environment()
            return

        requested = (requested_tmux_session_name or "").strip()
        session_name = requested
        if not session_name:
            try:
                session_name = generate_tmux_session_name_shared(
                    tool=self._plan.tool,
                    role_name=self._role_name,
                )
            except TmuxCommandError as exc:
                raise BackendExecutionError(str(exc)) from exc

        has = has_tmux_session_shared(session_name=session_name)
        if has.returncode == 0:
            raise BackendExecutionError(
                f"Tmux session `{session_name}` already exists. "
                "Choose a different `--session-name` or stop the existing tmux session first."
            )
        if has.returncode not in {1, 2}:
            detail = tmux_error_detail_shared(has) or "unknown tmux error"
            raise BackendExecutionError(f"Failed to query tmux session `{session_name}`: {detail}")

        created_session = False
        try:
            create_tmux_session_shared(
                session_name=session_name,
                working_directory=self._plan.working_directory,
            )
            created_session = True
            prepare_headless_agent_window_shared(session_name=session_name)
        except TmuxCommandError as exc:
            if created_session:
                try:
                    kill_tmux_session_shared(session_name=session_name)
                except TmuxCommandError:
                    pass
            raise BackendExecutionError(str(exc)) from exc

        self._state.tmux_session_name = session_name
        self._publish_tmux_session_environment()

    def _publish_tmux_session_environment(self) -> None:
        session_name = self._state.tmux_session_name
        if not session_name:
            return

        launch_env = dict(os.environ)
        launch_env.update(self._plan.env)
        launch_env[self._plan.home_env_var] = str(self._plan.home_path)
        inject_loopback_no_proxy_env(launch_env)
        launch_env[AGENT_MANIFEST_PATH_ENV_VAR] = str(self._session_manifest_path)
        if self._agent_def_dir is not None:
            launch_env[AGENT_DEF_DIR_ENV_VAR] = str(self._agent_def_dir)
        launch_env["HOUMAO_TOOL"] = self._plan.tool
        if self._state.session_id:
            launch_env["HOUMAO_RESUME_ID"] = self._state.session_id

        try:
            set_tmux_session_environment_shared(
                session_name=session_name,
                env_vars=launch_env,
            )
        except TmuxCommandError as exc:
            raise BackendExecutionError(
                f"Failed to publish tmux launch environment for `{session_name}`: {exc}"
            ) from exc

    def _require_tmux_session_name(self) -> str:
        session_name = (self._state.tmux_session_name or "").strip()
        if not session_name:
            raise BackendExecutionError(
                f"{self.backend}: missing tmux session binding in backend state"
            )
        return session_name

    def _initial_resume_selector_args(self) -> list[str]:
        """Return the persisted first-turn resume selector args when present."""

        if self._state.resume_selection_kind == "none":
            return []
        if self._state.resume_selection_kind == "last":
            return self._latest_resume_args()
        if self._state.resume_selection_value is None:
            raise BackendExecutionError(
                f"{self.backend}: missing exact resume selector for joined headless launch."
            )
        return self._resume_args(self._state.resume_selection_value)

    def _uses_joined_surface(self) -> bool:
        """Return whether this backend adopts an existing joined tmux surface."""

        return (
            self._state.joined_session or self._plan.metadata.get("session_origin") == "joined_tmux"
        )

    def _uses_joined_operator_launch_args(self) -> bool:
        """Return whether joined headless operator args already describe provider startup."""

        return bool(self._uses_joined_surface() and self.backend != "local_interactive")


def headless_backend_state_payload(state: HeadlessSessionState) -> dict[str, Any]:
    """Convert headless state to manifest backend payload."""

    return {
        "session_id": state.session_id,
        "turn_index": state.turn_index,
        "role_bootstrap_applied": state.role_bootstrap_applied,
        "working_directory": state.working_directory,
        "tmux_session_name": state.tmux_session_name,
        "tmux_window_name": state.tmux_window_name,
        "resume_selection_kind": state.resume_selection_kind,
        "resume_selection_value": state.resume_selection_value,
    }


def _ensure_required_executable(*, executable: str, flow: str) -> None:
    if shutil.which(executable) is not None:
        return
    raise BackendExecutionError(
        f"{flow} requires `{executable}` on PATH. Install the required CLI and "
        f"verify with `command -v {executable}`."
    )
