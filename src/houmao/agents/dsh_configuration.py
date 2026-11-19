"""Materialize isolated DSH profiles and read their current invocation inputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from tempfile import mkstemp
from typing import Any, Literal

import yaml

from houmao.agents.tool_params.dsh import (
    MATERIALIZED_DSH_TOOL_PARAMS as MATERIALIZED_DSH_TOOL_PARAMS,
    DshConfigurationError as DshConfigurationError,
    DshEffectiveToolParams as DshEffectiveToolParams,
    DshModel,
    DshPermissionParams,
    DshToolParamsAdapter,
    validate_http_url,
)

DSH_LOCAL_API_KEY_ENV = "HOUMAO_DSH_LOCAL_API_KEY"
_DSH_LOCAL_API_KEY_VALUE = "houmao-local-no-auth"
_NATIVE_PERMISSION_PRESETS = {
    "read-only": {"sandbox": "read-only", "approval": "ask"},
    "workspace-write": {"sandbox": "workspace-write", "approval": "ask"},
    "danger-full-access": {"sandbox": "danger-full-access", "approval": "never"},
}
_PERMISSION_CONFIG_ROWS = frozenset({"approval", "sandbox-policy", "permission"})


@dataclass(frozen=True)
class DshPreparedHome:
    """Return private launch inputs separately from public, credential-free provenance."""

    patch_path: Path
    role_path: Path
    persistence_root: Path
    agents_home: Path
    environment: dict[str, str]
    model: str
    provider: str
    metadata: dict[str, Any]
    mcp_servers: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class DshLoadedHome:
    """Carry current native defaults and optional private invocation overrides."""

    patch_path: Path
    role_path: Path
    persistence_root: Path
    agents_home: Path
    environment: dict[str, str]
    mcp_servers: tuple[dict[str, Any], ...]
    model: tuple[str, str]
    reasoning_effort: str | None
    invocation_patch: tuple[dict[str, Any], ...]
    permission_preset: str | None


def load_dsh_home(
    home_path: Path,
    setup: DshEffectiveToolParams,
    environment: Mapping[str, str],
    *,
    credential_environment: Mapping[str, str] | None = None,
    selected_model: str | None = None,
    reasoning_level: str | None = None,
    native_profile: Literal["acp", "headless"] = "acp",
) -> DshLoadedHome:
    """Read a materialized home without rebuilding or repairing its files.

    Parameters
    ----------
    home_path:
        Existing managed native home. Launch materialization owns its creation.
    setup:
        Current setup loaded from its selected file, including current ACP MCP
        declarations and explicit credential references.
    environment:
        Explicit selected invocation environment, filtered for credential isolation.
    credential_environment:
        Selected private bundle values for resolving MCP references.
    selected_model, reasoning_level:
        Request-scoped overrides only. Absent controls select the current
        materialized native defaults rather than a previous turn's override.
    native_profile:
        Select the native profile that owns the materialized model row.

    Returns
    -------
    DshLoadedHome
        Read-only native paths, selected private environment, current MCP inputs,
        and a detached transient patch for explicit model controls.

    Raises
    ------
    DshConfigurationError
        Required material is missing or an explicit override cannot be applied.
    """

    if native_profile == "headless":
        DshToolParamsAdapter().prepare_launch(setup, backend="dsh_headless")
    home = home_path.resolve()
    patch_path = home / "houmao-profile.patch.json"
    role_path = home / "houmao-role.txt"
    agents_home = home / "shared-agents"
    if (
        not home.is_dir()
        or not role_path.is_file()
        or not (home / "houmao-empty-credentials.yaml").is_file()
        or not agents_home.is_dir()
    ):
        raise DshConfigurationError("DSH requires an existing materialized native home")
    try:
        raw = json.loads(patch_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DshConfigurationError("Cannot read the materialized DSH native patch") from exc
    if not isinstance(raw, list) or any(not isinstance(row, dict) for row in raw):
        raise DshConfigurationError("DSH native patch must contain a list of rows")
    configs = {
        row["id"]: row["config"]
        for row in raw
        if isinstance(row.get("id"), str) and "config" in row
    }
    persistence = _mapping(configs.get("session-persistence-jsonl"), "persistence config")
    persistence_root = Path(_text(persistence.get("root"), "persistence root"))
    if not persistence_root.is_absolute() or not persistence_root.is_dir():
        raise DshConfigurationError("DSH requires an existing absolute persistence root")
    private_environment = dsh_native_environment(home, setup, environment)
    patch: list[dict[str, Any]] = []
    selection_row = "agent-default-model" if native_profile == "headless" else "acp"
    selection = dict(_mapping(configs.get(selection_row), f"materialized {selection_row} config"))
    provider_name = _text(selection.get("provider"), f"materialized {selection_row} provider")
    model_name = _text(selection.get("model"), f"materialized {selection_row} model")
    model_selection = (provider_name, model_name)
    native_effort = selection.get("reasoningEffort") if native_profile == "headless" else None
    effort = (
        _text(native_effort, "materialized reasoning effort")
        if native_effort is not None
        else _materialized_reasoning(configs, provider_name, model_name)
    )
    if selected_model is not None or reasoning_level is not None:
        model_name = selected_model or model_name
        model, effort = setup.select_model(model_name, reasoning_level)
        if selected_model is not None and effort is None and model.reasoning_slots:
            effort = model.reasoning_slots[0]
        if selected_model is not None:
            model_selection = (setup.route, model.id)
            selection.update({"provider": setup.route, "model": model.id})
        if setup.adapter == "deepseek":
            config = dict(_mapping(configs.get("llm-deepseek"), "materialized adapter config"))
            if selected_model is not None:
                config.update(
                    {
                        "maxTokens": model.max_output_tokens,
                        "defaultContextWindow": model.context_window,
                    }
                )
            effort = _project_deepseek_reasoning(config, model, effort)
            patch.append({"id": "llm-deepseek", "config": config})
        else:
            config = dict(_mapping(configs.get("llm-pi-ai"), "materialized adapter config"))
            providers = dict(_mapping(config.get("providers"), "materialized providers"))
            provider = dict(_mapping(providers.get(setup.route), "materialized provider"))
            if selected_model is not None:
                provider.update(
                    {
                        "defaultMaxTokens": model.max_output_tokens,
                        "defaultContextWindow": model.context_window,
                    }
                )
                if model.reasoning_efforts is False:
                    provider.pop("reasoning", None)
            if effort is not None:
                provider["reasoning"] = effort
            providers[setup.route] = provider
            config["providers"] = providers
            patch.append({"id": "llm-pi-ai", "config": config})
        if native_profile == "headless" and effort is not None and model.reasoning_efforts:
            selection["reasoningEffort"] = effort
        if selected_model is not None or native_profile == "headless":
            patch.append({"id": selection_row, "config": selection})
    permission_config = configs.get("permission")
    permission_preset = (
        _mapping(permission_config, "materialized permission config").get("defaultPreset")
        if permission_config is not None
        else None
    )
    return DshLoadedHome(
        patch_path,
        role_path,
        persistence_root,
        agents_home,
        private_environment,
        _resolve_mcp_servers(setup, credential_environment),
        model_selection,
        effort,
        tuple(patch),
        _text(permission_preset, "materialized permission preset")
        if permission_preset is not None
        else None,
    )


def _materialized_reasoning(configs: Mapping[str, Any], provider: str, model: str) -> str | None:
    """Read native provider defaults without mapping frozen launch selections."""

    if provider == "deepseek-official":
        config = _mapping(configs.get("llm-deepseek"), "materialized adapter config")
        if config.get("thinking") == "disabled":
            return "off"
        return _text(config.get("reasoningEffort", "high"), "materialized reasoning effort")
    config = _mapping(configs.get("llm-pi-ai"), "materialized adapter config")
    providers = _mapping(config.get("providers"), "materialized providers")
    profile = _mapping(providers.get(provider), "materialized provider")
    catalog = profile.get("models", [])
    if not isinstance(catalog, list):
        raise DshConfigurationError("Materialized provider models must be a list")
    entry = next(
        (item for item in catalog if isinstance(item, dict) and item.get("id") == model),
        None,
    )
    if entry is None or not isinstance(entry.get("reasoningEfforts"), dict):
        return None
    # ACP advertises the empty value when the provider has no explicit default.
    value = profile.get("reasoning", "")
    if not isinstance(value, str):
        raise DshConfigurationError("Materialized reasoning effort must be a string")
    return value


def _project_deepseek_reasoning(
    config: dict[str, Any], model: DshModel, selected_slot: str | None
) -> str:
    """Use native DeepSeek effort names and keep capable models selectable."""

    if model.reasoning_efforts is False:
        config.update({"thinking": "disabled", "reasoningEffort": "off"})
        return "off"
    slot = selected_slot or model.reasoning_slots[0]
    config.update({"thinking": "enabled", "reasoningEffort": slot})
    return slot


def _selected_credentials(
    setup: DshEffectiveToolParams, environment: Mapping[str, str]
) -> tuple[str, str]:
    """Validate and return the explicitly selected provider endpoint and key."""

    endpoint = environment.get(setup.base_url_env, "").strip()
    if not endpoint:
        raise DshConfigurationError(f"DSH launch requires endpoint reference {setup.base_url_env}")
    parsed = validate_http_url(endpoint, field="endpoint")
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise DshConfigurationError(
            "DSH endpoint cannot contain credentials, query parameters, or fragments"
        )
    if setup.api_key_env is None:
        return endpoint, _DSH_LOCAL_API_KEY_VALUE
    key = environment.get(setup.api_key_env, "")
    if not key.strip():
        raise DshConfigurationError(f"DSH launch requires credential reference {setup.api_key_env}")
    return endpoint, key


def dsh_native_environment(
    home: Path, setup: DshEffectiveToolParams, environment: Mapping[str, str]
) -> dict[str, str]:
    """Select declared routing/authentication without changing native home files."""

    endpoint, key = _selected_credentials(setup, environment)
    mcp_names = setup.mcp_env_refs
    result = {
        name: value
        for name, value in environment.items()
        if name
        not in {"DSH_HOME", "DSH_AGENTS_HOME", "DSH_PERMISSION_MODE", "DSH_BUNDLED_SKILL_DIR"}
        and name not in mcp_names
        and not re.search(r"API_KEY|TOKEN|SECRET|PASSWORD|ACCESS_KEY|BASE_URL", name)
    }
    result.update(
        {
            "DSH_HOME": str(home),
            "DSH_AGENTS_HOME": str(home / "shared-agents"),
            setup.api_key_env or DSH_LOCAL_API_KEY_ENV: key,
            setup.base_url_env: endpoint,
        }
    )
    return result


def _project_models(setup: DshEffectiveToolParams) -> list[dict[str, Any]]:
    """Serialize the exact model catalog in the selected native adapter's format."""

    catalog: list[dict[str, Any]] = []
    native_input = "inputModalities" if setup.adapter == "deepseek" else "input"
    for entry in setup.models:
        model: dict[str, Any] = {
            "id": entry.id,
            "contextWindow": entry.context_window,
            "maxTokens": entry.max_output_tokens,
            native_input: entry.input_modalities or ["text"],
        }
        if entry.name is not None:
            model["name"] = entry.name
        if setup.adapter == "pi-ai":
            model["reasoningEfforts"] = entry.reasoning_efforts
            if entry.compat is not None:
                model["compat"] = entry.compat.model_dump(
                    mode="json", by_alias=True, exclude_none=True
                )
        catalog.append(model)
    return catalog


