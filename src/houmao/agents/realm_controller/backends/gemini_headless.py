"""Gemini headless backend (`gemini -p` + `--resume`)."""

from __future__ import annotations

from pathlib import Path

from .headless_base import HeadlessInteractiveSession, HeadlessSessionState
from ..models import LaunchPlan


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
