from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.server.config import HoumaoServerConfig
from houmao.server.control_core.core import (
    CompatibilityControlCore,
    PreparedNativeCompatibilityLaunch,
)
from houmao.server.control_core.models import CompatibilityAgentProfile, CompatibilityTerminalRecord


class _FakeTmuxController:
    def __init__(self) -> None:
        self.m_wait_for_shell_calls: list[dict[str, object]] = []
        self.m_send_command_calls: list[dict[str, object]] = []

    def wait_for_shell(
        self,
        *,
        window_id: str,
        timeout_seconds: float,
        polling_interval_seconds: float,
    ) -> None:
        self.m_wait_for_shell_calls.append(
            {
                "window_id": window_id,
                "timeout_seconds": timeout_seconds,
                "polling_interval_seconds": polling_interval_seconds,
            }
        )

    def send_command(self, *, window_id: str, command: str) -> None:
        self.m_send_command_calls.append({"window_id": window_id, "command": command})


class _FakeAdapter:
    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        self.m_wait_until_ready_calls: list[dict[str, object]] = []

    def build_command(
        self,
        *,
        profile: CompatibilityAgentProfile,
        profile_name: str,
        terminal_id: str,
        working_directory: Path,
    ) -> str:
        del profile, profile_name, terminal_id, working_directory
        return "provider --start"

    def wait_until_ready(
        self,
        *,
        tmux: _FakeTmuxController,
        window_id: str,
        profile_name: str,
        timeout_seconds: float,
        polling_interval_seconds: float,
    ) -> None:
        self.m_wait_until_ready_calls.append(
            {
                "tmux": tmux,
                "window_id": window_id,
                "profile_name": profile_name,
                "timeout_seconds": timeout_seconds,
                "polling_interval_seconds": polling_interval_seconds,
            }
        )


def test_initialize_terminal_uses_default_compatibility_timing_config(
    monkeypatch,
    tmp_path: Path,
) -> None:
    sleep_calls: list[float] = []
    monkeypatch.setattr("houmao.server.control_core.core.time.sleep", sleep_calls.append)
    tmux = _FakeTmuxController()
    adapter = _FakeAdapter("codex")
    core = CompatibilityControlCore(config=HoumaoServerConfig(runtime_root=tmp_path), tmux_controller=tmux)

    core._initialize_terminal(
        terminal_record=_sample_terminal_record(tmp_path),
        working_directory=tmp_path,
        prepared_provider_profile=_prepared_profile("codex"),
        adapter=adapter,
    )

    assert tmux.m_wait_for_shell_calls == [
        {
            "window_id": "@1",
            "timeout_seconds": 10.0,
            "polling_interval_seconds": 0.5,
        }
    ]
    assert len(adapter.m_wait_until_ready_calls) == 1
    assert adapter.m_wait_until_ready_calls[0]["tmux"] is tmux
    assert adapter.m_wait_until_ready_calls[0]["window_id"] == "@1"
    assert adapter.m_wait_until_ready_calls[0]["profile_name"] == "gpu-kernel-coder"
    assert adapter.m_wait_until_ready_calls[0]["timeout_seconds"] == 45.0
    assert adapter.m_wait_until_ready_calls[0]["polling_interval_seconds"] == 1.0
    assert tmux.m_send_command_calls == [
        {"window_id": "@1", "command": "echo ready"},
        {
            "window_id": "@1",
            "command": (
                "export HOME=/tmp/houmao-test-launch-home/codex; "
                "export CODEX_HOME=/tmp/houmao-test-launch-home/codex; "
                "export CAO_TERMINAL_ID=abcd1234; provider --start"
            ),
        },
    ]
    assert sleep_calls == [2.0]


def test_initialize_terminal_uses_override_timing_and_allows_zero_warmup(
    monkeypatch,
    tmp_path: Path,
) -> None:
    sleep_calls: list[float] = []
    monkeypatch.setattr("houmao.server.control_core.core.time.sleep", sleep_calls.append)
    config = HoumaoServerConfig(
        runtime_root=tmp_path,
        compat_shell_ready_timeout_seconds=20.0,
        compat_shell_ready_poll_interval_seconds=0.25,
        compat_provider_ready_timeout_seconds=90.0,
        compat_provider_ready_poll_interval_seconds=0.75,
        compat_codex_warmup_seconds=0.0,
    )
    tmux = _FakeTmuxController()
    adapter = _FakeAdapter("codex")
    core = CompatibilityControlCore(config=config, tmux_controller=tmux)

    core._initialize_terminal(
        terminal_record=_sample_terminal_record(tmp_path),
        working_directory=tmp_path,
        prepared_provider_profile=_prepared_profile("codex"),
        adapter=adapter,
    )

    assert tmux.m_wait_for_shell_calls == [
        {
            "window_id": "@1",
            "timeout_seconds": 20.0,
            "polling_interval_seconds": 0.25,
        }
    ]
    assert len(adapter.m_wait_until_ready_calls) == 1
    assert adapter.m_wait_until_ready_calls[0]["timeout_seconds"] == 90.0
    assert adapter.m_wait_until_ready_calls[0]["polling_interval_seconds"] == 0.75
    assert sleep_calls == []


