"""Verify explicit DSH route validation and private native home projection."""

import copy
import json
from pathlib import Path

import pytest

from houmao.agents.dsh_configuration import DshConfigurationError, DshSetup, prepare_dsh_home


def _setup() -> dict:
    """Return a fully explicit synthetic native Messages setup."""

    return {
        "version": 1,
        "provider": {
            "adapter": "deepseek",
            "protocol": "messages",
            "route": "deepseek-official",
            "base_url_env": "TEST_MESSAGES_ENDPOINT",
            "api_key_env": "TEST_MESSAGES_KEY",
        },
        "selected_model": "test-model",
        "models": [
            {
                "id": "test-model",
                "context_window": 8192,
                "max_output_tokens": 128,
                "reasoning": False,
            }
        ],
    }


def _environment() -> dict[str, str]:
    """Provide selected references alongside deliberately conflicting ambient auth."""

    return {
        "PATH": "/usr/bin",
        "TEST_MESSAGES_ENDPOINT": "http://127.0.0.1:9000/v1",
        "TEST_MESSAGES_KEY": "synthetic-selected-key",
        "DEEPSEEK_API_KEY": "synthetic-unselected-key",
        "OPENAI_API_KEY": "ambient-unwanted-key",
        "DEEPSEEK_BASE_URL_ANTHROPIC": "https://ambient.example/anthropic",
        "DSH_HOME": "/ambient/home",
        "DSH_AGENTS_HOME": "/ambient/agents",
        "DSH_PERMISSION_MODE": "danger-full-access",
    }


@pytest.mark.parametrize("field", ["context_window", "max_output_tokens", "reasoning"])
def test_explicit_model_metadata_is_required(field: str) -> None:
    """Do not inherit model capacities or reasoning from provider catalogs."""

    document = _setup()
    del document["models"][0][field]
    with pytest.raises(DshConfigurationError):
        DshSetup.from_mapping(document)


def test_protocol_mismatch_fails_before_projection() -> None:
    """Keep Chat Completions distinct from the native Messages adapter."""

    document = _setup()
    document["provider"]["protocol"] = "openai-completions"
    with pytest.raises(DshConfigurationError, match="adapter/protocol"):
        DshSetup.from_mapping(document)


def test_selected_route_credentials_are_private_and_isolated(tmp_path: Path) -> None:
    """Give each agent its own roots, selected key, and secret-free provenance."""

    setup = DshSetup.from_mapping(_setup())
    first = prepare_dsh_home(tmp_path / "one", setup, _environment(), "{{literal role}}")
    second = prepare_dsh_home(tmp_path / "two", setup, _environment(), "other role")
    assert first.persistence_root != second.persistence_root
    assert first.agents_home != second.agents_home
    assert first.environment["DSH_HOME"] != second.environment["DSH_HOME"]
    assert first.environment["TEST_MESSAGES_KEY"] == "synthetic-selected-key"
    assert "DEEPSEEK_API_KEY" not in first.environment
    assert "OPENAI_API_KEY" not in first.environment
    assert "DEEPSEEK_BASE_URL_ANTHROPIC" not in first.environment
    assert "DSH_PERMISSION_MODE" not in first.environment
    serialized = json.dumps(first.metadata)
    assert "synthetic-selected-key" not in serialized
    assert "127.0.0.1" not in serialized
    assert first.metadata["api_key_env"] == "TEST_MESSAGES_KEY"
    assert first.role_path.read_text() == "{{literal role}}"
    assert first.patch_path.stat().st_mode & 0o777 == 0o600
    patch = {entry["id"]: entry for entry in json.loads(first.patch_path.read_text())}
    assert patch["skill-filesystem"]["config"]["includeDefaultRoots"] is False
    assert patch["skill-filesystem"]["config"]["watch"] is False
    assert patch["hmr"]["disabled"] is True
    assert patch["approval"]["config"]["policy"] == "never"
    assert patch["session-persistence-jsonl"]["config"]["compression"] == "none"
    assert "synthetic-selected-key" not in first.patch_path.read_text()


