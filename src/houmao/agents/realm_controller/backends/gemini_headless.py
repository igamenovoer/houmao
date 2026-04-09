"""Gemini headless backend (`gemini -p` + `--resume`)."""

from __future__ import annotations

from pathlib import Path

from .headless_base import HeadlessInteractiveSession, HeadlessSessionState
from ..models import HeadlessTurnSessionSelection, LaunchPlan


class GeminiHeadlessSession(HeadlessInteractiveSession):
    """Gemini resumable headless backend."""

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
            backend="gemini_headless",
            launch_plan=launch_plan,
            role_name=role_name,
            session_manifest_path=session_manifest_path,
            agent_def_dir=agent_def_dir,
            state=state,
            tmux_session_name=tmux_session_name,
            output_format=output_format,
        )

    def _base_command_args(self) -> list[str]:
        return ["-p"]

    def _build_command(
        self,
        *,
        prompt: str,
        session_selection: HeadlessTurnSessionSelection | None = None,
    ) -> tuple[list[str], str]:
        if self._uses_joined_operator_launch_args():
            return super()._build_command(prompt=prompt, session_selection=session_selection)

        command = [self._plan.executable, *self._plan.args]
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

        # Gemini requires the prompt token immediately after `-p` / `--prompt`.
        command.extend(["-p", effective_prompt])
        if "--output-format" not in self._plan.args:
            command.extend(["--output-format", self._output_format])
        return command, effective_prompt

    def _latest_resume_args(self) -> list[str]:
        return ["--resume", "latest"]