def read_dsh_mcp_environment(
    setup: DshEffectiveToolParams, source: str | Path | None
) -> dict[str, str]:
    """Read only current MCP references from the selected private bundle."""

    names = sorted(setup.mcp_env_refs)
    if not names:
        return {}
    if not isinstance(source, (str, Path)):
        raise DshConfigurationError("DSH MCP requires the selected private credential source")

    from houmao.agents.realm_controller.loaders import parse_env_text

    try:
        descriptor = os.open(source, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(descriptor, encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077
            ):
                raise DshConfigurationError("DSH MCP requires an owner-private credential file")
            values = parse_env_text(stream.read())
    except (OSError, UnicodeError):
        raise DshConfigurationError("Cannot read the selected DSH MCP credential source") from None
    return {name: values[name] for name in names if name in values}


def _resolve_mcp_servers(
    setup: DshEffectiveToolParams, credential_environment: Mapping[str, str] | None
) -> tuple[dict[str, Any], ...]:
    """Project reference values solely into their declared native MCP entries."""

    bundle = credential_environment if credential_environment is not None else {}
    servers: list[dict[str, Any]] = []
    for index, server in enumerate(setup.mcp_servers):
        payload = server.model_dump(exclude_none=True, exclude={"headers", "env"})
        is_header = server.type == "http"
        field = "headers" if is_header else "env"
        entries = (server.headers if is_header else server.env) or []
        native_entries = []
        for entry_index, entry in enumerate(entries):
            value = bundle.get(entry.env_ref)
            field_path = f"mcp_servers.{index}.{field}.{entry_index}.env_ref"
            if value is None:
                raise DshConfigurationError(f"DSH {field_path} is missing in the selected bundle")
            if is_header and any(
                ord(c) > 255 or ord(c) == 127 or (ord(c) < 32 and c != "\t") for c in value
            ):
                raise DshConfigurationError(f"DSH {field_path} resolves to an invalid header value")
            if not is_header and "\x00" in value:
                raise DshConfigurationError(f"DSH {field_path} resolves to an invalid env value")
            native_entries.append({"name": entry.name, "value": value})
        payload[field] = native_entries
        if not is_header:
            payload.setdefault("args", [])
        servers.append(payload)
    return tuple(servers)


def validate_dsh_launch(
    setup: DshEffectiveToolParams,
    environment: Mapping[str, str],
    *,
    credential_environment: Mapping[str, str] | None = None,
    selected_model: str | None = None,
    reasoning_level: str | None = None,
) -> None:
    """Check DSH birth-time inputs without changing the runtime home."""

    setup.select_model(selected_model, reasoning_level)
    _selected_credentials(setup, environment)
    _resolve_mcp_servers(setup, credential_environment)
    if any(not Path(root).is_dir() for root in setup.skill_roots):
        raise DshConfigurationError("Every selected DSH skill root must exist as a directory")


def prepare_dsh_home(
    home_path: Path,
    setup: DshEffectiveToolParams,
    environment: Mapping[str, str],
    role_prompt: str,
    *,
    credential_environment: Mapping[str, str] | None = None,
    selected_model: str | None = None,
    reasoning_level: str | None = None,
    skill_roots: Sequence[Path] = (),
    operator_prompt_mode: str = "unattended",
    native_profile: Literal["acp", "headless"] = "acp",
    permissions: DshPermissionParams | None = None,
) -> DshPreparedHome:
    """Project an isolated native profile and literal role without installing software.

    Parameters
    ----------
    home_path:
        Managed agent home containing its generated configuration and journal root.
    setup:
        Validated route, exact model catalog, and explicit skill/MCP declarations.
    environment:
        Selected credential environment. Public metadata retains reference names only.
    credential_environment:
        Selected private bundle values for resolving MCP references.
    role_prompt:
        Complete effective native system section, preserved as literal text.
    selected_model, reasoning_level:
        Optional common launch overrides resolved against the exact setup catalog.
    skill_roots:
        Additional existing skill directories selected by managed brain construction.
    operator_prompt_mode:
        ``unattended`` applies the qualified no-question permissions. ``as_is``
        preserves native permission defaults without adding unattended overrides.
    native_profile:
        Select the native profile that receives the managed model defaults.
    permissions:
        Permission fields resolved for this startup. Standalone preparation
        without a versioned policy uses the supported DSH profile defaults.

    Returns
    -------
    DshPreparedHome
        Private subprocess inputs and credential-free public provenance.

    Raises
    ------
    DshConfigurationError
        Required selected inputs or supported native configuration are invalid.
    """

    if operator_prompt_mode not in {"unattended", "as_is"}:
        raise DshConfigurationError("DSH operator prompt mode must be unattended or as_is")
    if native_profile == "headless":
        DshToolParamsAdapter().prepare_launch(setup, backend="dsh_headless")
    model, effort = setup.select_model(selected_model, reasoning_level)
    if effort is None and model.reasoning_slots:
        effort = model.reasoning_slots[0]
    home = home_path.resolve()
    private_env = dsh_native_environment(home, setup, environment)
    endpoint = private_env[setup.base_url_env]
    mcp_servers = _resolve_mcp_servers(setup, credential_environment)
    roots = tuple(
        dict.fromkeys(
            [*(Path(root) for root in setup.skill_roots), *(p.resolve() for p in skill_roots)]
        )
    )
    if any(not root.is_dir() for root in roots):
        raise DshConfigurationError("Every selected DSH skill root must exist as a directory")
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    home.chmod(0o700)
    params = setup.model_dump(mode="json", exclude_none=True)
    if setup.api_key_env is None:
        params["provider"]["api_key_env"] = None
    _write_private(home / MATERIALIZED_DSH_TOOL_PARAMS, yaml.safe_dump(params, sort_keys=False))
    agents_home = home / "shared-agents"
    agents_home.mkdir(exist_ok=True, mode=0o700)
    persistence = home / "sessions"
    persistence.mkdir(exist_ok=True, mode=0o700)
    role_path = home / "houmao-role.txt"
    _write_private(role_path, role_prompt)
    credentials_path = home / "houmao-empty-credentials.yaml"
    _write_private(credentials_path, "{}\n")
    provider_options: dict[str, Any] = {
        "baseURL": endpoint,
        "apiKeyEnv": setup.api_key_env or DSH_LOCAL_API_KEY_ENV,
        "models": _project_models(setup),
        "defaultContextWindow": model.context_window,
    }
    if setup.provider.retry_policy is not None:
        provider_options["retryPolicy"] = setup.provider.retry_policy.model_dump(
            mode="json", by_alias=True, exclude_none=True
        )
    patch: list[dict[str, Any]] = [
        {
            "id": "session-persistence-jsonl",
            "config": {"root": str(persistence), "compression": "none"},
        },
        {"id": "credentials", "config": {"path": str(credentials_path), "watch": False}},
        {
            "id": "skill-filesystem",
            "config": {
                "includeDefaultRoots": False,
                "dshHome": str(home),
                "agentsHome": str(agents_home),
                "customSkillDirs": [str(root) for root in roots],
                "watch": False,
            },
        },
        {"id": "hmr", "disabled": True},
        {"id": "goal-round-driver", "disabled": True},
        {"id": "llm-deepseek-account", "disabled": True},
        {
            "id": "agent-default-model" if native_profile == "headless" else "acp",
            "config": {"provider": setup.route, "model": model.id},
        },
    ]
    if native_profile == "headless":
        patch.append({"id": "session-title-llm", "disabled": True})
    if permissions is None:
        permissions = setup.permissions
        if operator_prompt_mode == "unattended":
            permissions = DshPermissionParams(
                sandbox=permissions.sandbox or "danger-full-access",
                approval=permissions.approval or "never",
            )
    permission_rows, preset = _dsh_permission_configuration(permissions)
    patch.extend(permission_rows)
    if setup.adapter == "deepseek":
        provider_options["maxTokens"] = model.max_output_tokens
        _project_deepseek_reasoning(provider_options, model, effort)
        patch.extend(
            [
                {"id": "llm-deepseek", "config": provider_options},
                {"id": "llm-pi-ai", "config": {"providers": {}}},
            ]
        )
    else:
        provider_options.update(
            {"api": setup.protocol, "defaultMaxTokens": model.max_output_tokens}
        )
        if setup.provider.compat is not None:
            provider_options["compat"] = setup.provider.compat.model_dump(
                mode="json", by_alias=True, exclude_none=True
            )
        if effort is not None:
            provider_options["reasoning"] = effort
        patch.extend(
            [
                {"id": "llm-deepseek", "disabled": True},
                {"id": "llm-pi-ai", "config": {"providers": {setup.route: provider_options}}},
            ]
        )
    patch_path = home / "houmao-profile.patch.json"
    _write_private(patch_path, json.dumps(patch, ensure_ascii=False, indent=2) + "\n")
    metadata: dict[str, Any] = {
        "adapter": setup.adapter,
        "protocol": setup.protocol,
        "provider": setup.route,
        "model": model.id,
        "context_window": model.context_window,
        "max_output_tokens": model.max_output_tokens,
        "base_url_env": setup.base_url_env,
        "api_key_env": setup.api_key_env,
        "reasoning_effort": effort,
        "role_sha256": hashlib.sha256(role_prompt.encode()).hexdigest(),
        "activation": "startup-only",
        "operator_prompt_mode": operator_prompt_mode,
        "permissions": permissions.model_dump(mode="json", exclude_none=True),
        "permission_preset": preset,
        "journal_format": 4,
        "journal_compression": "none",
    }
    return DshPreparedHome(
        patch_path,
        role_path,
        persistence,
        agents_home,
        private_env,
        model.id,
        setup.route,
        metadata,
        mcp_servers,
    )


def project_dsh_home_permissions(patch_path: Path, permissions: DshPermissionParams) -> None:
    """Replace the generated permission fragments in a prepared raw ACP launch patch."""

    try:
        patch = json.loads(patch_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DshConfigurationError("Cannot read the materialized DSH native patch") from exc
    if not isinstance(patch, list) or any(not isinstance(row, dict) for row in patch):
        raise DshConfigurationError("DSH native patch must contain a list of rows")
    rows, _ = _dsh_permission_configuration(permissions)
    updated = [row for row in patch if row.get("id") not in _PERMISSION_CONFIG_ROWS] + rows
    if updated != patch:
        _write_private(patch_path, json.dumps(updated, ensure_ascii=False, indent=2) + "\n")


def _dsh_permission_configuration(
    permissions: DshPermissionParams,
) -> tuple[list[dict[str, Any]], str | None]:
    """Compose one native preset with the same sandbox and approval as service defaults."""

    if permissions.sandbox is None and permissions.approval is None:
        return [], None
    # The DSH base profile uses workspace-write + ask with DSH_PERMISSION_MODE unset.
    pair: dict[str, str] = {
        "sandbox": permissions.sandbox or "workspace-write",
        "approval": permissions.approval or "ask",
    }
    presets = dict(_NATIVE_PERMISSION_PRESETS)
    preset = next((name for name, value in presets.items() if value == pair), None)
    if preset is None:
        preset = "houmao-managed"
        presets[preset] = pair
    patch: list[dict[str, Any]] = []
    if permissions.sandbox is not None:
        patch.append({"id": "sandbox-policy", "config": {"mode": pair["sandbox"]}})
    if permissions.approval is not None:
        patch.append({"id": "approval", "config": {"policy": pair["approval"]}})
    patch.append({"id": "permission", "config": {"presets": presets, "defaultPreset": preset}})
    return patch, preset


def _mapping(value: object, field: str) -> dict[str, Any]:
    """Require a string-keyed configuration object."""

    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise DshConfigurationError(f"DSH {field} must be an object")
    return value


def _text(value: object, field: str) -> str:
    """Require an explicit nonempty text input."""

    if not isinstance(value, str) or not value.strip():
        raise DshConfigurationError(f"DSH {field} must be a nonempty string")
    return value


def _write_private(path: Path, text: str) -> None:
    """Publish complete Houmao-owned generated state with owner-only permissions."""

    descriptor, name = mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary_path = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
