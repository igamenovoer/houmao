from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from houmao.server.config import HoumaoServerConfig
from houmao.server.control_core.core import CompatibilityControlCore
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
                f"export HOME={tmp_path / 'houmao_servers' / '127.0.0.1-9889' / 'compat_home'}; "
                f"export CODEX_HOME={tmp_path / 'houmao_servers' / '127.0.0.1-9889' / 'compat_home'}; "
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
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://anthropic.test")
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
                f"export HOME={tmp_path / 'houmao_servers' / '127.0.0.1-9889' / 'compat_home'}; "
                f"export CLAUDE_CONFIG_DIR={tmp_path / 'houmao_servers' / '127.0.0.1-9889' / 'compat_home'}; "
                "export ANTHROPIC_API_KEY=anthropic-test-key; "
                "export ANTHROPIC_BASE_URL=https://anthropic.test; "
                "export CAO_TERMINAL_ID=abcd1234; provider --start"
            ),
        }
    ]


def _prepared_profile(provider_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        profile=CompatibilityAgentProfile(name="gpu-kernel-coder", description="GPU role"),
        resolved_provider=provider_id,
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
