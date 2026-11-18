"""Tests for authoring, precedence, and safe tool-parameter diagnostics."""

from pathlib import Path

import pytest

from houmao.agents.launch_overrides import LaunchDefaults, resolve_launch_behavior
from houmao.agents.tool_params import (
    merge_partial_tool_params,
    parse_tool_params_cli_input,
    resolve_tool_params,
    validate_tool_params,
)


def test_claude_partial_model_preserves_omitted_and_false_values() -> None:
    """An omitted setting inherits and an explicit false clears a true flag."""

    layers = [
        ("adapter", {"include_partial_messages": True}),
        ("setup", {}),
        ("preset", {"include_partial_messages": False}),
        ("launch_profile", {}),
    ]
    assert validate_tool_params("claude", {}, source="setup") == {}
    assert resolve_tool_params("claude", layers) == {"include_partial_messages": False}
    assert resolve_tool_params(
        "claude", [*layers, ("direct", {"include_partial_messages": True})]
    ) == {"include_partial_messages": True}


def test_claude_backend_projects_partial_messages_only_for_headless() -> None:
    """Tool-owned flags are validated when a backend is selected."""

    selected = {"include_partial_messages": True}
    result = resolve_launch_behavior(
        tool="claude",
        backend="claude_headless",
        adapter_defaults=LaunchDefaults(args=("--other-flag",)),
        recipe_overrides=None,
        direct_overrides=None,
        tool_params=selected,
    )
    assert result.args_before_policy == ("--other-flag", "--include-partial-messages")
    with pytest.raises(ValueError, match=r"include_partial_messages.*unsupported.*raw_launch"):
        resolve_launch_behavior(
            tool="claude",
            backend="raw_launch",
            adapter_defaults=LaunchDefaults(),
            recipe_overrides=None,
            direct_overrides=None,
            tool_params=selected,
        )


@pytest.mark.parametrize("tool", ["codex", "kimi"])
def test_empty_baseline_schemas_reject_foreign_values(tool: str) -> None:
    """Other tools keep strict schemas until they own a typed parameter."""

    with pytest.raises(ValueError, match="preset"):
        validate_tool_params(
            tool, {"include_partial_messages": "synthetic-secret"}, source="preset"
        )


def test_strict_errors_name_fields_without_echoing_values() -> None:
    """Validation errors display schema diagnostics and omit the raw input."""

    with pytest.raises(ValueError, match=r"preset\.include_partial_messages:") as raised:
        validate_tool_params(
            "claude", {"include_partial_messages": "synthetic-secret"}, source="preset"
        )
    assert "synthetic-secret" not in str(raised.value)


def test_dsh_models_and_mcp_servers_merge_by_identity() -> None:
    """A patch can update one named record and preserve the other fields."""

    base = {
        "provider": {
            "adapter": "pi-ai",
            "protocol": "openai-completions",
            "route": "local-llm",
            "api_key_env": "OPENAI_API_KEY",
            "base_url_env": "OPENAI_BASE_URL",
        },
        "models": [
            {
                "id": "first",
                "context_window": 1024,
                "max_output_tokens": 256,
                "reasoning_efforts": {"high": "upstream-high"},
                "compat": {"supports_store": False},
            },
            {
                "id": "second",
                "context_window": 1024,
                "max_output_tokens": 256,
                "reasoning_efforts": False,
            },
        ],
        "mcp_servers": [
            {
                "name": "audit",
                "type": "http",
                "url": "http://localhost/audit",
                "headers": [{"name": "Authorization", "env_ref": "AUDIT_AUTH"}],
            }
        ],
    }
    profile = {
        "provider": {"base_url_env": "LOCAL_BASE_URL"},
        "models": [
            {
                "id": "first",
                "max_output_tokens": 512,
                "reasoning_efforts": {"off": None, "low": "upstream-low"},
                "compat": {"supports_developer_role": False},
            }
        ],
        "mcp_servers": [{"name": "audit", "headers": None}],
    }
    partial = merge_partial_tool_params("dsh", [("profile", profile)])
    assert partial["mcp_servers"] == [{"name": "audit", "headers": None}]

    merged = resolve_tool_params("dsh", [("setup", base), ("profile", profile)])
    assert merged["provider"]["base_url_env"] == "LOCAL_BASE_URL"
    assert merged["provider"]["api_key_env"] == "OPENAI_API_KEY"
    assert [model["id"] for model in merged["models"]] == ["first", "second"]
    assert merged["models"][0]["context_window"] == 1024
    assert merged["models"][0]["max_output_tokens"] == 512
    assert merged["models"][0]["reasoning_efforts"] == {
        "high": "upstream-high",
        "low": "upstream-low",
        "off": None,
    }
    assert merged["models"][0]["compat"]["supports_store"] is False
    assert merged["models"][0]["compat"]["supports_developer_role"] is False
    assert merged["mcp_servers"][0]["url"] == "http://localhost/audit"
    assert merged["mcp_servers"][0]["headers"] is None


def test_tool_params_cli_reads_json_and_owner_relative_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recognize both CLI forms and resolve a referenced file from the current owner."""

    monkeypatch.chdir(tmp_path)
    Path("settings.yaml").write_text("include_partial_messages: true\n")
    assert parse_tool_params_cli_input("@settings.yaml") == {"include_partial_messages": True}
    assert parse_tool_params_cli_input('{"include_partial_messages": true}') == {
        "include_partial_messages": True,
    }
    Path("invalid.yaml").write_text("include_partial_messages: [synthetic-secret\n")
    with pytest.raises(ValueError, match="invalid.yaml") as raised:
        parse_tool_params_cli_input("@invalid.yaml")
    assert "synthetic-secret" not in str(raised.value)
