"""Shared tmux-backed resumable headless backend implementation."""

from __future__ import annotations

import os
import json
import logging
import shutil
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from houmao.execution.context import execution_is_read_only
from houmao.execution.tmux import TmuxPaneRecord, capture_tmux_socket_path

from houmao.agents.kimi_configuration import (
    kimi_launch_diagnostic_secrets,
    load_kimi_config,
    validate_kimi_config_credentials,
)
from houmao.agents.kimi_launch_env import (
    KIMI_API_KEY_ENV,
    KIMI_CONFIG_ENV_NAMES,
    KIMI_PRIVATE_ENV_NAMES,
    reject_kimi_config_env,
)
from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.model_mapping_policy import temporary_project_model_config
from houmao.agents.model_selection import ModelConfig
from houmao.cao.no_proxy import inject_loopback_no_proxy_env
from houmao.agents.realm_controller.usage_support import UsageService, persist_terminal_evidence
from houmao.agents.realm_controller.usage_store import UsageStoreError

from ..agent_identity import AGENT_DEF_DIR_ENV_VAR, AGENT_MANIFEST_PATH_ENV_VAR
from ..boundary_models import SessionManifestTmuxSectionV1
from ..errors import BackendExecutionError, SessionManifestError
from ..managed_terminal import observe_primary_tmux
from ..models import (
    BackendKind,
    HeadlessResumeSelectionKind,
    HeadlessTurnSessionSelection,
    LaunchPlan,
    RelaunchChatSessionSelection,
    SessionControlResult,
    SessionEvent,
)
from .claude_bootstrap import ensure_claude_home_bootstrap as _ensure_claude_home_bootstrap_legacy
from .codex_bootstrap import ensure_codex_home_bootstrap as _ensure_codex_home_bootstrap_legacy
from .dsh_diagnostics import sanitize_dsh_diagnostic
from .headless_output import (
    resolve_headless_display_detail,
    resolve_headless_display_style,
    resolve_headless_provider,
)
from .headless_runner import HeadlessCliRunner, HeadlessRunResult, HeadlessTurnWaitTimeout
from .tmux_runtime import (
    TmuxCommandError,
    create_tmux_session as create_tmux_session_shared,
    ensure_tmux_available as ensure_tmux_available_shared,
    generate_tmux_session_name as generate_tmux_session_name_shared,
    kill_tmux_session as kill_tmux_session_shared,
    overlay_tmux_rich_color_environment,
    prepare_headless_agent_window as prepare_headless_agent_window_shared,
    publish_tmux_launch_environment,
    set_tmux_session_environment as set_tmux_session_environment_shared,
    tmux_session_exists as tmux_session_exists_shared,
)

# Legacy module aliases kept for tests and external monkeypatch hooks. Runtime launch
# policy is resolved before backend execution and no longer invokes these directly.
ensure_claude_home_bootstrap = _ensure_claude_home_bootstrap_legacy
ensure_codex_home_bootstrap = _ensure_codex_home_bootstrap_legacy
_LOGGER = logging.getLogger(__name__)

_TmuxBindingRepair = Callable[
    [SessionManifestTmuxSectionV1, TmuxPaneRecord], SessionManifestTmuxSectionV1
]


