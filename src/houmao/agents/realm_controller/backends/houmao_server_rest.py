"""`houmao_server_rest` runtime backend built on the CAO-compatible session core."""

from __future__ import annotations

from pathlib import Path

from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.server.client import HoumaoServerClient

from ..models import CaoParsingMode, LaunchPlan
from .cao_rest import CaoRestSession, CaoSessionState


class HoumaoServerRestSession(CaoRestSession):
    """Runtime session that routes all control through `houmao-server`."""

    backend = "houmao_server_rest"

    def __init__(
        self,
        *,
        launch_plan: LaunchPlan,
        api_base_url: str,
        role_name: str,
        role_prompt: str,
        parsing_mode: CaoParsingMode,
        session_manifest_path: Path | None = None,
        agent_def_dir: Path | None = None,
        agent_identity: str | None = None,
        tmux_session_name: str | None = None,
        profile_store_dir: Path | None = None,
        poll_interval_seconds: float = 0.4,
        timeout_seconds: float = 120.0,
        prepend_role_text: str | None = None,
        append_role_text: str | None = None,
        substitutions: dict[str, str] | None = None,
        existing_state: CaoSessionState | None = None,
    ) -> None:
        client = HoumaoServerClient(api_base_url, timeout_seconds=timeout_seconds)
        try:
            health = client.health_extended()
        except Exception as exc:
            raise BackendExecutionError(
                f"Failed to reach `houmao-server` at {api_base_url}: {exc}"
            ) from exc
        if health.houmao_service != "houmao-server":
            raise BackendExecutionError(
                "backend='houmao_server_rest' requires a real `houmao-server`; "
                "mixed usage with raw `cao-server` is unsupported."
            )

        super().__init__(
            launch_plan=launch_plan,
            api_base_url=api_base_url,
            role_name=role_name,
            role_prompt=role_prompt,
            parsing_mode=parsing_mode,
            session_manifest_path=session_manifest_path,
            agent_def_dir=agent_def_dir,
            agent_identity=agent_identity,
            tmux_session_name=tmux_session_name,
            profile_store_dir=profile_store_dir,
            poll_interval_seconds=poll_interval_seconds,
            timeout_seconds=timeout_seconds,
            prepend_role_text=prepend_role_text,
            append_role_text=append_role_text,
            substitutions=substitutions,
            existing_state=existing_state,
        )