def test_initialize_terminal_exports_claude_config_dir_home_selector(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("houmao.server.control_core.core.time.sleep", lambda _seconds: None)
    tmux = _FakeTmuxController()
    adapter = _FakeAdapter("claude_code")
    core = CompatibilityControlCore(config=HoumaoServerConfig(runtime_root=tmp_path), tmux_controller=tmux)

    core._initialize_terminal(
        terminal_record=_sample_terminal_record(tmp_path),
        working_directory=tmp_path,
        prepared_provider_profile=_prepared_profile("claude_code"),
        adapter=adapter,
    )

    assert tmux.m_send_command_calls == [
        {
            "window_id": "@1",
            "command": (
                "export HOME=/tmp/houmao-test-launch-home/claude; "
                "export CLAUDE_CONFIG_DIR=/tmp/houmao-test-launch-home/claude; "
                "export ANTHROPIC_API_KEY=anthropic-test-key; "
                "export ANTHROPIC_BASE_URL=https://anthropic.test; "
                "export CAO_TERMINAL_ID=abcd1234; provider --start"
            ),
        }
    ]


def test_prepare_native_launch_projection_accepts_missing_role_as_brain_only(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tmux = _FakeTmuxController()
    core = CompatibilityControlCore(config=HoumaoServerConfig(runtime_root=tmp_path), tmux_controller=tmux)
    capture: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.server.control_core.core.resolve_native_launch_target",
        lambda **_kwargs: SimpleNamespace(
            selector="gpu-kernel-coder",
            provider="codex",
            tool="codex",
            working_directory=tmp_path,
            agent_def_dir=(tmp_path / "agents").resolve(),
            recipe_path=(tmp_path / "agents" / "brains" / "brain-recipes" / "codex" / "x.yaml").resolve(),
            recipe=SimpleNamespace(
                tool="codex",
                skills=[],
                config_profile="default",
                credential_profile="demo-default",
                launch_overrides=None,
                mailbox=None,
                default_agent_name="cao-codex-demo",
            ),
            role_name=None,
            role_prompt="",
            role_prompt_path=None,
        ),
    )
    monkeypatch.setattr(
        "houmao.server.control_core.core.build_brain_home",
        lambda _request: SimpleNamespace(manifest_path=(tmp_path / "manifest.yaml").resolve()),
    )
    monkeypatch.setattr(
        "houmao.server.control_core.core.load_brain_manifest",
        lambda _path: {"inputs": {"tool": "codex"}},
    )

    def _capture_launch_plan(request: object) -> LaunchPlan:
        capture["request"] = request
        return _prepared_profile("codex").launch_plan

    monkeypatch.setattr(
        "houmao.server.control_core.core.build_launch_plan",
        _capture_launch_plan,
    )

    prepared = core._prepare_native_launch_projection(
        selector="gpu-kernel-coder",
        provider="codex",
        working_directory=tmp_path,
    )

    assert prepared.profile.system_prompt == ""
    assert prepared.profile.provider == "codex"
    request = capture["request"]
    assert getattr(request, "role_package").role_name == "brain-only"
    assert getattr(request, "role_package").system_prompt == ""


def _prepared_profile(provider_id: str) -> PreparedNativeCompatibilityLaunch:
    launch_home = (
        Path("/tmp")
        / "houmao-test-launch-home"
        / ("codex" if provider_id == "codex" else "claude")
    ).resolve()
    home_env_var = "CODEX_HOME" if provider_id == "codex" else "CLAUDE_CONFIG_DIR"
    env = (
        {
            "ANTHROPIC_API_KEY": "anthropic-test-key",
            "ANTHROPIC_BASE_URL": "https://anthropic.test",
        }
        if provider_id == "claude_code"
        else {}
    )
    return PreparedNativeCompatibilityLaunch(
        profile=CompatibilityAgentProfile(name="gpu-kernel-coder", description="GPU role"),
        resolved_provider=provider_id,
        launch_plan=LaunchPlan(
            backend="houmao_server_rest",
            tool="codex" if provider_id == "codex" else "claude",
            executable="cao",
            args=[],
            working_directory=Path("/tmp").resolve(),
            home_env_var=home_env_var,
            home_path=launch_home,
            env=env,
            env_var_names=sorted(env),
            role_injection=RoleInjectionPlan(
                method="cao_profile",
                role_name="gpu-kernel-coder",
                prompt="",
            ),
        ),
    )


def _sample_terminal_record(tmp_path: Path) -> CompatibilityTerminalRecord:
    return CompatibilityTerminalRecord(
        terminal_id="abcd1234",
        session_name="cao-gpu",
        window_name="developer-1",
        window_id="@1",
        window_index="1",
        provider="codex",
        agent_profile="gpu-kernel-coder",
        working_directory=str(tmp_path),
    )
