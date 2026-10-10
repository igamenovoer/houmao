from __future__ import annotations

import shlex
from pathlib import Path

import pytest

from houmao.server.control_core.models import CompatibilityAgentProfile
from houmao.server.control_core.provider_adapters import (
    ClaudeCompatibilityProvider,
    CompatibilityProviderError,
    CodexCompatibilityProvider,
    KimiCompatibilityProvider,
    supported_provider_ids,
)


def test_supported_provider_ids_are_exact() -> None:
    """The compatibility control core exposes only its maintained providers."""

    assert supported_provider_ids() == (
        "claude_code",
        "codex",
        "kimi_cli",
        "kiro_cli",
        "q_cli",
    )


def test_codex_provider_recognizes_live_idle_prompt_line() -> None:
    """Codex idle screens may include prompt text on the same line as the cursor."""

    adapter = CodexCompatibilityProvider()
    output_text = """
╭─────────────────────────────────────────────────────╮
│ >_ OpenAI Codex (v0.116.0)                          │
╰─────────────────────────────────────────────────────╯

  Tip: New Build faster with Codex.

⚠ `OPENAI_BASE_URL` is deprecated. Set `openai_base_url` in config.toml instead.

› Improve documentation in @filename

  gpt-5.4 xhigh · 100% left · /tmp/workdir
"""

    assert adapter.get_status(output_text=output_text, profile_name="server-api-smoke") == "idle"


def test_codex_provider_exit_terminal_uses_escape() -> None:
    """Codex compatibility interrupt should use Escape."""

    calls: list[tuple[str, str]] = []

    class _FakeTmux:
        def send_special_key(self, *, window_id: str, key_name: str) -> None:
            calls.append((window_id, key_name))

    adapter = CodexCompatibilityProvider()
    adapter.exit_terminal(tmux=_FakeTmux(), window_id="@7")  # type: ignore[arg-type]

    assert calls == [("@7", "Escape")]


def test_claude_provider_exit_terminal_uses_escape() -> None:
    """Claude compatibility interrupt should use Escape."""

    calls: list[tuple[str, str]] = []

    class _FakeTmux:
        def send_special_key(self, *, window_id: str, key_name: str) -> None:
            calls.append((window_id, key_name))

    adapter = ClaudeCompatibilityProvider()
    adapter.exit_terminal(tmux=_FakeTmux(), window_id="@9")  # type: ignore[arg-type]

    assert calls == [("@9", "Escape")]


def test_kimi_compatibility_provider_writes_v034_markdown_agent_file(tmp_path: Path) -> None:
    """Deprecated CAO compatibility uses Kimi's current Markdown profile syntax."""

    adapter = KimiCompatibilityProvider()
    command = adapter.build_command(
        profile=CompatibilityAgentProfile(
            name="researcher",
            description="Research profile",
            system_prompt="Follow the compatibility role.",
        ),
        profile_name="researcher",
        terminal_id="terminal-1",
        working_directory=tmp_path,
    )

    command_parts = shlex.split(command)
    assert "--auto" in command_parts
    assert "--yolo" not in command_parts
    agent_path = Path(command_parts[command_parts.index("--agent-file") + 1])
    assert agent_path.name == "agent.md"
    assert agent_path.read_text(encoding="utf-8") == (
        "---\n"
        "name: houmao-cao-profile\n"
        "description: Temporary Houmao CAO compatibility profile\n"
        "override: true\n"
        "---\n\n"
        "${base_prompt}\n\n"
        "Follow the compatibility role.\n"
    )


def test_kimi_compatibility_provider_rejects_prompt_placeholders(tmp_path: Path) -> None:
    """CAO compatibility shares the all-placeholder rejection contract."""

    with pytest.raises(CompatibilityProviderError, match=r"\$\{cwd\}"):
        KimiCompatibilityProvider().build_command(
            profile=CompatibilityAgentProfile(
                name="researcher",
                description="Research profile",
                system_prompt="Literal ${cwd} is unsafe.",
            ),
            profile_name="researcher",
            terminal_id="terminal-1",
            working_directory=tmp_path,
        )
