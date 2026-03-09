from __future__ import annotations

from pathlib import Path

import pytest

from gig_agents.agents.brain_launch_runtime.backends.cao_rest import CaoRestSession
from gig_agents.agents.brain_launch_runtime.models import LaunchPlan, RoleInjectionPlan
from gig_agents.cao.models import (
    CaoHealthResponse,
    CaoSuccessResponse,
    CaoTerminal,
    CaoTerminalOutputResponse,
)


def _sample_launch_plan(tmp_path: Path) -> LaunchPlan:
    env_file = tmp_path / "codex-vars.env"
    env_file.write_text("OPENAI_API_KEY=from-profile\n", encoding="utf-8")
    return LaunchPlan(
        backend="cao_rest",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={"OPENAI_API_KEY": "secret"},
        env_var_names=["OPENAI_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="gpu-kernel-coder",
            prompt="Be precise",
        ),
        metadata={"env_source_file": str(env_file)},
    )


def test_shadow_only_runtime_returns_projection_payload_and_waits_for_real_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_sequence = [
        "Codex CLI v0.1.0\n> \n",
        "Codex CLI v0.1.0\n> \n",
        "Codex CLI v0.1.0\n> \n",
        "Codex CLI v0.1.0\n> hello\nassistant> final answer\n> \n",
    ]

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self.output_calls = 0

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError("shadow_only mode must not call terminal status API")

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self,
            terminal_id: str,
            mode: str = "full",
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            index = min(self.output_calls, len(output_sequence) - 1)
            self.output_calls += 1
            return CaoTerminalOutputResponse(output=output_sequence[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.backends.cao_rest.ensure_codex_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        session_manifest_path=tmp_path / "session-codex-shadow.json",
    )

    events = session.send_prompt("hello")

    done_event = events[-1]
    done_payload = done_event.payload or {}

    assert done_event.message == "prompt completed"
    assert done_payload["canonical_runtime_status"] == "completed"
    assert "output_text" not in done_payload
    assert done_payload["surface_assessment"]["activity"] == "ready_for_input"
    assert done_payload["dialog_projection"]["dialog_text"] == "hello\nfinal answer"
    assert done_payload["projection_slices"] == {
        "head": "hello\nfinal answer",
        "tail": "hello\nfinal answer",
    }
    assert "debug_transport_tail_excerpt" in done_payload["mode_diagnostics"]
    assert session._client.output_calls == 4  # noqa: SLF001
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001
