from __future__ import annotations

import json
from pathlib import Path

import pytest

from houmao.agents.realm_controller.backends.claude_bootstrap import (
    ensure_claude_home_bootstrap,
)
from houmao.agents.realm_controller.errors import (
    BackendExecutionError,
)


def _prepare_home(
    tmp_path: Path,
    *,
    settings: str = '{"skipDangerousModePermissionPrompt": true}\n',
    template: str | None = "{}\n",
) -> Path:
    home = tmp_path / "claude-home"
    home.mkdir()
    (home / "settings.json").write_text(settings, encoding="utf-8")
    if template is not None:
        (home / "claude_state.template.json").write_text(template, encoding="utf-8")
    return home


def test_bootstrap_materializes_state_with_api_key_and_is_create_only(
    tmp_path: Path,
) -> None:
    home = _prepare_home(
        tmp_path,
        template=json.dumps(
            {
                "mcpServers": {"local": {"command": "python", "args": ["-m", "mcp"]}},
                "custom": {"keep": True},
            }
        ),
    )
    api_key = "sk-live-abcdefghijklmnopqrstuvwxyz1234567890"

    ensure_claude_home_bootstrap(
        home_path=home,
        env={"ANTHROPIC_API_KEY": api_key},
    )
    written = (home / ".claude.json").read_text(encoding="utf-8")
    payload = json.loads(written)

    assert payload["hasCompletedOnboarding"] is True
    assert payload["numStartups"] == 1
    assert payload["customApiKeyResponses"] == {
        "approved": [api_key[-20:]],
        "rejected": [],
    }
    assert payload["mcpServers"]["local"]["command"] == "python"
    assert payload["custom"]["keep"] is True
    assert api_key not in written

    existing = home / ".claude.json"
    existing.write_text('{"existing":true}\n', encoding="utf-8")
    ensure_claude_home_bootstrap(
        home_path=home,
        env={"ANTHROPIC_API_KEY": "sk-new-value"},
    )
    assert json.loads(existing.read_text(encoding="utf-8")) == {"existing": True}


def test_bootstrap_materializes_state_without_api_key(tmp_path: Path) -> None:
    home = _prepare_home(tmp_path)
    credentials_path = home / ".credentials.json"
    credentials_path.write_text(
        '{"claudeAiOauth": {"accessToken": "vendor-access-token"}}\n',
        encoding="utf-8",
    )

    ensure_claude_home_bootstrap(home_path=home, env={})

    payload = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
    assert payload["hasCompletedOnboarding"] is True
    assert payload["numStartups"] == 1
    assert "customApiKeyResponses" not in payload
    assert credentials_path.read_text(encoding="utf-8") == (
        '{"claudeAiOauth": {"accessToken": "vendor-access-token"}}\n'
    )


def test_bootstrap_preserves_template_mcp_servers(tmp_path: Path) -> None:
    home = _prepare_home(
        tmp_path,
        template=json.dumps(
            {
                "mcpServers": {
                    "repo": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                    }
                }
            }
        ),
    )

    ensure_claude_home_bootstrap(home_path=home, env={})

    payload = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
    assert payload["mcpServers"]["repo"]["command"] == "npx"
    assert payload["mcpServers"]["repo"]["args"] == [
        "-y",
        "@modelcontextprotocol/server-filesystem",
    ]


def test_bootstrap_skips_template_when_vendor_runtime_state_already_exists(tmp_path: Path) -> None:
    home = _prepare_home(tmp_path, template=None)
    runtime_state_path = home / ".claude.json"
    credentials_path = home / ".credentials.json"
    runtime_state_path.write_text('{"hasCompletedOnboarding": true, "numStartups": 9}\n', encoding="utf-8")
    credentials_path.write_text(
        '{"claudeAiOauth": {"accessToken": "vendor-access-token"}}\n',
        encoding="utf-8",
    )

    ensure_claude_home_bootstrap(
        home_path=home,
        env={"CLAUDE_CODE_OAUTH_TOKEN": "oauth-token-test"},
    )

    assert json.loads(runtime_state_path.read_text(encoding="utf-8")) == {
        "hasCompletedOnboarding": True,
        "numStartups": 9,
    }
    assert credentials_path.read_text(encoding="utf-8") == (
        '{"claudeAiOauth": {"accessToken": "vendor-access-token"}}\n'
    )


def test_bootstrap_fails_when_template_missing(tmp_path: Path) -> None:
    home = _prepare_home(tmp_path, template=None)

    with pytest.raises(BackendExecutionError, match="Missing Claude bootstrap template"):
        ensure_claude_home_bootstrap(home_path=home, env={})


def test_bootstrap_fails_when_template_malformed(tmp_path: Path) -> None:
    home = _prepare_home(tmp_path, template="{not-json")

    with pytest.raises(BackendExecutionError, match="Malformed Claude bootstrap template"):
        ensure_claude_home_bootstrap(home_path=home, env={})


def test_bootstrap_fails_when_settings_prompt_flag_missing(tmp_path: Path) -> None:
    home = _prepare_home(
        tmp_path,
        settings='{"skipDangerousModePermissionPrompt": false}\n',
    )

    with pytest.raises(
        BackendExecutionError,
        match="skipDangerousModePermissionPrompt",
    ):
        ensure_claude_home_bootstrap(home_path=home, env={})
