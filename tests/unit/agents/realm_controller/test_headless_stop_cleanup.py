from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from houmao.agents.realm_controller.backends.codex_headless import (
    CodexHeadlessSession,
)
from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessSessionState,
)
from houmao.agents.realm_controller.backends.tmux_runtime import TmuxCommandError
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
    SessionControlResult,
)


def _sample_codex_launch_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="codex_headless",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={"OPENAI_API_KEY": "sk-secret"},
        env_var_names=["OPENAI_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="gpu-kernel-coder",
            prompt="role prompt",
        ),
        metadata={},
    )


@pytest.fixture(autouse=True)
def _stub_tmux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.HeadlessInteractiveSession._observe_primary_surface",
        lambda self, **_: SimpleNamespace(pane_id="%9"),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.ensure_tmux_available_shared",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.tmux_session_exists_shared",
        lambda **_: True,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.set_tmux_session_environment_shared",
        lambda *, session_name, env_vars: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.prepare_headless_agent_window_shared",
        lambda *, session_name: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.ensure_codex_home_bootstrap",
        lambda *, home_path, env, working_directory: None,
    )


def test_headless_terminate_preserves_tmux_by_default(tmp_path: Path) -> None:
    session = CodexHeadlessSession(
        launch_plan=_sample_codex_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-codex",
        ),
    )

    class _FakeRunner:
        def terminate(self) -> SessionControlResult:
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="No active headless process",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]
    result = session.terminate()

    assert result.status == "ok"
    assert "preserved tmux session" in result.detail
    assert session.state.tmux_session_name == "HOUMAO-codex"


def test_headless_terminate_force_cleanup_kills_tmux(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    session = CodexHeadlessSession(
        launch_plan=_sample_codex_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-codex",
        ),
    )
    captured: dict[str, str] = {}

    class _FakeRunner:
        def terminate(self) -> SessionControlResult:
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="No active headless process",
            )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.kill_tmux_session_shared",
        lambda *, session_name: captured.setdefault("session_name", session_name),
    )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]
    session.configure_stop_force_cleanup(force_cleanup=True)
    result = session.terminate()

    assert result.status == "ok"
    assert "deleted tmux session" in result.detail
    assert captured["session_name"] == "HOUMAO-codex"
    assert session.state.tmux_session_name is None


@pytest.mark.parametrize("runner_error", [False, True])
def test_headless_force_cleanup_succeeds_for_proven_absent_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, runner_error: bool
) -> None:
    """A last-window removal can finish cleanup before the native backend does."""

    session = CodexHeadlessSession(
        launch_plan=_sample_codex_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path), tmux_session_name="HOUMAO-codex"
        ),
    )

    class Runner:
        """Represent a stopped child with possibly stale tmux pane metadata."""

        active_process_running = False

        def terminate(self) -> SessionControlResult:
            """Report a stale-pane error only after the child is absent."""

            return SessionControlResult(
                status="error" if runner_error else "ok", action="terminate", detail="stale pane"
            )

    def absent(**_: object) -> None:
        """Report tmux's existing-session cleanup error."""

        raise TmuxCommandError("Owned session is already absent")

    session._runner = Runner()  # type: ignore[assignment]
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.kill_tmux_session_shared", absent
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.tmux_session_exists_shared",
        lambda **_: False,
    )
    session.configure_stop_force_cleanup(force_cleanup=True)
    result = session.terminate()
    assert result.status == "ok"
    assert session.state.tmux_session_name is None