def test_empty_role_and_credentials_replace_stale_managed_content(tmp_path: Path) -> None:
    """Remove Houmao-owned stale instructions and native credentials on rebuild."""

    setup = DshSetup.from_mapping(_setup())
    first = prepare_dsh_home(tmp_path, setup, _environment(), "old role")
    credentials = tmp_path / "houmao-empty-credentials.yaml"
    credentials.write_text("version: 1\nrefs:\n  TEST_MESSAGES_KEY: synthetic-stale\n")
    second = prepare_dsh_home(tmp_path, setup, _environment(), "")
    assert first.role_path == second.role_path
    assert second.role_path.read_text() == ""
    assert credentials.read_text() == "{}\n"


@pytest.mark.parametrize("missing", ["TEST_MESSAGES_ENDPOINT", "TEST_MESSAGES_KEY"])
def test_missing_reference_fails_before_creating_home(tmp_path: Path, missing: str) -> None:
    """Require the selected environment instead of falling back to ambient credentials."""

    environment = _environment()
    del environment[missing]
    destination = tmp_path / "not-created"
    with pytest.raises(DshConfigurationError, match=missing):
        prepare_dsh_home(destination, DshSetup.from_mapping(_setup()), environment, "")
    assert not destination.exists()


def test_pi_ai_uses_explicit_generic_catalog_and_reasoning(tmp_path: Path) -> None:
    """Preserve a generic compatible route without borrowing native DeepSeek defaults."""

    document = copy.deepcopy(_setup())
    document["provider"].update(
        {
            "adapter": "pi-ai",
            "protocol": "openai-completions",
            "route": "houmao-self-hosted",
        }
    )
    document["models"][0]["reasoning"] = {"0": "off", "1": "high"}
    setup = DshSetup.from_mapping(document)
    model, effort = setup.select_model("test-model", "1")
    assert model.id == "test-model"
    assert effort == "high"
    prepared = prepare_dsh_home(tmp_path, setup, _environment(), "", reasoning_level="1")
    patch = {entry["id"]: entry for entry in json.loads(prepared.patch_path.read_text())}
    assert patch["llm-deepseek"]["disabled"] is True
    provider = patch["llm-pi-ai"]["config"]["providers"]["houmao-self-hosted"]
    assert provider["api"] == "openai-completions"
    assert provider["models"][0]["reasoningEfforts"] == {"off": "off", "high": "high"}
    assert provider["defaultContextWindow"] == 8192
    assert provider["defaultMaxTokens"] == 128


def test_model_and_reasoning_selections_are_exact() -> None:
    """Refuse unknown model IDs and unsupported effort rather than choosing a fallback."""

    setup = DshSetup.from_mapping(_setup())
    with pytest.raises(DshConfigurationError, match="exact catalog"):
        setup.select_model("other")
    with pytest.raises(DshConfigurationError, match="reasoning level"):
        setup.select_model(reasoning_level="high")


def test_managed_hmr_cannot_be_enabled() -> None:
    """Make startup-only resource activation explicit."""

    document = _setup()
    document["hmr"] = True
    with pytest.raises(DshConfigurationError, match="startup-only"):
        DshSetup.from_mapping(document)


@pytest.mark.parametrize("adapter", ["deepseek", "pi-ai"])
def test_mcp_entries_are_canonical_for_the_selected_route(adapter: str, tmp_path: Path) -> None:
    """Pass explicit MCP entries without putting values into public provenance."""

    document = _setup()
    if adapter == "pi-ai":
        document["provider"].update(
            adapter="pi-ai", protocol="openai-completions", route="controlled-generic"
        )
    document["mcp_servers"] = [
        {"name": "local", "command": "/usr/bin/true"},
        {
            "name": "remote",
            "type": "http",
            "url": "https://mcp.example.test/rpc",
            "headers": [{"name": "Authorization", "value": "synthetic-private-header"}],
        },
    ]
    prepared = prepare_dsh_home(tmp_path, DshSetup.from_mapping(document), _environment(), "")
    assert prepared.mcp_servers[0] == {
        "name": "local",
        "command": "/usr/bin/true",
        "args": [],
        "env": [],
    }
    assert prepared.mcp_servers[1]["headers"][0]["value"] == "synthetic-private-header"
    assert "synthetic-private-header" not in json.dumps(prepared.metadata)