@dataclass
class HeadlessSessionState:
    """Persisted resumable state for headless backends."""

    session_id: str | None = None
    turn_index: int = 0
    role_bootstrap_applied: bool = False
    working_directory: str = ""
    tmux_session_name: str | None = None
    tmux_window_name: str | None = None
    tmux_window_id: str | None = None
    tmux_pane_id: str | None = None
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
            "kimi_headless",
            "dsh_acp",
            "dsh_headless",
            "hermes_headless",
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
        self.m_last_run_result: HeadlessRunResult | None = None
        self.m_dispatch_control: HeadlessDispatchControl | None = None
        self.m_tmux_binding: SessionManifestTmuxSectionV1 | None = None
        self.m_tmux_binding_repair: _TmuxBindingRepair | None = None

        if self.backend != "hermes_headless":
            _ensure_required_executable(
                executable=self._plan.executable,
                flow=f"{self.backend} runtime execution",
            )
        if not execution_is_read_only():
            self._ensure_tmux_container(requested_tmux_session_name=tmux_session_name)

    def prepare_stopped_revival(self, *, tmux_session_name: str) -> None:
        """Create a stopped envelope only at an explicit mutating revival boundary."""

        if execution_is_read_only():
            raise BackendExecutionError("Read-only reconstruction cannot prepare a revival surface")
        if self._state.tmux_session_name is None:
            self._ensure_tmux_container(requested_tmux_session_name=tmux_session_name)

    @property
    def state(self) -> HeadlessSessionState:
        """Return current headless backend state."""

        return self._state

    def configure_stop_force_cleanup(self, *, force_cleanup: bool) -> None:
        """Configure whether terminate() should kill the tmux session."""

        self._force_cleanup_on_terminate = force_cleanup

    def configure_request_dispatch(self, control: HeadlessDispatchControl | None) -> None:
        """Fence one immediate gateway request at the actual client launch seam."""

        self.m_dispatch_control = control
        self._runner.set_dispatch_control(control)

    def set_tmux_binding(
        self,
        binding: SessionManifestTmuxSectionV1,
        repair: _TmuxBindingRepair | None = None,
    ) -> None:
        """Install the controller's saved terminal binding and optional repair authority."""

        self.m_tmux_binding = binding
        self.m_tmux_binding_repair = repair
        self._state.tmux_session_name = binding.session_name
        self._state.tmux_window_name = binding.primary_window_name
        self._state.tmux_window_id = binding.primary_window_id
        self._state.tmux_pane_id = binding.primary_pane_id

    def plugin_execution_identity(self) -> tuple[str, ...]:
        """Observe the existing managed generation and stable native surface."""

        try:
            payload = json.loads(self._session_manifest_path.read_text(encoding="utf-8"))
            generation = payload.get("registry_generation_id")
            surface = self._refresh_primary_surface()
        except (OSError, ValueError, AttributeError, TmuxCommandError) as exc:
            raise BackendExecutionError("Cannot observe the current execution incarnation") from exc
        if not isinstance(generation, str) or not generation:
            raise BackendExecutionError("Managed execution generation is unavailable")
        return generation, surface.window_id, surface.pane_id

    def cancel_request_dispatch(self, control: HeadlessDispatchControl) -> None:
        """Revoke one request and signal only its own captured child process."""

        control.cancel()
        if self.m_dispatch_control is control and self.backend != "local_interactive":
            self._runner.cancel_request_dispatch(control)

    def send_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> list[SessionEvent]:
        """Send one prompt turn to the headless backend."""

        if not prompt.strip():
            raise BackendExecutionError("Prompt must not be empty")
        if self._plan.tool == "kimi":
            try:
                reject_kimi_config_env(
                    (*self._plan.env, *self._plan.env_var_names),
                    source="Committed Kimi launch environment",
                )
            except ValueError as exc:
                raise BackendExecutionError(str(exc)) from exc
        if set(self._plan.env_var_names).difference(self._plan.env):
            raise BackendExecutionError(
                "The committed launch environment is incomplete. Relaunch the managed agent "
                "to prepare its runtime inputs."
            )
        turn_id = turn_artifact_dir_name or f"turn-{uuid.uuid4().hex[:12]}"
        if Path(turn_id).name != turn_id or turn_id in {".", ".."}:
            raise BackendExecutionError("Headless turn ID must be one directory name")
        turn_dir = self._turn_artifacts_root / turn_id
        selected_id = (
            session_selection.session_id
            if session_selection is not None and session_selection.mode == "exact"
            else self._state.session_id
        )
        new_session = (session_selection is not None and session_selection.mode == "new") or (
            session_selection is None
            and selected_id is None
            and not self._initial_resume_selector_args()
        )
        service = UsageService.from_launch(self._session_manifest_path, self._plan, selected_id)
        service.begin_headless_turn(
            turn_id=turn_id,
            turn_dir=turn_dir,
            turn_index=self._state.turn_index + 1,
            new_session=new_session,
        )
        self.m_last_run_result = None
        started = time.monotonic()
        try:
            events = self._execute_prompt(
                prompt,
                turn_artifact_dir_name=turn_id,
                session_selection=session_selection,
                execution_model=execution_model,
            )
        except BaseException as exc:
            uncertain_dsh_wait = self.backend in {"dsh_acp", "dsh_headless"} and isinstance(
                exc, HeadlessTurnWaitTimeout
            )
            if not uncertain_dsh_wait and not getattr(
                self._runner, "active_process_running", False
            ):
                result = self.m_last_run_result
                persist_terminal_evidence(
                    turn_dir,
                    returncode=result.returncode if result is not None else 1,
                    completed_at_utc=datetime.now(UTC).isoformat(),
                    wall_time_ms=(time.monotonic() - started) * 1000,
                    interrupted=bool(getattr(self._runner, "m_interrupt_requested", False)),
                )
                try:
                    service.finalize_headless_turn(
                        turn_dir,
                        provider_session_id=result.session_id if result else None,
                        events=result.events if result else None,
                    )
                except Exception:
                    # Durable start/terminal evidence permits recovery after a recorder outage.
                    _LOGGER.warning(
                        "Headless usage recording failed; durable evidence awaits recovery"
                    )
            raise
        result = self.m_last_run_result
        persist_terminal_evidence(
            turn_dir,
            returncode=result.returncode if result is not None else 0,
            completed_at_utc=datetime.now(UTC).isoformat(),
            wall_time_ms=(time.monotonic() - started) * 1000,
            interrupted=bool(getattr(self._runner, "m_interrupt_requested", False)),
        )
        try:
            service.finalize_headless_turn(
                turn_dir,
                provider_session_id=self._state.session_id,
                events=result.events if result else events,
            )
        except (OSError, ValueError, UsageStoreError):
            _LOGGER.warning("Headless usage recording failed; durable evidence awaits recovery")
            events.append(
                SessionEvent(
                    kind="diagnostic",
                    message="Usage finalization is pending recovery",
                    turn_index=self._state.turn_index,
                    payload={"turn_id": turn_id, "diagnostic": "usage_finalization_pending"},
                )
            )
        return events

    def _execute_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> list[SessionEvent]:
        """Execute a registered turn while preserving existing provider semantics."""

        if not prompt.strip():
            raise BackendExecutionError("Prompt must not be empty")

        session_name = self._require_tmux_session_name()
        turn_index = self._state.turn_index + 1
        with temporary_project_model_config(
            home_path=self._plan.home_path,
            tool=self._plan.tool,
            model_config=execution_model,
        ) as execution_projection:
            command, input_prompt = self._build_command(
                prompt=prompt,
                session_selection=session_selection,
                extra_args=execution_projection.args,
            )
            resolved_environment = self._plan.public_env is not None or self._plan.tool == "kimi"
            env: dict[str, str] = {}
            if self._plan.public_env is None:
                env = os.environ.copy()
                if self._plan.tool == "kimi":
                    excluded = (
                        KIMI_CONFIG_ENV_NAMES
                        | KIMI_PRIVATE_ENV_NAMES
                        | self._plan.private_env_var_names
                    )
                    env = {name: value for name, value in env.items() if name not in excluded}
                elif self.backend in {"dsh_acp", "dsh_headless"}:
                    env = {
                        key: value
                        for key, value in env.items()
                        if key in {"PATH", "LANG", "LC_ALL", "SHELL", "TERM", "COLORTERM", "TMPDIR"}
                    }
            env.update(self._plan.env)
            env.update(execution_projection.env)
            if self._plan.tool == "kimi":
                try:
                    key_references = validate_kimi_config_credentials(
                        load_kimi_config(self._plan.home_path / "config.toml"),
                        self._plan.env,
                        self._plan.private_env_var_names,
                    )
                except ValueError as exc:
                    raise BackendExecutionError(str(exc)) from exc
                if KIMI_API_KEY_ENV not in key_references:
                    env.pop(KIMI_API_KEY_ENV, None)
            if self.backend == "dsh_headless":
                setup = self._plan.metadata.get("dsh")
                if isinstance(setup, dict) and isinstance(setup.get("api_key_env"), str):
                    env["HOUMAO_DSH_DIAGNOSTIC_KEY_NAME"] = setup["api_key_env"]
            env[self._plan.home_env_var] = str(self._plan.home_path)
            if self._plan.public_env is None:
                overlay_tmux_rich_color_environment(env)
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
                "tmux_pane_target": self._primary_tmux_pane_target(),
                "turn_artifacts_root": self._turn_artifacts_root,
            }
            if turn_artifact_dir_name is not None:
                run_kwargs["turn_artifact_dir_name"] = turn_artifact_dir_name
            if resolved_environment:
                run_kwargs["replace_environment"] = True

            run_result = self._runner.run(
                **run_kwargs,
            )
            self.m_last_run_result = run_result

        if run_result.returncode != 0:
            message = run_result.stderr.strip()
            if self._plan.tool == "kimi":
                message = sanitize_dsh_diagnostic(
                    message, secret_values=kimi_launch_diagnostic_secrets(env)
                )
            message = message or "headless command failed"
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
                    "turn_id": turn_artifact_dir_name,
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
        session_name = self._state.tmux_session_name
        if runner_result.status == "error":
            if not self._force_cleanup_on_terminate or not session_name:
                return runner_result
            try:
                already_absent = not tmux_session_exists_shared(
                    session_name=session_name, allow_missing_server=True
                )
            except TmuxCommandError:
                return runner_result
            if not already_absent or getattr(self._runner, "active_process_running", False):
                return runner_result

        if not self._force_cleanup_on_terminate:
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

        if not session_name:
            return runner_result
        try:
            if tmux_session_exists_shared(session_name=session_name, allow_missing_server=True):
                self._observe_primary_surface(allow_dead=True)
                kill_tmux_session_shared(session_name=session_name)
        except (TmuxCommandError, BackendExecutionError) as exc:
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

    def relaunch(
        self,
        *,
        chat_session: RelaunchChatSessionSelection | None = None,
    ) -> SessionControlResult:
        """Refresh the stable tmux-backed headless surface on window `0`."""

        session_name = self._require_tmux_session_name()
        try:
            self._primary_tmux_pane_target(allow_dead=True)
            self._apply_relaunch_chat_session(chat_session)
            self._publish_tmux_session_environment()
        except (TmuxCommandError, BackendExecutionError) as exc:
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

    def _apply_relaunch_chat_session(
        self,
        selection: RelaunchChatSessionSelection | None,
    ) -> None:
        """Apply a relaunch-time provider chat selector to the next headless prompt."""

        if selection is None:
            return
        self._state.session_id = None
        self._state.resume_selection_value = None
        if selection.mode == "new":
            self._state.turn_index = 0
            self._state.resume_selection_kind = "none"
            self._state.role_bootstrap_applied = False
            return
        self._state.role_bootstrap_applied = True
        if selection.mode == "tool_last_or_new":
            self._state.resume_selection_kind = "last"
            return
        assert selection.session_id is not None
        self._state.resume_selection_kind = "exact"
        self._state.resume_selection_value = selection.session_id

    def _build_command(
        self,
        *,
        prompt: str,
        session_selection: HeadlessTurnSessionSelection | None = None,
        extra_args: list[str] | None = None,
    ) -> tuple[list[str], str]:
        command = [self._plan.executable, *self._plan.args]
        command.extend(extra_args or [])
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
            try:
                if not tmux_session_exists_shared(session_name=persisted):
                    raise TmuxCommandError("Session does not exist on the owning server")
            except TmuxCommandError as exc:
                raise BackendExecutionError(
                    "Tmux-backed resume requires existing tmux session "
                    f"`{persisted}` but it is unavailable: {exc}"
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

        try:
            already_present = tmux_session_exists_shared(
                session_name=session_name, allow_missing_server=True
            )
        except TmuxCommandError as exc:
            raise BackendExecutionError(
                f"Failed to query tmux session `{session_name}`: {exc}"
            ) from exc
        if already_present:
            raise BackendExecutionError(
                f"Tmux session `{session_name}` already exists. "
                "Choose a different `--session-name` or stop the existing tmux session first."
            )
        created_session = False
        try:
            if self._plan.public_env is None:
                create_tmux_session_shared(
                    session_name=session_name,
                    working_directory=self._plan.working_directory,
                )
            else:
                create_tmux_session_shared(
                    session_name=session_name,
                    working_directory=self._plan.working_directory,
                    launch_plan=self._plan,
                )
            created_session = True
            self._prepare_primary_surface(session_name=session_name, fresh_session=True)
            self._publish_tmux_session_environment()
        except (TmuxCommandError, BackendExecutionError) as exc:
            if created_session:
                try:
                    kill_tmux_session_shared(session_name=session_name)
                except TmuxCommandError:
                    pass
            raise BackendExecutionError(str(exc)) from exc

    def _prepare_primary_surface(
        self,
        *,
        session_name: str,
        fresh_session: bool = False,
    ) -> TmuxPaneRecord:
        """Prepare the Houmao-owned primary tmux surface and store its handles."""

        surface = prepare_headless_agent_window_shared(
            session_name=session_name,
            fresh_session=fresh_session,
        )
        self.set_tmux_binding(
            SessionManifestTmuxSectionV1(
                session_name=surface.session_name,
                socket_path=capture_tmux_socket_path(),
                primary_window_name=surface.window_name,
                primary_window_id=surface.window_id,
                primary_pane_id=surface.pane_id,
            ),
            self.m_tmux_binding_repair,
        )
        return surface

    def _observe_primary_surface(
        self, *, allow_repair: bool = False, allow_dead: bool = False
    ) -> TmuxPaneRecord:
        """Resolve a checked pane and repair the saved binding only when authorized."""

        binding = self.m_tmux_binding
        if binding is None:
            raise TmuxCommandError("Managed primary tmux binding is unavailable")
        observation = observe_primary_tmux(binding, joined=self._uses_joined_surface())
        if observation.pane is not None and (observation.state == "valid" or allow_dead):
            return observation.pane
        repair = self.m_tmux_binding_repair
        if (
            allow_repair
            and not execution_is_read_only()
            and repair is not None
            and observation.replacement is not None
        ):
            replacement = observation.replacement
            updated = repair(binding, replacement)
            self.set_tmux_binding(updated, repair)
            return replacement
        raise TmuxCommandError(
            f"Primary tmux surface for `{binding.session_name}` is {observation.state}"
        )

    def _refresh_primary_surface(self) -> TmuxPaneRecord:
        """Check the saved primary surface for a read-only operation."""

        return self._observe_primary_surface()

    def _primary_tmux_pane_target(
        self, *, allow_dead: bool = False, allow_repair: bool = True
    ) -> str:
        """Return a checked primary pane id for a terminal mutation."""

        session_name = self._require_tmux_session_name()
        try:
            return self._observe_primary_surface(
                allow_repair=allow_repair, allow_dead=allow_dead
            ).pane_id
        except (TmuxCommandError, SessionManifestError) as exc:
            raise BackendExecutionError(
                f"Failed to resolve primary tmux pane in `{session_name}`: {exc}"
            ) from exc

    def _publish_tmux_session_environment(self) -> None:
        """Publish owned launch values or retain the adopted-session projection."""

        session_name = self._state.tmux_session_name
        if not session_name:
            return

        if self._plan.public_env is not None:
            launch_env = dict(self._plan.public_env)
            if self._state.session_id:
                launch_env["HOUMAO_RESUME_ID"] = self._state.session_id
            try:
                publish_tmux_launch_environment(
                    session_name=session_name,
                    launch_plan=replace(
                        self._plan,
                        public_env=launch_env,
                        previous_public_env_var_names=(
                            self._plan.previous_public_env_var_names | {"HOUMAO_RESUME_ID"}
                        ),
                    ),
                )
            except TmuxCommandError as exc:
                raise BackendExecutionError(str(exc)) from exc
            return

        launch_env = dict(os.environ)
        launch_env.update(self._plan.env)
        launch_env[self._plan.home_env_var] = str(self._plan.home_path)
        overlay_tmux_rich_color_environment(launch_env)
        inject_loopback_no_proxy_env(launch_env)
        launch_env[AGENT_MANIFEST_PATH_ENV_VAR] = str(self._session_manifest_path)
        if self._agent_def_dir is not None:
            launch_env[AGENT_DEF_DIR_ENV_VAR] = str(self._agent_def_dir)
        launch_env["HOUMAO_TOOL"] = self._plan.tool
        if self._state.session_id:
            launch_env["HOUMAO_RESUME_ID"] = self._state.session_id

        try:
            if self._plan.tool == "kimi":
                publish_tmux_launch_environment(
                    session_name=session_name,
                    launch_plan=replace(self._plan, public_env=launch_env),
                )
            else:
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
        "tmux_window_id": state.tmux_window_id,
        "tmux_pane_id": state.tmux_pane_id,
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
