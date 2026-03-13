from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from houmao.agents.realm_controller import cli
from houmao.agents.realm_controller.backends.headless_base import HeadlessSessionState
from houmao.agents.realm_controller.models import LaunchPlan, SessionControlResult
from houmao.agents.realm_controller.registry_storage import resolve_live_agent_record


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_role(agent_def_dir: Path) -> None:
    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt\n")


def _seed_brain_manifest(tmp_path: Path) -> Path:
    env_file = tmp_path / "vars.env"
    env_file.write_text("ANTHROPIC_API_KEY=secret\n", encoding="utf-8")
    manifest_path = tmp_path / "brain.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "inputs:",
                "  tool: claude",
                "runtime:",
                "  launch_executable: claude",
                "  launch_args: []",
                "  launch_home_selector:",
                "    env_var: CLAUDE_CONFIG_DIR",
                f"    value: {tmp_path / 'home'}",
                "credentials:",
                "  env_contract:",
                f"    source_file: {env_file}",
                "    allowlisted_env_vars:",
                "      - ANTHROPIC_API_KEY",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


class _FakeHeadlessSession:
    def __init__(self, *, tmux_session_name: str, launch_plan: LaunchPlan) -> None:
        self.backend = "claude_headless"
        self.m_launch_plan = launch_plan
        self.m_state = HeadlessSessionState(
            session_id="sess-1",
            turn_index=0,
            role_bootstrap_applied=True,
            working_directory=str(launch_plan.working_directory),
            tmux_session_name=tmux_session_name,
        )

    @property
    def state(self) -> HeadlessSessionState:
        return self.m_state

    def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
        self.m_launch_plan = launch_plan

    def configure_stop_force_cleanup(self, *, force_cleanup: bool) -> None:
        del force_cleanup

    def send_prompt(self, prompt: str) -> list[object]:
        del prompt
        self.m_state = replace(self.m_state, turn_index=self.m_state.turn_index + 1)
        return []

    def interrupt(self) -> SessionControlResult:
        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")

    def terminate(self) -> SessionControlResult:
        return SessionControlResult(status="ok", action="terminate", detail="stopped")

    def close(self) -> None:
        return


def test_cli_runtime_registry_contract_start_send_and_stop(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(
                kwargs.get("agent_identity")
                or kwargs["resume_state"].backend_state["tmux_session_name"]
            ),
            launch_plan=kwargs["launch_plan"],
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )

    start_exit = cli.main(
        [
            "start-session",
            "--agent-def-dir",
            str(agent_def_dir),
            "--runtime-root",
            str(runtime_root),
            "--brain-manifest",
            str(brain_manifest_path),
            "--role",
            "r",
            "--backend",
            "claude_headless",
            "--workdir",
            str(tmp_path),
            "--agent-identity",
            "gpu",
        ]
    )
    start_payload = json.loads(capsys.readouterr().out)
    manifest_path = Path(start_payload["session_manifest"])

    assert start_exit == 0
    started_record = resolve_live_agent_record("gpu")
    assert started_record is not None
    generation_id = started_record.generation_id

    prompt_exit = cli.main(
        [
            "send-prompt",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            str(manifest_path),
            "--prompt",
            "hello",
        ]
    )
    capsys.readouterr()

    assert prompt_exit == 0
    refreshed_record = resolve_live_agent_record("AGENTSYS-gpu")
    assert refreshed_record is not None
    assert refreshed_record.generation_id == generation_id

    stop_exit = cli.main(
        [
            "stop-session",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            str(manifest_path),
        ]
    )
    capsys.readouterr()

    assert stop_exit == 0
    assert resolve_live_agent_record("gpu") is None
