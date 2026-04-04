"""Codex headless backend (`codex exec --json` + `resume <thread_id>`)."""

from __future__ import annotations

from pathlib import Path

from .headless_base import HeadlessInteractiveSession, HeadlessSessionState
from ..models import HeadlessTurnSessionSelection, LaunchPlan


class CodexHeadlessSession(HeadlessInteractiveSession):
    """Codex resumable headless backend."""

    def __init__(
        self,
        *,
        launch_plan: LaunchPlan,
        role_name: str,
        session_manifest_path: Path,
        agent_def_dir: Path | None = None,
        state: HeadlessSessionState | None = None,
        tmux_session_name: str | None = None,
        output_format: str = "stream-json",
    ) -> None:
        super().__init__(
            backend="codex_headless",
            launch_plan=launch_plan,
            role_name=role_name,
            session_manifest_path=session_manifest_path,
            agent_def_dir=agent_def_dir,
            state=state,
            tmux_session_name=tmux_session_name,
            output_format=output_format,
        )

    def _build_command(
        self,
        *,
        prompt: str,
        session_selection: HeadlessTurnSessionSelection | None = None,
    ) -> tuple[list[str], str]:
        if self._uses_joined_operator_launch_args():
            command = [self._plan.executable, *self._plan.args]
            if session_selection is not None:
                if session_selection.mode == "exact":
                    assert session_selection.session_id is not None
                    command.extend(self._resume_args(session_selection.session_id))
                elif session_selection.mode == "tool_last_or_new":
                    command.extend(self._latest_resume_args())
            elif self._state.session_id:
                command.extend(self._resume_args(self._state.session_id))
            else:
                command.extend(self._initial_resume_selector_args())
            command.append(prompt)
            return command, prompt

        command = [self._plan.executable, *self._plan.args]
        if (
            self._plan.role_injection.method == "native_developer_instructions"
            and self._plan.role_injection.prompt
        ):
            command.extend(["-c", f"developer_instructions={self._plan.role_injection.prompt}"])
        command.extend(["exec", "--json"])
        if session_selection is not None:
            if session_selection.mode == "exact":
                assert session_selection.session_id is not None
                command.extend(self._resume_args(session_selection.session_id))
            elif session_selection.mode == "tool_last_or_new":
                command.extend(self._latest_resume_args())
        elif self._state.session_id:
            command.extend(self._resume_args(self._state.session_id))
        command.append(prompt)
        return command, prompt

    def _resume_args(self, session_id: str) -> list[str]:
        return ["resume", session_id]

    def _latest_resume_args(self) -> list[str]:
        return ["resume", "--last"]
