from __future__ import annotations

from houmao.server.control_core.provider_adapters import CodexCompatibilityProvider


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
