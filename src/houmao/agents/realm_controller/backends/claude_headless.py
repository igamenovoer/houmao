"""Claude headless backend (`claude -p` + `--resume`)."""

from __future__ import annotations

from pathlib import Path

from .headless_base import HeadlessInteractiveSession, HeadlessSessionState
from ..models import LaunchPlan


class ClaudeHeadlessSession(HeadlessInteractiveSession):
    """Claude resumable headless backend."""

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
            backend="claude_headless",
            launch_plan=launch_plan,
            role_name=role_name,
            session_manifest_path=session_manifest_path,
            agent_def_dir=agent_def_dir,
            state=state,
            tmux_session_name=tmux_session_name,
            output_format=output_format,
        )

    def _bootstrap_args(self) -> list[str]:
        if (
            self._plan.role_injection.method == "native_append_system_prompt"
            and self._plan.role_injection.prompt
        ):
            return ["--append-system-prompt", self._plan.role_injection.prompt]
        return []

    def _base_command_args(self) -> list[str]:
        args = ["-p"]
        if self._output_format == "stream-json":
            args.append("--verbose")
        return args

    def _latest_resume_args(self) -> list[str]:
        return ["--continue"]
