"""Local interactive tmux-backed runtime backend."""

from __future__ import annotations

import hashlib
import shlex
import time
from pathlib import Path

from houmao.server.tui.process import PaneProcessInspector

from ..errors import BackendExecutionError
from ..mail_commands import (
    MAIL_RESULT_SURFACES_PAYLOAD_KEY,
    MailPromptRequest,
    build_shadow_mail_result_surface_payloads,
    shadow_mail_result_for_request_reached,
)
from ..models import LaunchPlan, SessionControlResult, SessionEvent
from .claude_bootstrap import ensure_claude_home_bootstrap
from .headless_base import HeadlessInteractiveSession, HeadlessSessionState
from .shadow_parser_stack import ShadowParserStack, as_shadow_parser_error
from .tmux_runtime import (
    HEADLESS_AGENT_WINDOW_NAME,
    TmuxCommandError,
    TmuxControlInputError,
    capture_tmux_pane as capture_tmux_pane_shared,
    headless_agent_pane_target as headless_agent_pane_target_shared,
    kill_tmux_session as kill_tmux_session_shared,
    load_tmux_buffer as load_tmux_buffer_shared,
    list_tmux_panes as list_tmux_panes_shared,
    parse_tmux_control_input as parse_tmux_control_input_shared,
    paste_tmux_buffer as paste_tmux_buffer_shared,
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
_POST_PASTE_SUBMIT_DELAY_SECONDS = 0.3
_LOCAL_INTERACTIVE_MAIL_PROMPT_TIMEOUT_SECONDS = 300.0
_LOCAL_INTERACTIVE_MAIL_PROMPT_POLL_INTERVAL_SECONDS = 0.5


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
            self._submit_semantic_prompt(self._plan.role_injection.bootstrap_message)
            self._state.role_bootstrap_applied = True
        self._submit_semantic_prompt(prompt)
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

    def send_mail_prompt(self, prompt_request: MailPromptRequest) -> list[SessionEvent]:
        """Send one mailbox prompt and observe the live TUI for the result sentinel."""

        if not prompt_request.prompt.strip():
            raise BackendExecutionError("Prompt must not be empty")

        parser_stack = self._shadow_parser_stack()
        baseline_output = self._capture_live_pane_output()
        try:
            baseline_snapshot = parser_stack.parse_snapshot(baseline_output, baseline_pos=0)
        except Exception as exc:
            normalized = as_shadow_parser_error(exc)
            raise BackendExecutionError(
                f"Failed to parse local interactive baseline for mailbox prompt: {normalized}"
            ) from exc
        baseline_pos = parser_stack.capture_baseline_pos(baseline_output)

        self._submit_runtime_prompt(prompt_request.prompt)
        turn_index = self._state.turn_index
        submitted_event = SessionEvent(
            kind="submitted",
            message="prompt submitted",
            turn_index=turn_index,
            payload={"tmux_session_name": self._require_tmux_session_name()},
        )
        completion_payload = self._wait_for_mail_result_surfaces(
            parser_stack=parser_stack,
            baseline_output=baseline_output,
            baseline_projection=baseline_snapshot.dialog_projection,
            baseline_pos=baseline_pos,
            prompt_request=prompt_request,
        )
        return [
            submitted_event,
            SessionEvent(
                kind="done",
                message="prompt completed",
                turn_index=turn_index,
                payload=completion_payload,
            ),
        ]

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

    def relaunch(self) -> SessionControlResult:
        """Respawn the provider TUI on the stable tmux window `0` surface."""

        try:
            self._launch_provider_surface()
            self._apply_startup_bootstrap()
        except BackendExecutionError as exc:
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail=str(exc),
            )

        return SessionControlResult(
            status="ok",
            action="relaunch",
            detail=(
                "Local interactive provider surface relaunched on tmux window `0` without "
                "rebuilding the agent home."
            ),
        )

    def _launch_provider_surface(self) -> None:
        self._prepare_tool_home()
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

        if not self._uses_joined_surface():
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

    def _prepare_tool_home(self) -> None:
        """Apply tool-specific runtime-home bootstrap before launch."""

        if self._plan.tool == "claude":
            ensure_claude_home_bootstrap(home_path=self._plan.home_path, env=self._plan.env)

    def _build_launch_command(self) -> list[str]:
        command = [self._plan.executable, *self._plan.args]
        if (
            self._plan.role_injection.method == "native_developer_instructions"
            and self._plan.role_injection.prompt
        ):
            command.extend(["-c", f"developer_instructions={self._plan.role_injection.prompt}"])
        elif (
            self._plan.role_injection.method == "native_append_system_prompt"
            and self._plan.role_injection.prompt
        ):
            command.extend(["--append-system-prompt", self._plan.role_injection.prompt])
        return command

    def _apply_startup_bootstrap(self) -> None:
        bootstrap = self._plan.role_injection.bootstrap_message
        if self._plan.role_injection.method != "bootstrap_message" or not bootstrap:
            return
        time.sleep(0.2)
        self._submit_semantic_prompt(bootstrap)
        self._state.role_bootstrap_applied = True

    def _submit_runtime_prompt(self, prompt: str) -> None:
        """Submit one runtime-owned prompt after any launch-time bootstrap."""

        if (
            not self._state.role_bootstrap_applied
            and self._plan.role_injection.method == "bootstrap_message"
            and self._plan.role_injection.bootstrap_message
        ):
            self._submit_semantic_prompt(self._plan.role_injection.bootstrap_message)
            self._state.role_bootstrap_applied = True
        self._submit_semantic_prompt(prompt)
        self._state.turn_index += 1

    def _submit_semantic_prompt(self, text: str) -> None:
        """Paste literal prompt text and submit it as a separate tmux phase."""

        session_name = self._require_tmux_session_name()
        pane_target = headless_agent_pane_target_shared(session_name=session_name)
        buffer_name = self._prompt_buffer_name(session_name)
        try:
            load_tmux_buffer_shared(buffer_name=buffer_name, text=text)
            paste_tmux_buffer_shared(
                target=pane_target,
                buffer_name=buffer_name,
                bracketed_paste=True,
            )
            time.sleep(_POST_PASTE_SUBMIT_DELAY_SECONDS)
            send_tmux_control_input_shared(
                target=pane_target,
                segments=parse_tmux_control_input_shared(sequence="<[Enter]>"),
            )
        except (TmuxCommandError, TmuxControlInputError) as exc:
            raise BackendExecutionError(
                f"Failed to submit prompt to local interactive session: {exc}"
            ) from exc

    def _shadow_parser_stack(self) -> ShadowParserStack:
        """Return the shadow parser stack required for mailbox observation."""

        try:
            return ShadowParserStack(tool=self._plan.tool)
        except ValueError as exc:
            raise BackendExecutionError(
                f"Mailbox prompts are unsupported for local_interactive tool {self._plan.tool!r}: "
                "no shadow parser is available."
            ) from exc

    def _capture_live_pane_output(self) -> str:
        """Return the current tmux pane capture for the stable interactive surface."""

        try:
            return capture_tmux_pane_shared(
                target=headless_agent_pane_target_shared(
                    session_name=self._require_tmux_session_name()
                )
            )
        except TmuxCommandError as exc:
            raise BackendExecutionError(
                f"Failed to capture local interactive pane output: {exc}"
            ) from exc

    def _wait_for_mail_result_surfaces(
        self,
        *,
        parser_stack: ShadowParserStack,
        baseline_output: str,
        baseline_projection: object,
        baseline_pos: int,
        prompt_request: MailPromptRequest,
    ) -> dict[str, object]:
        """Poll the live TUI until the mailbox sentinel block is observable."""

        deadline = time.monotonic() + _LOCAL_INTERACTIVE_MAIL_PROMPT_TIMEOUT_SECONDS
        last_output = baseline_output
        last_error: str | None = None
        mailbox = self._plan.mailbox
        if mailbox is None:
            raise BackendExecutionError("Local interactive mailbox prompt requires a resolved mailbox.")
        while time.monotonic() < deadline:
            self._ensure_provider_tui_alive()
            current_output = self._capture_live_pane_output()
            last_output = current_output
            try:
                current_snapshot = parser_stack.parse_snapshot(current_output, baseline_pos=baseline_pos)
            except Exception as exc:
                normalized = as_shadow_parser_error(exc)
                last_error = str(normalized)
                time.sleep(_LOCAL_INTERACTIVE_MAIL_PROMPT_POLL_INTERVAL_SECONDS)
                continue

            surface_payloads = build_shadow_mail_result_surface_payloads(
                raw_output_text=current_output,
                current_projection=current_snapshot.dialog_projection,
                baseline_output_text=baseline_output,
                baseline_projection=baseline_projection,
            )
            if shadow_mail_result_for_request_reached(
                surface_payloads,
                request_id=prompt_request.request_id,
                operation=prompt_request.operation,
                mailbox=mailbox,
            ):
                return {
                    "tmux_session_name": self._require_tmux_session_name(),
                    MAIL_RESULT_SURFACES_PAYLOAD_KEY: list(surface_payloads),
                    "dialog_projection": {
                        "raw_text": current_snapshot.dialog_projection.raw_text,
                        "normalized_text": current_snapshot.dialog_projection.normalized_text,
                        "dialog_text": current_snapshot.dialog_projection.dialog_text,
                        "head": current_snapshot.dialog_projection.head,
                        "tail": current_snapshot.dialog_projection.tail,
                    },
                }
            time.sleep(_LOCAL_INTERACTIVE_MAIL_PROMPT_POLL_INTERVAL_SECONDS)

        final_payload = self._try_collect_mail_result_payload(
            parser_stack=parser_stack,
            baseline_output=baseline_output,
            baseline_projection=baseline_projection,
            baseline_pos=baseline_pos,
            prompt_request=prompt_request,
        )
        if final_payload is not None:
            return final_payload

        detail = (
            "Timed out waiting for the local interactive mailbox result sentinel."
        )
        if last_error:
            detail = f"{detail} Last parser error: {last_error}."
        excerpt = last_output.strip()
        if excerpt:
            detail = f"{detail}\n\nPane output:\n{excerpt[-1200:]}"
        raise BackendExecutionError(detail)

    def _try_collect_mail_result_payload(
        self,
        *,
        parser_stack: ShadowParserStack,
        baseline_output: str,
        baseline_projection: object,
        baseline_pos: int,
        prompt_request: MailPromptRequest,
    ) -> dict[str, object] | None:
        """Capture and parse the current pane once, returning the mailbox payload when present."""

        current_output = self._capture_live_pane_output()
        try:
            current_snapshot = parser_stack.parse_snapshot(current_output, baseline_pos=baseline_pos)
        except Exception:
            return None

        surface_payloads = build_shadow_mail_result_surface_payloads(
            raw_output_text=current_output,
            current_projection=current_snapshot.dialog_projection,
            baseline_output_text=baseline_output,
            baseline_projection=baseline_projection,
        )
        mailbox = self._plan.mailbox
        if mailbox is None:
            return None
        if not shadow_mail_result_for_request_reached(
            surface_payloads,
            request_id=prompt_request.request_id,
            operation=prompt_request.operation,
            mailbox=mailbox,
        ):
            return None
        return {
            "tmux_session_name": self._require_tmux_session_name(),
            MAIL_RESULT_SURFACES_PAYLOAD_KEY: list(surface_payloads),
            "dialog_projection": {
                "raw_text": current_snapshot.dialog_projection.raw_text,
                "normalized_text": current_snapshot.dialog_projection.normalized_text,
                "dialog_text": current_snapshot.dialog_projection.dialog_text,
                "head": current_snapshot.dialog_projection.head,
                "tail": current_snapshot.dialog_projection.tail,
            },
        }

    def _ensure_provider_tui_alive(self) -> None:
        """Raise when the tracked provider process is no longer live."""

        session_name = self._require_tmux_session_name()
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
        inspection = self._process_inspector.inspect(tool=self._plan.tool, pane_pid=pane.pane_pid)
        if inspection.process_state == "tui_up":
            return
        raise BackendExecutionError(
            f"Local interactive mailbox prompt failed because the {self._plan.tool} TUI is no "
            f"longer live (state={inspection.process_state})."
        )

    def _prompt_buffer_name(self, session_name: str) -> str:
        """Return the stable tmux buffer name used for semantic prompt submission."""

        digest = hashlib.md5(
            session_name.encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()[:16]
        return f"houmao-submit-prompt-{digest}"

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
