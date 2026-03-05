"""Codex headless backend (`codex exec --json` + `resume <thread_id>`)."""

from __future__ import annotations

from pathlib import Path

from .headless_base import HeadlessInteractiveSession, HeadlessSessionState
from ..models import LaunchPlan


class CodexHeadlessSession(HeadlessInteractiveSession):
    """Codex resumable headless backend."""

    def __init__(
        self,
        *,
        launch_plan: LaunchPlan,
        role_name: str,
        session_manifest_path: Path,
        state: HeadlessSessionState | None = None,
        tmux_session_name: str | None = None,
        output_format: str = "stream-json",
    ) -> None:
        super().__init__(
            backend="codex_headless",
            launch_plan=launch_plan,
            role_name=role_name,
            session_manifest_path=session_manifest_path,
            state=state,
            tmux_session_name=tmux_session_name,
            output_format=output_format,
        )

    def _build_command(self, *, prompt: str) -> tuple[list[str], str]:
        command = [self._plan.executable, *self._plan.args]
        if self._plan.role_injection.method == "native_developer_instructions":
            command.extend(
                ["-c", f"developer_instructions={self._plan.role_injection.prompt}"]
            )
        command.extend(["exec", "--json"])
        if self._state.session_id:
            command.extend(["resume", self._state.session_id])
        command.append(prompt)
        return command, prompt
