from __future__ import annotations

import pytest

from houmao.agents.codex_cli_config import (
    CodexCliConfigOverride,
    append_or_replace_codex_config_overrides,
    codex_provider_cli_config_overrides,
)


def test_codex_cli_config_override_renders_toml_scalars_and_quoted_key_paths() -> None:
    assert (
        CodexCliConfigOverride(("projects", "/tmp/work tree", "trust_level"), True).to_arg()
        == '--config=projects."/tmp/work tree".trust_level=true'
    )
    assert (
        CodexCliConfigOverride(("model_reasoning_effort",), "low").to_arg()
        == '--config=model_reasoning_effort="low"'
    )
    assert (
        CodexCliConfigOverride(
            ("model_providers", "openai.compat", "wire_api"), "responses"
        ).to_arg()
        == '--config=model_providers."openai.compat".wire_api="responses"'
    )
    assert CodexCliConfigOverride(("limit",), 3).to_arg() == "--config=limit=3"


def test_append_or_replace_codex_config_overrides_removes_conflicting_forms() -> None:
    args = [
        '--config=model_reasoning_effort="xhigh"',
        "-c",
        'sandbox_mode="read-only"',
        "--config",
        'approval_policy="on-request"',
        "--keep",
    ]

    append_or_replace_codex_config_overrides(
        args,
        (
            CodexCliConfigOverride(("approval_policy",), "never"),
            CodexCliConfigOverride(("sandbox_mode",), "danger-full-access"),
        ),
    )

    assert args == [
        '--config=model_reasoning_effort="xhigh"',
        "--keep",
        '--config=approval_policy="never"',
        '--config=sandbox_mode="danger-full-access"',
    ]


def test_codex_provider_cli_config_overrides_include_only_non_secret_provider_fields() -> None:
    overrides = codex_provider_cli_config_overrides(
        {
            "model_provider": "yunwu-openai",
            "model_providers": {
                "yunwu-openai": {
                    "name": "Yunwu",
                    "base_url": "https://api.example.test/v1",
                    "env_key": "OPENAI_API_KEY",
                    "requires_openai_auth": False,
                    "wire_api": "responses",
                    "api_key": "sk-secret",
                }
            },
        }
    )

    args = [override.to_arg() for override in overrides]
    assert '--config=model_provider="yunwu-openai"' in args
    assert '--config=model_providers.yunwu-openai.base_url="https://api.example.test/v1"' in args
    assert '--config=model_providers.yunwu-openai.env_key="OPENAI_API_KEY"' in args
    assert all("sk-secret" not in arg for arg in args)


def test_codex_cli_config_override_rejects_secret_key_paths() -> None:
    with pytest.raises(ValueError, match="secret-like key path"):
        CodexCliConfigOverride(("model_providers", "default", "api_key"), "sk-secret")


def test_codex_cli_config_override_rejects_secret_like_values() -> None:
    with pytest.raises(ValueError, match="secret-like value"):
        CodexCliConfigOverride(
            ("model_providers", "default", "base_url"),
            "https://api.example.test/v1?token=secret",
        )
