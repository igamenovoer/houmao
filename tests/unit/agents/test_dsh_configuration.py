"""Verify explicit DSH route validation and private native home projection."""

import copy
import json
from pathlib import Path

import pytest
import yaml

from houmao.agents.dsh_configuration import (
    DSH_LOCAL_API_KEY_ENV,
    MATERIALIZED_DSH_TOOL_PARAMS,
    DshConfigurationError,
    DshEffectiveToolParams,
    load_dsh_home,
    prepare_dsh_home,
    project_dsh_home_permissions,
    read_dsh_mcp_environment,
)
from houmao.agents.model_mapping_policy import resolve_reasoning_mapping
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.runtime import persist_runtime_launch_inputs
from houmao.agents.tool_params.dsh import DshPermissionParams


def _setup() -> dict:
    """Return a fully explicit synthetic native Messages setup."""

    return {
        "provider": {
            "adapter": "deepseek",
            "protocol": "messages",
            "route": "deepseek-official",
            "base_url_env": "TEST_MESSAGES_ENDPOINT",
            "api_key_env": "TEST_MESSAGES_KEY",
        },
        "models": [
            {
                "id": "test-model",
                "context_window": 8192,
                "max_output_tokens": 128,
                "reasoning_efforts": False,
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


@pytest.mark.parametrize("field", ["context_window", "max_output_tokens", "reasoning_efforts"])
def test_explicit_model_metadata_is_required(field: str) -> None:
    """Do not inherit model capacities or reasoning from provider catalogs."""

    document = _setup()
    del document["models"][0][field]
    with pytest.raises(DshConfigurationError):
        DshEffectiveToolParams.from_mapping(document)


def test_protocol_mismatch_fails_before_projection() -> None:
    """Keep Chat Completions distinct from the native Messages adapter."""

    document = _setup()
    document["provider"]["protocol"] = "openai-completions"
    with pytest.raises(DshConfigurationError, match="adapter/protocol"):
        DshEffectiveToolParams.from_mapping(document)


def test_selected_route_credentials_are_private_and_isolated(tmp_path: Path) -> None:
    """Give each agent its own roots, selected key, and secret-free provenance."""

    setup = DshEffectiveToolParams.from_mapping(_setup())
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
    assert patch["sandbox-policy"]["config"]["mode"] == "danger-full-access"
    assert patch["permission"]["config"]["defaultPreset"] == "danger-full-access"
    assert patch["session-persistence-jsonl"]["config"]["compression"] == "none"
    assert "synthetic-selected-key" not in first.patch_path.read_text()


def test_empty_role_and_credentials_replace_stale_managed_content(tmp_path: Path) -> None:
    """Remove Houmao-owned stale instructions and native credentials on rebuild."""

    setup = DshEffectiveToolParams.from_mapping(_setup())
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
        prepare_dsh_home(
            destination, DshEffectiveToolParams.from_mapping(_setup()), environment, ""
        )
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
    document["models"][0]["reasoning_efforts"] = {"off": None, "high": "custom-wire"}
    setup = DshEffectiveToolParams.from_mapping(document)
    model, effort = setup.select_model("test-model", "high")
    assert model.id == "test-model"
    assert effort == "high"
    prepared = prepare_dsh_home(tmp_path, setup, _environment(), "", reasoning_level="high")
    patch = {entry["id"]: entry for entry in json.loads(prepared.patch_path.read_text())}
    assert patch["llm-deepseek"]["disabled"] is True
    provider = patch["llm-pi-ai"]["config"]["providers"]["houmao-self-hosted"]
    assert provider["api"] == "openai-completions"
    assert provider["models"][0]["reasoningEfforts"] == {"off": None, "high": "custom-wire"}
    assert provider["defaultContextWindow"] == 8192
    assert provider["defaultMaxTokens"] == 128


@pytest.mark.parametrize(
    ("protocol", "compat", "native_compat"),
    [
        (
            "openai-completions",
            {"supports_developer_role": False, "thinking_format": "qwen"},
            {"supportsDeveloperRole": False, "thinkingFormat": "qwen"},
        ),
        (
            "openai-responses",
            {"supports_max_output_tokens": True},
            {"supportsMaxOutputTokens": True},
        ),
        ("anthropic-messages", {"allow_empty_signature": True}, {"allowEmptySignature": True}),
        ("google-generative-ai", None, None),
    ],
)
def test_pi_ai_projects_protocol_model_metadata_and_retry_policy(
    tmp_path: Path, protocol: str, compat: dict | None, native_compat: dict | None
) -> None:
    """Project the native metadata supported by each explicitly selected pi-ai protocol."""

    document = _setup()
    document["provider"].update(adapter="pi-ai", protocol=protocol, route="controlled-generic")
    if compat is not None:
        document["provider"]["compat"] = compat
        document["models"][0]["compat"] = compat
    document["provider"]["retry_policy"] = {
        "mode": "normal",
        "max_retries": 2,
        "retryable_codes": ["rate-limit"],
        "backoff": {"initial_delay_ms": 250, "max_delay_ms": 2000, "jitter_ratio": 0.25},
    }
    document["models"][0].update(name="Controlled Model", input_modalities=["text", "image"])
    setup = DshEffectiveToolParams.from_mapping(document)
    setup = DshEffectiveToolParams.from_mapping(setup.model_dump(mode="json"))
    built = prepare_dsh_home(tmp_path, setup, _environment(), "")
    rows = {
        row["id"]: row["config"]
        for row in json.loads(built.patch_path.read_text())
        if "config" in row
    }
    route = rows["llm-pi-ai"]["providers"]["controlled-generic"]
    assert route["api"] == protocol
    assert route.get("compat") == native_compat
    assert route["models"][0].get("compat") == native_compat
    assert route["models"][0]["name"] == "Controlled Model"
    assert route["models"][0]["input"] == ["text", "image"]
    assert route["models"][0]["reasoningEfforts"] is False
    assert "reasoning" not in route
    assert route["retryPolicy"] == {
        "mode": "normal",
        "maxRetries": 2,
        "retryableCodes": ["rate-limit"],
        "backoff": {"initialDelayMs": 250, "maxDelayMs": 2000, "jitterRatio": 0.25},
    }


@pytest.mark.parametrize(
    ("adapter", "protocol", "route"),
    [
        ("deepseek", "messages", "deepseek-official"),
        ("pi-ai", "openai-responses", "controlled"),
        ("pi-ai", "anthropic-messages", "controlled"),
        ("pi-ai", "google-generative-ai", "controlled"),
    ],
)
def test_endpoint_only_rejects_other_protocols(adapter: str, protocol: str, route: str) -> None:
    """Require a named API key on qualified protocols besides Chat Completions."""

    document = _setup()
    document["provider"].update(adapter=adapter, protocol=protocol, route=route, api_key_env=None)
    with pytest.raises(DshConfigurationError, match="provider.api_key_env"):
        DshEffectiveToolParams.from_mapping(document)


def test_endpoint_only_placeholder_stays_in_native_environment(tmp_path: Path) -> None:
    """Round-trip the explicit null reference and keep the public placeholder out of files."""

    document = _setup()
    document["provider"].update(
        adapter="pi-ai", protocol="openai-completions", route="controlled", api_key_env=None
    )
    setup = DshEffectiveToolParams.from_mapping(document)
    built = prepare_dsh_home(tmp_path, setup, _environment(), "")
    assert built.environment[DSH_LOCAL_API_KEY_ENV] == "houmao-local-no-auth"
    assert "OPENAI_API_KEY" not in built.environment
    assert "DEEPSEEK_API_KEY" not in built.environment
    content = (tmp_path / MATERIALIZED_DSH_TOOL_PARAMS).read_text()
    assert yaml.safe_load(content)["provider"]["api_key_env"] is None
    assert (
        DshEffectiveToolParams.from_file(tmp_path / MATERIALIZED_DSH_TOOL_PARAMS).api_key_env
        is None
    )
    patch_text = built.patch_path.read_text()
    assert DSH_LOCAL_API_KEY_ENV in patch_text
    assert all(
        "houmao-local-no-auth" not in text
        for text in (json.dumps(built.metadata), patch_text, content)
    )


def test_reasoning_slots_normalize_independently_of_wire_strings() -> None:
    """Apply canonical slot ordering, optional off, and saturation."""

    document = _setup()
    document["provider"].update(adapter="pi-ai", protocol="openai-completions", route="controlled")
    document["models"][0]["reasoning_efforts"] = {"max": "custom-max", "low": "custom-low"}
    setup = DshEffectiveToolParams.from_mapping(document)

    def mapping(level: int) -> dict:
        """Resolve common integer input using the effective model catalog."""

        return resolve_reasoning_mapping(
            tool="dsh", requested_level=level, model_name=None, dsh_tool_params=setup
        )

    assert mapping(1)["profile_key"] == "low"
    assert mapping(2)["profile_key"] == "max"
    assert mapping(3)["profile_key"] == "max"
    assert mapping(3)["saturated"]
    with pytest.raises(ValueError, match="does not support reasoning level 0"):
        mapping(0)
    document["models"][0]["reasoning_efforts"]["off"] = "none"
    setup = DshEffectiveToolParams.from_mapping(document)
    assert mapping(0)["profile_key"] == "off"
    assert setup.models[0].reasoning_efforts["off"] == "none"


def test_reasoning_yaml_requires_quoted_off_key() -> None:
    """Keep the off slot a string through YAML parsing."""

    document = _setup()
    document["models"][0]["reasoning_efforts"] = yaml.safe_load("off: null\nhigh: high\n")
    with pytest.raises(DshConfigurationError, match="reasoning_efforts"):
        DshEffectiveToolParams.from_mapping(document)
    document["models"][0]["reasoning_efforts"] = yaml.safe_load("'off': null\nhigh: high\n")
    setup = DshEffectiveToolParams.from_mapping(document)
    assert setup.models[0].reasoning_slots == ("off", "high")


def test_reject_retired_reasoning_shape() -> None:
    """Name the native model field when the retired numbered ladder appears."""

    document = _setup()
    document["models"][0]["reasoning"] = {"0": "off", "1": "high"}
    with pytest.raises(DshConfigurationError, match="use models\\[\\].reasoning_efforts"):
        DshEffectiveToolParams.from_mapping(document)


@pytest.mark.parametrize(
    ("adapter", "protocol", "field"),
    [
        ("deepseek", "messages", "supports_store"),
        ("pi-ai", "openai-responses", "supports_store"),
        ("pi-ai", "google-generative-ai", "supports_developer_role"),
    ],
)
def test_compatibility_fields_are_protocol_gated(adapter: str, protocol: str, field: str) -> None:
    """Reject mismatched model compatibility controls before native startup."""

    document = _setup()
    document["provider"].update(
        adapter=adapter,
        protocol=protocol,
        route="deepseek-official" if adapter == "deepseek" else "controlled",
    )
    document["models"][0]["compat"] = {field: False}
    with pytest.raises(DshConfigurationError, match=r"models.0.compat"):
        DshEffectiveToolParams.from_mapping(document)


def test_chat_template_options_use_native_fields_and_hide_malformed_inputs(tmp_path: Path) -> None:
    """Preserve template option names while hiding dynamic keys from errors."""

    from houmao.agents.tool_params import validate_tool_params

    document = _setup()
    document["provider"].update(adapter="pi-ai", protocol="openai-completions", route="controlled")
    document["provider"]["compat"] = {
        "chat_template_kwargs": {
            "enable_thinking": {"$var": "thinking.enabled", "omit_when_off": True},
            "optional_input": None,
        }
    }
    setup = DshEffectiveToolParams.from_mapping(document)
    prepared = prepare_dsh_home(tmp_path, setup, _environment(), "")
    patch = {row["id"]: row for row in json.loads(prepared.patch_path.read_text())}
    native = patch["llm-pi-ai"]["config"]["providers"]["controlled"]["compat"]
    assert native == {
        "chatTemplateKwargs": {
            "enable_thinking": {"$var": "thinking.enabled", "omitWhenOff": True},
            "optional_input": None,
        }
    }
    document["provider"]["compat"]["chat_template_kwargs"] = {"synthetic-private-key": []}
    with pytest.raises(ValueError, match="provider.compat.chat_template_kwargs") as failure:
        validate_tool_params("dsh", document, source="setup")
    assert "synthetic-private-key" not in str(failure.value)


def test_model_and_reasoning_selections_are_exact() -> None:
    """Refuse unknown model IDs and unsupported effort rather than choosing a fallback."""

    setup = DshEffectiveToolParams.from_mapping(_setup())
    with pytest.raises(DshConfigurationError, match="exact catalog"):
        setup.select_model("other")
    with pytest.raises(DshConfigurationError, match="reasoning level"):
        setup.select_model(reasoning_level="high")


@pytest.mark.parametrize("hmr", [False, True, 0, None])
def test_managed_hmr_rejects_authored_values(hmr: object) -> None:
    """Report a reserved field even when the supplied value matches the managed choice."""

    document = _setup()
    document["hmr"] = hmr
    with pytest.raises(DshConfigurationError, match="reserves hmr.*startup-only"):
        DshEffectiveToolParams.from_mapping(document)


def test_reasoning_requires_an_explicit_boolean_or_presets() -> None:
    """Reject numeric zero in the reasoning capability field."""

    document = _setup()
    document["models"][0]["reasoning_efforts"] = 0
    with pytest.raises(DshConfigurationError, match="must be false"):
        DshEffectiveToolParams.from_mapping(document)


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
            "headers": [{"name": "Authorization", "env_ref": "MCP_AUTH_EXAMPLE"}],
        },
    ]
    prepared = prepare_dsh_home(
        tmp_path,
        DshEffectiveToolParams.from_mapping(document),
        _environment(),
        "",
        credential_environment={"MCP_AUTH_EXAMPLE": "synthetic-private-header"},
    )
    assert prepared.mcp_servers[0] == {
        "name": "local",
        "command": "/usr/bin/true",
        "args": [],
        "env": [],
    }
    assert prepared.mcp_servers[1]["headers"][0]["value"] == "synthetic-private-header"
    assert "synthetic-private-header" not in json.dumps(prepared.metadata)
    assert "synthetic-private-header" not in prepared.patch_path.read_text()
    assert "MCP_AUTH_EXAMPLE" not in prepared.environment
    materialized = tmp_path / MATERIALIZED_DSH_TOOL_PARAMS
    assert "env_ref: MCP_AUTH_EXAMPLE" in materialized.read_text()
    assert "synthetic-private-header" not in materialized.read_text()
    assert materialized.stat().st_mode & 0o777 == 0o600

    private_source = tmp_path / "definition-vars.env"
    private_source.write_text("MCP_AUTH_EXAMPLE=synthetic-private-header\nUNUSED=ignored\n")
    private_source.chmod(0o600)
    launch_plan = LaunchPlan(
        backend="dsh_headless",
        tool="dsh",
        executable="dsh",
        args=[],
        working_directory=tmp_path,
        home_env_var="DSH_HOME",
        home_path=tmp_path,
        env=prepared.environment,
        env_var_names=sorted(prepared.environment),
        role_injection=RoleInjectionPlan(
            method="native_system_prompt_section", role_name="test-role", prompt=""
        ),
        metadata={
            "env_source_file": str(private_source),
            "dsh": {
                "setup_path": str(materialized),
                "mcp_server_names": ["local", "remote"],
            },
        },
    )
    committed = persist_runtime_launch_inputs(launch_plan, session_root=tmp_path / "runtime")
    private_source.unlink()
    assert read_dsh_mcp_environment(
        DshEffectiveToolParams.from_file(materialized), committed.metadata["env_source_file"]
    ) == {"MCP_AUTH_EXAMPLE": "synthetic-private-header"}
    assert "synthetic-private-header" not in json.dumps(committed.redacted_payload())
    assert "MCP_AUTH_EXAMPLE" not in committed.env


@pytest.mark.parametrize("value", [None, "synthetic-private\r\nX-Injected: value"])
def test_invalid_mcp_reference_fails_before_home_creation(
    tmp_path: Path, value: str | None
) -> None:
    """Resolve MCP references exclusively from a valid private bundle."""

    document = _setup()
    document["mcp_servers"] = [
        {
            "name": "remote",
            "type": "http",
            "url": "https://mcp.example.test/rpc",
            "headers": [{"name": "Authorization", "env_ref": "MCP_AUTH_EXAMPLE"}],
        },
    ]
    environment = _environment() | {"MCP_AUTH_EXAMPLE": "synthetic-private-ambient"}
    with pytest.raises(DshConfigurationError) as failure:
        prepare_dsh_home(
            tmp_path / "home",
            DshEffectiveToolParams.from_mapping(document),
            environment,
            "",
            credential_environment={} if value is None else {"MCP_AUTH_EXAMPLE": value},
        )
    assert "synthetic-private" not in str(failure.value)
    assert not (tmp_path / "home").exists()


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
            "env": [{"name": "X", "env_ref": "REF_ONE"}, {"name": "X", "env_ref": "REF_TWO"}],
        },
        {"name": "bad", "type": "http", "url": "file:///private"},
        {
            "name": "bad",
            "type": "http",
            "url": "https://mcp.example.test",
            "headers": [
                {"name": "Authorization", "env_ref": "REF_ONE"},
                {"name": "authorization", "env_ref": "REF_TWO"},
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
        DshEffectiveToolParams.from_mapping(document)
    assert "synthetic-private" not in str(failure.value)


def test_as_is_preserves_native_permissions_while_unattended_is_explicit(tmp_path: Path) -> None:
    """Do not apply unattended permissions when the operator selects native defaults."""

    setup = DshEffectiveToolParams.from_mapping(_setup())
    prepared = prepare_dsh_home(
        tmp_path / "as-is", setup, _environment(), "", operator_prompt_mode="as_is"
    )
    patch = {entry["id"]: entry for entry in json.loads(prepared.patch_path.read_text())}
    assert "approval" not in patch
    assert "sandbox-policy" not in patch
    assert "permission" not in patch
    assert prepared.metadata["operator_prompt_mode"] == "as_is"
    assert prepared.metadata["permissions"] == {}
    unattended = prepare_dsh_home(tmp_path / "unattended", setup, _environment(), "")
    patch = {entry["id"]: entry for entry in json.loads(unattended.patch_path.read_text())}
    assert patch["approval"]["config"]["policy"] == "never"
    assert patch["sandbox-policy"]["config"]["mode"] == "danger-full-access"
    assert patch["permission"]["config"] == {
        "defaultPreset": "danger-full-access",
        "presets": {
            "read-only": {"sandbox": "read-only", "approval": "ask"},
            "workspace-write": {"sandbox": "workspace-write", "approval": "ask"},
            "danger-full-access": {"sandbox": "danger-full-access", "approval": "never"},
        },
    }
    assert unattended.metadata["operator_prompt_mode"] == "unattended"


@pytest.mark.parametrize(
    "operator_prompt_mode,authored,expected",
    [
        ("unattended", {"sandbox": "workspace-write"}, ("workspace-write", "never")),
        ("unattended", {"approval": "ask"}, ("danger-full-access", "ask")),
        ("as_is", {"sandbox": "read-only"}, ("read-only", "ask")),
        ("as_is", {"approval": "never"}, ("workspace-write", "never")),
    ],
)
def test_dsh_permission_fields_compose_independently(
    tmp_path: Path,
    operator_prompt_mode: str,
    authored: dict[str, str],
    expected: tuple[str, str],
) -> None:
    """Use each authored field and the applicable default in a coherent preset."""

    setup = DshEffectiveToolParams.from_mapping({**_setup(), "permissions": authored})
    prepared = prepare_dsh_home(
        tmp_path,
        setup,
        _environment(),
        "",
        operator_prompt_mode=operator_prompt_mode,
        native_profile="headless",
    )
    patch = {
        entry["id"]: entry["config"]
        for entry in json.loads(prepared.patch_path.read_text())
        if "config" in entry
    }
    selected = patch["permission"]["defaultPreset"]
    assert patch["permission"]["presets"][selected] == dict(zip(("sandbox", "approval"), expected))
    loaded = load_dsh_home(tmp_path, setup, _environment(), native_profile="headless")
    assert loaded.permission_preset == selected
    assert (
        DshEffectiveToolParams.from_file(
            tmp_path / MATERIALIZED_DSH_TOOL_PARAMS
        ).permissions.model_dump()
        == authored
    )


def test_raw_permission_projection_replaces_previous_defaults(tmp_path: Path) -> None:
    """Restore native omissions and keep unrelated prepared state across raw starts."""

    prepared = prepare_dsh_home(
        tmp_path, DshEffectiveToolParams.from_mapping(_setup()), _environment(), "original role"
    )
    patch_path = prepared.patch_path
    project_dsh_home_permissions(patch_path, DshPermissionParams(sandbox="read-only"))
    patch = {entry["id"]: entry.get("config") for entry in json.loads(patch_path.read_text())}
    assert patch["permission"]["defaultPreset"] == "read-only"
    assert patch["sandbox-policy"]["mode"] == "read-only"
    assert "approval" not in patch
    project_dsh_home_permissions(patch_path, DshPermissionParams())
    updated = {entry["id"]: entry.get("config") for entry in json.loads(patch_path.read_text())}
    assert updated == {
        name: config
        for name, config in patch.items()
        if name not in {"permission", "sandbox-policy"}
    }
    assert prepared.role_path.read_text() == "original role"


@pytest.mark.parametrize("efforts", [{}, {"off": "none"}, {"high": ""}, {"high": None}, {0: "off"}])
def test_pi_ai_reasoning_requires_a_native_positive_preset(efforts: dict) -> None:
    """Validate the pinned adapter's supported effort names before native launch."""

    document = _setup()
    document["provider"].update(
        adapter="pi-ai", protocol="openai-completions", route="controlled-generic"
    )
    document["models"][0]["reasoning_efforts"] = efforts
    with pytest.raises(DshConfigurationError):
        DshEffectiveToolParams.from_mapping(document)


def test_endpoint_and_key_references_cannot_alias() -> None:
    """Keep route selection and private authentication as separate explicit inputs."""

    document = _setup()
    document["provider"]["api_key_env"] = document["provider"]["base_url_env"]
    with pytest.raises(DshConfigurationError, match="distinct references"):
        DshEffectiveToolParams.from_mapping(document)


@pytest.mark.parametrize("reference", ["DSH_HOME", "DSH_AGENTS_HOME", "HOME", "PATH", "TMUX"])
def test_provider_references_cannot_override_native_isolation(reference: str) -> None:
    """Prevent a selected credential reference from replacing the private native roots."""

    document = _setup()
    document["provider"]["api_key_env"] = reference
    with pytest.raises(DshConfigurationError, match="isolation or process settings"):
        DshEffectiveToolParams.from_mapping(document)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://[",
        "http://model.example:bad",
        "http://model.example:0",
        "http://model.example/\nprivate",
        "http://@model.example/v1",
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
        prepare_dsh_home(
            destination, DshEffectiveToolParams.from_mapping(_setup()), environment, ""
        )
    assert endpoint not in str(failure.value)
    assert not destination.exists()
