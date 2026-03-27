"""`houmao_server_rest` runtime backend built on the CAO-compatible session core."""

from __future__ import annotations

from pathlib import Path

from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.cao.rest_client import CaoRestClient
from houmao.server.config import HoumaoServerConfig
from houmao.server.client import HoumaoServerClient

from ..models import CaoParsingMode, LaunchPlan, SessionControlResult
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
            current_instance = client.current_instance()
        except Exception as exc:
            raise BackendExecutionError(
                f"Failed to reach `houmao-server` at {api_base_url}: {exc}"
            ) from exc
        if health.houmao_service != "houmao-server":
            raise BackendExecutionError(
                "backend='houmao_server_rest' requires a real `houmao-server`; "
                "mixed usage with raw `cao-server` is unsupported."
            )

        resolved_profile_store_dir = profile_store_dir
        if resolved_profile_store_dir is None and existing_state is None:
            server_root = Path(current_instance.server_root).expanduser().resolve()
            derived_config = HoumaoServerConfig(api_base_url=api_base_url)
            if derived_config.server_root != server_root:
                derived_config = derived_config.model_copy(
                    update={"runtime_root": server_root.parent.parent}
                )
            resolved_profile_store_dir = derived_config.compatibility_agent_store_dir

        super().__init__(
            launch_plan=launch_plan,
            api_base_url=api_base_url,
            client=CaoRestClient(
                api_base_url,
                timeout_seconds=timeout_seconds,
                path_prefix="/cao",
            ),
            role_name=role_name,
            role_prompt=role_prompt,
            parsing_mode=parsing_mode,
            session_manifest_path=session_manifest_path,
            agent_def_dir=agent_def_dir,
            agent_identity=agent_identity,
            tmux_session_name=tmux_session_name,
            profile_store_dir=resolved_profile_store_dir,
            poll_interval_seconds=poll_interval_seconds,
            timeout_seconds=timeout_seconds,
            prepend_role_text=prepend_role_text,
            append_role_text=append_role_text,
            substitutions=substitutions,
            existing_state=existing_state,
        )

    def _preflight_start_terminal(self) -> None:
        """Require only the tool executable for pair-backed compatibility startup."""

        from .cao_rest import _ensure_required_executable

        _ensure_required_executable(
            executable=self._plan.executable,
            flow=f"pair-backed `{self._plan.tool}` flow",
        )

    def relaunch(self) -> SessionControlResult:
        """Recreate the pair-managed terminal on the stable tmux window `0` surface."""

        try:
            new_terminal_id = self._relaunch_existing_terminal(primary_window_index="0")
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
                "Pair-managed terminal relaunched on tmux window `0` without rebuilding the "
                f"agent home (terminal_id={new_terminal_id})."
            ),
        )