@pytest.mark.parametrize(
    "server",
    [
        {"name": "bad", "type": "sse", "url": "https://mcp.example.test"},
        {"name": "bad", "command": "relative-command"},
        {"name": "bad", "command": "/usr/bin/true", "args": [1]},
        {"name": "bad", "command": "/usr/bin/true", "env": {"NAME": "synthetic-private"}},
        {"name": "bad", "command": "/usr/bin/true", "env": [{"name": "X", "value": 1}]},
        {
            "name": "bad",
            "command": "/usr/bin/true",
            "env": [{"name": "X", "value": "one"}, {"name": "X", "value": "two"}],
        },
        {"name": "bad", "type": "http", "url": "file:///private"},
        {
            "name": "bad",
            "type": "http",
            "url": "https://mcp.example.test",
            "headers": [
                {"name": "Authorization", "value": "synthetic-private"},
                {"name": "authorization", "value": "synthetic-private"},
            ],
        },
        {
            "name": "bad",
            "type": "http",
            "url": "https://mcp.example.test",
            "headers": [{"name": "Authorization", "value": "synthetic-private\r\nX: value"}],
        },
    ],
)
def test_invalid_mcp_declarations_fail_before_native_start(server: dict) -> None:
    """Refuse unsupported transports and malformed private fields without exposing values."""

    document = _setup()
    document["mcp_servers"] = [server]
    with pytest.raises(DshConfigurationError) as failure:
        DshSetup.from_mapping(document)
    assert "synthetic-private" not in str(failure.value)


def test_as_is_preserves_native_permissions_while_unattended_is_explicit(tmp_path: Path) -> None:
    """Do not apply unattended permissions when the operator selects native defaults."""

    setup = DshSetup.from_mapping(_setup())
    prepared = prepare_dsh_home(
        tmp_path / "as-is", setup, _environment(), "", operator_prompt_mode="as_is"
    )
    patch = {entry["id"]: entry for entry in json.loads(prepared.patch_path.read_text())}
    assert "approval" not in patch
    assert "sandbox-policy" not in patch
    assert prepared.metadata["operator_prompt_mode"] == "as_is"
    unattended = prepare_dsh_home(tmp_path / "unattended", setup, _environment(), "")
    patch = {entry["id"]: entry for entry in json.loads(unattended.patch_path.read_text())}
    assert patch["approval"]["config"]["policy"] == "never"
    assert patch["sandbox-policy"]["config"]["mode"] == "workspace-write"
    assert unattended.metadata["operator_prompt_mode"] == "unattended"


@pytest.mark.parametrize("efforts", [{"0": "off"}, {"1": "off"}, {"1": "invented"}])
def test_pi_ai_reasoning_requires_a_native_positive_preset(efforts: dict) -> None:
    """Validate the pinned adapter's supported effort names before native launch."""

    document = _setup()
    document["provider"].update(
        adapter="pi-ai", protocol="openai-completions", route="controlled-generic"
    )
    document["models"][0]["reasoning"] = efforts
    with pytest.raises(DshConfigurationError):
        DshSetup.from_mapping(document)


def test_endpoint_and_key_references_cannot_alias() -> None:
    """Keep route selection and private authentication as separate explicit inputs."""

    document = _setup()
    document["provider"]["api_key_env"] = document["provider"]["base_url_env"]
    with pytest.raises(DshConfigurationError, match="distinct references"):
        DshSetup.from_mapping(document)


@pytest.mark.parametrize("reference", ["DSH_HOME", "DSH_AGENTS_HOME", "HOME", "PATH", "TMUX"])
def test_provider_references_cannot_override_native_isolation(reference: str) -> None:
    """Prevent a selected credential reference from replacing the private native roots."""

    document = _setup()
    document["provider"]["api_key_env"] = reference
    with pytest.raises(DshConfigurationError, match="isolation or process settings"):
        DshSetup.from_mapping(document)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://[",
        "http://model.example:bad",
        "http://model.example:0",
        "http://model.example/\nprivate",
    ],
)
def test_malformed_provider_endpoint_fails_without_public_values(
    tmp_path: Path, endpoint: str
) -> None:
    """Validate endpoint syntax before creating a managed home or leaking the URL."""

    environment = _environment()
    environment["TEST_MESSAGES_ENDPOINT"] = endpoint
    destination = tmp_path / "not-created"
    with pytest.raises(DshConfigurationError) as failure:
        prepare_dsh_home(destination, DshSetup.from_mapping(_setup()), environment, "")
    assert endpoint not in str(failure.value)
    assert not destination.exists()
