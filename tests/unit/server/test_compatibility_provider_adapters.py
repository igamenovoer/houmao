from __future__ import annotations

from houmao.server.control_core.provider_adapters import (
    ClaudeCompatibilityProvider,
    CodexCompatibilityProvider,
    GeminiCompatibilityProvider,
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


def test_gemini_provider_exit_terminal_uses_escape() -> None:
    """Gemini compatibility interrupt should use Escape."""

    calls: list[tuple[str, str]] = []

    class _FakeTmux:
        def send_special_key(self, *, window_id: str, key_name: str) -> None:
            calls.append((window_id, key_name))

    adapter = GeminiCompatibilityProvider()
    adapter.exit_terminal(tmux=_FakeTmux(), window_id="@11")  # type: ignore[arg-type]

    assert calls == [("@11", "Escape")]
